# PyMoDAQ PyRPL Plugin Documentation

Comprehensive documentation for the PyRPL/PyMoDAQ integration plugin.

## Documentation Index

### Getting Started

- **[Installation Guide](INSTALLATION.md)** - Complete installation instructions for all platforms
- **[PyMoDAQ Setup Guide](PYMODAQ_SETUP_GUIDE.md)** - PyMoDAQ-specific setup and configuration
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Architecture, code structure, and development workflow

### Testing & Validation

- **[Hardware Testing Guide](HARDWARE_TESTING.md)** - Complete guide for testing with real Red Pitaya hardware
  - Hardware setup and configuration
  - PyRPL bug fixes (critical for v0.9.6.0)
  - Test results and validation
  - Known issues and troubleshooting
  - Performance optimization tips

- **[Mock Mode Tutorial](MOCK_TUTORIAL.md)** - Using mock mode for development and testing without hardware

### Architecture Documentation

- **[IPC Architecture](IPC_ARCHITECTURE.md)** - Inter-process communication architecture
- **[Architecture Review](ARCHITECTURE_REVIEW.md)** - Command multiplexing architecture review
- **[Shared Worker Architecture](SHARED_WORKER_ARCHITECTURE.md)** - Shared PyRPL worker design
- **[Threading Architecture](THREADING_ARCHITECTURE.md)** - How PyRPL integrates with PyMoDAQ's multi-threaded framework
- **[Control Theory Foundations](CONTROL_THEORY_FOUNDATIONS.md)** - PID control theory and implementation details

### Troubleshooting

- **[SSH Connection Troubleshooting](TROUBLESHOOTING_SSH_CONNECTION.md)** - Fixing SSH connection issues with Red Pitaya

## Quick Links

### For Users

Start here if you want to use the plugin:

1. [Installation Guide](INSTALLATION.md) - Install the plugin
2. [Hardware Testing Guide](HARDWARE_TESTING.md) - Test with your Red Pitaya
3. [Mock Tutorial](MOCK_TUTORIAL.md) - Practice without hardware

### For Developers

Start here if you want to contribute or modify the plugin:

1. [Developer Guide](DEVELOPER_GUIDE.md) - Understand the architecture
2. [Hardware Testing Guide](HARDWARE_TESTING.md) - Run validation tests
3. [Control Theory Foundations](CONTROL_THEORY_FOUNDATIONS.md) - Understand the algorithms

## Plugin Features

### Hardware Support

- **Compatible Devices:**
  - Red Pitaya STEMlab 125-10
  - Red Pitaya STEMlab 125-14 (recommended)
  - Red Pitaya STEMlab 122-16

- **Supported Modules:**
  - 3× PID Controllers (hardware-accelerated)
  - 2× Arbitrary Signal Generators
  - 1× Oscilloscope (16k samples, 125 MS/s)
  - 3× Lock-in Amplifiers (IQ detection)
  - Voltage Monitor (IN1, IN2)

### Plugin Components

#### Actuator Plugins (DAQ_Move)

- **DAQ_Move_PyRPL_PID** - PID setpoint control
  - ±1V setpoint range
  - Real-time gain adjustment (P, I, D)
  - Input/output routing
  - Safety limits

- **DAQ_Move_PyRPL_ASG** - Signal generation control
  - Waveforms: sine, cosine, ramp, square, noise, DC
  - Frequency: 0 Hz to 62.5 MHz
  - Amplitude/offset control
  - External triggering

#### Detector Plugins (DAQ_Viewer)

- **DAQ_0DViewer_PyRPL** - Multi-channel voltage monitoring
  - IN1/IN2 channels
  - PID setpoint readback
  - Configurable sampling rate (0.1-1000 Hz)

- **DAQ_0DViewer_PyRPL_IQ** - Lock-in amplifier
  - I/Q component measurement
  - Magnitude and phase calculation
  - Configurable reference frequency
  - Bandwidth control

- **DAQ_1DViewer_PyRPL_Scope** - Oscilloscope
  - 16,384 samples (2^14 points)
  - Decimation: 125 MHz to 1.9 kHz
  - Multiple trigger modes
  - Averaging support (1-1000)
  - Rolling mode for continuous acquisition

#### Models

- **PIDModelPyRPL** - Direct PID model for PyMoDAQ PID extension
  - Hardware PID bypassing external actuators
  - Minimal latency for critical applications
  - Automatic gain management

## Important Notes

### PyRPL Version Requirements

**Critical:** PyRPL 0.9.6.0 has two bugs that prevent hardware initialization. These must be patched before use.

See [Hardware Testing Guide - PyRPL Bug Fixes](HARDWARE_TESTING.md#pyrpl-bug-fixes) for:
- Detailed bug descriptions
- Fix implementations
- Automated patch script

### Python Compatibility

- **Python 3.8+** supported
- **Python 3.11-3.12** tested and verified
- All Python 3.10+ deprecations handled:
  - `collections.Mapping` → `collections.abc.Mapping`
  - `np.complex` → `np.complex128`
  - Qt timer float/int compatibility

### Qt Compatibility

- **PyQt5** and **PyQt6** both supported
- PyQtGraph compatibility issues resolved
- Qt timer patches applied automatically

## Support & Resources

### Documentation

- This documentation directory (`docs/`)
- Main README: `../README.rst`
- Plugin info: `../plugin_info.toml`

### Code Repository

- **Main:** https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl
- **PyRPL:** https://github.com/pyrpl-fpga/pyrpl
- **PyMoDAQ:** https://github.com/PyMoDAQ/PyMoDAQ

### Community

- **PyMoDAQ Forum:** https://pymodaq.cnrs.fr/
- **Red Pitaya Forum:** https://forum.redpitaya.com/
- **PyRPL Docs:** https://pyrpl.readthedocs.io/

### Issue Tracking

- **Plugin Issues:** GitHub Issues on plugin repository
- **PyRPL Issues:** https://github.com/pyrpl-fpga/pyrpl/issues
- **PyMoDAQ Issues:** https://github.com/PyMoDAQ/PyMoDAQ/issues

## Contributing

See [Developer Guide](DEVELOPER_GUIDE.md) for:
- Code structure and architecture
- Development setup
- Testing procedures
- Contribution guidelines

## Testing Status

### Hardware Validation

**Last Validated:** January 30, 2025

- **Device:** Red Pitaya STEMlab at 100.107.106.75
- **PyRPL:** v0.9.6.0 (with patches)
- **Python:** 3.11.12
- **Status:** All modules functional

See [Hardware Testing Guide](HARDWARE_TESTING.md) for detailed test results.

### Automated Tests

```bash
# Run all tests
pytest tests/

# Mock tests only (no hardware needed)
pytest tests/ -k "not hardware"

# Hardware tests (requires PYRPL_TEST_HOST)
export PYRPL_TEST_HOST=100.107.106.75
pytest tests/ -m hardware
```

## License

MIT License - See `../LICENSE` for details

## Authors

- **PyMoDAQ PyRPL Development Team**
- Contributors: See repository for full list

## Changelog

### Latest (Jan 2025)

- Hardware validation with real Red Pitaya
- PyRPL 0.9.6.0 bug fixes identified and patched
- All 8 hardware modules verified functional
- Comprehensive testing documentation
- Python 3.11/3.12 compatibility confirmed
- Qt6 compatibility verified

### Previous

- Plugin architecture development
- Mock mode implementations
- PyMoDAQ 5.x integration
- Comprehensive test suite
- Documentation framework
