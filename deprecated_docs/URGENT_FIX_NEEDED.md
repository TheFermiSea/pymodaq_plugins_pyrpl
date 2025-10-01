# URGENT: IPC Plugins Not Using SharedPyRPLManager!

## Critical Issue Discovered

The IPC plugins (`PyRPL_Scope_IPC`, `PyRPL_ASG_IPC`, etc.) are **NOT** using the `SharedPyRPLManager` singleton! 

### Current Broken Behavior

Each plugin creates its own separate `Process`:
```python
# daq_1Dviewer_PyRPL_Scope_IPC.py line ~170
self.worker_process = Process(
    target=pyrpl_worker_main,
    args=(self.command_queue, self.response_queue, config),
    daemon=True
)
self.worker_process.start()
```

This means:
- **Multiple PyRPL worker processes** are created
- Each tries to connect to the same Red Pitaya
- They share the same `pymodaq.yml` config file
- **Monitor server crashes** due to concurrent access
- Results in "NoneType object is not subscriptable" errors

### What Should Happen

ALL IPC plugins should use the `SharedPyRPLManager`:
```python
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# In _start_worker():
self.manager = get_shared_worker_manager()
queues = self.manager.start_worker(config)  # Returns SAME worker for all plugins
self.command_queue, self.response_queue = queues
```

This ensures:
- **Only ONE PyRPL worker process** across all plugins
- **ONE monitor server connection** shared by all
- **UUID-based command multiplexing** prevents cross-talk
- **No SSH/connection crashes**

### Impact

**HIGH SEVERITY** - Dashboard cannot use multiple plugins simultaneously

### Files That Need Fixing

1. `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_IPC.py`
2. `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/daq_0Dviewer_PyRPL_IQ_IPC.py`
3. `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_ASG_IPC.py`
4. `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_PID_IPC.py`

### Required Changes

For each IPC plugin file:

1. **Add import**:
   ```python
   from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager
   ```

2. **Replace `_start_worker()` method**:
   ```python
   def _start_worker(self) -> bool:
       try:
           # Use shared manager instead of creating own process
           self.manager = get_shared_worker_manager()
           
           config = {
               'hostname': self.settings['connection', 'rp_hostname'],
               'config_name': self.settings['connection', 'config_name'],
               'mock_mode': self.settings['dev', 'mock_mode']
           }
           
           # Start (or reuse) shared worker
           self.command_queue, self.response_queue = self.manager.start_worker(config)
           
           # Test connection
           response = self._send_command('ping', timeout=10.0)
           if response['status'] == 'ok':
               self.is_connected = True
               return True
           return False
       except Exception as e:
           logger.error(f"Failed to start worker: {e}")
           return False
   ```

3. **Update `close()` method**:
   ```python
   def close(self):
       # Don't shutdown shared worker - other plugins may still need it
       # Just clean up our own resources
       self.command_queue = None
       self.response_queue = None
       self.is_connected = False
       # Manager cleanup happens via atexit
   ```

4. **Remove** `self.worker_process` references (no longer needed)

### Temporary Workaround

Until fixed, users can only use ONE IPC plugin at a time, or use different config names for each plugin to avoid conflicts.

### Testing After Fix

```bash
# Should work without errors:
uv run dashboard  # Load preset with Scope + ASG
# Both should initialize successfully
# Scope continuous grab should work
# ASG frequency changes should work
# No "NoneType" or "wrong control sequence" errors
```

### Priority

**CRITICAL** - This breaks the core functionality of having multiple PyRPL plugins in PyMoDAQ Dashboard.
