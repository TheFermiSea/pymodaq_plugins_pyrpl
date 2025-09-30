# Query for Gemini: PyRPL-PyMoDAQ Qt Threading Integration

## Problem Statement

We are creating a PyMoDAQ plugin for PyRPL (Python Red Pitaya Lockbox) to control Red Pitaya hardware. Both frameworks are Qt-based, but we're experiencing fatal Qt metaobject recursion errors when PyRPL modules are accessed from PyMoDAQ worker threads.

### Error Symptom

```
Thread 22 Crashed:: QThread
Stack overflow due to excessive recursion in:
- qpycore_get_qmetaobject()
- qpycore_qobject_getattr()  
- trawl_hierarchy()

Over 431 levels of recursion through Qt's metaobject introspection system.
```

## Architectural Constraints

### PyMoDAQ Architecture
- **Threading Model**: Plugins run in worker threads (QThread), separate from main Qt GUI thread
- **Plugin Pattern**: Plugins inherit from `DAQ_Viewer_base` or `DAQ_Move_base`
- **Methods Called**: `ini_detector()`, `grab_data()`, `commit_settings()` - all run in worker threads
- **Communication**: Signal/slot mechanism to communicate with main GUI thread
- **Documentation**: https://pymodaq.readthedocs.io/

### PyRPL Architecture  
- **Design**: All hardware modules (Scope, PID, ASG, IQ) inherit from QObject
- **Event Loop**: Designed to run in main thread with its own Qt event loop
- **No Low-Level API**: No documented non-Qt API for direct FPGA/register access
- **gui Parameter**: Has `gui=False` option to disable GUI widgets, but modules remain QObjects
- **Documentation**: https://pyrpl.readthedocs.io/
- **Repository**: https://github.com/lneuhaus/pyrpl

## What We've Tried

### Attempt 1: Use `gui=False`
```python
self._pyrpl = pyrpl.Pyrpl(
    hostname=self.hostname,
    gui=False  # Disable GUI widgets
)
```
**Result**: Still crashes. Modules are still QObjects even without GUI.

### Attempt 2: Don't Cache QObjects
```python
# Instead of:
self._scope = self._pyrpl.rp.scope  # CRASHES

# We tried:
def get_scope():
    return self._pyrpl.rp.scope  # Still crashes
```
**Result**: Still crashes. Any access to QObject triggers introspection.

### Attempt 3: No Local Variables
```python
# Directly access without storing:
self._redpitaya.scope.trigger()
self._redpitaya.scope.curve()
```
**Result**: Still crashes. Even direct attribute access triggers Qt metaobject system.

## Core Issue

**Qt's metaobject system (`qpycore_get_qmetaobject`) recursively introspects QObject hierarchies when they're accessed from non-main threads.** Since:

1. PyMoDAQ worker threads try to access PyRPL modules
2. PyRPL modules are QObjects
3. Qt tries to build/inspect metaobject hierarchy
4. This triggers infinite recursion in `trawl_hierarchy()`

## What We've Discovered

### Investigation of PyRPL API (January 30, 2025)

