#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyRPL TCP Server for PyMoDAQ Integration

This server exposes PyRPL hardware modules to PyMoDAQ clients using PyMoDAQ's
standard TCP/IP protocol.

Architecture:
- PyMoDAQ (master) controls PyRPL (slave)
- Server manages ONE PyRPL instance shared by all clients
- Uses PyMoDAQ's TCPServer infrastructure
- Respects PyRPL's module ownership system

Usage:
    python pyrpl_tcp_server.py --hostname 100.107.106.75 --config pymodaq
    python pyrpl_tcp_server.py --mock  # Development mode

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import sys
import argparse
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

from qtpy import QtWidgets, QtCore
from pymodaq.utils.tcp_ip.tcp_server_client import TCPServer
from pymodaq_data.data import DataToExport, DataRaw, Axis
import numpy as np

# PyRPL imports
try:
    from pyrpl import Pyrpl
    PYRPL_AVAILABLE = True
except ImportError:
    PYRPL_AVAILABLE = False
    print("WARNING: PyRPL not available. Server will run in mock mode only.")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockPyRPL:
    """Mock PyRPL for development without hardware."""
    
    class MockModule:
        """Mock PyRPL hardware module."""
        
        def __init__(self, name):
            self.name = name
            self._attrs = {}
            
        def __setattr__(self, key, value):
            if key.startswith('_') or key == 'name':
                super().__setattr__(key, value)
            else:
                self._attrs[key] = value
                logger.debug(f"Mock {self.name}.{key} = {value}")
        
        def __getattr__(self, key):
            return self._attrs.get(key, None)
        
        def setup(self, **kwargs):
            """Mock setup method."""
            for key, value in kwargs.items():
                setattr(self, key, value)
            logger.info(f"Mock {self.name}.setup(**{kwargs})")
        
        def curve(self):
            """Mock scope curve acquisition."""
            logger.info(f"Mock {self.name}.curve()")
            t = np.linspace(0, 0.001, 2**14)  # 1ms, 16k samples
            return np.sin(2 * np.pi * 1000 * t)  # 1 kHz sine
        
        def iq(self):
            """Mock IQ demodulation."""
            logger.info(f"Mock {self.name}.iq()")
            return 0.5 + 0.1j
    
    class MockRP:
        """Mock Red Pitaya object."""
        
        def __init__(self):
            self.scope = MockPyRPL.MockModule('scope')
            self.iq0 = MockPyRPL.MockModule('iq0')
            self.iq1 = MockPyRPL.MockModule('iq1')
            self.iq2 = MockPyRPL.MockModule('iq2')
            self.asg0 = MockPyRPL.MockModule('asg0')
            self.asg1 = MockPyRPL.MockModule('asg1')
            self.pid0 = MockPyRPL.MockModule('pid0')
            self.pid1 = MockPyRPL.MockModule('pid1')
            self.pid2 = MockPyRPL.MockModule('pid2')
    
    def __init__(self, *args, **kwargs):
        logger.info(f"MockPyRPL initialized (config={kwargs.get('config')}, hostname={kwargs.get('hostname')})")
        self.rp = self.MockRP()
    
    def close(self):
        """Mock close method."""
        logger.info("MockPyRPL closed")


