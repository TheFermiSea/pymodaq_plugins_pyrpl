# -*- coding: utf-8 -*-
"""
PyMoDAQ Detector Plugin for Red Pitaya PyRPL IQ Lock-in Amplifier

This plugin provides phase-sensitive detection capabilities using Red Pitaya's
IQ (lock-in amplifier) modules for weak signal recovery and phase measurements.
It supports real-time I/Q measurements with configurable reference frequency,
bandwidth, and phase settings for advanced spectroscopy applications.

Features:
    - Lock-in amplifier functionality (I, Q, magnitude, phase measurements)
    - Multi-channel IQ monitoring (IQ0, IQ1, IQ2)
    - Configurable reference frequency, bandwidth, and phase
    - Real-time magnitude and phase calculations
    - AC bandwidth control for input filtering
    - Quadrature factor adjustment for detection modes
    - Output signal routing capabilities
    - Thread-safe PyRPL wrapper integration
    - Mock mode for development without hardware

Compatible Hardware:
    - Red Pitaya STEMlab 125-10/125-14
    - PyRPL firmware and library with IQ module support

Tested Configuration:
    - PyMoDAQ 5.0+
    - PyRPL 0.9.5+
    - Red Pitaya STEMlab 125-14
    - Ubuntu 20.04/22.04 LTS

Installation Requirements:
    - PyRPL library: `pip install pyrpl`
    - Red Pitaya network connection and PyRPL firmware
    - Proper network configuration (see documentation)

Usage:
    1. Configure Red Pitaya hostname/IP in plugin parameters
    2. Select IQ module (IQ0, IQ1, or IQ2) and input channel
    3. Set lock-in parameters (frequency, bandwidth, phase, gain)
    4. Choose which measurements to acquire (I, Q, magnitude, phase)
    5. Initialize detector to establish connection
    6. Start continuous acquisition for real-time lock-in measurements

Use Cases:
    - Weak signal detection and recovery
    - Phase-sensitive measurements
    - Spectroscopy applications
    - Noise reduction in measurements
    - Cavity locking applications
    - Integration with scanning (lock-in signals vs scan parameter)

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

import time
import numpy as np
from typing import Optional, Dict, List, Union, Tuple
import logging

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base, comon_parameters, main
)
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from pymodaq_data.data import DataToExport
from pymodaq_data import DataRaw, Axis

# Import PyRPL wrapper utilities
from ...utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, IQChannel, InputChannel,
    IQConfiguration, IQOutputDirect, ConnectionState
)

logger = logging.getLogger(__name__)


class MockIQMeasurement:
    """Mock IQ measurement for development without hardware."""

    def __init__(self, frequency: float = 1000.0, phase_offset: float = 0.0):
        self.frequency = frequency
        self.phase_offset = phase_offset
        self.time_start = time.time()

    def get_iq_values(self) -> Tuple[float, float]:
        """Generate realistic I/Q values with time-varying signal."""
        current_time = time.time() - self.time_start

        # Simulate a weak signal with noise
        signal_amplitude = 0.1  # 100mV signal amplitude
        noise_level = 0.005  # 5mV noise

        # Main signal component
        phase = 2 * np.pi * self.frequency * current_time + np.radians(self.phase_offset)
        signal_i = signal_amplitude * np.cos(phase)
        signal_q = signal_amplitude * np.sin(phase)

        # Add noise
        noise_i = np.random.normal(0, noise_level)
        noise_q = np.random.normal(0, noise_level)

        # Add slow drift (simulates real experimental conditions)
        drift_i = 0.01 * np.sin(0.1 * current_time)
        drift_q = 0.01 * np.cos(0.15 * current_time)

        i_total = signal_i + noise_i + drift_i
        q_total = signal_q + noise_q + drift_q

        return i_total, q_total


class MockPyRPLConnection:
    """Mock connection for development without hardware."""

    def __init__(self, hostname: str):
        self.hostname = hostname
        self.is_connected = True
        self.state = ConnectionState.CONNECTED
        self._iq_measurements: Dict[IQChannel, MockIQMeasurement] = {}

    def configure_iq(self, channel: IQChannel, config: IQConfiguration) -> bool:
        """Mock IQ configuration."""
        self._iq_measurements[channel] = MockIQMeasurement(
            frequency=config.frequency,
            phase_offset=config.phase
        )
        return True

    def get_iq_measurement(self, channel: IQChannel) -> Optional[Tuple[float, float]]:
        """Return mock I/Q measurements."""
        if channel not in self._iq_measurements:
            self._iq_measurements[channel] = MockIQMeasurement()
        return self._iq_measurements[channel].get_iq_values()

    def calculate_magnitude_phase(self, i: float, q: float) -> Tuple[float, float]:
        """Calculate magnitude and phase from I and Q components."""
        magnitude = np.sqrt(i**2 + q**2)
        phase_radians = np.arctan2(q, i)
        phase_degrees = np.degrees(phase_radians)
        return magnitude, phase_degrees

    def set_iq_frequency(self, channel: IQChannel, frequency: float) -> bool:
        """Mock frequency setting."""
        if channel in self._iq_measurements:
            self._iq_measurements[channel].frequency = frequency
        return True

    def disconnect(self, status_callback=None):
        """Mock disconnect."""
        self.is_connected = False


class DAQ_0DViewer_PyRPL_IQ(DAQ_Viewer_base):
    """
    PyMoDAQ 0D Viewer Plugin for Red Pitaya PyRPL IQ Lock-in Amplifier.

    This detector plugin enables phase-sensitive detection using Red Pitaya's
    IQ lock-in amplifier modules. It provides real-time I, Q, magnitude, and
    phase measurements for weak signal recovery applications in spectroscopy,
    laser stabilization, and precision measurements.

    The plugin supports multi-channel IQ monitoring with configurable reference
    frequency, bandwidth, and phase settings, integrating seamlessly with
    PyMoDAQ's data acquisition framework for logging, plotting, and scanning.

    Attributes:
        controller: PyRPLConnection instance for hardware communication
        pyrpl_manager: Singleton manager for PyRPL connections
        last_acquisition_time: Timestamp of last data acquisition
        iq_config: Current IQ configuration parameters
    """

    params = comon_parameters + [
        {
            'title': 'Connection Settings:',
            'name': 'connection',
            'type': 'group',
            'children': [
                {
                    'title': 'RedPitaya Host:',
                    'name': 'redpitaya_host',
                    'type': 'str',
                    'value': 'rp-f08d6c.local',
                    'tip': 'Hostname or IP address of Red Pitaya device'
                },
                {
                    'title': 'Config Name:',
                    'name': 'config_name',
                    'type': 'str',
                    'value': 'pymodaq_iq',
                    'tip': 'PyRPL configuration name for this connection'
                },
                {
                    'title': 'Connection Timeout (s):',
                    'name': 'connection_timeout',
                    'type': 'float',
                    'value': 10.0,
                    'min': 1.0,
                    'max': 60.0,
                    'tip': 'Timeout for establishing connection'
                },
                {
                    'title': 'Mock Mode:',
                    'name': 'mock_mode',
                    'type': 'bool',
                    'value': False,
                    'tip': 'Enable mock mode for development without hardware'
                }
            ]
        },
        {
            'title': 'IQ Module Settings:',
            'name': 'iq_settings',
            'type': 'group',
            'children': [
                {
                    'title': 'IQ Module:',
                    'name': 'iq_module',
                    'type': 'list',
                    'limits': ['iq0', 'iq1', 'iq2'],
                    'value': 'iq0',
                    'tip': 'IQ lock-in amplifier module to use'
                },
                {
                    'title': 'Input Channel:',
                    'name': 'input_channel',
                    'type': 'list',
                    'limits': ['in1', 'in2'],
                    'value': 'in1',
                    'tip': 'Analog input channel for signal'
                }
            ]
        },
        {
            'title': 'Lock-in Settings:',
            'name': 'lockin_group',
            'type': 'group',
            'children': [
                {
                    'title': 'Frequency (Hz):',
                    'name': 'frequency',
                    'type': 'float',
                    'value': 1000.0,
                    'min': 0.1,
                    'max': 62.5e6,
                    'tip': 'Reference frequency for lock-in detection'
                },
                {
                    'title': 'Bandwidth (Hz):',
                    'name': 'bandwidth',
                    'type': 'float',
                    'value': 100.0,
                    'min': 0.01,
                    'max': 62.5e6,
                    'tip': 'Lock-in amplifier bandwidth'
                },
                {
                    'title': 'AC Bandwidth (Hz):',
                    'name': 'acbandwidth',
                    'type': 'float',
                    'value': 10000.0,
                    'min': 0,
                    'max': 62.5e6,
                    'tip': 'AC bandwidth for input filtering'
                },
                {
                    'title': 'Phase (degrees):',
                    'name': 'phase',
                    'type': 'float',
                    'value': 0.0,
                    'min': -180,
                    'max': 180,
                    'tip': 'Phase offset for lock-in detection'
                },
                {
                    'title': 'Gain:',
                    'name': 'gain',
                    'type': 'float',
                    'value': 1.0,
                    'min': 0.001,
                    'max': 1000.0,
                    'tip': 'Amplification gain'
                }
            ]
        },
        {
            'title': 'Output Settings:',
            'name': 'output_group',
            'type': 'group',
            'children': [
                {
                    'title': 'Quadrature Factor:',
                    'name': 'quadrature_factor',
                    'type': 'float',
                    'value': 1.0,
                    'min': -10.0,
                    'max': 10.0,
                    'tip': 'Quadrature signal factor for different detection modes'
                },
                {
                    'title': 'Amplitude:',
                    'name': 'amplitude',
                    'type': 'float',
                    'value': 0.0,
                    'min': -1.0,
                    'max': 1.0,
                    'tip': 'Output amplitude (V)'
                },
                {
                    'title': 'Output Direct:',
                    'name': 'output_direct',
                    'type': 'list',
                    'limits': ['off', 'out1', 'out2'],
                    'value': 'off',
                    'tip': 'Direct output routing'
                }
            ]
        },
        {
            'title': 'Measurement Channels:',
            'name': 'channels_group',
            'type': 'group',
            'children': [
                {
                    'title': 'Measure I (In-phase):',
                    'name': 'measure_i',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Measure in-phase component'
                },
                {
                    'title': 'Measure Q (Quadrature):',
                    'name': 'measure_q',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Measure quadrature component'
                },
                {
                    'title': 'Measure Magnitude:',
                    'name': 'measure_magnitude',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Calculate and measure magnitude = sqrt(I² + Q²)'
                },
                {
                    'title': 'Measure Phase:',
                    'name': 'measure_phase',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Calculate and measure phase = atan2(Q, I)'
                }
            ]
        },
        {
            'title': 'Acquisition Settings:',
            'name': 'acquisition',
            'type': 'group',
            'children': [
                {
                    'title': 'Sampling Rate (Hz):',
                    'name': 'sampling_rate',
                    'type': 'float',
                    'value': 10.0,
                    'min': 0.1,
                    'max': 1000.0,
                    'tip': 'Data acquisition sampling rate'
                },
                {
                    'title': 'Max Acquisition Time (s):',
                    'name': 'max_acq_time',
                    'type': 'float',
                    'value': 0.1,
                    'min': 0.001,
                    'max': 1.0,
                    'tip': 'Maximum time allowed for data acquisition'
                }
            ]
        }
    ]

    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller: Optional[Union[PyRPLConnection, MockPyRPLConnection]] = None
        self.pyrpl_manager: Optional[PyRPLManager] = None
        self.last_acquisition_time: float = 0.0

        # IQ configuration
        self.iq_config: Optional[IQConfiguration] = None
        self.current_iq_channel: Optional[IQChannel] = None

        # Channel configuration
        self.active_channels: List[str] = []
        self.channel_data: Dict[str, float] = {}

    def commit_settings(self, param: Parameter):
        """
        Apply consequences of parameter changes.

        This method handles real-time parameter updates, particularly for
        IQ configuration changes that require hardware reconfiguration.

        Parameters:
            param: Parameter that was modified
        """
        param_name = param.name()
        param_path = param.path()

        logger.debug(f"Committing parameter change: {param_path}")

        # Handle channel configuration changes
        if param_name in ['measure_i', 'measure_q', 'measure_magnitude', 'measure_phase']:
            self._update_active_channels()
            logger.info(f"Updated active channels: {self.active_channels}")

        # Handle IQ module or input channel changes (require reconfiguration)
        elif param_name in ['iq_module', 'input_channel']:
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected:
                    self._reconfigure_iq_module()

        # Handle lock-in parameter changes (update hardware immediately if connected)
        elif param_name in ['frequency', 'bandwidth', 'acbandwidth', 'phase', 'gain',
                           'quadrature_factor', 'amplitude', 'output_direct']:
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected and self.current_iq_channel is not None:
                    self._update_iq_parameters()

        # Handle connection parameter changes
        elif param_name in ['redpitaya_host', 'config_name', 'mock_mode']:
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected:
                    self.emit_status(ThreadCommand('Update_Status',
                        ['Connection parameters changed. Please reinitialize detector.', 'log']))

        # Handle acquisition parameter changes
        elif param_name in ['sampling_rate', 'max_acq_time']:
            # These take effect immediately
            logger.debug(f"Updated acquisition parameter: {param_name} = {param.value()}")

    def _update_active_channels(self):
        """Update the list of active channels based on current parameters."""
        self.active_channels = []

        if self.settings['channels_group', 'measure_i']:
            self.active_channels.append('I Component (V)')

        if self.settings['channels_group', 'measure_q']:
            self.active_channels.append('Q Component (V)')

        if self.settings['channels_group', 'measure_magnitude']:
            self.active_channels.append('Magnitude (V)')

        if self.settings['channels_group', 'measure_phase']:
            self.active_channels.append('Phase (degrees)')

    def _create_iq_configuration(self) -> IQConfiguration:
        """Create IQ configuration from current parameters."""
        input_channel_str = self.settings['iq_settings', 'input_channel']
        input_channel = InputChannel.IN1 if input_channel_str == 'in1' else InputChannel.IN2

        output_direct_str = self.settings['output_group', 'output_direct']
        if output_direct_str == 'off':
            output_direct = IQOutputDirect.OFF
        elif output_direct_str == 'out1':
            output_direct = IQOutputDirect.OUT1
        else:
            output_direct = IQOutputDirect.OUT2

        return IQConfiguration(
            frequency=self.settings['lockin_group', 'frequency'],
            bandwidth=self.settings['lockin_group', 'bandwidth'],
            acbandwidth=self.settings['lockin_group', 'acbandwidth'],
            phase=self.settings['lockin_group', 'phase'],
            gain=self.settings['lockin_group', 'gain'],
            quadrature_factor=self.settings['output_group', 'quadrature_factor'],
            amplitude=self.settings['output_group', 'amplitude'],
            input_channel=input_channel,
            output_direct=output_direct
        )

    def _reconfigure_iq_module(self):
        """Reconfigure IQ module after parameter changes."""
        try:
            iq_module_str = self.settings['iq_settings', 'iq_module']
            self.current_iq_channel = IQChannel(iq_module_str)

            self.iq_config = self._create_iq_configuration()

            if isinstance(self.controller, MockPyRPLConnection):
                success = self.controller.configure_iq(self.current_iq_channel, self.iq_config)
            else:
                success = self.controller.configure_iq(self.current_iq_channel, self.iq_config)

            if success:
                logger.info(f"Reconfigured IQ module {iq_module_str}")
                self.emit_status(ThreadCommand('Update_Status',
                    [f"IQ module {iq_module_str} reconfigured", 'log']))
            else:
                logger.error(f"Failed to reconfigure IQ module {iq_module_str}")
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Failed to reconfigure IQ module {iq_module_str}", 'log']))

        except Exception as e:
            logger.error(f"Error reconfiguring IQ module: {e}")

    def _update_iq_parameters(self):
        """Update IQ parameters in real-time."""
        try:
            self.iq_config = self._create_iq_configuration()

            if isinstance(self.controller, MockPyRPLConnection):
                success = self.controller.configure_iq(self.current_iq_channel, self.iq_config)
            else:
                success = self.controller.configure_iq(self.current_iq_channel, self.iq_config)

            if success:
                logger.debug("Updated IQ parameters")
            else:
                logger.warning("Failed to update IQ parameters")

        except Exception as e:
            logger.error(f"Error updating IQ parameters: {e}")

    def ini_detector(self, controller=None):
        """
        Initialize detector and establish Red Pitaya connection.

        Parameters:
            controller: External controller (for slave mode) or None for master mode

        Returns:
            tuple: (info_string, initialization_success)
        """
        logger.info("Initializing PyRPL IQ viewer detector...")

        try:
            if self.is_master:
                # Master mode: create new connection
                mock_mode = self.settings['connection', 'mock_mode']
                hostname = self.settings['connection', 'redpitaya_host']

                if mock_mode:
                    # Use mock connection for development
                    self.controller = MockPyRPLConnection(hostname)
                    info = f"Mock PyRPL IQ connection established for {hostname}"
                    logger.info(info)

                else:
                    # Use real PyRPL connection
                    self.pyrpl_manager = PyRPLManager()

                    config_name = self.settings['connection', 'config_name']
                    timeout = self.settings['connection', 'connection_timeout']

                    # Connect to Red Pitaya
                    self.controller = self.pyrpl_manager.connect_device(
                        hostname=hostname,
                        config_name=config_name,
                        connection_timeout=timeout,
                        status_callback=self.emit_status
                    )

                    if self.controller is None or not self.controller.is_connected:
                        error_msg = f"Failed to connect to Red Pitaya at {hostname}"
                        if self.controller and self.controller.last_error:
                            error_msg += f": {self.controller.last_error}"
                        logger.error(error_msg)
                        return error_msg, False

                    info = f"Connected to Red Pitaya {hostname} ({config_name})"
                    logger.info(info)
            else:
                # Slave mode: use provided controller
                self.controller = controller
                info = "Using shared PyRPL connection"
                logger.info(info)

            # Configure IQ module
            iq_module_str = self.settings['iq_settings', 'iq_module']
            self.current_iq_channel = IQChannel(iq_module_str)

            self.iq_config = self._create_iq_configuration()

            success = self.controller.configure_iq(self.current_iq_channel, self.iq_config)
            if not success:
                error_msg = f"Failed to configure IQ module {iq_module_str}"
                logger.error(error_msg)
                return error_msg, False

            # Update active channels based on current settings
            self._update_active_channels()

            # Initialize data structure for PyMoDAQ
            self._initialize_data_structure()

            # Test initial data acquisition
            test_data = self._acquire_data()
            if test_data is None:
                return "Failed to acquire test data", False

            logger.info(f"IQ Detector initialized successfully. Active channels: {self.active_channels}")
            return info + f" (IQ Module: {iq_module_str})", True

        except Exception as e:
            error_msg = f"Detector initialization failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg, False

    def _initialize_data_structure(self):
        """Initialize PyMoDAQ data structure with current channel configuration."""
        if not self.active_channels:
            return

        # Create mock data for initialization
        mock_data_list = []
        for channel_name in self.active_channels:
            if 'Phase' in channel_name:
                units = 'degrees'
            else:
                units = 'V'

            data = DataRaw(
                name=channel_name,
                data=np.array([0.0]),
                labels=[channel_name],
                units=units
            )
            mock_data_list.append(data)

        # Emit initial data structure to PyMoDAQ
        self.dte_signal_temp.emit(
            DataToExport(name='PyRPL IQ', data=mock_data_list)
        )

    def _acquire_data(self) -> Optional[Dict[str, float]]:
        """
        Acquire I/Q data from the IQ lock-in amplifier.

        Returns:
            Dictionary mapping channel names to measurement values, or None if error
        """
        if self.controller is None or not self.controller.is_connected:
            logger.warning("Cannot acquire data: controller not connected")
            return None

        if self.current_iq_channel is None:
            logger.warning("Cannot acquire data: no IQ channel configured")
            return None

        data = {}

        try:
            # Get I and Q measurements from IQ module
            iq_result = self.controller.get_iq_measurement(self.current_iq_channel)
            if iq_result is None:
                logger.error("Failed to get IQ measurement")
                return None

            i_value, q_value = iq_result

            # Calculate magnitude and phase
            magnitude, phase_degrees = self.controller.calculate_magnitude_phase(i_value, q_value)

            # Store requested measurements
            if self.settings['channels_group', 'measure_i']:
                data['I Component (V)'] = i_value

            if self.settings['channels_group', 'measure_q']:
                data['Q Component (V)'] = q_value

            if self.settings['channels_group', 'measure_magnitude']:
                data['Magnitude (V)'] = magnitude

            if self.settings['channels_group', 'measure_phase']:
                data['Phase (degrees)'] = phase_degrees

            return data

        except Exception as e:
            logger.error(f"Error acquiring IQ data: {e}")
            return None

    def grab_data(self, Naverage=1, **kwargs):
        """
        Start data acquisition from Red Pitaya IQ lock-in amplifier.

        This method performs synchronous data acquisition from the configured
        IQ module and emits the data to PyMoDAQ for logging and visualization.

        Parameters:
            Naverage: Number of averages (currently ignored - hardware dependent)
            **kwargs: Additional arguments
        """
        start_time = time.time()

        try:
            # Acquire data from IQ lock-in amplifier
            channel_data = self._acquire_data()

            if channel_data is None:
                self.emit_status(ThreadCommand('Update_Status',
                    ['Failed to acquire data from IQ lock-in amplifier', 'log']))
                return

            # Create PyMoDAQ data objects
            data_list = []
            for channel_name in self.active_channels:
                if channel_name in channel_data:
                    value = channel_data[channel_name]

                    # Set appropriate units
                    if 'Phase' in channel_name:
                        units = 'degrees'
                    else:
                        units = 'V'

                    data = DataRaw(
                        name=channel_name,
                        data=np.array([value]),
                        labels=[channel_name],
                        units=units
                    )
                    data_list.append(data)
                else:
                    logger.warning(f"No data available for channel: {channel_name}")

            # Emit data to PyMoDAQ
            if data_list:
                self.dte_signal.emit(
                    DataToExport(name='PyRPL IQ', data=data_list)
                )

                # Update acquisition timing
                acquisition_time = time.time() - start_time
                self.last_acquisition_time = acquisition_time

                if acquisition_time > self.settings['acquisition', 'max_acq_time']:
                    logger.warning(f"Acquisition time ({acquisition_time:.3f}s) exceeded maximum")

            else:
                self.emit_status(ThreadCommand('Update_Status',
                    ['No active channels configured', 'log']))

        except Exception as e:
            error_msg = f"Error during IQ data acquisition: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def close(self):
        """
        Close detector and clean up resources.

        This method ensures proper disconnection from Red Pitaya hardware
        and cleanup of PyRPL resources to prevent conflicts with other plugins.
        """
        logger.info("Closing PyRPL IQ viewer detector...")

        try:
            # Disable IQ output before closing
            if (self.controller is not None and
                hasattr(self.controller, 'is_connected') and
                self.controller.is_connected and
                self.current_iq_channel is not None):

                try:
                    if not isinstance(self.controller, MockPyRPLConnection):
                        self.controller.enable_iq_output(self.current_iq_channel, IQOutputDirect.OFF)
                        logger.debug("Disabled IQ output before closing")
                except Exception as e:
                    logger.warning(f"Failed to disable IQ output: {e}")

            if self.controller is not None:
                if hasattr(self.controller, 'disconnect'):
                    self.controller.disconnect(status_callback=self.emit_status)

                self.controller = None

            if self.pyrpl_manager is not None:
                # Note: Don't cleanup the entire manager as it may be shared
                # Individual connections are cleaned up by the disconnect call above
                self.pyrpl_manager = None

            self.active_channels.clear()
            self.channel_data.clear()
            self.last_acquisition_time = 0.0
            self.iq_config = None
            self.current_iq_channel = None

            logger.info("PyRPL IQ detector closed successfully")

        except Exception as e:
            error_msg = f"Error during detector close: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def stop(self):
        """
        Stop current data acquisition.

        For this plugin, data acquisition is synchronous so this method
        mainly serves to update status and handle any cleanup if needed.

        Returns:
            Empty string (required by PyMoDAQ interface)
        """
        logger.debug("Stop IQ acquisition requested")
        self.emit_status(ThreadCommand('Update_Status', ['IQ acquisition stopped', 'log']))
        return ''


if __name__ == '__main__':
    # Run plugin in standalone mode for testing
    main(__file__)
