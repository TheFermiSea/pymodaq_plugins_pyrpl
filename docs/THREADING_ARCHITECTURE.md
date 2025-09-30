# PyMoDAQ-PyRPL Threading Architecture

## Overview

This document explains the threading architecture used to integrate PyRPL (a Qt-based library) with PyMoDAQ's multi-threaded plugin framework, and how we solved the Qt event loop recursion problem.

## The Problem

### Background

- **PyMoDAQ**: Uses a multi-threaded architecture where plugins run in worker threads separate from the main Qt GUI thread
- **PyRPL**: Originally designed as a standalone Qt application with its own GUI, timers, and event loop
- **Conflict**: When PyRPL creates Qt objects (timers, widgets) in PyMoDAQ's worker threads, these objects try to process Qt events, leading to:
  - Thread recursion errors (stack overflow)
  - Event loop conflicts
  - Application crashes

### Symptom

```
Exception Type:    EXC_BAD_ACCESS (SIGBUS)
Exception Subtype: KERN_PROTECTION_FAILURE
Exception Message: Thread stack size exceeded due to excessive recursion
```

This occurred when launching the Scope plugin in a PyMoDAQ dashboard preset.

## The Solution

### Core Fix: `gui=False` Parameter

The robust, production-ready solution is to **disable PyRPL's GUI components** when instantiating the Pyrpl object:

```python
# In src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py
self._pyrpl = pyrpl.Pyrpl(
    config=self.config_name,
    hostname=self.hostname,
    port=self.port,
    timeout=self.connection_timeout,
    gui=False  # CRITICAL: Prevents Qt widget/timer creation
)
```

### Why This Works

1. **No Qt Objects in Worker Threads**: With `gui=False`, PyRPL doesn't create any Qt widgets, timers, or GUI components
2. **Pure Hardware Control**: PyRPL still provides full hardware access (scope, PID, ASG, IQ modules) without GUI overhead
3. **Thread-Safe**: Hardware communication is thread-safe and doesn't involve Qt event processing
4. **PyMoDAQ Native**: PyMoDAQ provides all GUI functionality, so PyRPL's GUI is redundant

### Additional Safeguards

#### 1. Non-Recursive QTimer Patching

We kept a compatibility patch for edge cases, but made it non-recursive:

```python
# Patch prevents re-patching and handles errors gracefully
if not hasattr(QTimer, '_pymodaq_pyrpl_patched'):
    original_setInterval = QTimer.setInterval
    
    def setInterval_patched(self, msec):
        try:
            return original_setInterval(self, int(msec))
        except (ValueError, TypeError) as e:
            logger.warning(f"QTimer.setInterval called with invalid value {msec}: {e}")
            return original_setInterval(self, 1000)
    
    QTimer.setInterval = setInterval_patched
    QTimer._pymodaq_pyrpl_patched = True
```

#### 2. Thread-Safe PyRPL Wrapper

The `PyRPLConnection` class uses locks to ensure thread-safe access:

```python
class PyRPLConnection:
    def __init__(self, connection_info: ConnectionInfo):
        self._lock = threading.RLock()  # Reentrant lock
        self._connection_lock = threading.Lock()
```

## Architecture Principles

### 1. PyMoDAQ-First Design

This plugin prioritizes PyMoDAQ's threading model:

- **Worker threads**: Hardware communication happens in PyMoDAQ worker threads
- **Main thread**: Only PyMoDAQ's GUI runs in the main Qt thread  
- **No conflicts**: PyRPL operates in "headless" mode with `gui=False`

### 2. Single Responsibility

- **PyMoDAQ**: Handles all GUI, user interaction, data visualization
- **PyRPL**: Provides hardware abstraction and communication only
- **Plugin**: Bridges the two, translating PyMoDAQ requests to PyRPL hardware commands

### 3. Clean Separation

