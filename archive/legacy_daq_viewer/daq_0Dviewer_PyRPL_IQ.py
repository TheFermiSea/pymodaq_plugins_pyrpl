# -*- coding: utf-8 -*-
"""
PyMoDAQ 0D Viewer Plugin for Red Pitaya PyRPL IQ Demodulator

This plugin provides PyMoDAQ 0D viewer functionality for the PyRPL IQ demodulation modules,
enabling lock-in detection and phase-sensitive measurements from Red Pitaya hardware.

Features:
    - IQ demodulation (lock-in amplifier)
    - Three independent IQ modules (iq0, iq1, iq2)
    - Configurable demodulation frequency
    - Bandwidth control
    - Quadrature signal output (I and Q channels)
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
from pymodaq.utils.data import DataFromPlugins
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from pymodaq_data.data import DataToExport
import logging

# Import the shared PyRPL base class
from ...utils.pyrpl_plugin_base import PyRPLPluginBase

logger = logging.getLogger(__name__)


class DAQ_0Dviewer_PyRPL_IQ(DAQ_Viewer_base, PyRPLPluginBase):
    """
    PyMoDAQ plugin for Red Pitaya IQ demodulator using direct PyRPL access.
    
    This plugin provides 0D data acquisition (scalar I and Q values) from one of
    the three IQ demodulation modules. It uses a shared PyRPL instance managed by
    PyRPLPluginBase, allowing multiple plugins to coexist safely.
    
    The plugin returns two data channels:
        - I (in-phase component)
        - Q (quadrature component)
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
            {'title': 'IQ Module:', 'name': 'iq_module', 'type': 'list',
             'limits': ['iq0', 'iq1', 'iq2'],
             'value': 'iq0',
             'tip': 'Which IQ module to use (Red Pitaya has 3 independent IQ demodulators)'},
        ]},
        {'title': 'IQ Settings:', 'name': 'iq_settings', 'type': 'group', 'children': [
            {'title': 'Frequency (Hz):', 'name': 'frequency', 'type': 'float',
             'value': 1000.0, 'min': 0.0, 'max': 62.5e6, 'suffix': 'Hz', 'siPrefix': True,
             'tip': 'Demodulation frequency (0 Hz to 62.5 MHz)'},
            {'title': 'Bandwidth (Hz):', 'name': 'bandwidth', 'type': 'float',
             'value': 1000.0, 'min': 1.0, 'max': 1e6, 'suffix': 'Hz', 'siPrefix': True,
             'tip': 'Demodulation bandwidth (low-pass filter cutoff)'},
            {'title': 'Input:', 'name': 'input', 'type': 'list',
             'limits': ['in1', 'in2', 'asg0', 'asg1'],
             'value': 'in1',
             'tip': 'IQ input signal source'},
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2'],
             'value': 'off',
             'tip': 'Direct output routing (off = no output)'},
            {'title': 'Gain:', 'name': 'gain', 'type': 'float',
             'value': 1.0, 'min': 0.0, 'max': 100.0, 'siPrefix': True,
             'tip': 'IQ output gain factor'},
        ]},
        {'title': 'Display:', 'name': 'display', 'type': 'group', 'children': [
            {'title': 'Amplitude:', 'name': 'amplitude', 'type': 'float',
             'value': 0.0, 'readonly': True, 'suffix': 'V', 'siPrefix': True,
             'tip': 'Calculated amplitude (sqrt(I² + Q²))'},
            {'title': 'Phase (deg):', 'name': 'phase', 'type': 'float',
             'value': 0.0, 'readonly': True, 'suffix': '°',
             'tip': 'Calculated phase (atan2(Q, I))'},
        ]},
    ]
    
    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller = None  # Will hold the PyRPL IQ module
        self.hostname = None
        self.config = None
        self.iq_module_name = None
    
    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes from the GUI.
        
        Args:
            param: Parameter that was changed by the user
        """
        try:
            if self.controller is None:
                return
            
            # Handle IQ settings changes
            if param.parent().name() == 'iq_settings':
                if param.name() == 'frequency':
                    self.controller.frequency = param.value()
                    logger.debug(f"IQ frequency changed: {param.value()} Hz")
                    
                elif param.name() == 'bandwidth':
                    self.controller.bandwidth = param.value()
                    logger.debug(f"IQ bandwidth changed: {param.value()} Hz")
                    
                elif param.name() == 'input':
                    self.controller.input = param.value()
                    logger.debug(f"IQ input changed: {param.value()}")
                    
                elif param.name() == 'output_direct':
                    self.controller.output_direct = param.value()
                    logger.debug(f"IQ output_direct changed: {param.value()}")
                    
                elif param.name() == 'gain':
                    self.controller.gain = param.value()
                    logger.debug(f"IQ gain changed: {param.value()}")
        
        except Exception as e:
            logger.error(f"Error in commit_settings: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Settings error: {e}', 'log']))
    
    def ini_detector(self, controller=None):
        """
        Initialize the IQ demodulator detector.
        
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
                self.iq_module_name = self.settings.child('connection', 'iq_module').value()
                
                logger.info(f"Initializing IQ plugin: {self.iq_module_name} @ {self.hostname}")
                
                # Get shared PyRPL instance (creates it if needed)
                pyrpl = self.get_shared_pyrpl(
                    hostname=self.hostname,
                    config=self.config,
                    gui=False  # No GUI for PyMoDAQ integration
                )
                
                # Get the specific IQ module
                self.controller = self.get_module(self.iq_module_name)
                
                # Apply initial settings from GUI
                self.controller.frequency = self.settings.child('iq_settings', 'frequency').value()
                self.controller.bandwidth = self.settings.child('iq_settings', 'bandwidth').value()
                self.controller.input = self.settings.child('iq_settings', 'input').value()
                self.controller.output_direct = self.settings.child('iq_settings', 'output_direct').value()
                self.controller.gain = self.settings.child('iq_settings', 'gain').value()
                
                info = f"✓ Connected to {self.iq_module_name} on {self.hostname}"
                logger.info(info)
                initialized = True
                
                # Optional: Send initial data structure to PyMoDAQ
                self.dte_signal_temp.emit(DataToExport(
                    name=f'PyRPL_{self.iq_module_name}',
                    data=[DataFromPlugins(
                        name='I',
                        data=[np.array([0.0])],
                        dim='Data0D',
                        labels=['I (V)']
                    ), DataFromPlugins(
                        name='Q',
                        data=[np.array([0.0])],
                        dim='Data0D',
                        labels=['Q (V)']
                    )]
                ))
                
            else:
                # Slave mode (shared controller)
                self.controller = controller
                info = "Slave mode initialized"
                initialized = True
            
            return info, initialized
        
        except Exception as e:
            error_msg = f"Failed to initialize IQ: {e}"
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
            logger.info(f"Closing IQ plugin ({self.iq_module_name})")
            # Just log that we're closing; don't close shared PyRPL
    
    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquire IQ demodulation data.
        
        This is a SYNCHRONOUS acquisition - it reads the current I and Q values
        from the IQ demodulator and returns them as two 0D data channels.
        
        Args:
            Naverage: Number of averages (not used for IQ, always instantaneous)
            **kwargs: Additional parameters (not used)
        """
        try:
            if self.controller is None:
                raise RuntimeError("IQ module not initialized")
            
            # Read I and Q values
            # PyRPL IQ module has a complex-valued output
            iq_complex = self.controller.iq
            
            # Extract I and Q components
            i_value = float(np.real(iq_complex))
            q_value = float(np.imag(iq_complex))
            
            # Calculate amplitude and phase for display
            amplitude = np.sqrt(i_value**2 + q_value**2)
            phase_rad = np.arctan2(q_value, i_value)
            phase_deg = np.degrees(phase_rad)
            
            # Update read-only display parameters
            self.settings.child('display', 'amplitude').setValue(amplitude)
            self.settings.child('display', 'phase').setValue(phase_deg)
            
            # Create PyMoDAQ data structure
            # For 0D viewer, we return two scalar values (I and Q)
            i_data = DataFromPlugins(
                name='I',
                data=[np.array([i_value])],
                dim='Data0D',
                labels=['I (V)']
            )
            
            q_data = DataFromPlugins(
                name='Q',
                data=[np.array([q_value])],
                dim='Data0D',
                labels=['Q (V)']
            )
            
            # Emit data to PyMoDAQ
            self.dte_signal.emit(DataToExport(
                name=f'PyRPL_{self.iq_module_name}',
                data=[i_data, q_data]
            ))
            
            logger.debug(f"IQ data acquired: I={i_value:.6f}, Q={q_value:.6f}, "
                        f"Amp={amplitude:.6f}, Phase={phase_deg:.2f}°")
        
        except Exception as e:
            logger.error(f"Error in grab_data: {e}")
            self.emit_status(ThreadCommand('Update_Status', [f'Acquisition error: {e}', 'log']))
            
            # Emit zero data on error
            self.dte_signal.emit(DataToExport(
                name=f'PyRPL_IQ',
                data=[
                    DataFromPlugins(name='I', data=[np.array([0.0])], dim='Data0D', labels=['I (V)']),
                    DataFromPlugins(name='Q', data=[np.array([0.0])], dim='Data0D', labels=['Q (V)'])
                ]
            ))
    
    def stop(self):
        """
        Stop the current acquisition.
        """
        try:
            if self.controller is not None:
                logger.info("IQ acquisition stop requested")
                self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped', 'log']))
        
        except Exception as e:
            logger.error(f"Error in stop: {e}")


if __name__ == '__main__':
    main(__file__)
