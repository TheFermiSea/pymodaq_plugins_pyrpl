# -*- coding: utf-8 -*-
"""
PyMoDAQ Extension for PyRPL PID Controller

This extension provides a comprehensive interface for controlling Red Pitaya's
hardware PID controllers via PyRPL. It offers real-time monitoring, parameter
adjustment, and feedback display within PyMoDAQ's framework.

Features:
    - Real-time PID parameter adjustment (P, I, D gains)
    - Input/output channel configuration
    - Setpoint control and monitoring
    - Live feedback display with plotting
    - Error signal visualization
    - PID enable/disable control
    - Mock mode for development

Compatible Hardware:
    - Red Pitaya STEMlab 125-10/125-14
    - PyRPL firmware and library

Author: Generated for PyMoDAQ Integration
License: MIT
"""

import time
import numpy as np
from typing import Optional, Dict, Union
from functools import partial

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import QObject, Signal, QTimer, Slot

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.utils.widgets import QLED, LabelWithFont
from pymodaq_gui.utils.dock import Dock
from pymodaq_data.data import DataToExport, DataRaw, Axis

from pymodaq.extensions.utils import CustomExt

# Import PyRPL wrapper utilities
from ..utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, PIDChannel, InputChannel, 
    OutputChannel, PIDConfiguration, ConnectionState
)
# Configuration handled locally in extension

logger = set_logger(get_module_name(__file__))

# Extension metadata for PyMoDAQ discovery
EXTENSION_NAME = "PyRPL PID Controller"
CLASS_NAME = "DAQ_PyRPL_PID_Extension"


class PIDMonitorThread(QObject):
    """Background thread for monitoring PID values in real-time."""
    
    data_ready = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, controller: Optional[PyRPLConnection], pid_config: PIDConfiguration):
        super().__init__()
        self.controller = controller
        self.pid_config = pid_config
        self.monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.acquire_data)
        
    def start_monitoring(self, interval_ms: int = 100):
        """Start monitoring PID values."""
        if self.controller and self.controller.is_connected:
            self.monitoring = True
            self.timer.start(interval_ms)
            logger.debug(f"Started PID monitoring with {interval_ms}ms interval")
        else:
            self.error_occurred.emit("Cannot start monitoring: PyRPL not connected")
    
    def stop_monitoring(self):
        """Stop monitoring PID values."""
        self.monitoring = False
        self.timer.stop()
        logger.debug("Stopped PID monitoring")
    
    @Slot()
    def acquire_data(self):
        """Acquire PID data from hardware."""
        if not self.monitoring or not self.controller or not self.controller.is_connected:
            return
            
        try:
            # Read PID values
            pid_data = self.controller.get_pid_status(self.pid_config.channel)
            if pid_data:
                # Add timestamp
                pid_data['timestamp'] = time.time()
                self.data_ready.emit(pid_data)
        except Exception as e:
            logger.error(f"Error acquiring PID data: {e}")
            self.error_occurred.emit(f"PID monitoring error: {str(e)}")


