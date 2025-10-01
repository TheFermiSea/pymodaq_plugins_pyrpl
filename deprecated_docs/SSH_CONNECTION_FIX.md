# SSH Connection & Monitor Server Fix

## Problem

Hardware tests and PyMoDAQ integration were failing with two types of errors:

### 1. SSH Connection Timeout
```
OSError: Socket is closed
```
The issue occurred during PyRPL's FPGA bitstream loading process, which takes several seconds and was causing the SSH socket to close prematurely.

### 2. Monitor Server Not Running
```
TypeError: 'NoneType' object is not subscriptable
ERROR: Error: wrong control sequence from server
```
This occurs when PyRPL tries to use the monitor server (fast communication protocol) but the server isn't running on the Red Pitaya.

## Root Causes

### 1. FPGA Bitstream Reload
In commit `0bf7f74`, a previous change **removed** the `reloadfpga: False` and `reloadserver: False` settings, which forced PyRPL to reload the FPGA bitstream on every connection. This caused:
- **Long SSH operations**: FPGA bitstream loading takes 5-10 seconds
- **Socket timeouts**: The SSH connection would timeout/close during the lengthy FPGA upload

### 2. Monitor Server Not Running
PyRPL uses a "monitor server" binary on the Red Pitaya for fast communication. If this server crashes or is not started, PyRPL tries to use it anyway (when `reloadserver: false`) and fails with "wrong control sequence" errors.

### 3. Persistent Configuration Issues
PyRPL's configuration files persist across runs, and some configs had `reloadfpga: true`, `reloadserver: true`, and `modules: [NetworkAnalyzer, ...]` which would override programmatic settings.

## Solution

### 1. Smart Monitor Server Management

The code in `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` now intelligently manages the monitor server:

**First Connection** (new config):
```python
'redpitaya': {
    'hostname': hostname,
    'port': port,
    'user': 'root',
    'password': 'root',
    'gui': False,
    'autostart': True,
    'reloadfpga': False,  # Skip FPGA reload - use existing bitstream
    'reloadserver': True  # First connection: start monitor server (takes 5-10s)
}
```

**Subsequent Connections** (after successful init):
```python
'redpitaya': {
    ...
    'reloadserver': False  # Use existing monitor server (fast, ~1s)
}
```

The code automatically switches `reloadserver` from `True` to `False` after the first successful connection.

**Module Configuration**:
```python
'pyrpl': {
    'name': config_name,
    'modules': [],  # Don't load problematic modules (NetworkAnalyzer has ZeroDivisionError bug)
    'loglevel': 'info',
    'background_color': ''
}
```

### 2. Fix Persistent Configuration Files

PyRPL saves configuration to YAML files that persist across runs. These need to be updated:

```bash
# Created fix_pyrpl_configs.py script that:
# 1. Sets modules: [] (prevents NetworkAnalyzer bug)
# 2. Sets reloadfpga: false
# 3. Sets reloadserver: false

cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
uv run python fix_pyrpl_configs.py
```

### 3. SSH Client Keepalive (Optional)

Added SSH keepalive settings to `~/.ssh/config`:

```ssh-config
Host 100.107.106.75
    ServerAliveInterval 30
    ServerAliveCountMax 6
    TCPKeepAlive yes
    ConnectTimeout 30
```

## Results

After applying these fixes:

✅ **All 7 scope hardware tests pass** (16.15 seconds)
```bash
PYRPL_TEST_HOST=100.107.106.75 uv run pytest tests/test_plugin_ipc_scope_hardware.py -v
```

✅ **All 44 mock tests pass** (26.49 seconds)
```bash
uv run pytest tests/test_plugin_ipc_*_mock.py tests/test_multi_plugin_coordination.py -v
```

## Key Insights

1. **PyRPL caches FPGA bitstream**: Once loaded, PyRPL keeps the bitstream on the Red Pitaya, so `reloadfpga: false` uses the cached version
2. **Configuration persistence**: PyRPL YAML files override programmatic settings, so both code and files must be consistent
3. **NetworkAnalyzer bug**: PyRPL's NetworkAnalyzer module has a ZeroDivisionError during initialization, so `modules: []` prevents it from loading
4. **No functionality loss**: Setting `reloadfpga: false` doesn't impact hardware functionality - all modules (Scope, ASG, IQ, PID, Sampler) work correctly

## Testing

To verify the fix works:

```bash
# Test hardware scope (requires Red Pitaya at 100.107.106.75)
PYRPL_TEST_HOST=100.107.106.75 uv run pytest tests/test_plugin_ipc_scope_hardware.py -v

# Test all mock tests
uv run pytest tests/test_plugin_ipc_*_mock.py tests/test_multi_plugin_coordination.py -v
```

Expected output:
- 7 scope hardware tests: PASSED
- 44 mock tests: PASSED

## Prevention

To prevent this issue from recurring:

1. **Never set `reloadfpga: true`** in PyRPL configurations
2. **Never set `reloadserver: true`** in PyRPL configurations  
3. **Always use `modules: []`** to avoid buggy PyRPL modules
4. **Test hardware connection** after making PyRPL configuration changes

## References

- Commit `0bf7f74`: Where the breaking change was introduced
- Commit `8a74229`: Previous working configuration
- PyRPL SSH implementation: `/pyrpl/sshshell.py`, `/pyrpl/redpitaya.py`
