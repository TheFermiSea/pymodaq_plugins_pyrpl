# -*- coding: utf-8 -*-
"""
PyRPL Functionality Tests for PyMoDAQ PyRPL Plugin

This module provides comprehensive testing for PyRPL plugin functionality including:
- PyRPL wrapper connection tests (mock and real hardware)
- DAQ_Move_PyRPL_PID plugin functionality tests
- DAQ_0DViewer_PyRPL plugin functionality tests
- PIDModelPyRPL integration tests
- Error handling and edge case tests
- Thread safety and performance validation

Test Categories:
- Mock Hardware Tests: Test all functionality without real hardware
- Real Hardware Tests: Optional tests that require actual Red Pitaya
- Integration Tests: Test plugin interactions with PyMoDAQ framework
- Thread Safety Tests: Verify concurrent operations work correctly
- Error Recovery Tests: Network failures, disconnections, etc.

Usage:
    pytest tests/test_pyrpl_functionality.py                    # All mock tests
    pytest tests/test_pyrpl_functionality.py -m hardware        # Real hardware tests only
    pytest tests/test_pyrpl_functionality.py -k test_mock       # Mock tests only
    pytest tests/test_pyrpl_functionality.py -k test_real       # Real hardware tests only

Author: Claude Code
License: MIT
"""

import pytest
import threading
import time
import numpy as np
from unittest.mock import Mock, patch, PropertyMock
from typing import Optional
import logging

# Mock PyRPL completely to avoid Qt initialization issues in tests
import sys

# Create comprehensive PyRPL mock
pyrpl_mock = Mock()
pyrpl_mock.Pyrpl = Mock()
pyrpl_mock.hardware_modules = Mock()
pyrpl_mock.hardware_modules.pid = Mock()
pyrpl_mock.hardware_modules.pid.PidModule = Mock()

# Mock the entire pyrpl module
sys.modules['pyrpl'] = pyrpl_mock
sys.modules['pyrpl.hardware_modules'] = pyrpl_mock.hardware_modules
sys.modules['pyrpl.hardware_modules.pid'] = pyrpl_mock.hardware_modules.pid

# Import PyRPL wrapper and related utilities
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import (
    PyRPLManager, PyRPLConnection, PIDChannel, InputChannel, OutputChannel,
    PIDConfiguration, ConnectionInfo, ConnectionState, ScopeConfiguration, ScopeDecimation, ScopeTriggerSource,
    IQConfiguration, IQChannel, IQOutputDirect, ASGChannel
)

# Import plugin classes  
from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import (
    DAQ_0DViewer_PyRPL, MockPyRPLConnection
)
# PIDModelPyRPL removed - was broken with circular dependencies

# PyMoDAQ imports for data structures
from pymodaq_data.data import DataToExport
from pymodaq.utils.data import DataActuator

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Test Constants
TEST_HOSTNAME = "test-redpitaya.local"
TEST_IP = "192.168.1.100"
MOCK_VOLTAGE_RANGE = (-1.0, 1.0)
MOCK_DEFAULT_VOLTAGE_IN1 = 0.5
MOCK_DEFAULT_VOLTAGE_IN2 = 0.3
MOCK_DEFAULT_SETPOINT = 0.25

# Pytest markers for test categorization
pytest_markers = [
    ("mock", "Tests that run with mock hardware only"),
    ("hardware", "Tests that require real Red Pitaya hardware"),
    ("integration", "Integration tests with PyMoDAQ framework"),
    ("thread_safety", "Thread safety validation tests"),
    ("error_handling", "Error handling and recovery tests"),
    ("performance", "Performance and timing tests")
]

def pytest_configure(config):
    """Configure pytest with custom markers."""
    for marker, description in pytest_markers:
        config.addinivalue_line("markers", f"{marker}: {description}")


# Mock PyRPL Objects for Testing
class MockPidModule:
    """Mock PyRPL PID module for testing."""
    
    def __init__(self):
        self.setpoint = 0.0
        self.p = 0.1
        self.i = 0.01
        self.d = 0.0
        self.input = 'in1'
        self.output_direct = 'off'
        self.max_voltage = 1.0
        self.min_voltage = -1.0

class MockScope:
    """Mock PyRPL scope for configuration and acquisition testing."""
    def __init__(self, stop_after_polls: Optional[int] = 3, sample_count: int = 1024):
        # Instant voltage reading (used by read_voltage)
        self.voltage_in1 = MOCK_DEFAULT_VOLTAGE_IN1
        self.voltage_in2 = MOCK_DEFAULT_VOLTAGE_IN2

        # Configurable attributes (set by configure_scope)
        self.decimation = ScopeDecimation.DEC_64.value
        self.trigger_source = ScopeTriggerSource.IMMEDIATELY.value
        self.trigger_delay = 0
        self.trigger_level = 0.0
        self.average = 1
        self.rolling_mode = False
        self.input = 'in1'

        # Acquisition state
        self._acq_running = False
        self._polls = 0
        self._stop_after = stop_after_polls  # None => never stops (used to test timeout)
        self._sample_count = sample_count

        # Derived acquisition properties
        self.sampling_time = 1e-6  # 1 µs per sample
        self.duration = self._sample_count * self.sampling_time

    def trigger(self):
        self._acq_running = True
        self._polls = 0

    def stopped(self):
        if not self._acq_running:
            return True
        self._polls += 1
        if self._stop_after is not None and self._polls >= self._stop_after:
            self._acq_running = False
            return True
        return False

    def curve(self):
        # Simple sine waveform for deterministic tests
        t = np.arange(self._sample_count) * self.sampling_time
        return np.sin(2 * np.pi * 1e3 * t)

    def stop(self):
        self._acq_running = False

class MockSampler:
    """Mock PyRPL sampler for voltage reading."""
    
    def __init__(self):
        self.in1 = MOCK_DEFAULT_VOLTAGE_IN1
        self.in2 = MOCK_DEFAULT_VOLTAGE_IN2

class MockIQModule:
    """Mock PyRPL IQ (lock-in) module."""
    def __init__(self):
        self.frequency = 1000.0
        self.bandwidth = 100.0
        self.acbandwidth = 10000.0
        self.phase = 0.0
        self.gain = 1.0
        self.quadrature_factor = 1.0
        self.amplitude = 0.0
        self.input = 'in1'
        self.output_direct = 'off'
        self.I = 0.0
        self.Q = 0.0

class MockRedPitaya:
    """Mock Red Pitaya device for testing."""
    
    def __init__(self):
        self.version = "1.0.0-test"
        self.pid0 = MockPidModule()
        self.pid1 = MockPidModule()
        self.pid2 = MockPidModule()
        self.scope = MockScope()        # supports configure + acquisition
        self.sampler = MockSampler()
        # IQ modules
        self.iq0 = MockIQModule()
        self.iq1 = MockIQModule()
        self.iq2 = MockIQModule()

class MockPyrpl:
    """Mock PyRPL instance for testing."""
    
    def __init__(self, config=None, hostname=None, port=None, timeout=None):
        self.config = config
        self.hostname = hostname
        self.port = port
        self.timeout = timeout
        self.rp = MockRedPitaya()  # PyRPL uses 'rp' not 'redpitaya'
        self.redpitaya = self.rp  # Keep both for compatibility
        self._closed = False
    
    def close(self):
        """Mock close method."""
        self._closed = True


# Fixtures
@pytest.fixture
def mock_pyrpl():
    """Create a mock PyRPL instance."""
    return MockPyrpl()

@pytest.fixture
def mock_connection_info():
    """Create mock connection info."""
    return ConnectionInfo(
        hostname=TEST_HOSTNAME,
        config_name="test_config",
        port=2222,
        connection_timeout=5.0,
        retry_attempts=2,
        retry_delay=0.5
    )

@pytest.fixture
def mock_pid_config():
    """Create mock PID configuration."""
    return PIDConfiguration(
        setpoint=0.5,
        p_gain=0.1,
        i_gain=0.01,
        d_gain=0.0,
        input_channel=InputChannel.IN1,
        output_channel=OutputChannel.OUT1,
        voltage_limit_min=-1.0,
        voltage_limit_max=1.0,
        enabled=True
    )

@pytest.fixture
def pyrpl_manager():
    """Get a fresh PyRPL manager instance for testing."""
    # Clear any existing connections
    manager = PyRPLManager()
    manager.cleanup()
    return manager

