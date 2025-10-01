# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL Oscilloscope (IPC Mode)

This plugin provides PyMoDAQ 1D viewer functionality for the PyRPL oscilloscope
using Inter-Process Communication (IPC) to isolate PyRPL's Qt event loop from
PyMoDAQ's multi-threaded architecture.

Architecture:
- PyRPL runs in separate subprocess with its own Qt event loop
- Plugin communicates via multiprocessing.Queue
- Complete isolation prevents Qt threading conflicts
- Robust error handling and connection management

Features:
- Red Pitaya oscilloscope data acquisition
- Real-time trace capture with time axis
- Configurable sampling and triggering
- Automatic worker process management
- Mock mode support for development

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import time
import multiprocessing
from multiprocessing import Queue, Process
from queue import Empty
from typing import Optional

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base, comon_parameters, main
)
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

# Import the shared worker manager (singleton pattern)
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


class DAQ_1DViewer_PyRPL_Scope_IPC(DAQ_Viewer_base):
    """
    PyMoDAQ 1D Viewer plugin for PyRPL oscilloscope using IPC architecture.

    This plugin demonstrates the solution to PyRPL-PyMoDAQ integration challenges
    by running PyRPL in a completely separate process and communicating via queues.
    """

    # Plugin parameters that appear in PyMoDAQ GUI
    params = comon_parameters + [
        {'title': 'Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya Hostname:', 'name': 'rp_hostname', 'type': 'str',
             'value': '100.107.106.75', 'tip': 'Red Pitaya network address'},
            {'title': 'PyRPL Config Name:', 'name': 'config_name', 'type': 'str',
             'value': 'pymodaq', 'tip': 'PyRPL configuration name'},
            {'title': 'Connection Timeout (s):', 'name': 'connection_timeout', 'type': 'float',
             'value': 30.0, 'min': 5.0, 'max': 120.0,
             'tip': 'Maximum time to wait for worker startup'},
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
            {'title': 'Acquisition Timeout (s):', 'name': 'acquisition_timeout', 'type': 'float',
             'value': 5.0, 'min': 1.0, 'max': 30.0,
             'tip': 'Maximum time to wait for scope acquisition'},
        ]},
        {'title': 'Development:', 'name': 'dev', 'type': 'group', 'children': [
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False,
             'tip': 'Enable mock mode for development without hardware'},
            {'title': 'Debug Logging:', 'name': 'debug_logging', 'type': 'bool', 'value': False,
             'tip': 'Enable verbose debug logging'},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        """Initialize the plugin."""
        super().__init__(parent, params_state)

        # Shared worker manager (singleton - one worker shared by all plugins)
        self.manager = None
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None

        # Plugin state
        self.is_connected = False

        # Data caching
        self.last_data = None
        self.last_time_axis = None

    def _send_command(self, command: str, params: dict = None, timeout: float = 5.0) -> dict:
        """
        Send a command to the PyRPL worker via SharedPyRPLManager.

        This method uses the manager's send_command which handles:
        - UUID generation for command multiplexing
        - Thread-safe response routing
        - Automatic cleanup of pending responses

        Args:
            command: Command name
            params: Command parameters (optional)
            timeout: Response timeout in seconds

        Returns:
            Response dictionary from worker

        Raises:
            RuntimeError: If worker returns error or not initialized
            TimeoutError: If no response within timeout
        """
        if not self.manager:
            raise RuntimeError("Shared worker manager not initialized")

        if self.settings['dev', 'debug_logging']:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Sending command: {command}", 'log']))

        # Use manager's send_command for proper UUID-based multiplexing
        response = self.manager.send_command(command, params or {}, timeout=timeout)

        if response['status'] == 'error':
            error_msg = f"PyRPL worker error: {response['data']}"
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            raise RuntimeError(error_msg)

        return response

    def _start_worker(self) -> bool:
        """
        Start (or connect to) the shared PyRPL worker process.

        CRITICAL: This method uses SharedPyRPLManager singleton to ensure
        only ONE PyRPL worker process exists for ALL plugins. This prevents:
        - Multiple concurrent SSH connections to Red Pitaya
        - Monitor server conflicts
        - FPGA bitstream reload issues
        - "NoneType object is not subscriptable" errors

        Returns:
            True if worker is ready and responding
        """
        try:
            self.emit_status(ThreadCommand('Update_Status',
                ["Connecting to shared PyRPL worker...", 'log']))

            # Get the singleton manager instance
            # This ensures ALL plugins share the same worker process
            self.manager = get_shared_worker_manager()

            # Build configuration
            config = {
                'hostname': self.settings['connection', 'rp_hostname'],
                'config_name': self.settings['connection', 'config_name'],
                'mock_mode': self.settings['dev', 'mock_mode']
            }

            # Start worker (or get existing one if already running)
            # This will start a NEW worker ONLY if none exists
            # Otherwise it returns the queues to the EXISTING worker
            self.command_queue, self.response_queue = self.manager.start_worker(config)

            # Test connection with ping command
            timeout = self.settings['connection', 'connection_timeout']
            
            self.emit_status(ThreadCommand('Update_Status',
                ["Testing worker connection with ping...", 'log']))
            
            response = self.manager.send_command('ping', {}, timeout=timeout)
            
            if response['status'] == 'ok' and response['data'] == 'pong':
                self.is_connected = True
                self.emit_status(ThreadCommand('Update_Status',
                    ["Shared PyRPL worker connected successfully", 'log']))
                return True
            else:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Worker ping test failed: {response}", 'log']))
                return False

        except TimeoutError as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Worker connection timeout: {e}", 'log']))
            return False
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to connect to worker: {e}", 'log']))
            return False

    def commit_settings(self, param: Parameter):
        """
        Apply parameter changes to PyRPL hardware.

        Args:
            param: Parameter that was changed
        """
        if not self.is_connected:
            return

        try:
            # Only apply scope settings that affect hardware
            if param.parent().name() == 'scope':
                if param.name() == 'decimation':
                    self._send_command('scope_set_decimation', {'value': param.value()})
                elif param.name() == 'trigger_source':
                    self._send_command('scope_set_trigger', {'source': param.value()})

                if self.settings['dev', 'debug_logging']:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Updated {param.name()}: {param.value()}", 'log']))

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to apply setting {param.name()}: {e}", 'log']))

    def ini_detector(self, controller=None):
        """
        Initialize the detector (start PyRPL worker process).

        Args:
            controller: Unused, maintained for PyMoDAQ compatibility

        Returns:
            Initialization status
        """
        self.emit_status(ThreadCommand('Update_Status',
            ["Initializing PyRPL IPC connection...", 'log']))

        try:
            # Start worker process
            if not self._start_worker():
                raise RuntimeError("Failed to start PyRPL worker process")

            # Send initial test ping
            response = self._send_command('ping', timeout=5.0)
            if response['data'] != 'pong':
                raise RuntimeError("Worker ping test failed")

            # Apply initial scope configuration
            self._send_command('scope_set_decimation',
                {'value': self.settings['scope', 'decimation']})
            self._send_command('scope_set_trigger',
                {'source': self.settings['scope', 'trigger_source']})

            # Success
            self.status.initialized = True
            self.status.info = "PyRPL worker ready"
            self.emit_status(ThreadCommand('Update_Status',
                ["PyRPL initialization complete", 'log']))

        except Exception as e:
            self.status.initialized = False
            self.status.info = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))

            # Cleanup on failure
            self.close()

        return self.status

    def close(self):
        """
        Close plugin connection and clean up resources.
        
        IMPORTANT: This plugin does NOT shutdown the shared PyRPL worker
        because other plugins may still be using it. The SharedPyRPLManager
        handles worker lifecycle via atexit handlers.
        
        This method only cleans up this plugin's local references.
        """
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL plugin connection...", 'log']))

        # Clean up local references
        # DO NOT shutdown the shared worker - other plugins may need it
        self.command_queue = None
        self.response_queue = None
        self.manager = None
        self.is_connected = False

        self.emit_status(ThreadCommand('Update_Status',
            ["PyRPL plugin connection closed", 'log']))

    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquire oscilloscope trace data.

        Args:
            Naverage: Number of averages (handled by hardware, kept for PyMoDAQ compatibility)
            **kwargs: Additional parameters
        """
        try:
            # Build acquisition parameters
            acq_params = {
                'decimation': self.settings['scope', 'decimation'],
                'trigger_source': self.settings['scope', 'trigger_source'],
                'input_channel': self.settings['scope', 'input_channel'],
                'timeout': self.settings['scope', 'acquisition_timeout']
            }

            # Send acquisition command
            response = self._send_command(
                'scope_acquire',
                acq_params,
                timeout=self.settings['scope', 'acquisition_timeout'] + 2.0
            )

            # Extract data from response
            data = response['data']
            voltage = np.array(data['voltage'])
            time_axis = np.array(data['time'])

            # Cache data
            self.last_data = voltage
            self.last_time_axis = time_axis

            # Create PyMoDAQ data structure
            x_axis = Axis(data=time_axis, label='Time', units='s')

            mode_str = " (Mock)" if self.settings['dev', 'mock_mode'] else ""

            self.data_grabed_signal.emit([DataFromPlugins(
                name=f'PyRPL Scope{mode_str}',
                data=[voltage],
                dim='Data1D',
                axes=[x_axis]
            )])

            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Acquired {len(voltage)} points", 'log']))

        except TimeoutError as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Acquisition timeout: {e}", 'log']))

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Data acquisition failed: {e}", 'log']))

    def stop(self):
        """
        Stop data acquisition.
        
        For scope acquisition, this is a no-op since acquisitions are single-shot.
        This method is required by PyMoDAQ's viewer interface.
        """
        # Scope acquisitions are single-shot, nothing to stop
        pass


if __name__ == '__main__':
    main(__file__)
