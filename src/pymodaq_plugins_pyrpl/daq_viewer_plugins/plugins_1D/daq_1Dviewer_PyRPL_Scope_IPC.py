# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL Oscilloscope (IPC Mode)

This plugin provides PyMoDAQ 1D viewer functionality for the PyRPL oscilloscope
using Inter-Process Communication (IPC) to isolate PyRPL's Qt event loop from
PyMoDAQ's multi-threaded architecture.

Architecture:
- PyRPL runs in separate subprocess with its own Qt event loop
- Plugin acts as lightweight IPC client
- Complete isolation prevents Qt threading conflicts
- Robust error handling and connection management

Features:
- Red Pitaya oscilloscope data acquisition
- Real-time trace capture with time axis
- Configurable sampling and triggering
- Automatic server process management
- Mock mode support for development

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import sys
import time
import subprocess
from pathlib import Path
from multiprocessing.connection import Client
from typing import Optional, List, Union

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base, comon_parameters, main
)
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

# Try to locate server script within package
try:
    from importlib import resources
    SERVER_SCRIPT_AVAILABLE = True
except ImportError:
    # Python < 3.9 fallback
    try:
        import importlib_resources as resources
        SERVER_SCRIPT_AVAILABLE = True
    except ImportError:
        SERVER_SCRIPT_AVAILABLE = False