@pytest.fixture
def mock_move_plugin():
    """Create a mock move plugin instance."""
    with patch('pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID.PyRPLManager'), \
         patch('pymodaq_plugins_pyrpl.utils.config.PyRPLConfig') as mock_config_class:
        mock_config_class.return_value = Mock()
        plugin = DAQ_Move_PyRPL_PID()
        return plugin

@pytest.fixture
def mock_viewer_plugin():
    """Create a mock viewer plugin instance."""
    plugin = DAQ_0DViewer_PyRPL()
    plugin.ini_attributes()
    return plugin


# ============================================================================
# PyRPL Wrapper Tests
# ============================================================================

@pytest.mark.mock
class TestPyRPLWrapperMock:
    """Test PyRPL wrapper functionality with mock hardware."""

    def test_connection_info_creation(self, mock_connection_info):
        """Test ConnectionInfo dataclass creation and validation."""
        assert mock_connection_info.hostname == TEST_HOSTNAME
        assert mock_connection_info.config_name == "test_config"
        assert mock_connection_info.port == 2222
        assert mock_connection_info.connection_timeout == 5.0

    def test_pid_configuration_creation(self, mock_pid_config):
        """Test PIDConfiguration dataclass creation and validation."""
        assert mock_pid_config.setpoint == 0.5
        assert mock_pid_config.p_gain == 0.1
        assert mock_pid_config.input_channel == InputChannel.IN1
        assert mock_pid_config.output_channel == OutputChannel.OUT1
        assert mock_pid_config.enabled is True

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pyrpl_connection_success(self, mock_pyrpl_module, mock_connection_info):
        """Test successful PyRPL connection establishment."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)
        
        # Create connection and test
        connection = PyRPLConnection(mock_connection_info)
        assert connection.state == ConnectionState.DISCONNECTED
        
        # Test connection
        success = connection.connect()
        assert success is True
        assert connection.state == ConnectionState.CONNECTED
        assert connection.is_connected is True
        assert connection.pyrpl is mock_pyrpl_instance

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pyrpl_connection_failure(self, mock_pyrpl_module, mock_connection_info):
        """Test PyRPL connection failure handling."""
        # Setup mock to raise exception
        mock_pyrpl_module.Pyrpl = Mock(side_effect=Exception("Connection failed"))
        
        # Create connection and test failure
        connection = PyRPLConnection(mock_connection_info)
        success = connection.connect()
        
        assert success is False
        assert connection.state == ConnectionState.ERROR
        assert connection.last_error == "Connection failed"
        assert connection.is_connected is False

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pyrpl_connection_retry_logic(self, mock_pyrpl_module, mock_connection_info):
        """Test connection retry logic with eventual success."""
        # Setup mock to fail twice, then succeed
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            mock_pyrpl_instance  # Third attempt succeeds
        ])
        
        # Ensure we have enough retry attempts and reduce delay for testing
        mock_connection_info.retry_attempts = 3
        mock_connection_info.retry_delay = 0.01
        
        connection = PyRPLConnection(mock_connection_info)
        success = connection.connect()
        
        assert success is True
        assert connection.state == ConnectionState.CONNECTED
        assert mock_pyrpl_module.Pyrpl.call_count == 3

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pid_module_access(self, mock_pyrpl_module, mock_connection_info):
        """Test PID module access and caching."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test PID module access
        pid0 = connection.get_pid_module(PIDChannel.PID0)
        assert pid0 is mock_pyrpl_instance.redpitaya.pid0
        
        # Test caching
        pid0_cached = connection.get_pid_module(PIDChannel.PID0)
        assert pid0_cached is pid0

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pid_configuration(self, mock_pyrpl_module, mock_connection_info, mock_pid_config):
        """Test PID controller configuration."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test PID configuration
        success = connection.configure_pid(PIDChannel.PID0, mock_pid_config)
        assert success is True
        
        # Verify configuration was applied
        pid_module = mock_pyrpl_instance.redpitaya.pid0
        assert pid_module.setpoint == mock_pid_config.setpoint
        assert pid_module.p == mock_pid_config.p_gain
        assert pid_module.i == mock_pid_config.i_gain
        assert pid_module.input == mock_pid_config.input_channel.value
        assert pid_module.output_direct == mock_pid_config.output_channel.value

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_voltage_reading(self, mock_pyrpl_module, mock_connection_info):
        """Test voltage reading from input channels."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test voltage reading
        voltage1 = connection.read_voltage(InputChannel.IN1)
        voltage2 = connection.read_voltage(InputChannel.IN2)
        
        assert voltage1 == MOCK_DEFAULT_VOLTAGE_IN1
        assert voltage2 == MOCK_DEFAULT_VOLTAGE_IN2

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_multiple_voltage_reading(self, mock_pyrpl_module, mock_connection_info):
        """Test reading multiple voltage channels simultaneously."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test multiple channel reading
        channels = [InputChannel.IN1, InputChannel.IN2]
        voltages = connection.read_multiple_voltages(channels)
        
        assert len(voltages) == 2
        assert voltages[InputChannel.IN1] == MOCK_DEFAULT_VOLTAGE_IN1
        assert voltages[InputChannel.IN2] == MOCK_DEFAULT_VOLTAGE_IN2

    def test_pyrpl_manager_singleton(self):
        """Test PyRPLManager singleton behavior."""
        manager1 = PyRPLManager()
        manager2 = PyRPLManager()
        
        assert manager1 is manager2
        assert PyRPLManager.get_instance() is manager1

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_manager_connection_pooling(self, mock_pyrpl_module, pyrpl_manager):
        """Test connection pooling in PyRPL manager."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        # Request same connection twice
        conn1 = pyrpl_manager.get_connection(TEST_HOSTNAME, "test_config")
        conn2 = pyrpl_manager.get_connection(TEST_HOSTNAME, "test_config")
        
        assert conn1 is conn2  # Should be same instance (pooled)

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_manager_different_configs(self, mock_pyrpl_module, pyrpl_manager):
        """Test manager handling of different configurations."""
        # Setup mock
        mock_pyrpl_module.Pyrpl = Mock(return_value = MockPyrpl())
        
        # Request connections with different configs
        conn1 = pyrpl_manager.get_connection(TEST_HOSTNAME, "config1")
        conn2 = pyrpl_manager.get_connection(TEST_HOSTNAME, "config2")
        
        assert conn1 is not conn2  # Different configs = different connections


@pytest.mark.thread_safety
class TestPyRPLWrapperThreadSafety:
    """Test thread safety of PyRPL wrapper operations."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_concurrent_connections(self, mock_pyrpl_module, pyrpl_manager):
        """Test concurrent connection establishment."""
        mock_pyrpl_module.Pyrpl = Mock(return_value = MockPyrpl())
        
        results = []
        threads = []
        
        def connect_task(hostname, config):
            conn = pyrpl_manager.connect_device(hostname, config)
            results.append(conn is not None and conn.is_connected)
        
        # Start multiple concurrent connections
        for i in range(5):
            thread = threading.Thread(
                target=connect_task,
                args=(f"test-rp{i}.local", f"config{i}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)
        
        # All connections should succeed
        assert all(results)
        assert len(results) == 5

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_concurrent_pid_operations(self, mock_pyrpl_module, mock_connection_info):
        """Test concurrent PID operations on same connection."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        results = []
        threads = []
        
        def pid_task(channel, setpoint):
            success = connection.set_pid_setpoint(channel, setpoint)
            results.append(success)
        
        # Start concurrent PID operations
        setpoints = [0.1, 0.2, 0.3, 0.4, 0.5]
        for i, setpoint in enumerate(setpoints):
            thread = threading.Thread(
                target=pid_task,
                args=(PIDChannel.PID0, setpoint)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=2.0)
        
        # All operations should succeed
        assert all(results)
        assert len(results) == 5


