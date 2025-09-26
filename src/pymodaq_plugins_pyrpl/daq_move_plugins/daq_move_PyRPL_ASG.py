# -*- coding: utf-8 -*-
"""
PyMoDAQ Actuator Plugin for Red Pitaya PyRPL Arbitrary Signal Generator Control

This plugin provides PyMoDAQ actuator functionality for controlling Red Pitaya's
Arbitrary Signal Generator (ASG) frequency via the PyRPL library. It enables precise
frequency control for waveform generation in spectroscopy and test applications.

Features:
    - Hardware ASG frequency control (Red Pitaya STEMlab)
    - Dual-channel ASG support (ASG0/ASG1)
    - Multiple waveforms: sin, cos, ramp, square, noise, dc
    - Thread-safe PyRPL wrapper integration
    - Mock mode for development without hardware
    - Frequency range: 0 Hz to 62.5 MHz

Compatible Controllers:
    - Red Pitaya STEMlab 125-10/125-14
    - PyRPL firmware and library

Tested Configuration:
    - PyMoDAQ 4.0+
    - PyRPL 0.9.5+
    - Red Pitaya STEMlab 125-14
    - Ubuntu 20.04/22.04 LTS

Installation Requirements:
    - PyRPL library: `pip install pyrpl`
    - Red Pitaya network connection and PyRPL firmware
    - Proper network configuration (see documentation)

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

from typing import Union, List, Dict, Optional, Any
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun,
    main, DataActuatorType, DataActuator
)

from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
import logging

# Import configuration utilities
from ..utils.config import get_pyrpl_config

# Import PyRPL wrapper utilities
from ..utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, ASGChannel, ASGWaveform,
    ASGTriggerSource, ASGConfiguration, ConnectionState
)

logger = logging.getLogger(__name__)


def get_asg_parameters():
    """Generate parameter list with configuration defaults."""
    try:
        config = get_pyrpl_config()
        connection_config = config.get_connection_config()
        hardware_config = config.get_hardware_config()
        asg_defaults = hardware_config.get('asg_defaults', {})

        # Use config values with fallbacks
        default_hostname = connection_config.get('default_hostname', 'rp-f08d6c.local')
        default_timeout = connection_config.get('connection_timeout', 10.0)
        default_config_name = connection_config.get('config_name', 'pymodaq_pyrpl')
        default_frequency = asg_defaults.get('frequency', 1000.0)
        default_amplitude = asg_defaults.get('amplitude', 0.1)
        default_waveform = asg_defaults.get('waveform', 'sin')

    except Exception as e:
        logger.warning(f"Failed to load config defaults: {e}, using hardcoded values")
        # Fallback to hardcoded defaults
        default_hostname = 'rp-f08d6c.local'
        default_timeout = 10.0
        default_config_name = 'pymodaq_pyrpl'
        default_frequency = 1000.0
        default_amplitude = 0.1
        default_waveform = 'sin'

    return [
        {'title': 'Connection Settings', 'name': 'connection_settings', 'type': 'group', 'children': [
            {'title': 'RedPitaya Host:', 'name': 'redpitaya_host', 'type': 'str',
             'value': default_hostname, 'tip': 'Red Pitaya hostname or IP address'},
            {'title': 'Config Name:', 'name': 'config_name', 'type': 'str',
             'value': default_config_name, 'tip': 'PyRPL configuration name'},
            {'title': 'Connection Timeout (s):', 'name': 'connection_timeout', 'type': 'float',
             'value': default_timeout, 'min': 1.0, 'max': 60.0},
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False,
             'tip': 'Enable mock mode for testing without hardware'},
        ]},

        {'title': 'ASG Configuration', 'name': 'asg_config', 'type': 'group', 'children': [
            {'title': 'ASG Channel:', 'name': 'asg_channel', 'type': 'list',
             'limits': ['asg0', 'asg1'], 'value': 'asg0',
             'tip': 'Select ASG module (asg0 or asg1)'},
            {'title': 'Waveform:', 'name': 'waveform', 'type': 'list',
             'limits': ['sin', 'cos', 'ramp', 'square', 'noise', 'dc'],
             'value': default_waveform, 'tip': 'ASG waveform type'},
        ]},

        {'title': 'Signal Parameters', 'name': 'signal_params', 'type': 'group', 'children': [
            {'title': 'Frequency (Hz):', 'name': 'frequency', 'type': 'float',
             'value': default_frequency, 'min': 0.1, 'max': 62.5e6,
             'tip': 'Signal frequency in Hz'},
            {'title': 'Amplitude (V):', 'name': 'amplitude', 'type': 'float',
             'value': default_amplitude, 'min': 0.0, 'max': 1.0, 'step': 0.001,
             'tip': 'Signal amplitude (0-1V peak)'},
            {'title': 'Offset (V):', 'name': 'offset', 'type': 'float',
             'value': 0.0, 'min': -1.0, 'max': 1.0, 'step': 0.001,
             'tip': 'DC offset voltage'},
        ]},

        {'title': 'Safety Settings', 'name': 'safety_settings', 'type': 'group', 'children': [
            {'title': 'Min Frequency (Hz):', 'name': 'min_frequency', 'type': 'float',
             'value': 0.1, 'min': 0.1, 'max': 1e6,
             'tip': 'Minimum allowed frequency'},
            {'title': 'Max Frequency (Hz):', 'name': 'max_frequency', 'type': 'float',
             'value': 1e6, 'min': 1000.0, 'max': 62.5e6,
             'tip': 'Maximum allowed frequency'},
            {'title': 'Enable ASG on Connect:', 'name': 'auto_enable_asg', 'type': 'bool',
             'value': False, 'tip': 'Automatically enable ASG output on connection'},
        ]},

        {'title': 'Advanced Tools', 'name': 'advanced_tools', 'type': 'group', 'children': [
            {'title': 'Open Native ASG GUI', 'name': 'open_native_asg', 'type': 'action',
             'tip': 'Launch PyRPL native ASG widget for advanced waveform configuration'},
            {'title': 'Open Spectrum Analyzer', 'name': 'open_spectrum_analyzer', 'type': 'action',
             'tip': 'Launch PyRPL spectrum analyzer for output signal analysis'},
            {'title': 'Sync from Hardware', 'name': 'sync_from_hardware', 'type': 'action',
             'tip': 'Read current ASG settings from hardware and update PyMoDAQ parameters'},
            {'title': 'Advanced Diagnostics', 'name': 'show_diagnostics', 'type': 'bool',
             'value': False, 'tip': 'Show diagnostic information in status messages'},
        ]},
    ]


class DAQ_Move_PyRPL_ASG(DAQ_Move_base):
    """
    PyMoDAQ Actuator Plugin for Red Pitaya ASG Frequency Control.

    This plugin enables precise control of Red Pitaya's Arbitrary Signal Generator
    frequency through PyMoDAQ's actuator interface. It uses a centralized PyRPL
    wrapper to manage connections and prevent conflicts between multiple plugins.

    The plugin treats ASG frequency as the actuator position, allowing PyMoDAQ to:
    - Set absolute frequency values (move_abs)
    - Make relative frequency adjustments (move_rel)
    - Read current frequency values (get_actuator_value)
    - Control waveform parameters and output settings

    Key Features:
    - Hardware ASG frequency control with 0-62.5MHz range
    - Dual-channel support (ASG0, ASG1)
    - Multiple waveforms: sin, cos, ramp, square, noise, dc
    - Amplitude and offset control within ±1V range
    - Thread-safe operations via PyRPL wrapper
    - Mock mode for development without hardware
    - Comprehensive error handling and status reporting

    Attributes:
    -----------
    controller: PyRPLConnection
        The PyRPL connection object for hardware communication
    pyrpl_manager: PyRPLManager
        Centralized manager for PyRPL connections
    asg_channel: ASGChannel
        Selected ASG channel (ASG0/ASG1)
    mock_mode: bool
        Whether to operate in mock mode without hardware
    mock_frequency: float
        Simulated frequency value for mock mode
    """

    is_multiaxes = False
    _axis_names = ['Frequency']
    _controller_units = 'Hz'  # Frequency units for ASG control
    _epsilon = 1.0  # 1Hz precision for frequency control
    data_actuator_type = DataActuatorType.DataActuator

    params = get_asg_parameters() + comon_parameters_fun(is_multiaxes=is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)

    def ini_attributes(self) -> None:
        """
        Initialize plugin attributes and prepare for hardware connection.

        This method sets up the initial state of the plugin, including connection
        management, mock mode configuration, and parameter validation.
        """
        self.controller: Optional[PyRPLConnection] = None
        self.pyrpl_manager: PyRPLManager = PyRPLManager.get_instance()
        self.asg_channel: Optional[ASGChannel] = None

        # Mock mode attributes
        self.mock_mode: bool = False
        self.mock_frequency: float = 1000.0  # Default mock frequency
        self.mock_min_freq: float = 0.0
        self.mock_max_freq: float = 1e6

        # Connection state tracking
        self.connection_status: str = "Disconnected"
        self.last_error: Optional[str] = None

        # Native widget instances (for hybrid approach)
        self.native_asg_widget = None
        self.spectrum_analyzer_widget = None
        self.show_diagnostics: bool = False

        # ASG configuration storage
        self.current_asg_config: Optional[ASGConfiguration] = None

        # Configuration management
        self.config = get_pyrpl_config()

        # PyRPL Manager (threading support handled by wrapper)
        self.pyrpl_manager: PyRPLManager = PyRPLManager.get_instance()

        logger.info("ASG Plugin attributes initialized")

    def get_actuator_value(self) -> float:
        """
        Get the current ASG frequency value.

        Returns:
        --------
        float
            Current ASG frequency in Hz

        Raises:
        -------
        Exception
            If unable to read frequency from hardware or in mock mode error
        """
        try:
            if self.mock_mode:
                logger.debug(f"Mock mode: returning frequency {self.mock_frequency} Hz")
                return self.mock_frequency

            if self.controller is None or not self.controller.is_connected:
                raise Exception("ASG controller not connected")

            if self.asg_channel is None:
                raise Exception("ASG channel not configured")

            frequency = self.controller.get_asg_frequency(self.asg_channel)
            if frequency is None:
                raise Exception("Failed to read ASG frequency")

            logger.debug(f"Read ASG frequency: {frequency} Hz")
            return frequency

        except Exception as e:
            error_msg = f"Failed to get ASG frequency: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            raise

    def close(self) -> None:
        """
        Clean shutdown of the ASG plugin.

        Safely disconnects from Red Pitaya hardware, disables ASG output,
        and cleans up resources. This method ensures that the ASG output
        is disabled before disconnection to prevent unexpected signals.
        """
        logger.info("Closing ASG Plugin")

        try:
            if not self.mock_mode and self.controller is not None:
                # Safely disable ASG output before closing
                if (self.controller.is_connected and
                    self.asg_channel is not None):

                    logger.info(f"Disabling ASG {self.asg_channel.value} output")
                    self.controller.enable_asg_output(self.asg_channel, False)

                # Disconnect from Red Pitaya
                self.controller.disconnect(self.emit_status)

            self.controller = None
            self.asg_channel = None
            self.current_asg_config = None
            self.connection_status = "Disconnected"

            logger.info("ASG Plugin closed successfully")

        except Exception as e:
            error_msg = f"Error during ASG Plugin shutdown: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def commit_settings(self, param: Parameter) -> None:
        """
        Handle parameter changes and apply them to the ASG hardware.

        This method is called whenever a parameter changes in the PyMoDAQ GUI.
        It validates the new values and applies them to the ASG configuration.

        Parameters:
        -----------
        param : Parameter
            The parameter that was changed
        """
        param_name = param.name()
        param_value = param.value()

        logger.debug(f"Parameter changed: {param_name} = {param_value}")

        try:
            # Handle ASG configuration parameters
            if param_name in ['waveform', 'amplitude', 'offset', 'phase',
                              'trigger_source', 'output_enable']:
                self._update_asg_configuration()

            elif param_name in ['frequency_min', 'frequency_max']:
                self._validate_frequency_limits()

            elif param_name == 'debug_logging':
                self._setup_logging(param_value)

            elif param_name == 'mock_mode':
                if param_value != self.mock_mode:
                    logger.info(f"Mock mode changing to: {param_value}")
                    # Note: Changing mock mode typically requires reinitialization

            elif param_name == 'open_native_asg':
                # Launch PyRPL native ASG widget
                self._launch_native_asg_widget()

            elif param_name == 'open_spectrum_analyzer':
                # Launch PyRPL spectrum analyzer
                self._launch_spectrum_analyzer_widget()

            elif param_name == 'sync_from_hardware':
                # Synchronize parameters from hardware
                self._sync_parameters_from_hardware()

            elif param_name == 'show_diagnostics':
                # Toggle diagnostic information
                self.show_diagnostics = param_value
                status = "Enabled" if self.show_diagnostics else "Disabled"
                self.emit_status(ThreadCommand('Update_Status', [f"Advanced diagnostics: {status}", 'log']))

        except Exception as e:
            error_msg = f"Failed to apply parameter change {param_name}: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def ini_stage(self, controller=None) -> str:
        """
        Initialize the ASG hardware connection and configuration.

        This method establishes connection to the Red Pitaya device,
        configures the selected ASG channel, and prepares it for operation.

        Parameters:
        -----------
        controller : optional
            External controller (not used for PyRPL integration)

        Returns:
        --------
        str
            Status message indicating initialization result
        """
        logger.info("Initializing ASG Plugin")

        try:
            # Extract parameters from correct groups
            self.mock_mode = self.settings.child('connection_settings', 'mock_mode').value()
            auto_connect = True  # Always auto-connect in PyMoDAQ
            debug_logging = False  # Default to false

            # Setup logging
            self._setup_logging(debug_logging)

            if self.mock_mode:
                return self._initialize_mock_mode()
            else:
                return self._initialize_hardware_mode(auto_connect)

        except Exception as e:
            error_msg = f"ASG Plugin initialization failed: {str(e)}"
            logger.error(error_msg)
            self.connection_status = "Error"
            self.last_error = str(e)
            return error_msg

    def move_abs(self, position: float) -> None:
        """
        Move ASG frequency to absolute value.

        Parameters:
        -----------
        position : float
            Target frequency in Hz
        """
        try:
            # Validate frequency limits
            freq_min = self.settings.child('safety_settings', 'min_frequency').value()
            freq_max = self.settings.child('safety_settings', 'max_frequency').value()

            if not (freq_min <= position <= freq_max):
                raise ValueError(f"Frequency {position} Hz out of range [{freq_min}, {freq_max}] Hz")

            if self.mock_mode:
                self.mock_frequency = position
                logger.debug(f"Mock mode: set frequency to {position} Hz")
                return

            if self.controller is None or not self.controller.is_connected:
                raise Exception("ASG controller not connected")

            if self.asg_channel is None:
                raise Exception("ASG channel not configured")

            success = self.controller.set_asg_frequency(self.asg_channel, position)
            if not success:
                raise Exception("Failed to set ASG frequency")

            logger.info(f"Set ASG frequency to {position} Hz")

        except Exception as e:
            error_msg = f"Failed to move ASG to {position} Hz: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            raise

    def move_home(self) -> None:
        """
        Move ASG frequency to home position (default frequency).

        For ASG, home position is defined as 1kHz.
        """
        logger.info("Moving ASG to home position (1kHz)")
        self.move_abs(1000.0)

    def move_rel(self, position: float) -> None:
        """
        Move ASG frequency by relative amount.

        Parameters:
        -----------
        position : float
            Relative frequency change in Hz
        """
        try:
            current_freq = self.get_actuator_value()
            target_freq = current_freq + position

            logger.debug(f"Relative move: {current_freq} + {position} = {target_freq} Hz")
            self.move_abs(target_freq)

        except Exception as e:
            error_msg = f"Failed to move ASG relatively by {position} Hz: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            raise

    def stop_motion(self) -> None:
        """
        Stop ASG operation by disabling output.

        For ASG, stopping motion means disabling the output signal.
        """
        try:
            logger.info("Stopping ASG output")

            if self.mock_mode:
                logger.debug("Mock mode: ASG output stopped")
                return

            if (self.controller is not None and
                self.controller.is_connected and
                self.asg_channel is not None):

                success = self.controller.enable_asg_output(self.asg_channel, False)
                if success:
                    logger.info("ASG output disabled")
                else:
                    logger.warning("Failed to disable ASG output")

        except Exception as e:
            error_msg = f"Failed to stop ASG: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    # Helper methods

    def _initialize_mock_mode(self) -> str:
        """Initialize plugin in mock mode for development."""
        logger.info("Initializing ASG Plugin in mock mode")

        self.connection_status = "Mock Mode"
        self.mock_frequency = 1000.0  # Default 1kHz

        # Setup mock frequency limits
        self.mock_min_freq = self.settings.child('safety_settings', 'min_frequency').value()
        self.mock_max_freq = self.settings.child('safety_settings', 'max_frequency').value()

        return "ASG Plugin initialized in mock mode"

    def _initialize_hardware_mode(self, auto_connect: bool) -> str:
        """Initialize plugin with real hardware."""
        logger.info("Initializing ASG Plugin with hardware")

        # Get connection parameters
        hostname = self.settings.child('connection_settings', 'redpitaya_host').value()
        config_name = self.settings.child('connection_settings', 'config_name').value()
        timeout = self.settings.child('connection_settings', 'connection_timeout').value()
        # Get ASG channel
        asg_channel_name = self.settings.child('asg_config', 'asg_channel').value()
        self.asg_channel = ASGChannel(asg_channel_name)

        if auto_connect:
            # Establish connection
            self.controller = self.pyrpl_manager.connect_device(
                hostname=hostname,
                config_name=config_name,
                status_callback=self.emit_status,
                connection_timeout=timeout
            )

            if self.controller is None or not self.controller.is_connected:
                error_msg = f"Failed to connect to Red Pitaya at {hostname}"
                self.connection_status = "Connection Failed"
                return error_msg

            # Configure ASG
            self._configure_asg_hardware()
            self.connection_status = "Connected"

            return f"ASG Plugin connected to {hostname} on channel {asg_channel_name}"
        else:
            self.connection_status = "Ready (Not Connected)"
            return "ASG Plugin ready for manual connection"

    def _configure_asg_hardware(self) -> None:
        """Configure ASG hardware with current parameters."""
        if self.controller is None or self.asg_channel is None:
            return

        # Create ASG configuration from parameters
        config = ASGConfiguration(
            frequency=self.mock_frequency,  # Will be updated by moves
            amplitude=self.settings.child('signal_params', 'amplitude').value(),
            offset=self.settings.child('signal_params', 'offset').value(),
            phase=0.0,  # Default phase
            waveform=ASGWaveform(self.settings.child('asg_config', 'waveform').value()),
            trigger_source=ASGTriggerSource('immediately'),  # Default trigger
            output_enable=self.settings.child('safety_settings', 'auto_enable_asg').value(),
            frequency_min=self.settings.child('safety_settings', 'min_frequency').value(),
            frequency_max=self.settings.child('safety_settings', 'max_frequency').value(),
        )

        success = self.controller.configure_asg(self.asg_channel, config)
        if success:
            self.current_asg_config = config
            logger.info(f"ASG {self.asg_channel.value} configured successfully")
        else:
            raise Exception(f"Failed to configure ASG {self.asg_channel.value}")

    def _update_asg_configuration(self) -> None:
        """Update ASG configuration when parameters change."""
        if self.mock_mode or self.controller is None or not self.controller.is_connected:
            return

        try:
            self._configure_asg_hardware()
        except Exception as e:
            logger.error(f"Failed to update ASG configuration: {e}")

    def _validate_frequency_limits(self) -> None:
        """Validate frequency limit parameters."""
        freq_min = self.settings.child('safety_settings', 'min_frequency').value()
        freq_max = self.settings.child('safety_settings', 'max_frequency').value()

        if freq_min >= freq_max:
            logger.warning(f"Invalid frequency limits: min={freq_min} >= max={freq_max}")
            # Reset to safe defaults
            self.settings.child('safety_settings', 'min_frequency').setValue(0.1)
            self.settings.child('safety_settings', 'max_frequency').setValue(1e6)

    def _setup_logging(self, debug_enabled: bool) -> None:
        """Setup logging level based on debug setting."""
        if debug_enabled:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled for ASG Plugin")
        else:
            logger.setLevel(logging.INFO)

    def _launch_native_asg_widget(self):
        """
        Launch PyRPL's native ASG widget for advanced waveform configuration.

        This opens a standalone PyRPL ASG interface that provides
        advanced waveform controls and real-time visualization.
        """
        if self.mock_mode:
            self.emit_status(ThreadCommand('Update_Status',
                ['Native ASG widget not available in mock mode', 'log']))
            return

        if not self.controller or not self.controller.is_connected:
            self.emit_status(ThreadCommand('Update_Status',
                ['Cannot launch native widget: PyRPL not connected', 'log']))
            return

        try:
            # Get PyRPL instance from the controller
            pyrpl_instance = self.controller.get_pyrpl_instance()
            if pyrpl_instance is None:
                raise Exception("PyRPL instance not available")

            # Get the ASG module
            asg_module = getattr(pyrpl_instance.rp, self.asg_channel.value)

            # Close existing widget if open
            if self.native_asg_widget is not None:
                try:
                    self.native_asg_widget.close()
                except:
                    pass
                self.native_asg_widget = None

            # Create and show the native ASG widget
            self.native_asg_widget = asg_module.create_widget()
            self.native_asg_widget.setWindowTitle(f"PyRPL {self.asg_channel.value.upper()} - Native Interface")
            self.native_asg_widget.show()

            # Bring window to front
            self.native_asg_widget.raise_()
            self.native_asg_widget.activateWindow()

            self.emit_status(ThreadCommand('Update_Status',
                [f"Launched native ASG widget for {self.asg_channel.value}", 'log']))

            if self.show_diagnostics:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Native widget address: {hex(id(self.native_asg_widget))}", 'log']))

        except Exception as e:
            error_msg = f"Failed to launch native ASG widget: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def _launch_spectrum_analyzer_widget(self):
        """
        Launch PyRPL's spectrum analyzer for ASG output analysis.

        This provides real-time spectrum analysis of the ASG output signals.
        """
        if self.mock_mode:
            self.emit_status(ThreadCommand('Update_Status',
                ['Spectrum analyzer not available in mock mode', 'log']))
            return

        if not self.controller or not self.controller.is_connected:
            self.emit_status(ThreadCommand('Update_Status',
                ['Cannot launch spectrum analyzer: PyRPL not connected', 'log']))
            return

        try:
            # Get PyRPL instance from the controller
            pyrpl_instance = self.controller.get_pyrpl_instance()
            if pyrpl_instance is None:
                raise Exception("PyRPL instance not available")

            # Check if spectrum analyzer is available
            if not hasattr(pyrpl_instance.rp, 'spectrumanalyzer'):
                raise Exception("Spectrum analyzer module not available in this PyRPL version")

            # Close existing widget if open
            if self.spectrum_analyzer_widget is not None:
                try:
                    self.spectrum_analyzer_widget.close()
                except:
                    pass
                self.spectrum_analyzer_widget = None

            # Create and show the spectrum analyzer widget
            sa_module = pyrpl_instance.rp.spectrumanalyzer
            self.spectrum_analyzer_widget = sa_module.create_widget()
            self.spectrum_analyzer_widget.setWindowTitle("PyRPL Spectrum Analyzer - ASG Output")
            self.spectrum_analyzer_widget.show()

            # Bring window to front
            self.spectrum_analyzer_widget.raise_()
            self.spectrum_analyzer_widget.activateWindow()

            self.emit_status(ThreadCommand('Update_Status',
                ['Launched PyRPL spectrum analyzer', 'log']))

            if self.show_diagnostics:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Spectrum analyzer widget address: {hex(id(self.spectrum_analyzer_widget))}", 'log']))

        except Exception as e:
            error_msg = f"Failed to launch spectrum analyzer: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def _sync_parameters_from_hardware(self):
        """
        Synchronize PyMoDAQ parameters with current ASG hardware state.

        This reads the current ASG configuration from the Red Pitaya
        and updates the PyMoDAQ parameter tree to match.
        """
        if self.mock_mode:
            self.emit_status(ThreadCommand('Update_Status',
                ['Hardware sync not available in mock mode', 'log']))
            return

        if not self.controller or not self.controller.is_connected:
            self.emit_status(ThreadCommand('Update_Status',
                ['Cannot sync: PyRPL not connected', 'log']))
            return

        try:
            # Get current ASG configuration from hardware
            asg_config = self.controller.get_asg_configuration(self.asg_channel)
            if asg_config is None:
                raise Exception("Failed to read ASG configuration from hardware")

            # Update PyMoDAQ parameters to match hardware
            with self.settings.child('signal_params').blockTreeSignals():
                self.settings.child('signal_params', 'frequency').setValue(asg_config.frequency)
                self.settings.child('signal_params', 'amplitude').setValue(asg_config.amplitude)
                self.settings.child('signal_params', 'offset').setValue(asg_config.offset)

            with self.settings.child('asg_config').blockTreeSignals():
                self.settings.child('asg_config', 'waveform').setValue(asg_config.waveform.value)

            self.emit_status(ThreadCommand('Update_Status',
                [f"Synchronized parameters from {self.asg_channel.value} hardware", 'log']))

            if self.show_diagnostics:
                diag_msg = (f"Hardware sync - Freq: {asg_config.frequency:.1f}Hz, "
                           f"Amp: {asg_config.amplitude:.3f}V, "
                           f"Waveform: {asg_config.waveform.value}")
                self.emit_status(ThreadCommand('Update_Status', [diag_msg, 'log']))

        except Exception as e:
            error_msg = f"Failed to sync from hardware: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def close(self):
        """
        Close the plugin and cleanup resources.

        This ensures proper cleanup of native widgets and PyRPL connections.
        """
        # Close native widgets if open
        if self.native_asg_widget is not None:
            try:
                self.native_asg_widget.close()
            except:
                pass
            self.native_asg_widget = None

        if self.spectrum_analyzer_widget is not None:
            try:
                self.spectrum_analyzer_widget.close()
            except:
                pass
            self.spectrum_analyzer_widget = None

        # Disconnect from PyRPL
        if self.controller and self.controller.is_connected:
            try:
                self.pyrpl_manager.disconnect(self.hostname)
                logger.debug("Disconnected from PyRPL")
            except Exception as e:
                logger.warning(f"Error during PyRPL disconnect: {e}")

        logger.debug("DAQ_Move_PyRPL_ASG closed")


if __name__ == '__main__':
    main(__file__)
