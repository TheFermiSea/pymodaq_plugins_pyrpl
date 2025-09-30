# -*- coding: utf-8 -*-
"""
Tests for Singleton Mock Instance Management

This module tests the unified mock mode architecture to ensure that all plugins
share the same EnhancedMockPyRPLConnection instance for coordinated simulation.

Test Areas:
- Singleton mock instance creation and sharing
- Thread-safe access to shared mock instance
- PyRPLManager integration with mock mode
- Mock connection adapter functionality
- Coordinated simulation state management
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import (
    PyRPLManager, 
    get_shared_mock_instance, 
    reset_shared_mock_instance,
    get_mock_instance_info,
    create_pyrpl_connection,
    PyRPLMockConnectionAdapter
)


class TestSingletonMockInstance:
    """Test shared mock instance singleton pattern."""
    
    def setup_method(self):
        """Reset mock instance before each test."""
        reset_shared_mock_instance()
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_shared_mock_instance()
    
    def test_singleton_creation(self):
        """Test that only one mock instance is created."""
        hostname = "test-mock.local"
        
        # First call creates the instance
        instance1 = get_shared_mock_instance(hostname)
        assert instance1 is not None
        
        # Second call returns same instance
        instance2 = get_shared_mock_instance(hostname)
        assert instance2 is instance1
        
        # Different hostname still returns same instance (by design)
        instance3 = get_shared_mock_instance("different-host.local")
        assert instance3 is instance1
    
    def test_thread_safe_singleton_creation(self):
        """Test thread-safe singleton creation under concurrent access."""
        hostname = "test-threaded.local"
        instances = []
        create_errors = []
        
        def create_instance():
            try:
                instance = get_shared_mock_instance(hostname)
                instances.append(instance)
            except Exception as e:
                create_errors.append(e)
        
        # Start multiple threads trying to create instance simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
        
        # Start all threads at roughly the same time
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(create_errors) == 0, f"Creation errors: {create_errors}"
        
        # Verify all threads got the same instance
        assert len(instances) == 10
        unique_instances = set(id(instance) for instance in instances if instance is not None)
        assert len(unique_instances) == 1, f"Expected 1 unique instance, got {len(unique_instances)}"
    
    def test_mock_instance_reset(self):
        """Test mock instance reset functionality."""
        hostname = "test-reset.local"
        
        # Create initial instance
        instance1 = get_shared_mock_instance(hostname)
        assert instance1 is not None
        
        # Reset and verify new instance is created
        reset_shared_mock_instance()
        instance2 = get_shared_mock_instance(hostname)
        assert instance2 is not None
        assert instance2 is not instance1
    
    def test_mock_instance_info(self):
        """Test mock instance information retrieval."""
        # Initially no instance
        info = get_mock_instance_info()
        assert info["exists"] is False
        assert info["hostname"] is None
        
        # After creating instance
        hostname = "test-info.local"
        instance = get_shared_mock_instance(hostname)
        assert instance is not None
        
        info = get_mock_instance_info()
        assert info["exists"] is True
        assert info["hostname"] == hostname
    
    @pytest.mark.mock
    def test_enhanced_mock_unavailable(self):
        """Test behavior when EnhancedMockPyRPLConnection is unavailable."""
        with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.ENHANCED_MOCK_AVAILABLE', False):
            instance = get_shared_mock_instance("test.local")
            assert instance is None


class TestPyRPLManagerMockMode:
    """Test PyRPLManager integration with mock mode."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        # Get clean manager instance
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()  # Clean slate
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    def test_mock_mode_connection_creation(self):
        """Test PyRPLManager creates mock connections correctly."""
        hostname = "test-manager.local"
        config_name = "test_config"
        
        # Connect in mock mode
        connection = self.manager.connect_device(
            hostname, config_name, mock_mode=True
        )
        
        assert connection is not None
        assert connection.is_connected
        assert connection.hostname == hostname
        assert connection.config_name == config_name
    
    def test_shared_mock_across_connections(self):
        """Test that multiple connections share the same mock instance."""
        hostname = "test-shared.local"
        
        # Create multiple connections
        conn1 = self.manager.connect_device(hostname, "config1", mock_mode=True)
        conn2 = self.manager.connect_device(hostname, "config2", mock_mode=True)
        
        assert conn1 is not None
        assert conn2 is not None
        
        # Both connections should use the same underlying mock instance
        # (through the adapter pattern)
        assert hasattr(conn1, '_mock_instance')
        assert hasattr(conn2, '_mock_instance')
        assert conn1._mock_instance is conn2._mock_instance
    
    def test_mock_real_mode_isolation(self):
        """Test that mock and real modes don't interfere."""
        hostname = "test-isolation.local"
        
        # Create mock connection
        mock_conn = self.manager.connect_device(hostname, "mock_config", mock_mode=True)
        assert mock_conn is not None
        
        # Attempt real connection (should fail in test environment, but not crash)
        real_conn = self.manager.connect_device(hostname, "real_config", mock_mode=False)
        # real_conn may be None due to no hardware, but shouldn't affect mock_conn
        
        assert mock_conn.is_connected  # Mock connection still works
    
    def test_connection_reference_counting_mock(self):
        """Test reference counting works with mock connections."""
        hostname = "test-refcount.local"
        config_name = "ref_config"
        
        # First connection
        conn1 = self.manager.connect_device(hostname, config_name, mock_mode=True)
        assert conn1 is not None
        initial_refs = getattr(conn1, '_reference_count', 1)
        
        # Second connection to same host/config should increment references
        conn2 = self.manager.connect_device(hostname, config_name, mock_mode=True)
        assert conn2 is not None
        
        # Should be the same connection object with incremented reference count
        assert conn1 is conn2
        assert conn1._reference_count == initial_refs + 1


