# -*- coding: utf-8 -*-
"""
PyMoDAQ Actuator Plugin for Red Pitaya PyRPL Arbitrary Signal Generator (Direct Mode)

This plugin provides simplified PyMoDAQ actuator functionality for controlling Red Pitaya's
Arbitrary Signal Generator (ASG) using direct PyRPL access (no multiprocessing).

Features:
    - Hardware ASG frequency control
    - Dual-channel ASG support (ASG0/ASG1)
    - Multiple waveforms: sin, square, ramp, triangle
    - Amplitude and offset control
    - Thread-safe shared PyRPL instance
    - Simpler architecture than the IPC-based ASG plugin

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

Note:
    This is the "Direct" version using PyRPLPluginBase. For the IPC-based version
    with multiprocessing isolation, use daq_move_PyRPL_ASG.py instead.

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


class DAQ_Move_PyRPL_ASG_Direct(DAQ_Move_base, PyRPLPluginBase):
    """
    PyMoDAQ plugin for Red Pitaya ASG using direct PyRPL access.
    
    This plugin provides control over one of the two ASG modules (asg0, asg1)
    on the Red Pitaya. It uses a shared PyRPL instance managed by PyRPLPluginBase,
    allowing multiple ASG plugins (and other PyRPL plugins) to coexist safely.
    
    The 'position' of this actuator corresponds to the ASG frequency in Hz.
    """
    
    # Plugin metadata
    is_multiaxes = False
    _controller_units = 'Hz'  # ASG frequency is in Hz
    _epsilon = 1.0  # Precision for frequency (1 Hz)
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
            {'title': 'ASG Module:', 'name': 'asg_module', 'type': 'list',
             'limits': ['asg0', 'asg1'],
             'value': 'asg0',
             'tip': 'Which ASG module to control (Red Pitaya has 2 independent ASGs)'},
        ]},
        {'title': 'Signal Settings:', 'name': 'signal_settings', 'type': 'group', 'children': [
            {'title': 'Frequency (Hz):', 'name': 'frequency', 'type': 'float',
             'value': 1000.0, 'min': 0.0, 'max': 62.5e6, 'suffix': 'Hz', 'siPrefix': True,
             'tip': 'Signal frequency (0 Hz to 62.5 MHz)'},
            {'title': 'Amplitude (V):', 'name': 'amplitude', 'type': 'float',
             'value': 0.1, 'min': 0.0, 'max': 1.0, 'suffix': 'V', 'siPrefix': True,
             'tip': 'Signal amplitude (0 to 1 V)'},
            {'title': 'Offset (V):', 'name': 'offset', 'type': 'float',
             'value': 0.0, 'min': -1.0, 'max': 1.0, 'suffix': 'V', 'siPrefix': True,
             'tip': 'DC offset (-1 to 1 V)'},
            {'title': 'Waveform:', 'name': 'waveform', 'type': 'list',
             'limits': ['sin', 'square', 'ramp', 'triangle', 'halframp'],
             'value': 'sin',
             'tip': 'Waveform type'},
        ]},
        {'title': 'Output:', 'name': 'output', 'type': 'group', 'children': [
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2', 'both'],
             'value': 'off',
             'tip': 'Direct output routing (off = no output, out1/out2 = analog output)'},
        ]},
    ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)
    
    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller = None  # Will hold the PyRPL ASG module
        self.hostname = None
        self.config = None
        self.asg_module_name = None
    
    def get_actuator_value(self) -> DataActuator:
        """
        Get the current ASG frequency.
        
        Returns:
            DataActuator containing the current frequency in Hz
        """
        try:
            if self.controller is None:
                return DataActuator(data=0.0, units='Hz')
            
            # Read current frequency from hardware
            current_freq = self.controller.frequency
            
            return DataActuator(data=current_freq, units='Hz')
            
        except Exception as e:
            logger.error(f"Error reading ASG frequency: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Error reading frequency: {e}', 'log']))
            return DataActuator(data=0.0, units='Hz')
    
    def close(self):
        """
        Close the plugin.
        
        Note: We don't close the shared PyRPL instance here because other plugins
        might still be using it. PyMoDAQ will handle the proper shutdown order.
        """
        if self.is_master:
            logger.info(f"Closing ASG plugin ({self.asg_module_name})")
            # Turn off output before closing
            try:
                if self.controller is not None:
                    self.controller.output_direct = 'off'
            except:
                pass
    
    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes from the GUI.
        
        Args:
            param: Parameter that was changed by the user
        """
        try:
            if self.controller is None:
                return
            
            # Handle signal settings changes
            if param.parent().name() == 'signal_settings':
                if param.name() == 'frequency':
                    self.controller.frequency = param.value()
                    logger.debug(f"ASG frequency updated: {param.value()} Hz")
                    
                elif param.name() == 'amplitude':
                    self.controller.amplitude = param.value()
                    logger.debug(f"ASG amplitude updated: {param.value()} V")
                    
                elif param.name() == 'offset':
                    self.controller.offset = param.value()
                    logger.debug(f"ASG offset updated: {param.value()} V")
                    
                elif param.name() == 'waveform':
                    self.controller.waveform = param.value()
                    logger.debug(f"ASG waveform updated: {param.value()}")
            
            # Handle output routing changes
            elif param.parent().name() == 'output':
                if param.name() == 'output_direct':
                    self.controller.output_direct = param.value()
                    logger.debug(f"ASG output_direct changed: {param.value()}")
        
        except Exception as e:
            logger.error(f"Error in commit_settings: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Settings error: {e}', 'log']))
    
    def ini_stage(self, controller=None) -> tuple:
        """
        Initialize the ASG controller.
        
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
                self.asg_module_name = self.settings.child('connection', 'asg_module').value()
                
                logger.info(f"Initializing ASG plugin: {self.asg_module_name} @ {self.hostname}")
                
                # Get shared PyRPL instance (creates it if needed)
                pyrpl = self.get_shared_pyrpl(
                    hostname=self.hostname,
                    config=self.config,
                    gui=False  # No GUI for PyMoDAQ integration
                )
                
                # Get the specific ASG module
                self.controller = self.get_module(self.asg_module_name)
                
                # Apply initial settings from GUI
                self.controller.frequency = self.settings.child('signal_settings', 'frequency').value()
                self.controller.amplitude = self.settings.child('signal_settings', 'amplitude').value()
                self.controller.offset = self.settings.child('signal_settings', 'offset').value()
                self.controller.waveform = self.settings.child('signal_settings', 'waveform').value()
                self.controller.output_direct = self.settings.child('output', 'output_direct').value()
                
                info = f"✓ Connected to {self.asg_module_name} on {self.hostname}"
                logger.info(info)
                return info, True
                
            else:
                # Slave mode (shared controller)
                self.controller = controller
                return "Slave mode initialized", True
        
        except Exception as e:
            error_msg = f"Failed to initialize ASG: {e}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            return error_msg, False
    
    def move_abs(self, value: DataActuator):
        """
        Move to absolute frequency value.
        
        Args:
            value: Target frequency value in Hz
        """
        try:
            # Apply bounds checking if enabled
            value = self.check_bound(value)
            
            # Update target value
            self.target_value = value
            
            # Apply scaling if configured
            value = self.set_position_with_scaling(value)
            
            # Set the ASG frequency
            frequency_hz = value.value(self.axis_unit)
            self.controller.frequency = frequency_hz
            
            # Update GUI
            self.settings.child('signal_settings', 'frequency').setValue(frequency_hz)
            
            logger.debug(f"ASG frequency set to: {frequency_hz} Hz")
            self.emit_status(ThreadCommand('Update_Status', 
                [f'Frequency: {frequency_hz:.2f} Hz', 'log']))
        
        except Exception as e:
            logger.error(f"Error in move_abs: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Move error: {e}', 'log']))
    
    def move_rel(self, value: DataActuator):
        """
        Move relative to current frequency.
        
        Args:
            value: Relative change in frequency (Hz)
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
        Home the ASG - set frequency to 1 kHz (default reference).
        """
        try:
            # Set to default frequency
            default_freq = 1000.0  # 1 kHz
            self.controller.frequency = default_freq
            
            # Update GUI
            self.settings.child('signal_settings', 'frequency').setValue(default_freq)
            
            logger.info(f"ASG homed to {default_freq} Hz")
            self.emit_status(ThreadCommand('Update_Status', 
                [f'ASG homed to {default_freq} Hz', 'log']))
        
        except Exception as e:
            logger.error(f"Error in move_home: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Home error: {e}', 'log']))
    
    def stop_motion(self):
        """
        Stop motion - for ASG, we can disable the output.
        """
        try:
            # Disable output
            self.controller.output_direct = 'off'
            
            # Update GUI
            self.settings.child('output', 'output_direct').setValue('off')
            
            logger.info("ASG output disabled")
            self.emit_status(ThreadCommand('Update_Status', ['ASG output disabled', 'log']))
        
        except Exception as e:
            logger.error(f"Error in stop_motion: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Stop error: {e}', 'log']))


if __name__ == '__main__':
    main(__file__)
