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

# Import the worker function
from pymodaq_plugins_pyrpl.utils.pyrpl_ipc_worker import pyrpl_worker_main


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

        # IPC using multiprocessing.Queue
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None
        self.worker_process: Optional[Process] = None

        # Plugin state
        self.is_connected = False

        # Data caching
        self.last_data = None
        self.last_time_axis = None

    def _send_command(self, command: str, params: dict = None, timeout: float = 5.0) -> dict:
        """
        Send a command to the PyRPL worker and wait for response.

        Args:
            command: Command name
            params: Command parameters (optional)
            timeout: Response timeout in seconds

        Returns:
            Response dictionary from worker

        Raises:
            RuntimeError: If worker returns error
            TimeoutError: If no response within timeout
        """
        if not self.command_queue or not self.response_queue:
            raise RuntimeError("Worker not initialized")

        # Send command
        self.command_queue.put({
            'command': command,
            'params': params or {}
        })

        if self.settings['dev', 'debug_logging']:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Sent command: {command}", 'log']))

        # Wait for response
        try:
            response = self.response_queue.get(timeout=timeout)

            if response['status'] == 'error':
                error_msg = f"PyRPL worker error: {response['data']}"
                self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                raise RuntimeError(error_msg)

            return response

        except Empty:
            raise TimeoutError(f"No response from worker after {timeout}s")

    def _start_worker(self) -> bool:
        """
        Start the PyRPL worker process.

        Returns:
            True if worker started successfully
        """
        try:
            # Create fresh queues
            self.command_queue = Queue()
            self.response_queue = Queue()

            # Build configuration
            config = {
                'hostname': self.settings['connection', 'rp_hostname'],
                'config_name': self.settings['connection', 'config_name'],
                'mock_mode': self.settings['dev', 'mock_mode']
            }

            self.emit_status(ThreadCommand('Update_Status',
                ["Starting PyRPL worker process...", 'log']))

            # Start worker process
            self.worker_process = Process(
                target=pyrpl_worker_main,
                args=(self.command_queue, self.response_queue, config),
                daemon=True  # Ensure it terminates with main process
            )
            self.worker_process.start()

            # Wait for initialization confirmation
            timeout = self.settings['connection', 'connection_timeout']
            
            try:
                response = self.response_queue.get(timeout=timeout)
                
                if response['status'] == 'ok':
                    self.is_connected = True
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"PyRPL worker initialized: {response['data']}", 'log']))
                    return True
                else:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Worker initialization failed: {response['data']}", 'log']))
                    return False

            except Empty:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Worker did not respond within {timeout}s", 'log']))
                return False

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to start worker: {e}", 'log']))
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
        """Close connections and clean up resources."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL connection...", 'log']))

        # Send shutdown command
        if self.command_queue and self.is_connected:
            try:
                self.command_queue.put({'command': 'shutdown', 'params': {}})
                time.sleep(0.5)  # Give worker time to cleanup
            except Exception:
                pass

        # Terminate worker process
        if self.worker_process and self.worker_process.is_alive():
            try:
                # Try graceful termination first
                self.worker_process.join(timeout=3.0)
                
                # Force terminate if still alive
                if self.worker_process.is_alive():
                    self.worker_process.terminate()
                    self.worker_process.join(timeout=2.0)
                
                # Last resort: kill
                if self.worker_process.is_alive():
                    self.worker_process.kill()
                    self.worker_process.join()

            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"Warning: Error terminating worker: {e}", 'log']))

        # Cleanup resources
        self.worker_process = None
        self.command_queue = None
        self.response_queue = None
        self.is_connected = False

        self.emit_status(ThreadCommand('Update_Status',
            ["PyRPL connection closed", 'log']))

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
