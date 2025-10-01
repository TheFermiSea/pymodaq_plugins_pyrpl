# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL Arbitrary Signal Generator (IPC Mode)

This plugin provides PyMoDAQ actuator functionality for the PyRPL ASG
using Inter-Process Communication (IPC) to isolate PyRPL's Qt event loop from
PyMoDAQ's multi-threaded architecture.

The ASG can generate:
- Sine waves
- Triangle waves
- Square waves
- DC offsets
- Arbitrary waveforms

Features:
- Frequency control via PyMoDAQ
- Amplitude and offset control
- Waveform selection
- Output routing
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

# Import the shared worker manager (singleton pattern)
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


class DAQ_Move_PyRPL_ASG_IPC(DAQ_Move_base):
    """
    PyMoDAQ actuator plugin for PyRPL Arbitrary Signal Generator using IPC architecture.
    
    This plugin controls the signal generator on the Red Pitaya, useful for
    modulation, calibration, or stimulus generation.
    """
    
    _controller_units = 'Hz'  # Frequency control in Hertz
    is_multiaxes = False  # Single ASG per plugin instance
    
    _epsilon = 1.0  # Frequency precision (1 Hz)
    
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
        {'title': 'Signal Generator:', 'name': 'asg', 'type': 'group', 'children': [
            {'title': 'ASG Channel:', 'name': 'channel', 'type': 'list',
             'limits': ['asg0', 'asg1'], 'value': 'asg0',
             'tip': 'ASG instance (Red Pitaya has 2 ASGs)'},
            {'title': 'Waveform:', 'name': 'waveform', 'type': 'list',
             'limits': ['sin', 'square', 'triangle', 'dc'], 'value': 'sin',
             'tip': 'Output waveform type'},
            {'title': 'Frequency (Hz):', 'name': 'frequency', 'type': 'float',
             'value': 1000.0, 'min': 0.0, 'max': 62.5e6, 'step': 100.0,
             'tip': 'Output frequency (0 to 62.5 MHz)'},
            {'title': 'Amplitude (V):', 'name': 'amplitude', 'type': 'float',
             'value': 0.5, 'min': 0.0, 'max': 1.0, 'step': 0.01,
             'tip': 'Peak amplitude in volts'},
            {'title': 'Offset (V):', 'name': 'offset', 'type': 'float',
             'value': 0.0, 'min': -1.0, 'max': 1.0, 'step': 0.01,
             'tip': 'DC offset in volts'},
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2'], 'value': 'off',
             'tip': 'Direct output routing (off or analog output)'},
        ]},
        {'title': 'Advanced:', 'name': 'advanced', 'type': 'group', 'children': [
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
             'limits': ['immediately', 'ext_positive_edge', 'ext_negative_edge'], 
             'value': 'immediately',
             'tip': 'Trigger source for waveform start'},
            {'title': 'Cycles per Burst:', 'name': 'cycles_per_burst', 'type': 'int',
             'value': 0, 'min': 0, 'max': 65536,
             'tip': 'Number of cycles per trigger (0=continuous)'},
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
        
        # Shared worker manager (singleton - one worker shared by all plugins)
        self.manager = None
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None
        
        # Plugin state
        self.is_connected = False
        self._current_frequency = 1000.0
    
    def _send_command(self, command: str, params: dict = None, timeout: float = 5.0) -> dict:
        """Send a command to the PyRPL worker and wait for response."""
        if not self.command_queue or not self.response_queue:
            raise RuntimeError("Worker not initialized")
        
        self.command_queue.put({
            'command': command,
            'params': params or {}
        })
        
        if self.settings['dev', 'debug_logging']:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Sent command: {command}", 'log']))
        
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
        """Start the PyRPL worker process."""
        try:
            self.command_queue = Queue()
            self.response_queue = Queue()
            
            config = {
                'hostname': self.settings['connection', 'rp_hostname'],
                'config_name': self.settings['connection', 'config_name'],
                'mock_mode': self.settings['dev', 'mock_mode']
            }
            
            self.emit_status(ThreadCommand('Update_Status',
                ["Starting PyRPL worker process...", 'log']))
            
            self.worker_process = Process(
                target=pyrpl_worker_main,
                args=(self.command_queue, self.response_queue, config),
                daemon=True
            )
            self.worker_process.start()
            
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
        """Apply parameter changes to PyRPL ASG."""
        if not self.is_connected:
            return
        
        try:
            if param.parent().name() == 'asg':
                # Build full ASG configuration
                asg_config = {
                    'channel': self.settings['asg', 'channel'],
                    'waveform': self.settings['asg', 'waveform'],
                    'frequency': self.settings['asg', 'frequency'],
                    'amplitude': self.settings['asg', 'amplitude'],
                    'offset': self.settings['asg', 'offset'],
                    'output_direct': self.settings['asg', 'output_direct'],
                }
                
                # Send configuration
                self._send_command('asg_setup', asg_config)
                
                # Update cached frequency
                self._current_frequency = self.settings['asg', 'frequency']
                
                if self.settings['dev', 'debug_logging']:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Updated ASG {param.name()}: {param.value()}", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to apply setting {param.name()}: {e}", 'log']))
    
    def ini_stage(self, controller=None):
        """Initialize the ASG (start PyRPL worker process)."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Initializing PyRPL ASG IPC connection...", 'log']))
        
        try:
            # Start worker process
            if not self._start_worker():
                raise RuntimeError("Failed to start PyRPL worker process")
            
            # Test ping
            response = self._send_command('ping', timeout=5.0)
            if response['data'] != 'pong':
                raise RuntimeError("Worker ping test failed")
            
            # Apply initial ASG configuration
            asg_config = {
                'channel': self.settings['asg', 'channel'],
                'waveform': self.settings['asg', 'waveform'],
                'frequency': self.settings['asg', 'frequency'],
                'amplitude': self.settings['asg', 'amplitude'],
                'offset': self.settings['asg', 'offset'],
                'output_direct': self.settings['asg', 'output_direct'],
            }
            self._send_command('asg_setup', asg_config)
            
            # Cache initial frequency
            self._current_frequency = self.settings['asg', 'frequency']
            
            self.emit_status(ThreadCommand('Update_Status',
                ["PyRPL ASG initialization complete", 'log']))
            
            return "PyRPL ASG ready"
        
        except Exception as e:
            error_msg = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
            self.close()
            return error_msg
    
    def close(self):
        """
        Close plugin connection and clean up resources.
        Does NOT shutdown shared worker - other plugins may be using it.
        """
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL ASG plugin connection...", 'log']))
        
        # Optionally disable ASG output before closing
        if self.manager and self.is_connected:
            try:
                self._send_command('asg_setup', {
                    'channel': self.settings['asg', 'channel'],
                    'output_direct': 'off',
                    'amplitude': 0.0
                }, timeout=2.0)
            except Exception:
                pass
        
        # Clean up local references only
        self.command_queue = None
        self.response_queue = None
        self.manager = None
        self.is_connected = False
        
        self.emit_status(ThreadCommand('Update_Status',
            ["PyRPL ASG plugin connection closed", 'log']))
    
    def move_abs(self, value):
        """
        Move to absolute frequency.
        
        Args:
            value: Target frequency in Hz
        """
        try:
            # Update frequency via full configuration
            self._send_command('asg_setup', {
                'channel': self.settings['asg', 'channel'],
                'frequency': float(value)
            })
            
            # Update cached value and GUI
            self._current_frequency = float(value)
            self.settings.child('asg', 'frequency').setValue(value)
            
            # Emit position reached
            self.emit_status(ThreadCommand('move_done', value))
            
            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"ASG frequency set to {value:.2f} Hz", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to set frequency: {e}", 'log']))
    
    def move_rel(self, value):
        """
        Move to relative frequency.
        
        Args:
            value: Relative frequency change in Hz
        """
        new_frequency = self._current_frequency + value
        
        # Clamp to limits (0 to 62.5 MHz)
        new_frequency = max(0.0, min(62.5e6, new_frequency))
        
        self.move_abs(new_frequency)
    
    def move_home(self):
        """Move to home position (1 kHz)."""
        self.move_abs(1000.0)
    
    def get_actuator_value(self):
        """
        Get current ASG frequency.
        
        Returns:
            Current frequency in Hz
        """
        # ASG doesn't have a read-back, return cached value
        return self._current_frequency
    
    def stop_motion(self):
        """Stop ASG output (disable)."""
        try:
            self._send_command('asg_setup', {
                'channel': self.settings['asg', 'channel'],
                'output_direct': 'off'
            })
            
            self.settings.child('asg', 'output_direct').setValue('off')
            
            self.emit_status(ThreadCommand('Update_Status',
                ["ASG output disabled", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to stop ASG: {e}", 'log']))


if __name__ == '__main__':
    main(__file__)