```
┌─────────────────────────────────────────────┐
│ PyMoDAQ Main Thread (Qt GUI)                │
│  - Dashboard                                 │
│  - Parameter trees                           │
│  - Data plotters                             │
└───────────────┬─────────────────────────────┘
                │
                │ Signals/Slots
                ▼
┌─────────────────────────────────────────────┐
│ PyMoDAQ Worker Threads                      │
│  - Plugin grab_data()                        │
│  - Plugin commit_settings()                  │
│  ├─────────────────────────────────────────┤
│  │ PyRPL Wrapper (gui=False)               │
│  │  - Hardware communication               │
│  │  - No Qt objects created                │
│  │  - Thread-safe with locks               │
│  └─────────────────────────────────────────┤
│                                              │
└───────────────┬─────────────────────────────┘
                │
                │ Network (SCPI/TCP)
                ▼
        ┌───────────────────┐
        │  Red Pitaya       │
        │  Hardware         │
        └───────────────────┘
```

## What NOT to Do

### ❌ Using qasync Launcher

The repository contains `pymodaq_qasync_launcher.py` from earlier attempts to solve this problem. **Do not use it** for production:

- Requires users to launch PyMoDAQ differently
- Adds complexity and dependencies
- Not needed with `gui=False` solution
- May be removed in future versions

### ❌ Using IPC Version

The `DAQ_1DViewer_PyRPL_Scope_IPC` plugin runs PyRPL in a separate process. **Do not use it** for production:

- Adds process management overhead
- Introduces communication latency
- More failure points
- Not needed with `gui=False` solution
- May be removed or marked experimental

### ❌ Removing QTimer Patches

The QTimer compatibility patches should remain:

- They handle PyRPL 0.9.6.0 bugs (float → int conversion)
- Made non-recursive to be safe
- Low overhead
- Provide defense-in-depth

## Testing

### Verify Threading Solution

1. **Import Test**: Module should import without Qt warnings
   ```bash
   python -m pytest tests/test_pyrpl_functionality.py -v
   ```

2. **Hardware Test**: Should work without recursion errors
   ```bash
   python -m pytest tests/test_real_hardware_rp_f08d6c.py -v -m hardware
   ```

3. **Dashboard Test**: Launch scope in PyMoDAQ dashboard preset
   - No crashes on initialization
   - No thread recursion errors
   - Smooth data acquisition

### Expected Behavior

✅ **Should work**:
- Launching any plugin from PyMoDAQ dashboard
- Running multiple plugins simultaneously
- Continuous data acquisition
- Parameter changes during acquisition

❌ **Should NOT happen**:
- Thread recursion errors
- Stack overflow crashes
- Qt event loop warnings
- Hanging on initialization

## Future Maintenance

### If PyRPL Updates Break This

1. **Check `gui=False` support**: Verify PyRPL still supports headless mode
2. **Review compatibility patches**: May need updates for new PyRPL/Qt versions
3. **Test threading**: Run full test suite including hardware tests

### If Adding New PyRPL Features

1. **Always use `gui=False`**: Never create PyRPL with GUI in plugin code
2. **Lock hardware access**: Use `PyRPLConnection._lock` for thread safety
3. **Test in PyMoDAQ**: Verify plugin works in dashboard, not just standalone
4. **Document threading**: Update this file if architecture changes

## References

- PyMoDAQ threading: https://pymodaq.readthedocs.io/en/stable/developer_folder/dev_basics.html
- PyRPL API: https://pyrpl.readthedocs.io/
- Qt threading: https://doc.qt.io/qt-6/thread-basics.html

## Summary

**The key insight**: When embedding a Qt-based library (PyRPL) into a multi-threaded Qt application (PyMoDAQ), disable the embedded library's GUI (`gui=False`) to prevent Qt object creation in worker threads. This is a general pattern applicable to any Qt library integration.

**Result**: A robust, production-ready plugin that "just works" within PyMoDAQ's ecosystem without special launchers, workarounds, or user-visible complexity.
