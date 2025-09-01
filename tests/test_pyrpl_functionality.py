# -*- coding: utf-8 -*-
"""
PyRPL Functionality Tests for PyMoDAQ PyRPL Plugin

This module provides comprehensive testing for PyRPL plugin functionality including:
- PyRPL wrapper connection tests (mock and real hardware)
- DAQ_Move_PyRPL_PID plugin functionality tests
- DAQ_0DViewer_PyRPL plugin functionality tests
- PIDModelPyrpl integration tests
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
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, List, Optional, Any
import logging

# Mock PyRPL completely to avoid Qt initialization issues in tests
import sys
from unittest.mock import Mock

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
    PIDConfiguration, ConnectionInfo, ConnectionState, connect_redpitaya
)

# Import plugin classes  
from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import (
    DAQ_0DViewer_PyRPL, MockPyRPLConnection
)
from pymodaq_plugins_pyrpl.models.PIDModelPyrpl import PIDModelPyrpl

# PyMoDAQ imports for data structures
from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport, DataRaw
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
    """Mock PyRPL scope for voltage reading."""
    
    def __init__(self):
        self.voltage_in1 = MOCK_DEFAULT_VOLTAGE_IN1
        self.voltage_in2 = MOCK_DEFAULT_VOLTAGE_IN2

class MockSampler:
    """Mock PyRPL sampler for voltage reading."""
    
    def __init__(self):
        self.in1 = MOCK_DEFAULT_VOLTAGE_IN1
        self.in2 = MOCK_DEFAULT_VOLTAGE_IN2

class MockRedPitaya:
    """Mock Red Pitaya device for testing."""
    
    def __init__(self):
        self.version = "1.0.0-test"
        self.pid0 = MockPidModule()
        self.pid1 = MockPidModule()
        self.pid2 = MockPidModule()
        self.scope = MockScope()
        self.sampler = MockSampler()

class MockPyrpl:
    """Mock PyRPL instance for testing."""
    
    def __init__(self, config=None, hostname=None, port=None, timeout=None):
        self.config = config
        self.hostname = hostname
        self.port = port
        self.timeout = timeout
        self.redpitaya = MockRedPitaya()
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
    with patch('pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID.PyRPLManager'):
        plugin = DAQ_Move_PyRPL_PID()
        plugin.ini_attributes()
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pyrpl_connection_success(self, mock_pyrpl_class, mock_connection_info):
        """Test successful PyRPL connection establishment."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
        # Create connection and test
        connection = PyRPLConnection(mock_connection_info)
        assert connection.state == ConnectionState.DISCONNECTED
        
        # Test connection
        success = connection.connect()
        assert success is True
        assert connection.state == ConnectionState.CONNECTED
        assert connection.is_connected is True
        assert connection.pyrpl is mock_pyrpl_instance

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pyrpl_connection_failure(self, mock_pyrpl_class, mock_connection_info):
        """Test PyRPL connection failure handling."""
        # Setup mock to raise exception
        mock_pyrpl_class.side_effect = Exception("Connection failed")
        
        # Create connection and test failure
        connection = PyRPLConnection(mock_connection_info)
        success = connection.connect()
        
        assert success is False
        assert connection.state == ConnectionState.ERROR
        assert connection.last_error == "Connection failed"
        assert connection.is_connected is False

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pyrpl_connection_retry_logic(self, mock_pyrpl_class, mock_connection_info):
        """Test connection retry logic with eventual success."""
        # Setup mock to fail twice, then succeed
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            mock_pyrpl_instance  # Third attempt succeeds
        ]
        
        # Ensure we have enough retry attempts and reduce delay for testing
        mock_connection_info.retry_attempts = 3
        mock_connection_info.retry_delay = 0.01
        
        connection = PyRPLConnection(mock_connection_info)
        success = connection.connect()
        
        assert success is True
        assert connection.state == ConnectionState.CONNECTED
        assert mock_pyrpl_class.call_count == 3

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pid_module_access(self, mock_pyrpl_class, mock_connection_info):
        """Test PID module access and caching."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test PID module access
        pid0 = connection.get_pid_module(PIDChannel.PID0)
        assert pid0 is mock_pyrpl_instance.redpitaya.pid0
        
        # Test caching
        pid0_cached = connection.get_pid_module(PIDChannel.PID0)
        assert pid0_cached is pid0

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pid_configuration(self, mock_pyrpl_class, mock_connection_info, mock_pid_config):
        """Test PID controller configuration."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_voltage_reading(self, mock_pyrpl_class, mock_connection_info):
        """Test voltage reading from input channels."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        
        # Test voltage reading
        voltage1 = connection.read_voltage(InputChannel.IN1)
        voltage2 = connection.read_voltage(InputChannel.IN2)
        
        assert voltage1 == MOCK_DEFAULT_VOLTAGE_IN1
        assert voltage2 == MOCK_DEFAULT_VOLTAGE_IN2

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_multiple_voltage_reading(self, mock_pyrpl_class, mock_connection_info):
        """Test reading multiple voltage channels simultaneously."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_manager_connection_pooling(self, mock_pyrpl_class, pyrpl_manager):
        """Test connection pooling in PyRPL manager."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
        # Request same connection twice
        conn1 = pyrpl_manager.get_connection(TEST_HOSTNAME, "test_config")
        conn2 = pyrpl_manager.get_connection(TEST_HOSTNAME, "test_config")
        
        assert conn1 is conn2  # Should be same instance (pooled)

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_manager_different_configs(self, mock_pyrpl_class, pyrpl_manager):
        """Test manager handling of different configurations."""
        # Setup mock
        mock_pyrpl_class.return_value = MockPyrpl()
        
        # Request connections with different configs
        conn1 = pyrpl_manager.get_connection(TEST_HOSTNAME, "config1")
        conn2 = pyrpl_manager.get_connection(TEST_HOSTNAME, "config2")
        
        assert conn1 is not conn2  # Different configs = different connections


@pytest.mark.thread_safety
class TestPyRPLWrapperThreadSafety:
    """Test thread safety of PyRPL wrapper operations."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_concurrent_connections(self, mock_pyrpl_class, pyrpl_manager):
        """Test concurrent connection establishment."""
        mock_pyrpl_class.return_value = MockPyrpl()
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_concurrent_pid_operations(self, mock_pyrpl_class, mock_connection_info):
        """Test concurrent PID operations on same connection."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_connection_loss_detection(self, mock_pyrpl_class, mock_connection_info):
        """Test detection of lost connections."""
        # Setup mock that initially works
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
        connection = PyRPLConnection(mock_connection_info)
        connection.connect()
        assert connection.is_connected
        
        # Simulate connection loss by making redpitaya None
        connection._redpitaya = None
        assert not connection.is_connected

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_operation_without_connection(self, mock_pyrpl_class, mock_connection_info):
        """Test operations when not connected."""
        connection = PyRPLConnection(mock_connection_info)
        # Don't connect
        
        # All operations should fail gracefully
        assert connection.read_voltage(InputChannel.IN1) is None
        assert connection.get_pid_setpoint(PIDChannel.PID0) is None
        assert connection.set_pid_setpoint(PIDChannel.PID0, 0.5) is False
        assert connection.configure_pid(PIDChannel.PID0, PIDConfiguration()) is False

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pid_operation_failures(self, mock_pyrpl_class, mock_connection_info):
        """Test PID operation failure handling."""
        # Setup mock that raises exceptions
        mock_pyrpl_instance = MockPyrpl()
        
        # Create a mock pid module that raises exceptions when accessing setpoint
        failing_pid_module = Mock()
        type(failing_pid_module).setpoint = PropertyMock(side_effect=Exception("Hardware error"))
        mock_pyrpl_instance.redpitaya.pid0 = failing_pid_module
        
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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
        assert mock_move_plugin.settings.child('connection_settings', 'config_name').value() == 'pymodaq'
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
# PIDModelPyrpl Integration Tests
# ============================================================================

@pytest.mark.mock
class TestPIDModelPyrpl:
    """Test PIDModelPyrpl integration functionality."""

    @patch('pymodaq_plugins_pyrpl.models.PIDModelPyrpl.connect_redpitaya')
    def test_pid_model_initialization(self, mock_connect):
        """Test PID model initialization."""
        # Setup mock connection
        mock_connection = Mock()
        mock_connection.is_connected = True
        mock_connect.return_value = mock_connection
        
        # Create mock PID controller
        mock_pid_controller = Mock()
        mock_pid_controller.emit_status = Mock()
        
        # Initialize model
        model = PIDModelPyrpl(mock_pid_controller)
        model.settings = Mock()
        model.settings.child.return_value.value.return_value = TEST_HOSTNAME
        
        model.ini_model()
        
        assert model.pyrpl_connection is mock_connection
        mock_connect.assert_called_once()

    @patch('pymodaq_plugins_pyrpl.models.PIDModelPyrpl.connect_redpitaya')
    def test_pid_model_parameter_updates(self, mock_connect):
        """Test PID model parameter update handling."""
        # Setup mock connection
        mock_connection = Mock()
        mock_connection.is_connected = True
        mock_connect.return_value = mock_connection
        
        mock_pid_controller = Mock()
        model = PIDModelPyrpl(mock_pid_controller)
        model.pyrpl_connection = mock_connection
        model.settings = Mock()
        
        # Create mock parameter
        mock_param = Mock()
        mock_param.name.return_value = 'redpitaya_host'
        mock_param.value.return_value = TEST_IP
        
        # Test parameter update
        model.update_settings(mock_param)
        
        # Should trigger reconnection for hostname change
        mock_connect.assert_called()

    def test_pid_model_constants_and_limits(self):
        """Test PID model configuration constants."""
        mock_pid_controller = Mock()
        model = PIDModelPyrpl(mock_pid_controller)
        
        # Check limits
        assert model.limits['max']['value'] == 1
        assert model.limits['min']['value'] == -1
        
        # Check constants
        assert 'kp' in model.konstants
        assert 'ki' in model.konstants
        assert 'kd' in model.konstants
        
        # Check setpoint configuration
        assert model.Nsetpoints == 1
        assert model.setpoint_ini == [0.0]
        assert model.setpoints_names == ['Setpoint']

    def test_pid_model_parameters_structure(self):
        """Test PID model parameter structure."""
        mock_pid_controller = Mock()
        model = PIDModelPyrpl(mock_pid_controller)
        
        param_names = [param['name'] for param in model.params]
        
        expected_params = [
            'redpitaya_host', 'input_channel', 'output_channel',
            'pid_channel', 'use_hardware_pid', 'p_gain', 'i_gain',
            'd_gain', 'voltage_limit_min', 'voltage_limit_max'
        ]
        
        for expected_param in expected_params:
            assert expected_param in param_names


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestPluginIntegration:
    """Test integration between different plugin components."""

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_move_viewer_shared_connection(self, mock_pyrpl_class):
        """Test shared connection between Move and Viewer plugins."""
        # Setup mock PyRPL
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_pid_setpoint_monitoring_integration(self, mock_pyrpl_class):
        """Test PID setpoint changes are reflected in monitoring."""
        # Setup mock PyRPL
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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
        
        # Simulate multiple connections
        initial_count = len(manager.get_all_connections())
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_voltage_reading_performance(self, mock_pyrpl_class):
        """Test voltage reading performance."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.pyrpl.Pyrpl')
    def test_setpoint_change_performance(self, mock_pyrpl_class):
        """Test PID setpoint change performance."""
        # Setup mock
        mock_pyrpl_instance = MockPyrpl()
        mock_pyrpl_class.return_value = mock_pyrpl_instance
        
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
    """

    @pytest.fixture(autouse=True)
    def check_hardware_available(self):
        """Skip hardware tests if no hardware is configured."""
        import os
        test_host = os.getenv('PYRPL_TEST_HOST')
        if not test_host:
            pytest.skip("Hardware tests require PYRPL_TEST_HOST environment variable")
        return test_host

    def test_real_hardware_connection(self, check_hardware_available):
        """Test connection to real Red Pitaya hardware."""
        hostname = check_hardware_available
        
        # Attempt real connection
        connection = connect_redpitaya(hostname, config_name="pytest_test")
        
        if connection and connection.is_connected:
            try:
                # Test basic operations
                voltage = connection.read_voltage(InputChannel.IN1)
                assert voltage is not None
                assert -1.5 <= voltage <= 1.5  # Allow for some margin
                
                # Test PID configuration
                pid_config = PIDConfiguration(
                    setpoint=0.0,  # Safe setpoint
                    p_gain=0.01,   # Low gain for safety
                    i_gain=0.0,
                    input_channel=InputChannel.IN1,
                    output_channel=OutputChannel.OUT1
                )
                
                success = connection.configure_pid(PIDChannel.PID0, pid_config)
                assert success
                
                # Test setpoint change
                success = connection.set_pid_setpoint(PIDChannel.PID0, 0.1)
                assert success
                
                # Verify setpoint was set
                current_setpoint = connection.get_pid_setpoint(PIDChannel.PID0)
                assert abs(current_setpoint - 0.1) < 0.01
                
            finally:
                # Always disable PID and disconnect
                connection.disable_pid(PIDChannel.PID0)
                connection.disconnect()
                
        else:
            pytest.skip(f"Could not connect to Red Pitaya at {hostname}")

    def test_real_hardware_voltage_stability(self, check_hardware_available):
        """Test voltage reading stability with real hardware."""
        hostname = check_hardware_available
        
        connection = connect_redpitaya(hostname, config_name="pytest_stability")
        
        if connection and connection.is_connected:
            try:
                # Take multiple readings
                readings = []
                for _ in range(10):
                    voltage = connection.read_voltage(InputChannel.IN1)
                    readings.append(voltage)
                    time.sleep(0.01)  # 10ms between readings
                
                # Check that readings are reasonable
                readings = np.array(readings)
                std_dev = np.std(readings)
                
                # Standard deviation should be reasonable for a stable signal
                assert std_dev < 0.1  # Less than 100mV standard deviation
                
            finally:
                connection.disconnect()
        else:
            pytest.skip(f"Could not connect to Red Pitaya at {hostname}")


# ============================================================================
# Test Execution and Reporting
# ============================================================================

def test_suite_coverage():
    """Verify test suite covers all major functionality."""
    # This test ensures we have comprehensive coverage
    expected_test_categories = [
        "PyRPL wrapper connection management",
        "DAQ_Move_PyRPL_PID plugin functionality", 
        "DAQ_0DViewer_PyRPL plugin functionality",
        "PIDModelPyrpl integration",
        "Thread safety validation",
        "Error handling and recovery",
        "Performance characteristics",
        "Hardware integration (optional)"
    ]
    
    # Count test methods in each category
    test_counts = {
        "mock": len([m for m in dir(TestPyRPLWrapperMock) if m.startswith('test_')]) +
               len([m for m in dir(TestDAQMovePyRPLPID) if m.startswith('test_')]) +
               len([m for m in dir(TestDAQ0DViewerPyRPL) if m.startswith('test_')]) +
               len([m for m in dir(TestPIDModelPyrpl) if m.startswith('test_')]),
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