# Red Pitaya Plugin Testing Guide

This guide provides comprehensive testing procedures for the new PyRPL extensions for PyMoDAQ.

## Prerequisites

### Hardware
- Red Pitaya STEMlab connected and accessible at IP: `100.107.106.75`
- Network connectivity to Red Pitaya
- Red Pitaya powered on and running firmware

### Software
- Python environment with PyMoDAQ and dependencies installed
- StemLab library installed: `pip install git+https://github.com/ograsdijk/StemLab.git`
- PyMoDAQ dashboard accessible

### Verify Installation

```bash
# Activate your virtual environment
source venv_hardware_test/bin/activate  # or your venv

# Verify dependencies
python -c "import pymodaq; import stemlab; import numpy; print('All dependencies OK')"

# Run structure validation
python test_plugin_structure.py
```

Expected output: `✓ ALL TESTS PASSED!`

## Test Level 1: Automated Hardware Tests

### Running Automated Tests

```bash
# Ensure Red Pitaya is connected at 100.107.106.75
# Run comprehensive hardware tests
python test_hardware_plugins.py
```

### What Gets Tested

1. **PyrplWorker Connection** (Test 1)
   - Connection to Red Pitaya
   - IDN retrieval
   - Connection stability

2. **ASG Control** (Test 2)
   - Module setup with all parameters
   - Frequency sweep (1, 5, 10 MHz)
   - Amplitude control (0.1, 0.5, 1.0 V)
   - Output enable/disable

3. **PID Control** (Test 3)
   - Module configuration
   - Setpoint changes
   - P gain adjustment
   - Integrator reset

4. **IQ Demodulation** (Test 4)
   - Module setup
   - Frequency control
   - Phase control

5. **Sampler Access** (Test 5)
   - Instantaneous value reading
   - IQ data acquisition with averaging
   - PID data monitoring

6. **Oscilloscope Acquisition** (Test 6)
   - Rolling mode configuration
   - Trace acquisition
   - Different decimation rates
   - Data statistics

7. **Plugin Integration** (Test 7)
   - Shared controller usage
   - Plugin instantiation

### Expected Results

All tests should show `✓` checkmarks. Typical output:

```
==================================================================
TESTING PyrplWorker Connection
==================================================================

[1/3] Creating PyrplWorker instance...
  ✓ PyrplWorker created

[2/3] Connecting to Red Pitaya at 100.107.106.75...
  ✓ Connection successful
  ✓ IDN: StemLab on 100.107.106.75

... [more tests] ...

==================================================================
ALL TESTS PASSED!
==================================================================
```

### Troubleshooting Automated Tests

| Error | Solution |
|-------|----------|
| `Connection failed` | Verify Red Pitaya IP, network connectivity, and that device is powered on |
| `ModuleNotFoundError: stemlab` | Install StemLab: `pip install git+https://github.com/ograsdijk/StemLab.git` |
| `SSH Connection Error` | Check SSH service on Red Pitaya, verify credentials |
| `Timeout during acquisition` | Increase duration parameter, check decimation settings |

## Test Level 2: PyMoDAQ Dashboard Testing

### Launching PyMoDAQ Dashboard

```bash
# Activate virtual environment
source venv_hardware_test/bin/activate

# Launch dashboard
python -m pymodaq.dashboard
```

### Test Sequence 1: DAQ_Move_RedPitaya

#### 1.1 Add Plugin

1. In PyMoDAQ dashboard, click "Add Move"
2. Select `RedPitaya` from the plugin list
3. Click OK to initialize

**Expected**: Plugin appears in dashboard with hierarchical parameter tree

#### 1.2 Test ASG Control

1. Expand **ASG Settings → ASG0**
2. Test each parameter:
   - Set **Frequency**: 1000000 Hz (1 MHz)
   - Set **Amplitude**: 0.5 V
   - Set **Waveform**: sin
   - Set **Output Direct**: out1
3. Commit settings
4. Navigate to **ASG0_Freq** actuator and move to different frequencies

**Expected**:
- Parameters update without errors
- Status log shows "ASG module 'asg0' reconfigured"
- Physical output 1 produces sine wave (verify with oscilloscope if available)

#### 1.3 Test PID Control

1. Expand **PID Settings → PID0**
2. Configure:
   - **Input Signal**: in1
   - **Setpoint**: 0.0 V
   - **P Gain**: 100
   - **I Gain**: 1000
   - **Output Direct**: off (for testing, avoid feedback)
3. Commit settings
4. Use actuators to adjust PID parameters

