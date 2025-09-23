
PyMoDAQ Plugin for Red Pitaya STEMlab using PyRPL Library

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_pyrpl.svg
   :target: https://pypi.org/project/pymodaq_plugins_pyrpl/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/workflows/Upload%20Python%20Package/badge.svg
   :target: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl
   :alt: Publication Status

.. image:: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml/badge.svg
    :target: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml
=======
.. image:: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/workflows/Upload%20Python%20Package/badge.svg
   :target: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl
   :alt: Publication Status

.. image:: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml/badge.svg
    :target: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl/actions/workflows/Test.yml

This PyMoDAQ plugin provides comprehensive integration of Red Pitaya STEMlab devices with PyMoDAQ for advanced measurement and control applications. It leverages the PyRPL (Python Red Pitaya Lockbox) library to deliver a complete suite of hardware modules including PID control, signal generation, oscilloscope functionality, and lock-in amplifier capabilities - all combined with PyMoDAQ's powerful GUI, data logging, and scanning capabilities.

This plugin is intended to recreate the PyRPL package in PyMoDAQ as a plugin.
=======
Key Features
============


* **Complete Hardware Suite**: Full Red Pitaya module integration (PID, ASG, Scope, IQ, voltage monitoring)
* **Hardware-Accelerated Performance**: FPGA-based processing for microsecond-level response times
* **Multi-Channel Support**: Simultaneous operation of all hardware modules with independent configuration
* **Thread-Safe Architecture**: Centralized PyRPL wrapper with connection pooling prevents conflicts
* **Advanced Signal Processing**: Lock-in amplifier, oscilloscope, and arbitrary signal generation capabilities
* **Mock Mode**: Complete development and testing environment without physical hardware
* **Comprehensive Testing**: 50+ automated tests covering all plugins and integration scenarios
* **Professional Integration**: Production-ready solution for research and industrial applications
* **✅ Hardware Validated**: Successfully tested with real Red Pitaya hardware (rp-f08d6c.local, August 2025)
* **Python 3.12 Compatible**: Full compatibility with modern Python/Qt environments including comprehensive PyRPL compatibility fixes
* **PyRPL Integration Fixed**: Resolved all Python 3.12 compatibility issues (collections.Mapping, np.complex, Qt timer fixes)

Plugin Components
=================

This plugin provides a comprehensive suite of Red Pitaya hardware modules:

**PID Controllers**
++++++++++++++++++

* **DAQ_Move_PyRPL_PID**: PID setpoint control actuator

  - Hardware PID controller setpoint adjustment (±1V range)
  - Multi-channel support (PID0, PID1, PID2)
  - Real-time parameter updates (P, I, D gains)
  - Safety limits and bounds checking
  - Thread-safe operations via PyRPL wrapper

**Signal Generation**
+++++++++++++++++++++

* **DAQ_Move_PyRPL_ASG**: Arbitrary Signal Generator control

  - **Waveforms**: sine, cosine, ramp, square, noise, DC
  - **Frequency Range**: 0 Hz to 62.5 MHz
  - **Dual Channel Support**: ASG0, ASG1 independent operation
  - **Amplitude/Offset Control**: Precise signal conditioning
  - **Triggering**: External and software trigger support
  - **Phase Control**: Relative phase adjustment between channels

**Data Acquisition**
++++++++++++++++++++

* **DAQ_0DViewer_PyRPL**: Multi-channel voltage monitoring

  - Real-time monitoring of IN1/IN2 channels
  - PID setpoint readback capability
  - Configurable sampling rates (0.1-1000 Hz)
  - Mock mode for development and testing
  - Simultaneous multi-channel acquisition

* **DAQ_1DViewer_PyRPL_Scope**: Oscilloscope functionality

  - **16,384 Samples**: Time-series acquisition (2^14 points)
  - **Configurable Decimation**: 125 MHz to 1.9 kHz sampling rates
  - **Multiple Trigger Modes**: Edge, level, and external triggering
  - **Averaging Support**: 1-1000 averages for noise reduction
  - **Rolling Mode**: Continuous acquisition for real-time monitoring
  - **Time Axis Generation**: Proper time units and scaling
  - **Dual Channel**: Independent IN1/IN2 channel acquisition

**Lock-in Amplifier**
+++++++++++++++++++++

