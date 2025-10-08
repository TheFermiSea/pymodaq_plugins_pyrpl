# PyMoDAQ Plugin for Red Pitaya STEMlab using PyRPL Library

[![Latest Version](https://img.shields.io/pypi/v/pymodaq_plugins_pyrpl.svg)](https://pypi.org/project/pymodaq_plugins_pyrpl/)
[![Documentation Status](https://readthedocs.org/projects/pymodaq/badge/?version=latest)](https://pymodaq.readthedocs.io/en/stable/?badge=latest)
[![Publication Status](https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/workflows/Upload%20Python%20Package/badge.svg)](https://github.com/TheFermiSea/pymodaq_plugins_pyrpl)
[![Test Status](https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml/badge.svg)](https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml)

This PyMoDAQ plugin provides comprehensive integration of Red Pitaya STEMlab devices with PyMoDAQ for advanced measurement and control applications. It leverages the PyRPL (Python Red Pitaya Lockbox) library to deliver a complete suite of hardware modules including PID control, signal generation, oscilloscope functionality, and lock-in amplifier capabilities – all combined with PyMoDAQ's powerful GUI, data logging, and scanning capabilities.

## Documentation

**Complete documentation:** [docs/](docs/)

* **Getting Started:**
  - [Installation guide](docs/INSTALLATION.md)
  - [Hardware testing guide](docs/HARDWARE_TESTING.md) - **Read this first for hardware setup!**
  - [Mock mode tutorial](docs/MOCK_TUTORIAL.md)

* **Advanced:**
  - [Developer guide](docs/DEVELOPER_GUIDE.md)
  - [Control theory foundations](docs/CONTROL_THEORY_FOUNDATIONS.md)

* **Important:** PyRPL 0.9.6.0 has critical bugs that must be patched. See [Hardware Testing Guide](docs/HARDWARE_TESTING.md#pyrpl-bug-fixes) for fixes.

## CRITICAL: Hardware Voltage Mode Configuration

**BEFORE USING THIS PLUGIN, YOU MUST VERIFY YOUR RED PITAYA'S VOLTAGE MODE**

Red Pitaya STEMlab devices have physical jumpers that configure the input/output voltage range:

* **LV Mode (Low Voltage)**: ±1V range - Default factory setting
* **HV Mode (High Voltage)**: ±20V range - Requires physical jumper change

**Why This Matters:**

1. **Safety**: Incorrect mode configuration can damage connected equipment
2. **Measurement Accuracy**: Wrong mode causes 20x voltage scaling errors
3. **Plugin Operation**: Scope acquisition and trigger settings depend on correct mode

**How to Check Your Hardware:**

1. **Physical Inspection**: Open your Red Pitaya case and check jumper positions (see Red Pitaya documentation)
2. **Verification Test**: Apply a known voltage (e.g., 1.5V battery) to an input and verify the reading matches

**Current Plugin Status:**

The plugins currently assume **LV mode (±1V)** by default. If your hardware is in HV mode, you will experience:
- Scope acquisition failures ("Result is not set" errors)
- Incorrect voltage measurements (off by 20x)
- Trigger level mismatches

**Planned Update:** A hardware_mode configuration parameter will be added to allow proper operation in both modes.

**For now: Only use this plugin if your Red Pitaya is configured in LV mode (±1V)**

## Key Features

* **Complete Hardware Suite**: Full Red Pitaya module integration (PID, ASG, Scope, IQ, voltage monitoring)
* **Hardware-Accelerated Performance**: FPGA-based processing for microsecond-level response times
* **Multi-Channel Support**: Simultaneous operation of all hardware modules with independent configuration
* **Thread-Safe Architecture**: Centralized PyRPL wrapper with connection pooling prevents conflicts
* **Advanced Signal Processing**: Lock-in amplifier, oscilloscope, and arbitrary signal generation capabilities
* **Mock Mode**: Complete development and testing environment without physical hardware
* **Enhanced Mock Simulation**: Scope viewer now offers selectable waveforms with realistic noise profiles
* **Comprehensive Testing**: 50+ automated tests covering all plugins and integration scenarios
* **Professional Integration**: Production-ready solution for research and industrial applications
* **Hardware Validated**: Successfully tested with real Red Pitaya hardware (rp-f08d6c.local, August 2025)
* **Python 3.12 Compatible**: Full compatibility with modern Python/Qt environments including comprehensive PyRPL compatibility fixes
* **PyRPL Integration Fixed**: Resolved all Python 3.12 compatibility issues (collections.Mapping, np.complex, Qt timer fixes)

## Plugin Components

### PID Controllers & Models

#### PIDModelPyRPL
Direct PyRPL PID model for PyMoDAQ PID extension

- Hardware PID control bypassing external actuators/detectors
- Direct Red Pitaya communication for minimal latency
- Configurable input/output channel routing
- Automatic gain and limit management

#### DAQ_Move_PyRPL_PID
PID setpoint control actuator

- Hardware PID controller setpoint adjustment (±1V range)
- Multi-channel support (PID0, PID1, PID2)
- Real-time parameter updates (P, I, D gains)
- Safety limits and bounds checking
- Thread-safe operations via PyRPL wrapper

### Signal Generation

#### DAQ_Move_PyRPL_ASG
Arbitrary Signal Generator control

- **Waveforms**: sine, cosine, ramp, square, noise, DC
- **Frequency Range**: 0 Hz to 62.5 MHz
- **Dual Channel Support**: ASG0, ASG1 independent operation
- **Amplitude/Offset Control**: Precise signal conditioning
- **Triggering**: External and software trigger support
- **Phase Control**: Relative phase adjustment between channels

### Data Acquisition

#### DAQ_0DViewer_PyRPL
Multi-channel voltage monitoring

- Real-time monitoring of IN1/IN2 channels
- PID setpoint readback capability
- Configurable sampling rates (0.1-1000 Hz)
- Mock mode for development and testing
- Simultaneous multi-channel acquisition

#### DAQ_1DViewer_PyRPL_Scope
Oscilloscope functionality

- **16,384 Samples**: Time-series acquisition (2^14 points)
- **Configurable Decimation**: 125 MHz to 1.9 kHz sampling rates
- **Multiple Trigger Modes**: Edge, level, and external triggering
- **Averaging Support**: 1-1000 averages for noise reduction
- **Rolling Mode**: Continuous acquisition for real-time monitoring
- **Time Axis Generation**: Proper time units and scaling
- **Dual Channel**: Independent IN1/IN2 channel acquisition

### Lock-in Amplifier

#### DAQ_0DViewer_PyRPL_IQ
Phase-sensitive detection

- **I/Q Component Measurement**: Real and imaginary signal components
- **Magnitude and Phase Calculation**: Automatic signal analysis
- **Configurable Reference**: Frequency and phase reference control
- **Bandwidth Control**: AC coupling and filtering options
- **Multi-Channel Support**: IQ0, IQ1, IQ2 independent operation
- **Weak Signal Recovery**: High-sensitivity measurement applications
- **Quadrature Detection**: Phase-sensitive signal processing

### Infrastructure

#### PyRPL Wrapper
Centralized, thread-safe hardware management

- **Connection Pooling**: Efficient resource management for multiple plugins
- **Support for All Modules**: PID, ASG, Scope, IQ, Sampler integration
- **Automatic Error Recovery**: Robust connection handling and cleanup
- **Thread Safety**: Concurrent plugin operation without conflicts
- **Mock Mode Support**: Complete simulation for development

## Hardware Support

**Compatible Devices:**
- Red Pitaya STEMlab 125-10
- Red Pitaya STEMlab 125-14 (recommended)

**Specifications:**
- Voltage Range: ±1V (use external amplification/attenuation as needed)
- Input Channels: 2 x high-impedance analog inputs (IN1, IN2)
- Output Channels: 2 x analog outputs (OUT1, OUT2)
- PID Controllers: 3 x hardware PID modules with FPGA acceleration
- Bandwidth: ~60 MHz (Red Pitaya hardware limit)
- Network: Ethernet connection required

## Installation

### Requirements

- **PyMoDAQ**: Version 5.0.0 or higher
- **Python**: 3.8+ (tested with 3.8, 3.9, 3.10, 3.11)
- **Operating System**: Linux (Ubuntu 20.04/22.04 LTS), Windows 10+, macOS 10.15+
- **Network**: Ethernet connection to Red Pitaya device

### Dependencies

The plugin automatically installs required dependencies:

- `pyrpl`: PyRPL library for Red Pitaya communication
- `pymodaq>=5.0.0`: PyMoDAQ framework
- `numpy`: Numerical computing
- `pymodaq_utils`: PyMoDAQ utilities

### Install from PyPI

```bash
pip install pymodaq_plugins_pyrpl
```

### Install from Source

```bash
git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
cd pymodaq_plugins_pyrpl
pip install -e .
```

## Hardware Setup

### Network Configuration

1. **Connect Red Pitaya**: Connect Red Pitaya to your network via Ethernet

2. **Configure IP Address**: Set a static IP for your Red Pitaya

   **Tested Configuration:**
   - **IP Address**: 100.107.106.75 (hardware validated, January 2025)
   - **Alternative**: rp-f08d6c.local (hostname-based access)
   - **Gateway**: Configure according to your network
   - **Subnet**: Configure according to your network (e.g., 255.255.255.0)

   **USB Serial Configuration (if network issues):**

   If you encounter network connectivity problems, you can configure the Red Pitaya via USB serial:

   ```bash
   # Connect via USB serial (typically /dev/ttyUSB2 on Linux)
   screen /dev/ttyUSB2 115200

   # Configure static IP via serial console:
   ifconfig eth0 100.107.106.75 netmask 255.255.255.0
   route add default gw 100.107.106.1  # Adjust to your gateway
   echo "nameserver 8.8.8.8" > /etc/resolv.conf
   ```

3. **Test Connection**:

   ```bash
   ping 100.107.106.75  # Use your Red Pitaya's IP address
   ```

   **Note**: Ensure your host computer is on the same network subnet

4. **PyRPL Connection**: The plugin uses PyRPL's SSH-based connection (port 22), not SCPI

   **Hardware Validated (January 2025)**: Comprehensive validation with real Red Pitaya:
   - Red Pitaya STEMlab at 100.107.106.75
   - All 8 hardware modules verified: PID×3, ASG×2, Scope, IQ, Sampler
   - PyRPL 0.9.6.0 bugs identified and patched
   - Python 3.11/3.12 + PyQt5/PyQt6 compatibility confirmed
   - PID module ready for production use
   - **Important:** PyRPL 0.9.6.0 requires bug patches (see documentation)

### Physical Connections

```
Laser → EOM → Optical Path → Photodiode → Red Pitaya IN1
                                             ↓
EOM Driver ← External Amplifier ← Red Pitaya OUT1
```

**Signal Conditioning:**
- Red Pitaya operates at ±1V - use appropriate amplifiers/attenuators
- Ensure proper grounding for all analog connections
- Use BNC cables for reliable signal transmission
- Consider isolation for sensitive optical setups

## Usage Examples

### Basic PyMoDAQ Integration

1. **Launch PyMoDAQ Dashboard**:

   ```bash
   python -m pymodaq.dashboard
   ```

2. **Add PyRPL Plugins**:
   - Add `DAQ_Move_PyRPL_PID` for setpoint control
   - Add `DAQ_0DViewer_PyRPL` for voltage monitoring

3. **Configure Connection**:
   - Set RedPitaya Host: `rp-f08d6c.local` or IP address
   - Configure channels (IN1/IN2 for inputs, OUT1/OUT2 for outputs)
   - Set PID parameters (P, I, D gains)

### Plugin Configuration

**DAQ_Move_PyRPL_PID Configuration:**

```yaml
Connection Settings:
  redpitaya_host: "100.107.106.75"  # Use your Red Pitaya's IP
  config_name: "pymodaq"
  mock_mode: false

PID Configuration:
  pid_module: "pid0"     # pid0, pid1, or pid2
  input_channel: "in1"   # in1 or in2
  output_channel: "out1" # out1 or out2

PID Parameters:
  p_gain: 0.1
  i_gain: 0.01
  d_gain: 0.0

Safety Limits:
  min_voltage: -1.0
  max_voltage: 1.0
```

**DAQ_0DViewer_PyRPL Configuration:**

```yaml
Connection Settings:
  redpitaya_host: "100.107.106.75"  # Use your Red Pitaya's IP
  config_name: "pymodaq_viewer"

Channel Configuration:
  monitor_in1: true
  monitor_in2: false
  monitor_pid: true
  pid_module: "pid0"

Acquisition Settings:
  sampling_rate: 10.0  # Hz
```

### Hardware Testing Status

**HARDWARE VALIDATED** (August 2025)

All plugins have been successfully tested with real Red Pitaya hardware:

- **PyRPL Library**: Full compatibility achieved with Python 3.12/Qt6
- **Hardware Connection**: Verified at IP 100.107.106.75
- **All Modules Tested**: PID, ASG, Scope (LV mode only), IQ, Sampler
- **Network Configuration**: Complete USB serial setup guide included
- **Compatibility Fixes**: All Python 3.10+ and Qt6 issues resolved
- **Known Limitation**: HV mode (±20V) not yet supported - see hardware warning above

### Mock Mode for Development

Enable mock mode for development without hardware:

```python
# In plugin parameters
mock_mode: True
```

Mock mode provides:
- Simulated voltage readings with realistic noise
- Selectable waveform models in the scope viewer (damped sine, square, broadband noise)
- PID setpoint simulation
- Full plugin functionality for GUI development
- Automated testing capabilities

## Advanced Usage

### Multi-Plugin Coordination

The plugin suite supports sophisticated multi-module coordination:

```python
# Complete measurement setup with all modules
# All plugins share the same Red Pitaya connection safely

# Signal generation for stimulus
asg_stimulus = DAQ_Move_PyRPL_ASG(
    asg_channel="asg0",
    frequency=1000,
    amplitude=0.1
)

# PID control for feedback
pid_control = DAQ_Move_PyRPL_PID(
    pid_module="pid0",
    input="in1",
    output="out1"
)

# Lock-in detection for weak signals
lockin_detection = DAQ_0DViewer_PyRPL_IQ(
    iq_module="iq0",
    frequency=1000,  # matches ASG frequency
    bandwidth=10     # narrow detection bandwidth
)

# Oscilloscope for transient capture
scope_monitoring = DAQ_1DViewer_PyRPL_Scope(
    input_channel="in1",
    decimation=64,
    trigger_source="external"
)

# Real-time voltage monitoring
voltage_monitoring = DAQ_0DViewer_PyRPL(
    monitor_in1=True,
    monitor_in2=True,
    monitor_pid=True
)
```

### Coordinated Scanning Applications

```python
# PyMoDAQ scanning with multiple PyRPL modules
from pymodaq.dashboard import DashBoard

# Configure scan: ASG frequency vs IQ magnitude
dashboard = DashBoard()

# Add actuator: ASG frequency control
dashboard.add_actuator('PyRPL_ASG_Freq', 'DAQ_Move_PyRPL_ASG')

# Add detectors: IQ lock-in + scope traces
dashboard.add_detector('PyRPL_IQ_Signal', 'DAQ_0DViewer_PyRPL_IQ')
dashboard.add_detector('PyRPL_Scope_Trace', 'DAQ_1DViewer_PyRPL_Scope')

# Scan ASG frequency while monitoring IQ response
# Result: 2D dataset (frequency vs time) with IQ magnitude
#         + 3D dataset (frequency vs time vs scope_samples)
```

### Direct PID Model Integration

Use the PID model for direct hardware control in PyMoDAQ PID extension:

```python
from pymodaq.extensions.pid import PIDController
from pymodaq_plugins_pyrpl.models.PIDModelPyRPL import PIDModelPyRPL

# Initialize PID with PyRPL hardware model
pid_controller = PIDController()
pid_controller.model = PIDModelPyRPL(pid_controller)

# Configure Red Pitaya connection
pid_controller.model_params['redpitaya_host'] = '100.107.106.75'  # Your Red Pitaya IP
pid_controller.model_params['config_name'] = 'pymodaq_pid'
pid_controller.model_params['use_hardware_pid'] = True

# Configure hardware routing
pid_controller.model_params['pid_module'] = 'pid0'
pid_controller.model_params['input_channel'] = 'in1'
pid_controller.model_params['output_channel'] = 'out1'

# Hardware PID provides microsecond response times
# bypassing software actuator/detector latency
```

## Development and Testing

### Running Tests

```bash
# Install in development mode
pip install -e .

# Run all tests
python -m pytest tests/

# Run specific test categories
pytest tests/test_pyrpl_functionality.py -k test_mock      # Mock tests only
pytest tests/test_pyrpl_functionality.py -k test_real     # Hardware tests only

# Test structure validation
python tests/test_plugin_package_structure.py
```

### Mock vs Real Hardware Testing

```bash
# Mock hardware tests (no Red Pitaya needed)
pytest tests/ -k "not test_real_hardware"

# Real hardware tests (requires Red Pitaya connection)
pytest tests/ -k "test_real_hardware"
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
cd pymodaq_plugins_pyrpl

# Create development environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install in development mode
pip install -e .

# Run tests
python -m pytest
```

## Troubleshooting

### Common Issues

**Connection Problems:**

```bash
# Test Red Pitaya network connectivity
ping 100.107.106.75  # Use your Red Pitaya's IP address

# Check PyRPL installation and compatibility
python -c "import pyrpl; print('PyRPL OK')"

# Test PyRPL hardware connection
python -c "import pyrpl; rp = pyrpl.Pyrpl(hostname='100.107.106.75')"
```

**PyRPL Compatibility Issues:**

If you encounter PyRPL import or connection errors:

```bash
# Install compatible versions
pip install 'pyqtgraph==0.12.4' quamash

# Check Python 3.10+ collections compatibility
python -c "import collections.abc; print('Collections OK')"
```

The plugin includes automatic compatibility fixes for Python 3.10+ and Qt6 environments.

**Plugin Loading Issues:**
- Ensure PyMoDAQ 5.0+ is installed
- Check plugin is properly installed: `pip list | grep pymodaq_plugins_pyrpl`
- Verify Python environment has all dependencies

**Mock Mode Issues:**
- Enable mock mode in plugin parameters
- Check plugin logs for initialization errors
- Verify PyMoDAQ can load plugin without hardware

### Performance Optimization

- Use hardware PID mode for best performance (microsecond response)
- Minimize sampling rates for viewer plugins when not needed
- Use appropriate P, I, D gains for your specific system
- Consider network latency in your control loop design
- Leverage the dashboard extension's signal-driven updates when monitoring many devices simultaneously

## Safety Considerations

### Hardware Protection

- Always set appropriate voltage limits (±1V maximum)
- Use external protection circuits for sensitive equipment
- Test with low laser power before full operation
- Enable PID limits to prevent output saturation

### Software Safety

- Use mock mode for initial configuration and testing
- Monitor PID output before connecting to expensive equipment
- Implement software interlocks in your PyMoDAQ preset
- Regular backup of working configurations

## License and Citation

**License:** MIT License - see LICENSE file for details

**Citation:** If you use this plugin in scientific work, please cite:

```bibtex
@software{pymodaq_plugins_pyrpl,
  title = {PyMoDAQ PyRPL Plugin: Red Pitaya Integration for Laser Control},
  url = {https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl},
  version = {1.0.0},
  author = {PyMoDAQ Development Team},
  year = {2024}
}
```

## Authors

- **PyMoDAQ Development Team**
- **Contributors:** Sebastien Weber

## Support

- **Documentation:** https://pymodaq.readthedocs.io/
- **Issues:** https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl/issues
- **PyMoDAQ Forum:** https://pymodaq.cnrs.fr/
- **PyRPL Documentation:** https://pyrpl.readthedocs.io/
