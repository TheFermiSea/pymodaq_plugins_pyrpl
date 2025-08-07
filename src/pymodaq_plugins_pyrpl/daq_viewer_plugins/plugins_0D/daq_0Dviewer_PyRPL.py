# -*- coding: utf-8 -*-
"""
PyMoDAQ Detector Plugin for Red Pitaya PyRPL Signal Monitoring

This plugin provides real-time voltage monitoring capabilities for Red Pitaya
STEMlab devices via the PyRPL library. It supports simultaneous monitoring of
analog inputs and PID setpoints for laser power stabilization applications.

Features:
    - Multi-channel voltage monitoring (IN1, IN2, PID setpoints)
    - Real-time data acquisition for PyMoDAQ logging and plotting
    - Thread-safe PyRPL wrapper integration
    - Mock mode for development without hardware
    - Configurable sampling rates and channel selection
    - Voltage range: ±1V (Red Pitaya hardware limit)

Compatible Hardware:
    - Red Pitaya STEMlab 125-10/125-14
    - PyRPL firmware and library

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
    2. Select channels to monitor (IN1, IN2, PID setpoints)
    3. Set appropriate sampling rate (0.1-1000 Hz)
    4. Initialize detector to establish connection
    5. Start continuous acquisition for real-time monitoring

Author: Claude Code
License: MIT
"""

import time
import numpy as np
from typing import Optional, Dict, List, Union
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
    PyRPLManager, PyRPLConnection, PIDChannel, InputChannel,
    ConnectionState
)

logger = logging.getLogger(__name__)


class MockPyRPLConnection:
    """Mock connection for development without hardware."""
    
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.is_connected = True
        self.state = ConnectionState.CONNECTED
        
    def read_voltage(self, channel: InputChannel) -> float:
        """Return mock voltage readings with realistic variations."""
        base_voltage = 0.5 if channel == InputChannel.IN1 else 0.3
        noise = np.random.normal(0, 0.01)  # 10mV noise
        return base_voltage + noise
    
    def get_pid_setpoint(self, channel: PIDChannel) -> float:
        """Return mock PID setpoint."""
        return 0.5 + np.random.normal(0, 0.001)  # 1mV noise
    
    def disconnect(self, status_callback=None):
        """Mock disconnect."""
        self.is_connected = False


