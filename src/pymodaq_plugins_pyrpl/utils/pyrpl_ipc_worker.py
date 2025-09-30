#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyRPL IPC Worker Process

This module runs in a separate process and manages the PyRPL instance.
It receives commands via multiprocessing.Queue and returns results.

The worker runs PyRPL with gui=False in its own process with its own Qt event loop,
completely isolated from PyMoDAQ's threading architecture.

Architecture:
- Separate process with dedicated Python interpreter
- Own Qt event loop for PyRPL's QObject-based modules
- Command/response queue-based communication
- Graceful error handling and shutdown

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import sys
import time
import traceback
import logging
import os
from typing import Optional, Dict, Any
from multiprocessing import Queue

import numpy as np

# Set environment variables to help SSH stability
os.environ['PARAMIKO_LOG_LEVEL'] = 'WARNING'  # Reduce noise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[PyRPL Worker] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def pyrpl_worker_main(command_queue: Queue, response_queue: Queue, config: Dict[str, Any]):
    """
    Main entry point for the PyRPL worker process.

    This function:
    1. Initializes PyRPL with gui=False in its own process
    2. Enters command processing loop
    3. Handles commands from PyMoDAQ plugin
    4. Returns results via response queue
    5. Cleanly shuts down on 'shutdown' command

    Args:
        command_queue: Queue to receive commands from plugin
        response_queue: Queue to send responses back to plugin
        config: Configuration dictionary with keys:
            - 'hostname': Red Pitaya hostname/IP
            - 'config_name': PyRPL configuration name
            - 'port': Red Pitaya port (default 2222)
            - 'mock_mode': Enable mock mode (default False)
    """
    pyrpl_instance = None
    
    try:
        logger.info("PyRPL worker process starting...")
        
        # Extract configuration
        hostname = config.get('hostname', '100.107.106.75')
        config_name = config.get('config_name', 'pymodaq')
        port = config.get('port', 2222)
        mock_mode = config.get('mock_mode', False)
        
        if mock_mode:
            logger.info("Mock mode enabled - skipping PyRPL initialization")
            init_response = {
                'status': 'ok',
                'data': 'Mock mode initialized'
            }
            response_queue.put(init_response)
        else:
            # Initialize PyRPL in this process
            # CRITICAL: gui=False prevents Qt GUI widget creation
            # PyRPL still uses QObjects internally, but they live in THIS process's Qt event loop
            logger.info(f"Initializing PyRPL: hostname={hostname}, config={config_name}")
            
            import pyrpl
            
            # Retry logic for network instability
            max_retries = 3
            retry_delay = 2.0
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.warning(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                        time.sleep(retry_delay)
                    
                    # Create minimal config to avoid Network Analyzer bug
                    import yaml
                    config_path = os.path.expanduser(f'~/pyrpl_user_dir/config/{config_name}.yml')
                    
                    # If config doesn't exist or is corrupted, create minimal one
                    if not os.path.exists(config_path) or os.path.getsize(config_path) < 100:
                        logger.info(f"Creating minimal config at {config_path}")
                        os.makedirs(os.path.dirname(config_path), exist_ok=True)
                        minimal_config = {
                            'pyrpl': {
                                'name': config_name,
                                'modules': [],  # Don't load problematic modules
                                'loglevel': 'info',
                                'background_color': ''
                            },
                            'redpitaya': {
                                'hostname': hostname,
                                'port': port,
                                'user': 'root',
                                'password': 'root',
                                'gui': False,
                                'autostart': True,
                                'reloadfpga': False,  # Skip FPGA reload - use existing bitstream
                                'reloadserver': False  # Skip server reload
                            }
                        }
                        with open(config_path, 'w') as f:
                            yaml.dump(minimal_config, f)
                    
                    pyrpl_instance = pyrpl.Pyrpl(
                        hostname=hostname,
                        config=config_name,
                        gui=False,  # CRITICAL: No GUI widgets
                        source=None  # Let PyRPL use default bitstream
                    )
                    
                    # Test that we can access a basic module
                    _ = pyrpl_instance.rp.scope
                    
                    logger.info("PyRPL initialized successfully")
                    response_queue.put({
                        'status': 'ok',
                        'data': 'PyRPL initialized'
                    })
                    break  # Success!
                    
                except (OSError, IOError, TimeoutError) as e:
                    last_error = e
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    
                    # Clean up any partial connection
                    try:
                        if 'pyrpl_instance' in locals():
                            pyrpl_instance.close()
                    except Exception:
                        pass
                    
                    if attempt == max_retries - 1:
                        # Final attempt failed
                        raise last_error
            
            if pyrpl_instance is None:
                raise RuntimeError("Failed to initialize PyRPL after retries")
        
    except Exception as e:
        error_msg = f"PyRPL initialization failed: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        response_queue.put({
            'status': 'error',
            'data': error_msg
        })
        return  # Exit if initialization fails
    
    # Command processing loop
    logger.info("Entering command processing loop...")
    
    while True:
        try:
            # Block until command received
            command_request = command_queue.get()
            command = command_request.get('command')
            params = command_request.get('params', {})
            cmd_id = command_request.get('id')  # May be None for backward compat
            
            logger.debug(f"Received command: {command}")
            
            # Handle shutdown command
            if command == 'shutdown':
                logger.info("Shutdown command received")
                shutdown_response = {'status': 'ok', 'data': 'Shutting down'}
                if cmd_id:
                    shutdown_response['id'] = cmd_id
                response_queue.put(shutdown_response)
                break
            
            # Handle ping command
            if command == 'ping':
                ping_response = {'status': 'ok', 'data': 'pong'}
                if cmd_id:
                    ping_response['id'] = cmd_id
                response_queue.put(ping_response)
                continue
            
            # Mock mode responses
            if mock_mode:
                response = _handle_mock_command(command, params)
                if cmd_id:
                    response['id'] = cmd_id
                response_queue.put(response)
                continue
            
            # Real hardware commands
            if pyrpl_instance is None:
                error_response = {
                    'status': 'error',
                    'data': 'PyRPL not initialized'
                }
                if cmd_id:
                    error_response['id'] = cmd_id
                response_queue.put(error_response)
                continue
            
            # Route command to appropriate handler
            try:
                response = _handle_pyrpl_command(pyrpl_instance, command, params)
                if cmd_id:
                    response['id'] = cmd_id
                response_queue.put(response)
                
            except Exception as e:
                error_msg = f"Command execution error: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                error_response = {
                    'status': 'error',
                    'data': error_msg
                }
                if cmd_id:
                    error_response['id'] = cmd_id
                response_queue.put(error_response)
        
        except KeyboardInterrupt:
            logger.info("Worker interrupted by keyboard")
            break
        
        except Exception as e:
            error_msg = f"Unexpected error in command loop: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            # Try to send error response
            try:
                error_response = {
                    'status': 'error',
                    'data': error_msg
                }
                if 'cmd_id' in locals() and cmd_id:
                    error_response['id'] = cmd_id
                response_queue.put(error_response)
            except Exception:
                pass  # Queue might be broken
    
    # Cleanup
    logger.info("Cleaning up PyRPL worker...")
    
    if pyrpl_instance is not None:
        try:
            # Cleanly close PyRPL connection
            logger.info("Closing PyRPL connection...")
            pyrpl_instance.close()
        except Exception as e:
            logger.error(f"Error closing PyRPL: {e}")
    
    # Send final shutdown confirmation
    try:
        response_queue.put({
            'status': 'ok',
            'data': 'PyRPL worker shutdown complete'
        })
    except Exception:
        pass
    
    logger.info("PyRPL worker process exiting")


