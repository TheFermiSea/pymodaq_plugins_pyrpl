# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pymodaq_plugins_pyrpl` provides comprehensive integration of Red Pitaya STEMlab devices with PyMoDAQ, delivering a complete suite of hardware modules including PID control, arbitrary signal generation, oscilloscope functionality, and lock-in amplifier capabilities. This represents a full Red Pitaya integration solution for advanced measurement and control applications.

## Development Commands

### Building and Testing
```bash
# Install in development mode
pip install -e .

# Run all tests (50+ test cases)
python -m pytest tests/

# Run specific plugin tests
python -m pytest tests/test_pyrpl_functionality.py -k "test_pid"     # PID tests only
python -m pytest tests/test_pyrpl_functionality.py -k "test_asg"     # ASG tests only  
python -m pytest tests/test_pyrpl_functionality.py -k "test_scope"   # Scope tests only
python -m pytest tests/test_pyrpl_functionality.py -k "test_iq"      # IQ tests only

# Test by mode
python -m pytest tests/test_pyrpl_functionality.py -k "test_mock"    # Mock tests only
python -m pytest tests/test_pyrpl_functionality.py -k "test_real"    # Hardware tests only

# Test structure validation
python tests/test_plugin_package_structure.py

# Run tests in parallel (CI configuration)
pytest -n auto tests/

# Build package (uses hatch + custom metadata hook)
python -m build
```

### Code Quality
```bash
# Lint code (syntax errors and undefined names)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=src/pymodaq/resources/QtDesigner_Ressources,docs

# Run full linting check
flake8 .
```

## Architecture Overview

**Complete PyRPL Integration**: Full Red Pitaya functionality beyond basic PID control

**Implemented Modules**:
- **PID Controllers**: Hardware PID with PyMoDAQ integration (3 channels)
- **Signal Generation**: ASG with full waveform and frequency control (2 channels)
- **Data Acquisition**: Oscilloscope with triggering and time-series capture (2 channels)
- **Lock-in Detection**: IQ modules for phase-sensitive measurements (3 channels)
- **Voltage Monitoring**: Multi-channel real-time monitoring

**Infrastructure**:
- **Centralized PyRPL Wrapper**: Connection pooling and thread-safe operations
- **Mock Mode Support**: Complete development environment without hardware
- **Comprehensive Error Handling**: Robust connection management and recovery
- **Thread-Safe Operations**: Concurrent plugin usage without conflicts

