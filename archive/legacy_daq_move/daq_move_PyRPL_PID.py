# -*- coding: utf-8 -*-
"""
PyMoDAQ Actuator Plugin for Red Pitaya PyRPL PID Controller

This plugin provides PyMoDAQ actuator functionality for controlling Red Pitaya's
PID controller modules via the PyRPL library. It enables closed-loop control for
laser locking, cavity stabilization, and other feedback control applications.

Features:
    - Hardware PID control (Red Pitaya STEMlab)
    - Three independent PID controllers (PID0, PID1, PID2)
    - Full P, I, D gain control
    - Input/output signal routing
    - Integrator monitoring and reset
    - Thread-safe shared PyRPL instance

Compatible Controllers:
    - Red Pitaya STEMlab 125-10/125-14
    - PyRPL firmware and library

Tested Configuration:
    - PyMoDAQ 4.0+
    - PyRPL 0.9.5+
    - Red Pitaya STEMlab 125-14

Installation Requirements:
    - PyRPL library: `pip install pyrpl`
    - Red Pitaya network connection and PyRPL firmware

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

from typing import Union, List
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun,
    main, DataActuatorType, DataActuator
)

from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
import logging

# Import the shared PyRPL base class
from ..utils.pyrpl_plugin_base import PyRPLPluginBase

logger = logging.getLogger(__name__)


class DAQ_Move_PyRPL_PID(DAQ_Move_base, PyRPLPluginBase):
    """
    PyMoDAQ plugin for Red Pitaya PID controller using direct PyRPL access.
    
    This plugin provides control over one of the three PID modules (pid0, pid1, pid2)
    on the Red Pitaya. It uses a shared PyRPL instance managed by PyRPLPluginBase,
    allowing multiple PID plugins (and other PyRPL plugins) to coexist safely.
    
    The 'position' of this actuator corresponds to the PID setpoint value.
    """
    
    # Plugin metadata
    is_multiaxes = False
    _controller_units = 'V'  # PID setpoint is in volts
    _epsilon = 0.001  # Precision for target reached (1 mV)
    data_actuator_type = DataActuatorType.DataActuator
    
    # Parameters shown in PyMoDAQ settings tree
    params = [
        {'title': 'Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya Host:', 'name': 'hostname', 'type': 'str',
             'value': 'rp-f08d6c.local',
             'tip': 'Red Pitaya IP address or hostname (e.g., rp-f08d6c.local or 192.168.1.100)'},
            {'title': 'Config Name:', 'name': 'config', 'type': 'str',
             'value': 'pymodaq',
             'tip': 'PyRPL configuration name (used for saving settings)'},
            {'title': 'PID Module:', 'name': 'pid_module', 'type': 'list',
             'limits': ['pid0', 'pid1', 'pid2'],
             'value': 'pid0',
             'tip': 'Which PID module to control (Red Pitaya has 3 independent PIDs)'},
        ]},
        {'title': 'PID Settings:', 'name': 'pid_settings', 'type': 'group', 'children': [
            {'title': 'Setpoint (V):', 'name': 'setpoint', 'type': 'float',
             'value': 0.0, 'suffix': 'V', 'siPrefix': True,
             'tip': 'PID setpoint - target value for the control loop'},
            {'title': 'P Gain:', 'name': 'p', 'type': 'float',
             'value': 0.0, 'siPrefix': True,
             'tip': 'Proportional gain'},
            {'title': 'I Gain:', 'name': 'i', 'type': 'float',
             'value': 0.0, 'siPrefix': True,
             'tip': 'Integral gain'},
            {'title': 'D Gain:', 'name': 'd', 'type': 'float',
             'value': 0.0, 'siPrefix': True,
             'tip': 'Derivative gain (not implemented in current PyRPL version)'},
        ]},
        {'title': 'Input/Output:', 'name': 'io', 'type': 'group', 'children': [
            {'title': 'Input:', 'name': 'input', 'type': 'list',
             'limits': ['in1', 'in2', 'iq0', 'iq1', 'iq2', 'asg0', 'asg1'],
             'value': 'in1',
             'tip': 'PID input signal source'},
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2', 'both'],
             'value': 'off',
             'tip': 'Direct output routing (off = no output, out1/out2 = analog output)'},
        ]},
        {'title': 'Actions:', 'name': 'actions', 'type': 'group', 'children': [
            {'title': 'Reset Integrator', 'name': 'reset_integrator', 'type': 'action',
             'tip': 'Reset the integral term to zero'},
            {'title': 'Read Integrator', 'name': 'read_integrator', 'type': 'float',
             'value': 0.0, 'readonly': True, 'suffix': 'V',
             'tip': 'Current integrator value (read-only)'},
        ]},
    ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)
    
    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller = None  # Will hold the PyRPL PID module
        self.hostname = None
        self.config = None
        self.pid_module_name = None
    
    def get_actuator_value(self) -> DataActuator:
        """
        Get the current PID setpoint value.
        
        Returns:
            DataActuator containing the current setpoint in volts
        """
        try:
            if self.controller is None:
                return DataActuator(data=0.0, units='V')
            
            # Read current setpoint from hardware
            current_setpoint = self.controller.setpoint
            
            return DataActuator(data=current_setpoint, units='V')
            
        except Exception as e:
            logger.error(f"Error reading PID setpoint: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Error reading setpoint: {e}', 'log']))
            return DataActuator(data=0.0, units='V')
    
    def close(self):
        """
        Close the plugin.
        
        Note: We don't close the shared PyRPL instance here because other plugins
        might still be using it. PyMoDAQ will handle the proper shutdown order.
        """
        if self.is_master:
            logger.info(f"Closing PID plugin ({self.pid_module_name})")
            # Just log that we're closing; don't close shared PyRPL
            # The shared instance will be closed when ALL plugins are closed
    
    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes from the GUI.
        
        Args:
            param: Parameter that was changed by the user
        """
        try:
            if self.controller is None:
                return
            
            # Handle PID settings changes
            if param.parent().name() == 'pid_settings':
                if param.name() == 'setpoint':
                    self.controller.setpoint = param.value()
                    logger.debug(f"PID setpoint updated: {param.value()} V")
                    
                elif param.name() == 'p':
                    self.controller.p = param.value()
                    logger.debug(f"PID P gain updated: {param.value()}")
                    
                elif param.name() == 'i':
                    self.controller.i = param.value()
                    logger.debug(f"PID I gain updated: {param.value()}")
                    
                elif param.name() == 'd':
                    # D gain not implemented in current PyRPL
                    logger.warning("D gain not supported by PyRPL PID")
            
            # Handle I/O routing changes
            elif param.parent().name() == 'io':
                if param.name() == 'input':
                    self.controller.input = param.value()
                    logger.debug(f"PID input changed: {param.value()}")
                    
                elif param.name() == 'output_direct':
                    self.controller.output_direct = param.value()
                    logger.debug(f"PID output_direct changed: {param.value()}")
            
            # Handle actions
            elif param.parent().name() == 'actions':
                if param.name() == 'reset_integrator':
                    self.controller.integrator = 0.0
                    # Update the read-only display
                    self.settings.child('actions', 'read_integrator').setValue(0.0)
                    self.emit_status(ThreadCommand('Update_Status', ['Integrator reset to zero', 'log']))
                    logger.info("PID integrator reset")
        
        except Exception as e:
            logger.error(f"Error in commit_settings: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Settings error: {e}', 'log']))
    
    def ini_stage(self, controller=None) -> tuple:
        """
        Initialize the PID controller.
        
        Args:
            controller: Shared controller (for slave mode). None for master mode.
        
        Returns:
            Tuple of (info_message, initialized_success)
        """
        try:
            if self.is_master:
                # Get connection parameters
                self.hostname = self.settings.child('connection', 'hostname').value()
                self.config = self.settings.child('connection', 'config').value()
                self.pid_module_name = self.settings.child('connection', 'pid_module').value()
                
                logger.info(f"Initializing PID plugin: {self.pid_module_name} @ {self.hostname}")
                
                # Get shared PyRPL instance (creates it if needed)
                pyrpl = self.get_shared_pyrpl(
                    hostname=self.hostname,
                    config=self.config,
                    gui=False  # No GUI for PyMoDAQ integration
                )
                
                # Get the specific PID module
                self.controller = self.get_module(self.pid_module_name)
                
                # Apply initial settings from GUI
                self.controller.setpoint = self.settings.child('pid_settings', 'setpoint').value()
                self.controller.p = self.settings.child('pid_settings', 'p').value()
                self.controller.i = self.settings.child('pid_settings', 'i').value()
                self.controller.input = self.settings.child('io', 'input').value()
                self.controller.output_direct = self.settings.child('io', 'output_direct').value()
                
                # Update integrator display
                integrator_value = self.controller.integrator
                self.settings.child('actions', 'read_integrator').setValue(integrator_value)
                
                info = f"✓ Connected to {self.pid_module_name} on {self.hostname}"
                logger.info(info)
                return info, True
                
            else:
                # Slave mode (shared controller)
                self.controller = controller
                return "Slave mode initialized", True
        
        except Exception as e:
            error_msg = f"Failed to initialize PID: {e}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            return error_msg, False
    
    def move_abs(self, value: DataActuator):
        """
        Move to absolute setpoint value.
        
        Args:
            value: Target setpoint value in volts
        """
        try:
            # Apply bounds checking if enabled
            value = self.check_bound(value)
            
            # Update target value
            self.target_value = value
            
            # Apply scaling if configured
            value = self.set_position_with_scaling(value)
            
            # Set the PID setpoint
            setpoint_volts = value.value(self.axis_unit)
            self.controller.setpoint = setpoint_volts
            
            # Update GUI
            self.settings.child('pid_settings', 'setpoint').setValue(setpoint_volts)
            
            logger.debug(f"PID setpoint set to: {setpoint_volts} V")
            self.emit_status(ThreadCommand('Update_Status', 
                [f'Setpoint: {setpoint_volts:.4f} V', 'log']))
        
        except Exception as e:
            logger.error(f"Error in move_abs: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Move error: {e}', 'log']))
    
    def move_rel(self, value: DataActuator):
        """
        Move relative to current setpoint.
        
        Args:
            value: Relative change in setpoint (volts)
        """
        try:
            # Calculate new absolute position
            current = self.get_actuator_value()
            new_value = current + value
            
            # Use move_abs for the actual move
            self.move_abs(new_value)
        
        except Exception as e:
            logger.error(f"Error in move_rel: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Relative move error: {e}', 'log']))
    
    def move_home(self):
        """
        Home the PID - reset integrator and set setpoint to zero.
        """
        try:
            # Reset integrator
            self.controller.integrator = 0.0
            
            # Set setpoint to zero
            self.controller.setpoint = 0.0
            
            # Update GUI
            self.settings.child('pid_settings', 'setpoint').setValue(0.0)
            self.settings.child('actions', 'read_integrator').setValue(0.0)
            
            logger.info("PID homed: integrator reset, setpoint = 0")
            self.emit_status(ThreadCommand('Update_Status', 
                ['PID homed (integrator reset, setpoint = 0)', 'log']))
        
        except Exception as e:
            logger.error(f"Error in move_home: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Home error: {e}', 'log']))
    
    def stop_motion(self):
        """
        Stop motion - for PID, we can disable the output.
        """
        try:
            # Disable output
            self.controller.output_direct = 'off'
            
            # Update GUI
            self.settings.child('io', 'output_direct').setValue('off')
            
            logger.info("PID output disabled")
            self.emit_status(ThreadCommand('Update_Status', ['PID output disabled', 'log']))
        
        except Exception as e:
            logger.error(f"Error in stop_motion: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Stop error: {e}', 'log']))


if __name__ == '__main__':
    main(__file__)
