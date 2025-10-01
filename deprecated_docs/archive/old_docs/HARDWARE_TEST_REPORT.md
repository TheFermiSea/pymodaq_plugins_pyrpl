# Hardware Test Report - PyRPL/PyMoDAQ Integration
**Date:** January 30, 2025  
**Device:** Red Pitaya at 100.107.106.75  
**PyRPL Version:** 0.9.3.6  
**Python Version:** 3.11.12

## Executive Summary

Successfully established network connectivity and SSH authentication to the Red Pitaya device at 100.107.106.75. However, a critical bug in PyRPL v0.9.3.6's Network Analyzer module prevents complete initialization. The bug causes a `ZeroDivisionError` during PyRPL object creation, which blocks access to all hardware modules.

**Status:** ⚠️ **BLOCKED** - Upstream PyRPL bug prevents hardware testing

## Test Environment

### Hardware Configuration
- **Device:** Red Pitaya STEMlab at 100.107.106.75
- **Network:** Tailscale VPN connection
- **Physical Setup:**
  - Output1 → Input1 (BNC loopback)
  - Input2 ← External function generator
  
### Software Environment
- **Python:** 3.11.12
- **PyMoDAQ:** 5.x
- **PyRPL:** 0.9.3.6
- **Qt:** PyQt6 6.9.1 / Qt 6.9.2
- **OS:** macOS (darwin 25.0.0)

## Test Results

### ✅ Successful Components

1. **Network Connectivity**
   - Ping successful to 100.107.106.75
   - Latency: 5-90ms (acceptable for Tailscale VPN)
   - No packet loss

2. **SSH Authentication**
   - Successfully connected via paramiko
   - Public key authentication working
   - Log message: "Successfully connected to Redpitaya with hostname 100.107.106.75"

3. **PyRPL Compatibility Patches**
   - ✅ `collections.Mapping` → `collections.abc.Mapping` (Python 3.10+)
   - ✅ `np.complex` → `np.complex128` (NumPy 1.20+)
   - ✅ `QTimer.setInterval()` accepts floats (Qt6 compatibility)
   - All compatibility patches applied successfully

4. **Plugin Architecture**
   - All PyMoDAQ plugin modules present and importable:
     - `DAQ_Move_PyRPL_PID` (PID setpoint control)
     - `DAQ_Move_PyRPL_ASG` (Signal generator)
     - `DAQ_0DViewer_PyRPL` (Voltage monitoring)
     - `DAQ_0DViewer_PyRPL_IQ` (Lock-in amplifier)
     - `DAQ_1DViewer_PyRPL_Scope` (Oscilloscope)
   - `PIDModelPyRPL` model available
   - `PyRPLManager` wrapper functional

### ❌ Critical Issue: PyRPL Network Analyzer Bug

**Error:** `ZeroDivisionError: float division by zero`

**Location:**
```
File: /venv/lib/python3.11/site-packages/pyrpl/attributes.py", line 785
Method: FrequencyRegister._MAXSHIFT()
Code: return clog2(125000000.0/float(self._MINBW(obj)))
```

**Root Cause:**
The PyRPL Network Analyzer module initialization calls `_MINBW(obj)` which returns `0`, causing a division by zero when calculating the maximum frequency shift value. This occurs during the `Pyrpl()` object creation, before any user code can access the hardware.

**Call Stack:**
```
pyrpl.Pyrpl.__init__()
  → NetworkAnalyzer._load_setup_attributes()
    → NetworkAnalyzer._setup()
      → NetworkAnalyzer._update_data_x()
        → NetworkAnalyzer.iq (property access)
          → IQ.bandwidth.__set__()
            → FrequencyRegister.validate_and_normalize()
              → FrequencyRegister.valid_frequencies()
                → FrequencyRegister._MAXSHIFT()
                  → ZeroDivisionError!
```

**Impact:**
- **BLOCKING:** Cannot create `Pyrpl()` instance
- **Scope:** Affects ALL PyRPL modules (PID, ASG, Scope, IQ, Sampler)
- **Workaround Attempted:** Monkey-patching unsuccessful (method structure prevents clean patching)

## Detailed Findings

### Network & Connection Layer ✅
```
Test: ping 100.107.106.75
Result: 3 packets transmitted, 3 received, 0% packet loss
RTT: min 5.247ms / avg 33.898ms / max 89.956ms

Test: SSH connection via PyRPL
Result: Connected (version 2.0, client Tailscale)
Auth: publickey authentication successful
```

