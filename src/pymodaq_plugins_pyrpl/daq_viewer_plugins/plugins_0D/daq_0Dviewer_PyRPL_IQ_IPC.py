# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin: PyRPL IQ Demodulator (IPC Mode)

This plugin provides PyMoDAQ 0D viewer functionality for the PyRPL IQ demodulator
using Inter-Process Communication (IPC) to isolate PyRPL's Qt event loop from
PyMoDAQ's multi-threaded architecture.

The IQ demodulator acts as a lock-in amplifier, providing:
- Quadrature demodulation (I and Q channels)
- Phase-sensitive detection
- Narrow bandwidth filtering
- High dynamic range measurements

Applications:
- Laser frequency stabilization
- Cavity lock signals
- Phase measurements
- Heterodyne detection

Features:
- I/Q quadrature outputs
- Configurable demodulation frequency
- Bandwidth control
- Input/output routing
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
from pymodaq.utils.data import DataFromPlugins
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

# Import the shared worker manager (singleton pattern)
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


class DAQ_0DViewer_PyRPL_IQ_IPC(DAQ_Viewer_base):
    """
    PyMoDAQ 0D Viewer plugin for PyRPL IQ demodulator using IPC architecture.
    
    This plugin reads the quadrature outputs (I and Q) from PyRPL's lock-in
    amplifier for phase-sensitive detection and narrow-band measurements.
    """
    
    # Plugin parameters
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
        {'title': 'IQ Demodulator:', 'name': 'iq', 'type': 'group', 'children': [
            {'title': 'IQ Channel:', 'name': 'channel', 'type': 'list',
             'limits': ['iq0', 'iq1', 'iq2'], 'value': 'iq0',
             'tip': 'IQ demodulator instance (Red Pitaya has 3 IQs)'},
            {'title': 'Input Signal:', 'name': 'input', 'type': 'list',
             'limits': ['in1', 'in2', 'pid0', 'pid1', 'pid2'], 'value': 'in1',
             'tip': 'Input signal for demodulation'},
            {'title': 'Frequency (Hz):', 'name': 'frequency', 'type': 'float',
             'value': 25e6, 'min': 0.0, 'max': 62.5e6, 'step': 1e6,
             'tip': 'Demodulation frequency (0 to 62.5 MHz)'},
            {'title': 'Bandwidth (Hz):', 'name': 'bandwidth', 'type': 'float',
             'value': 1000.0, 'min': 1.0, 'max': 1e6, 'step': 100.0,
             'tip': 'Detection bandwidth (lowpass filter cutoff)'},
            {'title': 'Quadrature Phase (°):', 'name': 'quadrature_factor', 'type': 'float',
             'value': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.1,
             'tip': 'Quadrature phase adjustment (1.0 = 90°)'},
            {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
             'limits': ['off', 'out1', 'out2'], 'value': 'off',
             'tip': 'Direct output routing (typically off for lock-in)'},
        ]},
        {'title': 'Display:', 'name': 'display', 'type': 'group', 'children': [
            {'title': 'Show Channels:', 'name': 'channels', 'type': 'list',
             'limits': ['I only', 'Q only', 'Both I and Q', 'Magnitude', 'Phase'], 
             'value': 'Both I and Q',
             'tip': 'Which channels to display'},
            {'title': 'Acquisition Rate (Hz):', 'name': 'rate', 'type': 'float',
             'value': 10.0, 'min': 0.1, 'max': 1000.0, 'step': 1.0,
             'tip': 'Data acquisition rate'},
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
        self.last_i = 0.0
        self.last_q = 0.0
    
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
        """Apply parameter changes to PyRPL IQ demodulator."""
        if not self.is_connected:
            return
        
        try:
            if param.parent().name() == 'iq':
                # Build full IQ configuration
                iq_config = {
                    'channel': self.settings['iq', 'channel'],
                    'frequency': self.settings['iq', 'frequency'],
                    'bandwidth': self.settings['iq', 'bandwidth'],
                    'input': self.settings['iq', 'input'],
                    'output_direct': self.settings['iq', 'output_direct'],
                }
                
                # Send configuration
                self._send_command('iq_setup', iq_config)
                
                if self.settings['dev', 'debug_logging']:
                    self.emit_status(ThreadCommand('Update_Status',
                        [f"Updated IQ {param.name()}: {param.value()}", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Failed to apply setting {param.name()}: {e}", 'log']))
    
    def ini_detector(self, controller=None):
        """Initialize the detector (start PyRPL worker process)."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Initializing PyRPL IQ IPC connection...", 'log']))
        
        try:
            # Start worker process
            if not self._start_worker():
                raise RuntimeError("Failed to start PyRPL worker process")
            
            # Test ping
            response = self._send_command('ping', timeout=5.0)
            if response['data'] != 'pong':
                raise RuntimeError("Worker ping test failed")
            
            # Apply initial IQ configuration
            iq_config = {
                'channel': self.settings['iq', 'channel'],
                'frequency': self.settings['iq', 'frequency'],
                'bandwidth': self.settings['iq', 'bandwidth'],
                'input': self.settings['iq', 'input'],
                'output_direct': self.settings['iq', 'output_direct'],
            }
            self._send_command('iq_setup', iq_config)
            
            # Success
            self.status.initialized = True
            self.status.info = "PyRPL IQ ready"
            self.emit_status(ThreadCommand('Update_Status',
                ["PyRPL IQ initialization complete", 'log']))
        
        except Exception as e:
            self.status.initialized = False
            self.status.info = f"Initialization failed: {e}"
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))
            self.close()
        
        return self.status
    
    def close(self):
        """Close connections and clean up resources."""
        self.emit_status(ThreadCommand('Update_Status',
            ["Closing PyRPL IQ connection...", 'log']))
        
        # Disable IQ output before closing
        if self.command_queue and self.is_connected:
            try:
                self._send_command('iq_setup', {
                    'channel': self.settings['iq', 'channel'],
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
            ["PyRPL IQ connection closed", 'log']))
    
    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquire IQ quadrature values.
        
        Args:
            **kwargs: Additional parameters
        """
        try:
            # Get quadrature values from IQ demodulator
            response = self._send_command('iq_get_quadratures', {
                'channel': self.settings['iq', 'channel']
            })
            
            data = response['data']
            i_value = data['i']
            q_value = data['q']
            
            # Cache values
            self.last_i = i_value
            self.last_q = q_value
            
            # Determine what to display
            channel_mode = self.settings['display', 'channels']
            
            mode_str = " (Mock)" if self.settings['dev', 'mock_mode'] else ""
            
            if channel_mode == 'I only':
                self.data_grabed_signal.emit([DataFromPlugins(
                    name=f'IQ I-channel{mode_str}',
                    data=[np.array([i_value])],
                    dim='Data0D'
                )])
            
            elif channel_mode == 'Q only':
                self.data_grabed_signal.emit([DataFromPlugins(
                    name=f'IQ Q-channel{mode_str}',
                    data=[np.array([q_value])],
                    dim='Data0D'
                )])
            
            elif channel_mode == 'Both I and Q':
                self.data_grabed_signal.emit([
                    DataFromPlugins(
                        name=f'IQ I-channel{mode_str}',
                        data=[np.array([i_value])],
                        dim='Data0D'
                    ),
                    DataFromPlugins(
                        name=f'IQ Q-channel{mode_str}',
                        data=[np.array([q_value])],
                        dim='Data0D'
                    )
                ])
            
            elif channel_mode == 'Magnitude':
                magnitude = np.sqrt(i_value**2 + q_value**2)
                self.data_grabed_signal.emit([DataFromPlugins(
                    name=f'IQ Magnitude{mode_str}',
                    data=[np.array([magnitude])],
                    dim='Data0D'
                )])
            
            elif channel_mode == 'Phase':
                phase = np.arctan2(q_value, i_value) * 180.0 / np.pi  # degrees
                self.data_grabed_signal.emit([DataFromPlugins(
                    name=f'IQ Phase{mode_str}',
                    data=[np.array([phase])],
                    dim='Data0D'
                )])
            
            if self.settings['dev', 'debug_logging']:
                self.emit_status(ThreadCommand('Update_Status',
                    [f"IQ: I={i_value:.6f}, Q={q_value:.6f}", 'log']))
        
        except TimeoutError as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Acquisition timeout: {e}", 'log']))
        
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                [f"Data acquisition failed: {e}", 'log']))

    def stop(self):
        """
        Stop data acquisition.
        
        For IQ measurements, this is a no-op since acquisitions are single-shot.
        This method is required by PyMoDAQ's viewer interface.
        """
        # IQ acquisitions are single-shot, nothing to stop
        pass


if __name__ == '__main__':
    main(__file__)
