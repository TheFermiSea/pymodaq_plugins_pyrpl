# PyRPL Worker Safeguards Documentation

This document details all the safeguards, checks, and protective mechanisms implemented in the PyRPL worker architecture to ensure robust and reliable operation.

## Table of Contents
1. [Critical FPGA Bitstream Protection](#critical-fpga-bitstream-protection)
2. [Shared Worker Architecture](#shared-worker-architecture)
3. [Hardware Module Validation](#hardware-module-validation)
4. [Connection Health Checks](#connection-health-checks)
5. [Error Recovery Mechanisms](#error-recovery-mechanisms)
6. [Configuration Management](#configuration-management)

---

## Critical FPGA Bitstream Protection

### The Problem
PyRPL requires its **custom FPGA bitstream** to be loaded onto the Red Pitaya for hardware modules (ASG, PID, Scope, IQ) to function. Setting `reloadfpga: False` in the configuration prevents this critical loading step, causing all hardware modules to fail silently.

### The Solution

#### 1. Never Set `reloadfpga: False`
**Location:** `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` (lines 101-170)

```python
# ============================================================
# CRITICAL: FPGA Bitstream Loading Configuration
# ============================================================
# PyRPL REQUIRES its custom FPGA bitstream to be loaded for
# hardware modules (ASG, PID, Scope, IQ) to function.
# 
# DO NOT set reloadfpga=False unless you are 100% certain
# the PyRPL bitstream is already loaded.
# 
# The default (reloadfpga=True) is CORRECT and NECESSARY.
# ============================================================
```

#### 2. Automatic Config Fixing
The worker now **automatically detects and removes** any `reloadfpga: False` settings:

```python
# CRITICAL: Remove any reloadfpga=False settings
if existing_config and 'redpitaya' in existing_config:
    if 'reloadfpga' in existing_config['redpitaya']:
        if existing_config['redpitaya']['reloadfpga'] == False:
            logger.warning("FIXING CRITICAL BUG: Removing reloadfpga=False from config")
            logger.warning("PyRPL REQUIRES FPGA bitstream to be loaded!")
            del existing_config['redpitaya']['reloadfpga']
            config_modified = True
```

**This safeguard prevents future agents or developers from accidentally breaking hardware support.**

---

## Shared Worker Architecture

### The Problem
Each plugin creating its own PyRPL worker process causes:
- Multiple concurrent SSH connections to Red Pitaya
- Monitor server conflicts ("NoneType object is not subscriptable" errors)
- Connection instability
- FPGA bitstream reload conflicts

### The Solution

#### SharedPyRPLManager Singleton
**Location:** `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`

All 4 IPC plugins now use the same singleton manager:
1. `DAQ_1DViewer_PyRPL_Scope_IPC`
2. `DAQ_0DViewer_PyRPL_IQ_IPC`
3. `DAQ_Move_PyRPL_PID_IPC`
4. `DAQ_Move_PyRPL_ASG_IPC`

```python
# In each plugin __init__:
self.manager = None  # Will hold SharedPyRPLManager instance

# In _start_worker():
self.manager = get_shared_worker_manager()  # Singleton!
self.command_queue, self.response_queue = self.manager.start_worker(config)
```

#### Benefits
- **ONE PyRPL instance** shared across all plugins
- **ONE SSH connection** to Red Pitaya
- **ONE FPGA bitstream load** (takes 5-7 seconds once, not per plugin)
- **UUID-based command multiplexing** prevents cross-talk

---

## Hardware Module Validation

### The Problem
Without validation, FPGA bitstream loading failures go undetected, leading to silent failures where commands appear to work but hardware doesn't respond.

### The Solution

#### Post-Initialization Validation
**Location:** `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` (lines 178-200)

After PyRPL initialization, we **explicitly test** access to critical hardware modules:

```python
# ============================================================
# VALIDATION: Test that hardware modules are accessible
# ============================================================
# This verifies the FPGA bitstream was loaded successfully
logger.info("Validating PyRPL hardware module access...")
try:
    # Test scope module access
    scope_test = pyrpl_instance.rp.scope
    logger.info(f"✓ Scope module accessible: {scope_test}")
    
    # Test that ASG is accessible (critical for signal generation)
    asg_test = pyrpl_instance.rp.asg0
    logger.info(f"✓ ASG module accessible: {asg_test}")
    
    # Test PID accessibility
    pid_test = pyrpl_instance.rp.pid0
    logger.info(f"✓ PID module accessible: {pid_test}")
    
    logger.info("✓ All critical hardware modules validated successfully")
except AttributeError as e:
    logger.error(f"❌ Hardware module validation FAILED: {e}")
    logger.error("This indicates FPGA bitstream was NOT loaded properly!")
    raise RuntimeError(f"FPGA bitstream validation failed: {e}")
```

#### What This Detects
- ✅ FPGA bitstream loaded correctly
- ✅ Hardware modules are accessible
- ✅ PyRPL initialization completed fully
- ❌ Missing or failed FPGA bitstream load
- ❌ Hardware communication issues

---

## Connection Health Checks

### Retry Logic
**Location:** `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` (lines 92-220)

Network connections can be unstable. The worker implements automatic retry:

```python
max_retries = 3
retry_delay = 2.0

for attempt in range(max_retries):
    try:
        if attempt > 0:
            logger.warning(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
            time.sleep(retry_delay)
        
        # Initialize PyRPL
        pyrpl_instance = pyrpl.Pyrpl(...)
        break  # Success!
        
    except (OSError, IOError, TimeoutError) as e:
        last_error = e
        logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
        
        # Clean up partial connection
        if pyrpl_instance:
            pyrpl_instance.close()
        
        if attempt == max_retries - 1:
            raise last_error
```

### Ping Command
The worker responds to `ping` commands to verify it's alive and responsive:

```python
if command == 'ping':
    ping_response = {'status': 'ok', 'data': 'pong'}
    if cmd_id:
        ping_response['id'] = cmd_id
    response_queue.put(ping_response)
    continue
```

Plugins use this during startup to verify connection:

```python
# In plugin _start_worker():
response = self.manager.send_command('ping', {}, timeout=timeout)

if response['status'] == 'ok' and response['data'] == 'pong':
    self.is_connected = True
```

---

## Error Recovery Mechanisms

### 1. Graceful Shutdown
**Location:** All plugin `close()` methods

Plugins **never** shutdown the shared worker because other plugins may still need it:

```python
def close(self):
    """
    Close plugin connection and clean up resources.
    Does NOT shutdown shared worker - other plugins may be using it.
    """
    # Clean up local references only
    self.command_queue = None
    self.response_queue = None
    self.manager = None
    self.is_connected = False
```

The SharedPyRPLManager handles worker lifecycle via `atexit` handlers.

### 2. Command Error Isolation
Each command execution is wrapped in try/except to prevent one bad command from crashing the worker:

```python
try:
    response = _handle_pyrpl_command(pyrpl_instance, command, params)
    if cmd_id:
        response['id'] = cmd_id
    response_queue.put(response)
    
except Exception as e:
    error_msg = f"Command execution error: {e}\\n{traceback.format_exc()}"
    logger.error(error_msg)
    error_response = {
        'status': 'error',
        'data': error_msg
    }
    if cmd_id:
        error_response['id'] = cmd_id
    response_queue.put(error_response)
```

### 3. Clean Resource Cleanup
Worker cleanup is thorough and error-tolerant:

```python
# Cleanup
logger.info("Cleaning up PyRPL worker...")

if pyrpl_instance is not None:
    try:
        logger.info("Closing PyRPL connection...")
        pyrpl_instance.close()
    except Exception as e:
        logger.error(f"Error closing PyRPL: {e}")

# Send final shutdown confirmation
try:
    response_queue.put({
        'status': 'ok',
        'data': 'PyRPL worker shutdown complete'
    })
except Exception:
    pass
```

---

## Configuration Management

### 1. Minimal Configuration
The worker creates minimal configs to avoid buggy PyRPL modules:

```python
minimal_config = {
    'pyrpl': {
        'name': config_name,
        'modules': [],  # Don't load problematic modules (NetworkAnalyzer has bugs)
        'loglevel': 'info',
        'background_color': ''
    },
    'redpitaya': {
        'hostname': hostname,
        'port': port,
        'user': 'root',
        'password': 'root',
        'gui': False,
        'autostart': True,
        # reloadfpga: Let PyRPL decide (defaults to True, which is correct)
        # DO NOT set reloadfpga=False - it breaks hardware modules!
    }
}
```

### 2. Config Self-Healing
The worker automatically fixes problematic configs:

```python
# Ensure pyrpl modules list is empty (avoid NetworkAnalyzer bugs)
if existing_config and 'pyrpl' in existing_config:
    if existing_config['pyrpl'].get('modules') != []:
        existing_config['pyrpl']['modules'] = []
        config_modified = True
        logger.info("Set pyrpl.modules=[] to avoid buggy modules")

# CRITICAL: Remove any reloadfpga=False settings
if existing_config and 'redpitaya' in existing_config:
    if 'reloadfpga' in existing_config['redpitaya']:
        if existing_config['redpitaya']['reloadfpga'] == False:
            logger.warning("FIXING CRITICAL BUG: Removing reloadfpga=False from config")
            logger.warning("PyRPL REQUIRES FPGA bitstream to be loaded!")
            del existing_config['redpitaya']['reloadfpga']
            config_modified = True
```

---

## Testing Safeguards

### Mock Mode
All safeguards work in mock mode for development without hardware:

```python
if mock_mode:
    logger.info("Mock mode enabled - skipping PyRPL initialization")
    response = _handle_mock_command(command, params)
    if cmd_id:
        response['id'] = cmd_id
    response_queue.put(response)
    continue
```

### Comprehensive Test Suite
- `tests/test_command_multiplexing.py` - 5/5 mock tests ✅
- `tests/test_command_multiplexing_hardware.py` - 5/5 hardware tests ✅
- `tests/test_pid_hardware.py` - 5/5 PID tests ✅
- **Total: 15/15 tests passing**

---

## Common Pitfalls & How We Prevent Them

### 1. ❌ Setting `reloadfpga: False`
**Prevention:** Automatic detection and removal from configs
**Detection:** Hardware module validation fails if bitstream not loaded

### 2. ❌ Multiple Worker Processes
**Prevention:** SharedPyRPLManager singleton enforced
**Detection:** Plugins now cannot create their own worker processes

### 3. ❌ Silent Hardware Failures
**Prevention:** Post-initialization hardware module validation
**Detection:** Worker raises RuntimeError if modules inaccessible

### 4. ❌ Uncaught Command Errors
**Prevention:** All command execution wrapped in try/except
**Detection:** Error responses sent back to plugin with full traceback

### 5. ❌ Resource Leaks
**Prevention:** Explicit cleanup in worker shutdown and plugin close()
**Detection:** Response listener thread tracks pending responses

---

## Monitoring & Debugging

### Log Messages
All critical operations are logged:

```
[PyRPL Worker] INFO: Creating minimal config at ~/pyrpl_user_dir/config/pymodaq.yml
[PyRPL Worker] INFO: FPGA bitstream will be loaded (this takes ~5-7 seconds on first connection)
[PyRPL Worker] INFO: Config created - PyRPL will load FPGA bitstream automatically
[PyRPL Worker] INFO: Validating PyRPL hardware module access...
[PyRPL Worker] INFO: ✓ Scope module accessible: <...>
[PyRPL Worker] INFO: ✓ ASG module accessible: <...>
[PyRPL Worker] INFO: ✓ PID module accessible: <...>
[PyRPL Worker] INFO: ✓ All critical hardware modules validated successfully
[PyRPL Worker] INFO: PyRPL initialized successfully with FPGA bitstream loaded
```

### Warning Messages
Critical issues are highlighted:

```
[PyRPL Worker] WARNING: FIXING CRITICAL BUG: Removing reloadfpga=False from config
[PyRPL Worker] WARNING: PyRPL REQUIRES FPGA bitstream to be loaded!
```

### Error Messages
Failures are explicit:

```
[PyRPL Worker] ERROR: ❌ Hardware module validation FAILED: ...
[PyRPL Worker] ERROR: This indicates FPGA bitstream was NOT loaded properly!
```

---

## Summary of Protections

| Protection | Purpose | Implementation |
|------------|---------|----------------|
| FPGA Bitstream Safeguard | Ensures hardware modules work | Auto-removes `reloadfpga: False` |
| Shared Worker Singleton | Prevents multiple PyRPL instances | SharedPyRPLManager enforced |
| Hardware Module Validation | Detects FPGA loading failures | Post-init accessibility test |
| Connection Retry | Handles network instability | 3 retries with 2s delay |
| Ping/Pong Health Check | Verifies worker responsiveness | `ping` command support |
| Command Error Isolation | Prevents single failure cascade | Per-command try/except |
| Graceful Shutdown | Clean resource cleanup | Multiple fallback mechanisms |
| Config Self-Healing | Fixes problematic settings | Automatic config validation |
| Comprehensive Logging | Debugging and monitoring | All critical operations logged |

---

## For Future Developers

### DO's ✅
- Use `get_shared_worker_manager()` for all IPC plugins
- Let PyRPL manage FPGA bitstream loading (default behavior)
- Test hardware module accessibility after initialization
- Implement retry logic for network operations
- Log all critical operations
- Handle errors gracefully and return informative messages

### DON'Ts ❌
- **NEVER** set `reloadfpga: False` in configs
- **NEVER** create separate PyRPL worker processes
- **NEVER** assume FPGA bitstream is loaded without validation
- **NEVER** shutdown shared worker from individual plugins
- **NEVER** ignore connection errors without retry
- **NEVER** let one command failure crash the entire worker

---

## References

- Worker Implementation: `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`
- Shared Manager: `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`
- Plugin Examples: `src/pymodaq_plugins_pyrpl/daq_*_plugins/`
- Test Suite: `tests/test_command_multiplexing*.py`

---

**Last Updated:** October 2025  
**Status:** Production Ready - All safeguards tested and validated