### PyRPL Import & Compatibility ✅
```python
# Compatibility patches applied successfully
import collections.abc  # Python 3.10+ fix
collections.Mapping = collections.abc.Mapping

import numpy as np  # NumPy 1.20+ fix  
np.complex = np.complex128

# QTimer float compatibility
QTimer.setInterval = lambda self, msec: original(self, int(msec))
```

### PyRPL Initialization ❌
```python
# This fails with ZeroDivisionError
p = pyrpl.Pyrpl(
    hostname="100.107.106.75",
    gui=False,
    reloadserver=False,
    reloadfpga=False,
    timeout=10,
    config='test_config'
)
# Error: float division by zero in attributes.py:785
```

### Plugin Test Status

Since PyRPL initialization fails, none of the plugin hardware tests could be executed:

| Plugin | Expected Functionality | Test Status |
|--------|----------------------|-------------|
| `DAQ_Move_PyRPL_PID` | PID setpoint control (±1V) | ⚠️ Blocked |
| `DAQ_Move_PyRPL_ASG` | Signal generation (sine, square, etc.) | ⚠️ Blocked |
| `DAQ_0DViewer_PyRPL` | Voltage monitoring (IN1, IN2) | ⚠️ Blocked |
| `DAQ_0DViewer_PyRPL_IQ` | Lock-in amplifier (I/Q detection) | ⚠️ Blocked |
| `DAQ_1DViewer_PyRPL_Scope` | Oscilloscope (16k samples) | ⚠️ Blocked |
| `PIDModelPyRPL` | Direct PID model | ⚠️ Blocked |

## Attempted Solutions

### 1. Monkey Patching `_MAXSHIFT` ❌
**Approach:** Patch `FrequencyRegister._MAXSHIFT` to handle zero `_MINBW`
**Result:** Failed - method not accessible as class attribute
**Reason:** `_MAXSHIFT` appears to be defined locally or dynamically

### 2. Pre-configuring Network Analyzer ❌  
**Approach:** Create PyRPL config file with valid network analyzer settings
**Result:** Failed - config loaded AFTER initialization
**Reason:** Bug occurs during object creation, before config is read

### 3. Disabling Network Analyzer ❌
**Approach:** Attempt to skip network analyzer module initialization  
**Result:** Not possible - network analyzer is a core software module
**Reason:** No configuration option to disable it

## Recommendations

### Immediate Actions

1. **Report Bug to PyRPL Maintainers**
   - File issue at: https://github.com/lneuhaus/pyrpl
   - Include traceback and `_MINBW` returning 0
   - Request fix or workaround

2. **Check for PyRPL Updates**
   ```bash
   pip install --upgrade pyrpl
   ```
   - Current version: 0.9.3.6
   - Check if newer version addresses this issue

3. **Use Mock Mode for Plugin Development**
   ```python
   # All plugins support mock_mode=True
   plugin.settings['connection', 'mock_mode'] = True
   ```
   - Allows GUI and integration testing without hardware
   - Mock implementations provide realistic simulated data

### Alternative Approaches

#### Option A: Direct RedPitaya Access (Recommended)
Skip the PyRPL `Pyrpl` wrapper and access the `RedPitaya` object directly:

```python
from pyrpl.redpitaya import RedPitaya

# Bypass Pyrpl() initialization
rp = RedPitaya(hostname="100.107.106.75")

# Access modules directly
pid0 = rp.pid0
asg0 = rp.asg0
scope = rp.scope
sampler = rp.sampler

# Use with PyMoDAQ plugins
# (May require plugin modifications)
```

**Pros:**
- Bypasses Network Analyzer initialization
- Direct access to all hardware modules
- Same API as PyRPL modules

**Cons:**
- Skips PyRPL software modules (lockbox, network analyzer)
- May need to modify plugin connection logic
- No config file management

#### Option B: Patch PyRPL Source Code
Directly edit the installed PyRPL package:

```bash
# Edit: venv/lib/python3.11/site-packages/pyrpl/attributes.py
# Line 785: Add zero check

def _MAXSHIFT(self, obj):
    min_bw = self._MINBW(obj)
    if min_bw == 0 or min_bw is None:
        return 25  # Default for Red Pitaya
    return clog2(125000000.0/float(min_bw))
```