class TestPyRPLMockConnectionAdapter:
    """Test the mock connection adapter functionality."""
    
    def test_adapter_interface_compatibility(self):
        """Test that adapter provides PyRPLConnection-compatible interface."""
        # Create mock instance
        mock_instance = Mock()
        mock_instance.is_connected = True
        mock_instance.hostname = "adapter-test.local"
        mock_instance.get_connection_info.return_value = {"test": "info"}
        
        # Create adapter
        adapter = PyRPLMockConnectionAdapter(mock_instance, "test.local", "test_config")
        
        # Test interface compatibility
        assert adapter.is_connected == True
        assert adapter.hostname == "test.local"
        assert adapter.config_name == "test_config"
        
        # Test reference counting
        initial_refs = adapter._reference_count
        new_refs = adapter.add_reference()
        assert new_refs == initial_refs + 1
        
        remaining_refs = adapter.remove_reference()
        assert remaining_refs == initial_refs
    
    def test_adapter_delegates_to_mock(self):
        """Test that adapter correctly delegates calls to mock instance."""
        # Create mock instance with custom methods
        mock_instance = Mock()
        mock_instance.custom_method.return_value = "mock_result"
        mock_instance.custom_property = "mock_value"
        
        adapter = PyRPLMockConnectionAdapter(mock_instance, "test.local", "config")
        
        # Test method delegation
        result = adapter.custom_method("test_arg")
        assert result == "mock_result"
        mock_instance.custom_method.assert_called_once_with("test_arg")
        
        # Test property delegation
        assert adapter.custom_property == "mock_value"
    
    def test_adapter_connection_info(self):
        """Test adapter provides comprehensive connection information."""
        mock_instance = Mock()
        mock_instance.get_connection_info.return_value = {
            "hostname": "mock-host.local",
            "is_connected": True,
            "state": "connected"
        }
        
        adapter = PyRPLMockConnectionAdapter(mock_instance, "adapter-host.local", "adapter_config")
        
        info = adapter.get_connection_info()
        assert info["config_name"] == "adapter_config"
        assert info["reference_count"] == 1
        assert info["adapter_type"] == "PyRPLMockConnectionAdapter"
        assert info["hostname"] == "mock-host.local"  # From mock instance
        assert info["is_connected"] == True


class TestCreatePyRPLConnection:
    """Test the create_pyrpl_connection function."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
    
    def teardown_method(self):
        """Cleanup after tests."""
        reset_shared_mock_instance()
    
    def test_create_mock_connection(self):
        """Test creating connection in mock mode."""
        connection = create_pyrpl_connection(
            hostname="test-create.local",
            config_name="test_config",
            mock_mode=True
        )
        
        assert connection is not None
        assert connection.is_connected
        assert isinstance(connection, PyRPLMockConnectionAdapter)
    
    def test_create_real_connection(self):
        """Test creating connection in real mode."""
        # This will likely fail due to no hardware, but shouldn't crash
        connection = create_pyrpl_connection(
            hostname="test-real.local",
            config_name="test_config",
            mock_mode=False
        )
        
        # Connection may be None due to no hardware, but function should not crash
        # The important thing is that it doesn't try to create a mock instance
        if connection is not None:
            assert not isinstance(connection, PyRPLMockConnectionAdapter)
    
    def test_mock_connection_sharing(self):
        """Test that multiple mock connections share the same underlying instance."""
        conn1 = create_pyrpl_connection("host1.local", "config1", mock_mode=True)
        conn2 = create_pyrpl_connection("host2.local", "config2", mock_mode=True)
        
        assert conn1 is not None
        assert conn2 is not None
        
        # Different adapter instances but same underlying mock
        assert conn1 is not conn2
        assert conn1._mock_instance is conn2._mock_instance


@pytest.mark.integration
class TestMockCoordinationIntegration:
    """Integration tests for coordinated mock simulation."""
    
    def setup_method(self):
        """Setup integration test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
    
    def teardown_method(self):
        """Cleanup integration tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    def test_multi_plugin_simulation_sharing(self):
        """Test that multiple plugins share simulation state."""
        # Simulate connections from different plugin types
        pid_conn = self.manager.connect_device("rp-test.local", "pid_config", mock_mode=True)
        scope_conn = self.manager.connect_device("rp-test.local", "scope_config", mock_mode=True)
        viewer_conn = self.manager.connect_device("rp-test.local", "viewer_config", mock_mode=True)
        
        assert pid_conn is not None
        assert scope_conn is not None  
        assert viewer_conn is not None
        
        # All should share the same mock instance
        assert pid_conn._mock_instance is scope_conn._mock_instance
        assert scope_conn._mock_instance is viewer_conn._mock_instance
        
        # Test coordinated behavior - changes through one connection
        # should be visible through others
        mock_instance = pid_conn._mock_instance
        if hasattr(mock_instance, 'set_pid_setpoint'):
            # Set PID setpoint through PID connection
            success = mock_instance.set_pid_setpoint(mock_instance.pid_states.get('PID0', 'pid0'), 0.5)
            if success and hasattr(mock_instance, 'read_voltage'):
                # Read voltage through viewer connection should reflect the change
                voltage = mock_instance.read_voltage(mock_instance.base_voltages.get('IN1', 'in1'))
                assert voltage is not None
                # The exact value depends on simulation, but it should be a number
                assert isinstance(voltage, (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])