# PyRPL Extensions for PyMoDAQ

## Overview

This document describes the PyRPL module extensions implemented as PyMoDAQ plugins, providing comprehensive control and monitoring capabilities for Red Pitaya hardware.

## Implementation Summary

### Completed Components

1. **Extended PyrplWorker** (`src/pymodaq_plugins_pyrpl/hardware/pyrpl_worker.py`)
   - Added ASG (Arbitrary Signal Generator) control methods
   - Added PID (Proportional-Integral-Derivative) control methods
   - Added IQ (Demodulation) control methods
   - Added Sampler access methods for 0D data acquisition

2. **DAQ_Move_RedPitaya** (`src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_RedPitaya.py`)
   - Multi-actuator plugin exposing all control parameters
   - Hierarchical parameter tree for organized settings
   - 21 actuator axes across ASG, PID, and IQ modules

3. **DAQ_1DViewer_RedPitaya** (`src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_RedPitaya.py`)
   - Multi-mode acquisition plugin
   - Four acquisition modes: Oscilloscope, Spectrum Analyzer, IQ Monitor, PID Monitor
   - Automatic mode switching with parameter visibility management

## Architecture

### PyRPL Module Mapping

The implementation maps PyRPL modules to PyMoDAQ plugins as follows:

**Hardware Modules → DAQ Plugins:**
- **ASG0/ASG1** (Arbitrary Signal Generators) → DAQ_Move_RedPitaya actuators + Waveform parameters
- **PID0/PID1/PID2** (PID Controllers) → DAQ_Move_RedPitaya actuators + PID parameters
- **IQ0/IQ1/IQ2** (IQ Demodulators) → DAQ_Move_RedPitaya actuators + DAQ_1DViewer_RedPitaya (IQ Monitor mode)
- **Scope** (Oscilloscope) → DAQ_1DViewer_RedPitaya (Oscilloscope mode)
- **Sampler** (Instant values) → Used internally by all monitoring modes

**Software Modules → PyMoDAQ Extensions:**
- **Network Analyzer** → Can be implemented using PyMoDAQ's DAQ_Scan extension
- **Spectrum Analyzer** → Implemented as DAQ_1DViewer_RedPitaya mode with FFT processing
- **Lockbox** → Future extension using coordinated ASG/PID/IQ control

### Design Principles

1. **Contract-First Architecture**: All hardware interactions go through `PyrplWorker`, maintaining the existing contract pattern
2. **Hierarchical Organization**: Parameters grouped by module type (ASG, PID, IQ) for clarity
3. **Efficient Mapping**: Dictionary-based mapping for fast axis-to-method resolution
4. **Code Reuse**: Helper methods to generate parameter structures programmatically
5. **Mode Isolation**: Each viewer mode has dedicated parameter groups with automatic visibility management

## Plugin Details

### DAQ_Move_RedPitaya

**Purpose**: Control all settable parameters across PyRPL hardware modules

**Actuator Axes** (21 total):
```
ASG0: Frequency, Amplitude, Offset
ASG1: Frequency, Amplitude, Offset
PID0: Setpoint, P Gain, I Gain
PID1: Setpoint, P Gain, I Gain
PID2: Setpoint, P Gain, I Gain
IQ0: Frequency, Phase
IQ1: Frequency, Phase
IQ2: Frequency, Phase
```

**Parameter Groups**:
- **ASG Settings**: Configuration for both arbitrary signal generators
  - Frequency (0-62.5 MHz)
  - Amplitude (-1 to 1 V)
  - Offset (-1 to 1 V)
  - Waveform (sin, dc, halframp, square)
  - Output Direct (off, out1, out2)

- **PID Settings**: Configuration for all three PID controllers
  - Setpoint (-1 to 1 V)
  - P Gain (-1e6 to 1e6)
  - I Gain (0 to 1e6 Hz)
  - Input Signal (in1, in2, asg0, asg1)
  - Output Direct (off, out1, out2)

- **IQ Settings**: Configuration for all three IQ demodulators
  - Frequency (0-62.5 MHz)
  - Phase (-180 to 180 degrees)
  - Bandwidth (1-1e6 Hz)
  - Input Signal (in1, in2)

**Key Features**:
- Per-axis units (Hz, V, degrees)
- Atomic module reconfiguration via `commit_settings`
- Clean dictionary-based mapping for efficient move operations
- Programmatic parameter generation to avoid code duplication

### DAQ_1DViewer_RedPitaya

**Purpose**: Multi-mode data acquisition from Red Pitaya hardware

