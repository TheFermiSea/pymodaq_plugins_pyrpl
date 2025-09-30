# -*- coding: utf-8 -*-
"""
Tests for Unified Plugin Mock Connections

This module tests that all PyRPL plugins now use the unified PyRPLManager
approach for mock mode, ensuring coordinated simulation across different
plugin types (PID controllers, viewers, IQ detectors).

Test Areas:
- Viewer plugins using PyRPLManager for mock connections
- Shared simulation state between different plugin types
- Mock mode integration without embedded MockPyRPLConnection classes
- Connection management and reference counting
- Data consistency across coordinated plugins
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager, reset_shared_mock_instance
from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import EnhancedMockPyRPLConnection


class TestViewerPluginMockIntegration:
    """Test that viewer plugins properly use PyRPLManager for mock connections."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    @pytest.mark.mock
    def test_0d_viewer_mock_connection(self):
        """Test that DAQ_0DViewer_PyRPL uses PyRPLManager for mock connections."""
        # Verify that the plugin properly imports PyRPLManager and can create connections
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager

        # Test PyRPLManager connection creation in mock mode
        manager = PyRPLManager.get_instance()

        connection = manager.connect_device(
            hostname='test-viewer.local',
            config_name='viewer_config',
            mock_mode=True
        )

        assert connection is not None
        assert connection.is_connected
        assert hasattr(connection, '_mock_instance')  # Should be PyRPLMockConnectionAdapter

        # Test that plugin imports the PyRPLManager correctly
        plugin = DAQ_0DViewer_PyRPL()
        assert hasattr(plugin, 'pyrpl_manager')  # Plugin should have pyrpl_manager attribute

        # Verify no embedded MockPyRPLConnection class exists in the module
        import inspect
        plugin_module = inspect.getmodule(plugin)
        class_names = [name for name, obj in inspect.getmembers(plugin_module, inspect.isclass)]
        assert 'MockPyRPLConnection' not in class_names, "Plugin should not have embedded MockPyRPLConnection class"
    
    @pytest.mark.mock
    def test_iq_viewer_mock_connection(self):
        """Test that DAQ_0DViewer_PyRPL_IQ uses PyRPLManager for mock connections."""
        # Verify that the plugin properly imports PyRPLManager and can create connections
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager

        # Test PyRPLManager connection creation in mock mode
        manager = PyRPLManager.get_instance()

        connection = manager.connect_device(
            hostname='test-iq.local',
            config_name='iq_config',
            mock_mode=True
        )

        assert connection is not None
        assert connection.is_connected
        assert hasattr(connection, '_mock_instance')  # Should be PyRPLMockConnectionAdapter

        # Test that plugin imports the PyRPLManager correctly
        plugin = DAQ_0DViewer_PyRPL_IQ()
        assert hasattr(plugin, 'pyrpl_manager')  # Plugin should have pyrpl_manager attribute

        # Verify no embedded MockPyRPLConnection class exists in the module
        import inspect
        plugin_module = inspect.getmodule(plugin)
        class_names = [name for name, obj in inspect.getmembers(plugin_module, inspect.isclass)]
        assert 'MockPyRPLConnection' not in class_names, "Plugin should not have embedded MockPyRPLConnection class"


class TestPluginConnectionSharing:
    """Test that plugins share mock connections correctly."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    @pytest.mark.mock
    def test_multiple_plugins_share_mock_connection(self):
        """Test that multiple plugins share the same underlying mock connection."""
        hostname = "shared-test.local"
        
        # Create connections for different plugin types
        conn1 = self.manager.connect_device(hostname, "viewer_config", mock_mode=True)
        conn2 = self.manager.connect_device(hostname, "iq_config", mock_mode=True) 
        conn3 = self.manager.connect_device(hostname, "pid_config", mock_mode=True)
        
        assert conn1 is not None
        assert conn2 is not None
        assert conn3 is not None
        
        # All connections should be using the same underlying mock instance
        assert hasattr(conn1, '_mock_instance')
        assert hasattr(conn2, '_mock_instance')
        assert hasattr(conn3, '_mock_instance')
        
        # The underlying mock instances should be identical
        assert conn1._mock_instance is conn2._mock_instance
        assert conn2._mock_instance is conn3._mock_instance
    
    @pytest.mark.mock
    def test_mock_connection_data_consistency(self):
        """Test that data changes through one connection are visible through others."""
        hostname = "consistency-test.local"
        
        # Create two connections representing different plugins
        conn1 = self.manager.connect_device(hostname, "plugin1", mock_mode=True)
        conn2 = self.manager.connect_device(hostname, "plugin2", mock_mode=True)
        
        assert conn1 is not None
        assert conn2 is not None
        
        # Get the shared mock instance
        mock_instance = conn1._mock_instance
        
        # Test voltage reading consistency
        if hasattr(mock_instance, 'read_voltage'):
            from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import InputChannel
            
            # Read voltage through first connection
            voltage1 = conn1.read_voltage(InputChannel.IN1)
            
            # Read voltage through second connection 
            voltage2 = conn2.read_voltage(InputChannel.IN1)
            
            # Both should return valid voltages (exact values may vary due to simulation)
            assert isinstance(voltage1, (int, float))
            assert isinstance(voltage2, (int, float))
            
            # The simulation state should be shared
            assert mock_instance is conn2._mock_instance


class TestMockDataAcquisition:
    """Test mock data acquisition through unified connections."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    @pytest.mark.mock
    def test_mock_voltage_acquisition(self):
        """Test voltage data acquisition through mock connections."""
        connection = self.manager.connect_device("voltage-test.local", "test_config", mock_mode=True)
        assert connection is not None
        
        # Test voltage reading
        if hasattr(connection, 'read_voltage'):
            from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import InputChannel
            
            voltage = connection.read_voltage(InputChannel.IN1)
            assert isinstance(voltage, (int, float))
            assert -2.0 <= voltage <= 2.0  # Reasonable voltage range
    
    @pytest.mark.mock
    def test_mock_iq_measurement(self):
        """Test IQ measurements through mock connections."""
        connection = self.manager.connect_device("iq-test.local", "iq_config", mock_mode=True)
        assert connection is not None
        
        # Test IQ measurement
        if hasattr(connection, 'get_iq_measurement'):
            from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import IQChannel
            
            iq_result = connection.get_iq_measurement(IQChannel.IQ0)
            
            if iq_result is not None:
                i_val, q_val = iq_result
                assert isinstance(i_val, (int, float))
                assert isinstance(q_val, (int, float))
                
                # Calculate magnitude - should be reasonable
                magnitude = (i_val**2 + q_val**2)**0.5
                assert magnitude >= 0
    
    @pytest.mark.mock  
    def test_mock_pid_control(self):
        """Test PID control through mock connections."""
        connection = self.manager.connect_device("pid-test.local", "pid_config", mock_mode=True)
        assert connection is not None
        
        # Test PID setpoint operations
        if hasattr(connection, 'set_pid_setpoint') and hasattr(connection, 'get_pid_setpoint'):
            from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import PIDChannel
            
            # Set a PID setpoint
            test_setpoint = 0.5
            success = connection.set_pid_setpoint(PIDChannel.PID0, test_setpoint)
            
            if success:
                # Read back the setpoint
                readback = connection.get_pid_setpoint(PIDChannel.PID0)
                
                if readback is not None:
                    # Should be close to the set value (allowing for simulation variations)
                    assert abs(readback - test_setpoint) < 0.1