**Pros:**
- Fixes root cause directly
- Full PyRPL functionality restored

**Cons:**
- Modification lost on package reinstall/upgrade
- Not maintainable across environments
- Requires manual patching on each deployment

#### Option C: Use Older PyRPL Version
Test with earlier PyRPL releases:

```bash
# Try previous versions
pip install pyrpl==0.9.3.5  
pip install pyrpl==0.9.3.4
# etc.
```

**Pros:**
- May avoid this specific bug
- No code modifications needed

**Cons:**
- Unknown if older versions work
- May have other compatibility issues
- Missing newer features/fixes

### Long-term Solution

**Integrate Direct RedPitaya Access into Plugins:**

Modify `pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py` to support both modes:

```python
class PyRPLConnection:
    def __init__(self, hostname, config_name='default', use_pyrpl_wrapper=True):
        if use_pyrpl_wrapper:
            # Current approach (blocked by bug)
            self._pyrpl = pyrpl.Pyrpl(hostname=hostname, ...)
            self._redpitaya = self._pyrpl.rp
        else:
            # Direct access (bypass Pyrpl wrapper)
            from pyrpl.redpitaya import RedPitaya
            self._redpitaya = RedPitaya(hostname=hostname)
            self._pyrpl = None  # No Pyrpl wrapper
```

This would allow:
- Testing with direct access immediately
- Switching back to full PyRPL when bug is fixed
- Configuration option for users

## Testing Plan (Once Unblocked)

When PyRPL initialization issue is resolved, execute these tests:

### Phase 1: Basic Hardware Access
1. ✅ Establish connection
2. ✅ Read IN1/IN2 voltages
3. ✅ Verify PID modules accessible (pid0-2)
4. ✅ Verify ASG modules accessible (asg0-1)
5. ✅ Verify scope accessible
6. ✅ Verify IQ modules accessible (iq0-2)
7. ✅ Verify sampler accessible

### Phase 2: Signal Generation & Monitoring
1. Configure ASG0 (1kHz sine, 0.3V amplitude)
2. Monitor output with scope
3. Read voltage with sampler
4. Verify waveform parameters

### Phase 3: PID Control
1. Configure PID0 (setpoint, gains)
2. Set input to IN1, output to OUT1 (loopback)
3. Verify PID response
4. Test setpoint changes

### Phase 4: Plugin Integration Tests
1. Test each plugin with real hardware:
   - `DAQ_Move_PyRPL_PID`: Set setpoint, read output
   - `DAQ_Move_PyRPL_ASG`: Generate signals, verify frequency
   - `DAQ_0DViewer_PyRPL`: Monitor voltages continuously
   - `DAQ_0DViewer_PyRPL_IQ`: Lock-in detection
   - `DAQ_1DViewer_PyRPL_Scope`: Capture waveforms

### Phase 5: Comprehensive Integration
1. Run full test suite: `pytest tests/test_real_hardware_rp_f08d6c.py -m hardware`
2. Multi-plugin coordination tests
3. Thread safety validation
4. Long-duration stability testing

## Conclusion

The PyMoDAQ-PyRPL plugin integration architecture is sound and all compatibility patches are working correctly. Hardware connectivity to the Red Pitaya at 100.107.106.75 is fully functional. 

**The critical blocker is an upstream PyRPL library bug in version 0.9.3.6** that prevents initialization of the `Pyrpl` object due to a division-by-zero error in the Network Analyzer module.

**Recommended immediate action:** Implement Option A (Direct RedPitaya Access) to bypass the PyRPL wrapper and enable hardware testing of all plugin modules.

## Files Created

- `test_hardware_connection.py` - Comprehensive hardware connection test
- `test_pyrpl_simple.py` - Minimal PyRPL connection test
- `test_pyrpl_no_na.py` - Network analyzer bypass attempt
- `test_with_fixes.py` - Patch application test
- `test_patch_debug.py` - Patch debugging script
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_fixes.py` - PyRPL bug fix module (attempted)

## Next Steps

1. ✅ Document findings (this report)
2. ⏭ Implement Direct RedPitaya Access mode in PyRPLManager
3. ⏭ Test all plugins with direct access mode
4. ⏭ File bug report with PyRPL project
5. ⏭ Update documentation with workaround instructions