**Expected**:
- All parameters accept values
- Status shows "PID module 'pid0' reconfigured"
- No errors in log

#### 1.4 Test IQ Demodulation

1. Expand **IQ Settings → IQ0**
2. Configure:
   - **Frequency**: 5000000 Hz (5 MHz)
   - **Phase**: 0 degrees
   - **Bandwidth**: 1000 Hz
   - **Input Signal**: in1
3. Move **IQ0_Freq** and **IQ0_Phase** actuators

**Expected**:
- Frequency and phase update correctly
- No connection errors

#### 1.5 Test Multi-Axis Operations

1. Select multiple actuators (Ctrl+Click)
2. Move all selected axes simultaneously
3. Read current positions from all axes

**Expected**:
- All axes move independently
- get_actuator_value() returns all 21 axis values
- No axis confusion or errors

### Test Sequence 2: DAQ_1DViewer_RedPitaya

#### 2.1 Add Plugin

1. Click "Add Viewer" → 1D Viewer
2. Select `RedPitaya` from plugin list
3. Initialize

**Expected**: Plugin appears with mode selector showing "Oscilloscope" by default

#### 2.2 Test Oscilloscope Mode

1. Verify **Mode**: Oscilloscope
2. Configure in **Oscilloscope** group:
   - **Channel**: in1
   - **Decimation**: 64
   - **Duration**: 1.0 s
3. Click "Grab" button

**Expected**:
- Time-domain waveform appears in viewer
- X-axis labeled "Time (s)"
- Y-axis shows voltage values
- Continuous grab updates plot

#### 2.3 Test Spectrum Analyzer Mode

1. Change **Mode** to "Spectrum Analyzer"
2. Verify parameter visibility:
   - Oscilloscope group hidden
   - Spectrum Analyzer group visible
3. Configure:
   - **Input Channel**: in1
   - **FFT Window**: hanning
   - **Frequency Span**: 10000000 Hz (10 MHz)
4. Click "Grab"

**Expected**:
- Frequency-domain spectrum appears
- X-axis labeled "Frequency (Hz)"
- FFT magnitude on Y-axis
- Peaks visible at input signal frequencies

#### 2.4 Test IQ Monitor Mode

1. Change **Mode** to "IQ Monitor"
2. Configure:
   - **IQ Module**: iq0
   - **Averages**: 10
3. Click "Grab"

**Expected**:
- Two 0D values displayed: I_value and Q_value
- Values update on each grab
- Both values in reasonable voltage range

#### 2.5 Test PID Monitor Mode

1. Change **Mode** to "PID Monitor"
2. Configure:
   - **PID Module**: pid0
   - **Signal Type**: output
   - **Averages**: 10
3. Click "Grab"
4. Switch **Signal Type** to "error", then "ival" and grab each

**Expected**:
- Single 0D value displayed for each signal type
- Values change based on signal type
- No errors on mode switches

#### 2.6 Test Parameter Reconfiguration

1. In Oscilloscope mode, change **Decimation** from 64 to 256
2. Verify status log shows "Configuring scope..."
3. Grab data and verify sample rate changed

**Expected**:
- Hardware reconfigures automatically
- No manual reinitialization needed
- Data acquisition works with new settings

### Test Sequence 3: Controller Sharing

#### 3.1 Shared Worker Test

1. Initialize **DAQ_Move_RedPitaya** first
2. Add **DAQ_1DViewer_RedPitaya**
3. During viewer initialization, pass the move plugin's controller

**Expected**:
- Viewer accepts shared controller
- Both plugins control same hardware
- No connection conflicts

#### 3.2 Coordinated Operation

1. With both plugins active:
   - Use DAQ_Move to set ASG0 frequency to 5 MHz with output to out1
   - Connect out1 to in1 externally (loopback cable)
   - Use DAQ_Viewer in Oscilloscope mode to observe signal
2. Change ASG frequency via DAQ_Move
3. Observe frequency change in DAQ_Viewer spectrum

**Expected**:
- Changes in Move plugin visible in Viewer data
- Real-time coordination works
- No synchronization issues

## Test Level 3: Integration Scenarios

### Scenario 1: Lock-in Detection

**Setup:**
1. Configure IQ0 for 5 MHz demodulation
2. Set ASG0 to generate 5 MHz reference signal
3. Monitor I/Q values with averaging

**Test Steps:**
1. Use DAQ_Move to set:
   - ASG0: 5 MHz, 0.5 V amplitude, sine wave, output to out1
   - IQ0: 5 MHz demodulation, 1 kHz bandwidth, input from in1