@pytest.mark.error_handling
class TestPyRPLWrapperErrorHandling:
    """Test error handling and recovery in PyRPL wrapper."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_connection_loss_detection(self, mock_pyrpl_module, mock_connection_info):
        """Test detection of lost connections."""
        # Setup mock that initially works
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        assert connection.is_connected
        
        # Simulate connection loss by making redpitaya None
        connection._redpitaya = None
        assert not connection.is_connected

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_operation_without_connection(self, mock_pyrpl_module, mock_connection_info):
        """Test operations when not connected."""
        connection = PyRPLConnection(mock_connection_info)
        # Don't connect
        
        # All operations should fail gracefully
        assert connection.read_voltage(InputChannel.IN1) is None
        assert connection.get_pid_setpoint(PIDChannel.PID0) is None
        assert connection.set_pid_setpoint(PIDChannel.PID0, 0.5) is False
        assert connection.configure_pid(PIDChannel.PID0, PIDConfiguration()) is False

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pid_operation_failures(self, mock_pyrpl_module, mock_connection_info):
        """Test PID operation failure handling."""
        # Setup mock that raises exceptions
        mock_pyrpl_instance = MockPyrpl()
        
        # Create a mock pid module that raises exceptions when accessing setpoint
        failing_pid_module = Mock()
        type(failing_pid_module).setpoint = PropertyMock(side_effect=Exception("Hardware error"))
        mock_pyrpl_instance.redpitaya.pid0 = failing_pid_module
        
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # PID operations should handle exceptions gracefully
        assert connection.set_pid_setpoint(PIDChannel.PID0, 0.5) is False
        assert connection.get_pid_setpoint(PIDChannel.PID0) is None


# ============================================================================
# DAQ_Move_PyRPL_PID Plugin Tests
# ============================================================================

@pytest.mark.mock
class TestDAQMovePyRPLPID:
    """Test DAQ_Move_PyRPL_PID plugin functionality."""

    def test_plugin_initialization(self, mock_move_plugin):
        """Test plugin attribute initialization."""
        assert mock_move_plugin.controller is None
        assert mock_move_plugin.pyrpl_manager is not None
        assert mock_move_plugin.pid_channel is None
        assert mock_move_plugin.mock_mode is False
        assert mock_move_plugin.mock_setpoint == 0.0

    def test_plugin_parameters(self, mock_move_plugin):
        """Test plugin parameter structure and defaults."""
        # Check connection parameters
        assert mock_move_plugin.settings.child('connection_settings', 'redpitaya_host').value() == 'rp-f08d6c.local'
        assert mock_move_plugin.settings.child('connection_settings', 'config_name').value() == 'pymodaq_pyrpl'
        assert mock_move_plugin.settings.child('connection_settings', 'mock_mode').value() is False
        
        # Check PID configuration parameters
        assert mock_move_plugin.settings.child('pid_config', 'pid_module').value() == 'pid0'
        assert mock_move_plugin.settings.child('pid_config', 'input_channel').value() == 'in1'
        assert mock_move_plugin.settings.child('pid_config', 'output_channel').value() == 'out1'
        
        # Check PID parameters
        assert mock_move_plugin.settings.child('pid_params', 'p_gain').value() == 0.1
        assert mock_move_plugin.settings.child('pid_params', 'i_gain').value() == 0.01
        assert mock_move_plugin.settings.child('pid_params', 'd_gain').value() == 0.0

    @patch('pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID.PyRPLManager')
    def test_mock_mode_initialization(self, mock_manager_class, mock_move_plugin):
        """Test plugin initialization in mock mode."""
        # Set mock mode
        mock_move_plugin.settings.child('connection_settings', 'mock_mode').setValue(True)
        mock_move_plugin.mock_mode = True
        
        # Mock the is_master property since it's read-only
        with patch.object(type(mock_move_plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
            mock_is_master.return_value = True
            
            # Test initialization
            info, success = mock_move_plugin.ini_stage()
            
            assert success is True
            assert "MOCK mode" in info
            assert mock_move_plugin.controller is None

    def test_mock_mode_operations(self, mock_move_plugin):
        """Test actuator operations in mock mode."""
        # Enable mock mode
        mock_move_plugin.mock_mode = True
        
        # Test move absolute
        target_value = DataActuator(data=0.5, units='V')
        mock_move_plugin.move_abs(target_value)
        assert mock_move_plugin.mock_setpoint == 0.5
        
        # Test get actuator value
        current_pos = mock_move_plugin.get_actuator_value()
        assert current_pos.value('V') == 0.5
        
        # Test move relative
        relative_value = DataActuator(data=0.2, units='V')
        mock_move_plugin.move_rel(relative_value)
        assert mock_move_plugin.mock_setpoint == 0.7
        
        # Test move home
        mock_move_plugin.move_home()
        assert mock_move_plugin.mock_setpoint == 0.0

    @patch('pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID.PyRPLManager')
    def test_hardware_mode_initialization(self, mock_manager_class, mock_move_plugin):
        """Test plugin initialization with mock hardware manager."""
        # Setup mock manager chain properly
        mock_connection = Mock()
        mock_connection.is_connected = True
        mock_connection.configure_pid.return_value = True
        mock_connection.get_connection_info.return_value = {'state': 'connected'}
        
        mock_manager = Mock()
        mock_manager.connect_device.return_value = mock_connection
        
        # Ensure the get_instance chain works
        mock_manager_class.return_value = mock_manager
        mock_manager_class.get_instance.return_value = mock_manager
        
        # Set hardware mode
        mock_move_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        mock_move_plugin.mock_mode = False
        
        # Replace the plugin's manager instance with our mock
        mock_move_plugin.pyrpl_manager = mock_manager
        
        # Mock the is_master property since it's read-only
        with patch.object(type(mock_move_plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
            mock_is_master.return_value = True
            
            # Test initialization
            info, success = mock_move_plugin.ini_stage()
            
            assert success is True
            # The controller might be assigned differently, so check it was called
            assert mock_manager.connect_device.called
            assert mock_connection.configure_pid.called

    def test_bounds_checking(self, mock_move_plugin):
        """Test voltage bounds checking."""
        # Enable mock mode for testing
        mock_move_plugin.mock_mode = True
        
        # Test within bounds
        valid_value = DataActuator(data=0.5, units='V')
        bounded_value = mock_move_plugin.check_bound(valid_value)
        assert bounded_value.value('V') == 0.5
        
        # Test boundary conditions (should be handled by PyMoDAQ framework)
        # This test verifies that the bounds are properly configured
        min_voltage = mock_move_plugin.settings.child('safety_limits', 'min_voltage').value()
        max_voltage = mock_move_plugin.settings.child('safety_limits', 'max_voltage').value()
        assert min_voltage == -1.0
        assert max_voltage == 1.0

    def test_parameter_changes(self, mock_move_plugin):
        """Test parameter change handling."""
        # Test mock mode parameter change
        mock_move_plugin.emit_status = Mock()
        param = mock_move_plugin.settings.child('connection_settings', 'mock_mode')
        param.setValue(True)
        mock_move_plugin.commit_settings(param)
        
        assert mock_move_plugin.mock_mode is True
        mock_move_plugin.emit_status.assert_called()

    def test_units_configuration(self, mock_move_plugin):
        """Test that plugin uses correct voltage units."""
        assert mock_move_plugin._controller_units == 'V'

    def test_epsilon_precision(self, mock_move_plugin):
        """Test precision setting for setpoint control."""
        assert mock_move_plugin._epsilon == 0.001  # 1mV precision


# ============================================================================
# DAQ_0DViewer_PyRPL Plugin Tests
# ============================================================================

@pytest.mark.mock
class TestDAQ0DViewerPyRPL:
    """Test DAQ_0DViewer_PyRPL plugin functionality."""

    def test_plugin_initialization(self, mock_viewer_plugin):
        """Test viewer plugin attribute initialization."""
        assert mock_viewer_plugin.controller is None
        assert mock_viewer_plugin.pyrpl_manager is None
        assert mock_viewer_plugin.last_acquisition_time == 0.0
        assert mock_viewer_plugin.active_channels == []
        assert mock_viewer_plugin.channel_data == {}

    def test_plugin_parameters(self, mock_viewer_plugin):
        """Test viewer plugin parameter structure."""
        # Check connection parameters exist
        conn_group = mock_viewer_plugin.settings.child('connection')
        assert conn_group.child('redpitaya_host').value() == 'rp-f08d6c.local'
        assert conn_group.child('config_name').value() == 'pymodaq_viewer'
        assert conn_group.child('mock_mode').value() is False
        
        # Check channel configuration parameters
        chan_group = mock_viewer_plugin.settings.child('channels')
        assert chan_group.child('monitor_in1').value() is True
        assert chan_group.child('monitor_in2').value() is False
        assert chan_group.child('monitor_pid').value() is True
        assert chan_group.child('pid_module').value() == 'pid0'

    def test_active_channels_update(self, mock_viewer_plugin):
        """Test active channel list updates."""
        # Test default configuration
        mock_viewer_plugin._update_active_channels()
        expected_channels = ['Input 1 (V)', 'PID PID0 Setpoint (V)']
        assert mock_viewer_plugin.active_channels == expected_channels
        
        # Enable IN2 channel
        mock_viewer_plugin.settings.child('channels', 'monitor_in2').setValue(True)
        mock_viewer_plugin._update_active_channels()
        assert 'Input 2 (V)' in mock_viewer_plugin.active_channels
        
        # Disable PID monitoring
        mock_viewer_plugin.settings.child('channels', 'monitor_pid').setValue(False)
        mock_viewer_plugin._update_active_channels()
        assert 'PID PID0 Setpoint (V)' not in mock_viewer_plugin.active_channels

    def test_mock_connection_initialization(self, mock_viewer_plugin):
        """Test initialization with mock connection."""
        mock_viewer_plugin.settings.child('connection', 'mock_mode').setValue(True)
        
        # Mock the required methods and is_master property
        mock_viewer_plugin.emit_status = Mock()
        mock_viewer_plugin.dte_signal_temp = Mock()
        mock_viewer_plugin.dte_signal_temp.emit = Mock()
        
        with patch.object(type(mock_viewer_plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
            mock_is_master.return_value = True
            
            info, success = mock_viewer_plugin.ini_detector()
            
            assert success is True
            assert "Mock PyRPL connection" in info
            assert isinstance(mock_viewer_plugin.controller, MockPyRPLConnection)

    def test_mock_data_acquisition(self, mock_viewer_plugin):
        """Test data acquisition with mock connection."""
        # Setup mock connection and enable all channels
        mock_viewer_plugin.controller = MockPyRPLConnection(TEST_HOSTNAME)
        mock_viewer_plugin.settings.child('channels', 'monitor_in1').setValue(True)
        mock_viewer_plugin.settings.child('channels', 'monitor_in2').setValue(True)
        mock_viewer_plugin.settings.child('channels', 'monitor_pid').setValue(True)
        mock_viewer_plugin.active_channels = ['Input 1 (V)', 'Input 2 (V)', 'PID PID0 Setpoint (V)']
        
        # Test data acquisition
        data = mock_viewer_plugin._acquire_data()
        
        assert data is not None
        assert len(data) == 3
        assert 'Input 1 (V)' in data
        assert 'Input 2 (V)' in data
        assert 'PID PID0 Setpoint (V)' in data
        
        # Check voltage values are within expected ranges
        assert -1.0 <= data['Input 1 (V)'] <= 1.0
        assert -1.0 <= data['Input 2 (V)'] <= 1.0
        assert -1.0 <= data['PID PID0 Setpoint (V)'] <= 1.0

    def test_grab_data_functionality(self, mock_viewer_plugin):
        """Test grab_data method with mock connection."""
        # Setup mock connection and channels
        mock_viewer_plugin.controller = MockPyRPLConnection(TEST_HOSTNAME)
        mock_viewer_plugin.active_channels = ['Input 1 (V)']
        
        # Mock the data emission
        mock_viewer_plugin.dte_signal = Mock()
        mock_viewer_plugin.dte_signal.emit = Mock()
        mock_viewer_plugin.emit_status = Mock()
        
        # Test data grab
        mock_viewer_plugin.grab_data()
        
        # Verify data was emitted
        mock_viewer_plugin.dte_signal.emit.assert_called_once()
        call_args = mock_viewer_plugin.dte_signal.emit.call_args[0][0]
        assert isinstance(call_args, DataToExport)
        assert call_args.name == 'PyRPL Monitor'
        assert len(call_args.data) == 1

    def test_channel_parameter_changes(self, mock_viewer_plugin):
        """Test channel parameter change handling."""
        mock_viewer_plugin._update_active_channels = Mock()
        
        # Test channel enable/disable
        param = mock_viewer_plugin.settings.child('channels', 'monitor_in2')
        param.setValue(True)
        
        # Mock the path method if it doesn't exist
        if not hasattr(param, 'path'):
            param.path = Mock(return_value=['channels', 'monitor_in2'])
        
        mock_viewer_plugin.commit_settings(param)
        
        mock_viewer_plugin._update_active_channels.assert_called()

    def test_acquisition_timing_validation(self, mock_viewer_plugin):
        """Test acquisition timing constraints."""
        sampling_rate = mock_viewer_plugin.settings.child('acquisition', 'sampling_rate').value()
        max_acq_time = mock_viewer_plugin.settings.child('acquisition', 'max_acq_time').value()
        
        assert 0.1 <= sampling_rate <= 1000.0
        assert 0.001 <= max_acq_time <= 1.0

    def test_data_structure_initialization(self, mock_viewer_plugin):
        """Test PyMoDAQ data structure initialization."""
        mock_viewer_plugin.active_channels = ['Input 1 (V)', 'Input 2 (V)']
        mock_viewer_plugin.dte_signal_temp = Mock()
        mock_viewer_plugin.dte_signal_temp.emit = Mock()
        
        mock_viewer_plugin._initialize_data_structure()
        
        # Verify data structure was emitted
        mock_viewer_plugin.dte_signal_temp.emit.assert_called_once()
        call_args = mock_viewer_plugin.dte_signal_temp.emit.call_args[0][0]
        assert isinstance(call_args, DataToExport)
        assert len(call_args.data) == 2


# ============================================================================
# NOTE: PIDModelPyRPL tests removed - model had circular dependencies
# The working PyRPL plugins provide all needed functionality
# ============================================================================


# ============================================================================
# Scope API Tests
# ============================================================================

@pytest.mark.mock
class TestScopeAPIMock:
    """Test Scope API functionality with mock hardware."""

    @pytest.fixture
    def mock_scope_config(self):
        """Create mock scope configuration."""
        return ScopeConfiguration(
            input_channel=InputChannel.IN1,
            decimation=ScopeDecimation.DEC_64,
            trigger_source=ScopeTriggerSource.IMMEDIATELY,
            trigger_delay=0,
            trigger_level=0.0,
            average=1,
            rolling_mode=False,
            timeout=2.0,
            data_length=1024
        )

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_scope_configuration(self, mock_pyrpl_module, mock_connection_info, mock_scope_config):
        """Test scope configuration with mock hardware."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()

        # Test scope configuration
        success = connection.configure_scope(mock_scope_config)
        assert success is True

        # Verify configuration was applied to mock scope
        scope = mock_pyrpl_instance.redpitaya.scope
        assert scope.decimation == mock_scope_config.decimation.value
        assert scope.trigger_source == mock_scope_config.trigger_source.value
        assert scope.trigger_delay == mock_scope_config.trigger_delay
        assert scope.trigger_level == mock_scope_config.trigger_level
        assert scope.average == mock_scope_config.average
        assert scope.rolling_mode == mock_scope_config.rolling_mode
        assert scope.input == mock_scope_config.input_channel.value

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_scope_acquisition(self, mock_pyrpl_module, mock_connection_info, mock_scope_config):
        """Test scope data acquisition with mock hardware."""
        # Setup mock with predictable acquisition
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_scope(mock_scope_config)

        # Test data acquisition
        result = connection.acquire_scope_data(timeout=1.0)
        assert result is not None

        time_axis, voltage_data = result
        assert len(time_axis) == len(voltage_data)
        assert len(voltage_data) == mock_pyrpl_instance.redpitaya.scope._sample_count
        assert isinstance(time_axis, np.ndarray)
        assert isinstance(voltage_data, np.ndarray)

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_scope_acquisition_timeout(self, mock_pyrpl_module, mock_connection_info, mock_scope_config):
        """Test scope acquisition timeout handling."""
        # Setup mock that never stops (simulates timeout)
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_instance.redpitaya.scope = MockScope(stop_after_polls=None)  # Never stops
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_scope(mock_scope_config)

        # Test timeout handling
        result = connection.acquire_scope_data(timeout=0.1)  # Very short timeout
        assert result is None  # Should timeout and return None

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_scope_control_methods(self, mock_pyrpl_module, mock_connection_info):
        """Test scope start/stop/status methods."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()

        scope = mock_pyrpl_instance.redpitaya.scope

        # Test initial state
        assert scope.stopped() is True
        assert connection.is_scope_running() is False

        # Test start acquisition
        success = connection.start_scope_acquisition()
        assert success is True
        assert scope._acq_running is True
        assert connection.is_scope_running() is True

        # Test stop acquisition
        success = connection.stop_scope_acquisition()
        assert success is True
        assert scope._acq_running is False
        assert connection.is_scope_running() is False

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_scope_getters(self, mock_pyrpl_module, mock_connection_info):
        """Test scope getter methods."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()

        # Test sampling time getter
        sampling_time = connection.get_scope_sampling_time()
        assert sampling_time is not None
        assert sampling_time == mock_pyrpl_instance.redpitaya.scope.sampling_time

        # Test duration getter
        duration = connection.get_scope_duration()
        assert duration is not None
        assert duration == mock_pyrpl_instance.redpitaya.scope.duration


