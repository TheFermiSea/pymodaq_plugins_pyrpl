# -*- coding: utf-8 -*-
"""
PyMoDAQ 1D Viewer Plugin for Red Pitaya PyRPL Oscilloscope

This plugin provides real-time oscilloscope functionality for Red Pitaya
STEMlab devices via the PyRPL library. It supports time-series data acquisition
with configurable triggering, decimation rates, and averaging for high-quality
signal analysis and monitoring applications.

Features:
    - Real-time oscilloscope functionality with 16384 samples (2^14)
    - Configurable decimation rates (1x to 65536x)
    - Multiple trigger sources and modes
    - Averaging support (1 to 1000 averages)
    - Rolling mode for continuous acquisition
    - Time axis generation with proper units
    - Thread-safe PyRPL wrapper integration
    - Mock mode for development without hardware
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
    2. Select input channel (IN1 or IN2)
    3. Set decimation rate for desired time resolution
    4. Configure trigger settings (source, level, delay)
    5. Initialize detector to establish connection
    6. Start acquisition for time-series data capture

Use Cases:
    - Transient signal capture and analysis
    - Real-time waveform monitoring  
    - Trigger-synchronized measurements
    - Time-domain characterization
    - Signal integrity analysis
    - Integration with PyMoDAQ scanning (scope traces as function of scan parameter)

Author: Claude Code
License: MIT
"""

import time
import numpy as np
from typing import Optional, Tuple, Union
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
    PyRPLManager, PyRPLConnection, InputChannel, ScopeConfiguration,
    ScopeTriggerSource, ScopeDecimation, ConnectionState
)

logger = logging.getLogger(__name__)


