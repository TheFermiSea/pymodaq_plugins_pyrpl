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

import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Optional, Union, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from qtpy.QtCore import QObject, Signal

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
    # NOTE: With gui=False in Pyrpl(), this patch should not be needed
    # Kept as a safeguard for edge cases, but made non-recursive
    try:
        from qtpy.QtCore import QTimer
        if not hasattr(QTimer, '_pymodaq_pyrpl_patched'):
            original_setInterval = QTimer.setInterval

            def setInterval_patched(self, msec):
                """Patched setInterval to handle float inputs properly."""
                try:
                    return original_setInterval(self, int(msec))
                except (ValueError, TypeError) as e:
                    logger.warning(f"QTimer.setInterval called with invalid value {msec}: {e}")
                    return original_setInterval(self, 1000)  # fallback to 1 second

            QTimer.setInterval = setInterval_patched
            QTimer._pymodaq_pyrpl_patched = True  # Mark as patched to prevent re-patching
    except ImportError:
        pass  # Qt not available, skip timer patch

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
            import pyrpl as pyrpl_module
            from pyrpl.hardware_modules.pid import Pid as PidModule_imported
            
            pyrpl = pyrpl_module
            PidModule = PidModule_imported
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
    
    def _lazy_import_pyrpl():
        return False

from pymodaq_utils.utils import ThreadCommand


logger = logging.getLogger(__name__)


ENHANCED_MOCK_AVAILABLE: Optional[bool] = None
EnhancedMockPyRPLConnection = None  # type: ignore[assignment]
create_enhanced_mock_connection = None  # type: ignore[assignment]


def _ensure_enhanced_mock_loaded() -> bool:
    """Lazy import for enhanced mock connection support."""

    global ENHANCED_MOCK_AVAILABLE, EnhancedMockPyRPLConnection, create_enhanced_mock_connection

    if ENHANCED_MOCK_AVAILABLE is not None:
        return ENHANCED_MOCK_AVAILABLE

    try:
        from .enhanced_mock_connection import (  # type: ignore
            EnhancedMockPyRPLConnection as _EnhancedMockPyRPLConnection,
            create_enhanced_mock_connection as _create_enhanced_mock_connection,
        )

        EnhancedMockPyRPLConnection = _EnhancedMockPyRPLConnection
        create_enhanced_mock_connection = _create_enhanced_mock_connection
        ENHANCED_MOCK_AVAILABLE = True
        logger.info("Enhanced mock connection support available")
    except Exception as exc:  # noqa: BLE001 - optional dependency
        ENHANCED_MOCK_AVAILABLE = False
        EnhancedMockPyRPLConnection = None
        create_enhanced_mock_connection = None
        logger.warning("Enhanced mock connection unavailable: %s", exc)

    return ENHANCED_MOCK_AVAILABLE


_shared_mock_lock = threading.Lock()
_shared_mock_instance = None
_shared_mock_hostname: Optional[str] = None


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