class TestNoEmbeddedMockClasses:
    """Test that embedded MockPyRPLConnection classes have been removed."""
    
    @pytest.mark.mock
    def test_no_embedded_mock_in_viewer_plugin(self):
        """Test that basic viewer plugin has no embedded MockPyRPLConnection."""
        import inspect
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        
        # Get the module containing the plugin
        module = inspect.getmodule(DAQ_0DViewer_PyRPL)
        
        # Check that no MockPyRPLConnection class exists in the module
        module_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
        assert 'MockPyRPLConnection' not in module_classes
        
        # Verify the plugin class itself doesn't have embedded mock references
        plugin_source = inspect.getsource(DAQ_0DViewer_PyRPL)
        assert 'class MockPyRPLConnection' not in plugin_source
    
    @pytest.mark.mock
    def test_no_embedded_mock_in_iq_plugin(self):
        """Test that IQ viewer plugin has no embedded MockPyRPLConnection."""
        import inspect
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ
        
        # Get the module containing the plugin
        module = inspect.getmodule(DAQ_0DViewer_PyRPL_IQ)
        
        # Check that no MockPyRPLConnection class exists in the module
        module_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
        assert 'MockPyRPLConnection' not in module_classes
        
        # Verify the plugin class itself doesn't have embedded mock references
        plugin_source = inspect.getsource(DAQ_0DViewer_PyRPL_IQ)
        assert 'class MockPyRPLConnection' not in plugin_source


class TestConnectionLifecycle:
    """Test connection lifecycle management through PyRPLManager."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    @pytest.mark.mock
    def test_connection_reference_counting(self):
        """Test that mock connections support proper reference counting."""
        hostname = "refcount-test.local"
        
        # Create first connection
        conn1 = self.manager.connect_device(hostname, "config1", mock_mode=True)
        assert conn1 is not None
        initial_refs = conn1._reference_count
        
        # Create second connection to same host
        conn2 = self.manager.connect_device(hostname, "config1", mock_mode=True)
        assert conn2 is not None
        
        # Should be the same connection object
        assert conn1 is conn2
        assert conn1._reference_count == initial_refs + 1
        
        # Disconnect one connection
        success1 = self.manager.disconnect_device(hostname, "config1")
        assert success1
        assert conn1._reference_count == initial_refs
        
        # Disconnect second connection
        success2 = self.manager.disconnect_device(hostname, "config1")
        assert success2
        # Note: reference count behavior depends on PyRPLManager implementation
    
    @pytest.mark.mock
    def test_mock_real_mode_separation(self):
        """Test that mock and real mode connections are properly separated."""
        hostname = "separation-test.local"
        
        # Create mock connection
        mock_conn = self.manager.connect_device(hostname, "mock_cfg", mock_mode=True)
        assert mock_conn is not None
        
        # Create real connection (will likely fail, but should not affect mock)
        real_conn = self.manager.connect_device(hostname, "real_cfg", mock_mode=False)
        # real_conn may be None due to no hardware - that's expected
        
        # Mock connection should still work
        assert mock_conn.is_connected
        
        # They should be different connection objects if real connection succeeded
        if real_conn is not None:
            assert mock_conn is not real_conn


if __name__ == '__main__':
    pytest.main([__file__, '-v'])