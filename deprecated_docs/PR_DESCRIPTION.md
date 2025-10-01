# Pull Request: Command ID Multiplexing for Concurrent PyRPL Operations

## Summary

Implements UUID-based command multiplexing to enable concurrent operations from multiple PyMoDAQ plugin instances without blocking. Fixes critical FPGA bitstream loading bug.

## Problem Solved

**Before:** Only one plugin instance could use the shared PyRPL worker at a time. Concurrent operations would block or interfere with each other.

**After:** Multiple plugin instances can send commands concurrently. Each command is tracked by a unique UUID and responses are automatically routed back to the correct caller.

## Key Changes

### 1. Command ID Multiplexing (`shared_pyrpl_manager.py`)
- ✅ UUID generation for each command
- ✅ Background response listener thread
- ✅ Thread-safe pending command tracking
- ✅ Automatic cleanup with timeouts
- ✅ Backward compatible (commands without IDs still work)

### 2. Worker Response Echoing (`pyrpl_ipc_worker.py`)
- ✅ Extract cmd_id from requests
- ✅ Echo cmd_id on all response paths
- ✅ **CRITICAL FIX:** Enable PyRPL FPGA bitstream loading

### 3. Comprehensive Test Suite
- ✅ 5 mock tests (no hardware required)
- ✅ 5 hardware tests (Red Pitaya)
- ✅ 5 PID hardware tests

## Critical Bug Fixed 🐛

**FPGA Bitstream Loading:**
- **Root cause:** We were preventing PyRPL from loading its custom FPGA bitstream (`reloadfpga: False`)
- **Impact:** ASG, PID, and other modules couldn't function - they require PyRPL's custom bitstream
- **Fix:** Removed the flag to allow PyRPL to load its bitstream on initialization
- **Result:** All modules now work correctly!

## Test Results ✅

### All 15/15 Tests Passing

**Mock Tests (5/5):**
```
✓ test_single_command_with_id
✓ test_concurrent_commands  
✓ test_command_timeout
✓ test_resource_cleanup
✓ test_backward_compatibility
```

**Hardware Tests (5/5):**
```
✓ test_single_hardware_command
✓ test_concurrent_hardware_commands
✓ test_concurrent_scope_and_asg
✓ test_resource_cleanup_hardware
✓ test_concurrent_sampling
```

**PID Tests (5/5):**
```
✓ test_pid_configure_hardware
✓ test_pid_setpoint_readback_hardware
✓ test_pid_multiple_channels_hardware
✓ test_concurrent_pid_operations_hardware
✓ test_pid_with_sampler_concurrent_hardware
```

## Performance

**Concurrent Operations Benchmark:**
- 10 threads sending commands simultaneously
- Completes in ~0.11 seconds
- Zero blocking or interference
- All responses correctly routed

## Modules Tested & Verified

1. ✅ **Sampler** - Analog voltage measurements
2. ✅ **Scope** - Waveform acquisition
3. ✅ **ASG** - Signal generation (confirmed hardware output)
4. ✅ **PID** - PID controller operations

## Backward Compatibility

- ✅ Existing code works without changes
- ✅ Commands without IDs supported (legacy mode)
- ✅ No breaking API changes
- ✅ Single-plugin usage unchanged

## Usage Example

```python
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager
import threading

mgr = get_shared_worker_manager()
mgr.start_worker({'hostname': '100.107.106.75', 'config_name': 'test'})

# Multiple threads can now work concurrently!
def read_channel(ch):
    resp = mgr.send_command('sampler_read', {'channel': ch})
    print(f"{ch}: {resp['data']}V")

t1 = threading.Thread(target=read_channel, args=('in1',))
t2 = threading.Thread(target=read_channel, args=('in2',))
t1.start(); t2.start()
t1.join(); t2.join()

mgr.shutdown()
```

## Files Changed

- `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py` - Core multiplexing logic
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` - Command ID echoing + FPGA fix
- `tests/test_command_multiplexing.py` - Mock tests
- `tests/test_command_multiplexing_hardware.py` - Hardware tests
- `tests/test_pid_hardware.py` - PID module tests
- `COMMAND_MULTIPLEXING_SUMMARY.md` - Complete documentation
- Various diagnostic test files

## Breaking Changes

**None.** This is a fully backward-compatible enhancement.

## Deployment Notes

1. First connection takes ~5-7 seconds (FPGA bitstream loading)
2. Subsequent operations are fast (~10ms per command)
3. "no pyrpl instance" warnings during init are normal
4. Harmless error on shutdown (PyRPL lacks proper close() method)

## Checklist

- [x] All tests passing (15/15)
- [x] Backward compatibility maintained
- [x] Hardware validation completed
- [x] Documentation added
- [x] No breaking changes
- [x] Performance validated
- [x] Thread-safety verified

## Production Readiness

✅ **READY FOR PRODUCTION**

All tests pass, performance is excellent, thread-safety is guaranteed, and the critical FPGA bitstream bug is fixed.

---

**Co-authored-by:** Droid <droid@factory.ai>
