# -*- coding: utf-8 -*-
"""
PyMoDAQ 1D Viewer Plugin for Red Pitaya PyRPL Oscilloscope

This plugin provides PyMoDAQ 1D viewer functionality for the PyRPL oscilloscope,
enabling real-time waveform capture and visualization from Red Pitaya hardware.

Features:
    - Real-time oscilloscope data acquisition
    - Configurable input channels (in1, in2)
    - Trigger configuration (immediate, edge-triggered)
    - Adjustable sampling rate (decimation)
    - Duration control
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

import numpy as np
from typing import Optional

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base, comon_parameters, main
)
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from pymodaq_data.data import DataToExport
import logging

# Import the shared PyRPL base class
from ...utils.pyrpl_plugin_base import PyRPLPluginBase

logger = logging.getLogger(__name__)


class DAQ_1Dviewer_PyRPL_Scope(DAQ_Viewer_base, PyRPLPluginBase):
    """
    PyMoDAQ plugin for Red Pitaya oscilloscope using direct PyRPL access.
    
    This plugin provides 1D data acquisition from the Red Pitaya scope module.
    It uses a shared PyRPL instance managed by PyRPLPluginBase, allowing multiple
    plugins to coexist safely.
    """
    
    # Parameters shown in PyMoDAQ settings tree
    params = comon_parameters + [
        {'title': 'Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya Host:', 'name': 'hostname', 'type': 'str',
             'value': 'rp-f08d6c.local',
             'tip': 'Red Pitaya IP address or hostname (e.g., rp-f08d6c.local or 192.168.1.100)'},
            {'title': 'Config Name:', 'name': 'config', 'type': 'str',
             'value': 'pymodaq',
             'tip': 'PyRPL configuration name (used for saving settings)'},
        ]},
        {'title': 'Scope Settings:', 'name': 'scope_settings', 'type': 'group', 'children': [
            {'title': 'Input Channel:', 'name': 'input', 'type': 'list',
             'limits': ['in1', 'in2', 'asg0', 'asg1'],
             'value': 'in1',
             'tip': 'Oscilloscope input channel (in1/in2 = physical inputs, asg0/asg1 = internal signals)'},
            {'title': 'Duration (ms):', 'name': 'duration', 'type': 'float',
             'value': 1.0, 'min': 0.001, 'max': 1000.0, 'suffix': 'ms', 'siPrefix': True,
             'tip': 'Acquisition duration in milliseconds'},
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
             'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge',
                       'ch2_positive_edge', 'ch2_negative_edge'],
             'value': 'immediately',
             'tip': 'Trigger condition for data acquisition'},
            {'title': 'Trigger Threshold (V):', 'name': 'threshold', 'type': 'float',
             'value': 0.0, 'suffix': 'V', 'siPrefix': True,
             'tip': 'Trigger threshold level in volts'},
            {'title': 'Averaging:', 'name': 'average', 'type': 'bool',
             'value': False,
             'tip': 'Enable trace averaging (reduces noise)'},
        ]},
    ]
    
    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller = None  # Will hold the PyRPL scope module
        self.hostname = None
        self.config = None
    
    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes from the GUI.
        
        Args:
            param: Parameter that was changed by the user
        """
        try:
            if self.controller is None:
                return
            
            # Handle scope settings changes
            if param.parent().name() == 'scope_settings':
                if param.name() == 'input':
                    self.controller.input1 = param.value()
                    logger.debug(f"Scope input changed: {param.value()}")
                    
                elif param.name() == 'duration':
                    # Convert ms to seconds
                    duration_s = param.value() / 1000.0
                    self.controller.duration = duration_s
                    logger.debug(f"Scope duration changed: {duration_s} s")
                    
                elif param.name() == 'trigger_source':
                    self.controller.trigger_source = param.value()
                    logger.debug(f"Trigger source changed: {param.value()}")
                    
                elif param.name() == 'threshold':
                    self.controller.threshold = param.value()
                    logger.debug(f"Trigger threshold changed: {param.value()} V")
                    
                elif param.name() == 'average':
                    self.controller.average = param.value()
                    logger.debug(f"Averaging: {param.value()}")
        
        except Exception as e:
            logger.error(f"Error in commit_settings: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Settings error: {e}', 'log']))
    
    def ini_detector(self, controller=None):
        """
        Initialize the oscilloscope detector.
        
        Args:
            controller: Shared controller (for slave mode). None for master mode.
        
        Returns:
            Initialization status message
        """
        try:
            if self.is_master:
                # Get connection parameters
                self.hostname = self.settings.child('connection', 'hostname').value()
                self.config = self.settings.child('connection', 'config').value()
                
                logger.info(f"Initializing Scope plugin @ {self.hostname}")
                
                # Get shared PyRPL instance (creates it if needed)
                pyrpl = self.get_shared_pyrpl(
                    hostname=self.hostname,
                    config=self.config,
                    gui=False  # No GUI for PyMoDAQ integration
                )
                
                # Get the scope module
                self.controller = self.get_module('scope')
                
                # Apply initial settings from GUI
                self.controller.input1 = self.settings.child('scope_settings', 'input').value()
                duration_ms = self.settings.child('scope_settings', 'duration').value()
                self.controller.duration = duration_ms / 1000.0  # Convert to seconds
                self.controller.trigger_source = self.settings.child('scope_settings', 'trigger_source').value()
                self.controller.threshold = self.settings.child('scope_settings', 'threshold').value()
                self.controller.average = self.settings.child('scope_settings', 'average').value()
                
                info = f"✓ Connected to Scope on {self.hostname}"
                logger.info(info)
                initialized = True
                
            else:
                # Slave mode (shared controller)
                self.controller = controller
                info = "Slave mode initialized"
                initialized = True
            
            # Optional: Send initial data structure to PyMoDAQ
            # This helps PyMoDAQ configure its display
            # (We'll send real data in grab_data())
            
            return info, initialized
        
        except Exception as e:
            error_msg = f"Failed to initialize Scope: {e}"
            logger.error(error_msg)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            return error_msg, False
    
    def close(self):
        """
        Close the plugin.
        
        Note: We don't close the shared PyRPL instance here because other plugins
        might still be using it.
        """
        if self.is_master:
            logger.info("Closing Scope plugin")
            # Just log that we're closing; don't close shared PyRPL
    
    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquire oscilloscope trace.
        
        This is a SYNCHRONOUS acquisition - it triggers the scope, waits for
        data capture to complete, then returns the data.
        
        Args:
            Naverage: Number of averages (if hardware averaging enabled)
            **kwargs: Additional parameters (not used)
        """
        try:
            if self.controller is None:
                raise RuntimeError("Scope not initialized")
            
            # Trigger the scope
            self.controller.trigger()
            
            # Wait for acquisition to complete
            # PyRPL scope has an is_running() method to check status
            timeout = 10.0  # Maximum wait time in seconds
            start_time = 0
            while self.controller.is_running():
                if start_time > timeout:
                    raise TimeoutError(f"Scope acquisition timed out after {timeout}s")
                import time
                time.sleep(0.01)  # 10 ms polling interval
                start_time += 0.01
            
            # Get the data
            trace = self.controller.curve()  # Returns numpy array
            times = self.controller.times  # Time axis (numpy array)
            
            # Validate data
            if trace is None or len(trace) == 0:
                raise ValueError("Scope returned empty data")
            
            # Create PyMoDAQ data structure
            # For 1D viewer, we need DataFromPlugins with proper axis
            data_array = np.atleast_1d(trace)
            time_array = np.atleast_1d(times)
            
            # Create axis object
            time_axis = Axis(
                label='Time',
                units='s',
                data=time_array,
                index=0
            )
            
            # Create data object
            data_obj = DataFromPlugins(
                name='PyRPL_Scope',
                data=[data_array],
                dim='Data1D',
                labels=['Voltage (V)'],
                axes=[time_axis]
            )
            
            # Emit data to PyMoDAQ
            self.dte_signal.emit(DataToExport(
                name='PyRPL_Scope',
                data=[data_obj]
            ))
            
            logger.debug(f"Scope data acquired: {len(trace)} points")
        
        except Exception as e:
            logger.error(f"Error in grab_data: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Acquisition error: {e}', 'log']))
            
            # Emit empty data on error
            empty_data = DataFromPlugins(
                name='PyRPL_Scope',
                data=[np.array([0])],
                dim='Data1D',
                labels=['Error'],
                axes=[Axis(label='Time', units='s', data=np.array([0]), index=0)]
            )
            self.dte_signal.emit(DataToExport(name='PyRPL_Scope', data=[empty_data]))
    
    def stop(self):
        """
        Stop the current acquisition.
        """
        try:
            if self.controller is not None:
                # PyRPL scope doesn't have an explicit stop, but we can just return
                logger.info("Scope acquisition stop requested")
                self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped', 'log']))
        
        except Exception as e:
            logger.error(f"Error in stop: {e}")


if __name__ == '__main__':
    main(__file__)