@pytest.mark.hardware
class TestScopeAPIHardware:
    """Test Scope API functionality with real hardware."""

    def safe_scope_config(self, **overrides):
        """Create safe scope configuration for hardware testing."""
        config = get_hardware_config()
        safe_config = ScopeConfiguration(
            input_channel=InputChannel.IN1,
            decimation=ScopeDecimation.DEC_1024,  # Slower sampling for safety
            trigger_source=ScopeTriggerSource.IMMEDIATELY,
            trigger_delay=0,
            trigger_level=0.0,
            average=1,
            rolling_mode=False,
            timeout=config['test_duration'],
            data_length=16384
        )

        # Apply any overrides
        for key, value in overrides.items():
            setattr(safe_config, key, value)

        return safe_config

    def test_real_scope_configuration(self, hardware_connection):
        """Test scope configuration with real hardware."""
        connection = hardware_connection
        scope_config = self.safe_scope_config()

        try:
            # Test scope configuration
            success = connection.configure_scope(scope_config)
            assert success, "Scope configuration failed"

            # Verify configuration was applied (if getter methods work)
            sampling_time = connection.get_scope_sampling_time()
            duration = connection.get_scope_duration()

            if sampling_time is not None and duration is not None:
                assert sampling_time > 0
                assert duration > 0
                logger.info(f"Scope configured: sampling_time={sampling_time}s, duration={duration}s")

        finally:
            # Reset scope to safe state
            try:
                connection.stop_scope_acquisition()
            except Exception as e:
                logger.warning(f"Scope cleanup warning: {e}")

    def test_real_scope_acquisition(self, hardware_connection):
        """Test scope data acquisition with real hardware."""
        connection = hardware_connection
        scope_config = self.safe_scope_config(timeout=3.0)

        try:
            # Configure scope
            success = connection.configure_scope(scope_config)
            assert success

            # Test data acquisition
            result = connection.acquire_scope_data()
            assert result is not None, "Scope acquisition failed"

            time_axis, voltage_data = result
            assert len(time_axis) == len(voltage_data)
            assert len(voltage_data) > 0
            assert isinstance(time_axis, np.ndarray)
            assert isinstance(voltage_data, np.ndarray)

            # Verify data is within reasonable bounds
            assert np.all(np.abs(voltage_data) <= 2.0), "Voltage data outside expected range"

            logger.info(f"Acquired {len(voltage_data)} scope samples, "
                       f"voltage range: [{np.min(voltage_data):.3f}, {np.max(voltage_data):.3f}]V")

        finally:
            connection.stop_scope_acquisition()

    def test_real_scope_control(self, hardware_connection):
        """Test scope start/stop control with real hardware."""
        connection = hardware_connection
        scope_config = self.safe_scope_config()

        try:
            # Configure scope
            success = connection.configure_scope(scope_config)
            assert success

            # Test start acquisition
            success = connection.start_scope_acquisition()
            assert success, "Failed to start scope acquisition"

            # Check if running (may not be reliable on all hardware)
            running_status = connection.is_scope_running()
            if running_status is not None:
                # If we can determine status, verify it's running
                logger.info(f"Scope running status: {running_status}")

            # Test stop acquisition
            success = connection.stop_scope_acquisition()
            assert success, "Failed to stop scope acquisition"

        finally:
            connection.stop_scope_acquisition()


