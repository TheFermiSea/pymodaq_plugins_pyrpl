# -*- coding: utf-8 -*-
"""
PyTest Configuration for PyMoDAQ PyRPL Plugin Tests

This module provides shared test fixtures, configurations, and environment
setup for both mock and real hardware testing of PyRPL plugins.

Environment Variables:
- PYRPL_TEST_HOST: Hostname/IP of Red Pitaya for hardware tests
- PYRPL_TEST_CONFIG: PyRPL configuration name for tests
- PYRPL_MOCK_ONLY: Set to '1' to skip all hardware tests
- PYRPL_HARDWARE_TIMEOUT: Timeout for hardware operations (default: 10s)

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import os
import sys
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)

# Determine whether to rely on real hardware or the mock implementation
USE_PYRPL_MOCK = os.getenv('PYRPL_MOCK_ONLY', '0') == '1' or not os.getenv('PYRPL_TEST_HOST')


# Mock PyRPL early to prevent Qt initialization issues when hardware is unavailable
def create_pyrpl_mock():
    """Create comprehensive PyRPL mock for testing."""
    pyrpl_mock = Mock()

    # Mock PyRPL main classes
    pyrpl_mock.Pyrpl = Mock()
    pyrpl_mock.RedPitaya = Mock()

    # Mock hardware modules
    pyrpl_mock.hardware_modules = Mock()
    pyrpl_mock.hardware_modules.pid = Mock()
    pyrpl_mock.hardware_modules.pid.PidModule = Mock()
    pyrpl_mock.hardware_modules.asg = Mock()
    pyrpl_mock.hardware_modules.scope = Mock()
    pyrpl_mock.hardware_modules.iq = Mock()

    # Mock software modules
    pyrpl_mock.software_modules = Mock()
    pyrpl_mock.software_modules.lockbox = Mock()

    return pyrpl_mock

if USE_PYRPL_MOCK:
    # Install PyRPL mock before imports
    if 'pyrpl' not in sys.modules:
        pyrpl_mock = create_pyrpl_mock()
        sys.modules['pyrpl'] = pyrpl_mock
        sys.modules['pyrpl.hardware_modules'] = pyrpl_mock.hardware_modules
        sys.modules['pyrpl.hardware_modules.pid'] = pyrpl_mock.hardware_modules.pid
        sys.modules['pyrpl.hardware_modules.asg'] = pyrpl_mock.hardware_modules.asg
        sys.modules['pyrpl.hardware_modules.scope'] = pyrpl_mock.hardware_modules.scope
        sys.modules['pyrpl.hardware_modules.iq'] = pyrpl_mock.hardware_modules.iq
        sys.modules['pyrpl.software_modules'] = pyrpl_mock.software_modules
        sys.modules['pyrpl.software_modules.lockbox'] = pyrpl_mock.software_modules.lockbox
else:
    # Ensure PyRPL's legacy dependencies remain compatible with modern Python versions
    try:
        from pymodaq_qasync_monkey_patch import install_quamash_shim
        logging.getLogger('pymodaq_qasync_patch').setLevel(logging.WARNING)

        install_quamash_shim()
    except Exception as exc:  # pragma: no cover - hardware path diagnostics
        logger.warning("Failed to install qasync shim for hardware tests: %s", exc)

    # Provide backwards-compatible aliases for old collections APIs
    import collections  # type: ignore
    import collections.abc  # type: ignore

    if not hasattr(collections, "Mapping"):
        collections.Mapping = collections.abc.Mapping  # type: ignore[attr-defined]

    # NumPy compatibility for legacy PyRPL expectations
    try:
        import numpy as np

        if not hasattr(np, "complex"):
            np.complex = np.complex128  # type: ignore[attr-defined]
        if not hasattr(np, "bool"):
            np.bool = np.bool_  # type: ignore[attr-defined]
        if not hasattr(np, "float"):
            np.float = float  # type: ignore[attr-defined]
    except ImportError as exc:  # pragma: no cover - numpy always available in env
        logger.warning("NumPy not available to patch legacy aliases: %s", exc)

    # Point PyRPL to the repository-provided hardware config directory
    user_dir = Path(__file__).parent / "pyrpl_user_dir"
    os.environ['PYRPL_USER_DIR'] = str(user_dir)
    os.environ['PYRPL_CONFIG_DIR'] = str(user_dir / "config")

    # Patch PyRPL's MainThreadTimer to accept float intervals
    try:
        from pyrpl import async_utils  # type: ignore

        _original_set_interval = async_utils.MainThreadTimer.setInterval

        def _safe_set_interval(self, msec):
            return _original_set_interval(self, int(max(0, round(msec))))

        async_utils.MainThreadTimer.setInterval = _safe_set_interval
    except Exception as exc:  # pragma: no cover - fallback when PyRPL not yet available
        logger.warning("Failed to patch MainThreadTimer for hardware tests: %s", exc)

# Configure test logging
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

# Test environment configuration
TEST_CONFIG = {
    'default_hostname': 'test-rp.local',
    'default_config_name': 'pytest_config',
    'mock_timeout': 1.0,
    'hardware_timeout': 10.0,
    'test_voltage_range': (-1.0, 1.0),
    'test_setpoint_range': (-0.5, 0.5),
    'test_pid_gains': {'p': 1.0, 'i': 0.1, 'd': 0.05}
}


def pytest_configure(config):
    """Configure pytest with custom markers and test environment."""
    # Register custom markers
    markers = [
        ("mock", "Tests that run with mock hardware only"),
        ("hardware", "Tests that require real Red Pitaya hardware"),
        ("integration", "Integration tests with PyMoDAQ framework"),
        ("thread_safety", "Thread safety validation tests"),
        ("error_handling", "Error handling and recovery tests"),
        ("performance", "Performance and timing tests"),
        ("slow", "Slow-running tests that may take several seconds"),
        ("network", "Tests that require network connectivity")
    ]

    for marker, description in markers:
        config.addinivalue_line("markers", f"{marker}: {description}")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment and command line options."""
    # Skip hardware tests if no hardware environment or mock-only mode
    mock_only = os.getenv('PYRPL_MOCK_ONLY', '0') == '1'
    no_hardware_env = not os.getenv('PYRPL_TEST_HOST')

    if mock_only or no_hardware_env:
        skip_hardware = pytest.mark.skip(
            reason="Hardware tests disabled (PYRPL_MOCK_ONLY=1 or no PYRPL_TEST_HOST)"
        )
        for item in items:
            if 'hardware' in item.keywords:
                item.add_marker(skip_hardware)


