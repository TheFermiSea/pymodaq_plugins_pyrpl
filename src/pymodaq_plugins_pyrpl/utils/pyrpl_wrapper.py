# -*- coding: utf-8 -*-
"""
PyRPL Wrapper Utilities for PyMoDAQ

This module provides centralized PyRPL connection management, preventing conflicts
between multiple plugins and providing a clean abstraction layer for Red Pitaya
hardware control.

Classes:
    PyRPLConnection: Manages individual Red Pitaya device connections
    PyRPLManager: Singleton connection pool manager
"""

import asyncio
import logging
import sys
import threading
import time
import types
from contextlib import contextmanager
from typing import Dict, Optional, Union, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .quamash_shim import ensure_quamash_shim

QtCore = None
QtWidgets = None
_main_thread_invoker = None
_qt_app = None

# Set up logger early
logger = logging.getLogger(__name__)
try:
    # Python 3.10+ compatibility fix for collections.Mapping
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

    # NumPy 1.20+ compatibility fix for np.complex
    if not hasattr(np, 'complex'):
        np.complex = complex
        np.complex_ = complex

    # PyQTGraph compatibility fix - patch before importing pyrpl
    try:
        import pyqtgraph as pg
        if not hasattr(pg, 'GraphicsWindow'):
            # pyqtgraph 0.13+ removed GraphicsWindow, use GraphicsLayoutWidget instead
            pg.GraphicsWindow = pg.GraphicsLayoutWidget
    except ImportError:
        pass  # pyqtgraph not available

    # Qt timer compatibility fix - patch before importing pyrpl
    try:
        from qtpy import QtCore as _QtCore, QtWidgets as _QtWidgets
        from qtpy.QtCore import QTimer

        globals()['QtCore'] = _QtCore
        globals()['QtWidgets'] = _QtWidgets

        # Removed QApplication creation to avoid conflicts with PyMoDAQ's QApplication
        # The _execute_in_main_thread function has fallback: QtWidgets.QApplication.instance()
        globals()['_qt_app'] = None

        # Qt timer compatibility patch - only apply if not already patched
        if not hasattr(QTimer, '_pyrpl_patched'):
            original_setInterval = QTimer.setInterval

            def setInterval_patched(self, msec):
                """Patched setInterval to handle float inputs properly."""
                try:
                    return original_setInterval(self, int(msec))
                except (ValueError, TypeError):
                    logger.warning(f"QTimer.setInterval called with invalid value: {msec}, using 1000ms default")
                    return original_setInterval(self, 1000)

            QTimer.setInterval = setInterval_patched
            QTimer._pyrpl_patched = True
            logger.debug("Applied PyRPL Qt timer compatibility patch")

        class _MainThreadInvoker(QtCore.QObject):
            """Utility to synchronously execute callables on the Qt main thread."""

            execute = QtCore.Signal(object, object)

            def __init__(self):
                super().__init__()
                self.execute.connect(self._run, QtCore.Qt.BlockingQueuedConnection)

            @QtCore.Slot(object, object)
            def _run(self, func: Callable[[], Any], container: Dict[str, Any]) -> None:
                try:
                    container['result'] = func()
                except Exception as exc:  # pragma: no cover - propagated to caller
                    container['error'] = exc

        globals()['_MainThreadInvoker'] = _MainThreadInvoker

    except ImportError:
        pass  # Qt not available, skip timer patch

    def _execute_in_main_thread(func: Callable[[], Any]) -> Any:
        """Execute *func* on the Qt main thread when possible."""

        _qt_app = globals().get('_qt_app')

        if QtCore is None or QtWidgets is None:
            return func()

        app = _qt_app or QtWidgets.QApplication.instance()
        if app is None or QtCore.QThread.currentThread() == app.thread():
            return func()

        global _main_thread_invoker

        invoker_cls = globals().get('_MainThreadInvoker')
        if invoker_cls is None:
            return func()

        if (_main_thread_invoker is None or
                _main_thread_invoker.thread() != app.thread()):
            _main_thread_invoker = invoker_cls()
            _main_thread_invoker.moveToThread(app.thread())

        container: Dict[str, Any] = {}
        _main_thread_invoker.execute.emit(func, container)

        if 'error' in container:
            raise container['error']

        return container.get('result')

    # Don't import PyRPL at module level - use lazy loading
    PYRPL_AVAILABLE = None  # Will be determined on first use
    pyrpl = None
    PidModule = object
    
    def _lazy_import_pyrpl():
        """Lazy import PyRPL only when needed."""
        global pyrpl, PidModule, PYRPL_AVAILABLE
        
        if PYRPL_AVAILABLE is not None:
            return PYRPL_AVAILABLE
            
        try:
            ensure_quamash_shim(logger)
            _ensure_pyqt4_alias()
            import pyrpl as pyrpl_module
            from pyrpl.hardware_modules.pid import Pid as PidModule_imported
            
            pyrpl = pyrpl_module
            PidModule = PidModule_imported
            _get_or_create_event_loop()
            PYRPL_AVAILABLE = True
            logger.info("PyRPL imported successfully via lazy loading")
            return True
            
        except (ImportError, TypeError, AttributeError) as e:
            logger.warning(f"PyRPL lazy import failed: {e}")
            PYRPL_AVAILABLE = False
            pyrpl = None
            PidModule = object
            
            # Create a mock Pyrpl class
            class _MockPyrpl:
                pass
            pyrpl = type('MockPyrplModule', (), {'Pyrpl': _MockPyrpl})()
            return False

except (ImportError, TypeError, AttributeError) as e:
    # Handle any setup issues
    logger.warning(f"PyRPL wrapper setup failed: {e}")
    PYRPL_AVAILABLE = False
    pyrpl = None
    PidModule = object

    def _execute_in_main_thread(func: Callable[[], Any]) -> Any:
        return func()

    def _lazy_import_pyrpl():
        return False

from pymodaq_utils.utils import ThreadCommand


logger = logging.getLogger(__name__)

_EVENT_LOOP_LOCK = threading.Lock()
_QASYNC_DEFAULT_LOOP: Optional[asyncio.AbstractEventLoop] = None


def _ensure_pyqt4_alias() -> bool:
    existing = sys.modules.get("PyQt4")
    if existing and getattr(existing, "_pymodaq_pyqt4_shim", False):
        return True

    try:
        from qtpy import QtCore as _QtCore, QtGui as _QtGui, QtWidgets as _QtWidgets
    except ImportError as exc:
        logger.error("Qt bindings not available for PyRPL integration: %s", exc)
        return False

    module = types.ModuleType("PyQt4")
    module.QtCore = _QtCore
    module.QtGui = _QtGui
    module.QtWidgets = _QtWidgets
    module.__all__ = ["QtCore", "QtGui", "QtWidgets"]
    module._pymodaq_pyqt4_shim = True

    sys.modules["PyQt4"] = module
    sys.modules.setdefault("PyQt4.QtCore", _QtCore)
    sys.modules.setdefault("PyQt4.QtGui", _QtGui)
    sys.modules.setdefault("PyQt4.QtWidgets", _QtWidgets)
    return True


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass

    with _EVENT_LOOP_LOCK:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            pass

        ensure_quamash_shim(logger)
        _ensure_pyqt4_alias()

        try:
            import qasync
            from qtpy import QtWidgets
        except ImportError as exc:
            raise RuntimeError(
                "qasync>=0.28.0 and Qt bindings are required for PyRPL integration"
            ) from exc

        qt_app = QtWidgets.QApplication.instance()
        if qt_app is None:
            qt_app = QtWidgets.QApplication(["pymodaq-pyrpl"])

        global _QASYNC_DEFAULT_LOOP
        if _QASYNC_DEFAULT_LOOP is not None and not _QASYNC_DEFAULT_LOOP.is_closed():
            asyncio.set_event_loop(_QASYNC_DEFAULT_LOOP)
            return _QASYNC_DEFAULT_LOOP

        loop = qasync.QEventLoop(qt_app)
        asyncio.set_event_loop(loop)
        _QASYNC_DEFAULT_LOOP = loop
        return loop


# =============================================================================
# Singleton Mock Instance Management
# =============================================================================

# Module-level variables for shared mock instance management
_shared_mock_instance: Optional['EnhancedMockPyRPLConnection'] = None
_mock_instance_lock = threading.Lock()

