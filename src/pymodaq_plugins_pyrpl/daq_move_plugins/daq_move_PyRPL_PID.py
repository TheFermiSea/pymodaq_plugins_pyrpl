# -*- coding: utf-8 -*-
"""
PyMoDAQ Actuator Plugin for Red Pitaya PyRPL PID Controller Setpoint Control

This plugin provides PyMoDAQ actuator functionality for controlling Red Pitaya's
hardware PID controller setpoints via the PyRPL library. It enables precise
setpoint adjustment for laser power stabilization applications.

Features:
    - Hardware PID setpoint control (Red Pitaya STEMlab)
    - Multi-channel PID support (PID0/PID1/PID2)
    - Thread-safe PyRPL wrapper integration
    - Mock mode for development without hardware
    - Voltage range: ±1V with proper safety limits

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

from typing import Union, List, Dict, Optional
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun,
    main, DataActuatorType, DataActuator
)

from pymodaq_utils.utils import ThreadCommand
from ..utils.config import get_pyrpl_config
from ..utils.threading import ThreadedHardwareManager, threaded_hardware_operation
from pymodaq_gui.parameter import Parameter
import logging

# Import PyRPL wrapper utilities
from ..utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, PIDChannel, InputChannel, 
    OutputChannel, PIDConfiguration, ConnectionState
)

logger = logging.getLogger(__name__)


def get_pid_parameters():
    """Generate parameter list with configuration defaults."""
    try:
        config = get_pyrpl_config()
        connection_config = config.get_connection_config()
        hardware_config = config.get_hardware_config()
        pid_defaults = hardware_config.get('pid_default_gains', {})
        
        # Use config values with fallbacks
        default_hostname = connection_config.get('default_hostname', 'rp-f08d6c.local')
        default_timeout = connection_config.get('connection_timeout', 10.0)
        default_config_name = connection_config.get('config_name', 'pymodaq_pyrpl')
        default_p_gain = pid_defaults.get('p', 0.1)
        default_i_gain = pid_defaults.get('i', 0.01)
        default_d_gain = pid_defaults.get('d', 0.0)
        voltage_range = hardware_config.get('voltage_range', 1.0)
        
    except Exception as e:
        logger.warning(f"Failed to load config defaults: {e}, using hardcoded values")
        # Fallback to hardcoded defaults
        default_hostname = 'rp-f08d6c.local'
        default_timeout = 10.0
        default_config_name = 'pymodaq_pyrpl'
        default_p_gain = 0.1
        default_i_gain = 0.01
        default_d_gain = 0.0
        voltage_range = 1.0
    
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
        
        {'title': 'PID Configuration', 'name': 'pid_config', 'type': 'group', 'children': [
            {'title': 'PID Module:', 'name': 'pid_module', 'type': 'list', 
             'limits': ['pid0', 'pid1', 'pid2'], 'value': 'pid0',
             'tip': 'Select PID controller module'},
            {'title': 'Input Channel:', 'name': 'input_channel', 'type': 'list', 
             'limits': ['in1', 'in2'], 'value': 'in1',
             'tip': 'PID input channel selection'},
            {'title': 'Output Channel:', 'name': 'output_channel', 'type': 'list', 
             'limits': ['out1', 'out2'], 'value': 'out1',
             'tip': 'PID output channel selection'},
        ]},
        
        {'title': 'PID Parameters', 'name': 'pid_params', 'type': 'group', 'children': [
            {'title': 'P Gain:', 'name': 'p_gain', 'type': 'float', 
             'value': default_p_gain, 'min': 0.0, 'max': 10.0, 'step': 0.01,
             'tip': 'Proportional gain coefficient'},
            {'title': 'I Gain:', 'name': 'i_gain', 'type': 'float', 
             'value': default_i_gain, 'min': 0.0, 'max': 1.0, 'step': 0.001,
             'tip': 'Integral gain coefficient'},
            {'title': 'D Gain:', 'name': 'd_gain', 'type': 'float', 
             'value': default_d_gain, 'min': 0.0, 'max': 1.0, 'step': 0.001,
             'tip': 'Derivative gain coefficient (usually kept at 0)'},
        ]},
        
        {'title': 'Safety Limits', 'name': 'safety_limits', 'type': 'group', 'children': [
            {'title': 'Min Voltage (V):', 'name': 'min_voltage', 'type': 'float', 
             'value': -voltage_range, 'min': -voltage_range, 'max': 0.0,
             'tip': 'Minimum allowed setpoint voltage'},
            {'title': 'Max Voltage (V):', 'name': 'max_voltage', 'type': 'float', 
             'value': voltage_range, 'min': 0.0, 'max': voltage_range,
             'tip': 'Maximum allowed setpoint voltage'},
            {'title': 'Enable PID on Connect:', 'name': 'auto_enable_pid', 'type': 'bool', 
             'value': False, 'tip': 'Automatically enable PID output on connection'},
        ]},
    ]


class DAQ_Move_PyRPL_PID(DAQ_Move_base):
    """
    PyMoDAQ Actuator Plugin for Red Pitaya PID Setpoint Control.
    
    This plugin enables precise control of Red Pitaya's hardware PID controller
    setpoints through PyMoDAQ's actuator interface. It uses a centralized PyRPL
    wrapper to manage connections and prevent conflicts between multiple plugins.
    
    The plugin treats PID setpoints as actuator positions, allowing PyMoDAQ to:
    - Set absolute setpoint values (move_abs)
    - Make relative setpoint adjustments (move_rel)
    - Read current setpoint values (get_actuator_value)
    - Provide safety limits and validation
    
    Key Features:
    - Hardware PID setpoint control with ±1V range
    - Multi-channel support (PID0, PID1, PID2)
    - Thread-safe operations via PyRPL wrapper
    - Mock mode for development without hardware
    - Comprehensive error handling and status reporting
    
    Attributes:
    -----------
    controller: PyRPLConnection
        The PyRPL connection object for hardware communication
    pyrpl_manager: PyRPLManager
        Centralized manager for PyRPL connections
    pid_channel: PIDChannel
        Selected PID channel (PID0/PID1/PID2)
    mock_mode: bool
        Whether to operate in mock mode without hardware
    mock_setpoint: float
        Simulated setpoint value for mock mode
    """
    
    is_multiaxes = False
    _axis_names = ['Setpoint']
    _controller_units = 'V'  # Voltage units (Red Pitaya operates in ±1V range)
    _epsilon = 0.001  # 1mV precision for setpoint control
    data_actuator_type = DataActuatorType.DataActuator

    params = get_pid_parameters() + comon_parameters_fun(is_multiaxes=is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)

    def ini_attributes(self):
        """Initialize plugin attributes and connections."""
        # PyRPL connection management
        self.controller: Optional[PyRPLConnection] = None
        self.pyrpl_manager: PyRPLManager = PyRPLManager.get_instance()
        
        # PID configuration
        self.pid_channel: Optional[PIDChannel] = None
        self.input_channel: Optional[InputChannel] = None
        self.output_channel: Optional[OutputChannel] = None
        
        # Mock mode attributes
        self.mock_mode: bool = False
        self.mock_setpoint: float = 0.0
        
        # Configuration management
        self.config = get_pyrpl_config()
        
        # Threading support
        self.hardware_manager = ThreadedHardwareManager(
            max_workers=2, 
            status_callback=self.emit_status
        )
        
        # Connection state
        self.hostname: str = ''
        self.config_name: str = 'pymodaq'
        self.is_pid_configured: bool = False
        
        logger.debug("DAQ_Move_PyRPL_PID attributes initialized")

    def get_actuator_value(self) -> DataActuator:
        """
        Get the current PID setpoint value from the hardware.

        Returns
        -------
        DataActuator: The current setpoint value with voltage units
        """
        if self.mock_mode:
            # Return mock setpoint
            pos = DataActuator(data=self.mock_setpoint, units='V')
        else:
            if not self.controller or not self.controller.is_connected:
                logger.warning("Controller not connected, returning 0V")
                pos = DataActuator(data=0.0, units='V')
            else:
                try:
                    setpoint = self.controller.get_pid_setpoint(self.pid_channel)
                    if setpoint is not None:
                        pos = DataActuator(data=setpoint, units='V')
                    else:
                        logger.error("Failed to read PID setpoint")
                        pos = DataActuator(data=0.0, units='V')
                except Exception as e:
                    logger.error(f"Error reading PID setpoint: {e}")
                    pos = DataActuator(data=0.0, units='V')
        
        # Apply any scaling configured by user
        pos = self.get_position_with_scaling(pos)
        return pos

    def user_condition_to_reach_target(self) -> bool:
        """
        Check if the PID setpoint has reached the target value.
        
        For PID setpoint control, we consider the target reached immediately
        after setting it, as the setpoint change is instantaneous.
        
        Returns
        -------
        bool: True if target has been reached
        """
        return True  # Setpoint changes are immediate

    def close(self):
        """Terminate the communication protocol and clean up resources."""
        if self.is_master and self.controller:
            try:
                # Safely disable PID if it was enabled
                if self.is_pid_configured and not self.mock_mode:
                    self.controller.disable_pid(self.pid_channel)
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f"Disabled PID {self.pid_channel.value} before disconnect", 'log']))
                
                # Disconnect through manager
                if not self.mock_mode:
                    self.pyrpl_manager.disconnect_device(
                        self.hostname, 
                        self.config_name,
                        status_callback=self._status_callback
                    )
                
                self.emit_status(ThreadCommand('Update_Status', 
                    ['PyRPL PID controller disconnected', 'log']))
                    
            except Exception as e:
                logger.error(f"Error during PyRPL PID disconnect: {e}")
                self.emit_status(ThreadCommand('Update_Status', 
                    [f"Disconnect error: {str(e)}", 'log']))
            finally:
                self.controller = None
                self.is_pid_configured = False

    def _status_callback(self, command: ThreadCommand):
        """Internal callback for status updates from PyRPL wrapper."""
        self.emit_status(command)

    def commit_settings(self, param: Parameter):
        """
        Apply consequences of parameter changes in the plugin settings.

        Parameters
        ----------
        param: Parameter
            The parameter that was changed by the user
        """
        if param.name() in ['redpitaya_host', 'config_name', 'connection_timeout']:
            # Connection parameters changed - may need reconnection
            if self.controller and self.controller.is_connected and not self.mock_mode:
                self.emit_status(ThreadCommand('Update_Status', 
                    ['Connection parameter changed - restart plugin to apply', 'log']))
        
        elif param.name() == 'mock_mode':
            self.mock_mode = param.value()
            self.emit_status(ThreadCommand('Update_Status', 
                [f"Mock mode: {'Enabled' if self.mock_mode else 'Disabled'}", 'log']))
        
        elif param.name() in ['pid_module', 'input_channel', 'output_channel']:
            # PID configuration changed - update if connected
            if self.controller and self.controller.is_connected and not self.mock_mode:
                self._update_pid_configuration()
        
        elif param.name() in ['p_gain', 'i_gain', 'd_gain', 'min_voltage', 'max_voltage']:
            # PID parameters changed - update if connected
            if self.controller and self.controller.is_connected and not self.mock_mode:
                self._update_pid_parameters()
        
        elif param.name() == 'auto_enable_pid':
            # Auto-enable setting changed
            pass  # This only affects initialization
        
        else:
            pass  # Handle other parameters as needed

    def _update_pid_configuration(self):
        """Update PID module configuration based on current parameters."""
        try:
            # Update channel selections
            self.pid_channel = PIDChannel(self.settings.child('pid_config', 'pid_module').value())
            self.input_channel = InputChannel(self.settings.child('pid_config', 'input_channel').value())
            self.output_channel = OutputChannel(self.settings.child('pid_config', 'output_channel').value())
            
            # Create new PID configuration
            pid_config = self._create_pid_configuration()
            
            # Apply configuration
            success = self.controller.configure_pid(self.pid_channel, pid_config)
            
            if success:
                self.is_pid_configured = True
                self.emit_status(ThreadCommand('Update_Status', 
                    [f"Updated PID {self.pid_channel.value} configuration", 'log']))
            else:
                self.emit_status(ThreadCommand('Update_Status', 
                    ["Failed to update PID configuration", 'log']))
                
        except Exception as e:
            logger.error(f"Error updating PID configuration: {e}")
            self.emit_status(ThreadCommand('Update_Status', 
                [f"PID configuration error: {str(e)}", 'log']))

    def _update_pid_parameters(self):
        """Update PID parameters (gains, limits) for current configuration."""
        if not self.is_pid_configured:
            return
            
        try:
            pid_config = self._create_pid_configuration()
            success = self.controller.configure_pid(self.pid_channel, pid_config)
            
            if success:
                self.emit_status(ThreadCommand('Update_Status', 
                    ["Updated PID parameters", 'log']))
            else:
                self.emit_status(ThreadCommand('Update_Status', 
                    ["Failed to update PID parameters", 'log']))
                
        except Exception as e:
            logger.error(f"Error updating PID parameters: {e}")
            self.emit_status(ThreadCommand('Update_Status', 
                [f"PID parameter update error: {str(e)}", 'log']))

    def _create_pid_configuration(self) -> PIDConfiguration:
        """Create PID configuration from current parameter values."""
        return PIDConfiguration(
            setpoint=0.0,  # Will be set by move commands
            p_gain=self.settings.child('pid_params', 'p_gain').value(),
            i_gain=self.settings.child('pid_params', 'i_gain').value(),
            d_gain=self.settings.child('pid_params', 'd_gain').value(),
            input_channel=self.input_channel,
            output_channel=self.output_channel,
            voltage_limit_min=self.settings.child('safety_limits', 'min_voltage').value(),
            voltage_limit_max=self.settings.child('safety_limits', 'max_voltage').value(),
            enabled=self.settings.child('safety_limits', 'auto_enable_pid').value()
        )

    def ini_stage(self, controller=None):
        """
        Initialize the PID controller stage.

        Parameters
        ----------
        controller: object, optional
            Shared controller object for multi-plugin setups (slave mode)

        Returns
        -------
        info: str
            Initialization information message
        initialized: bool
            True if initialization successful, False otherwise
        """
        try:
            self.emit_status(ThreadCommand('Update_Status', ['Initializing PyRPL PID Controller...', 'log']))
            
            # Extract connection parameters
            self.hostname = self.settings.child('connection_settings', 'redpitaya_host').value()
            self.config_name = self.settings.child('connection_settings', 'config_name').value()
            self.mock_mode = self.settings.child('connection_settings', 'mock_mode').value()
            connection_timeout = self.settings.child('connection_settings', 'connection_timeout').value()
            
            # Extract PID configuration
            self.pid_channel = PIDChannel(self.settings.child('pid_config', 'pid_module').value())
            self.input_channel = InputChannel(self.settings.child('pid_config', 'input_channel').value())
            self.output_channel = OutputChannel(self.settings.child('pid_config', 'output_channel').value())
            
            if self.is_master:
                if self.mock_mode:
                    # Mock mode initialization
                    self.controller = None  # No real controller needed
                    self.mock_setpoint = 0.0
                    info = f"PyRPL PID Controller initialized in MOCK mode (PID: {self.pid_channel.value})"
                    self.emit_status(ThreadCommand('Update_Status', [info, 'log']))
                    return info, True
                
                else:
                    # Real hardware initialization
                    self.controller = self.pyrpl_manager.connect_device(
                        hostname=self.hostname,
                        config_name=self.config_name,
                        status_callback=self._status_callback,
                        connection_timeout=connection_timeout
                    )
                    
                    if not self.controller or not self.controller.is_connected:
                        error_msg = f"Failed to connect to Red Pitaya at {self.hostname}"
                        self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                        return error_msg, False
                    
                    # Configure PID controller
                    pid_config = self._create_pid_configuration()
                    success = self.controller.configure_pid(self.pid_channel, pid_config)
                    
                    if not success:
                        error_msg = f"Failed to configure PID {self.pid_channel.value}"
                        self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                        return error_msg, False
                    
                    self.is_pid_configured = True
                    
                    # Get connection info for status
                    conn_info = self.controller.get_connection_info()
                    info = (f"PyRPL PID Controller connected to {self.hostname} "
                           f"(PID: {self.pid_channel.value}, "
                           f"State: {conn_info['state']})")
                    
                    self.emit_status(ThreadCommand('Update_Status', [info, 'log']))
                    return info, True
            
            else:
                # Slave mode - use shared controller
                self.controller = controller
                if self.controller and hasattr(self.controller, 'is_connected'):
                    initialized = self.controller.is_connected
                else:
                    initialized = True  # Assume slave initialization is OK
                
                info = f"PyRPL PID Controller initialized in slave mode (PID: {self.pid_channel.value})"
                self.emit_status(ThreadCommand('Update_Status', [info, 'log']))
                return info, initialized
                
        except Exception as e:
            error_msg = f"PyRPL PID initialization failed: {str(e)}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            return error_msg, False

    def move_abs(self, value: DataActuator):
        """
        Move the PID setpoint to an absolute target value.

        Parameters
        ----------
        value: DataActuator
            Absolute target setpoint voltage value
        """
        # Apply bounds checking
        value = self.check_bound(value)
        self.target_value = value
        
        # Apply scaling if configured
        value = self.set_position_with_scaling(value)
        
        # Extract voltage value
        voltage_value = value.value('V')
        
        if self.mock_mode:
            # Mock mode operation
            self.mock_setpoint = voltage_value
            self.emit_status(ThreadCommand('Update_Status', 
                [f"Mock PID setpoint set to {voltage_value:.3f}V", 'log']))
        else:
            if not self.controller or not self.controller.is_connected:
                error_msg = "Cannot set setpoint: controller not connected"
                logger.error(error_msg)
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                return
            
            try:
                success = self.controller.set_pid_setpoint(self.pid_channel, voltage_value)
                
                if success:
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f"PID {self.pid_channel.value} setpoint set to {voltage_value:.3f}V", 'log']))
                else:
                    error_msg = f"Failed to set PID setpoint to {voltage_value:.3f}V"
                    logger.error(error_msg)
                    self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                    
            except Exception as e:
                error_msg = f"Error setting PID setpoint: {str(e)}"
                logger.error(error_msg)
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def move_rel(self, value: DataActuator):
        """
        Move the PID setpoint by a relative amount.

        Parameters
        ----------
        value: DataActuator
            Relative change in setpoint voltage value
        """
        # Calculate new absolute position with bounds checking
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        
        # Apply scaling if configured
        value = self.set_position_relative_with_scaling(value)
        
        # Calculate absolute target
        current_setpoint = self.get_actuator_value().value('V')
        new_setpoint = current_setpoint + value.value('V')
        
        if self.mock_mode:
            # Mock mode operation
            self.mock_setpoint = new_setpoint
            self.emit_status(ThreadCommand('Update_Status', 
                [f"Mock PID setpoint adjusted by {value.value('V'):+.3f}V to {new_setpoint:.3f}V", 'log']))
        else:
            if not self.controller or not self.controller.is_connected:
                error_msg = "Cannot adjust setpoint: controller not connected"
                logger.error(error_msg)
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                return
            
            try:
                success = self.controller.set_pid_setpoint(self.pid_channel, new_setpoint)
                
                if success:
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f"PID {self.pid_channel.value} setpoint adjusted by "
                         f"{value.value('V'):+.3f}V to {new_setpoint:.3f}V", 'log']))
                else:
                    error_msg = f"Failed to adjust PID setpoint by {value.value('V'):+.3f}V"
                    logger.error(error_msg)
                    self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                    
            except Exception as e:
                error_msg = f"Error adjusting PID setpoint: {str(e)}"
                logger.error(error_msg)
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def move_home(self):
        """
        Move the PID setpoint to the home position (zero volts).
        
        This provides a known reference position for the PID controller.
        """
        home_position = DataActuator(data=0.0, units='V')
        
        self.emit_status(ThreadCommand('Update_Status', 
            ['Moving PID setpoint to home position (0V)', 'log']))
        
        # Use move_abs to go to zero position
        self.move_abs(home_position)

    def stop_motion(self):
        """
        Stop any ongoing motion and maintain current setpoint.
        
        For PID setpoint control, this doesn't stop physical motion but
        ensures the current setpoint is maintained.
        """
        if self.mock_mode:
            self.emit_status(ThreadCommand('Update_Status', 
                [f"Mock PID motion stopped at {self.mock_setpoint:.3f}V", 'log']))
        else:
            if self.controller and self.controller.is_connected:
                try:
                    # Read current setpoint to confirm it's stable
                    current_setpoint = self.controller.get_pid_setpoint(self.pid_channel)
                    if current_setpoint is not None:
                        self.emit_status(ThreadCommand('Update_Status', 
                            [f"PID {self.pid_channel.value} motion stopped at {current_setpoint:.3f}V", 'log']))
                    else:
                        self.emit_status(ThreadCommand('Update_Status', 
                            [f"PID {self.pid_channel.value} motion stopped", 'log']))
                except Exception as e:
                    logger.error(f"Error in stop_motion: {e}")
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f"PID motion stopped (status read error: {str(e)})", 'log']))
            else:
                self.emit_status(ThreadCommand('Update_Status', 
                    ["PID motion stopped (controller not connected)", 'log']))


if __name__ == '__main__':
    main(__file__)