def is_hardware_available() -> bool:
    """Check if hardware testing environment is available."""
    return (
        os.getenv('PYRPL_MOCK_ONLY', '0') != '1' and
        os.getenv('PYRPL_TEST_HOST') is not None
    )


def get_hardware_config() -> Dict[str, Any]:
    """Get hardware test configuration from environment."""
    return {
        'hostname': os.getenv('PYRPL_TEST_HOST', TEST_CONFIG['default_hostname']),
        'config_name': os.getenv('PYRPL_TEST_CONFIG', TEST_CONFIG['default_config_name']),
        'timeout': float(os.getenv('PYRPL_HARDWARE_TIMEOUT', TEST_CONFIG['hardware_timeout']))
    }


@pytest.fixture(scope="session")
def hardware_config():
    """Provide hardware configuration for tests."""
    return get_hardware_config()


@pytest.fixture(scope="session")
def test_config():
    """Provide general test configuration."""
    return TEST_CONFIG.copy()


@pytest.fixture
def mock_pyrpl_manager():
    """Provide mocked PyRPL manager for testing."""
    with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PyRPLManager') as mock_manager_class:
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Mock connection methods
        mock_connection = Mock()
        mock_connection.is_connected = True
        mock_connection.hostname = TEST_CONFIG['default_hostname']
        mock_connection.config_name = TEST_CONFIG['default_config_name']
        mock_manager.connect_device.return_value = mock_connection

        yield mock_manager


@pytest.fixture
def enhanced_mock_connection():
    """Provide enhanced mock connection for testing."""
    from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import EnhancedMockPyRPLConnection

    # Clear any existing instances to ensure clean state
    EnhancedMockPyRPLConnection._instances.clear()

    connection = EnhancedMockPyRPLConnection("test-enhanced.local")
    yield connection

    # Cleanup
    connection.reset_simulation()


@pytest.fixture
def demo_preset_manager():
    """Provide demo preset manager for testing."""
    from pymodaq_plugins_pyrpl.utils.demo_presets import get_demo_preset_manager
    return get_demo_preset_manager()


@pytest.fixture
def mock_move_plugin():
    """Create mock DAQ_Move_PyRPL_PID plugin for testing."""
    with patch('pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID.PyRPLManager'):
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID

        plugin = DAQ_Move_PyRPL_PID()
        plugin.emit_status = Mock()
        plugin.emit_actuator_value = Mock()
        plugin.data_actuator_signal = Mock()

        # Mock settings structure with subscript support
        plugin.settings = Mock()
        plugin.settings.child = Mock()

        # Mock parameter children
        def mock_child(*path):
            param = Mock()
            param.setValue = Mock()
            param.value = Mock(return_value=None)
            return param

        plugin.settings.child.side_effect = mock_child

        # Mock settings subscript access for bounds and multiaxes
        def mock_getitem(self, keys):
            if isinstance(keys, tuple):
                if keys == ('bounds', 'is_bounds'):
                    return False
                elif keys == ('multiaxes', 'multi_status'):
                    return 'Master'
                elif keys[0] == 'connection_settings':
                    return Mock(value=Mock(return_value=True))
            return Mock()

        plugin.settings.__getitem__ = mock_getitem.__get__(plugin.settings, type(plugin.settings))

        yield plugin