**Acquisition Modes**:

1. **Oscilloscope Mode** (1D Data)
   - Time-domain waveforms using rolling mode acquisition
   - Parameters: Channel (in1/in2), Decimation, Duration
   - Returns: Time series data with voltage axis

2. **Spectrum Analyzer Mode** (1D Data)
   - Frequency-domain FFT analysis
   - Parameters: Input Channel, FFT Window, Frequency Span
   - Automatic decimation calculation based on Nyquist criterion
   - Returns: Frequency spectrum with magnitude axis

3. **IQ Monitor Mode** (0D Data)
   - I/Q quadrature values from demodulators
   - Parameters: IQ Module, Averages
   - Returns: Two 0D values (I and Q)

4. **PID Monitor Mode** (0D Data)
   - PID controller outputs and internal signals
   - Parameters: PID Module, Signal Type (output/error/ival), Averages
   - Returns: Single 0D value

**Key Features**:
- Dynamic parameter visibility based on selected mode
- Automatic hardware reconfiguration on mode or parameter changes
- FFT windowing for spectrum analysis (Hanning, Hamming, Blackman, Bartlett)
- Averaged measurements for 0D modes to reduce noise

## Usage Examples

### Example 1: Signal Generation with ASG

1. Add **DAQ_Move_RedPitaya** plugin to PyMoDAQ dashboard
2. Navigate to **ASG Settings → ASG0**
3. Set parameters:
   - Frequency: 1 MHz
   - Amplitude: 0.5 V
   - Waveform: sin
   - Output Direct: out1
4. Move the **ASG0_Freq** actuator or use **commit_settings** to apply configuration
5. Signal is now output on physical output 1

### Example 2: PID Control

1. Add **DAQ_Move_RedPitaya** plugin
2. Configure PID0:
   - Input Signal: in1
   - Setpoint: 0.0 V
   - P Gain: 100
   - I Gain: 1000 Hz
   - Output Direct: out2
3. Commit settings to activate PID loop
4. Monitor PID performance using **DAQ_1DViewer_RedPitaya** in **PID Monitor** mode

### Example 3: Spectrum Analysis

1. Add **DAQ_1DViewer_RedPitaya** plugin
2. Select **Spectrum Analyzer** mode
3. Configure:
   - Input Channel: in1
   - FFT Window: hanning
   - Frequency Span: 10 MHz
4. Click "Grab" to acquire and display frequency spectrum

### Example 4: Lock-in Detection

1. Configure IQ0 demodulator via **DAQ_Move_RedPitaya**:
   - Frequency: 5 MHz (match reference signal)
   - Phase: 0 degrees
   - Bandwidth: 1 kHz
   - Input Signal: in1
2. Switch **DAQ_1DViewer_RedPitaya** to **IQ Monitor** mode
3. Select IQ0 module and set averaging
4. Acquire I/Q data for lock-in measurements

### Example 5: Network Analyzer (Using DAQ_Scan)

This is a future enhancement that combines existing plugins:

1. Use **DAQ_Move_RedPitaya** to control ASG0 frequency as scan actuator
2. Use **DAQ_1DViewer_RedPitaya** in **IQ Monitor** mode to measure response
3. Configure **DAQ_Scan** extension:
   - Scan actuator: ASG0_Freq
   - Scan range: 100 kHz to 10 MHz
   - Detector: IQ0 I/Q values
4. Run scan to measure frequency response (amplitude and phase vs frequency)

## Integration with Existing Plugins

### Controller Sharing

Both new plugins can share a `PyrplWorker` controller instance:

```python
# In PyMoDAQ dashboard:
# 1. Initialize DAQ_Move_RedPitaya first
# 2. Add DAQ_1DViewer_RedPitaya
# 3. Pass the same controller to viewer via controller parameter
```

This ensures:
- Single hardware connection
- Consistent state across plugins
- No connection conflicts

### Compatibility with Phase 1/Phase 2 Plugins

The new plugins complement existing plugins:

- **Phase 1 (InProcess)**: Direct threading for rapid prototyping
- **Phase 2 (BridgeClient)**: Process isolation for production stability
- **New Plugins**: Direct hardware control with multi-module coordination

All three approaches use the same `PyrplWorker` core, ensuring consistent behavior.

## Testing

### Unit Testing

Test files should be added to `tests/`:
- `tests/unit/test_move_redpitaya.py` - Test DAQ_Move_RedPitaya functionality
- `tests/unit/test_viewer_redpitaya.py` - Test DAQ_1DViewer_RedPitaya modes
- `tests/integration/test_move_viewer_integration.py` - Test controller sharing