# ============================================================================
# IQ API Tests
# ============================================================================

@pytest.mark.mock
class TestIQAPIMock:
    """Test IQ (Lock-in Amplifier) API functionality with mock hardware."""

    @pytest.fixture
    def mock_iq_config(self):
        """Create mock IQ configuration."""
        return IQConfiguration(
            frequency=1000.0,
            bandwidth=100.0,
            acbandwidth=10000.0,
            phase=0.0,
            gain=1.0,
            quadrature_factor=1.0,
            amplitude=0.0,
            input_channel=InputChannel.IN1,
            output_direct=IQOutputDirect.OFF
        )

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_iq_configuration(self, mock_pyrpl_module, mock_connection_info, mock_iq_config):
        """Test IQ configuration with mock hardware."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()

        # Test IQ configuration
        success = connection.configure_iq(IQChannel.IQ0, mock_iq_config)
        assert success is True

        # Verify configuration was applied to mock IQ
        iq = mock_pyrpl_instance.redpitaya.iq0
        assert iq.frequency == mock_iq_config.frequency
        assert iq.bandwidth == mock_iq_config.bandwidth
        assert iq.acbandwidth == mock_iq_config.acbandwidth
        assert iq.phase == mock_iq_config.phase
        assert iq.gain == mock_iq_config.gain
        assert iq.quadrature_factor == mock_iq_config.quadrature_factor
        assert iq.amplitude == mock_iq_config.amplitude
        assert iq.input == mock_iq_config.input_channel.value
        assert iq.output_direct == mock_iq_config.output_direct.value

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_iq_measurement(self, mock_pyrpl_module, mock_connection_info, mock_iq_config):
        """Test IQ measurement with mock hardware."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_iq(IQChannel.IQ0, mock_iq_config)

        # Test IQ measurement
        result = connection.get_iq_measurement(IQChannel.IQ0)
        assert result is not None

        i_value, q_value = result
        assert isinstance(i_value, (int, float))
        assert isinstance(q_value, (int, float))

        # Test magnitude/phase calculation
        magnitude, phase = connection.calculate_magnitude_phase(i_value, q_value)
        assert magnitude >= 0
        assert -180 <= phase <= 180

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_iq_frequency_control(self, mock_pyrpl_module, mock_connection_info, mock_iq_config):
        """Test IQ frequency control methods."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_iq(IQChannel.IQ0, mock_iq_config)

        # Test set frequency
        new_frequency = 2000.0
        success = connection.set_iq_frequency(IQChannel.IQ0, new_frequency)
        assert success is True

        # Test get frequency
        current_frequency = connection.get_iq_frequency(IQChannel.IQ0)
        assert current_frequency == new_frequency

        # Verify mock IQ was updated
        iq = mock_pyrpl_instance.redpitaya.iq0
        assert iq.frequency == new_frequency

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_iq_phase_control(self, mock_pyrpl_module, mock_connection_info, mock_iq_config):
        """Test IQ phase control methods."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_iq(IQChannel.IQ0, mock_iq_config)

        # Test set phase
        new_phase = 45.0
        success = connection.set_iq_phase(IQChannel.IQ0, new_phase)
        assert success is True

        # Verify mock IQ was updated
        iq = mock_pyrpl_instance.redpitaya.iq0
        assert iq.phase == new_phase

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_mock_iq_output_control(self, mock_pyrpl_module, mock_connection_info, mock_iq_config):
        """Test IQ output enable/disable control."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value=mock_pyrpl_instance)

        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        connection.configure_iq(IQChannel.IQ0, mock_iq_config)

        # Test enable output
        success = connection.enable_iq_output(IQChannel.IQ0, IQOutputDirect.OUT1)
        assert success is True

        # Verify mock IQ was updated
        iq = mock_pyrpl_instance.redpitaya.iq0
        assert iq.output_direct == IQOutputDirect.OUT1.value


@pytest.mark.hardware
class TestIQAPIHardware:
    """Test IQ (Lock-in Amplifier) API functionality with real hardware."""

    def safe_iq_config(self, **overrides):
        """Create safe IQ configuration for hardware testing."""
        safe_config = IQConfiguration(
            frequency=1000.0,  # Safe frequency
            bandwidth=10.0,    # Narrow bandwidth for stability
            acbandwidth=1000.0,
            phase=0.0,
            gain=0.1,          # Low gain for safety
            quadrature_factor=1.0,
            amplitude=0.0,     # No output amplitude
            input_channel=InputChannel.IN1,
            output_direct=IQOutputDirect.OFF  # Output disabled for safety
        )

        # Apply any overrides
        for key, value in overrides.items():
            setattr(safe_config, key, value)

        return safe_config

    def test_real_iq_configuration(self, hardware_connection):
        """Test IQ configuration with real hardware."""
        connection = hardware_connection
        iq_config = self.safe_iq_config()

        try:
            # Test IQ configuration
            success = connection.configure_iq(IQChannel.IQ0, iq_config)
            assert success, "IQ configuration failed"

            # Verify frequency can be read back
            current_frequency = connection.get_iq_frequency(IQChannel.IQ0)
            if current_frequency is not None:
                assert abs(current_frequency - iq_config.frequency) < 1.0  # 1Hz tolerance
                logger.info(f"IQ configured with frequency: {current_frequency}Hz")

        finally:
            # Reset IQ to safe state
            try:
                connection.enable_iq_output(IQChannel.IQ0, IQOutputDirect.OFF)
            except Exception as e:
                logger.warning(f"IQ cleanup warning: {e}")

    def test_real_iq_measurement(self, hardware_connection):
        """Test IQ measurement with real hardware."""
        connection = hardware_connection
        iq_config = self.safe_iq_config()

        try:
            # Configure IQ
            success = connection.configure_iq(IQChannel.IQ0, iq_config)
            assert success

            # Test IQ measurement
            result = connection.get_iq_measurement(IQChannel.IQ0)
            assert result is not None, "IQ measurement failed"

            i_value, q_value = result
            assert isinstance(i_value, (int, float))
            assert isinstance(q_value, (int, float))

            # Test magnitude/phase calculation
            magnitude, phase = connection.calculate_magnitude_phase(i_value, q_value)
            assert magnitude >= 0
            assert -180 <= phase <= 180

            logger.info(f"IQ measurement: I={i_value:.3f}, Q={q_value:.3f}, "
                       f"magnitude={magnitude:.3f}, phase={phase:.1f}°")

        finally:
            connection.enable_iq_output(IQChannel.IQ0, IQOutputDirect.OFF)

    def test_real_iq_frequency_control(self, hardware_connection):
        """Test IQ frequency control with real hardware."""
        connection = hardware_connection
        iq_config = self.safe_iq_config()

        try:
            # Configure IQ
            success = connection.configure_iq(IQChannel.IQ0, iq_config)
            assert success

            # Test frequency changes within safe range
            test_frequencies = [500.0, 1000.0, 2000.0]

            for freq in test_frequencies:
                # Set frequency
                success = connection.set_iq_frequency(IQChannel.IQ0, freq)
                assert success, f"Failed to set frequency to {freq}Hz"

                # Verify frequency was set
                current_freq = connection.get_iq_frequency(IQChannel.IQ0)
                if current_freq is not None:
                    assert abs(current_freq - freq) < 1.0, f"Frequency mismatch: expected {freq}, got {current_freq}"

                # Small delay for hardware to settle
                time.sleep(0.1)

        finally:
            connection.enable_iq_output(IQChannel.IQ0, IQOutputDirect.OFF)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestPluginIntegration:
    """Test integration between different plugin components."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_move_viewer_shared_connection(self, mock_pyrpl_module):
        """Test shared connection between Move and Viewer plugins."""
        # Setup mock PyRPL
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        # Create manager and establish connection
        manager = PyRPLManager()
        manager.cleanup()  # Start fresh
        
        connection = manager.connect_device(TEST_HOSTNAME, "shared_config")
        assert connection is not None
        
        # Verify both plugins can use the same connection
        conn1 = manager.get_connection(TEST_HOSTNAME, "shared_config")
        conn2 = manager.get_connection(TEST_HOSTNAME, "shared_config")
        
        assert conn1 is conn2
        assert conn1 is connection

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_pid_setpoint_monitoring_integration(self, mock_pyrpl_module):
        """Test PID setpoint changes are reflected in monitoring."""
        # Setup mock PyRPL
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        # Create connection
        connection_info = ConnectionInfo(hostname=TEST_HOSTNAME)
        connection = PyRPLConnection(connection_info)
        connection.connect()
        
        # Configure PID
        pid_config = PIDConfiguration(
            setpoint=0.3,
            p_gain=0.1,
            input_channel=InputChannel.IN1,
            output_channel=OutputChannel.OUT1
        )
        
        connection.configure_pid(PIDChannel.PID0, pid_config)
        
        # Change setpoint
        new_setpoint = 0.7
        success = connection.set_pid_setpoint(PIDChannel.PID0, new_setpoint)
        assert success
        
        # Verify setpoint was updated
        current_setpoint = connection.get_pid_setpoint(PIDChannel.PID0)
        assert current_setpoint == new_setpoint
        
        # Verify PID module was updated
        assert mock_pyrpl_instance.redpitaya.pid0.setpoint == new_setpoint

    def test_multiple_plugin_cleanup(self):
        """Test proper cleanup when multiple plugins are used."""
        # This test would require real plugin instances
        # For now, test that manager cleanup works properly
        manager = PyRPLManager()
        
        # Create mock connections manually
        mock_conn1 = Mock()
        mock_conn1.is_connected = True
        mock_conn1.disconnect = Mock()
        
        mock_conn2 = Mock() 
        mock_conn2.is_connected = True
        mock_conn2.disconnect = Mock()
        
        # Add to manager manually for testing
        manager._connections["test1:config1"] = mock_conn1
        manager._connections["test2:config2"] = mock_conn2
        
        # Test cleanup
        manager.cleanup()
        
        # Verify connections were cleaned up
        mock_conn1.disconnect.assert_called_once()
        mock_conn2.disconnect.assert_called_once()
        assert len(manager.get_all_connections()) == 0


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.performance
class TestPerformance:
    """Test performance characteristics of PyRPL plugin operations."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_voltage_reading_performance(self, mock_pyrpl_module):
        """Test voltage reading performance."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection_info = ConnectionInfo(hostname=TEST_HOSTNAME)
        connection = PyRPLConnection(connection_info)
        connection.connect()
        
        # Measure voltage reading time
        num_readings = 100
        start_time = time.time()
        
        for _ in range(num_readings):
            voltage = connection.read_voltage(InputChannel.IN1)
            assert voltage is not None
        
        end_time = time.time()
        avg_time = (end_time - start_time) / num_readings
        
        # Should be very fast for mock operations
        assert avg_time < 0.001  # Less than 1ms per reading

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PYRPL_AVAILABLE', True)
    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl')
    def test_setpoint_change_performance(self, mock_pyrpl_module):
        """Test PID setpoint change performance."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_module.Pyrpl = Mock(return_value = mock_pyrpl_instance)
        
        connection_info = ConnectionInfo(hostname=TEST_HOSTNAME)
        connection = PyRPLConnection(connection_info)
        connection.connect()
        
        # Configure PID first
        pid_config = PIDConfiguration()
        connection.configure_pid(PIDChannel.PID0, pid_config)
        
        # Measure setpoint change time
        num_changes = 50
        setpoints = np.linspace(-1.0, 1.0, num_changes)
        
        start_time = time.time()
        for setpoint in setpoints:
            success = connection.set_pid_setpoint(PIDChannel.PID0, setpoint)
            assert success
        end_time = time.time()
        
        avg_time = (end_time - start_time) / num_changes
        assert avg_time < 0.001  # Less than 1ms per setpoint change

    def test_data_acquisition_throughput(self, mock_viewer_plugin):
        """Test viewer data acquisition throughput."""
        # Setup mock connection
        mock_viewer_plugin.controller = MockPyRPLConnection(TEST_HOSTNAME)
        mock_viewer_plugin.active_channels = ['Input 1 (V)', 'Input 2 (V)']
        
        # Mock data emission
        mock_viewer_plugin.dte_signal = Mock()
        mock_viewer_plugin.dte_signal.emit = Mock()
        mock_viewer_plugin.emit_status = Mock()
        
        # Measure acquisition time
        num_acquisitions = 20
        start_time = time.time()
        
        for _ in range(num_acquisitions):
            mock_viewer_plugin.grab_data()
        
        end_time = time.time()
        avg_time = (end_time - start_time) / num_acquisitions
        
        # Should be fast for mock operations
        assert avg_time < 0.01  # Less than 10ms per acquisition


# ============================================================================
# Hardware Tests (Optional - require real Red Pitaya)
# ============================================================================

# Hardware testing helpers and environment
def get_hardware_config():
    """Parse hardware configuration from environment variables."""
    import os
    config = {
        'hostname': os.getenv('PYRPL_TEST_HOST'),
        'port': int(os.getenv('PYRPL_TEST_PORT', '2222')),
        'timeout': float(os.getenv('PYRPL_TEST_TIMEOUT', '10.0')),
        'config_name': os.getenv('PYRPL_TEST_CONFIG', 'pytest_test'),
        'max_voltage': float(os.getenv('PYRPL_TEST_MAX_VOLTAGE', '0.5')),
        'max_gain': float(os.getenv('PYRPL_TEST_MAX_GAIN', '0.1')),
        'test_duration': float(os.getenv('PYRPL_TEST_DURATION', '5.0')),
        'skip_dangerous': os.getenv('PYRPL_SKIP_DANGEROUS', 'true').lower() == 'true'
    }
    return config

def validate_hardware_environment():
    """Validate hardware test environment and safety parameters."""
    config = get_hardware_config()

    # Check required parameters
    if not config['hostname']:
        return False, "PYRPL_TEST_HOST environment variable required"

    # Validate safety limits
    if config['max_voltage'] > 1.0:
        return False, f"max_voltage {config['max_voltage']} exceeds safe limit of 1.0V"

    if config['max_gain'] > 1.0:
        return False, f"max_gain {config['max_gain']} exceeds safe limit of 1.0"

    return True, "Hardware environment validated"

def safe_pid_config(setpoint=0.0, gain_factor=1.0):
    """Create safe PID configuration for testing."""
    config = get_hardware_config()

    return PIDConfiguration(
        setpoint=min(max(setpoint, -config['max_voltage']), config['max_voltage']),
        p_gain=config['max_gain'] * gain_factor,
        i_gain=config['max_gain'] * gain_factor * 0.1,  # I gain = 10% of P gain
        d_gain=0.0,  # No derivative gain for safety
        input_channel=InputChannel.IN1,
        output_channel=OutputChannel.OUT1,
        voltage_limit_min=-config['max_voltage'],
        voltage_limit_max=config['max_voltage'],
        enabled=True
    )

def hardware_safety_cleanup(connection, channels=None):
    """Perform comprehensive safety cleanup after hardware tests."""
    if not connection or not connection.is_connected:
        return

    try:
        # Disable all PID channels if not specified
        if channels is None:
            channels = [PIDChannel.PID0, PIDChannel.PID1, PIDChannel.PID2]

        for channel in channels:
            try:
                # Set safe setpoint first
                connection.set_pid_setpoint(channel, 0.0)
                # Disable PID
                connection.disable_pid(channel)
            except Exception as e:
                logger.warning(f"Cleanup warning for {channel}: {e}")

        # Set ASG outputs to safe state if available
        try:
            asg_channels = [ASGChannel.ASG0, ASGChannel.ASG1]
            for asg_channel in asg_channels:
                try:
                    connection.enable_asg_output(asg_channel, False)
                except Exception as e:
                    logger.warning(f"ASG {asg_channel.value} cleanup warning: {e}")
        except Exception as e:
            logger.warning(f"ASG cleanup warning: {e}")

        # Set IQ modules to safe state
        try:
            iq_channels = [IQChannel.IQ0, IQChannel.IQ1, IQChannel.IQ2]
            for iq_channel in iq_channels:
                try:
                    connection.enable_iq_output(iq_channel, IQOutputDirect.OFF)
                except Exception as e:
                    logger.warning(f"IQ {iq_channel.value} cleanup warning: {e}")
        except Exception as e:
            logger.warning(f"IQ cleanup warning: {e}")

        # Stop scope acquisition if running
        try:
            connection.stop_scope_acquisition()
        except Exception as e:
            logger.warning(f"Scope cleanup warning: {e}")

    except Exception as e:
        logger.error(f"Safety cleanup failed: {e}")
    finally:
        try:
            connection.disconnect()
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")

@pytest.fixture
def hardware_connection():
    """Fixture providing safe hardware connection with automatic cleanup."""
    is_valid, message = validate_hardware_environment()
    if not is_valid:
        pytest.skip(f"Hardware validation failed: {message}")

    config = get_hardware_config()
    connection = None

    try:
        # Import real PyRPL if available
        import pyrpl  # noqa: F401

        # Create connection info
        connection_info = ConnectionInfo(
            hostname=config['hostname'],
            config_name=config['config_name'],
            port=config['port'],
            connection_timeout=config['timeout'],
            retry_attempts=3,
            retry_delay=1.0
        )

        # Establish connection
        connection = PyRPLConnection(connection_info)
        if not connection.connect():
            pytest.skip(f"Could not connect to Red Pitaya at {config['hostname']}")

        yield connection

    except ImportError:
        pytest.skip("PyRPL not available for hardware tests")
    except Exception as e:
        pytest.skip(f"Hardware connection failed: {e}")
    finally:
        if connection:
            hardware_safety_cleanup(connection)

@pytest.mark.hardware
class TestRealHardware:
    """
    Tests requiring actual Red Pitaya hardware.

    These tests are optional and will be skipped unless:
    1. Hardware is available
    2. PYRPL_TEST_HOST environment variable is set
    3. Tests are run with -m hardware

    Example usage:
        PYRPL_TEST_HOST=rp-f08d6c.local pytest -m hardware

    Environment variables:
        PYRPL_TEST_HOST: Red Pitaya hostname (required)
        PYRPL_TEST_PORT: SSH port (default: 2222)
        PYRPL_TEST_TIMEOUT: Connection timeout (default: 10.0)
        PYRPL_TEST_CONFIG: PyRPL config name (default: pytest_test)
        PYRPL_TEST_MAX_VOLTAGE: Max test voltage (default: 0.5V)
        PYRPL_TEST_MAX_GAIN: Max PID gain (default: 0.1)
        PYRPL_TEST_DURATION: Test duration (default: 5.0s)
        PYRPL_SKIP_DANGEROUS: Skip potentially dangerous tests (default: true)
    """

    def test_hardware_environment_validation(self):
        """Test hardware environment validation."""
        is_valid, message = validate_hardware_environment()
        assert is_valid, f"Hardware environment validation failed: {message}"

        config = get_hardware_config()
        assert config['hostname'] is not None
        assert 0 < config['max_voltage'] <= 1.0
        assert 0 < config['max_gain'] <= 1.0

    def test_real_hardware_connection(self, hardware_connection):
        """Test connection to real Red Pitaya hardware."""
        connection = hardware_connection
        assert connection.is_connected

        # Test basic connection info
        info = connection.get_connection_info()
        assert info is not None
        assert info['state'] == 'connected'

    def test_real_hardware_voltage_reading(self, hardware_connection):
        """Test voltage reading from real hardware."""
        connection = hardware_connection

        # Test single channel reading
        voltage1 = connection.read_voltage(InputChannel.IN1)
        voltage2 = connection.read_voltage(InputChannel.IN2)

        assert voltage1 is not None
        assert voltage2 is not None
        assert -1.5 <= voltage1 <= 1.5  # Allow for some margin beyond ±1V
        assert -1.5 <= voltage2 <= 1.5

        # Test multi-channel reading
        channels = [InputChannel.IN1, InputChannel.IN2]
        voltages = connection.read_multiple_voltages(channels)

        assert len(voltages) == 2
        assert InputChannel.IN1 in voltages
        assert InputChannel.IN2 in voltages

    def test_real_hardware_voltage_stability(self, hardware_connection):
        """Test voltage reading stability with real hardware."""
        connection = hardware_connection
        config = get_hardware_config()

        # Take multiple readings over time
        readings = []
        num_samples = 20
        interval = config['test_duration'] / num_samples

        for i in range(num_samples):
            voltage = connection.read_voltage(InputChannel.IN1)
            readings.append(voltage)
            if i < num_samples - 1:  # Don't sleep after last reading
                time.sleep(interval)

        # Analyze stability
        readings = np.array(readings)
        mean_voltage = np.mean(readings)
        std_dev = np.std(readings)
        min_voltage = np.min(readings)
        max_voltage = np.max(readings)

        # Log statistics for debugging
        logger.info(f"Voltage stability: mean={mean_voltage:.3f}V, std={std_dev:.3f}V, "
                   f"range=[{min_voltage:.3f}, {max_voltage:.3f}]V")

        # Standard deviation should be reasonable (depending on input signal)
        assert std_dev < 0.2, f"Voltage standard deviation {std_dev:.3f}V too high"
        assert max_voltage - min_voltage < 1.0, f"Voltage range {max_voltage - min_voltage:.3f}V too large"

    def test_real_hardware_pid_configuration(self, hardware_connection):
        """Test PID configuration with real hardware."""
        connection = hardware_connection

        # Create safe PID configuration
        pid_config = safe_pid_config(setpoint=0.0, gain_factor=0.5)

        try:
            # Configure PID
            success = connection.configure_pid(PIDChannel.PID0, pid_config)
            assert success, "PID configuration failed"

            # Verify configuration was applied
            current_config = connection.get_pid_configuration(PIDChannel.PID0)
            assert current_config is not None
            assert abs(current_config.setpoint - pid_config.setpoint) < 0.01
            assert abs(current_config.p_gain - pid_config.p_gain) < 0.001
            assert current_config.input_channel == pid_config.input_channel
            assert current_config.output_channel == pid_config.output_channel

        finally:
            # Ensure PID is disabled
            connection.disable_pid(PIDChannel.PID0)

    def test_real_hardware_setpoint_control(self, hardware_connection):
        """Test PID setpoint control with real hardware."""
        connection = hardware_connection
        config = get_hardware_config()

        # Configure PID with minimal gain for safety
        pid_config = safe_pid_config(setpoint=0.0, gain_factor=0.1)

        try:
            success = connection.configure_pid(PIDChannel.PID0, pid_config)
            assert success

            # Test setpoint changes within safe range
            test_setpoints = [-config['max_voltage']/2, 0.0, config['max_voltage']/2]

            for target_setpoint in test_setpoints:
                # Set new setpoint
                success = connection.set_pid_setpoint(PIDChannel.PID0, target_setpoint)
                assert success, f"Failed to set setpoint to {target_setpoint}"

                # Verify setpoint was set
                current_setpoint = connection.get_pid_setpoint(PIDChannel.PID0)
                assert current_setpoint is not None
                assert abs(current_setpoint - target_setpoint) < 0.01, \
                    f"Setpoint mismatch: expected {target_setpoint}, got {current_setpoint}"

                # Small delay to allow hardware to respond
                time.sleep(0.1)

        finally:
            # Reset to safe state
            connection.set_pid_setpoint(PIDChannel.PID0, 0.0)
            connection.disable_pid(PIDChannel.PID0)

    def test_real_hardware_multi_channel_operation(self, hardware_connection):
        """Test multiple PID channels operating simultaneously."""
        connection = hardware_connection

        channels = [PIDChannel.PID0, PIDChannel.PID1]
        configs = []

        try:
            # Configure multiple PIDs with different setpoints
            for i, channel in enumerate(channels):
                setpoint = 0.1 * (i + 1)  # 0.1V, 0.2V
                pid_config = safe_pid_config(setpoint=setpoint, gain_factor=0.05)
                configs.append(pid_config)

                success = connection.configure_pid(channel, pid_config)
                assert success, f"Failed to configure {channel}"

            # Verify all configurations
            for channel, expected_config in zip(channels, configs):
                current_config = connection.get_pid_configuration(channel)
                assert current_config is not None
                assert abs(current_config.setpoint - expected_config.setpoint) < 0.01

                # Test setpoint changes
                new_setpoint = expected_config.setpoint * 0.5
                success = connection.set_pid_setpoint(channel, new_setpoint)
                assert success

                verified_setpoint = connection.get_pid_setpoint(channel)
                assert abs(verified_setpoint - new_setpoint) < 0.01

        finally:
            # Clean up all channels
            for channel in channels:
                connection.set_pid_setpoint(channel, 0.0)
                connection.disable_pid(channel)

    def test_real_hardware_connection_recovery(self, hardware_connection):
        """Test connection recovery after temporary disconnection."""
        connection = hardware_connection
        original_state = connection.is_connected
        assert original_state

        # Test connection state detection
        assert connection.get_connection_info()['state'] == 'connected'

        # Simulate a brief disconnection (if supported by wrapper)
        try:
            # This test is more about verifying the connection remains stable
            # and can detect state changes
            time.sleep(1.0)
            assert connection.is_connected

            # Test that operations still work
            voltage = connection.read_voltage(InputChannel.IN1)
            assert voltage is not None

        except Exception as e:
            pytest.fail(f"Connection recovery test failed: {e}")

    @pytest.mark.skipif(
        get_hardware_config().get('skip_dangerous', True),
        reason="Dangerous tests disabled by PYRPL_SKIP_DANGEROUS=true"
    )
    def test_real_hardware_performance_stress(self, hardware_connection):
        """Stress test hardware performance with rapid operations."""
        connection = hardware_connection
        config = get_hardware_config()

        # Configure PID with minimal gain for safety
        pid_config = safe_pid_config(setpoint=0.0, gain_factor=0.01)

        try:
            success = connection.configure_pid(PIDChannel.PID0, pid_config)
            assert success

            # Rapid voltage readings
            start_time = time.time()
            num_readings = 100

            voltages = []
            for _ in range(num_readings):
                voltage = connection.read_voltage(InputChannel.IN1)
                voltages.append(voltage)

            reading_time = time.time() - start_time
            avg_reading_time = reading_time / num_readings

            logger.info(f"Hardware reading performance: {avg_reading_time*1000:.2f}ms per reading")

            # Rapid setpoint changes
            start_time = time.time()
            num_setpoints = 50
            max_setpoint = config['max_voltage'] / 4  # Quarter of max for safety

            for i in range(num_setpoints):
                setpoint = max_setpoint * np.sin(2 * np.pi * i / num_setpoints)
                success = connection.set_pid_setpoint(PIDChannel.PID0, setpoint)
                assert success

            setpoint_time = time.time() - start_time
            avg_setpoint_time = setpoint_time / num_setpoints

            logger.info(f"Hardware setpoint performance: {avg_setpoint_time*1000:.2f}ms per setpoint")

            # Verify all readings were valid
            assert all(v is not None for v in voltages)
            assert all(-2.0 <= v <= 2.0 for v in voltages)  # Reasonable bounds

            # Performance assertions (these may need adjustment based on actual hardware)
            assert avg_reading_time < 0.1, f"Reading time {avg_reading_time*1000:.2f}ms too slow"
            assert avg_setpoint_time < 0.1, f"Setpoint time {avg_setpoint_time*1000:.2f}ms too slow"

        finally:
            # Ensure safe state
            connection.set_pid_setpoint(PIDChannel.PID0, 0.0)
            connection.disable_pid(PIDChannel.PID0)


# ============================================================================
# Test Execution and Reporting
# ============================================================================

def test_suite_coverage():
    """Verify test suite covers all major functionality."""
    # This test ensures we have comprehensive coverage
    
    # Count test methods in each category
    test_counts = {
        "mock": len([m for m in dir(TestPyRPLWrapperMock) if m.startswith('test_')]) +
               len([m for m in dir(TestDAQMovePyRPLPID) if m.startswith('test_')]) +
               len([m for m in dir(TestDAQ0DViewerPyRPL) if m.startswith('test_')]),
               # TestPIDModelPyRPL removed - had circular dependencies
        "thread_safety": len([m for m in dir(TestPyRPLWrapperThreadSafety) if m.startswith('test_')]),
        "error_handling": len([m for m in dir(TestPyRPLWrapperErrorHandling) if m.startswith('test_')]),
        "integration": len([m for m in dir(TestPluginIntegration) if m.startswith('test_')]),
        "performance": len([m for m in dir(TestPerformance) if m.startswith('test_')]),
        "hardware": len([m for m in dir(TestRealHardware) if m.startswith('test_')])
    }
    
    # Ensure we have reasonable coverage
    assert test_counts["mock"] >= 15, "Should have at least 15 mock tests"
    assert test_counts["thread_safety"] >= 2, "Should have thread safety tests"
    assert test_counts["error_handling"] >= 3, "Should have error handling tests" 
    assert test_counts["integration"] >= 2, "Should have integration tests"
    assert test_counts["performance"] >= 3, "Should have performance tests"
    assert test_counts["hardware"] >= 2, "Should have hardware tests"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])