class PyMoDAQPyRPLServer(TCPServer):
    """
    TCP Server that exposes PyRPL modules to PyMoDAQ clients.
    
    Inherits from PyMoDAQ's TCPServer to leverage existing infrastructure:
    - Message serialization/deserialization
    - Client connection management
    - Command routing
    
    Manages ONE PyRPL instance shared by all clients, using PyRPL's
    module ownership system to prevent resource conflicts.
    """
    
    def __init__(self, hostname: str, config_name: str, port: int = 6341, mock_mode: bool = False):
        """
        Initialize the PyRPL TCP server.
        
        Args:
            hostname: Red Pitaya IP address (e.g., '100.107.106.75')
            config_name: PyRPL configuration name (e.g., 'pymodaq')
            port: TCP server port (default: 6341)
            mock_mode: Run in mock mode without real hardware
        """
        super().__init__(port=port)
        
        self.hostname = hostname
        self.config_name = config_name
        self.mock_mode = mock_mode
        self.pyrpl: Optional[Pyrpl] = None
        
        # Track client module ownership
        # Format: {client_id: {'scope': scope_instance, ...}}
        self.client_modules: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"PyMoDAQPyRPLServer initializing (mock={mock_mode})")
        
        # Initialize PyRPL
        self._init_pyrpl()
    
    def _init_pyrpl(self):
        """Initialize PyRPL instance (ONCE for entire server)."""
        try:
            if self.mock_mode or not PYRPL_AVAILABLE:
                logger.info("Initializing MockPyRPL...")
                self.pyrpl = MockPyRPL(config=self.config_name, hostname=self.hostname)
            else:
                logger.info(f"Initializing PyRPL (hostname={self.hostname}, config={self.config_name})...")
                self.pyrpl = Pyrpl(config=self.config_name, hostname=self.hostname)
            
            logger.info("✓ PyRPL initialized successfully")
            logger.info(f"  Available modules: scope, iq0-2, asg0-1, pid0-2")
            
        except Exception as e:
            logger.error(f"Failed to initialize PyRPL: {e}")
            logger.info("Falling back to mock mode...")
            self.mock_mode = True
            self.pyrpl = MockPyRPL(config=self.config_name, hostname=self.hostname)
    
    def _get_module(self, module_name: str):
        """
        Get PyRPL module by name.
        
        Args:
            module_name: Module name (e.g., 'scope', 'iq0', 'asg1', 'pid0')
        
        Returns:
            PyRPL module instance
        
        Raises:
            ValueError: If module name is invalid
        """
        if not hasattr(self.pyrpl.rp, module_name):
            raise ValueError(f"Invalid module name: {module_name}")
        
        return getattr(self.pyrpl.rp, module_name)
    
    def command_to_from_client(self, client_socket, data: dict):
        """
        Process commands from PyMoDAQ clients.
        
        This method is called by TCPServer when a client sends a command.
        It routes the command to the appropriate PyRPL module and returns
        the result using PyMoDAQ's standard protocol.
        
        Args:
            client_socket: Socket connection to client
            data: Command data dictionary with keys:
                - 'command': Command name (e.g., 'grab', 'move_abs')
                - 'module': PyRPL module name (e.g., 'scope', 'asg0')
                - Additional command-specific parameters
        """
        try:
            command = data.get('command', '')
            module_name = data.get('module', '')
            
            logger.info(f"Command received: {command} on {module_name}")
            logger.debug(f"  Data: {data}")
            
            # Route command to appropriate handler
            if command == 'ping':
                self._handle_ping(client_socket)
            
            elif command == 'grab':
                self._handle_grab(client_socket, module_name, data)
            
            elif command == 'move_abs':
                self._handle_move_abs(client_socket, module_name, data)
            
            elif command == 'move_rel':
                self._handle_move_rel(client_socket, module_name, data)
            
            elif command == 'move_home':
                self._handle_move_home(client_socket, module_name, data)
            
            elif command == 'stop_motion':
                self._handle_stop_motion(client_socket, module_name, data)
            
            elif command == 'check_position':
                self._handle_check_position(client_socket, module_name, data)
            
            elif command == 'configure':
                self._handle_configure(client_socket, module_name, data)
            
            else:
                logger.warning(f"Unknown command: {command}")
                self._send_error(client_socket, f"Unknown command: {command}")
        
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            self._send_error(client_socket, str(e))
    
    def _handle_ping(self, client_socket):
        """Handle ping command."""
        logger.debug("Ping received, responding with pong")
        self.socket.check_sended_with_serializer('pong')
    
    def _handle_grab(self, client_socket, module_name: str, data: dict):
        """
        Handle data acquisition command (GRABBER clients: Scope, IQ).
        
        Args:
            client_socket: Client socket
            module_name: Module to acquire from ('scope', 'iq0', etc.)
            data: Acquisition parameters
        """
        try:
            module = self._get_module(module_name)
            
            # Configure module with provided parameters
            config = data.get('config', {})
            if config:
                module.setup(**config)
            
            # Acquire data based on module type
            if module_name == 'scope':
                # Scope: acquire curve
                curve_data = module.curve()
                
                # Create DataToExport
                timebase = data.get('timebase', 0.001)  # 1ms default
                n_points = len(curve_data)
                time_axis = Axis(
                    data=np.linspace(0, timebase, n_points),
                    label='Time',
                    units='s'
                )
                
                dte = DataToExport(
                    name='PyRPL_Scope',
                    data=[DataRaw(
                        'Ch1',
                        data=[curve_data],
                        axes=[time_axis]
                    )]
                )
            
            elif module_name.startswith('iq'):
                # IQ: single complex value
                iq_value = module.iq()
                
                # Create DataToExport with I and Q components
                dte = DataToExport(
                    name=f'PyRPL_{module_name.upper()}',
                    data=[
                        DataRaw('I', data=[np.array([iq_value.real])]),
                        DataRaw('Q', data=[np.array([iq_value.imag])])
                    ]
                )
            
            else:
                raise ValueError(f"Module {module_name} does not support grab command")
            
            # Send response
            logger.info(f"Sending acquired data from {module_name}")
            self.socket.check_sended_with_serializer('Done')
            self.socket.check_sended_with_serializer(dte)
        
        except Exception as e:
            logger.error(f"Grab error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _handle_move_abs(self, client_socket, module_name: str, data: dict):
        """
        Handle absolute move command (ACTUATOR clients: ASG, PID).
        
        Args:
            client_socket: Client socket
            module_name: Module to move ('asg0', 'pid0', etc.)
            data: Move parameters including 'value'
        """
        try:
            module = self._get_module(module_name)
            value = data.get('value', 0.0)
            
            # Set value based on module type
            if module_name.startswith('asg'):
                # ASG: set offset voltage
                module.offset = float(value)
                logger.info(f"{module_name}.offset = {value}")
            
            elif module_name.startswith('pid'):
                # PID: set setpoint
                module.setpoint = float(value)
                logger.info(f"{module_name}.setpoint = {value}")
            
            else:
                raise ValueError(f"Module {module_name} does not support move commands")
            
            # Send move_done response
            self.socket.check_sended_with_serializer('move_done')
            self.socket.check_sended_with_serializer(value)
        
        except Exception as e:
            logger.error(f"Move abs error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _handle_move_rel(self, client_socket, module_name: str, data: dict):
        """Handle relative move command."""
        try:
            module = self._get_module(module_name)
            delta = data.get('value', 0.0)
            
            # Get current value
            if module_name.startswith('asg'):
                current = module.offset or 0.0
                module.offset = current + delta
                new_value = module.offset
            elif module_name.startswith('pid'):
                current = module.setpoint or 0.0
                module.setpoint = current + delta
                new_value = module.setpoint
            else:
                raise ValueError(f"Module {module_name} does not support move commands")
            
            logger.info(f"{module_name} moved by {delta} to {new_value}")
            
            # Send move_done response
            self.socket.check_sended_with_serializer('move_done')
            self.socket.check_sended_with_serializer(new_value)
        
        except Exception as e:
            logger.error(f"Move rel error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _handle_move_home(self, client_socket, module_name: str, data: dict):
        """Handle move to home position (0.0)."""
        data['value'] = 0.0
        self._handle_move_abs(client_socket, module_name, data)
    
    def _handle_stop_motion(self, client_socket, module_name: str, data: dict):
        """Handle stop motion command."""
        try:
            module = self._get_module(module_name)
            
            # Disable output
            if module_name.startswith('asg'):
                module.output_direct = 'off'
            elif module_name.startswith('pid'):
                module.output_direct = 'off'
            
            logger.info(f"{module_name} motion stopped")
            
            # Send acknowledgment
            self.socket.check_sended_with_serializer('Done')
        
        except Exception as e:
            logger.error(f"Stop motion error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _handle_check_position(self, client_socket, module_name: str, data: dict):
        """Handle position check command."""
        try:
            module = self._get_module(module_name)
            
            # Get current position
            if module_name.startswith('asg'):
                position = module.offset or 0.0
            elif module_name.startswith('pid'):
                position = module.setpoint or 0.0
            else:
                raise ValueError(f"Module {module_name} does not support position check")
            
            # Send position response
            self.socket.check_sended_with_serializer('position_is')
            self.socket.check_sended_with_serializer(position)
        
        except Exception as e:
            logger.error(f"Check position error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _handle_configure(self, client_socket, module_name: str, data: dict):
        """Handle module configuration command."""
        try:
            module = self._get_module(module_name)
            config = data.get('config', {})
            
            # Apply configuration using PyRPL's setup method
            module.setup(**config)
            
            logger.info(f"{module_name} configured with {config}")
            
            # Send acknowledgment
            self.socket.check_sended_with_serializer('Done')
        
        except Exception as e:
            logger.error(f"Configure error on {module_name}: {e}")
            self._send_error(client_socket, str(e))
    
    def _send_error(self, client_socket, error_msg: str):
        """Send error message to client."""
        logger.error(f"Sending error to client: {error_msg}")
        self.socket.check_sended_with_serializer('Error')
        self.socket.check_sended_with_serializer(error_msg)
    
    def close_server(self):
        """Close server and cleanup PyRPL."""
        logger.info("Closing PyRPL TCP server...")
        
        if self.pyrpl:
            try:
                self.pyrpl.close()
                logger.info("✓ PyRPL closed")
            except Exception as e:
                logger.error(f"Error closing PyRPL: {e}")
        
        super().close_server()
        logger.info("✓ Server closed")


def main():
    """Main entry point for PyRPL TCP server."""
    parser = argparse.ArgumentParser(
        description='PyRPL TCP Server for PyMoDAQ Integration'
    )
    parser.add_argument(
        '--hostname',
        type=str,
        default='100.107.106.75',
        help='Red Pitaya IP address'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='pymodaq',
        help='PyRPL configuration name'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=6341,
        help='TCP server port'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode without hardware'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("=" * 70)
    print("  PyRPL TCP Server for PyMoDAQ")
    print("=" * 70)
    print(f"  Hostname:      {args.hostname}")
    print(f"  Config:        {args.config}")
    print(f"  Port:          {args.port}")
    print(f"  Mock Mode:     {args.mock}")
    print("=" * 70)
    print()
    
    # Create Qt application
    app = QtWidgets.QApplication(sys.argv)
    
    # Create and start server
    server = PyMoDAQPyRPLServer(
        hostname=args.hostname,
        config_name=args.config,
        port=args.port,
        mock_mode=args.mock
    )
    
    logger.info(f"Server listening on port {args.port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.close_server()


if __name__ == '__main__':
    main()