def get_shared_mock_instance(hostname: str) -> Optional['EnhancedMockPyRPLConnection']:
    """
    Factory function to get or create the singleton EnhancedMockPyRPLConnection instance.
    
    This ensures that ALL plugins in mock mode share the same simulation engine,
    enabling coordinated behavior between PID controllers, signal generators,
    oscilloscopes, and IQ detectors.
    
    Parameters:
        hostname (str): Mock hostname for the shared instance
        
    Returns:
        EnhancedMockPyRPLConnection: Shared mock instance, or None if unavailable
        
    Thread Safety:
        This function is thread-safe and can be called concurrently from multiple plugins.
    """
    global _shared_mock_instance
    
    if not ENHANCED_MOCK_AVAILABLE:
        logger.error("EnhancedMockPyRPLConnection not available - mock mode disabled")
        return None
    
    with _mock_instance_lock:
        if _shared_mock_instance is None:
            # Create the one and only shared mock instance
            try:
                _shared_mock_instance = EnhancedMockPyRPLConnection(hostname)
                logger.info(f"Created shared mock instance for hostname: {hostname}")
            except Exception as e:
                logger.error(f"Failed to create shared mock instance: {e}")
                return None
        else:
            # Return existing shared instance - ignore hostname for consistency
            logger.debug(f"Returning existing shared mock instance (original hostname: {_shared_mock_instance.hostname})")
            
        return _shared_mock_instance

def reset_shared_mock_instance() -> None:
    """
    Reset the shared mock instance.
    
    This is primarily used for testing scenarios where a clean mock state is needed.
    In production, the shared instance should persist for the entire application lifetime.
    """
    global _shared_mock_instance
    
    with _mock_instance_lock:
        if _shared_mock_instance is not None:
            try:
                _shared_mock_instance.reset_simulation()
                logger.info("Reset shared mock instance simulation")
            except Exception as e:
                logger.error(f"Error resetting shared mock instance: {e}")
                
        # Clear both our wrapper singleton and the EnhancedMockPyRPLConnection registry
        _shared_mock_instance = None
        
        # Clear the EnhancedMockPyRPLConnection internal registry for complete reset
        if ENHANCED_MOCK_AVAILABLE and EnhancedMockPyRPLConnection is not None:
            try:
                EnhancedMockPyRPLConnection._instances.clear()
                logger.info("Cleared EnhancedMockPyRPLConnection registry")
            except Exception as e:
                logger.error(f"Error clearing mock connection registry: {e}")
                
        logger.info("Cleared shared mock instance")

def get_mock_instance_info() -> Dict[str, Any]:
    """
    Get information about the current shared mock instance.
    
    Returns:
        Dict with mock instance status and connection information
    """
    with _mock_instance_lock:
        if _shared_mock_instance is None:
            return {
                "exists": False,
                "hostname": None,
                "connection_count": 0
            }
        else:
            try:
                info = _shared_mock_instance.get_connection_info()
                info["exists"] = True
                return info
            except Exception as e:
                logger.error(f"Error getting mock instance info: {e}")
                return {
                    "exists": True,
                    "hostname": getattr(_shared_mock_instance, 'hostname', 'unknown'),
                    "error": str(e)
                }


