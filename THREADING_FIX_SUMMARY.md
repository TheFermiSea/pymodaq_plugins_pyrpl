# Thread Recursion Fix Summary

**Date**: January 30, 2025  
**Issue**: Thread stack overflow when launching Scope plugin in PyMoDAQ dashboard  
**Status**: ✅ RESOLVED

## Problem

When launching a PyMoDAQ dashboard preset with the Scope plugin, a thread recursion error occurred:

```
Exception Type:    EXC_BAD_ACCESS (SIGBUS)
Exception Subtype: KERN_PROTECTION_FAILURE  
Exception Message: Thread stack size exceeded due to excessive recursion
Terminating in Thread 21 (QThread)
```

**Root Cause**: PyRPL was creating Qt objects (widgets, timers) in PyMoDAQ's worker threads, causing recursive Qt event processing and stack overflow.

## Solution

### One-Line Fix

Added `gui=False` parameter when instantiating PyRPL in `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py`:

```python
self._pyrpl = pyrpl.Pyrpl(
    config=self.config_name,
    hostname=self.hostname,
    port=self.port,
    timeout=self.connection_timeout,
    gui=False  # Prevents Qt widget creation in worker threads
)
```

### Why This Works

1. **`gui=False`**: Tells PyRPL to operate in headless mode without creating any Qt GUI components
2. **No Qt in Worker Threads**: PyRPL doesn't create timers or widgets that could recursively process events
3. **PyMoDAQ Provides GUI**: All user interface is handled by PyMoDAQ's native GUI
4. **Thread-Safe Hardware Access**: PyRPL still provides full hardware control, just without GUI overhead

## Changes Made

### File: `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py`

1. **Line ~500**: Added `gui=False` to `pyrpl.Pyrpl()` instantiation
2. **Lines 59-78**: Enhanced QTimer patching with recursion prevention
   - Added `_pymodaq_pyrpl_patched` flag to prevent re-patching
   - Added error handling for invalid timer values
   - Made patch defensive for edge cases

### Documentation Added

1. **`docs/THREADING_ARCHITECTURE.md`**: Complete technical explanation of the threading model
2. **`docs/README.md`**: Updated to reference threading documentation

## Verification

### Before Fix
- ❌ Scope plugin crashes with stack overflow
- ❌ Thread recursion in Qt event loop
- ❌ Dashboard presets with Scope unusable

### After Fix
- ✅ Scope plugin initializes cleanly
- ✅ No thread recursion errors
- ✅ All plugins work in PyMoDAQ dashboard
- ✅ Continuous data acquisition stable

## What NOT to Use

These workarounds are **NOT NEEDED** and should **NOT** be used:

1. **`pymodaq_qasync_launcher.py`**: Special launcher (adds complexity, not needed with `gui=False`)
2. **`DAQ_1DViewer_PyRPL_Scope_IPC`**: Separate process version (adds overhead, not needed with `gui=False`)
3. **Removing QTimer patches**: Patches are now safe and provide defense-in-depth

These may be removed or marked experimental in future versions.

## Testing

```bash
# Syntax check
python3 -m py_compile src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py

# Unit tests (no hardware needed)
pytest tests/ -k "not hardware"

# Hardware tests (requires Red Pitaya)
export PYRPL_TEST_HOST=100.107.106.75
pytest tests/ -m hardware -v

# Manual verification
# 1. Launch PyMoDAQ dashboard
# 2. Load a preset with Scope plugin
# 3. Verify no crashes, clean initialization
# 4. Start data acquisition
# 5. Verify continuous operation without errors
```

## Production Readiness

This solution is **production-ready** for distribution:

✅ **Minimal Changes**: One parameter addition, defensive patching improvements  
✅ **No New Dependencies**: Uses existing PyRPL feature (`gui=False`)  
✅ **PyMoDAQ-Native**: Works within PyMoDAQ's standard threading model  
✅ **No User Impact**: Plugin users see no difference, just reliability  
✅ **Well Documented**: Complete technical documentation for maintainers  
✅ **Tested**: Verified with real hardware and automated tests

## References

- Threading Architecture: `docs/THREADING_ARCHITECTURE.md`
- PyRPL Documentation: https://pyrpl.readthedocs.io/
- PyMoDAQ Threading: https://pymodaq.readthedocs.io/en/stable/developer_folder/dev_basics.html

## Key Insight

**When integrating a Qt-based library into a multi-threaded Qt application, disable the library's GUI components to prevent Qt object creation in worker threads.**

This is a general pattern applicable beyond PyRPL/PyMoDAQ integration.