**Key Components**:
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py` - centralized PyRPL communication
- `src/pymodaq_plugins_pyrpl/daq_move_plugins/` - actuator plugins (PID, ASG)
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/` - 0D detectors (voltage, IQ)
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/` - 1D detectors (scope)
- `src/pymodaq_plugins_pyrpl/models/PIDModelPyrpl.py` - PID model implementation

## Implementation Status

**✅ Completed Plugins**:
1. **PIDModelPyrpl** - PyMoDAQ PID extension model
2. **DAQ_Move_PyRPL_PID** - PID setpoint control actuator
3. **DAQ_0DViewer_PyRPL** - Basic voltage monitoring detector
4. **DAQ_Move_PyRPL_ASG** - Arbitrary Signal Generator control (NEW)
5. **DAQ_1DViewer_PyRPL_Scope** - Oscilloscope time-series acquisition (NEW)
6. **DAQ_0DViewer_PyRPL_IQ** - Lock-in amplifier for phase-sensitive detection (NEW)

**✅ Infrastructure**:
- **Centralized PyRPL Wrapper** - Thread-safe connection management for all modules
- **Comprehensive Test Suite** - Mock hardware support for all plugins (50+ tests)
- **Complete Error Handling** - Graceful degradation when PyRPL unavailable
- **Documentation** - Complete user and developer documentation

## PyMoDAQ Plugin Conventions

**Plugin naming**: 
- Move plugins: `DAQ_Move_PluginName` class in `daq_move_PluginName.py`
- Viewer plugins: `DAQ_XDViewer_PluginName` class in `daq_XDviewer_PluginName.py`

**Required methods**:
- Move plugins: `ini_attributes`, `get_actuator_value`, `close`, `commit_settings`, `ini_stage`, `move_abs`, `move_home`, `move_rel`, `stop_motion`
- Viewer plugins: `ini_attributes`, `grab_data`, `close`, `commit_settings`, `ini_detector`

**Units**: Must use valid Pint units (validated by tests)
**Class structure**: Plugin classes must have `_controller_units` attribute (string, list, or dict of valid units)

**PyRPL Plugin Specifics**:
- All plugins support `mock_mode` parameter for development
- Thread-safe operations via centralized PyRPL wrapper
- Shared connection management across multiple plugin instances
- Comprehensive error handling for PyRPL/Qt compatibility issues

## Key PyRPL Integration Points

**Connection**: Use hostname (e.g., 'rp-f0a552.local' or IP address)

**PID Control**: 
- `pid.setpoint` = target voltage
- `pid.p`, `pid.i`, `pid.d` = PID gains
- `pid.input`, `pid.output_direct` = signal routing
- 3 independent PID modules: pid0, pid1, pid2

**ASG (Arbitrary Signal Generator)**:
- `asg.frequency`, `asg.amplitude`, `asg.offset` = signal parameters
- `asg.waveform` = sin, cos, ramp, square, noise, dc, custom
- `asg.trigger_source` = triggering control
- 2 independent ASG modules: asg0, asg1

**Oscilloscope**:
- `scope.input1`, `scope.input2` = input channels
- `scope.decimation` = sampling rate control (1x to 65536x)
- `scope.trigger_source`, `scope.trigger_delay` = trigger configuration
- 16,384 samples per acquisition (2^14)

**IQ (Lock-in Amplifier)**:
- `iq.frequency`, `iq.bandwidth` = detection parameters
- `iq.phase`, `iq.gain` = signal conditioning
- `iq.na_averages` = averaging control
- 3 independent IQ modules: iq0, iq1, iq2

**Voltage Reading**: 
- Real-time: `rp.sampler.in1`, `rp.sampler.in2`
- Scope mode: `rp.scope.voltage_in1`, `rp.scope.voltage_in2`

## Development Notes

- **Hardware Limits**: Red Pitaya voltage range ±1V (use external amplifiers/attenuators as needed)
- **Safety**: Always disable PID/ASG outputs before disconnecting (`output_direct = 'off'`)
- **Template Structure**: `pymodaq_plugins_template` provides the structural foundation
- **Package Layout**: Both template and pyrpl-specific packages coexist in `src/`
- **Build System**: Uses hatch with custom metadata hook (`hatch_build.py`)
- **Entry Points**: Dynamically generated from plugin structure
- **CI/CD**: Python 3.11 with PyQt5, includes flake8 linting and pytest with xvfb
- **Testing**: 50+ tests validate plugin structure, methods, units, and functionality
- **PyRPL Compatibility**: Includes workarounds for Qt version conflicts
- **Mock Mode**: Complete simulation environment for development without hardware
- **Thread Safety**: PyRPL wrapper manages concurrent access to hardware modules
- **Performance**: Hardware modules provide microsecond-level response times

## Plugin Usage Examples

### PID Control
```python
# Configure PID for laser power stabilization
pid_params = {
    'redpitaya_host': 'rp-f0a552.local',
    'pid_module': 'pid0',
    'input_channel': 'in1',    # photodiode signal
    'output_channel': 'out1',   # laser control
    'p_gain': 0.1,
    'i_gain': 0.01
}
```

### Signal Generation
```python
# Configure ASG for modulation or stimulus
asg_params = {
    'redpitaya_host': 'rp-f0a552.local',
    'asg_channel': 'asg0',
    'frequency': 1000.0,        # Hz
    'amplitude': 0.5,           # V
    'waveform': 'sin',
    'trigger_source': 'immediately'
}
```

### Oscilloscope Acquisition
```python
# Configure scope for transient capture
scope_params = {
    'redpitaya_host': 'rp-f0a552.local',
    'input_channel': 'in1',
    'decimation': 64,           # 1.95 MS/s effective rate
    'trigger_source': 'ch1_positive_edge',
    'trigger_delay': 0.0,
    'average': 10               # noise reduction
}
```

### Lock-in Detection
```python
# Configure IQ for weak signal recovery
iq_params = {
    'redpitaya_host': 'rp-f0a552.local',
    'iq_module': 'iq0',
    'input_channel': 'in1',
    'frequency': 1000.0,        # reference frequency
    'bandwidth': 10.0,          # detection bandwidth
    'phase': 0.0                # reference phase
}
```

## Hardware Requirements

**Supported Red Pitaya Models**:
- STEMlab 125-10: Standard precision, 10-bit ADC/DAC
- STEMlab 125-14: High precision, 14-bit ADC/DAC (recommended)
- STEMlab 122-16: Highest precision, 16-bit ADC/DAC

**PyRPL Version Compatibility**:
- PyRPL 0.9.5+: Recommended version with stability improvements
- Qt Compatibility: May require Qt5 for stable operation
- Workaround: Enable mock mode for development with Qt6

**Performance Specifications**:
- **PID Response**: < 1 microsecond (hardware FPGA processing)
- **ASG Frequency Range**: DC to 62.5 MHz
- **Scope Sampling Rate**: 125 MS/s (decimated to 1.9 kHz - 125 MS/s)
- **IQ Detection Bandwidth**: 1 Hz to 1 MHz
- **Network Latency**: < 1 ms (direct Ethernet connection)

## Troubleshooting

### PyRPL/Qt Compatibility Issues
- **Symptom**: Import errors, GUI crashes, Qt version conflicts
- **Solution**: Use virtual environment with PyQt5
- **Workaround**: Enable mock mode for development
- **Alternative**: Run plugins in separate processes

### Common PyRPL Problems
- **Connection refused**: Check Red Pitaya network configuration
- **FPGA bitstream**: Ensure PyRPL firmware is loaded
- **Resource conflicts**: Use PyRPL wrapper's connection pooling
- **Performance issues**: Use direct Ethernet connection

### Mock Mode Development
- **Enable**: Set `mock_mode: True` in plugin parameters
- **Features**: Complete simulation of all hardware modules
- **Testing**: All plugins work without physical hardware
- **Integration**: Full PyMoDAQ compatibility in mock mode

## File References

Project documentation:
- `README.rst` - comprehensive user guide and plugin documentation
- `CLAUDE.md` - developer guide and project instructions
- `ai_docs/` - historical implementation guides (may be outdated)
- `tests/` - comprehensive test suite with mock and hardware tests

## Tooling for Shell Interactions

**Finding FILES**: use `fd` or built-in `find`
**Finding TEXT/strings**: use `rg` (ripgrep) - faster than grep
**Finding CODE STRUCTURE**: use `ast-grep` for semantic code search
**Selecting from multiple results**: pipe to `fzf` for interactive selection
**JSON processing**: use `jq`
**YAML/XML processing**: use `yq`

These tools significantly improve search efficiency and accuracy when available.

## Project Status Summary

**Current State**: Complete PyRPL integration suite with comprehensive functionality
**Plugin Count**: 6 complete plugins + infrastructure
**Test Coverage**: 50+ automated tests including mock and hardware validation
**Documentation**: Complete user and developer documentation
**Maturity**: Production-ready for research and industrial applications

**Key Achievements**:
- Thread-safe multi-plugin coordination
- Complete hardware module coverage (PID, ASG, Scope, IQ)
- Mock mode for development without hardware
- Comprehensive error handling and recovery
- Professional documentation and testing

**Next Steps**: 
- Package release and PyPI publication
- User feedback integration
- Performance optimization based on real-world usage
- Additional waveform and trigger mode support

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.