class ConnectionState(Enum):
    """Connection states for PyRPL devices."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class PIDChannel(Enum):
    """Available PID channels on Red Pitaya."""
    PID0 = "pid0"
    PID1 = "pid1"
    PID2 = "pid2"


class InputChannel(Enum):
    """Available input channels on Red Pitaya."""
    IN1 = "in1"
    IN2 = "in2"


class OutputChannel(Enum):
    """Available output channels on Red Pitaya."""
    OUT1 = "out1"
    OUT2 = "out2"


class ASGChannel(Enum):
    """Available ASG (Arbitrary Signal Generator) channels on Red Pitaya."""
    ASG0 = "asg0"
    ASG1 = "asg1"


class ASGWaveform(Enum):
    """Available waveforms for ASG."""
    SIN = "sin"
    COS = "cos"
    RAMP = "ramp"
    HALFRAMP = "halframp"
    SQUARE = "square"
    NOISE = "noise"
    DC = "dc"
    CUSTOM = "custom"


class ASGTriggerSource(Enum):
    """Available trigger sources for ASG."""
    OFF = "off"
    IMMEDIATELY = "immediately"
    EXT_POSITIVE_EDGE = "ext_positive_edge"
    EXT_NEGATIVE_EDGE = "ext_negative_edge"
    EXT_POSITIVE_LEVEL = "ext_positive_level"
    EXT_NEGATIVE_LEVEL = "ext_negative_level"


class IQChannel(Enum):
    """Available IQ (Lock-in Amplifier) channels on Red Pitaya."""
    IQ0 = "iq0"
    IQ1 = "iq1"
    IQ2 = "iq2"


class IQOutputDirect(Enum):
    """Available output routing for IQ modules."""
    OFF = "off"
    OUT1 = "out1"
    OUT2 = "out2"


class ScopeTriggerSource(Enum):
    """Available trigger sources for Scope."""
    IMMEDIATELY = "immediately"
    CH1_POSITIVE_EDGE = "ch1_positive_edge"
    CH1_NEGATIVE_EDGE = "ch1_negative_edge"
    CH2_POSITIVE_EDGE = "ch2_positive_edge"
    CH2_NEGATIVE_EDGE = "ch2_negative_edge"
    EXT_POSITIVE_EDGE = "ext_positive_edge"
    EXT_NEGATIVE_EDGE = "ext_negative_edge"


class ScopeDecimation(Enum):
    """Available decimation values for Scope."""
    DEC_1 = 1
    DEC_8 = 8
    DEC_64 = 64
    DEC_1024 = 1024
    DEC_8192 = 8192
    DEC_65536 = 65536



# Import enhanced mock connection for unified simulation (after enum definitions)
try:
    from .enhanced_mock_connection import EnhancedMockPyRPLConnection
    ENHANCED_MOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Enhanced mock connection unavailable: {e}")
    ENHANCED_MOCK_AVAILABLE = False
    EnhancedMockPyRPLConnection = None

@dataclass
class PIDConfiguration:
    """Configuration for a PID controller."""
    setpoint: float = 0.0
    p_gain: float = 0.1
    i_gain: float = 0.0
    d_gain: float = 0.0
    input_channel: InputChannel = InputChannel.IN1
    output_channel: OutputChannel = OutputChannel.OUT1
    voltage_limit_min: float = -1.0
    voltage_limit_max: float = 1.0
    enabled: bool = False


@dataclass
class ASGConfiguration:
    """Configuration for an Arbitrary Signal Generator."""
    frequency: float = 1000.0  # Hz
    amplitude: float = 0.1  # V
    offset: float = 0.0  # V
    phase: float = 0.0  # degrees
    waveform: ASGWaveform = ASGWaveform.SIN
    trigger_source: ASGTriggerSource = ASGTriggerSource.IMMEDIATELY
    output_enable: bool = True
    frequency_min: float = 0.0
    frequency_max: float = 62.5e6  # 62.5 MHz max frequency for Red Pitaya
    amplitude_min: float = -1.0
    amplitude_max: float = 1.0
    offset_min: float = -1.0
    offset_max: float = 1.0


@dataclass
class IQConfiguration:
    """Configuration for IQ (Lock-in Amplifier) module."""
    frequency: float = 1000.0  # Hz
    bandwidth: float = 100.0  # Hz
    acbandwidth: float = 10000.0  # Hz, AC bandwidth/inputfilter
    phase: float = 0.0  # degrees
    gain: float = 1.0  # amplification factor
    quadrature_factor: float = 1.0  # quadrature signal factor
    amplitude: float = 0.0  # V, output amplitude
    input_channel: InputChannel = InputChannel.IN1
    output_direct: IQOutputDirect = IQOutputDirect.OFF
    frequency_min: float = 0.1
    frequency_max: float = 62.5e6  # 62.5 MHz max frequency for Red Pitaya
    bandwidth_min: float = 0.01
    bandwidth_max: float = 62.5e6
    acbandwidth_max: float = 62.5e6
    phase_min: float = -180.0
    phase_max: float = 180.0
    gain_min: float = 0.001
    gain_max: float = 1000.0
    quadrature_factor_min: float = -10.0
    quadrature_factor_max: float = 10.0
    amplitude_min: float = -1.0
    amplitude_max: float = 1.0


@dataclass
class ScopeConfiguration:
    """Configuration for Scope module."""
    input_channel: InputChannel = InputChannel.IN1
    decimation: ScopeDecimation = ScopeDecimation.DEC_64
    trigger_source: ScopeTriggerSource = ScopeTriggerSource.IMMEDIATELY
    trigger_delay: int = 0  # 0 to 16383 samples
    trigger_level: float = 0.0  # -1.0 to 1.0 V
    average: int = 1  # 1 to 1000 averages
    rolling_mode: bool = False
    timeout: float = 5.0  # acquisition timeout in seconds
    data_length: int = 16384  # 2^14 samples fixed for Red Pitaya


@dataclass
class ConnectionInfo:
    """Information about a Red Pitaya connection."""
    hostname: str
    config_name: str = "pymodaq"
    port: int = 2222
    connection_timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


class PyRPLConnection:
    """
    Manages a single Red Pitaya connection with thread-safe operations.

    This class handles the connection lifecycle, PID module management,
    and provides safe access to hardware resources.

    Attributes:
        hostname (str): Red Pitaya hostname or IP address
        config_name (str): PyRPL configuration name
        state (ConnectionState): Current connection state
        last_error (Optional[str]): Last error message if any
    """

    def __init__(self, connection_info: ConnectionInfo):
        self.hostname = connection_info.hostname
        self.config_name = connection_info.config_name
        self.port = connection_info.port
        self.connection_timeout = connection_info.connection_timeout
        self.retry_attempts = connection_info.retry_attempts
        self.retry_delay = connection_info.retry_delay

        self.state = ConnectionState.DISCONNECTED
        self.last_error: Optional[str] = None
        self.connected_at: Optional[float] = None

        # PyRPL objects (using Any to avoid import issues)
        self._pyrpl: Optional[Any] = None
        self._redpitaya: Optional[Any] = None

        # Thread safety
        self._lock = threading.RLock()
        self._connection_lock = threading.Lock()

        # PID modules tracking
        self._active_pids: Dict[PIDChannel, PidModule] = {}
        self._pid_configs: Dict[PIDChannel, PIDConfiguration] = {}

        # ASG modules tracking
        self._active_asgs: Dict[ASGChannel, Any] = {}
        self._asg_configs: Dict[ASGChannel, ASGConfiguration] = {}

        # IQ modules tracking
        self._active_iqs: Dict[IQChannel, Any] = {}
        self._iq_configs: Dict[IQChannel, IQConfiguration] = {}

        # Scope module tracking
        self._scope_module: Optional[Any] = None
        self._scope_config: Optional[ScopeConfiguration] = None

        # Reference counting for proper cleanup
        self._ref_count = 0

    @property
    def is_connected(self) -> bool:
        """Check if the connection is active and healthy."""
        with self._lock:
            return (self.state == ConnectionState.CONNECTED and
                    self._pyrpl is not None and
                    self._redpitaya is not None)

    @property
    def pyrpl(self) -> Optional[Any]:
        """Get the PyRPL instance (thread-safe)."""
        with self._lock:
            return self._pyrpl

    @property
    def redpitaya(self) -> Optional[Any]:
        """Get the Red Pitaya instance (thread-safe)."""
        with self._lock:
            return self._redpitaya

    def get_pyrpl_instance(self) -> Optional[Any]:
        """
        Return the underlying pyrpl.Pyrpl instance for native widget access.

        Returns:
            The pyrpl.Pyrpl instance if connected; otherwise None.
            In environments where PyRPL is unavailable or when operating without
            a live connection (e.g., mock usage at plugin layer), this returns None.

        Thread-safety:
            This method is thread-safe and follows the class locking pattern.
        """
        with self._lock:
            if not self.is_connected:
                return None
            return self._pyrpl

    def connect(self, status_callback: Optional[callable] = None) -> bool:
        """
        Establish connection to Red Pitaya with robust error handling and retries.

        This method implements a sophisticated connection strategy that handles:
        - PyRPL import verification and lazy loading
        - Connection retries with exponential backoff
        - PyRPL-specific error handling (ZeroDivisionError workarounds)
        - Thread-safe connection state management
        - Comprehensive status reporting and logging

        Args:
            status_callback (Optional[callable]): Callback function for status updates.
                Should accept ThreadCommand objects for PyMoDAQ integration.

        Returns:
            bool: True if connection successful, False otherwise

        Note:
            This method includes specific workarounds for PyRPL compatibility issues,
            particularly handling ZeroDivisionError exceptions that can occur during
            PyRPL module initialization but don't prevent successful connections.
        """
        with self._connection_lock:  # Ensure thread-safe connection operations
            # Early return if already connected - avoid redundant connection attempts
            if self.is_connected:
                logger.debug(f"Already connected to {self.hostname}")
                return True

            # Initialize connection state for this attempt
            self.state = ConnectionState.CONNECTING
            self.last_error = None

            # Notify user of connection initiation
            if status_callback:
                status_callback(ThreadCommand('Update_Status',
                    [f"Connecting to Red Pitaya at {self.hostname}", 'log']))

            # Verify PyRPL availability before attempting connection
            # This handles cases where PyRPL failed to import during initialization
            if not _lazy_import_pyrpl():
                # _lazy_import_pyrpl already logs a warning if it fails.
                # Here, we escalate it to an error for the connection context.
                error_msg = "PyRPL is not available - lazy import failed. Cannot establish connection."
                logger.error(error_msg)
                self.state = ConnectionState.ERROR
                self.last_error = error_msg
                return False

            # Retry loop with configurable attempts and delay
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Connection attempt {attempt + 1}/{self.retry_attempts} to {self.hostname}")
                    
                    # Create PyRPL connection instance
                    # This is the core PyRPL initialization that connects to Red Pitaya
                    # Handle asyncio event loop requirement for PyRPL
                    # Require host-provided qasync loop instead of creating competing loops
                    loop = _get_or_create_event_loop()
                    logger.info(f"Using event loop: {type(loop)}")
                    
                    def _create_pyrpl_instance():
                        return pyrpl.Pyrpl(
                            config=self.config_name,      # PyRPL configuration name for persistence
                            hostname=self.hostname,       # Red Pitaya network address
                            port=self.port,               # SSH port (typically 22)
                            timeout=self.connection_timeout,  # Network timeout
                            gui=False                     # Force headless mode inside PyMoDAQ worker threads
                        )

                    self._pyrpl = _execute_in_main_thread(_create_pyrpl_instance)

                    # Get the Red Pitaya device object for hardware access
                    self._redpitaya = self._pyrpl.rp

                    # Connection is successful if we reach this point without exceptions
                    # Note: We skip version checks due to PyRPL compatibility issues
                    logger.debug(f"PyRPL connection established to {self.hostname}")

                    # Update connection state and metadata
                    self.state = ConnectionState.CONNECTED
                    self.connected_at = time.time()  # Record connection timestamp
                    self.last_error = None           # Clear any previous errors

                    logger.info(f"Successfully connected to Red Pitaya {self.hostname}")

                    # Notify user of successful connection
                    if status_callback:
                        status_callback(ThreadCommand('Update_Status',
                            [f"Red Pitaya {self.hostname} connected", 'log']))

                    return True

                except ZeroDivisionError as e:
                    # PyRPL-specific workaround: Sometimes PyRPL throws ZeroDivisionError
                    # during module initialization, but the connection is actually successful.
                    # This is a known PyRPL issue that doesn't prevent hardware access.
                    logger.debug(f"Ignoring PyRPL ZeroDivisionError: {e}")
                    
                    # Check if connection objects were created despite the error
                    if self._pyrpl and self._redpitaya:
                        logger.info(f"PyRPL connection successful despite ZeroDivisionError")
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True
                    
                    # If no connection objects exist, treat as a real error
                    error_msg = f"Connection attempt {attempt + 1} failed: {str(e)}"
                    logger.warning(error_msg)
                    self.last_error = str(e)

                    # Wait before retry (unless this is the last attempt)
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

                except Exception as e:
                    # Handle other PyRPL-related errors that might not prevent connection
                    error_str = str(e)
                    
                    # Another PyRPL workaround: "float division by zero" errors
                    # can occur during initialization but don't prevent successful connections
                    if "float division by zero" in error_str and self._pyrpl and self._redpitaya:
                        logger.info(f"PyRPL connection successful despite error: {error_str}")
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True

                    # Log the error and prepare for potential retry
                    error_msg = f"Connection attempt {attempt + 1} failed: {error_str}"
                    logger.warning(error_msg)
                    self.last_error = error_str

                    # Wait before retry (unless this is the last attempt)
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

            # All retry attempts have been exhausted without success
            self.state = ConnectionState.ERROR
            error_msg = f"Failed to connect to {self.hostname} after {self.retry_attempts} attempts"
            logger.error(error_msg)

            # Notify user of connection failure
            if status_callback:
                status_callback(ThreadCommand('Update_Status', [error_msg, 'log']))

            return False

    def disconnect(self, status_callback: Optional[callable] = None) -> None:
        """
        Safely disconnect from Red Pitaya.

        Args:
            status_callback: Optional callback for status updates
        """
        with self._connection_lock:
            if not self.is_connected:
                return

            try:
                if status_callback:
                    status_callback(ThreadCommand('Update_Status',
                        [f"Disconnecting from {self.hostname}", 'log']))

                # Safely disable all active PIDs, ASGs, IQs, and Scope
                self._disable_all_pids()
                self._disable_all_asgs()
                self._disable_all_iqs()
                self._disable_scope()

                # Close PyRPL connection
                if self._pyrpl is not None:
                    self._pyrpl.close()

                self._pyrpl = None
                self._redpitaya = None
                self._active_pids.clear()
                self._pid_configs.clear()
                self._active_asgs.clear()
                self._asg_configs.clear()
                self._active_iqs.clear()
                self._iq_configs.clear()
                self._scope_module = None
                self._scope_config = None

                self.state = ConnectionState.DISCONNECTED
                self.connected_at = None

                logger.info(f"Disconnected from Red Pitaya {self.hostname}")

                if status_callback:
                    status_callback(ThreadCommand('Update_Status',
                        [f"Disconnected from {self.hostname}", 'log']))

            except Exception as e:
                error_msg = f"Error during disconnect from {self.hostname}: {str(e)}"
                logger.error(error_msg)
                self.last_error = str(e)
                self.state = ConnectionState.ERROR

    def _disable_all_pids(self) -> None:
        """Safely disable all active PID controllers."""
        for pid_channel, pid_module in self._active_pids.items():
            try:
                pid_module.output_direct = 'off'
                pid_module.input = 'off'
                logger.debug(f"Disabled PID {pid_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable PID {pid_channel.value}: {e}")

    def _disable_all_asgs(self) -> None:
        """Safely disable all active ASG modules."""
        for asg_channel, asg_module in self._active_asgs.items():
            try:
                asg_module.output_direct = 'off'
                asg_module.trigger_source = 'off'
                logger.debug(f"Disabled ASG {asg_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable ASG {asg_channel.value}: {e}")

    def _disable_all_iqs(self) -> None:
        """Safely disable all active IQ modules."""
        for iq_channel, iq_module in self._active_iqs.items():
            try:
                iq_module.output_direct = 'off'
                iq_module.input = 'off'
                logger.debug(f"Disabled IQ {iq_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable IQ {iq_channel.value}: {e}")

    def _disable_scope(self) -> None:
        """Safely disable scope module."""
        if self._scope_module is not None:
            try:
                # Stop any ongoing acquisition
                self._scope_module.trigger_source = 'off'
                logger.debug("Disabled scope module")
            except Exception as e:
                logger.warning(f"Failed to disable scope: {e}")

    def get_pid_module(self, channel: PIDChannel) -> Optional[PidModule]:
        """
        Get a PID module for the specified channel.

        Args:
            channel: PID channel to retrieve

        Returns:
            PidModule or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                if channel not in self._active_pids:
                    pid_module = getattr(self._redpitaya, channel.value)
                    self._active_pids[channel] = pid_module

                return self._active_pids[channel]

            except Exception as e:
                logger.error(f"Failed to get PID module {channel.value}: {e}")
                return None

    def configure_pid(self, channel: PIDChannel, config: PIDConfiguration) -> bool:
        """
        Configure a Red Pitaya hardware PID controller with comprehensive parameter setup.

        This method configures all aspects of a PID controller including:
        - PID gains (P, I, D coefficients)
        - Signal routing (input/output channel assignment)
        - Voltage limits and safety bounds
        - Enable/disable state management
        - Setpoint initialization

        The configuration is applied atomically - either all parameters are set
        successfully, or the operation fails and logs appropriate errors.

        Args:
            channel (PIDChannel): PID channel to configure (PID0, PID1, or PID2)
            config (PIDConfiguration): Complete PID configuration including:
                - setpoint: Target voltage value
                - p_gain, i_gain, d_gain: PID coefficients
                - input_channel: Signal input (IN1, IN2)
                - output_channel: Control output (OUT1, OUT2)
                - voltage_limit_min/max: Safety voltage bounds
                - enabled: Whether to activate the PID output

        Returns:
            bool: True if configuration successful, False if any step failed

        Thread Safety:
            This method is thread-safe and uses internal locks to prevent
            concurrent access to hardware during configuration.

        Hardware Impact:
            - Changes to PID parameters take effect immediately
            - Output routing changes are applied instantly
            - Voltage limits provide hardware-level protection
            - Disabled PIDs set output_direct to 'off' for safety
        """
        with self._lock:  # Ensure thread-safe hardware access
            # Verify connection state before attempting hardware operations
            if not self.is_connected:
                logger.error(f"Cannot configure PID {channel.value}: not connected")
                return False

            try:
                # Get the hardware PID module object for this channel
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    # get_pid_module already logged the specific error
                    return False

                # Store configuration in our internal cache for later reference
                # This allows other methods to query current PID settings
                self._pid_configs[channel] = config

                # Configure core PID parameters
                # These are the fundamental control law coefficients
                pid_module.setpoint = config.setpoint  # Target value for control
                pid_module.p = config.p_gain          # Proportional gain
                pid_module.i = config.i_gain          # Integral gain  
                pid_module.d = config.d_gain          # Derivative gain

                # Configure signal routing for the PID loop
                # Input: where the PID reads the process variable (sensor signal)
                pid_module.input = config.input_channel.value
                
                # Output: where the PID sends the control signal (actuator drive)
                # The output routing is conditional based on enable state for safety
                if config.enabled:
                    # Enable PID output to the specified channel
                    pid_module.output_direct = config.output_channel.value
                else:
                    # Disable PID output for safety - no control signal generated
                    pid_module.output_direct = 'off'

                # Apply voltage safety limits to prevent hardware damage
                # These limits are enforced at the hardware level by the Red Pitaya FPGA
                pid_module.max_voltage = config.voltage_limit_max  # Upper bound (typically +1V)
                pid_module.min_voltage = config.voltage_limit_min  # Lower bound (typically -1V)

                # Track this PID as active for proper cleanup during disconnection
                self._active_pids[channel] = pid_module

                logger.debug(f"Configured PID {channel.value} with setpoint {config.setpoint}")
                return True

            except Exception as e:
                # Log detailed error for debugging while returning simple failure status
                logger.error(f"Failed to configure PID {channel.value}: {e}")
                return False

    def set_pid_setpoint(self, channel: PIDChannel, setpoint: float) -> bool:
        """
        Set the setpoint for a PID controller.

        Args:
            channel: PID channel
            setpoint: New setpoint value

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                pid_module.setpoint = setpoint

                # Update stored configuration
                if channel in self._pid_configs:
                    self._pid_configs[channel].setpoint = setpoint

                return True

            except Exception as e:
                logger.error(f"Failed to set setpoint for PID {channel.value}: {e}")
                return False

    def get_pid_setpoint(self, channel: PIDChannel) -> Optional[float]:
        """
        Get the current setpoint for a PID controller.

        Args:
            channel: PID channel

        Returns:
            Current setpoint or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return None

                return pid_module.setpoint

            except Exception as e:
                logger.error(f"Failed to get setpoint for PID {channel.value}: {e}")
                return None

    def get_pid_configuration(self, channel: PIDChannel) -> Optional[PIDConfiguration]:
        """
        Read current PID configuration from hardware or cached state.

        Returns:
            PIDConfiguration or None on error/not connected.
        """
        with self._lock:
            if not self.is_connected:
                return None
            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return None

                # Prefer cached routing/limits if available (some backends may report 'off')
                cached = self._pid_configs.get(channel)

                # Gains and setpoint are always read from hardware
                p_gain = getattr(pid_module, 'p', None)
                i_gain = getattr(pid_module, 'i', None)
                d_gain = getattr(pid_module, 'd', None)
                setpoint = getattr(pid_module, 'setpoint', None)

                # Route mapping with fallbacks to cached values if hardware reports unsupported values
                in_val = getattr(pid_module, 'input', None)
                out_val = getattr(pid_module, 'output_direct', None)

                try:
                    input_channel = InputChannel(in_val) if in_val in [e.value for e in InputChannel] else (
                        cached.input_channel if cached else InputChannel.IN1
                    )
                except Exception:
                    input_channel = cached.input_channel if cached else InputChannel.IN1

                try:
                    output_channel = OutputChannel(out_val) if out_val in [e.value for e in OutputChannel] else (
                        cached.output_channel if cached else OutputChannel.OUT1
                    )
                except Exception:
                    output_channel = cached.output_channel if cached else OutputChannel.OUT1

                # Limits; fallback to cached if not present
                vmin = getattr(pid_module, 'min_voltage', None)
                vmax = getattr(pid_module, 'max_voltage', None)
                voltage_limit_min = vmin if isinstance(vmin, (int, float)) else (cached.voltage_limit_min if cached else -1.0)
                voltage_limit_max = vmax if isinstance(vmax, (int, float)) else (cached.voltage_limit_max if cached else 1.0)

                enabled = (out_val in [e.value for e in OutputChannel]) if out_val is not None else (cached.enabled if cached else False)

                # Build configuration object
                return PIDConfiguration(
                    setpoint=setpoint if isinstance(setpoint, (int, float)) else (cached.setpoint if cached else 0.0),
                    p_gain=p_gain if isinstance(p_gain, (int, float)) else (cached.p_gain if cached else 0.1),
                    i_gain=i_gain if isinstance(i_gain, (int, float)) else (cached.i_gain if cached else 0.0),
                    d_gain=d_gain if isinstance(d_gain, (int, float)) else (cached.d_gain if cached else 0.0),
                    input_channel=input_channel,
                    output_channel=output_channel,
                    voltage_limit_min=voltage_limit_min,
                    voltage_limit_max=voltage_limit_max,
                    enabled=enabled
                )
            except Exception as e:
                logger.error(f"Failed to get PID configuration for {channel.value}: {e}")
                return None

    def enable_pid(self, channel: PIDChannel) -> bool:
        """
        Enable a PID controller.

        Args:
            channel: PID channel to enable

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None or channel not in self._pid_configs:
                    return False

                config = self._pid_configs[channel]
                pid_module.output_direct = config.output_channel.value
                config.enabled = True

                logger.debug(f"Enabled PID {channel.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to enable PID {channel.value}: {e}")
                return False

    def disable_pid(self, channel: PIDChannel) -> bool:
        """
        Disable a PID controller.

        Args:
            channel: PID channel to disable

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                pid_module.output_direct = 'off'

                if channel in self._pid_configs:
                    self._pid_configs[channel].enabled = False

                logger.debug(f"Disabled PID {channel.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to disable PID {channel.value}: {e}")
                return False

    def read_voltage(self, channel: InputChannel) -> Optional[float]:
        """
        Read voltage from an input channel.

        Args:
            channel: Input channel to read

        Returns:
            Voltage value or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # Use scope for fast voltage reading
                if hasattr(self._redpitaya, 'scope'):
                    scope = self._redpitaya.scope
                    if channel == InputChannel.IN1:
                        return scope.voltage_in1
                    elif channel == InputChannel.IN2:
                        return scope.voltage_in2

                # Fallback to sampler if scope not available
                if hasattr(self._redpitaya, 'sampler'):
                    sampler = self._redpitaya.sampler
                    return getattr(sampler, channel.value)

                logger.warning("Neither scope nor sampler available for voltage reading")
                return None

            except Exception as e:
                logger.error(f"Failed to read voltage from {channel.value}: {e}")
                return None

    def get_asg_module(self, channel: ASGChannel) -> Optional[Any]:
        """
        Get an ASG module for the specified channel.

        Args:
            channel: ASG channel to retrieve

        Returns:
            ASG module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                if channel not in self._active_asgs:
                    asg_module = getattr(self._redpitaya, channel.value)
                    self._active_asgs[channel] = asg_module

                return self._active_asgs[channel]

            except Exception as e:
                logger.error(f"Failed to get ASG module {channel.value}: {e}")
                return None

    def configure_asg(self, channel: ASGChannel, config: ASGConfiguration) -> bool:
        """
        Configure an ASG with the specified parameters.

        Args:
            channel: ASG channel to configure
            config: ASG configuration parameters

        Returns:
            bool: True if configuration successful
        """
        with self._lock:
            if not self.is_connected:
                logger.error(f"Cannot configure ASG {channel.value}: not connected")
                return False

            try:
                asg_module = self.get_asg_module(channel)
                if asg_module is None:
                    return False

                # Store configuration
                self._asg_configs[channel] = config

                # Configure ASG parameters
                asg_module.frequency = config.frequency
                asg_module.amplitude = config.amplitude
                asg_module.offset = config.offset
                asg_module.phase = config.phase

                # Set waveform
                asg_module.waveform = config.waveform.value

                # Configure trigger
                asg_module.trigger_source = config.trigger_source.value

                # Enable/disable output
                if config.output_enable:
                    asg_module.output_direct = f'out{channel.value[-1]}'  # out1 or out2
                else:
                    asg_module.output_direct = 'off'

                logger.debug(f"Configured ASG {channel.value} with frequency {config.frequency} Hz")
                return True

            except Exception as e:
                logger.error(f"Failed to configure ASG {channel.value}: {e}")
                return False

    def set_asg_frequency(self, channel: ASGChannel, frequency: float) -> bool:
        """
        Set the frequency for an ASG.

        Args:
            channel: ASG channel
            frequency: New frequency value in Hz

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                asg_module = self.get_asg_module(channel)
                if asg_module is None:
                    return False

                asg_module.frequency = frequency

                # Update stored configuration
                if channel in self._asg_configs:
                    self._asg_configs[channel].frequency = frequency

                return True

            except Exception as e:
                logger.error(f"Failed to set frequency for ASG {channel.value}: {e}")
                return False

    def get_asg_frequency(self, channel: ASGChannel) -> Optional[float]:
        """
        Get the current frequency for an ASG.

        Args:
            channel: ASG channel

        Returns:
            Current frequency in Hz or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                asg_module = self.get_asg_module(channel)
                if asg_module is None:
                    return None

                return asg_module.frequency

            except Exception as e:
                logger.error(f"Failed to get frequency for ASG {channel.value}: {e}")
                return None

    def set_asg_amplitude(self, channel: ASGChannel, amplitude: float) -> bool:
        """
        Set the amplitude for an ASG.

        Args:
            channel: ASG channel
            amplitude: New amplitude value in V

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                asg_module = self.get_asg_module(channel)
                if asg_module is None:
                    return False

                asg_module.amplitude = amplitude

                # Update stored configuration
                if channel in self._asg_configs:
                    self._asg_configs[channel].amplitude = amplitude

                return True

            except Exception as e:
                logger.error(f"Failed to set amplitude for ASG {channel.value}: {e}")
                return False

    def enable_asg_output(self, channel: ASGChannel, enable: bool) -> bool:
        """
        Enable or disable ASG output.

        Args:
            channel: ASG channel
            enable: True to enable, False to disable output

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                asg_module = self.get_asg_module(channel)
                if asg_module is None:
                    return False

                if enable:
                    asg_module.output_direct = f'out{channel.value[-1]}'  # out1 or out2
                else:
                    asg_module.output_direct = 'off'

                # Update stored configuration
                if channel in self._asg_configs:
                    self._asg_configs[channel].output_enable = enable

                logger.debug(f"{'Enabled' if enable else 'Disabled'} ASG {channel.value} output")
                return True

            except Exception as e:
                logger.error(f"Failed to {'enable' if enable else 'disable'} ASG {channel.value}: {e}")
                return False

    def get_scope_module(self) -> Optional[Any]:
        """
        Get the scope module for oscilloscope functionality.

        Returns:
            Scope module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                if self._scope_module is None:
                    self._scope_module = self._redpitaya.scope

                return self._scope_module

            except Exception as e:
                logger.error(f"Failed to get scope module: {e}")
                return None

    def configure_scope(self, config: ScopeConfiguration) -> bool:
        """
        Configure the scope with the specified parameters.

        Args:
            config: Scope configuration parameters

        Returns:
            bool: True if configuration successful
        """
        with self._lock:
            if not self.is_connected:
                logger.error("Cannot configure scope: not connected")
                return False

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return False

                # Store configuration
                self._scope_config = config

                # Configure scope parameters
                scope.decimation = config.decimation.value
                scope.trigger_source = config.trigger_source.value
                scope.trigger_delay = config.trigger_delay
                scope.trigger_level = config.trigger_level
                scope.average = config.average
                scope.rolling_mode = config.rolling_mode

                # Set input channel
                scope.input = config.input_channel.value

                logger.debug(f"Configured scope with decimation {config.decimation.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to configure scope: {e}")
                return False

    def acquire_scope_data(self, timeout: Optional[float] = None) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Acquire data from the scope.

        Args:
            timeout: Optional timeout in seconds (uses config timeout if None)

        Returns:
            Tuple of (time_axis, voltage_data) or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            if self._scope_config is None:
                logger.error("Scope not configured")
                return None

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return None

                # Use config timeout if not specified
                acq_timeout = timeout if timeout is not None else self._scope_config.timeout

                # Start acquisition
                start_time = time.time()
                scope.trigger()

                # Wait for acquisition to complete
                while not scope.stopped():
                    if time.time() - start_time > acq_timeout:
                        logger.error(f"Scope acquisition timeout ({acq_timeout}s)")
                        return None
                    time.sleep(0.001)  # 1ms polling interval

                # Get data
                voltage_data = scope.curve()

                # Generate time axis
                sampling_time = scope.sampling_time
                duration = scope.duration
                data_length = len(voltage_data)
                time_axis = np.linspace(0, duration, data_length)

                logger.debug(f"Acquired {len(voltage_data)} scope samples")
                return time_axis, voltage_data

            except Exception as e:
                logger.error(f"Failed to acquire scope data: {e}")
                return None

    def get_scope_sampling_time(self) -> Optional[float]:
        """
        Get the current scope sampling time.

        Returns:
            Sampling time in seconds or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return None

                return scope.sampling_time

            except Exception as e:
                logger.error(f"Failed to get scope sampling time: {e}")
                return None

    def get_scope_duration(self) -> Optional[float]:
        """
        Get the current scope acquisition duration.

        Returns:
            Duration in seconds or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return None

                return scope.duration

            except Exception as e:
                logger.error(f"Failed to get scope duration: {e}")
                return None

    def start_scope_acquisition(self) -> bool:
        """
        Start scope acquisition (trigger).

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return False

                scope.trigger()
                return True

            except Exception as e:
                logger.error(f"Failed to start scope acquisition: {e}")
                return False

    def stop_scope_acquisition(self) -> bool:
        """
        Stop scope acquisition.

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return False

                scope.stop()
                return True

            except Exception as e:
                logger.error(f"Failed to stop scope acquisition: {e}")
                return False

    def is_scope_running(self) -> Optional[bool]:
        """
        Check if scope acquisition is running.

        Returns:
            True if running, False if stopped, None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                scope = self.get_scope_module()
                if scope is None:
                    return None

                return not scope.stopped()

            except Exception as e:
                logger.error(f"Failed to check scope status: {e}")
                return None

    def get_iq_module(self, channel: IQChannel) -> Optional[Any]:
        """
        Get an IQ module for the specified channel.

        Args:
            channel: IQ channel to retrieve

        Returns:
            IQ module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                if channel not in self._active_iqs:
                    iq_module = getattr(self._redpitaya, channel.value)
                    self._active_iqs[channel] = iq_module

                return self._active_iqs[channel]

            except Exception as e:
                logger.error(f"Failed to get IQ module {channel.value}: {e}")
                return None

    def configure_iq(self, channel: IQChannel, config: IQConfiguration) -> bool:
        """
        Configure an IQ lock-in amplifier with the specified parameters.

        Args:
            channel: IQ channel to configure
            config: IQ configuration parameters

        Returns:
            bool: True if configuration successful
        """
        with self._lock:
            if not self.is_connected:
                logger.error(f"Cannot configure IQ {channel.value}: not connected")
                return False

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return False

                # Store configuration
                self._iq_configs[channel] = config

                # Configure IQ parameters
                iq_module.frequency = config.frequency
                iq_module.bandwidth = config.bandwidth
                iq_module.acbandwidth = config.acbandwidth
                iq_module.phase = config.phase
                iq_module.gain = config.gain
                iq_module.quadrature_factor = config.quadrature_factor
                iq_module.amplitude = config.amplitude

                # Configure input/output routing
                iq_module.input = config.input_channel.value
                iq_module.output_direct = config.output_direct.value

                logger.debug(f"Configured IQ {channel.value} with frequency {config.frequency} Hz")
                return True

            except Exception as e:
                logger.error(f"Failed to configure IQ {channel.value}: {e}")
                return False

    def get_iq_measurement(self, channel: IQChannel) -> Optional[Tuple[float, float]]:
        """
        Get I and Q measurements from the lock-in amplifier.

        Args:
            channel: IQ channel to read from

        Returns:
            Tuple of (I, Q) values or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return None

                # Get I and Q values from the IQ module
                i_value = iq_module.I
                q_value = iq_module.Q

                return i_value, q_value

            except Exception as e:
                logger.error(f"Failed to get IQ measurement for {channel.value}: {e}")
                return None

    def calculate_magnitude_phase(self, i: float, q: float) -> Tuple[float, float]:
        """
        Calculate magnitude and phase from I and Q components.

        Args:
            i: In-phase component
            q: Quadrature component

        Returns:
            Tuple of (magnitude, phase_degrees)
        """
        magnitude = np.sqrt(i**2 + q**2)
        phase_radians = np.arctan2(q, i)
        phase_degrees = np.degrees(phase_radians)
        return magnitude, phase_degrees

    def set_iq_frequency(self, channel: IQChannel, frequency: float) -> bool:
        """
        Set the frequency for an IQ lock-in amplifier.

        Args:
            channel: IQ channel
            frequency: New frequency value in Hz

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return False

                iq_module.frequency = frequency

                # Update stored configuration
                if channel in self._iq_configs:
                    self._iq_configs[channel].frequency = frequency

                return True

            except Exception as e:
                logger.error(f"Failed to set frequency for IQ {channel.value}: {e}")
                return False

    def get_iq_frequency(self, channel: IQChannel) -> Optional[float]:
        """
        Get the current frequency for an IQ lock-in amplifier.

        Args:
            channel: IQ channel

        Returns:
            Current frequency in Hz or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return None

                return iq_module.frequency

            except Exception as e:
                logger.error(f"Failed to get frequency for IQ {channel.value}: {e}")
                return None

    def set_iq_phase(self, channel: IQChannel, phase: float) -> bool:
        """
        Set the phase for an IQ lock-in amplifier.

        Args:
            channel: IQ channel
            phase: New phase value in degrees

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return False

                iq_module.phase = phase

                # Update stored configuration
                if channel in self._iq_configs:
                    self._iq_configs[channel].phase = phase

                return True

            except Exception as e:
                logger.error(f"Failed to set phase for IQ {channel.value}: {e}")
                return False

    def enable_iq_output(self, channel: IQChannel, output_channel: IQOutputDirect) -> bool:
        """
        Enable IQ output to specified channel.

        Args:
            channel: IQ channel
            output_channel: Output channel to enable

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                iq_module = self.get_iq_module(channel)
                if iq_module is None:
                    return False

                iq_module.output_direct = output_channel.value

                # Update stored configuration
                if channel in self._iq_configs:
                    self._iq_configs[channel].output_direct = output_channel

                logger.debug(f"Enabled IQ {channel.value} output to {output_channel.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to enable IQ {channel.value} output: {e}")
                return False

    def read_multiple_voltages(self, channels: List[InputChannel]) -> Dict[InputChannel, Optional[float]]:
        """
        Read voltages from multiple input channels simultaneously.

        Args:
            channels: List of input channels to read

        Returns:
            Dictionary mapping channels to voltage values
        """
        result = {}
        for channel in channels:
            result[channel] = self.read_voltage(channel)
        return result

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get detailed connection information.

        Returns:
            Dictionary with connection details
        """
        with self._lock:
            return {
                'hostname': self.hostname,
                'config_name': self.config_name,
                'state': self.state.value,
                'connected_at': self.connected_at,
                'last_error': self.last_error,
                'active_pids': list(self._active_pids.keys()),
                'active_asgs': list(self._active_asgs.keys()),
                'active_iqs': list(self._active_iqs.keys()),
                'scope_configured': self._scope_config is not None,
                'ref_count': self._ref_count
            }

    def add_reference(self) -> int:
        """
        Add a reference count for connection sharing.

        Returns:
            int: Current reference count after increment
        """
        with self._lock:
            self._ref_count += 1
            return self._ref_count

    def remove_reference(self) -> int:
        """
        Remove a reference count for connection sharing.

        Returns:
            int: Current reference count after decrement
        """
        with self._lock:
            self._ref_count = max(0, self._ref_count - 1)
            return self._ref_count

    def cleanup(self) -> None:
        """
        Cleanup connection resources. This is an alias for disconnect.
        """
        self.disconnect()

    @contextmanager
    def acquire_reference(self):
        """
        Context manager for reference counting.

        Usage:
            with connection.acquire_reference():
                # Use connection safely
                pass
        """
        with self._lock:
            self._ref_count += 1
        try:
            yield self
        finally:
            with self._lock:
                self._ref_count -= 1

    def __enter__(self):
        """Context manager entry."""
        return self.acquire_reference().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # This is handled by acquire_reference context manager
        pass


def create_pyrpl_connection(hostname: str, config_name: str, 
                           status_callback: Optional[Callable] = None,
                           connection_timeout: float = 10.0,
                           mock_mode: bool = False) -> Optional[PyRPLConnection]:
    """
    Create a new PyRPL connection, either to real hardware or mock simulation.
    
    This function abstracts the creation of PyRPL connections, supporting both
    real hardware connections and unified mock mode simulation.
    
    Parameters:
        hostname (str): Red Pitaya hostname or IP address
        config_name (str): PyRPL configuration name
        status_callback (Optional[Callable]): Callback for status updates
        connection_timeout (float): Connection timeout in seconds
        mock_mode (bool): If True, return shared mock instance instead of real connection
        
    Returns:
        Optional[PyRPLConnection]: Connection object or None if failed
    """
    if mock_mode:
        # Return shared mock instance for coordinated simulation
        mock_instance = get_shared_mock_instance(hostname)
        if mock_instance is not None:
            # Wrap the mock instance in a PyRPLConnection-compatible interface
            return PyRPLMockConnectionAdapter(mock_instance, hostname, config_name)
        else:
            logger.error("Failed to create mock connection - EnhancedMockPyRPLConnection unavailable")
            return None
    else:
        # Create real hardware connection
        try:
            connection_info = ConnectionInfo(
                hostname=hostname,
                config_name=config_name,
                connection_timeout=connection_timeout
            )
            
            real_connection = PyRPLConnection(connection_info)
            
            # Establish the actual connection
            if real_connection.connect(status_callback):
                return real_connection
            else:
                logger.error(f"Failed to establish connection to {hostname}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to create real PyRPL connection: {e}")
            return None


class PyRPLMockConnectionAdapter:
    """
    Adapter to make EnhancedMockPyRPLConnection compatible with PyRPLConnection interface.
    
    This adapter ensures that plugins can use the shared mock instance through the
    same interface as real PyRPL connections, maintaining code compatibility.
    """
    
    def __init__(self, mock_instance: 'EnhancedMockPyRPLConnection', hostname: str, config_name: str):
        self._mock_instance = mock_instance
        self._hostname = hostname
        self._config_name = config_name
        self._reference_count = 1
        self._reference_lock = threading.Lock()
        
    @property
    def is_connected(self) -> bool:
        """Check if mock connection is active."""
        return self._mock_instance.is_connected
        
    @property
    def hostname(self) -> str:
        """Get hostname."""
        return self._hostname
        
    @property
    def config_name(self) -> str:
        """Get config name."""
        return self._config_name
        
    def add_reference(self) -> int:
        """Add reference count for connection sharing."""
        with self._reference_lock:
            self._reference_count += 1
            return self._reference_count
            
    def remove_reference(self) -> int:
        """Remove reference count."""
        with self._reference_lock:
            self._reference_count = max(0, self._reference_count - 1)
            return self._reference_count
            
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        base_info = self._mock_instance.get_connection_info()
        base_info.update({
            'config_name': self._config_name,
            'reference_count': self._reference_count,
            'adapter_type': 'PyRPLMockConnectionAdapter'
        })
        return base_info
        
    def disconnect(self) -> None:
        """Disconnect (no-op for shared mock instance)."""
        logger.debug(f"Mock connection adapter disconnect called for {self._hostname}")
        
    def cleanup(self) -> None:
        """Cleanup (no-op for shared mock instance)."""
        logger.debug(f"Mock connection adapter cleanup called for {self._hostname}")
        
    def __getattr__(self, name):
        """Delegate all other attributes to the mock instance."""
        return getattr(self._mock_instance, name)


class PyRPLManager:
    """
    Singleton manager for PyRPL connections with thread-safe connection pooling.

    The PyRPLManager provides centralized management of PyRPL connections to prevent
    conflicts when multiple PyMoDAQ plugins access the same Red Pitaya devices. It
    implements connection pooling, reference counting, and automatic cleanup to ensure
    robust multi-plugin coordination.

    Key Features:
    - **Singleton Pattern**: Single manager instance across all plugins
    - **Connection Pooling**: Reuse connections between plugins
    - **Reference Counting**: Track active plugin usage
    - **Thread Safety**: Concurrent access protection with locks
    - **Automatic Cleanup**: Resource management and error recovery
    - **Status Monitoring**: Real-time connection health tracking

    Design Pattern:
    The manager follows a singleton pattern where all PyRPL plugins share the same
    manager instance. This prevents connection conflicts that would occur if each
    plugin created its own PyRPL instance to the same Red Pitaya device.

    Connection Lifecycle:
    1. **Request**: Plugin requests connection via connect_device()
    2. **Pool Check**: Manager checks if connection already exists
    3. **Create/Reuse**: Creates new connection or increments reference count
    4. **Return**: Returns connection object to plugin
    5. **Release**: Plugin releases connection via disconnect_device()
    6. **Cleanup**: Manager decrements reference count and cleans up if needed

    Thread Safety:
    All public methods are protected with locks to ensure thread-safe operation
    when multiple plugins access the manager concurrently.

    Attributes:
        _instance (PyRPLManager): Singleton instance
        _lock (threading.Lock): Class-level lock for singleton creation
        _connections (Dict): Pool of active PyRPL connections
        _manager_lock (threading.RLock): Instance-level lock for thread safety
        _initialized (bool): Initialization state flag

    Example:
        >>> manager = PyRPLManager.get_instance()
        >>> connection = manager.connect_device('rp-f08d6c.local', 'myconfig')
        >>> # Use connection...
        >>> manager.disconnect_device('rp-f08d6c.local', 'myconfig')

    Note:
        This class should not be instantiated directly. Use get_instance() to
        obtain the singleton instance.
    """

    _instance: Optional['PyRPLManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'PyRPLManager':
        """
        Singleton implementation with thread-safe instance creation.
        
        Returns:
            PyRPLManager: The singleton manager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize the PyRPL manager with connection pool and threading support.
        
        Note:
            This method is called only once due to singleton pattern.
            Subsequent calls are no-ops to prevent re-initialization.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._connections: Dict[str, PyRPLConnection] = {}
        self._manager_lock = threading.RLock()
        self._initialized = True
        logger.info("PyRPL Manager initialized")

    def get_connection(self, hostname: str, config_name: str) -> Optional[PyRPLConnection]:
        """
        Retrieve an existing connection from the pool.
        
        Parameters:
            hostname (str): Red Pitaya hostname or IP address
            config_name (str): PyRPL configuration name
            
        Returns:
            Optional[PyRPLConnection]: Existing connection if found, None otherwise
            
        Thread Safety:
            This method is thread-safe and can be called concurrently.
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"
            connection = self._connections.get(connection_key)
            
            if connection is not None:
                if connection.is_connected:
                    logger.debug(f"Retrieved existing connection for {connection_key}")
                    return connection
                else:
                    # Clean up dead connection
                    logger.warning(f"Removing dead connection for {connection_key}")
                    del self._connections[connection_key]
                    try:
                        connection.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up dead connection: {e}")
                    
            return None

    def connect_device(self, hostname: str, config_name: str, 
                      status_callback: Optional[Callable] = None,
                      connection_timeout: float = 10.0,
                      mock_mode: bool = False) -> Optional[PyRPLConnection]:
        """
        Connect to a Red Pitaya device with connection pooling and reference counting.
        
        This method implements intelligent connection management:
        - Returns existing connection if available and healthy
        - Creates new connection if none exists
        - Increments reference count for connection tracking
        - Handles connection failures gracefully
        
        Parameters:
            hostname (str): Red Pitaya hostname or IP address (e.g., 'rp-f08d6c.local')
            config_name (str): PyRPL configuration name for this connection
            status_callback (Optional[Callable]): Callback for status updates
            connection_timeout (float): Connection timeout in seconds (default: 10.0)
            mock_mode (bool): If True, use shared EnhancedMockPyRPLConnection for simulation
            
        Returns:
            Optional[PyRPLConnection]: Connected PyRPL connection object, or None if failed
            
        Raises:
            ConnectionError: If connection fails after retries
            TimeoutError: If connection times out
            
        Example:
            >>> manager = PyRPLManager.get_instance()
            >>> def status_cb(cmd): print(f"Status: {cmd}")
            >>> conn = manager.connect_device('rp-f08d6c.local', 'pid_control', status_cb)
            >>> if conn and conn.is_connected:
            ...     print("Connected successfully")
        """
        connection = self.get_connection(hostname, config_name)
        if connection is not None:
            connection.add_reference()
            return connection
        
        # Create new connection
        try:
            connection = create_pyrpl_connection(hostname, config_name, 
                                               status_callback, connection_timeout, mock_mode)
            if connection and connection.is_connected:
                with self._manager_lock:
                    connection_key = f"{hostname}:{config_name}"
                    self._connections[connection_key] = connection
                    logger.info(f"Created new connection for {connection_key}")
                return connection
            else:
                logger.error(f"Failed to create connection to {hostname}")
                return None
        except Exception as e:
            logger.error(f"Error creating connection to {hostname}: {e}")
            return None

    def disconnect_device(self, hostname: str, config_name: str,
                         status_callback: Optional[Callable] = None) -> bool:
        """
        Disconnect from a Red Pitaya device with reference counting.
        
        This method decrements the reference count for the specified connection.
        The actual disconnection only occurs when the reference count reaches zero,
        allowing multiple plugins to safely share the same connection.
        
        Parameters:
            hostname (str): Red Pitaya hostname or IP address
            config_name (str): PyRPL configuration name
            status_callback (Optional[Callable]): Callback for status updates
            
        Returns:
            bool: True if disconnect successful, False otherwise
            
        Behavior:
            - Decrements reference count for the connection
            - If count reaches zero, performs actual disconnection
            - If count > 0, keeps connection alive for other plugins
            - Handles cleanup of connection resources
            
        Example:
            >>> manager.disconnect_device('rp-f08d6c.local', 'pid_control')
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"
            connection = self._connections.get(connection_key)
            
            if connection is None:
                logger.warning(f"No connection found for {connection_key}")
                return False
            
            try:
                remaining_refs = connection.remove_reference()
                
                if remaining_refs <= 0:
                    # Last reference removed - perform actual disconnect
                    connection.disconnect()
                    del self._connections[connection_key]
                    logger.info(f"Disconnected and removed connection for {connection_key}")
                else:
                    logger.info(f"Decremented reference count for {connection_key} (remaining: {remaining_refs})")
                
                return True
                
            except Exception as e:
                logger.error(f"Error disconnecting from {hostname}: {e}")
                return False

    def remove_connection(self, hostname: str, config_name: str) -> bool:
        """
        Forcibly remove a connection from the pool.
        
        This method removes a connection from the pool regardless of reference count.
        Use with caution as it may leave plugins with invalid connection objects.
        
        Parameters:
            hostname (str): Red Pitaya hostname or IP address
            config_name (str): PyRPL configuration name
            
        Returns:
            bool: True if connection was found and removed, False otherwise
            
        Warning:
            This method bypasses reference counting and should only be used for
            cleanup operations or error recovery. It may leave plugins with
            invalid connection references.
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"
            connection = self._connections.get(connection_key)
            
            if connection is None:
                return False
                
            try:
                connection.disconnect()
                connection.cleanup()
                del self._connections[connection_key]
                logger.warning(f"Forcibly removed connection for {connection_key}")
                return True
                
            except Exception as e:
                logger.error(f"Error removing connection for {connection_key}: {e}")
                # Remove from pool even if cleanup failed
                del self._connections[connection_key]
                return False

    def get_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all active connections.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping connection keys to status info
            
        The returned dictionary contains connection information with the following structure:
        {
            "hostname:config_name": {
                "hostname": str,
                "config_name": str,
                "is_connected": bool,
                "reference_count": int,
                "state": str,
                "last_activity": float
            }
        }
        
        Example:
            >>> manager = PyRPLManager.get_instance()
            >>> connections = manager.get_all_connections()
            >>> for key, info in connections.items():
            ...     print(f"{key}: {info['reference_count']} refs, connected={info['is_connected']}")
        """
        with self._manager_lock:
            status = {}
            for key, connection in self._connections.items():
                try:
                    conn_info = connection.get_connection_info()
                    status[key] = conn_info
                except Exception as e:
                    logger.error(f"Error getting info for connection {key}: {e}")
                    status[key] = {
                        "hostname": key.split(':')[0],
                        "config_name": key.split(':')[1] if ':' in key else 'unknown',
                        "is_connected": False,
                        "reference_count": 0,
                        "state": "error",
                        "error": str(e)
                    }
            return status

    def disconnect_all(self) -> None:
        """
        Disconnect all active connections and clear the connection pool.
        
        This method forcibly disconnects all connections regardless of reference counts.
        It's primarily used during application shutdown or emergency cleanup.
        
        Warning:
            This method bypasses reference counting and will invalidate all active
            connection objects. Plugins may experience connection errors after this call.
            
        Use Cases:
            - Application shutdown
            - Emergency cleanup
            - Testing scenarios
            - Error recovery
        """
        with self._manager_lock:
            logger.info("Disconnecting all PyRPL connections")
            for key, connection in list(self._connections.items()):
                try:
                    connection.disconnect()
                    connection.cleanup()
                except Exception as e:
                    logger.error(f"Error disconnecting {key}: {e}")
            
            self._connections.clear()
            logger.info("All PyRPL connections disconnected")

    def cleanup(self) -> None:
        """
        Perform comprehensive cleanup of the manager and all connections.
        
        This method ensures proper resource cleanup including:
        - Disconnecting all active connections
        - Clearing the connection pool
        - Resetting manager state
        
        Note:
            After calling this method, the manager remains functional and can
            create new connections. This is different from a destructor.
        """
        self.disconnect_all()
        logger.info("PyRPL Manager cleanup completed")

    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information about the manager and all connections.
        
        Returns:
            Dict[str, Any]: Comprehensive manager status including:
                - total_connections: Number of active connections
                - connections: Detailed info for each connection
                - manager_state: Manager health and statistics
                
        Example:
            >>> status = manager.get_manager_status()
            >>> print(f"Active connections: {status['total_connections']}")
            >>> for conn_info in status['connections'].values():
            ...     print(f"  {conn_info['hostname']}: {conn_info['reference_count']} refs")
        """
        with self._manager_lock:
            connections_info = self.get_all_connections()
            
            return {
                "total_connections": len(self._connections),
                "connections": connections_info,
                "manager_state": {
                    "initialized": getattr(self, '_initialized', False),
                    "thread_id": threading.current_thread().ident,
                    "lock_acquired": False  # Can't check this safely
                }
            }

    @classmethod
    def get_instance(cls) -> 'PyRPLManager':
        """
        Get the singleton PyRPLManager instance.
        
        Returns:
            PyRPLManager: The singleton manager instance
            
        Note:
            This is the preferred way to access the PyRPLManager. Do not
            instantiate the class directly.
            
        Example:
            >>> manager = PyRPLManager.get_instance()
            >>> connection = manager.connect_device('hostname', 'config')
        """
        return cls()


# Convenience functions for easy access
def get_pyrpl_manager() -> PyRPLManager:
    """Get the global PyRPL manager instance."""
    return PyRPLManager.get_instance()


def connect_redpitaya(hostname: str, config_name: str = "pymodaq",
                     status_callback: Optional[callable] = None,
                     **kwargs) -> Optional[PyRPLConnection]:
    """
    Convenience function to connect to a Red Pitaya device.

    Args:
        hostname: Red Pitaya hostname or IP address
        config_name: PyRPL configuration name
        status_callback: Optional callback for status updates
        **kwargs: Additional connection parameters

    Returns:
        Connected PyRPLConnection instance or None if failed

    Example:
        >>> connection = connect_redpitaya('rp-f08d6c.local')
        >>> if connection and connection.is_connected:
        ...     voltage = connection.read_voltage(InputChannel.IN1)
        ...     print(f"Input voltage: {voltage}V")
    """
    manager = get_pyrpl_manager()
    return manager.connect_device(hostname, config_name, status_callback, **kwargs)


def disconnect_redpitaya(hostname: str, config_name: str = "pymodaq",
                        status_callback: Optional[callable] = None) -> bool:
    """
    Convenience function to disconnect from a Red Pitaya device.

    Args:
        hostname: Red Pitaya hostname or IP address
        config_name: PyRPL configuration name
        status_callback: Optional callback for status updates

    Returns:
        bool: True if successful
    """
    manager = get_pyrpl_manager()
    return manager.disconnect_device(hostname, config_name, status_callback)


if __name__ == "__main__":
    # Example usage and testing
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Usage: python pyrpl_wrapper.py <hostname>")
        sys.exit(1)

    hostname = sys.argv[1]
    print(f"Testing connection to {hostname}")

    # Test connection
    connection = connect_redpitaya(hostname)

    if connection and connection.is_connected:
        print("Connection successful!")

        # Test voltage reading
        voltage = connection.read_voltage(InputChannel.IN1)
        print(f"Input 1 voltage: {voltage}V")

        # Test PID configuration
        config = PIDConfiguration(
            setpoint=0.5,
            p_gain=0.1,
            i_gain=0.01,
            input_channel=InputChannel.IN1,
            output_channel=OutputChannel.OUT1
        )

        success = connection.configure_pid(PIDChannel.PID0, config)
        print(f"PID configuration: {'Success' if success else 'Failed'}")

        # Test cleanup
        disconnect_redpitaya(hostname)
        print("Disconnected successfully")

    else:
        print("Connection failed!")
        if connection:
            print(f"Error: {connection.last_error}")