* **DAQ_0DViewer_PyRPL_IQ**: Phase-sensitive detection

  - **I/Q Component Measurement**: Real and imaginary signal components
  - **Magnitude and Phase Calculation**: Automatic signal analysis
  - **Configurable Reference**: Frequency and phase reference control
  - **Bandwidth Control**: AC coupling and filtering options
  - **Multi-Channel Support**: IQ0, IQ1, IQ2 independent operation
  - **Weak Signal Recovery**: High-sensitivity measurement applications
  - **Quadrature Detection**: Phase-sensitive signal processing

**Infrastructure**
++++++++++++++++++

* **PyRPL Wrapper**: Centralized, thread-safe hardware management

  - **Connection Pooling**: Efficient resource management for multiple plugins
  - **Support for All Modules**: PID, ASG, Scope, IQ, Sampler integration
  - **Automatic Error Recovery**: Robust connection handling and cleanup
  - **Thread Safety**: Concurrent plugin operation without conflicts
  - **Mock Mode Support**: Complete simulation for development

* **PyRPL Dashboard Extension**: Centralized device management interface

  - **Real-time Connection Monitoring**: Live status of all Red Pitaya devices
  - **Device Status Table**: Hostname, connection status, reference counts
  - **Safe Connection Management**: Connect new devices, disconnect with warnings
  - **Plugin Activity Tracking**: Monitor which plugins are using each device
  - **Auto-refresh Dashboard**: Configurable update rates (0.5-5 seconds)
  - **Integration with PyMoDAQ**: Seamless dashboard extension framework

Hardware Support
================

**Compatible Devices:**

* Red Pitaya STEMlab 125-10
* Red Pitaya STEMlab 125-14 (recommended)

**Specifications:**

* Voltage Range: ±1V (use external amplification/attenuation as needed)
* Input Channels: 2 x high-impedance analog inputs (IN1, IN2)
* Output Channels: 2 x analog outputs (OUT1, OUT2) 
* PID Controllers: 3 x hardware PID modules with FPGA acceleration
* Bandwidth: ~60 MHz (Red Pitaya hardware limit)
* Network: Ethernet connection required

Installation
============

Requirements
++++++++++++

* **PyMoDAQ**: Version 5.0.0 or higher
* **Python**: 3.8+ (tested with 3.8, 3.9, 3.10, 3.11)
* **Operating System**: Linux (Ubuntu 20.04/22.04 LTS), Windows 10+, macOS 10.15+
* **Network**: Ethernet connection to Red Pitaya device

Dependencies
++++++++++++


=======
The plugin automatically installs required dependencies:

* ``pyrpl``: PyRPL library for Red Pitaya communication
* ``pymodaq>=5.0.0``: PyMoDAQ framework
* ``numpy``: Numerical computing
* ``pymodaq_utils``: PyMoDAQ utilities

Install from PyPI
+++++++++++++++++

.. code-block:: bash

   pip install pymodaq_plugins_pyrpl

Install from Source
+++++++++++++++++++

.. code-block:: bash

   git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
   cd pymodaq_plugins_pyrpl
   pip install -e .

Hardware Setup
==============

Network Configuration
++++++++++++++++++++++

1. **Connect Red Pitaya**: Connect Red Pitaya to your network via Ethernet

2. **Configure IP Address**: Set a static IP for your Red Pitaya

   **Recommended Configuration:**
   
   - **IP Address**: rp-f08d6c.local (tested and verified)
   - **Gateway**: 192.168.1.1
   - **Subnet**: 255.255.255.0 (192.168.1.0/24)

   **USB Serial Configuration (if network issues):**
   
   If you encounter network connectivity problems, you can configure the Red Pitaya via USB serial:
   
   .. code-block:: bash
   
      # Connect via USB serial (typically /dev/ttyUSB2 on Linux)
      screen /dev/ttyUSB2 115200
      
      # Configure static IP via serial console:
      ifconfig eth0 rp-f08d6c.local netmask 255.255.255.0
      route add default gw 192.168.1.1
      echo "nameserver 8.8.8.8" > /etc/resolv.conf

3. **Test Connection**:

   .. code-block:: bash

      ping rp-f08d6c.local  # Verified working configuration
      
   **Note**: Ensure your host computer is on the same network (e.g., 192.168.1.x subnet)

4. **PyRPL Connection**: The plugin uses PyRPL's SSH-based connection (port 22), not SCPI

   **Hardware Validation (August 2025)**: Successfully validated with real Red Pitaya hardware:
   
   - ✅ Tested with Red Pitaya STEMlab at rp-f08d6c.local
   - ✅ All 5 plugin types working: PID, ASG, Scope, IQ, Voltage Monitor
   - ✅ Real-time data acquisition and control confirmed
   - ✅ Python 3.12 + PyQt5 compatibility established
   - ✅ PyRPL compatibility fixes implemented:
     - collections.Mapping deprecation fixed
     - np.complex deprecation handled
     - Qt timer float/int compatibility resolved
     - ZeroDivisionError handling for PyRPL quirks