class DAQ_1DViewer_PyRPL_Scope_IPC(DAQ_Viewer_base):
    """
    PyMoDAQ 1D Viewer plugin for PyRPL oscilloscope using IPC architecture.

    This plugin demonstrates the solution to PyRPL-PyMoDAQ integration challenges
    by running PyRPL in a completely separate process and communicating via IPC.
    """

    # Plugin parameters that appear in PyMoDAQ GUI
    params = comon_parameters + [
        {'title': 'IPC Server Settings:', 'name': 'server_settings', 'type': 'group', 'children': [
            {'title': 'IP Address:', 'name': 'ip_address', 'type': 'str', 'value': 'localhost',
             'tip': 'IP address for IPC communication (usually localhost)'},
            {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': 6000, 'min': 1024, 'max': 65535,
             'tip': 'Port number for IPC communication'},
            {'title': 'Auth Key:', 'name': 'auth_key', 'type': 'str', 'value': 'pymodaq_pyrpl_secret',
             'tip': 'Authentication key for secure IPC communication'},
            {'title': 'Connection Timeout (s):', 'name': 'connection_timeout', 'type': 'float',
             'value': 30.0, 'min': 5.0, 'max': 120.0,
             'tip': 'Maximum time to wait for server startup'},
        ]},
        {'title': 'PyRPL Settings:', 'name': 'pyrpl_settings', 'type': 'group', 'children': [
            {'title': 'Config File:', 'name': 'pyrpl_config_file', 'type': 'browsepath',
             'value': '', 'tip': 'Path to PyRPL configuration file'},
            {'title': 'Red Pitaya Hostname:', 'name': 'rp_hostname', 'type': 'str',
             'value': 'rp-f08d6c.local', 'tip': 'Red Pitaya network address'},
        ]},
        {'title': 'Oscilloscope Settings:', 'name': 'scope_settings', 'type': 'group', 'children': [
            {'title': 'Input Channel:', 'name': 'input_channel', 'type': 'list',
             'limits': ['in1', 'in2'], 'value': 'in1',
             'tip': 'Oscilloscope input channel selection'},
            {'title': 'Decimation:', 'name': 'decimation', 'type': 'int',
             'value': 64, 'min': 1, 'max': 65536,
             'tip': 'Sampling rate decimation factor'},
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
             'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge',
                       'ch2_positive_edge', 'ch2_negative_edge', 'external_positive_edge'],
             'value': 'immediately', 'tip': 'Trigger source for data acquisition'},
            {'title': 'Trigger Delay:', 'name': 'trigger_delay', 'type': 'float',
             'value': 0.0, 'min': -1.0, 'max': 1.0,
             'tip': 'Trigger delay in seconds'},
        ]},
        {'title': 'Development:', 'name': 'dev_settings', 'type': 'group', 'children': [
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False,
             'tip': 'Enable mock mode for development without hardware'},
            {'title': 'Debug Logging:', 'name': 'debug_logging', 'type': 'bool', 'value': False,
             'tip': 'Enable debug logging for troubleshooting'},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        """Initialize the plugin."""
        super().__init__(parent, params_state)

        # IPC connection management
        self.server_process: Optional[subprocess.Popen] = None
        self.connection: Optional[Client] = None

        # Plugin state
        self.is_connected = False

        # Data caching
        self.last_data = None
        self.last_time_axis = None

    def _send_command(self, attribute: str, *args, **kwargs) -> any:
        """
        Send a command to the PyRPL server and return the result.

        Args:
            attribute: Dot-separated attribute path (e.g., 'scope.data', 'pid0.setpoint')
            *args: Arguments to pass to method calls
            **kwargs: Keyword arguments to pass to method calls

        Returns:
            Result from PyRPL server

        Raises:
            ConnectionError: If not connected to server
            RuntimeError: If server returns an error
        """
        if not self.connection:
            raise ConnectionError("Not connected to PyRPL server")

        try:
            # Prepare and send command
            payload = {
                'attribute': attribute,
                'args': args,
                'kwargs': kwargs
            }

            if self.settings['dev_settings', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Sending command: {attribute}", 'log']))

            self.connection.send(payload)

            # Wait for response
            response = self.connection.recv()

            # Handle server response
            if response['status'] == 'error':
                error_msg = f"PyRPL server error: {response['message']}"
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                raise RuntimeError(error_msg)

            return response['result']

        except (EOFError, ConnectionResetError, BrokenPipeError) as e:
            # Connection lost
            self.is_connected = False
            self.emit_status(ThreadCommand('Update_Status',
                [f"Connection to PyRPL server lost: {e}", 'log']))
            raise ConnectionError("Connection to PyRPL server lost") from e

    def _ping_server(self) -> bool:
        """
        Test server connectivity.

        Returns:
            True if server responds to ping, False otherwise
        """
        try:
            result = self._send_command('ping')
            return result == 'pong'
        except Exception:
            return False

    def _start_server(self) -> bool:
        """
        Start the PyRPL server process.

        Returns:
            True if server started successfully, False otherwise
        """
        if not SERVER_SCRIPT_AVAILABLE:
            self.emit_status(ThreadCommand('Update_Status',
                ["Cannot locate server script - importlib.resources not available", 'log']))
            return False

        try:
            # Locate server script within package
            with resources.path('pymodaq_plugins_pyrpl.utils', 'pyrpl_server.py') as server_path:
                if not server_path.exists():
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Server script not found at {server_path}", 'log']))
                    return False

                # Build command to run server
                cmd = [
                    sys.executable, str(server_path),
                    self.settings['server_settings', 'ip_address'],
                    str(self.settings['server_settings', 'port']),
                    self.settings['server_settings', 'auth_key'],
                    self.settings['pyrpl_settings', 'pyrpl_config_file'] or 'default'
                ]

                self.emit_status(ThreadCommand('Update_Status',
                    ["Starting PyRPL server process...", 'log']))

                # Start server process
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                return True

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to start server process: {e}", 'log']))
            return False

    def _connect_to_server(self) -> bool:
        """
        Connect to PyRPL server with retries.

        Returns:
            True if connected successfully, False otherwise
        """
        address = (
            self.settings['server_settings', 'ip_address'],
            self.settings['server_settings', 'port']
        )
        authkey = self.settings['server_settings', 'auth_key'].encode('utf-8')
        timeout = self.settings['server_settings', 'connection_timeout']

        # Retry connection with timeout
        start_time = time.time()
        retry_count = 0

        while time.time() - start_time < timeout:
            try:
                self.connection = Client(address, authkey=authkey)

                # Test connection with ping
                if self._ping_server():
                    self.is_connected = True
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Connected to PyRPL server on attempt {retry_count + 1}", 'log']))
                    return True
                else:
                    self.connection.close()
                    self.connection = None

            except ConnectionRefusedError:
                # Server not ready yet, wait and retry
                retry_count += 1
                if retry_count % 5 == 0:  # Log every 5 attempts
                    remaining = timeout - (time.time() - start_time)
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Waiting for server... ({remaining:.1f}s remaining)", 'log']))

                time.sleep(1)

            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Connection attempt failed: {e}", 'log']))
                time.sleep(1)

        return False

    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes to the PyRPL hardware.

        Args:
            param: Parameter that was changed
        """
        if not self.is_connected:
            return

        try:
            # Apply oscilloscope settings
            if param.parent().name() == 'scope_settings':
                if param.name() == 'decimation':
                    self._send_command('scope.decimation', param.value())
                elif param.name() == 'trigger_source':
                    self._send_command('scope.trigger_source', param.value())
                elif param.name() == 'trigger_delay':
                    self._send_command('scope.trigger_delay', param.value())

                self.emit_status(ThreadCommand('Update_Status',
                    [f"Updated {param.name()}: {param.value()}", 'log']))

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to apply setting {param.name()}: {e}", 'log']))

    def ini_detector(self, controller=None):
        """
        Initialize the detector (establish connection to PyRPL server).

        Args:
            controller: Unused, maintained for PyMoDAQ compatibility

        Returns:
            Initialization status
        """
        self.emit_status(ThreadCommand('Update_Status', ["Initializing PyRPL IPC connection...", 'log']))

        try:
            # Check if using mock mode
            if self.settings['dev_settings', 'mock_mode']:
                self.emit_status(ThreadCommand('Update_Status', ["Mock mode enabled - skipping hardware", 'log']))
                self.status.initialized = True
                self.status.info = "Mock mode active"
                return self.status

            # Start server process
            if not self._start_server():
                raise RuntimeError("Failed to start PyRPL server process")

            # Connect to server
            if not self._connect_to_server():
                raise RuntimeError("Failed to connect to PyRPL server")

            # Configure initial oscilloscope settings
            self.commit_settings(self.settings['scope_settings', 'decimation'])
            self.commit_settings(self.settings['scope_settings', 'trigger_source'])
            self.commit_settings(self.settings['scope_settings', 'trigger_delay'])

            # Success
            self.status.initialized = True
            self.status.info = "Connected to PyRPL server"
            self.emit_status(ThreadCommand('Update_Status', ["PyRPL initialization complete", 'log']))

        except Exception as e:
            self.status.initialized = False
            self.status.info = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))

            # Cleanup on failure
            self.close()

        return self.status

    def close(self):
        """Close connections and clean up resources."""
        self.emit_status(ThreadCommand('Update_Status', ["Closing PyRPL connection...", 'log']))

        # Close IPC connection
        if self.connection:
            try:
                # Send shutdown command to server
                self.connection.send({'command': 'shutdown'})
                time.sleep(0.5)  # Give server time to process shutdown
            except Exception:
                pass  # Connection might already be closed
            finally:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None

        # Terminate server process
        if self.server_process:
            try:
                # First try graceful termination
                self.server_process.terminate()

                # Wait for process to exit
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't respond
                    self.server_process.kill()
                    self.server_process.wait()

            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Warning: Error terminating server process: {e}", 'log']))
            finally:
                self.server_process = None

        self.is_connected = False
        self.emit_status(ThreadCommand('Update_Status', ["PyRPL connection closed", 'log']))

    def grab_data(self, naverage: int = 1, **kwargs):
        """
        Acquire oscilloscope trace data.

        Args:
            naverage: Number of averages (handled by hardware)
            **kwargs: Additional parameters
        """
        try:
            if self.settings['dev_settings', 'mock_mode']:
                # Generate mock data for development
                times = np.linspace(0, 1e-3, 16384)  # 1ms timespan, 16k points
                signal = np.sin(2 * np.pi * 1000 * times) + 0.1 * np.random.randn(len(times))

                x_axis = Axis(data=times, label='Time', units='s')

                self.data_grabed_signal.emit([DataFromPlugins(
                    name='PyRPL Scope (Mock)',
                    data=[signal],
                    dim='Data1D',
                    axes=[x_axis]
                )])
                return

            # Real hardware data acquisition
            if not self.is_connected:
                raise RuntimeError("Not connected to PyRPL server")

            # Get oscilloscope data from server
            trace_data = self._send_command('scope.data')
            time_data = self._send_command('scope.times')

            # Cache data for potential reuse
            self.last_data = np.array(trace_data)
            self.last_time_axis = np.array(time_data)

            # Create PyMoDAQ data structure
            x_axis = Axis(data=self.last_time_axis, label='Time', units='s')

            self.data_grabed_signal.emit([DataFromPlugins(
                name='PyRPL Scope',
                data=[self.last_data],
                dim='Data1D',
                axes=[x_axis]
            )])

            if self.settings['dev_settings', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Acquired {len(self.last_data)} data points", 'log']))

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Data acquisition failed: {e}", 'log']))

            # Try to reconnect if connection was lost
            if not self.is_connected:
                self.emit_status(ThreadCommand('Update_Status',
                    ["Attempting to reconnect...", 'log']))
                try:
                    if self._connect_to_server():
                        self.emit_status(ThreadCommand('Update_Status',
                            ["Reconnected successfully", 'log']))
                except Exception:
                    pass


if __name__ == '__main__':
    main(__file__)