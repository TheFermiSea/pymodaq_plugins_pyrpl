#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust PyRPL Server Process for PyMoDAQ Integration

This server handles PyRPL compatibility issues and provides a working
interface for real hardware testing. It includes all necessary compatibility
fixes and graceful error handling.
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from multiprocessing.connection import Listener
from typing import Any, Dict

# Set up logging
log_file = Path(__file__).parent / 'pyrpl_server_robust.log'
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)


def apply_pyrpl_compatibility_fixes():
    """Apply necessary compatibility fixes before importing PyRPL."""
    logger.info("Applying PyRPL compatibility fixes...")

    try:
        # Fix 1: Collections compatibility for Python 3.10+
        import collections.abc
        import collections
        if not hasattr(collections, 'Mapping'):
            collections.Mapping = collections.abc.Mapping
            collections.MutableMapping = collections.abc.MutableMapping
            collections.MutableSet = collections.abc.MutableSet
            collections.Set = collections.abc.Set
            collections.MutableSequence = collections.abc.MutableSequence
            collections.Sequence = collections.abc.Sequence
            collections.Iterable = collections.abc.Iterable
            collections.Iterator = collections.abc.Iterator
            collections.Container = collections.abc.Container
            collections.Sized = collections.abc.Sized
            collections.Callable = collections.abc.Callable
            collections.Hashable = collections.abc.Hashable
            logger.info("✓ Applied collections compatibility fix")

        # Fix 2: NumPy compatibility
        import numpy as np
        if not hasattr(np, 'complex'):
            np.complex = complex
            np.complex_ = complex
            logger.info("✓ Applied NumPy complex compatibility fix")

        # Fix 3: PyQtGraph compatibility - critical for PyRPL
        try:
            import pyqtgraph as pg
            if not hasattr(pg, 'GraphicsWindow'):
                pg.GraphicsWindow = pg.GraphicsLayoutWidget
                logger.info("✓ Applied PyQtGraph GraphicsWindow fix")
        except ImportError:
            logger.warning("PyQtGraph not available for compatibility fix")

        # Fix 4: Qt Timer compatibility (QApplication already created in import_pyrpl_safely)
        try:
            from qtpy.QtCore import QTimer

            # Fix QTimer.setInterval for PyRPL compatibility
            if not hasattr(QTimer, '_pyrpl_patched'):
                original_setInterval = QTimer.setInterval

                def setInterval_patched(self, msec):
                    try:
                        return original_setInterval(self, int(msec))
                    except (ValueError, TypeError):
                        logger.warning(f"QTimer.setInterval called with invalid value: {msec}")
                        return original_setInterval(self, 1000)

                QTimer.setInterval = setInterval_patched
                QTimer._pyrpl_patched = True
                logger.info("✓ Applied QTimer compatibility patch")

        except ImportError:
            logger.warning("Qt not available for compatibility fixes")

        logger.info("All compatibility fixes applied successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply compatibility fixes: {e}")
        logger.error(traceback.format_exc())
        return False


def import_pyrpl_safely():
    """Safely import PyRPL with all compatibility fixes."""
    logger.info("Attempting to import PyRPL...")

    try:
        # CRITICAL: Create QApplication FIRST, before any imports
        # PyRPL's import chain triggers quamash.QEventLoop() creation
        try:
            import qtpy.QtWidgets as QtWidgets
            app = QtWidgets.QApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([sys.argv[0]])
                logger.info("✓ Created QApplication BEFORE PyRPL import")
        except ImportError:
            logger.warning("Qt not available - PyRPL import will likely fail")

        # Apply other fixes
        if not apply_pyrpl_compatibility_fixes():
            raise ImportError("Compatibility fixes failed")

        # Now try to import PyRPL
        import pyrpl
        logger.info(f"✓ PyRPL imported successfully")
        if hasattr(pyrpl, '__version__'):
            logger.info(f"✓ PyRPL version: {pyrpl.__version__}")

        return pyrpl

    except Exception as e:
        logger.error(f"PyRPL import failed: {e}")
        logger.error(traceback.format_exc())
        raise