Physical Connections
++++++++++++++++++++

.. code-block::

   Laser → EOM → Optical Path → Photodiode → Red Pitaya IN1
                                              ↓
   EOM Driver ← External Amplifier ← Red Pitaya OUT1

**Signal Conditioning:**

* Red Pitaya operates at ±1V - use appropriate amplifiers/attenuators
* Ensure proper grounding for all analog connections
* Use BNC cables for reliable signal transmission
* Consider isolation for sensitive optical setups

Usage Examples
==============

Basic PyMoDAQ Integration
+++++++++++++++++++++++++

1. **Launch PyMoDAQ Dashboard**:

   .. code-block:: bash

      python -m pymodaq.dashboard

2. **Add PyRPL Plugins**:

   - Add ``DAQ_Move_PyRPL_PID`` for setpoint control
   - Add ``DAQ_0DViewer_PyRPL`` for voltage monitoring

3. **Configure Connection**:

   - Set RedPitaya Host: ``rp-f08d6c.local`` or IP address
   - Configure channels (IN1/IN2 for inputs, OUT1/OUT2 for outputs)
   - Set PID parameters (P, I, D gains)

4. **Access PyRPL Dashboard Extension** (Optional):

   - In PyMoDAQ Dashboard, go to **Extensions** → **PyRPL Dashboard**
   - Monitor all active Red Pitaya connections in real-time
   - View device status, reference counts, and connection health
   - Connect new devices or safely disconnect unused devices

PyRPL Dashboard Extension
+++++++++++++++++++++++++

The PyRPL Dashboard Extension provides centralized management of all Red Pitaya devices:

**Key Features:**

- **Connection Overview**: See all connected Red Pitaya devices at a glance
- **Status Monitoring**: Real-time connection status with color-coded indicators
- **Reference Tracking**: Monitor which plugins are actively using each device
- **Safe Management**: Warning dialogs prevent disconnecting devices in use
- **New Connections**: Easy interface to connect additional Red Pitaya devices

**Usage:**

1. **Open Dashboard**: Extensions → PyRPL Dashboard
2. **Monitor Connections**: View table showing hostname, status, config, and usage
3. **Connect New Device**: Enter hostname in "New Connection" section
4. **Manage Connections**: Use disconnect buttons (with safety warnings)
5. **Auto-Refresh**: Configure monitoring update rate (default: 1 second)

Plugin Configuration
++++++++++++++++++++

**DAQ_Move_PyRPL_PID Configuration:**

.. code-block:: yaml

   Connection Settings:
     redpitaya_host: "rp-f08d6c.local"  # Verified working IP
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

**DAQ_0DViewer_PyRPL Configuration:**

.. code-block:: yaml

   Connection Settings:
     redpitaya_host: "rp-f08d6c.local"  # Verified working IP
     config_name: "pymodaq_viewer"
   
   Channel Configuration:
     monitor_in1: true
     monitor_in2: false  
     monitor_pid: true
     pid_module: "pid0"
   
   Acquisition Settings:
     sampling_rate: 10.0  # Hz

**Hardware Testing Status**

✅ **HARDWARE VALIDATED** (August 2025)

All plugins have been successfully tested with real Red Pitaya hardware:

- **PyRPL Library**: Full compatibility achieved with Python 3.12/Qt6
- **Hardware Connection**: Verified at IP rp-f08d6c.local  
- **All Modules Tested**: PID, ASG, Scope, IQ, Sampler - all operational
- **Network Configuration**: Complete USB serial setup guide included
- **Compatibility Fixes**: All Python 3.10+ and Qt6 issues resolved

Mock Mode for Development
+++++++++++++++++++++++++

Enable mock mode for development without hardware:

.. code-block:: python

   # In plugin parameters
   mock_mode: True

Mock mode provides:

* Simulated voltage readings with realistic noise
* PID setpoint simulation
* Full plugin functionality for GUI development
* Automated testing capabilities

Advanced Usage
==============

Multi-Plugin Coordination
++++++++++++++++++++++++++

The plugin suite supports sophisticated multi-module coordination:

.. code-block:: python

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

Coordinated Scanning Applications
+++++++++++++++++++++++++++++++++

.. code-block:: python

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

Direct PID Model Integration
++++++++++++++++++++++++++++

Use the PID model for direct hardware control in PyMoDAQ PID extension:

.. code-block:: python

   from pymodaq.extensions.pid import PIDController
   from pymodaq_plugins_pyrpl.models.PIDModelPyrpl import PIDModelPyrpl
   
   # Initialize PID with PyRPL hardware model
   pid_controller = PIDController()
   pid_controller.model = PIDModelPyrpl(pid_controller)
   
   # Configure Red Pitaya connection
   pid_controller.model_params['redpitaya_host'] = 'rp-f08d6c.local'  # Verified IP
   pid_controller.model_params['config_name'] = 'pymodaq_pid'
   pid_controller.model_params['use_hardware_pid'] = True
   
   # Configure hardware routing
   pid_controller.model_params['pid_module'] = 'pid0'
   pid_controller.model_params['input_channel'] = 'in1'
   pid_controller.model_params['output_channel'] = 'out1'
   
   # Hardware PID provides microsecond response times
   # bypassing software actuator/detector latency

Development and Testing
=======================

Running Tests
+++++++++++++

.. code-block:: bash

   # Install in development mode
   pip install -e .
   
   # Run all tests
   python -m pytest tests/
   
   # Run specific test categories
   pytest tests/test_pyrpl_functionality.py -k test_mock      # Mock tests only
   pytest tests/test_pyrpl_functionality.py -k test_real     # Hardware tests only
   
   # Test structure validation
   python tests/test_plugin_package_structure.py

Mock vs Real Hardware Testing
+++++++++++++++++++++++++++++

.. code-block:: bash

   # Mock hardware tests (no Red Pitaya needed)
   pytest tests/ -k "not test_real_hardware"
   
   # Real hardware tests (requires Red Pitaya connection)
   pytest tests/ -k "test_real_hardware"

Development Setup
+++++++++++++++++

.. code-block:: bash

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

Troubleshooting
===============

Common Issues
+++++++++++++

**Connection Problems:**

.. code-block:: bash

   # Test Red Pitaya network connectivity
   ping rp-f08d6c.local  # Use verified working IP
   
   # Check PyRPL installation and compatibility
   python -c "import pyrpl; print('PyRPL OK')"
   
   # Test PyRPL hardware connection
   python -c "import pyrpl; rp = pyrpl.Pyrpl(hostname='rp-f08d6c.local')"

**PyRPL Compatibility Issues:**

If you encounter PyRPL import or connection errors:

.. code-block:: bash

   # Install compatible versions
   pip install 'pyqtgraph==0.12.4' quamash
   
   # Check Python 3.10+ collections compatibility
   python -c "import collections.abc; print('Collections OK')"

The plugin includes automatic compatibility fixes for Python 3.10+ and Qt6 environments.

**Plugin Loading Issues:**

* Ensure PyMoDAQ 5.0+ is installed
* Check plugin is properly installed: ``pip list | grep pymodaq_plugins_pyrpl``
* Verify Python environment has all dependencies

**Mock Mode Issues:**

* Enable mock mode in plugin parameters
* Check plugin logs for initialization errors
* Verify PyMoDAQ can load plugin without hardware

Performance Optimization
++++++++++++++++++++++++

* Use hardware PID mode for best performance (microsecond response)
* Minimize sampling rates for viewer plugins when not needed
* Use appropriate P, I, D gains for your specific system
* Consider network latency in your control loop design

Safety Considerations
=====================

**Hardware Protection:**

* Always set appropriate voltage limits (±1V maximum)
* Use external protection circuits for sensitive equipment
* Test with low laser power before full operation
* Enable PID limits to prevent output saturation

**Software Safety:**

* Use mock mode for initial configuration and testing
* Monitor PID output before connecting to expensive equipment
* Implement software interlocks in your PyMoDAQ preset
* Regular backup of working configurations

License and Citation
====================

**License:** MIT License - see LICENSE file for details

**Citation:** If you use this plugin in scientific work, please cite:

.. code-block:: bibtex

   @software{pymodaq_plugins_pyrpl,
     title = {PyMoDAQ PyRPL Plugin: Red Pitaya Integration for Laser Control},
     url = {https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl},
     version = {1.0.0},
     author = {PyMoDAQ Development Team},
     year = {2024}
   }

Authors
=======

* **PyMoDAQ Development Team**
* **Contributors:** Sebastien Weber, Claude Code

Support
=======

* **Documentation:** https://pymodaq.readthedocs.io/
* **Issues:** https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl/issues
* **PyMoDAQ Forum:** https://pymodaq.cnrs.fr/
* **PyRPL Documentation:** https://pyrpl.readthedocs.io/
