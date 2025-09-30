# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL PID Controller (IPC Mode)

This plugin provides PyMoDAQ actuator functionality for the PyRPL PID controller
using Inter-Process Communication (IPC) to isolate PyRPL's Qt event loop from
PyMoDAQ's multi-threaded architecture.

The PID controller can be used for:
- Laser frequency locking
- Temperature stabilization
- Cavity lock loops
- Any feedback control application

Features:
- Full P/I/D parameter configuration
- Setpoint control via PyMoDAQ
- Input/output routing
- Automatic gain limits
- Mock mode support for development

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import time
import multiprocessing
from multiprocessing import Queue, Process
from queue import Empty
from typing import Optional

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun, main
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

# Import the worker function
from pymodaq_plugins_pyrpl.utils.pyrpl_ipc_worker import pyrpl_worker_main


class DAQ_Move_PyRPL_PID_IPC(DAQ_Move_base):
    """
    PyMoDAQ actuator plugin for PyRPL PID controller using IPC architecture.
    
    This plugin controls a PID feedback loop on the Red Pitaya, useful for
    locking lasers, stabilizing temperatures, or any control application.
    """
    
    _controller_units = 'V'  # PID setpoint in volts
    is_multiaxes = False  # Single PID controller per plugin instance
    
    _epsilon = 0.001  # Position precision (1 mV)
    
    # Build parameters
    params = [
        {'title': 'Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya Hostname:', 'name': 'rp_hostname', 'type': 'str',
             'value': '100.107.106.75', 'tip': 'Red Pitaya network address'},
            {'title': 'PyRPL Config Name:', 'name': 'config_name', 'type': 'str',
             'value': 'pymodaq', 'tip': 'PyRPL configuration name'},
            {'title': 'Connection Timeout (s):', 'name': 'connection_timeout', 'type': 'float',
             'value': 30.0, 'min': 5.0, 'max': 120.0,
             'tip': 'Maximum time to wait for worker startup'},
        ]},
        {'title': 'PID Controller:', 'name': 'pid', 'type': 'group', 'children': [
            {'title': 'PID Channel:', 'name': 'channel', 'type': 'list',
             'limits': ['pid0', 'pid1', 'pid2'], 'value': 'pid0',
             'tip': 'PID controller instance (Red Pitaya has 3 PIDs)'},
            {'title': 'Input Signal:', 'name': 'input', 'type': 'list',
             'limits': ['in1', 'in2', 'iq0', 'iq1', 'iq2'], 'value': 'in1',
             'tip': 'Input signal for PID error calculation'},
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2'], 'value': 'out1',
             'tip': 'Direct output routing (off or analog output)'},
            {'title': 'Proportional Gain (P):', 'name': 'p', 'type': 'float',
             'value': 0.1, 'min': -1000.0, 'max': 1000.0, 'step': 0.01,
             'tip': 'Proportional gain coefficient'},
            {'title': 'Integral Gain (I):', 'name': 'i', 'type': 'float',
             'value': 10.0, 'min': 0.0, 'max': 100000.0, 'step': 1.0,
             'tip': 'Integral gain coefficient (Hz)'},
            {'title': 'Differential Gain (D):', 'name': 'd', 'type': 'float',
             'value': 0.0, 'min': -1000.0, 'max': 1000.0, 'step': 0.01,
             'tip': 'Differential gain coefficient'},
            {'title': 'Setpoint (V):', 'name': 'setpoint', 'type': 'float',
             'value': 0.0, 'min': -1.0, 'max': 1.0, 'step': 0.001,
             'tip': 'PID setpoint in volts'},
            {'title': 'Enable PID:', 'name': 'enabled', 'type': 'bool',
             'value': False, 'tip': 'Enable/disable PID output'},
        ]},
        {'title': 'Advanced:', 'name': 'advanced', 'type': 'group', 'children': [
            {'title': 'Input Filter:', 'name': 'inputfilter', 'type': 'float',
             'value': 0.0, 'min': 0.0, 'max': 1e6, 'step': 1000.0,
             'tip': 'Input lowpass filter bandwidth (Hz, 0=off)'},
            {'title': 'Max Voltage:', 'name': 'max_voltage', 'type': 'float',
             'value': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.01,
             'tip': 'Maximum output voltage limit'},
            {'title': 'Min Voltage:', 'name': 'min_voltage', 'type': 'float',
             'value': -1.0, 'min': -1.0, 'max': 0.0, 'step': 0.01,
             'tip': 'Minimum output voltage limit'},
        ]},
        {'title': 'Development:', 'name': 'dev', 'type': 'group', 'children': [
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False,
             'tip': 'Enable mock mode for development without hardware'},
            {'title': 'Debug Logging:', 'name': 'debug_logging', 'type': 'bool', 'value': False,
             'tip': 'Enable verbose debug logging'},
        ]},
    ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)
    
    def __init__(self, parent=None, params_state=None):
        """Initialize the plugin."""
        super().__init__(parent, params_state)
        
        # IPC using multiprocessing.Queue
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None
        self.worker_process: Optional[Process] = None
        
        # Plugin state
        self.is_connected = False
        self._current_setpoint = 0.0
    
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
                daemon=True
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
        Apply parameter changes to PyRPL PID controller.
        
        Args:
            param: Parameter that was changed
        """
        if not self.is_connected:
            return
        
        try:
            # Handle PID parameter changes
            if param.parent().name() == 'pid':
                # Build full PID configuration
                pid_config = {
                    'channel': self.settings['pid', 'channel'],
                    'p': self.settings['pid', 'p'],
                    'i': self.settings['pid', 'i'],
                    'd': self.settings['pid', 'd'],
                    'setpoint': self.settings['pid', 'setpoint'],
                    'input': self.settings['pid', 'input'],
                    'output_direct': self.settings['pid', 'output_direct'],
                }
                
                # Send configuration
                self._send_command('pid_configure', pid_config)
                
                # Update cached setpoint
                self._current_setpoint = self.settings['pid', 'setpoint']
                
                if self.settings['dev', 'debug_logging']:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Updated PID {param.name()}: {param.value()}", 'log']))
            
            # Handle advanced parameters
            elif param.parent().name() == 'advanced':
                # These would need additional commands in the worker
                # For now, apply via full reconfiguration
                self.commit_settings(self.settings['pid', 'p'])
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to apply setting {param.name()}: {e}", 'log']))
    
    def ini_stage(self, controller=None):
        """
        Initialize the PID controller (start PyRPL worker process).
        
        Args:
            controller: Unused, maintained for PyMoDAQ compatibility
        
        Returns:
            Initialization status message
        """
        self.emit_status(ThreadCommand('Update_Status',
            ["Initializing PyRPL PID IPC connection...", 'log']))
        
        try:
            # Start worker process
            if not self._start_worker():
                raise RuntimeError("Failed to start PyRPL worker process")
            
            # Send initial test ping
            response = self._send_command('ping', timeout=5.0)
            if response['data'] != 'pong':
                raise RuntimeError("Worker ping test failed")
            
            # Apply initial PID configuration
            pid_config = {
                'channel': self.settings['pid', 'channel'],
                'p': self.settings['pid', 'p'],
                'i': self.settings['pid', 'i'],
                'd': self.settings['pid', 'd'],
                'setpoint': self.settings['pid', 'setpoint'],
                'input': self.settings['pid', 'input'],
                'output_direct': self.settings['pid', 'output_direct'],
            }
            self._send_command('pid_configure', pid_config)
            
            # Cache initial setpoint
            self._current_setpoint = self.settings['pid', 'setpoint']
            
            # Success
            self.emit_status(ThreadCommand('Update_Status',
                ["PyRPL PID initialization complete", 'log']))
            
            return "PyRPL PID ready"
        
        except Exception as e:
            error_msg = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            
            # Cleanup on failure
            self.close()
            
            return error_msg
    
    def close(self):
        """Close connections and clean up resources."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL PID connection...", 'log']))
        
        # Disable PID output before closing
        if self.command_queue and self.is_connected:
            try:
                self._send_command('pid_configure', {
                    'channel': self.settings['pid', 'channel'],
                    'output_direct': 'off'
                }, timeout=2.0)
            except Exception:
                pass
        
        # Send shutdown command
        if self.command_queue and self.is_connected:
            try:
                self.command_queue.put({'command': 'shutdown', 'params': {}})
                time.sleep(0.5)
            except Exception:
                pass
        
        # Terminate worker process
        if self.worker_process and self.worker_process.is_alive():
            try:
                self.worker_process.join(timeout=3.0)
                
                if self.worker_process.is_alive():
                    self.worker_process.terminate()
                    self.worker_process.join(timeout=2.0)
                
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
            ["PyRPL PID connection closed", 'log']))
    
    def move_abs(self, value):
        """
        Move to absolute setpoint position.
        
        Args:
            value: Target setpoint in volts
        """
        try:
            # Update setpoint
            self._send_command('pid_set_setpoint', {
                'channel': self.settings['pid', 'channel'],
                'value': float(value)
            })
            
            # Update cached value and GUI
            self._current_setpoint = float(value)
            self.settings.child('pid', 'setpoint').setValue(value)
            
            # Emit position reached
            self.emit_status(ThreadCommand('move_done', value))
            
            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"PID setpoint set to {value:.4f} V", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to set setpoint: {e}", 'log']))
    
    def move_rel(self, value):
        """
        Move to relative setpoint position.
        
        Args:
            value: Relative change in volts
        """
        new_setpoint = self._current_setpoint + value
        
        # Clamp to limits
        min_val = self.settings['advanced', 'min_voltage']
        max_val = self.settings['advanced', 'max_voltage']
        new_setpoint = max(min_val, min(max_val, new_setpoint))
        
        self.move_abs(new_setpoint)
    
    def move_home(self):
        """Move to home position (setpoint = 0.0 V)."""
        self.move_abs(0.0)
    
    def get_actuator_value(self):
        """
        Get current PID setpoint.
        
        Returns:
            Current setpoint in volts
        """
        try:
            response = self._send_command('pid_get_setpoint', {
                'channel': self.settings['pid', 'channel']
            })
            
            value = float(response['data'])
            self._current_setpoint = value
            
            return value
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to get setpoint: {e}", 'log']))
            return self._current_setpoint
    
    def stop_motion(self):
        """Stop PID motion (disable output)."""
        try:
            self._send_command('pid_configure', {
                'channel': self.settings['pid', 'channel'],
                'output_direct': 'off'
            })
            
            self.settings.child('pid', 'output_direct').setValue('off')
            
            self.emit_status(ThreadCommand('Update_Status',
                ["PID output disabled", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to stop PID: {e}", 'log']))


if __name__ == '__main__':
    main(__file__)
