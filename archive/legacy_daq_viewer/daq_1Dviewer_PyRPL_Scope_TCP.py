# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL Oscilloscope (TCP/IP Mode)

This plugin provides PyMoDAQ 1D viewer functionality for the PyRPL oscilloscope
using PyMoDAQ's native TCP/IP infrastructure.

Architecture:
- PyMoDAQ (master) controls PyRPL (slave)
- Plugin is lightweight TCP client using TCPClientTemplate
- Server manages PyRPL instance and hardware communication
- Uses PyMoDAQ's standard GRABBER protocol

Features:
- Red Pitaya oscilloscope data acquisition
- Real-time trace capture with time axis
- Configurable sampling and triggering
- Clean reconnection handling
- No multiprocessing complexity

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import numpy as np
from typing import Optional

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base, comon_parameters, main
)
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.tcp_ip.tcp_server_client import TCPClientTemplate
from pymodaq_data.data import DataToExport

from pymodaq_plugins_pyrpl.utils.tcp_server_manager import TCPServerManager


class DAQ_1DViewer_PyRPL_Scope_TCP(DAQ_Viewer_base):
    """
    PyMoDAQ 1D Viewer plugin for PyRPL oscilloscope using TCP/IP architecture.
    
    This plugin connects to the PyRPL TCP server as a GRABBER client,
    following PyMoDAQ's standard TCP/IP protocol.
    """
    
    # Plugin parameters that appear in PyMoDAQ GUI
    params = comon_parameters + [
        {'title': 'Server Connection:', 'name': 'server', 'type': 'group', 'children': [
            {'title': 'Server IP:', 'name': 'ip_address', 'type': 'str',
             'value': 'localhost', 'tip': 'PyRPL TCP server IP address'},
            {'title': 'Server Port:', 'name': 'port', 'type': 'int',
             'value': 6341, 'min': 1024, 'max': 65535,
             'tip': 'PyRPL TCP server port'},
            {'title': 'Connection Timeout (s):', 'name': 'timeout', 'type': 'float',
             'value': 10.0, 'min': 1.0, 'max': 60.0,
             'tip': 'Maximum time to wait for server connection'},
        ]},
        {'title': 'Oscilloscope:', 'name': 'scope', 'type': 'group', 'children': [
            {'title': 'Input Channel:', 'name': 'input_channel', 'type': 'list',
             'limits': ['in1', 'in2'], 'value': 'in1',
             'tip': 'Oscilloscope input channel selection'},
            {'title': 'Decimation:', 'name': 'decimation', 'type': 'int',
             'value': 64, 'min': 1, 'max': 65536,
             'tip': 'Sampling rate decimation factor (125 MHz / decimation)'},
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
             'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge',
                       'ch2_positive_edge', 'ch2_negative_edge', 'external_positive_edge'],
             'value': 'immediately', 'tip': 'Trigger source for data acquisition'},
            {'title': 'Duration (ms):', 'name': 'duration', 'type': 'float',
             'value': 1.0, 'min': 0.001, 'max': 1000.0, 'step': 0.1,
             'tip': 'Acquisition duration in milliseconds'},
        ]},
        {'title': 'Development:', 'name': 'dev', 'type': 'group', 'children': [
            {'title': 'Debug Logging:', 'name': 'debug_logging', 'type': 'bool', 'value': False,
             'tip': 'Enable verbose debug logging'},
        ]},
    ]
    
    def __init__(self, parent=None, params_state=None):
        """Initialize the plugin."""
        super().__init__(parent, params_state)
        
        # TCP client (will be initialized in ini_detector)
        self.tcp_client: Optional[TCPClientWrapper] = None
        
        # Connection state
        self.is_connected = False
        
        # Data caching
        self.last_data = None
    
    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes.
        
        Args:
            param: Parameter that was changed
        """
        if not self.is_connected:
            return
        
        try:
            # Send configuration to server when scope parameters change
            if param.parent().name() == 'scope':
                config = {
                    'input1': self.settings['scope', 'input_channel'],
                    'decimation': self.settings['scope', 'decimation'],
                    'trigger_source': self.settings['scope', 'trigger_source'],
                    'duration': self.settings['scope', 'duration'] / 1000.0,  # Convert ms to s
                }
                
                # Send configure command to server
                self.tcp_client.send_command({
                    'command': 'configure',
                    'module': 'scope',
                    'config': config
                })
                
                if self.settings['dev', 'debug_logging']:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Scope configured: {param.name()} = {param.value()}", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to update scope parameter: {e}", 'log']))
    
    def ini_detector(self, controller=None):
        """
        Initialize the detector (connect to TCP server).
        
        Auto-starts the PyRPL TCP server if not already running.
        
        Returns:
            Initialization status message
        """
        self.emit_status(ThreadCommand('Update_Status',
            ["Initializing PyRPL TCP connection...", 'log']))
        
        try:
            # Get server configuration
            ip = self.settings['server', 'ip_address']
            port = self.settings['server', 'port']
            timeout = self.settings['server', 'timeout']
            
            # Auto-start server if not running
            self.emit_status(ThreadCommand('Update_Status',
                ["Checking PyRPL TCP server...", 'log']))
            
            # Note: For real hardware, you'd pass redpitaya_ip from settings
            # For now, using localhost assumes mock mode for testing
            server_running = TCPServerManager.ensure_server_running(
                host=ip,
                port=port,
                redpitaya_ip='100.107.106.75',  # TODO: Add to settings
                config_name='pymodaq',
                mock_mode=(ip == 'localhost'),  # Mock if localhost
                timeout=timeout
            )
            
            if not server_running:
                raise RuntimeError("Failed to start/connect to PyRPL TCP server")
            
            self.emit_status(ThreadCommand('Update_Status',
                ["Connecting to PyRPL server...", 'log']))
            
            # Create TCP client
            self.tcp_client = TCPClientWrapper(
                ipaddress=ip,
                port=port,
                client_type='GRABBER',
                timeout=timeout,
                parent_plugin=self
            )
            
            # Connect to server
            if not self.tcp_client.connect():
                raise RuntimeError("Failed to connect to PyRPL TCP server")
            
            # Send initial scope configuration
            config = {
                'input1': self.settings['scope', 'input_channel'],
                'decimation': self.settings['scope', 'decimation'],
                'trigger_source': self.settings['scope', 'trigger_source'],
                'duration': self.settings['scope', 'duration'] / 1000.0,
            }
            
            self.tcp_client.send_command({
                'command': 'configure',
                'module': 'scope',
                'config': config
            })
            
            self.is_connected = True
            
            # Initialize data structure
            self.controller = {'tcp_client': self.tcp_client}
            
            # Emit success
            self.emit_status(ThreadCommand('Update_Status',
                [f"✓ Connected to PyRPL server at {ip}:{port}", 'log']))
            
            return "PyRPL Scope TCP ready"
        
        except Exception as e:
            error_msg = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            
            # Cleanup on failure
            self.close()
            
            return error_msg
    
    def close(self):
        """Close TCP connection and cleanup."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL Scope TCP connection...", 'log']))
        
        if self.tcp_client:
            try:
                self.tcp_client.close()
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Warning: Error closing TCP client: {e}", 'log']))
        
        # Release server (will auto-stop if we were the last client)
        try:
            ip = self.settings['server', 'ip_address']
            port = self.settings['server', 'port']
            TCPServerManager.release_server(ip, port)
        except Exception as e:
            pass  # Already logged above
        
        self.tcp_client = None
        self.is_connected = False
        
        self.emit_status(ThreadCommand('Update_Status',
            ["✓ PyRPL Scope TCP connection closed", 'log']))
    
    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquire oscilloscope data from PyRPL server.
        
        Args:
            Naverage: Number of averages (currently unused)
            **kwargs: Additional acquisition parameters
        """
        try:
            if not self.is_connected or not self.tcp_client:
                self.emit_status(ThreadCommand('Update_Status',
                    ["Not connected to server", 'log']))
                return
            
            # Build acquisition command
            command_data = {
                'command': 'grab',
                'module': 'scope',
                'config': {
                    'input1': self.settings['scope', 'input_channel'],
                    'decimation': self.settings['scope', 'decimation'],
                    'trigger_source': self.settings['scope', 'trigger_source'],
                },
                'timebase': self.settings['scope', 'duration'] / 1000.0,  # Convert ms to s
            }
            
            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    ["Requesting scope acquisition...", 'log']))
            
            # Send grab command and wait for data
            dte = self.tcp_client.grab_data(command_data)
            
            if dte is None:
                self.emit_status(ThreadCommand('Update_Status',
                    ["No data received from server", 'log']))
                return
            
            # Convert DataToExport to PyMoDAQ DataFromPlugins format
            data_list = []
            for data_raw in dte.data:
                # Extract numpy array and axis
                trace_data = data_raw.data[0]  # First (and only) array in list
                
                # Get time axis from DataRaw
                if data_raw.axes:
                    time_axis_data = data_raw.axes[0].data
                    time_label = data_raw.axes[0].label
                    time_units = data_raw.axes[0].units
                else:
                    # Fallback: create time axis from data length
                    duration = self.settings['scope', 'duration'] / 1000.0
                    n_points = len(trace_data)
                    time_axis_data = np.linspace(0, duration, n_points)
                    time_label = 'Time'
                    time_units = 's'
                
                # Create PyMoDAQ Axis
                x_axis = Axis(
                    data=time_axis_data,
                    label=time_label,
                    units=time_units
                )
                
                data_list.append(trace_data)
            
            # Create DataFromPlugins with proper axis
            self.last_data = DataFromPlugins(
                name='PyRPL_Scope',
                data=data_list,
                dim='Data1D',
                axes=[x_axis]
            )
            
            # Emit data
            self.dte_signal.emit(self.last_data)
            
            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Data acquired: {len(data_list[0])} points", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Data acquisition error: {e}", 'log']))
    
    def stop(self):
        """Stop acquisition (no-op for scope)."""
        pass


class TCPClientWrapper:
    """
    Wrapper around PyMoDAQ's TCPClientTemplate for plugin use.
    
    This class adapts TCPClientTemplate to work within a PyMoDAQ plugin,
    providing simplified command/response methods.
    """
    
    def __init__(self, ipaddress: str, port: int, client_type: str, timeout: float, parent_plugin):
        """
        Initialize TCP client wrapper.
        
        Args:
            ipaddress: Server IP address
            port: Server port
            client_type: 'GRABBER' or 'ACTUATOR'
            timeout: Connection timeout in seconds
            parent_plugin: Parent plugin instance for logging
        """
        self.parent = parent_plugin
        self.timeout = timeout
        self.client_type = client_type
        
        # Create TCP client
        self.client = SimpleTCPClient(
            ipaddress=ipaddress,
            port=port,
            client_type=client_type,
            parent=parent_plugin
        )
    
    def connect(self) -> bool:
        """
        Connect to server.
        
        Returns:
            True if connected successfully
        """
        try:
            # Initialize connection in thread
            from threading import Thread
            connect_thread = Thread(target=self.client.init_connection)
            connect_thread.start()
            connect_thread.join(timeout=self.timeout)
            
            if not self.client.connected:
                return False
            
            return True
        
        except Exception as e:
            self.parent.emit_status(ThreadCommand('Update_Status',
                [f"Connection error: {e}", 'log']))
            return False
    
    def send_command(self, command_data: dict):
        """
        Send a command to the server.
        
        Args:
            command_data: Command dictionary
        """
        if self.client.socket:
            self.client.socket.check_sended_with_serializer(command_data)
    
    def grab_data(self, command_data: dict) -> Optional[DataToExport]:
        """
        Send grab command and wait for data response.
        
        Args:
            command_data: Grab command dictionary
        
        Returns:
            DataToExport from server, or None on error
        """
        try:
            # Send command
            self.send_command(command_data)
            
            # Wait for response
            # The client's get_data method will be called automatically
            # when data arrives, and it will store it in self.client.received_data
            
            # Poll for data with timeout
            import time
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if hasattr(self.client, 'received_data') and self.client.received_data:
                    data = self.client.received_data
                    self.client.received_data = None  # Clear for next acquisition
                    return data
                time.sleep(0.01)  # 10ms polling interval
            
            self.parent.emit_status(ThreadCommand('Update_Status',
                [f"Data timeout after {self.timeout}s", 'log']))
            return None
        
        except Exception as e:
            self.parent.emit_status(ThreadCommand('Update_Status',
                [f"Grab error: {e}", 'log']))
            return None
    
    def close(self):
        """Close TCP connection."""
        if self.client:
            self.client.close()


class SimpleTCPClient(TCPClientTemplate):
    """
    Simple TCP client implementation for PyRPL scope plugin.
    
    Inherits from PyMoDAQ's TCPClientTemplate to handle low-level
    TCP communication and message deserialization.
    """
    
    def __init__(self, ipaddress: str, port: int, client_type: str, parent):
        """Initialize TCP client."""
        super().__init__(ipaddress=ipaddress, port=port, client_type=client_type)
        self.parent = parent
        self.received_data = None
    
    def post_init(self, extra_commands=[]):
        """Called after connection is established."""
        # Send client type to server
        self.socket.check_sended_with_serializer(self.client_type)
        
        if hasattr(self.parent, 'emit_status'):
            self.parent.emit_status(ThreadCommand('Update_Status',
                ["TCP client connected and initialized", 'log']))
    
    def ready_to_read(self):
        """Called when data is ready to read from socket."""
        # Deserialize message type
        message = self._deserializer.string_deserialization()
        self.get_data(message)
    
    def get_data(self, message: str):
        """
        Process incoming message from server.
        
        Args:
            message: Message type string ('Done', 'Error', etc.)
        """
        if self.socket is not None:
            if message == 'Done':
                # Data follows
                data = self._deserializer.dte_deserialization()
                self.received_data = data
                
                if hasattr(self.parent, 'emit_status') and hasattr(self.parent.settings, 'child'):
                    if self.parent.settings['dev', 'debug_logging']:
                        self.parent.emit_status(ThreadCommand('Update_Status',
                            ["Data received from server", 'log']))
            
            elif message == 'Error':
                # Error message follows
                error_msg = self._deserializer.string_deserialization()
                if hasattr(self.parent, 'emit_status'):
                    self.parent.emit_status(ThreadCommand('Update_Status',
                        [f"Server error: {error_msg}", 'log']))
            
            else:
                # Other messages
                if hasattr(self.parent, 'emit_status'):
                    self.parent.emit_status(ThreadCommand('Update_Status',
                        [f"Server message: {message}", 'log']))
    
    def ready_to_write(self):
        """Called when socket is ready for writing (unused)."""
        pass
    
    def ready_with_error(self):
        """Called when socket encounters an error."""
        self.connected = False
        if hasattr(self.parent, 'emit_status'):
            self.parent.emit_status(ThreadCommand('Update_Status',
                ["TCP connection error", 'log']))
    
    def process_error_in_polling(self, e: Exception):
        """Handle errors during socket polling."""
        if hasattr(self.parent, 'emit_status'):
            self.parent.emit_status(ThreadCommand('Update_Status',
                [f"Polling error: {e}", 'log']))


if __name__ == '__main__':
    main(__file__)