class DAQ_PyRPL_PID_Extension(CustomExt):
    """
    PyMoDAQ Extension for PyRPL Hardware PID Controller.
    
    This extension provides a comprehensive interface for controlling Red Pitaya's
    hardware PID controllers through PyRPL. It includes real-time monitoring,
    parameter adjustment, and feedback visualization.
    
    The extension creates multiple docks:
    - Connection Control: PyRPL connection management
    - PID Configuration: Channel setup and parameter control
    - Real-time Display: Live PID monitoring and feedback
    - Error Analysis: PID performance visualization
    """
    
    # Signals for internal communication
    pid_data_signal = Signal(dict)
    connection_changed = Signal(bool)
    parameter_changed = Signal(str, object)
    
    params = [
        {
            'title': 'Connection Settings',
            'name': 'connection',
            'type': 'group',
            'expanded': True,
            'children': [
                {
                    'title': 'Red Pitaya Host:',
                    'name': 'hostname',
                    'type': 'str',
                    'value': 'rp-f08d6c.local',
                    'tip': 'Red Pitaya hostname or IP address'
                },
                {
                    'title': 'Config Name:',
                    'name': 'config_name',
                    'type': 'str',
                    'value': 'pymodaq_pid_extension',
                    'tip': 'PyRPL configuration name'
                },
                {
                    'title': 'Connection Timeout (s):',
                    'name': 'timeout',
                    'type': 'float',
                    'value': 10.0,
                    'min': 1.0,
                    'max': 60.0,
                    'tip': 'Connection timeout in seconds'
                },
                {
                    'title': 'Mock Mode:',
                    'name': 'mock_mode',
                    'type': 'bool',
                    'value': False,
                    'tip': 'Enable mock mode for development'
                }
            ]
        },
        {
            'title': 'PID Configuration',
            'name': 'pid_config',
            'type': 'group',
            'expanded': True,
            'children': [
                {
                    'title': 'PID Module:',
                    'name': 'pid_module',
                    'type': 'list',
                    'limits': ['pid0', 'pid1', 'pid2'],
                    'value': 'pid0',
                    'tip': 'Select PID controller module'
                },
                {
                    'title': 'Input Channel:',
                    'name': 'input_channel',
                    'type': 'list',
                    'limits': ['in1', 'in2'],
                    'value': 'in1',
                    'tip': 'PID input channel'
                },
                {
                    'title': 'Output Channel:',
                    'name': 'output_channel',
                    'type': 'list',
                    'limits': ['out1', 'out2'],
                    'value': 'out1',
                    'tip': 'PID output channel'
                }
            ]
        },
        {
            'title': 'PID Parameters',
            'name': 'pid_params',
            'type': 'group',
            'expanded': True,
            'children': [
                {
                    'title': 'Proportional Gain (P):',
                    'name': 'p_gain',
                    'type': 'float',
                    'value': 0.1,
                    'min': 0.0,
                    'max': 10.0,
                    'step': 0.01,
                    'tip': 'Proportional gain coefficient'
                },
                {
                    'title': 'Integral Gain (I):',
                    'name': 'i_gain',
                    'type': 'float',
                    'value': 0.01,
                    'min': 0.0,
                    'max': 1.0,
                    'step': 0.001,
                    'tip': 'Integral gain coefficient'
                },
                {
                    'title': 'Derivative Gain (D):',
                    'name': 'd_gain',
                    'type': 'float',
                    'value': 0.0,
                    'min': 0.0,
                    'max': 1.0,
                    'step': 0.001,
                    'tip': 'Derivative gain coefficient (usually 0 for stability)'
                },
                {
                    'title': 'Setpoint (V):',
                    'name': 'setpoint',
                    'type': 'float',
                    'value': 0.0,
                    'min': -1.0,
                    'max': 1.0,
                    'step': 0.001,
                    'tip': 'PID setpoint voltage'
                }
            ]
        },
        {
            'title': 'Monitoring Settings',
            'name': 'monitoring',
            'type': 'group',
            'expanded': False,
            'children': [
                {
                    'title': 'Update Rate (ms):',
                    'name': 'update_rate',
                    'type': 'int',
                    'value': 100,
                    'min': 50,
                    'max': 1000,
                    'step': 10,
                    'tip': 'PID monitoring update rate'
                },
                {
                    'title': 'Plot History (s):',
                    'name': 'plot_history',
                    'type': 'int',
                    'value': 30,
                    'min': 10,
                    'max': 300,
                    'step': 10,
                    'tip': 'Time history to display in plots'
                },
                {
                    'title': 'Auto-scale Plots:',
                    'name': 'autoscale',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Auto-scale plot axes'
                }
            ]
        }
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        
        # Initialize attributes
        self.controller: Optional[PyRPLConnection] = None
        self.pyrpl_manager: Optional[PyRPLManager] = None
        self.pid_config: Optional[PIDConfiguration] = None
        self.monitor_thread: Optional[PIDMonitorThread] = None
        
        # Data storage for plotting
        self.time_data = np.array([])
        self.input_data = np.array([])
        self.setpoint_data = np.array([])
        self.output_data = np.array([])
        self.error_data = np.array([])
        
        # Status tracking
        self.is_connected = False
        self.is_monitoring = False
        self.pid_enabled = False
        
        # Load configuration
        try:
            self.config = get_pyrpl_config()
        except Exception:
            self.config = None
        
        # Setup the extension
        self.setup_ui()
        self.setup_signals()
        
        logger.info("PyRPL PID Extension initialized")

    def setup_actions(self):
        """Setup toolbar actions."""
        self.add_action('connect', 'Connect to PyRPL', 'network', checkable=True)
        self.add_action('enable_pid', 'Enable PID', 'play', checkable=True, enabled=False)
        self.add_action('monitor', 'Start Monitoring', 'timer', checkable=True, enabled=False)
        self.add_action('reset_plots', 'Reset Plot Data', 'clear')
        self.add_action('quit', 'Quit Extension', 'close2')

    def setup_docks(self):
        """Setup docking interface."""
        # Main control dock
        self.control_dock = Dock("PyRPL PID Control", self.dockarea)
        self.dockarea.addDock(self.control_dock)
        
        # Parameter tree widget  
        self.param_tree = ParameterTree()
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.param_tree.setParameters(self.settings, showTop=False)
        
        # Create control panel
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout()
        
        # Status indicators
        status_frame = QtWidgets.QFrame()
        status_layout = QtWidgets.QGridLayout()
        
        # Connection status
        self.connection_led = QLED()
        self.connection_label = LabelWithFont('Disconnected', font_size=10)
        status_layout.addWidget(QtWidgets.QLabel('Connection:'), 0, 0)
        status_layout.addWidget(self.connection_led, 0, 1)
        status_layout.addWidget(self.connection_label, 0, 2)
        
        # PID status
        self.pid_led = QLED()
        self.pid_label = LabelWithFont('Disabled', font_size=10)
        status_layout.addWidget(QtWidgets.QLabel('PID State:'), 1, 0)
        status_layout.addWidget(self.pid_led, 1, 1)
        status_layout.addWidget(self.pid_label, 1, 2)
        
        # Monitoring status
        self.monitor_led = QLED()
        self.monitor_label = LabelWithFont('Stopped', font_size=10)
        status_layout.addWidget(QtWidgets.QLabel('Monitoring:'), 2, 0)
        status_layout.addWidget(self.monitor_led, 2, 1)
        status_layout.addWidget(self.monitor_label, 2, 2)
        
        status_frame.setLayout(status_layout)
        status_frame.setFrameStyle(QtWidgets.QFrame.Box)
        
        # Add widgets to control layout
        control_layout.addWidget(QtWidgets.QLabel('<b>Status</b>'))
        control_layout.addWidget(status_frame)
        control_layout.addWidget(QtWidgets.QLabel('<b>Parameters</b>'))
        control_layout.addWidget(self.param_tree)
        
        control_widget.setLayout(control_layout)
        self.control_dock.addWidget(control_widget)
        
        # Real-time monitoring dock
        self.monitor_dock = Dock("Real-time PID Monitor", self.dockarea)
        self.dockarea.addDock(self.monitor_dock, 'right', self.control_dock)
        
        # Create monitoring widget
        monitor_widget = QtWidgets.QWidget()
        monitor_layout = QtWidgets.QVBoxLayout()
        
        # Current values display
        values_frame = QtWidgets.QFrame()
        values_layout = QtWidgets.QGridLayout()
        
        # Value displays
        self.input_value_label = LabelWithFont('0.000 V', font_size=12)
        self.setpoint_value_label = LabelWithFont('0.000 V', font_size=12)
        self.output_value_label = LabelWithFont('0.000 V', font_size=12)
        self.error_value_label = LabelWithFont('0.000 V', font_size=12)
        
        values_layout.addWidget(QtWidgets.QLabel('Input:'), 0, 0)
        values_layout.addWidget(self.input_value_label, 0, 1)
        values_layout.addWidget(QtWidgets.QLabel('Setpoint:'), 1, 0)
        values_layout.addWidget(self.setpoint_value_label, 1, 1)
        values_layout.addWidget(QtWidgets.QLabel('Output:'), 0, 2)
        values_layout.addWidget(self.output_value_label, 0, 3)
        values_layout.addWidget(QtWidgets.QLabel('Error:'), 1, 2)
        values_layout.addWidget(self.error_value_label, 1, 3)
        
        values_frame.setLayout(values_layout)
        values_frame.setFrameStyle(QtWidgets.QFrame.Box)
        
        # 0D viewer for current values
        self.current_viewer = Viewer0D()
        
        monitor_layout.addWidget(QtWidgets.QLabel('<b>Current Values</b>'))
        monitor_layout.addWidget(values_frame)
        monitor_layout.addWidget(QtWidgets.QLabel('<b>Real-time Display</b>'))
        # TODO: Add viewers when PyQtGraph compatibility is resolved
        
        monitor_widget.setLayout(monitor_layout)
        self.monitor_dock.addWidget(monitor_widget)
        
        # Time series plot dock
        self.plot_dock = Dock("PID Time Series", self.dockarea)
        self.dockarea.addDock(self.plot_dock, 'bottom', self.monitor_dock)
        
        # 1D viewer for time series
        self.timeseries_viewer = Viewer1D()
        # TODO: Add viewer to dock when PyQtGraph compatibility is resolved

    def connect_things(self):
        """Connect signals and slots."""
        # Toolbar actions
        self.connect_action('connect', self.toggle_connection)
        self.connect_action('enable_pid', self.toggle_pid)
        self.connect_action('monitor', self.toggle_monitoring)
        self.connect_action('reset_plots', self.reset_plot_data)
        self.connect_action('quit', self.quit_extension)
        
        # Parameter changes
        self.settings.sigTreeStateChanged.connect(self.parameter_changed_slot)
        
        # Internal signals
        self.connection_changed.connect(self.update_connection_status)
        self.pid_data_signal.connect(self.update_displays)

    def setup_signals(self):
        """Setup internal signal connections."""
        pass  # Additional signal setup if needed

    @Slot(bool)
    def update_connection_status(self, connected: bool):
        """Update UI based on connection status."""
        self.is_connected = connected
        
        if connected:
            self.connection_led.set_as_true()
            self.connection_label.setText('Connected')
            self.get_action('enable_pid').setEnabled(True)
            self.get_action('monitor').setEnabled(True)
        else:
            self.connection_led.set_as_false()
            self.connection_label.setText('Disconnected')
            self.get_action('enable_pid').setEnabled(False)
            self.get_action('monitor').setEnabled(False)
            
            # Also disable PID and monitoring if disconnected
            if self.pid_enabled:
                self.toggle_pid()
            if self.is_monitoring:
                self.toggle_monitoring()

    @Slot(dict)
    def update_displays(self, pid_data: Dict):
        """Update real-time displays with PID data."""
        try:
            # Extract values
            input_val = pid_data.get('input', 0.0)
            setpoint_val = pid_data.get('setpoint', 0.0)  
            output_val = pid_data.get('output', 0.0)
            error_val = input_val - setpoint_val
            timestamp = pid_data.get('timestamp', time.time())
            
            # Update value labels
            self.input_value_label.setText(f'{input_val:.3f} V')
            self.setpoint_value_label.setText(f'{setpoint_val:.3f} V')
            self.output_value_label.setText(f'{output_val:.3f} V')
            self.error_value_label.setText(f'{error_val:.3f} V')
            
            # Update 0D viewer
            data_0d = [
                DataRaw(name='Input', data=np.array([input_val]), labels=['Input'], units='V'),
                DataRaw(name='Setpoint', data=np.array([setpoint_val]), labels=['Setpoint'], units='V'),
                DataRaw(name='Output', data=np.array([output_val]), labels=['Output'], units='V'),
                DataRaw(name='Error', data=np.array([error_val]), labels=['Error'], units='V')
            ]
            
            data_export_0d = DataToExport(name='PID_Current', data=data_0d)
            self.current_viewer.show_data(data_export_0d)
            
            # Update time series data
            self._update_timeseries_data(timestamp, input_val, setpoint_val, output_val, error_val)
            
        except Exception as e:
            logger.error(f"Error updating displays: {e}")

    def _update_timeseries_data(self, timestamp: float, input_val: float, 
                              setpoint_val: float, output_val: float, error_val: float):
        """Update time series data and plots."""
        history_seconds = self.settings['monitoring', 'plot_history']
        
        # Add new data points
        self.time_data = np.append(self.time_data, timestamp)
        self.input_data = np.append(self.input_data, input_val)
        self.setpoint_data = np.append(self.setpoint_data, setpoint_val)
        self.output_data = np.append(self.output_data, output_val)
        self.error_data = np.append(self.error_data, error_val)
        
        # Trim data to history length
        cutoff_time = timestamp - history_seconds
        valid_indices = self.time_data >= cutoff_time
        
        self.time_data = self.time_data[valid_indices]
        self.input_data = self.input_data[valid_indices]
        self.setpoint_data = self.setpoint_data[valid_indices]
        self.output_data = self.output_data[valid_indices]
        self.error_data = self.error_data[valid_indices]
        
        # Create relative time axis (seconds from now)
        if len(self.time_data) > 0:
            relative_time = self.time_data - self.time_data[-1]
            
            # Create time axis
            time_axis = Axis(
                data=relative_time,
                label='Time',
                units='s',
                index=0
            )
            
            # Create 1D data
            data_1d = [
                DataRaw(name='Input', data=self.input_data, axes=[time_axis], units='V'),
                DataRaw(name='Setpoint', data=self.setpoint_data, axes=[time_axis], units='V'),
                DataRaw(name='Output', data=self.output_data, axes=[time_axis], units='V'),
                DataRaw(name='Error', data=self.error_data, axes=[time_axis], units='V')
            ]
            
            data_export_1d = DataToExport(name='PID_Timeseries', data=data_1d)
            self.timeseries_viewer.show_data(data_export_1d)

    def parameter_changed_slot(self, param, changes):
        """Handle parameter changes."""
        for param_change, change, data in changes:
            path = self.settings.childPath(param_change)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param_change.name()
                
            logger.debug(f"Parameter changed: {childName} = {data}")
            
            # Handle PID parameter changes
            if childName.startswith('pid_params') and self.is_connected:
                self._apply_pid_parameters()

    def _apply_pid_parameters(self):
        """Apply PID parameters to hardware."""
        if not self.controller or not self.controller.is_connected:
            return
            
        try:
            # Get parameter values
            p_gain = self.settings['pid_params', 'p_gain']
            i_gain = self.settings['pid_params', 'i_gain'] 
            d_gain = self.settings['pid_params', 'd_gain']
            setpoint = self.settings['pid_params', 'setpoint']
            
            # Update PID configuration
            if self.pid_config:
                self.pid_config.p_gain = p_gain
                self.pid_config.i_gain = i_gain
                self.pid_config.d_gain = d_gain
                self.pid_config.setpoint = setpoint
                
                # Apply to hardware
                success = self.controller.configure_pid(self.pid_config)
                if success:
                    logger.info(f"Applied PID parameters: P={p_gain}, I={i_gain}, D={d_gain}, SP={setpoint}")
                else:
                    logger.error("Failed to apply PID parameters to hardware")
                    
        except Exception as e:
            logger.error(f"Error applying PID parameters: {e}")

    def toggle_connection(self):
        """Toggle PyRPL connection."""
        if not self.is_connected:
            self._connect_to_pyrpl()
        else:
            self._disconnect_from_pyrpl()

    def _connect_to_pyrpl(self):
        """Connect to PyRPL."""
        try:
            hostname = self.settings['connection', 'hostname']
            config_name = self.settings['connection', 'config_name'] 
            timeout = self.settings['connection', 'timeout']
            mock_mode = self.settings['connection', 'mock_mode']
            
            if mock_mode:
                # Use mock connection
                from ..utils.pyrpl_wrapper import MockPyRPLConnection
                self.controller = MockPyRPLConnection(hostname)
                logger.info(f"Connected to mock PyRPL at {hostname}")
            else:
                # Use real PyRPL connection
                self.pyrpl_manager = PyRPLManager()
                self.controller = self.pyrpl_manager.connect_device(
                    hostname=hostname,
                    config_name=config_name,
                    connection_timeout=timeout,
                    status_callback=None
                )
                
                if not self.controller or not self.controller.is_connected:
                    raise ConnectionError(f"Failed to connect to PyRPL at {hostname}")
                    
                logger.info(f"Connected to PyRPL at {hostname}")
            
            # Create PID configuration
            self._setup_pid_configuration()
            
            # Update UI
            self.get_action('connect').setChecked(True)
            self.connection_changed.emit(True)
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.get_action('connect').setChecked(False)
            QtWidgets.QMessageBox.warning(None, 'Connection Error', 
                                        f'Failed to connect to PyRPL:\n{str(e)}')

    def _disconnect_from_pyrpl(self):
        """Disconnect from PyRPL."""
        try:
            # Stop monitoring first
            if self.is_monitoring:
                self.toggle_monitoring()
                
            # Disable PID if enabled
            if self.pid_enabled:
                self.toggle_pid()
                
            # Close connection
            if self.controller:
                if hasattr(self.controller, 'disconnect'):
                    self.controller.disconnect()
                self.controller = None
                
            if self.pyrpl_manager:
                self.pyrpl_manager = None
                
            self.pid_config = None
            
            # Update UI
            self.get_action('connect').setChecked(False)
            self.connection_changed.emit(False)
            
            logger.info("Disconnected from PyRPL")
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    def _setup_pid_configuration(self):
        """Setup PID configuration from parameters."""
        try:
            pid_module = self.settings['pid_config', 'pid_module']
            input_channel = InputChannel(self.settings['pid_config', 'input_channel'])
            output_channel = OutputChannel(self.settings['pid_config', 'output_channel'])
            
            self.pid_config = PIDConfiguration(
                channel=PIDChannel(pid_module),
                input_channel=input_channel,
                output_channel=output_channel,
                p_gain=self.settings['pid_params', 'p_gain'],
                i_gain=self.settings['pid_params', 'i_gain'],
                d_gain=self.settings['pid_params', 'd_gain'],
                setpoint=self.settings['pid_params', 'setpoint']
            )
            
            logger.info(f"Setup PID configuration: {pid_module}, {input_channel.value} -> {output_channel.value}")
            
        except Exception as e:
            logger.error(f"Error setting up PID configuration: {e}")

    def toggle_pid(self):
        """Toggle PID enable/disable."""
        if not self.is_connected or not self.pid_config:
            return
            
        try:
            if not self.pid_enabled:
                # Enable PID
                success = self.controller.enable_pid(self.pid_config, True)
                if success:
                    self.pid_enabled = True
                    self.get_action('enable_pid').setChecked(True)
                    self.pid_led.set_as_true()
                    self.pid_label.setText('Enabled')
                    logger.info("PID enabled")
                else:
                    logger.error("Failed to enable PID")
            else:
                # Disable PID
                success = self.controller.enable_pid(self.pid_config, False)
                if success:
                    self.pid_enabled = False
                    self.get_action('enable_pid').setChecked(False)
                    self.pid_led.set_as_false()
                    self.pid_label.setText('Disabled')
                    logger.info("PID disabled")
                else:
                    logger.error("Failed to disable PID")
                    
        except Exception as e:
            logger.error(f"Error toggling PID: {e}")

    def toggle_monitoring(self):
        """Toggle PID monitoring."""
        if not self.is_connected or not self.pid_config:
            return
            
        try:
            if not self.is_monitoring:
                # Start monitoring
                self.monitor_thread = PIDMonitorThread(self.controller, self.pid_config)
                self.monitor_thread.data_ready.connect(self.pid_data_signal.emit)
                self.monitor_thread.error_occurred.connect(self._handle_monitor_error)
                
                update_rate = self.settings['monitoring', 'update_rate']
                self.monitor_thread.start_monitoring(update_rate)
                
                self.is_monitoring = True
                self.get_action('monitor').setChecked(True)
                self.monitor_led.set_as_true()
                self.monitor_label.setText('Running')
                logger.info("Started PID monitoring")
            else:
                # Stop monitoring
                if self.monitor_thread:
                    self.monitor_thread.stop_monitoring()
                    self.monitor_thread = None
                    
                self.is_monitoring = False
                self.get_action('monitor').setChecked(False)
                self.monitor_led.set_as_false()
                self.monitor_label.setText('Stopped')
                logger.info("Stopped PID monitoring")
                
        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}")

    def _handle_monitor_error(self, error_msg: str):
        """Handle monitoring errors."""
        logger.error(f"Monitor error: {error_msg}")
        if self.is_monitoring:
            self.toggle_monitoring()

    def reset_plot_data(self):
        """Reset plot data arrays."""
        self.time_data = np.array([])
        self.input_data = np.array([])
        self.setpoint_data = np.array([])
        self.output_data = np.array([])
        self.error_data = np.array([])
        
        # Clear viewers
        self.timeseries_viewer.clear()
        logger.info("Reset plot data")

    def quit_extension(self):
        """Quit extension and cleanup."""
        try:
            # Stop monitoring
            if self.is_monitoring:
                self.toggle_monitoring()
                
            # Disconnect
            if self.is_connected:
                self._disconnect_from_pyrpl()
                
            # Close docks
            self.control_dock.close()
            self.monitor_dock.close()
            self.plot_dock.close()
            
            logger.info("PyRPL PID Extension closed")
            
        except Exception as e:
            logger.error(f"Error closing extension: {e}")