class PyRPLMockConnectionAdapter:
    """Adapter exposing mock connections with PyRPLConnection-like interface."""

    def __init__(self, mock_instance: Any, hostname: str, config_name: str):
        self._mock_instance = mock_instance
        self.hostname = hostname
        self.config_name = config_name
        self.is_mock = True
        self.is_connected = True
        self._reference_count = 1

    def add_reference(self) -> int:
        self._reference_count += 1
        return self._reference_count

    def remove_reference(self) -> int:
        if self._reference_count > 0:
            self._reference_count -= 1
        return self._reference_count

    def disconnect(self, status_callback: Optional[callable] = None) -> None:
        remaining = self.remove_reference()
        if remaining <= 0:
            self.is_connected = False
            if hasattr(self._mock_instance, "disconnect"):
                try:
                    self._mock_instance.disconnect(status_callback)
                except Exception as exc:  # noqa: BLE001 - best effort cleanup
                    logger.debug("Mock disconnect raised: %s", exc)

    def get_connection_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "hostname": self.hostname,
            "config_name": self.config_name,
            "adapter_type": "PyRPLMockConnectionAdapter",
            "reference_count": self._reference_count,
            "is_mock": True,
            "is_connected": self.is_connected,
        }
        if hasattr(self._mock_instance, "get_connection_info"):
            try:
                mock_info = self._mock_instance.get_connection_info()
                if isinstance(mock_info, dict):
                    info.update(mock_info)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to retrieve mock connection info: %s", exc)
        return info

    def __getattr__(self, item: str) -> Any:
        return getattr(self._mock_instance, item)


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

    def connect(self, status_callback: Optional[callable] = None) -> bool:
        """
        Establish connection to Red Pitaya.

        Args:
            status_callback: Optional callback for status updates

        Returns:
            bool: True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self.is_connected:
                logger.debug(f"Already connected to {self.hostname}")
                return True

            self.state = ConnectionState.CONNECTING
            self.last_error = None

            if status_callback:
                status_callback(ThreadCommand('Update_Status',
                    [f"Connecting to Red Pitaya at {self.hostname}", 'log']))

            # Lazy import PyRPL if not already done
            if not _lazy_import_pyrpl():
                error_msg = "PyRPL is not available - cannot establish connection"
                logger.error(error_msg)
                self.state = ConnectionState.ERROR
                self.last_error = error_msg
                return False

            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Connection attempt {attempt + 1}/{self.retry_attempts} to {self.hostname}")

                    # Create PyRPL connection
                    # CRITICAL: gui=False prevents Qt widget creation in PyMoDAQ worker threads
                    # This avoids thread recursion errors when PyRPL's Qt objects run in non-main threads
                    self._pyrpl = pyrpl.Pyrpl(
                        config=self.config_name,
                        hostname=self.hostname,
                        port=self.port,
                        timeout=self.connection_timeout,
                        gui=False  # Disable GUI to prevent Qt threading conflicts
                    )

                    self._redpitaya = self._pyrpl.rp

                    # Connection is successful if we reach this point
                    # Skip version check due to PyRPL compatibility issues
                    logger.debug(f"PyRPL connection established to {self.hostname}")

                    self.state = ConnectionState.CONNECTED
                    self.connected_at = time.time()
                    self.last_error = None

                    logger.info(f"Successfully connected to Red Pitaya {self.hostname}")

                    if status_callback:
                        status_callback(ThreadCommand('Update_Status',
                            [f"Red Pitaya {self.hostname} connected", 'log']))

                    return True

                except ZeroDivisionError as e:
                    # PyRPL sometimes has division by zero errors during module loading
                    # but the connection itself is successful, so ignore these
                    logger.debug(f"Ignoring PyRPL ZeroDivisionError: {e}")
                    if self._pyrpl and self._redpitaya:
                        logger.info(f"PyRPL connection successful despite ZeroDivisionError")
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True
                    # If no connection objects, treat as real error
                    error_msg = f"Connection attempt {attempt + 1} failed: {str(e)}"
                    logger.warning(error_msg)
                    self.last_error = str(e)

                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

                except Exception as e:
                    # Check if this is a PyRPL-related error that we can ignore
                    error_str = str(e)
                    if "float division by zero" in error_str and self._pyrpl and self._redpitaya:
                        logger.info(f"PyRPL connection successful despite error: {error_str}")
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True

                    error_msg = f"Connection attempt {attempt + 1} failed: {error_str}"
                    logger.warning(error_msg)
                    self.last_error = error_str

                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

            # All attempts failed
            self.state = ConnectionState.ERROR
            error_msg = f"Failed to connect to {self.hostname} after {self.retry_attempts} attempts"
            logger.error(error_msg)

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

        CRITICAL: Always retrieves fresh reference to avoid Qt metaobject recursion.
        Do NOT cache as it's a QObject.

        Args:
            channel: PID channel to retrieve

        Returns:
            PidModule or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # CRITICAL: Get fresh reference each time
                # Caching QObjects causes Qt metaobject recursion
                return getattr(self._redpitaya, channel.value)

            except Exception as e:
                logger.error(f"Failed to get PID module {channel.value}: {e}")
                return None

    def configure_pid(self, channel: PIDChannel, config: PIDConfiguration) -> bool:
        """
        Configure a PID controller with the specified parameters.

        Args:
            channel: PID channel to configure
            config: PID configuration parameters

        Returns:
            bool: True if configuration successful
        """
        with self._lock:
            if not self.is_connected:
                logger.error(f"Cannot configure PID {channel.value}: not connected")
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                # Store configuration
                self._pid_configs[channel] = config

                # Configure PID parameters
                pid_module.setpoint = config.setpoint
                pid_module.p = config.p_gain
                pid_module.i = config.i_gain
                pid_module.d = config.d_gain

                # Configure input/output routing
                pid_module.input = config.input_channel.value
                if config.enabled:
                    pid_module.output_direct = config.output_channel.value
                else:
                    pid_module.output_direct = 'off'

                # Set voltage limits
                pid_module.max_voltage = config.voltage_limit_max
                pid_module.min_voltage = config.voltage_limit_min

                logger.debug(f"Configured PID {channel.value} with setpoint {config.setpoint}")
                return True

            except Exception as e:
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

        CRITICAL: Always retrieves fresh reference to avoid Qt metaobject recursion.
        Do NOT cache as it's a QObject.

        Args:
            channel: ASG channel to retrieve

        Returns:
            ASG module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # CRITICAL: Get fresh reference each time
                # Caching QObjects causes Qt metaobject recursion
                return getattr(self._redpitaya, channel.value)

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

        CRITICAL: Always retrieves fresh reference to avoid Qt metaobject recursion.
        Do NOT cache the scope object as it's a QObject that triggers Qt introspection
        when accessed from worker threads.

        Returns:
            Scope module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # CRITICAL: Get fresh reference each time, do NOT cache
                # Caching QObjects causes Qt metaobject recursion in worker threads
                return self._redpitaya.scope

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

                # Acquire data (curve() handles trigger and wait internally)
                voltage_data = scope.curve(timeout=acq_timeout)

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

        CRITICAL: Always retrieves fresh reference to avoid Qt metaobject recursion.
        Do NOT cache as it's a QObject.

        Args:
            channel: IQ channel to retrieve

        Returns:
            IQ module or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # CRITICAL: Get fresh reference each time
                # Caching QObjects causes Qt metaobject recursion
                return getattr(self._redpitaya, channel.value)

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


class PyRPLManager(QObject):
    """
    Singleton manager for PyRPL connections.

    Provides centralized connection pooling to prevent conflicts between
    multiple PyMoDAQ plugins accessing the same Red Pitaya devices.
    """

    status_updated = Signal(dict)
    _instance: Optional['PyRPLManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'PyRPLManager':
        """Singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager (called only once due to singleton)."""
        if self._initialized:
            return

        super().__init__()
        self._connections: Dict[str, PyRPLConnection] = {}
        self._mock_connections: Dict[str, PyRPLMockConnectionAdapter] = {}
        self._manager_lock = threading.RLock()
        self._initialized = True

        logger.info("PyRPL Manager initialized")

    def get_connection(self, hostname: str, config_name: str = "pymodaq",
                      **connection_kwargs) -> Optional[PyRPLConnection]:
        """
        Get or create a connection to a Red Pitaya device.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name
            **connection_kwargs: Additional connection parameters

        Returns:
            PyRPLConnection instance or None if creation failed
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key in self._connections:
                connection = self._connections[connection_key]
                logger.debug(f"Returning existing connection to {hostname}")
                return connection

            # Create new connection
            connection_info = ConnectionInfo(
                hostname=hostname,
                config_name=config_name,
                **connection_kwargs
            )

            try:
                connection = PyRPLConnection(connection_info)
                self._connections[connection_key] = connection
                logger.info(f"Created new connection to {hostname}")
                return connection

            except Exception as e:
                logger.error(f"Failed to create connection to {hostname}: {e}")
                return None

    def connect_device(self, hostname: str, config_name: str = "pymodaq",
                      status_callback: Optional[callable] = None,
                      **connection_kwargs) -> Optional[PyRPLConnection]:
        """
        Connect to a Red Pitaya device.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name
            status_callback: Optional callback for status updates
            **connection_kwargs: Additional connection parameters

        Returns:
            Connected PyRPLConnection instance or None if failed
        """
        mock_mode = connection_kwargs.pop("mock_mode", False)

        if mock_mode:
            return self._connect_mock_device(
                hostname, config_name, status_callback=status_callback, **connection_kwargs
            )

        connection_key = f"{hostname}:{config_name}"
        connection = self.get_connection(hostname, config_name, **connection_kwargs)

        if connection is None:
            self.status_updated.emit(self.get_manager_status())
            return None

        if connection.connect(status_callback):
            self.status_updated.emit(self.get_manager_status())
            return connection

        with self._manager_lock:
            self._connections.pop(connection_key, None)

        self.status_updated.emit(self.get_manager_status())
        return None

    def _connect_mock_device(
        self,
        hostname: str,
        config_name: str,
        status_callback: Optional[callable] = None,
        **_: Any,
    ) -> Optional[PyRPLMockConnectionAdapter]:
        if not _ensure_enhanced_mock_loaded():
            logger.error("Mock mode requested but enhanced mock support unavailable")
            return None

        mock_instance = get_shared_mock_instance(hostname)
        if mock_instance is None:
            logger.error("Failed to create shared mock instance for %s", hostname)
            return None

        connection_key = f"{hostname}:{config_name}"

        with self._manager_lock:
            adapter = self._mock_connections.get(connection_key)
            if adapter is None:
                adapter = PyRPLMockConnectionAdapter(mock_instance, hostname, config_name)
                self._mock_connections[connection_key] = adapter
            else:
                adapter.add_reference()

        if status_callback:
            try:
                status_callback(ThreadCommand("Update_Status", [f"Connected to mock {hostname}", "log"]))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Status callback for mock connection failed: %s", exc)

        self.status_updated.emit(self.get_manager_status())
        return adapter

    def disconnect_device(self, hostname: str, config_name: str = "pymodaq",
                         status_callback: Optional[callable] = None) -> bool:
        """
        Disconnect from a Red Pitaya device.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name
            status_callback: Optional callback for status updates

        Returns:
            bool: True if successful
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key in self._mock_connections:
                adapter = self._mock_connections[connection_key]
                adapter.disconnect(status_callback)
                if adapter._reference_count <= 0:
                    del self._mock_connections[connection_key]
                self.status_updated.emit(self.get_manager_status())
                return True

            if connection_key not in self._connections:
                self.status_updated.emit(self.get_manager_status())
                return True  # Already disconnected

            connection = self._connections[connection_key]

            # Check if connection is still in use
            if connection._ref_count > 0:
                logger.warning(f"Connection {hostname} still has active references, disconnecting anyway")

            connection.disconnect(status_callback)
            self.status_updated.emit(self.get_manager_status())
            return True

    def remove_connection(self, hostname: str, config_name: str = "pymodaq") -> bool:
        """
        Remove a connection from the manager.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name

        Returns:
            bool: True if removed successfully
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key in self._mock_connections:
                adapter = self._mock_connections.pop(connection_key)
                adapter.disconnect()
                self.status_updated.emit(self.get_manager_status())
                return True

            if connection_key in self._connections:
                connection = self._connections[connection_key]

                # Ensure connection is disconnected
                if connection.is_connected:
                    connection.disconnect()

                del self._connections[connection_key]
                logger.info(f"Removed connection to {hostname}")
                self.status_updated.emit(self.get_manager_status())
                return True

            self.status_updated.emit(self.get_manager_status())
            return False

    def get_all_connections(self) -> Dict[str, Any]:
        """
        Get all active connections.

        Returns:
            Dictionary mapping connection keys to PyRPLConnection instances
        """
        with self._manager_lock:
            combined: Dict[str, Any] = {}
            combined.update(self._connections)
            combined.update(self._mock_connections)
            return combined

    def disconnect_all(self, status_callback: Optional[callable] = None) -> None:
        """
        Disconnect all active connections.

        Args:
            status_callback: Optional callback for status updates
        """
        with self._manager_lock:
            for connection_key, connection in list(self._connections.items()):
                try:
                    connection.disconnect(status_callback)
                except Exception as e:
                    logger.error(f"Error disconnecting {connection_key}: {e}")

            for connection_key, adapter in list(self._mock_connections.items()):
                try:
                    adapter.disconnect(status_callback)
                except Exception as e:
                    logger.error(f"Error disconnecting mock {connection_key}: {e}")
                finally:
                    if adapter._reference_count <= 0:
                        self._mock_connections.pop(connection_key, None)

    def cleanup(self) -> None:
        """
        Clean up all connections and resources.
        """
        logger.info("Cleaning up PyRPL Manager")
        self.disconnect_all()

        with self._manager_lock:
            self._connections.clear()
            self._mock_connections.clear()

    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get detailed manager status.

        Returns:
            Dictionary with manager status information
        """
        with self._manager_lock:
            connections_info = {}
            for key, conn in self._connections.items():
                connections_info[key] = conn.get_connection_info()
            for key, adapter in self._mock_connections.items():
                connections_info[f"mock::{key}"] = adapter.get_connection_info()

            return {
                'total_connections': len(self._connections) + len(self._mock_connections),
                'connections': connections_info
            }

    @classmethod
    def get_instance(cls) -> 'PyRPLManager':
        """Get the singleton instance."""
        return cls()


# Convenience functions for easy access
def get_pyrpl_manager() -> PyRPLManager:
    """Get the global PyRPL manager instance."""
    return PyRPLManager.get_instance()


def get_shared_mock_instance(hostname: str) -> Optional[Any]:
    """Return the shared enhanced mock instance, creating it if needed."""

    if not _ensure_enhanced_mock_loaded():
        return None

    global _shared_mock_instance, _shared_mock_hostname

    with _shared_mock_lock:
        if _shared_mock_instance is None:
            if create_enhanced_mock_connection is None:
                return None
            _shared_mock_instance = create_enhanced_mock_connection(hostname)
            _shared_mock_hostname = hostname
        return _shared_mock_instance


def reset_shared_mock_instance() -> None:
    """Reset the shared mock instance and clear cached adapters."""

    if not _ensure_enhanced_mock_loaded():
        return

    global _shared_mock_instance, _shared_mock_hostname

    with _shared_mock_lock:
        if ENHANCED_MOCK_AVAILABLE and EnhancedMockPyRPLConnection is not None:
            try:
                EnhancedMockPyRPLConnection.reset_all_simulations()
                EnhancedMockPyRPLConnection._instances.clear()  # type: ignore[attr-defined]
                EnhancedMockPyRPLConnection._simulation_engine = None  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                logger.debug("Enhanced mock reset reported: %s", exc)
        _shared_mock_instance = None
        _shared_mock_hostname = None

    manager = PyRPLManager.get_instance()
    with manager._manager_lock:  # type: ignore[attr-defined]
        manager._mock_connections.clear()  # type: ignore[attr-defined]


def get_mock_instance_info() -> Dict[str, Any]:
    """Return metadata about the shared mock instance if present."""

    info = {
        "exists": False,
        "hostname": None,
        "enhanced_available": _ensure_enhanced_mock_loaded(),
    }

    global _shared_mock_instance, _shared_mock_hostname
    with _shared_mock_lock:
        if _shared_mock_instance is not None:
            info["exists"] = True
            info["hostname"] = _shared_mock_hostname
            if hasattr(_shared_mock_instance, "get_connection_info"):
                try:
                    extra = _shared_mock_instance.get_connection_info()
                    if isinstance(extra, dict):
                        info.update(extra)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Failed to obtain mock instance info: %s", exc)

    return info


def create_pyrpl_connection(
    hostname: str,
    config_name: str = "pymodaq",
    *,
    mock_mode: bool = False,
    **kwargs: Any,
) -> Optional[Any]:
    """Factory function used by tests to create PyRPL connections."""

    manager = PyRPLManager.get_instance()
    return manager.connect_device(
        hostname,
        config_name,
        mock_mode=mock_mode,
        **kwargs,
    )


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
