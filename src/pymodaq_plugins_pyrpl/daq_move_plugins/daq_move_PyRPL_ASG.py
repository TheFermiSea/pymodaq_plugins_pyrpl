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

Author: Claude Code
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

# Import PyRPL wrapper utilities
from ..utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, ASGChannel, ASGWaveform,
    ASGTriggerSource, ASGConfiguration, ConnectionState
)

logger = logging.getLogger(__name__)


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

    params = [
        {'title': 'Connection Settings', 'name': 'connection_settings', 'type': 'group', 'children': [
            {'title': 'RedPitaya Host:', 'name': 'redpitaya_host', 'type': 'str', 
             'value': 'rp-f0a552.local', 'tip': 'Red Pitaya hostname or IP address'},
            {'title': 'Config Name:', 'name': 'config_name', 'type': 'str', 
             'value': 'pymodaq', 'tip': 'PyRPL configuration name'},
            {'title': 'Connection Timeout (s):', 'name': 'connection_timeout', 'type': 'float', 
             'value': 10.0, 'min': 1.0, 'max': 60.0, 'tip': 'Timeout for connection attempts'},
            {'title': 'Retry Attempts:', 'name': 'retry_attempts', 'type': 'int', 
             'value': 3, 'min': 1, 'max': 10, 'tip': 'Number of connection retry attempts'},
        ]},
        
        {'title': 'ASG Settings', 'name': 'asg_settings', 'type': 'group', 'children': [
            {'title': 'ASG Channel:', 'name': 'asg_channel', 'type': 'list', 
             'limits': ['asg0', 'asg1'], 'value': 'asg0', 'tip': 'ASG channel selection'},
            {'title': 'Waveform:', 'name': 'waveform', 'type': 'list', 
             'limits': ['sin', 'cos', 'ramp', 'square', 'noise', 'dc'], 'value': 'sin',
             'tip': 'ASG waveform type'},
            {'title': 'Amplitude (V):', 'name': 'amplitude', 'type': 'float', 
             'value': 0.1, 'min': -1.0, 'max': 1.0, 'step': 0.001, 
             'tip': 'ASG output amplitude in volts (±1V max)'},
            {'title': 'Offset (V):', 'name': 'offset', 'type': 'float', 
             'value': 0.0, 'min': -1.0, 'max': 1.0, 'step': 0.001,
             'tip': 'ASG DC offset in volts (±1V max)'},
            {'title': 'Phase (degrees):', 'name': 'phase', 'type': 'float', 
             'value': 0.0, 'min': -180, 'max': 180, 'step': 1.0,
             'tip': 'Phase shift for sine/cosine waveforms'},
        ]},
        
        {'title': 'Control Settings', 'name': 'control_settings', 'type': 'group', 'children': [
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list', 
             'limits': ['off', 'immediately', 'ext_positive_edge', 'ext_negative_edge'], 
             'value': 'immediately', 'tip': 'ASG trigger source selection'},
            {'title': 'Output Enable:', 'name': 'output_enable', 'type': 'bool', 
             'value': True, 'tip': 'Enable ASG output to physical connector'},
            {'title': 'Frequency Min (Hz):', 'name': 'frequency_min', 'type': 'float', 
             'value': 0.0, 'min': 0.0, 'max': 1e6, 'step': 1.0,
             'tip': 'Minimum frequency limit for safety'},
            {'title': 'Frequency Max (Hz):', 'name': 'frequency_max', 'type': 'float', 
             'value': 1e6, 'min': 1.0, 'max': 62.5e6, 'step': 1.0,
             'tip': 'Maximum frequency limit for safety (max 62.5MHz)'},
        ]},
        
        {'title': 'Development Settings', 'name': 'dev_settings', 'type': 'group', 'children': [
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False,
             'tip': 'Enable mock mode for development without hardware'},
            {'title': 'Auto Connect:', 'name': 'auto_connect', 'type': 'bool', 'value': True,
             'tip': 'Automatically connect on initialization'},
            {'title': 'Debug Logging:', 'name': 'debug_logging', 'type': 'bool', 'value': False,
             'tip': 'Enable detailed debug logging'},
        ]},
    ]

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
        
        # ASG configuration storage
        self.current_asg_config: Optional[ASGConfiguration] = None
        
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
        param_path = self.get_param_path(param)
        param_name = param.name()
        param_value = param.value()
        
        logger.debug(f"Parameter changed: {param_path} = {param_value}")
        
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
            # Extract parameters
            self.mock_mode = self.settings.child('dev_settings', 'mock_mode').value()
            auto_connect = self.settings.child('dev_settings', 'auto_connect').value()
            debug_logging = self.settings.child('dev_settings', 'debug_logging').value()
            
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
            freq_min = self.settings.child('control_settings', 'frequency_min').value()
            freq_max = self.settings.child('control_settings', 'frequency_max').value()
            
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
        self.mock_min_freq = self.settings.child('control_settings', 'frequency_min').value()
        self.mock_max_freq = self.settings.child('control_settings', 'frequency_max').value()
        
        return "ASG Plugin initialized in mock mode"

    def _initialize_hardware_mode(self, auto_connect: bool) -> str:
        """Initialize plugin with real hardware."""
        logger.info("Initializing ASG Plugin with hardware")
        
        # Get connection parameters
        hostname = self.settings.child('connection_settings', 'redpitaya_host').value()
        config_name = self.settings.child('connection_settings', 'config_name').value()
        timeout = self.settings.child('connection_settings', 'connection_timeout').value()
        retry_attempts = self.settings.child('connection_settings', 'retry_attempts').value()
        
        # Get ASG channel
        asg_channel_name = self.settings.child('asg_settings', 'asg_channel').value()
        self.asg_channel = ASGChannel(asg_channel_name)
        
        if auto_connect:
            # Establish connection
            self.controller = self.pyrpl_manager.connect_device(
                hostname=hostname,
                config_name=config_name,
                status_callback=self.emit_status,
                connection_timeout=timeout,
                retry_attempts=retry_attempts
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
            amplitude=self.settings.child('asg_settings', 'amplitude').value(),
            offset=self.settings.child('asg_settings', 'offset').value(),
            phase=self.settings.child('asg_settings', 'phase').value(),
            waveform=ASGWaveform(self.settings.child('asg_settings', 'waveform').value()),
            trigger_source=ASGTriggerSource(self.settings.child('control_settings', 'trigger_source').value()),
            output_enable=self.settings.child('control_settings', 'output_enable').value(),
            frequency_min=self.settings.child('control_settings', 'frequency_min').value(),
            frequency_max=self.settings.child('control_settings', 'frequency_max').value(),
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
        freq_min = self.settings.child('control_settings', 'frequency_min').value()
        freq_max = self.settings.child('control_settings', 'frequency_max').value()
        
        if freq_min >= freq_max:
            logger.warning(f"Invalid frequency limits: min={freq_min} >= max={freq_max}")
            # Reset to safe defaults
            self.settings.child('control_settings', 'frequency_min').setValue(0.0)
            self.settings.child('control_settings', 'frequency_max').setValue(1e6)

    def _setup_logging(self, debug_enabled: bool) -> None:
        """Setup logging level based on debug setting."""
        if debug_enabled:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled for ASG Plugin")
        else:
            logger.setLevel(logging.INFO)


if __name__ == '__main__':
    main(__file__)