def _handle_pyrpl_command(pyrpl: Any, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle commands for real PyRPL hardware.

    Args:
        pyrpl: PyRPL instance
        command: Command name
        params: Command parameters

    Returns:
        Response dictionary with 'status' and 'data' keys
    """
    # Scope commands
    if command == 'scope_acquire':
        # Trigger oscilloscope acquisition
        decimation = params.get('decimation', 64)
        trigger_source = params.get('trigger_source', 'immediately')
        input_channel = params.get('input_channel', 'in1')
        
        # Configure scope
        pyrpl.rp.scope.decimation = decimation
        pyrpl.rp.scope.trigger_source = trigger_source
        pyrpl.rp.scope.input1 = input_channel
        
        # PyRPL scope acquisition:
        # The scope continuously fills its buffer. We just need to read the data.
        # For trigger_source='immediately', data is always available.
        timeout_val = params.get('timeout', 5.0)
        start_time = time.time()
        
        try:
            # For 'immediately' trigger, data should be ready instantly
            # For other triggers, we'd need to wait for curve_ready()
            if trigger_source == 'immediately':
                # Data is continuously acquired, just read it
                time.sleep(0.01)  # Small delay to ensure buffer is filled
            else:
                # Wait for trigger event and data acquisition
                while not pyrpl.rp.scope.curve_ready():
                    if time.time() - start_time > timeout_val:
                        return {
                            'status': 'error',
                            'data': f'Scope acquisition timeout ({timeout_val}s) waiting for trigger'
                        }
                    time.sleep(0.001)
            
            # Read the data directly from scope properties
            ch1_data = pyrpl.rp.scope._data_ch1
            ch2_data = pyrpl.rp.scope._data_ch2
            
            # Use the correct channel based on input_channel setting
            if input_channel == 'in1':
                voltage_data = ch1_data
            else:
                voltage_data = ch2_data
            
            # Log signal statistics for debugging
            logger.info(f"Acquired {len(voltage_data)} points, "
                       f"Vmin={voltage_data.min():.6f}, "
                       f"Vmax={voltage_data.max():.6f}, "
                       f"Vpp={voltage_data.max()-voltage_data.min():.6f}")
                
        except Exception as e:
            return {
                'status': 'error',
                'data': f'Scope acquisition failed: {str(e)}'
            }
        
        # Get timing information
        duration = pyrpl.rp.scope.duration
        data_length = len(voltage_data)
        time_data = np.linspace(0, duration, data_length)
        
        return {
            'status': 'ok',
            'data': {
                'voltage': voltage_data.tolist() if isinstance(voltage_data, np.ndarray) else voltage_data,
                'time': time_data.tolist() if isinstance(time_data, np.ndarray) else time_data
            }
        }
    
    elif command == 'scope_set_decimation':
        pyrpl.rp.scope.decimation = params.get('value')
        return {'status': 'ok', 'data': None}
    
    elif command == 'scope_set_trigger':
        pyrpl.rp.scope.trigger_source = params.get('source')
        return {'status': 'ok', 'data': None}
    
    # PID commands
    elif command == 'pid_set_setpoint':
        pid_channel = params.get('channel', 'pid0')
        value = params.get('value')
        pid = getattr(pyrpl.rp, pid_channel)
        pid.setpoint = value
        return {'status': 'ok', 'data': None}
    
    elif command == 'pid_get_setpoint':
        pid_channel = params.get('channel', 'pid0')
        pid = getattr(pyrpl.rp, pid_channel)
        return {'status': 'ok', 'data': pid.setpoint}
    
    elif command == 'pid_configure':
        pid_channel = params.get('channel', 'pid0')
        pid = getattr(pyrpl.rp, pid_channel)
        
        # Apply configuration
        if 'p' in params:
            pid.p = params['p']
        if 'i' in params:
            pid.i = params['i']
        if 'd' in params:
            pid.d = params['d']
        if 'setpoint' in params:
            pid.setpoint = params['setpoint']
        if 'input' in params:
            pid.input = params['input']
        if 'output_direct' in params:
            pid.output_direct = params['output_direct']
        
        return {'status': 'ok', 'data': None}
    
    # ASG commands
    elif command == 'asg_setup':
        asg_channel = params.get('channel', 'asg0')
        asg = getattr(pyrpl.rp, asg_channel)
        
        # Configure ASG
        if 'waveform' in params:
            asg.waveform = params['waveform']
        if 'frequency' in params:
            asg.frequency = params['frequency']
        if 'amplitude' in params:
            asg.amplitude = params['amplitude']
        if 'offset' in params:
            asg.offset = params['offset']
        if 'output_direct' in params:
            asg.output_direct = params['output_direct']
        
        return {'status': 'ok', 'data': None}
    
    # IQ commands
    elif command == 'iq_setup':
        iq_channel = params.get('channel', 'iq0')
        iq = getattr(pyrpl.rp, iq_channel)
        
        # Configure IQ
        if 'frequency' in params:
            iq.frequency = params['frequency']
        if 'bandwidth' in params:
            iq.bandwidth = params['bandwidth']
        if 'input' in params:
            iq.input = params['input']
        if 'output_direct' in params:
            iq.output_direct = params['output_direct']
        
        return {'status': 'ok', 'data': None}
    
    elif command == 'iq_get_quadratures':
        iq_channel = params.get('channel', 'iq0')
        iq = getattr(pyrpl.rp, iq_channel)
        
        return {
            'status': 'ok',
            'data': {
                'i': float(iq.quadrature_i),
                'q': float(iq.quadrature_q)
            }
        }
    
    # Sampler commands (voltage monitoring)
    elif command == 'sampler_read':
        channel = params.get('channel', 'in1')
        value = getattr(pyrpl.rp.sampler, channel)
        return {'status': 'ok', 'data': float(value)}
    
    else:
        return {
            'status': 'error',
            'data': f'Unknown command: {command}'
        }


def _handle_mock_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle commands in mock mode (for development without hardware).

    Args:
        command: Command name
        params: Command parameters

    Returns:
        Response dictionary with 'status' and 'data' keys
    """
    if command == 'scope_acquire':
        # Generate mock oscilloscope data
        n_points = 16384  # PyRPL scope default
        decimation = params.get('decimation', 64)
        
        # Calculate time axis
        sampling_rate = 125e6 / decimation  # Hz
        duration = n_points / sampling_rate  # seconds
        time_data = np.linspace(0, duration, n_points)
        
        # Generate mock signal: sine wave + noise
        frequency = 1e3  # 1 kHz signal
        voltage_data = (
            0.5 * np.sin(2 * np.pi * frequency * time_data) +
            0.05 * np.random.randn(n_points)
        )
        
        return {
            'status': 'ok',
            'data': {
                'voltage': voltage_data.tolist(),
                'time': time_data.tolist()
            }
        }
    
    elif command in ['scope_set_decimation', 'scope_set_trigger',
                      'pid_set_setpoint', 'pid_configure', 'asg_setup', 'iq_setup']:
        # Configuration commands - just acknowledge
        return {'status': 'ok', 'data': None}
    
    elif command == 'pid_get_setpoint':
        # Return mock setpoint
        return {'status': 'ok', 'data': 0.0}
    
    elif command == 'iq_get_quadratures':
        # Return mock IQ values
        return {
            'status': 'ok',
            'data': {'i': 0.1, 'q': 0.05}
        }
    
    elif command == 'sampler_read':
        # Return mock voltage
        return {'status': 'ok', 'data': 0.0 + 0.01 * np.random.randn()}
    
    else:
        return {
            'status': 'error',
            'data': f'Unknown mock command: {command}'
        }


if __name__ == '__main__':
    # This allows testing the worker directly
    import multiprocessing
    
    print("Starting PyRPL worker in test mode...")
    
    cmd_queue = multipro