### Hardware Testing

With Red Pitaya at `100.107.106.75`:

```bash
# Test oscilloscope mode
pytest tests/e2e/test_viewer_oscilloscope.py -m hardware

# Test ASG control
pytest tests/e2e/test_move_asg.py -m hardware

# Test PID control
pytest tests/e2e/test_move_pid.py -m hardware

# Test IQ demodulation
pytest tests/e2e/test_viewer_iq.py -m hardware
```

### Manual Testing Checklist

**DAQ_Move_RedPitaya**:
- [ ] ASG frequency sweep generates expected waveform
- [ ] PID setpoint changes produce control response
- [ ] IQ phase adjustment affects demodulation
- [ ] Commit settings applies all module parameters atomically
- [ ] Multi-axis moves work correctly

**DAQ_1DViewer_RedPitaya**:
- [ ] Oscilloscope mode displays clean time-domain signal
- [ ] Spectrum analyzer shows expected frequency peaks
- [ ] IQ monitor returns reasonable I/Q values
- [ ] PID monitor tracks controller output
- [ ] Mode switching updates parameter visibility correctly
- [ ] Parameter changes trigger hardware reconfiguration

## Known Issues and TODOs

### Current Limitations

1. **Hardcoded IP Address**: Default Red Pitaya IP is hardcoded to `100.107.106.75`
   - **TODO**: Add connection parameters to plugin settings UI

2. **IQ Q-Value Access**: Placeholder implementation in `get_iq_data()`
   - **TODO**: Verify correct sampler signal names for I/Q access in StemLab API

3. **Spectrum Duration**: Fixed 1.0s duration for spectrum analyzer
   - **TODO**: Make duration a user parameter for frequency resolution control

4. **No Mock Mode**: Plugins require real hardware
   - **TODO**: Implement mock/simulation mode for offline development

### Future Enhancements

1. **Network Analyzer Extension**: Create dedicated DAQ_Scan-based extension
2. **Lockbox Implementation**: Coordinated feedback control across modules
3. **Advanced Triggering**: Support for complex trigger conditions in scope mode
4. **Real-time Streaming**: Continuous data streaming for long acquisitions
5. **Parameter Presets**: Save/load module configurations

## File Locations

### Implementation Files
- **Worker Extension**: `src/pymodaq_plugins_pyrpl/hardware/pyrpl_worker.py`
- **Move Plugin**: `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_RedPitaya.py`
- **Viewer Plugin**: `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_RedPitaya.py`

### Documentation
- **This Document**: `PYRPL_EXTENSIONS_README.md`
- **Project CLAUDE.md**: `CLAUDE.md` (AI development guidelines)
- **Main README**: `README.md` (Package overview)

### Testing (To be created)
- **Unit Tests**: `tests/unit/test_move_redpitaya.py`, `tests/unit/test_viewer_redpitaya.py`
- **Integration Tests**: `tests/integration/test_move_viewer_integration.py`
- **Hardware Tests**: `tests/e2e/test_*_hardware.py`

## Development History

This implementation was created through AI-assisted development with the following workflow:

1. **Research Phase**: Used Zen chat with Gemini 2.5 Pro to analyze PyRPL documentation
2. **Architecture Design**: Collaborative design session mapping PyRPL modules to PyMoDAQ plugins
3. **Planning Phase**: Used Zen planner with Gemini to create 3-phase implementation plan
4. **Implementation**:
   - Phase 1: Extended `pyrpl_worker.py` with new control methods (Claude)
   - Phase 2: Created `DAQ_Move_RedPitaya` plugin (delegated to Gemini 2.5 Pro)
   - Phase 3: Created `DAQ_1DViewer_RedPitaya` plugin (delegated to Gemini 2.5 Flash)
5. **Integration**: Fixed import statements and controller initialization (Claude)

## References

- **PyRPL Documentation**: https://pyrpl.readthedocs.io/en/latest/
- **StemLab GitHub**: https://github.com/ograsdijk/StemLab
- **PyMoDAQ Documentation**: https://pymodaq.cnrs.fr/
- **Red Pitaya**: https://www.redpitaya.com/

## Support and Contribution

For issues, questions, or contributions related to these plugins:
1. Check existing documentation in this repository
2. Review PyMoDAQ plugin development guide in `CLAUDE.md`
3. Test with hardware at IP `100.107.106.75`
4. Submit issues or pull requests following project conventions