@pytest.fixture
def mock_viewer_plugin():
    """Create mock DAQ_0DViewer_PyRPL plugin for testing."""
    with patch('pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL.PyRPLManager'):
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL

        plugin = DAQ_0DViewer_PyRPL()
        plugin.emit_status = Mock()
        plugin.dte_signal = Mock()
        plugin.dte_signal_temp = Mock()
        plugin.dte_signal.emit = Mock()
        plugin.dte_signal_temp.emit = Mock()

        # Mock settings structure with subscript support
        plugin.settings = Mock()
        plugin.settings.child = Mock()

        def mock_child(*path):
            param = Mock()
            param.setValue = Mock()
            param.value = Mock(return_value=False)  # Default to mock_mode = False
            return param

        plugin.settings.child.side_effect = mock_child

        # Mock settings subscript access
        def mock_getitem(self, keys):
            if isinstance(keys, tuple):
                if keys == ('connection', 'mock_mode'):
                    return False
            return Mock()

        plugin.settings.__getitem__ = mock_getitem.__get__(plugin.settings, type(plugin.settings))

        yield plugin


@pytest.fixture
def mock_scope_plugin():
    """Create mock DAQ_1DViewer_PyRPL_Scope plugin for testing."""
    with patch('pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope.PyRPLManager'):
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope

        plugin = DAQ_1DViewer_PyRPL_Scope()
        plugin.emit_status = Mock()
        plugin.dte_signal = Mock()
        plugin.dte_signal_temp = Mock()

        # Mock settings
        plugin.settings = Mock()
        plugin.settings.child = Mock()

        def mock_child(*path):
            param = Mock()
            param.setValue = Mock()
            param.value = Mock(return_value=64)  # Default decimation
            return param

        plugin.settings.child.side_effect = mock_child

        yield plugin


@pytest.fixture
def mock_iq_plugin():
    """Create mock DAQ_0DViewer_PyRPL_IQ plugin for testing."""
    with patch('pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ.PyRPLManager'):
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ

        plugin = DAQ_0DViewer_PyRPL_IQ()
        plugin.emit_status = Mock()
        plugin.dte_signal = Mock()
        plugin.dte_signal_temp = Mock()

        # Mock settings
        plugin.settings = Mock()
        plugin.settings.child = Mock()

        def mock_child(*path):
            param = Mock()
            param.setValue = Mock()
            param.value = Mock(return_value=1000.0)  # Default frequency
            return param

        plugin.settings.child.side_effect = mock_child

        yield plugin


@pytest.fixture
def skip_if_no_hardware():
    """Skip test if hardware environment is not available."""
    if not is_hardware_available():
        pytest.skip("Hardware testing environment not available")


@pytest.fixture
def temporary_pyrpl_config(tmp_path):
    """Provide temporary PyRPL configuration directory."""
    config_dir = tmp_path / "pyrpl_config"
    config_dir.mkdir()

    # Set environment variable for PyRPL to use temporary config
    old_config = os.environ.get('PYRPL_CONFIG_DIR')
    os.environ['PYRPL_CONFIG_DIR'] = str(config_dir)

    yield config_dir

    # Restore original environment
    if old_config is not None:
        os.environ['PYRPL_CONFIG_DIR'] = old_config
    elif 'PYRPL_CONFIG_DIR' in os.environ:
        del os.environ['PYRPL_CONFIG_DIR']


# Hardware validation utilities
def validate_hardware_environment() -> tuple[bool, str]:
    """
    Validate that hardware testing environment is properly configured.

    Returns:
        Tuple of (is_valid, message)
    """
    if os.getenv('PYRPL_MOCK_ONLY', '0') == '1':
        return False, "Hardware tests disabled by PYRPL_MOCK_ONLY"

    if not os.getenv('PYRPL_TEST_HOST'):
        return False, "PYRPL_TEST_HOST environment variable required"

    hostname = os.getenv('PYRPL_TEST_HOST')
    if not hostname:
        return False, "PYRPL_TEST_HOST cannot be empty"

    # Additional validation could include network connectivity checks
    # For now, just validate environment variables exist

    return True, f"Hardware environment validated for {hostname}"


# Export utilities for use in tests
__all__ = [
    'is_hardware_available',
    'get_hardware_config',
    'validate_hardware_environment',
    'TEST_CONFIG'
]