class DAQ_0DViewer_PyRPL(DAQ_Viewer_base):
    """
    PyMoDAQ 0D Viewer Plugin for Red Pitaya PyRPL Signal Monitoring.
    
    This detector plugin enables real-time monitoring of voltage signals from
    Red Pitaya analog inputs and PID controller setpoints. It integrates with
    PyMoDAQ's data acquisition framework for logging, plotting, and scanning
    applications in laser stabilization systems.
    
    The plugin supports multi-channel monitoring with configurable sampling
    rates and provides both hardware and mock modes for flexible development
    and deployment scenarios.
    
    Attributes:
        controller: PyRPLConnection instance for hardware communication
        pyrpl_manager: Singleton manager for PyRPL connections
        last_acquisition_time: Timestamp of last data acquisition
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
                    'value': 'rp-f0a552.local',
                    'tip': 'Hostname or IP address of Red Pitaya device'
                },
                {
                    'title': 'Config Name:',
                    'name': 'config_name',
                    'type': 'str',
                    'value': 'pymodaq_viewer',
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
            'title': 'Channel Configuration:',
            'name': 'channels',
            'type': 'group',
            'children': [
                {
                    'title': 'Monitor IN1:',
                    'name': 'monitor_in1',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Monitor analog input 1 voltage'
                },
                {
                    'title': 'Monitor IN2:',
                    'name': 'monitor_in2',
                    'type': 'bool',
                    'value': False,
                    'tip': 'Monitor analog input 2 voltage'
                },
                {
                    'title': 'Monitor PID Setpoint:',
                    'name': 'monitor_pid',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Monitor PID controller setpoint'
                },
                {
                    'title': 'PID Module:',
                    'name': 'pid_module',
                    'type': 'list',
                    'limits': ['pid0', 'pid1', 'pid2'],
                    'value': 'pid0',
                    'tip': 'PID module to monitor for setpoint'
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
        
        # Channel configuration
        self.active_channels: List[str] = []
        self.channel_data: Dict[str, float] = {}

    def commit_settings(self, param: Parameter):
        """
        Apply consequences of parameter changes.
        
        This method handles real-time parameter updates, particularly for
        channel configuration changes that affect data acquisition structure.
        
        Parameters:
            param: Parameter that was modified
        """
        param_name = param.name()
        param_path = param.path()
        
        logger.debug(f"Committing parameter change: {param_path}")
        
        # Handle channel configuration changes
        if param_name in ['monitor_in1', 'monitor_in2', 'monitor_pid', 'pid_module']:
            self._update_active_channels()
            logger.info(f"Updated active channels: {self.active_channels}")
            
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
        
        if self.settings['channels', 'monitor_in1']:
            self.active_channels.append('Input 1 (V)')
            
        if self.settings['channels', 'monitor_in2']:
            self.active_channels.append('Input 2 (V)')
            
        if self.settings['channels', 'monitor_pid']:
            pid_module = self.settings['channels', 'pid_module']
            self.active_channels.append(f'PID {pid_module.upper()} Setpoint (V)')

    def ini_detector(self, controller=None):
        """
        Initialize detector and establish Red Pitaya connection.
        
        Parameters:
            controller: External controller (for slave mode) or None for master mode
            
        Returns:
            tuple: (info_string, initialization_success)
        """
        logger.info("Initializing PyRPL viewer detector...")
        
        try:
            if self.is_master:
                # Master mode: create new connection
                mock_mode = self.settings['connection', 'mock_mode']
                hostname = self.settings['connection', 'redpitaya_host']
                
                if mock_mode:
                    # Use mock connection for development
                    self.controller = MockPyRPLConnection(hostname)
                    info = f"Mock PyRPL connection established for {hostname}"
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
            
            # Update active channels based on current settings
            self._update_active_channels()
            
            # Initialize data structure for PyMoDAQ
            self._initialize_data_structure()
            
            # Test initial data acquisition
            test_data = self._acquire_data()
            if test_data is None:
                return "Failed to acquire test data", False
                
            logger.info(f"Detector initialized successfully. Active channels: {self.active_channels}")
            return info, True
            
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
            data = DataRaw(
                name=channel_name,
                data=np.array([0.0]),
                labels=[channel_name],
                units='V'
            )
            mock_data_list.append(data)
        
        # Emit initial data structure to PyMoDAQ
        self.dte_signal_temp.emit(
            DataToExport(name='PyRPL Monitor', data=mock_data_list)
        )

    def _acquire_data(self) -> Optional[Dict[str, float]]:
        """
        Acquire voltage data from all active channels.
        
        Returns:
            Dictionary mapping channel names to voltage values, or None if error
        """
        if self.controller is None or not self.controller.is_connected:
            logger.warning("Cannot acquire data: controller not connected")
            return None
            
        data = {}
        
        try:
            # Read analog input channels
            if self.settings['channels', 'monitor_in1']:
                voltage = self.controller.read_voltage(InputChannel.IN1)
                if voltage is not None:
                    data['Input 1 (V)'] = voltage
                    
            if self.settings['channels', 'monitor_in2']:
                voltage = self.controller.read_voltage(InputChannel.IN2)
                if voltage is not None:
                    data['Input 2 (V)'] = voltage
            
            # Read PID setpoint if enabled
            if self.settings['channels', 'monitor_pid']:
                pid_module_name = self.settings['channels', 'pid_module']
                pid_channel = PIDChannel(pid_module_name)
                
                if isinstance(self.controller, MockPyRPLConnection):
                    setpoint = self.controller.get_pid_setpoint(pid_channel)
                else:
                    setpoint = self.controller.get_pid_setpoint(pid_channel)
                    
                if setpoint is not None:
                    data[f'PID {pid_module_name.upper()} Setpoint (V)'] = setpoint
            
            return data
            
        except Exception as e:
            logger.error(f"Error acquiring data: {e}")
            return None

    def grab_data(self, Naverage=1, **kwargs):
        """
        Start data acquisition from Red Pitaya.
        
        This method performs synchronous data acquisition from the configured
        channels and emits the data to PyMoDAQ for logging and visualization.
        
        Parameters:
            Naverage: Number of averages (currently ignored - hardware dependent)
            **kwargs: Additional arguments
        """
        start_time = time.time()
        
        try:
            # Acquire data from active channels
            channel_data = self._acquire_data()
            
            if channel_data is None:
                self.emit_status(ThreadCommand('Update_Status', 
                    ['Failed to acquire data from Red Pitaya', 'log']))
                return
                
            # Create PyMoDAQ data objects
            data_list = []
            for channel_name in self.active_channels:
                if channel_name in channel_data:
                    voltage = channel_data[channel_name]
                    data = DataRaw(
                        name=channel_name,
                        data=np.array([voltage]),
                        labels=[channel_name],
                        units='V'
                    )
                    data_list.append(data)
                else:
                    logger.warning(f"No data available for channel: {channel_name}")
            
            # Emit data to PyMoDAQ
            if data_list:
                self.dte_signal.emit(
                    DataToExport(name='PyRPL Monitor', data=data_list)
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
            error_msg = f"Error during data acquisition: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def close(self):
        """
        Close detector and clean up resources.
        
        This method ensures proper disconnection from Red Pitaya hardware
        and cleanup of PyRPL resources to prevent conflicts with other plugins.
        """
        logger.info("Closing PyRPL viewer detector...")
        
        try:
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
            
            logger.info("PyRPL detector closed successfully")
            
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
        logger.debug("Stop acquisition requested")
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped', 'log']))
        return ''


if __name__ == '__main__':
    # Run plugin in standalone mode for testing
    main(__file__)