We examined the PyRPL API documentation (https://pyrpl.readthedocs.io/en/latest/api.html) and found:

**PyRPL "Low-Level" API Reality:**
```python
# What PyRPL calls "low-level" API:
r = pyrpl.Pyrpl().redpitaya
r.scope.curve()        # Still a QObject method!
r.pid0.setup()         # Still a QObject method!
r.asg0.setup()         # Still a QObject method!
```

**Key Findings:**
1. **No true low-level API exists** - The "low-level" API is just direct access to the same QObject modules
2. **All modules are QObjects** - Every hardware module (scope, pid0-2, asg0-1, iq0-2, iir) inherits from QObject
3. **Custom protocol, not SCPI** - PyRPL uses a custom Python client-server protocol on port 2222, not standard SCPI
4. **Register access goes through QObjects** - All FPGA register reads/writes go through the QObject-based Python API
5. **~300µs per register operation** - As stated in docs, all hardware access has this overhead

**From API Documentation:**
> "With the last command, you have successfully retrieved a value from an FPGA register. This operation takes about 300 µs on my computer."

This confirms there is no direct register or SCPI access - everything goes through PyRPL's QObject wrapper.

### Red Pitaya Native SCPI API

We discovered Red Pitaya has its own native SCPI server (separate from PyRPL):
- **Documentation**: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/scpi.html
- **Command List**: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list.html
- **Protocol**: Standard SCPI over TCP sockets (thread-safe, no Qt dependencies)
- **Capabilities**: Oscilloscope, signal generation, data acquisition, GPIO control

**Limitation**: Red Pitaya's SCPI API does NOT include PyRPL's advanced FPGA features:
- PyRPL's custom PID controllers (3x FPGA-based)
- IQ demodulation modules (3x)
- IIR filters (16th order)
- Lock-in amplifiers
- Network analyzer functionality

### Architectural Analysis

**Why PyRPL Cannot Work in PyMoDAQ Worker Threads:**

1. **QObject Access from Non-Main Thread**: Any attribute access on a QObject from a non-main thread triggers Qt's metaobject introspection
2. **Metaobject Recursion**: `qpycore_get_qmetaobject()` recursively traverses the object hierarchy via `trawl_hierarchy()`
3. **Infinite Loop**: Something in PyRPL's QObject hierarchy causes this traversal to recurse infinitely
4. **Stack Overflow**: 431+ levels of recursion exhaust thread stack (16KB guard page exceeded)

**Even These Don't Work:**
```python
# All of these still crash with recursion:
scope = self._redpitaya.scope                    # Crashes on assignment
self._redpitaya.scope.trigger()                  # Crashes on attribute access
data = getattr(self._redpitaya, 'scope').curve() # Crashes on getattr
```

The problem is fundamental: **any Python access to a QObject attribute from a worker thread triggers Qt introspection**.

## Questions for Gemini

Given the above findings, please analyze both PyRPL and PyMoDAQ documentation and source code to answer:

### 1. PyRPL Architecture Deep Dive
**Given that ALL PyRPL modules are QObjects, is there ANY hidden/undocumented way to bypass them?**
- Can we access PyRPL's internal register communication layer directly?
- Does PyRPL expose any C/Cython bindings that avoid Qt?
- Can we monkey-patch or subclass PyRPL modules to remove QObject dependency?
- Is there a way to serialize/deserialize PyRPL commands without object access?

### 2. Alternative Architectures - Detailed Analysis Needed
**What is the most robust production-ready solution?**

**Option A: IPC with Separate Process**
- Run PyRPL in dedicated process with its own Qt event loop
- Communicate via multiprocessing.Connection, ZeroMQ, or similar
- Pro: Keeps all PyRPL functionality (PID, IQ, IIR, network analyzer)
- Con: Complexity, IPC overhead, process management
- Question: What IPC mechanism has lowest latency for ~1kHz control loops?

**Option B: Red Pitaya Native SCPI**
- Use Red Pitaya's built-in SCPI server directly (bypass PyRPL)
- Pro: Thread-safe, simple TCP sockets, no Qt dependencies
- Con: Loses PyRPL's advanced FPGA features (PID, IQ, IIR)
- Question: Can Red Pitaya SCPI API be extended with custom FPGA code?

**Option C: Hybrid Approach**
- Use SCPI for basic scope/ASG
- Use PyRPL via IPC for advanced features (PID, lockbox)
- Question: Is the complexity worth it?

**Option D: Qt Threading Patterns**
- Use QObject::moveToThread() to move PyRPL objects to worker thread?
- Use signals/slots with Qt::QueuedConnection exclusively?
- Question: Can this work or does PyRPL's architecture prevent it?

### 3. Qt Threading Patterns - Why Standard Patterns Don't Work
**We tried standard Qt threading patterns - why did they fail?**

**What we attempted:**
- `gui=False` - Prevents GUI widgets but modules remain QObjects
- No caching - Getting fresh reference each time still crashes
- No local variables - Direct inline access still crashes
- All attempts crash at `qpycore_get_qmetaobject()` during attribute access

**Questions:**
- Why does Qt's metaobject introspection trigger on simple attribute access?
- Is the recursion a bug in PyQt/SIP or something specific to PyRPL's QObject hierarchy?
- Can we set Qt thread affinity for PyRPL objects to worker thread before accessing?
- Would using PyQt5 instead of PyQt6 (or vice versa) make any difference?
- Is there a Qt flag or environment variable to disable metaobject introspection?

### 4. PyMoDAQ Best Practices
**How do other PyMoDAQ plugins handle Qt-based hardware libraries?**
- Do any plugins wrap Qt-based SDKs?
- Recommended patterns for thread-safe hardware access?

### 5. Feasibility Assessment and Recommendation
**What is the most practical solution for a production plugin?**

**Given our findings:**
- PyRPL has NO non-Qt API for hardware access
- Red Pitaya has SCPI API but lacks PyRPL's advanced features
- All attempts to use PyRPL QObjects from worker threads fail with recursion
- IPC approach adds significant complexity

**Critical Questions:**
1. **For basic oscilloscope/signal generation**: Is Red Pitaya SCPI sufficient for most users?
2. **For advanced features (PID, lock-in, network analyzer)**: Is IPC complexity justified?
3. **Architecture recommendation**: Should we provide TWO plugins:
   - Simple SCPI-based plugin (recommended for most users)
   - Advanced IPC-based PyRPL plugin (for users needing PID/IQ/IIR)
4. **Maintenance burden**: Which approach is most maintainable long-term?

**Specific Use Case:**
Our user needs oscilloscope functionality primarily. PID and advanced features are desirable but not critical. What would you recommend?

## Desired Outcome

Based on your analysis, please provide:

1. **Architecture Recommendation**: Which approach (SCPI, IPC, hybrid, or other) is most appropriate for production use?

2. **Implementation Guidance**: If recommending IPC:
   - Best IPC mechanism for <1ms latency control loops
   - Process management strategy
   - Error handling and recovery

3. **Feature Trade-off Analysis**: Clear comparison of what users gain/lose with each approach:
   - SCPI: Simple but limited features
   - IPC: Full PyRPL features but complex
   - Hybrid: Best of both but maintenance burden

4. **Qt Threading Verdict**: Is there ANY way to make PyRPL QObjects work in worker threads, or is this definitively impossible?

5. **Code Examples**: If you identify a viable solution, provide architectural pseudocode showing the key integration points

## Resources for Analysis

### Documentation URLs

**PyRPL Documentation and Repository:**
- **PyRPL Main Documentation**: https://pyrpl.readthedocs.io/en/latest/
- **PyRPL Full API**: https://pyrpl.readthedocs.io/en/latest/api.html
- **PyRPL Basics**: https://pyrpl.readthedocs.io/en/latest/basics.html
- **PyRPL GitHub Repository**: https://github.com/pyrpl-fpga/pyrpl.git
- **PyRPL Legacy Repository**: https://github.com/lneuhaus/pyrpl (may be outdated)

**PyMoDAQ Documentation and Repository:**
- **PyMoDAQ Main Documentation**: https://pymodaq.cnrs.fr/en/latest/
- **PyMoDAQ Plugin Development Guide**: https://pymodaq.cnrs.fr/en/latest/developer_folder/plugin_development.html
- **PyMoDAQ GitHub Repository**: https://github.com/PyMoDAQ/PyMoDAQ
- **PyMoDAQ Threading/Architecture**: https://pymodaq.cnrs.fr/en/latest/developer_folder/dev_basics.html

**Red Pitaya SCPI (Alternative Approach):**
- **Red Pitaya SCPI Documentation**: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/scpi.html
- **Red Pitaya Command List**: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list.html
- **Red Pitaya Examples**: https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/scpi_examples.html

### Code to Analyze
Repository: `/Users/briansquires/serena_projects/pymodaq_plugins_pyrpl`

**Current Implementation (crashes):**
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py` - PyRPL wrapper with QObject access
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope.py` - Scope plugin

**IPC Experiment (incomplete):**
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_IPC.py` - IPC approach

**Relevant PyRPL Source** (for your analysis):
- `pyrpl/hardware_modules/scope.py` - Scope QObject implementation
- `pyrpl/hardware_modules/pid.py` - PID QObject implementation  
- `pyrpl/redpitaya.py` - Main RedPitaya class
- `pyrpl/pyrpl.py` - Pyrpl main class with gui parameter

### Current Status Summary

**Works:** 
- PyRPL standalone (with gui=True or gui=False)
- PyMoDAQ plugins with non-Qt hardware libraries
- Red Pitaya SCPI commands from any thread

**Fails:**
- Any PyRPL QObject access from PyMoDAQ worker threads
- Crashes with 431+ level recursion in Qt metaobject system

**Plugin Version:** 0.1.dev175 (latest commit includes all attempted fixes)

---

## Request for Gemini

Please provide a comprehensive analysis addressing all questions above, with specific emphasis on:

1. **Practical recommendation** for production-ready solution
2. **Concrete implementation steps** for the recommended approach
3. **Performance implications** (latency, throughput) of each option
4. **Long-term maintenance** considerations

Thank you for your detailed analysis!
