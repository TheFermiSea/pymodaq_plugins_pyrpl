# Command ID Multiplexing Implementation - Complete Summary

## Overview

Implemented UUID-based command multiplexing for the PyMoDAQ-PyRPL plugin to enable concurrent operations from multiple plugin instances without blocking. This addresses the architectural requirement documented in `ARCHITECTURE_REVIEW.md`.

## Problem Solved

**Before:** Only one PyMoDAQ plugin instance could communicate with the shared PyRPL worker at a time. Commands from multiple plugins would block or interfere with each other.

**After:** Multiple plugin instances can send commands concurrently. Each command gets a unique ID, and responses are automatically routed back to the correct caller.

## Implementation Details

### Core Components

1. **UUID-based Command IDs**
   - Each command gets a unique UUID
   - Backward compatible (commands without IDs still work)
   - Thread-safe command tracking

2. **Background Response Listener Thread**
   - Continuously listens for responses from worker
   - Routes responses to correct waiting threads
   - Automatic cleanup of completed commands

3. **Thread-Safe Response Tracking**
   - Uses `threading.Event` for efficient waiting
   - Timeout support per command
   - Proper cleanup on timeout or completion

### Key Files Modified

- `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`
  - Added UUID generation for commands
  - Added background response listener thread
  - Added pending command tracking with Events
  - Added automatic cleanup mechanisms

- `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`
  - Extract cmd_id from requests
  - Echo cmd_id on all response paths
  - **CRITICAL FIX:** Enabled PyRPL FPGA bitstream loading

### Critical Bug Fixed

**FPGA Bitstream Loading Issue:**
- Root cause: We were setting `reloadfpga: False` which prevented PyRPL from loading its custom FPGA bitstream
- PyRPL requires its own FPGA bitstream for ASG, PID, scope, and other modules to function
- Red Pitaya web-apps use the standard bitstream, which is why they worked
- Fix: Removed `reloadfpga: False` to allow PyRPL to load its bitstream
- Result: All modules now work correctly!

## Test Results

### Mock Tests (no hardware): 5/5 PASS ✓
```
test_single_command_with_id ..................... PASSED
test_concurrent_commands ........................ PASSED  
test_command_timeout ............................ PASSED
test_resource_cleanup ........................... PASSED
test_backward_compatibility ..................... PASSED
```

### Hardware Tests (Red Pitaya): 5/5 PASS ✓
```
test_single_hardware_command .................... PASSED
test_concurrent_hardware_commands ............... PASSED
test_concurrent_scope_and_asg ................... PASSED
test_resource_cleanup_hardware .................. PASSED
test_concurrent_sampling ........................ PASSED
```

### PID Hardware Tests: 5/5 PASS ✓
```
test_pid_configure_hardware ..................... PASSED
test_pid_setpoint_readback_hardware ............. PASSED
test_pid_multiple_channels_hardware ............. PASSED
test_concurrent_pid_operations_hardware ......... PASSED
test_pid_with_sampler_concurrent_hardware ....... PASSED
```

**Total: 15/15 tests passing**

## Performance

**Concurrent Operations Benchmark:**
- 10 threads each sending commands concurrently
- Total time: ~0.11 seconds
- All commands complete without blocking
- All responses correctly routed to callers

## Modules Tested & Working

1. ✅ **Sampler** - Voltage measurements from analog inputs
2. ✅ **Scope** - Oscilloscope waveform acquisition
3. ✅ **ASG** - Arbitrary signal generator (confirmed outputting)
4. ✅ **PID** - PID controller configuration and operation

## Backward Compatibility

The implementation is fully backward compatible:
- Commands without IDs still work (for legacy code)
- Existing single-plugin usage unchanged
- No breaking changes to public API

## Usage Example

```python
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Get shared manager (singleton)
mgr = get_shared_worker_manager()

# Start worker
config = {
    'hostname': '100.107.106.75',
    'config_name': 'my_config',
    'mock_mode': False
}
mgr.start_worker(config)

# Send commands concurrently from multiple threads
import threading

def read_voltage(channel):
    response = mgr.send_command('sampler_read', {'channel': channel}, timeout=5.0)
    print(f"Channel {channel}: {response['data']} V")

# These run concurrently without blocking!
t1 = threading.Thread(target=read_voltage, args=('in1',))
t2 = threading.Thread(target=read_voltage, args=('in2',))
t1.start()
t2.start()
t1.join()
t2.join()

# Cleanup
mgr.shutdown()
```

## Known Limitations

1. **FPGA Bitstream Loading Time:** First connection takes ~5-7 seconds while PyRPL loads its FPGA bitstream
2. **PyRPL Close Error:** PyRPL doesn't have a proper `.close()` method, so we see a harmless error on shutdown
3. **"no pyrpl instance" Warnings:** Normal warnings during FPGA loading phase

## Production Readiness

✅ **READY FOR PRODUCTION**

All tests pass, performance is excellent, and the implementation is thread-safe with proper cleanup. The critical FPGA bitstream loading bug has been identified and fixed.

## Deployment Notes

1. Ensure Red Pitaya is accessible at configured hostname
2. First connection will take longer (~5-7s) due to FPGA bitstream loading
3. Subsequent operations are fast (~0.01s per command)
4. Monitor logs for "PyRPL initialized successfully" message
5. "no pyrpl instance" warnings during init are normal

## Future Enhancements (Optional)

1. Add caching of FPGA bitstream to speed up reconnection
2. Implement proper PyRPL cleanup to avoid close() error
3. Add metrics/logging for command latency monitoring
4. Consider connection pooling for multiple Red Pitaya devices

## Credits

Implemented following architectural guidance from `ARCHITECTURE_REVIEW.md`

Co-authored-by: Droid <droid@factory.ai>