class MockScopeConnection:
    """Mock connection for development without hardware."""
    
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.is_connected = True
        self.state = ConnectionState.CONNECTED
        self._scope_config: Optional[ScopeConfiguration] = None
        
    def configure_scope(self, config: ScopeConfiguration) -> bool:
        """Mock scope configuration."""
        self._scope_config = config
        return True
    
    def acquire_scope_data(self, timeout: Optional[float] = None) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return mock scope data with realistic waveform."""
        if self._scope_config is None:
            return None
            
        # Generate mock time-series data
        data_length = self._scope_config.data_length
        
        # Calculate mock timing parameters
        decimation = self._scope_config.decimation.value
        base_sampling_rate = 125e6  # 125 MHz base rate for Red Pitaya
        sampling_rate = base_sampling_rate / decimation
        duration = data_length / sampling_rate
        
        # Generate time axis
        time_axis = np.linspace(0, duration, data_length)
        
        # Generate mock signal: damped sine wave with noise
        frequency = 1e3  # 1 kHz signal
        amplitude = 0.5
        decay_time = duration / 3
        noise_level = 0.02
        
        signal = amplitude * np.sin(2 * np.pi * frequency * time_axis) * np.exp(-time_axis / decay_time)
        noise = np.random.normal(0, noise_level, data_length)
        voltage_data = signal + noise
        
        # Simulate acquisition delay
        time.sleep(0.01)
        
        return time_axis, voltage_data
    
    def get_scope_sampling_time(self) -> Optional[float]:
        """Return mock sampling time."""
        if self._scope_config is None:
            return None
        decimation = self._scope_config.decimation.value
        return decimation / 125e6  # Base rate 125 MHz
    
    def get_scope_duration(self) -> Optional[float]:
        """Return mock duration."""
        if self._scope_config is None:
            return None
        sampling_time = self.get_scope_sampling_time()
        return sampling_time * self._scope_config.data_length
    
    def disconnect(self, status_callback=None):
        """Mock disconnect."""
        self.is_connected = False


class DAQ_1DViewer_PyRPL_Scope(DAQ_Viewer_base):
    """
    PyMoDAQ 1D Viewer Plugin for Red Pitaya PyRPL Oscilloscope.
    
    This detector plugin enables real-time oscilloscope functionality with
    configurable triggering, decimation, and averaging. It integrates with
    PyMoDAQ's data acquisition framework for time-series signal analysis
    in laser stabilization and general measurement applications.
    
    The plugin provides 16384 samples (2^14) per acquisition with configurable
    time resolution via decimation settings, supporting everything from
    high-speed transient capture to long-duration monitoring.
    
    Attributes:
        controller: PyRPLConnection instance for hardware communication
        pyrpl_manager: Singleton manager for PyRPL connections
        scope_config: Current scope configuration parameters
    """
    
    _controller_units = 'V'  # Required for PyMoDAQ 5.x compatibility
    
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
                    'value': 'pymodaq_scope',
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
            'title': 'Input Channel:',
            'name': 'input_channel',
            'type': 'list',
            'limits': ['in1', 'in2'],
            'value': 'in1',
            'tip': 'Red Pitaya analog input channel'
        },
        {
            'title': 'Timing Settings:',
            'name': 'timing',
            'type': 'group',
            'children': [
                {
                    'title': 'Decimation:',
                    'name': 'decimation',
                    'type': 'list',
                    'limits': ['1', '8', '64', '1024', '8192', '65536'],
                    'value': '64',
                    'tip': 'Decimation factor (higher = longer time spans, lower resolution)'
                },
                {
                    'title': 'Sampling Rate (Hz):',
                    'name': 'sampling_rate',
                    'type': 'float',
                    'value': 1953125.0,
                    'readonly': True,
                    'tip': 'Effective sampling rate (calculated from decimation)'
                },
                {
                    'title': 'Duration (s):',
                    'name': 'duration',
                    'type': 'float',
                    'value': 0.008389,
                    'readonly': True,
                    'tip': 'Total acquisition duration (calculated)'
                }
            ]
        },
        {
            'title': 'Trigger Settings:',
            'name': 'trigger',
            'type': 'group',
            'children': [
                {
                    'title': 'Trigger Source:',
                    'name': 'trigger_source',
                    'type': 'list',
                    'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge', 
                              'ch2_positive_edge', 'ch2_negative_edge', 
                              'ext_positive_edge', 'ext_negative_edge'],
                    'value': 'immediately',
                    'tip': 'Trigger source for scope acquisition'
                },
                {
                    'title': 'Trigger Delay:',
                    'name': 'trigger_delay',
                    'type': 'int',
                    'value': 0,
                    'min': 0,
                    'max': 16383,
                    'tip': 'Trigger delay in samples (0 = center trigger)'
                },
                {
                    'title': 'Trigger Level (V):',
                    'name': 'trigger_level',
                    'type': 'float',
                    'value': 0.0,
                    'min': -1.0,
                    'max': 1.0,
                    'tip': 'Trigger voltage level for edge triggers'
                }
            ]
        },
        {
            'title': 'Acquisition Settings:',
            'name': 'acquisition',
            'type': 'group',
            'children': [
                {
                    'title': 'Average:',
                    'name': 'average',
                    'type': 'int',
                    'value': 1,
                    'min': 1,
                    'max': 1000,
                    'tip': 'Number of acquisitions to average'
                },
                {
                    'title': 'Rolling Mode:',
                    'name': 'rolling_mode',
                    'type': 'bool',
                    'value': False,
                    'tip': 'Enable rolling mode for continuous acquisition'
                },
                {
                    'title': 'Timeout (s):',
                    'name': 'timeout',
                    'type': 'float',
                    'value': 5.0,
                    'min': 0.1,
                    'max': 60.0,
                    'tip': 'Maximum time to wait for triggered acquisition'
                }
            ]
        }
    ]

    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.controller: Optional[Union[PyRPLConnection, MockScopeConnection]] = None
        self.pyrpl_manager: Optional[PyRPLManager] = None
        self.scope_config: Optional[ScopeConfiguration] = None
        
        # Data structure
        self.x_axis: Optional[Axis] = None

    def _update_timing_parameters(self):
        """Update calculated timing parameters based on decimation."""
        try:
            decimation_value = int(self.settings['timing', 'decimation'])
            base_rate = 125e6  # 125 MHz base sampling rate for Red Pitaya
            data_length = 16384  # 2^14 samples fixed for Red Pitaya
            
            # Calculate effective parameters
            sampling_rate = base_rate / decimation_value
            duration = data_length / sampling_rate
            
            # Update readonly parameters
            self.settings.child('timing', 'sampling_rate').setValue(sampling_rate)
            self.settings.child('timing', 'duration').setValue(duration)
            
            logger.debug(f"Updated timing: decimation={decimation_value}, "
                        f"rate={sampling_rate:.0f} Hz, duration={duration:.6f} s")
                        
        except Exception as e:
            logger.error(f"Failed to update timing parameters: {e}")

    def commit_settings(self, param: Parameter):
        """
        Apply consequences of parameter changes.
        
        This method handles real-time parameter updates, particularly for
        timing calculations and scope reconfiguration.
        
        Parameters:
            param: Parameter that was modified
        """
        param_name = param.name()
        param_path = param.path()
        
        logger.debug(f"Committing parameter change: {param_path}")
        
        # Handle decimation changes - update calculated timing parameters
        if param_name == 'decimation':
            self._update_timing_parameters()
            
            # Reconfigure scope if connected
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected and self.scope_config is not None:
                    self._update_scope_configuration()
                    
        # Handle trigger parameter changes
        elif param_name in ['trigger_source', 'trigger_delay', 'trigger_level', 
                           'average', 'rolling_mode', 'timeout']:
            # Reconfigure scope if connected
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected and self.scope_config is not None:
                    self._update_scope_configuration()
                    
        # Handle connection parameter changes
        elif param_name in ['redpitaya_host', 'config_name', 'mock_mode']:
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected:
                    self.emit_status(ThreadCommand('Update_Status', 
                        ['Connection parameters changed. Please reinitialize detector.', 'log']))
                        
        # Handle input channel change
        elif param_name == 'input_channel':
            # Reconfigure scope if connected
            if self.controller is not None and hasattr(self.controller, 'is_connected'):
                if self.controller.is_connected and self.scope_config is not None:
                    self._update_scope_configuration()

    def _create_scope_configuration(self) -> ScopeConfiguration:
        """Create scope configuration from current parameters."""
        return ScopeConfiguration(
            input_channel=InputChannel(self.settings['input_channel']),
            decimation=ScopeDecimation(int(self.settings['timing', 'decimation'])),
            trigger_source=ScopeTriggerSource(self.settings['trigger', 'trigger_source']),
            trigger_delay=self.settings['trigger', 'trigger_delay'],
            trigger_level=self.settings['trigger', 'trigger_level'],
            average=self.settings['acquisition', 'average'],
            rolling_mode=self.settings['acquisition', 'rolling_mode'],
            timeout=self.settings['acquisition', 'timeout']
        )

    def _update_scope_configuration(self) -> bool:
        """Update scope configuration with current parameters."""
        try:
            self.scope_config = self._create_scope_configuration()
            
            if isinstance(self.controller, MockScopeConnection):
                success = self.controller.configure_scope(self.scope_config)
            else:
                success = self.controller.configure_scope(self.scope_config)
            
            if success:
                logger.debug("Scope configuration updated successfully")
            else:
                logger.error("Failed to update scope configuration")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating scope configuration: {e}")
            return False

    def ini_detector(self, controller=None):
        """
        Initialize detector and establish Red Pitaya connection.
        
        Parameters:
            controller: External controller (for slave mode) or None for master mode
            
        Returns:
            tuple: (info_string, initialization_success)
        """
        logger.info("Initializing PyRPL scope detector...")
        
        try:
            if self.is_master:
                # Master mode: create new connection
                mock_mode = self.settings['connection', 'mock_mode']
                hostname = self.settings['connection', 'redpitaya_host']
                
                if mock_mode:
                    # Use mock connection for development
                    self.controller = MockScopeConnection(hostname)
                    info = f"Mock PyRPL Scope connection established for {hostname}"
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
                        if self.controller and hasattr(self.controller, 'last_error'):
                            if self.controller.last_error:
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
            
            # Initialize timing parameters
            self._update_timing_parameters()
            
            # Create and configure scope
            self.scope_config = self._create_scope_configuration()
            
            # Configure scope on hardware
            if not self._update_scope_configuration():
                return "Failed to configure scope", False
                
            # Initialize data structure for PyMoDAQ
            self._initialize_data_structure()
            
            # Test initial data acquisition
            test_data = self._acquire_scope_data()
            if test_data is None:
                return "Failed to acquire test scope data", False
                
            logger.info(f"Scope detector initialized successfully. "
                       f"Channel: {self.settings['input_channel']}, "
                       f"Decimation: {self.settings['timing', 'decimation']}")
            return info, True
            
        except Exception as e:
            error_msg = f"Scope detector initialization failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg, False

    def _initialize_data_structure(self):
        """Initialize PyMoDAQ data structure with current scope configuration."""
        try:
            # Create mock time axis for initialization
            data_length = 16384
            duration = self.settings['timing', 'duration']
            time_axis = np.linspace(0, duration, data_length)
            
            self.x_axis = Axis(
                data=time_axis,
                label='Time', 
                units='s',
                index=0
            )
            
            # Create mock data for initialization
            mock_voltage_data = np.zeros(data_length)
            channel_name = f"Scope {self.settings['input_channel'].upper()}"
            
            data = DataRaw(
                name=channel_name,
                data=mock_voltage_data,
                axes=[self.x_axis],
                nav_axes=[],
                units='V'
            )
            
            # Emit initial data structure to PyMoDAQ
            self.dte_signal_temp.emit(
                DataToExport(name='PyRPL Scope', data=[data])
            )
            
            logger.debug("Initialized scope data structure")
            
        except Exception as e:
            logger.error(f"Failed to initialize data structure: {e}")

    def _acquire_scope_data(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Acquire time-series data from the scope.
        
        Returns:
            Tuple of (time_axis, voltage_data) or None if error
        """
        if self.controller is None or not self.controller.is_connected:
            logger.warning("Cannot acquire scope data: controller not connected")
            return None
            
        try:
            # Acquire data using the configured timeout
            timeout = self.settings['acquisition', 'timeout']
            
            if isinstance(self.controller, MockScopeConnection):
                result = self.controller.acquire_scope_data(timeout)
            else:
                result = self.controller.acquire_scope_data(timeout)
                
            if result is None:
                logger.error("Scope data acquisition returned None")
                return None
                
            time_axis, voltage_data = result
            
            # Validate data
            if len(time_axis) != len(voltage_data):
                logger.error(f"Time axis length ({len(time_axis)}) != "
                           f"voltage data length ({len(voltage_data)})")
                return None
                
            logger.debug(f"Acquired {len(voltage_data)} scope samples, "
                        f"duration: {time_axis[-1]:.6f} s")
            
            return time_axis, voltage_data
            
        except Exception as e:
            logger.error(f"Error acquiring scope data: {e}")
            return None

    def grab_data(self, Naverage=1, **kwargs):
        """
        Start data acquisition from Red Pitaya scope.
        
        This method performs synchronous data acquisition from the configured
        scope and emits the time-series data to PyMoDAQ for logging and visualization.
        
        Parameters:
            Naverage: Number of averages (handled by scope configuration)
            **kwargs: Additional arguments
        """
        start_time = time.time()
        
        try:
            # Acquire scope data
            scope_result = self._acquire_scope_data()
            
            if scope_result is None:
                self.emit_status(ThreadCommand('Update_Status', 
                    ['Failed to acquire scope data from Red Pitaya', 'log']))
                return
                
            time_axis, voltage_data = scope_result
            
            # Update x-axis with actual acquired time data
            self.x_axis = Axis(
                data=time_axis,
                label='Time',
                units='s',
                index=0
            )
            
            # Create PyMoDAQ data object
            channel_name = f"Scope {self.settings['input_channel'].upper()}"
            
            data = DataRaw(
                name=channel_name,
                data=voltage_data,
                axes=[self.x_axis],
                nav_axes=[],
                units='V'
            )
            
            # Emit data to PyMoDAQ
            self.dte_signal.emit(
                DataToExport(name='PyRPL Scope', data=[data])
            )
            
            # Update acquisition timing
            acquisition_time = time.time() - start_time
            logger.debug(f"Scope acquisition completed in {acquisition_time:.3f}s, "
                        f"{len(voltage_data)} samples")
                        
        except Exception as e:
            error_msg = f"Error during scope data acquisition: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def close(self):
        """
        Close detector and clean up resources.
        
        This method ensures proper disconnection from Red Pitaya hardware
        and cleanup of PyRPL resources to prevent conflicts with other plugins.
        """
        logger.info("Closing PyRPL scope detector...")
        
        try:
            if self.controller is not None:
                if hasattr(self.controller, 'disconnect'):
                    self.controller.disconnect(status_callback=self.emit_status)
                    
                self.controller = None
                
            if self.pyrpl_manager is not None:
                # Note: Don't cleanup the entire manager as it may be shared
                # Individual connections are cleaned up by the disconnect call above
                self.pyrpl_manager = None
                
            self.scope_config = None
            self.x_axis = None
            
            logger.info("PyRPL scope detector closed successfully")
            
        except Exception as e:
            error_msg = f"Error during scope detector close: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))

    def stop(self):
        """
        Stop current data acquisition.
        
        Attempts to stop ongoing scope acquisition if supported by hardware.
        
        Returns:
            Empty string (required by PyMoDAQ interface)
        """
        logger.debug("Stop scope acquisition requested")
        
        try:
            if (self.controller is not None and 
                hasattr(self.controller, 'stop_scope_acquisition') and
                self.controller.is_connected):
                
                success = self.controller.stop_scope_acquisition()
                if success:
                    self.emit_status(ThreadCommand('Update_Status', 
                        ['Scope acquisition stopped', 'log']))
                else:
                    self.emit_status(ThreadCommand('Update_Status', 
                        ['Failed to stop scope acquisition', 'log']))
            else:
                self.emit_status(ThreadCommand('Update_Status', 
                    ['Scope acquisition stop requested', 'log']))
                    
        except Exception as e:
            logger.error(f"Error stopping scope acquisition: {e}")
            self.emit_status(ThreadCommand('Update_Status', 
                [f'Error stopping acquisition: {str(e)}', 'log']))
        
        return ''


if __name__ == '__main__':
    # Run plugin in standalone mode for testing
    main(__file__)