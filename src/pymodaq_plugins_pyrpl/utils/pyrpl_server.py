#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyRPL Server Process for PyMoDAQ Integration

This script runs PyRPL in a separate process to completely isolate its Qt event
loop requirements from PyMoDAQ's multi-threaded architecture. It provides IPC
communication for PyMoDAQ plugins to control PyRPL hardware.

This solves the fundamental architectural conflict between:
- PyRPL: Single-threaded Qt event loop with quamash asyncio integration
- PyMoDAQ: Multi-threaded worker isolation for hardware plugins
"""

import sys
import logging
import traceback
from pathlib import Path
from multiprocessing.connection import Listener
from typing import Any, Callable, Dict

# Set up logging for the server process
log_file = Path(__file__).parent / 'pyrpl_server.log'
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # Overwrite log on each restart
)

# Also log to console for debugging
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)


def resolve_attribute(obj: Any, path: str) -> Any:
    """
    Recursively gets a nested attribute from an object.

    Args:
        obj: The object to traverse
        path: Dot-separated attribute path (e.g., 'scope.data', 'pid0.setpoint')

    Returns:
        The resolved attribute or method

    Example:
        resolve_attribute(pyrpl, 'scope.data') -> pyrpl.scope.data
        resolve_attribute(pyrpl, 'pid0.setpoint') -> pyrpl.pid0.setpoint
    """
    for name in path.split('.'):
        obj = getattr(obj, name)
    return obj


def run_server(address: tuple, authkey: bytes, config_file: str) -> None:
    """
    Initialize PyRPL and listen for IPC commands from PyMoDAQ plugins.

    Args:
        address: (hostname, port) tuple for IPC listener
        authkey: Authentication key for secure communication
        config_file: Path to PyRPL configuration file
    """
    logger.info(f"PyRPL server starting on {address}")
    logger.info(f"Using PyRPL config: {config_file}")
    logger.info(f"Log file: {log_file}")

    pyrpl = None

    try:
        # Import and initialize PyRPL in this isolated process
        # This is where the slow SSH connection and FPGA bitfile upload happens
        logger.info("Importing PyRPL...")
        import pyrpl as pyrpl_module

        logger.info("Initializing PyRPL connection...")
        pyrpl = pyrpl_module.Pyrpl(config=config_file)

        logger.info("PyRPL initialized successfully!")
        logger.info(f"Connected to Red Pitaya: {pyrpl.rp.name}")

    except Exception as e:
        logger.error(f"Failed to initialize PyRPL: {e}")
        logger.error(traceback.format_exc())
        return  # Exit if PyRPL can't start

    # Set up IPC listener to accept connections from PyMoDAQ plugins
    try:
        with Listener(address, authkey=authkey) as listener:
            logger.info(f"Server listening for connections...")

            while True:  # Allow multiple plugin connections
                try:
                    with listener.accept() as conn:
                        client_addr = listener.last_accepted
                        logger.info(f"Connection accepted from {client_addr}")

                        # Main command processing loop for this client
                        while True:
                            try:
                                # Receive command from PyMoDAQ plugin
                                msg = conn.recv()
                                command = msg.get('command')
                                attribute = msg.get('attribute')
                                args = msg.get('args', [])
                                kwargs = msg.get('kwargs', {})

                                logger.debug(f"Received command: {command}, attribute: {attribute}")

                                if command == 'shutdown':
                                    logger.info("Shutdown command received")
                                    conn.send({'status': 'ok', 'result': 'Server shutting down'})
                                    return  # Exit server completely

                                elif command == 'ping':
                                    # Health check command
                                    conn.send({'status': 'ok', 'result': 'pong'})
                                    continue

                                # Resolve the attribute/method path (e.g., 'scope.data', 'pid0.setpoint')
                                target = resolve_attribute(pyrpl, attribute)

                                if callable(target):
                                    # Execute method with arguments
                                    result = target(*args, **kwargs)
                                else:
                                    # Return attribute value directly
                                    result = target

                                # Send successful result back to plugin
                                conn.send({'status': 'ok', 'result': result})
                                logger.debug(f"Command executed successfully: {attribute}")

                            except EOFError:
                                logger.info("Client disconnected")
                                break  # Exit inner loop, wait for new connection

                            except Exception as e:
                                error_msg = f"Error processing command '{attribute}': {e}"
                                logger.error(error_msg)
                                logger.error(traceback.format_exc())

                                # Send error back to plugin
                                try:
                                    conn.send({'status': 'error', 'message': str(e)})
                                except (BrokenPipeError, ConnectionResetError):
                                    logger.warning("Could not send error response - connection lost")
                                    break

                except Exception as e:
                    logger.error(f"Connection error: {e}")
                    logger.error(traceback.format_exc())

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server listener failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean shutdown
        if pyrpl:
            try:
                logger.info("Closing PyRPL connection...")
                pyrpl.close()
            except Exception as e:
                logger.warning(f"Error closing PyRPL: {e}")

        logger.info("PyRPL server shutdown complete")


def main():
    """Main entry point when run as script."""
    if len(sys.argv) != 5:
        print("Usage: python pyrpl_server.py <hostname> <port> <authkey> <config_file>")
        print("Example: python pyrpl_server.py localhost 6000 secret_key /path/to/config.yml")
        sys.exit(1)

    # Parse command line arguments
    hostname = sys.argv[1]
    port = int(sys.argv[2])
    authkey = sys.argv[3].encode('utf-8')
    config_file = sys.argv[4]

    address = (hostname, port)

    logger.info(f"Starting PyRPL server with args: {sys.argv[1:]}")

    try:
        run_server(address, authkey, config_file)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()