2. Connect out1 to in1 (loopback)
3. Use DAQ_Viewer (IQ Monitor mode) to acquire I/Q data
4. Adjust IQ0 phase via DAQ_Move and observe I/Q changes

**Expected Results:**
- I value maximized when phase = 0°
- Q value maximized when phase = 90°
- Clean lock-in signal detection

### Scenario 2: Frequency Response

**Setup:**
1. Use DAQ_Move ASG0_Freq as scan actuator
2. Use DAQ_Viewer in IQ Monitor mode as detector
3. Configure DAQ_Scan extension

**Test Steps:**
1. Configure ASG0 sweep from 100 kHz to 10 MHz
2. Set IQ0 to track ASG0 frequency
3. Run scan acquisition
4. Plot I/Q magnitude vs frequency

**Expected Results:**
- Automated frequency sweep
- Data acquisition at each point
- Frequency response curve

### Scenario 3: PID Feedback Loop

**Setup:**
1. Configure PID for feedback control
2. Monitor PID output and error signals

**Test Steps:**
1. Set PID0 input to in1, output to out2
2. Set initial P and I gains
3. Apply step change to setpoint
4. Monitor response with PID Monitor mode
5. Tune gains for desired response

**Expected Results:**
- Feedback loop stable
- PID output tracks setpoint
- Gain changes affect response speed

## Test Checklist

### Pre-Testing
- [ ] Red Pitaya accessible at 100.107.106.75
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] Structure validation passed

### Automated Tests
- [ ] Test 1: Connection successful
- [ ] Test 2: ASG control working
- [ ] Test 3: PID control working
- [ ] Test 4: IQ control working
- [ ] Test 5: Sampler access working
- [ ] Test 6: Scope acquisition working
- [ ] Test 7: Plugin integration verified

### DAQ_Move Plugin
- [ ] Plugin loads in dashboard
- [ ] ASG parameters configure correctly
- [ ] PID parameters configure correctly
- [ ] IQ parameters configure correctly
- [ ] All 21 actuators functional
- [ ] Multi-axis moves work
- [ ] Commit settings applies changes
- [ ] Status updates displayed

### DAQ_Viewer Plugin
- [ ] Plugin loads in dashboard
- [ ] Oscilloscope mode acquires data
- [ ] Spectrum Analyzer mode shows FFT
- [ ] IQ Monitor mode reads I/Q values
- [ ] PID Monitor mode reads controller data
- [ ] Mode switching updates parameters
- [ ] Hardware reconfigures on changes
- [ ] Continuous grab works

### Integration
- [ ] Plugins share controller
- [ ] Coordinated operation works
- [ ] Lock-in scenario tested
- [ ] No connection conflicts

## Known Issues and Workarounds

### Issue 1: Hardcoded IP Address

**Problem**: Default IP is hardcoded to `100.107.106.75`

**Workaround**: Modify plugin source if using different IP:
- Edit `daq_move_RedPitaya.py` line 103
- Edit `daq_1Dviewer_RedPitaya.py` line 76

**Permanent Fix**: TODO - Add connection parameters to plugin settings

### Issue 2: IQ Q-Value Placeholder

**Problem**: `get_iq_data()` uses placeholder for Q value

**Workaround**: Verify sampler signal names in StemLab documentation

**Testing**: Compare I/Q values with known reference signal

### Issue 3: Fixed Spectrum Duration

**Problem**: Spectrum analyzer uses fixed 1.0s duration

**Impact**: Frequency resolution fixed at 1 Hz

**Workaround**: Modify `_setup_scope_hardware()` if different resolution needed

## Reporting Issues

When reporting issues, include:

1. **Test Type**: Which test level and sequence
2. **Error Message**: Full error output from console
3. **Configuration**: Red Pitaya IP, PyMoDAQ version, Python version
4. **Reproducibility**: Steps to reproduce the issue
5. **Logs**: PyMoDAQ log files if available

## Success Criteria

Testing is complete when:

✅ All automated tests pass
✅ All dashboard manual tests complete
✅ All modes in viewer plugin functional
✅ Multi-axis control works in move plugin
✅ At least one integration scenario tested successfully
✅ No crashes or freezes during normal operation

## Next Steps After Testing

1. Document any hardware-specific calibrations needed
2. Create user presets for common configurations
3. Consider implementing Network Analyzer extension
4. Add mock mode for offline development
5. Contribute test results and feedback to repository