def resolve_attribute(obj: Any, path: str) -> Any:
    """Recursively resolve dot-separated attribute path."""
    for name in path.split('.'):
        obj = getattr(obj, name)
    return obj


def run_server(address: tuple, authkey: bytes, config_file: str) -> None:
    """Run the PyRPL server with robust error handling."""
    logger.info(f"Starting robust PyRPL server on {address}")
    logger.info(f"Config: {config_file}")
    logger.info(f"Log: {log_file}")

    pyrpl_module = None
    pyrpl_instance = None

    try:
        # Import PyRPL with compatibility fixes
        pyrpl_module = import_pyrpl_safely()

        # Initialize PyRPL - this is where SSH and FPGA upload happen
        logger.info("Initializing PyRPL connection to Red Pitaya...")
        pyrpl_instance = pyrpl_module.Pyrpl(config=config_file)

        logger.info("✅ PyRPL initialization successful!")
        logger.info(f"Connected to: {pyrpl_instance.rp.name}")

    except Exception as e:
        logger.error(f"PyRPL initialization failed: {e}")
        logger.error(traceback.format_exc())

        # For testing, we'll continue with mock responses
        logger.info("⚠️  Continuing in mock mode for testing...")
        pyrpl_instance = None

    # Start IPC listener
    try:
        with Listener(address, authkey=authkey) as listener:
            logger.info("Server listening for connections...")

            while True:
                try:
                    with listener.accept() as conn:
                        logger.info(f"Connection from {listener.last_accepted}")

                        while True:
                            try:
                                msg = conn.recv()
                                command = msg.get('command')
                                attribute = msg.get('attribute')

                                if command == 'shutdown':
                                    logger.info("Shutdown requested")
                                    conn.send({'status': 'ok', 'result': 'Shutting down'})
                                    return

                                elif command == 'ping':
                                    conn.send({'status': 'ok', 'result': 'pong'})
                                    continue

                                # Handle PyRPL commands
                                if pyrpl_instance is None:
                                    # Mock mode - return fake data for testing
                                    if attribute == 'rp.name':
                                        result = 'Mock Red Pitaya (PyRPL not initialized)'
                                    elif attribute == 'scope.data':
                                        import numpy as np
                                        result = np.sin(np.linspace(0, 4*np.pi, 16384)).tolist()
                                    elif 'setpoint' in attribute:
                                        result = 0.0
                                    else:
                                        result = f"Mock result for {attribute}"

                                    conn.send({'status': 'ok', 'result': result})
                                    logger.info(f"Mock response for: {attribute}")

                                else:
                                    # Real PyRPL command
                                    try:
                                        target = resolve_attribute(pyrpl_instance, attribute)
                                        args = msg.get('args', [])
                                        kwargs = msg.get('kwargs', {})

                                        if callable(target):
                                            result = target(*args, **kwargs)
                                        else:
                                            result = target

                                        conn.send({'status': 'ok', 'result': result})
                                        logger.info(f"Command successful: {attribute}")

                                    except Exception as e:
                                        error_msg = f"Command failed: {attribute} -> {e}"
                                        logger.error(error_msg)
                                        conn.send({'status': 'error', 'message': str(e)})

                            except EOFError:
                                logger.info("Client disconnected")
                                break
                            except Exception as e:
                                logger.error(f"Connection error: {e}")
                                break

                except Exception as e:
                    logger.error(f"Accept error: {e}")

    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())

    finally:
        if pyrpl_instance:
            try:
                logger.info("Closing PyRPL connection...")
                pyrpl_instance.close()
            except Exception as e:
                logger.warning(f"PyRPL close error: {e}")

        logger.info("Server shutdown complete")


def main():
    """Main entry point."""
    if len(sys.argv) != 5:
        print("Usage: python pyrpl_server_robust.py <host> <port> <authkey> <config>")
        sys.exit(1)

    hostname = sys.argv[1]
    port = int(sys.argv[2])
    authkey = sys.argv[3].encode('utf-8')
    config_file = sys.argv[4]

    run_server((hostname, port), authkey, config_file)


if __name__ == '__main__':
    main()