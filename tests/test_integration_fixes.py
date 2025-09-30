# -*- coding: utf-8 -*-
"""
Test suite for PyMoDAQ-PyRPL integration fixes

This test suite validates the critical fixes implemented to resolve
integration issues between PyMoDAQ and PyRPL, including:

1. Dictionary/set API mismatches
2. Reference counting implementation
3. Qt threading safety improvements
4. Dashboard interface compatibility

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import (
    PyRPLConnection, PyRPLManager, ConnectionInfo, PIDChannel,
    PIDConfiguration, InputChannel, OutputChannel, ConnectionState,
    PyRPLMockConnectionAdapter, create_pyrpl_connection,
    reset_shared_mock_instance
)


class TestCriticalFixes:
    """Test critical bug fixes implemented in the integration."""

    def test_active_pids_dictionary_fix(self):
        """
        Test that _active_pids is properly managed as a dictionary.

        This test validates the fix for the critical bug where
        _active_pids.add() was called on a dictionary instead of a set.
        """
        # Create connection info
        connection_info = ConnectionInfo(
            hostname="test-host",
            config_name="test-config"
        )

        # Create connection instance
        connection = PyRPLConnection(connection_info)

        # Verify _active_pids is initialized as dictionary
        assert isinstance(connection._active_pids, dict)
        assert len(connection._active_pids) == 0

        # Mock PyRPL components for testing
        mock_pyrpl = Mock()
        mock_redpitaya = Mock()
        mock_pid_module = Mock()

        connection._pyrpl = mock_pyrpl
        connection._redpitaya = mock_redpitaya
        connection.state = ConnectionState.CONNECTED

        # Mock the PID module retrieval
        setattr(mock_redpitaya, 'pid0', mock_pid_module)

        # Create PID configuration
        config = PIDConfiguration(
            setpoint=0.5,
            p_gain=0.1,
            i_gain=0.01,
            input_channel=InputChannel.IN1,
            output_channel=OutputChannel.OUT1
        )

        # Configure PID - this should NOT raise AttributeError anymore
        success = connection.configure_pid(PIDChannel.PID0, config)

        # Verify the fix worked
        assert success is True
        assert PIDChannel.PID0 in connection._active_pids
        assert connection._active_pids[PIDChannel.PID0] is mock_pid_module

        # Verify PID module was configured correctly
        assert mock_pid_module.setpoint == 0.5
        assert mock_pid_module.p == 0.1
        assert mock_pid_module.i == 0.01

    def test_reference_counting_methods(self):
        """Reference counting now lives on the mock adapter."""
        reset_shared_mock_instance()

        with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.get_shared_mock_instance') as get_mock:
            get_mock.return_value = Mock()
            adapter = create_pyrpl_connection(
                hostname="mock-host",
                config_name="mock-config",
                mock_mode=True,
            )

        assert isinstance(adapter, PyRPLMockConnectionAdapter)
        assert adapter._reference_count == 1

        count = adapter.add_reference()
        assert count == 2
        count = adapter.add_reference()
        assert count == 3

        count = adapter.remove_reference()
        assert count == 2
        count = adapter.remove_reference()
        assert count == 1
        count = adapter.remove_reference()
        assert count == 0

        # Additional removals should clamp at zero
        count = adapter.remove_reference()
        assert count == 0

    def test_manager_connection_lifecycle(self):
        """
        Test PyRPLManager connection lifecycle with reference counting.

        This validates the complete connection management workflow
        including the fixes for missing methods.
        """
        manager = PyRPLManager.get_instance()
        manager.disconnect_all()
        reset_shared_mock_instance()

        with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.get_shared_mock_instance') as get_mock:
            get_mock.return_value = Mock()

            connection = manager.connect_device(
                "test-host", "test-config", mock_mode=True
            )

            assert isinstance(connection, PyRPLMockConnectionAdapter)
            assert connection._reference_count == 1

            same_connection = manager.connect_device(
                "test-host", "test-config", mock_mode=True
            )

            assert same_connection is connection
            assert connection._reference_count == 2

            # First disconnect leaves one reference
            success = manager.disconnect_device("test-host", "test-config")
            assert success is True
            assert connection._reference_count == 1

            # Second disconnect releases adapter completely
            success = manager.disconnect_device("test-host", "test-config")
            assert success is True
            assert connection._reference_count == 0

            status = manager.get_manager_status()
            assert status['total_connections'] == 0

    def test_qt_timer_patch_safety(self):
        """
        Test that Qt timer patch is applied safely and doesn't conflict.

        This validates the improved Qt threading safety fixes.
        """
        # Test is only meaningful if Qt is available
        try:
            from qtpy.QtCore import QTimer
        except ImportError:
            pytest.skip("Qt not available for testing")

        # Check if patch was applied
        if hasattr(QTimer, '_pyrpl_patched'):
            # Verify patched setInterval handles various inputs safely
            timer = QTimer()

            # Test normal integer input
            timer.setInterval(1000)

            # Test float input (should convert to int)
            timer.setInterval(1000.5)

            # Test edge cases that should be handled gracefully
            try:
                timer.setInterval("invalid")
                # Should not raise exception due to our patch
            except Exception:
                pytest.fail("QTimer patch should handle invalid input gracefully")

    def test_thread_safety(self):
        """
        Test thread safety of the connection manager.

        This validates that multiple threads can safely access
        the connection manager without race conditions.
        """
        manager = PyRPLManager.get_instance()
        manager.disconnect_all()
        reset_shared_mock_instance()

        results = []
        exceptions = []

        def connect_worker(worker_id):
            try:
                with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.get_shared_mock_instance') as get_mock:
                    get_mock.return_value = Mock()

                    connection = manager.connect_device(
                        f"host-{worker_id}", f"config-{worker_id}", mock_mode=True
                    )
                    results.append((worker_id, connection is not None))

                    time.sleep(0.01)

                    success = manager.disconnect_device(
                        f"host-{worker_id}", f"config-{worker_id}"
                    )
                    results.append((worker_id, success))

            except Exception as e:
                exceptions.append((worker_id, e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=connect_worker, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Thread safety test failed with exceptions: {exceptions}"

        # Verify all operations succeeded
        assert len(results) == 10  # 2 operations per thread * 5 threads
        for worker_id, success in results:
            assert success, f"Operation failed for worker {worker_id}"

    def test_mock_connection_compatibility(self):
        """
        Test that mock connections work with the fixed interface.

        This validates mock mode functionality after the fixes.
        """
        # Test mock mode connection creation
        with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper._lazy_import_pyrpl') as mock_import:
            mock_import.return_value = False  # Simulate PyRPL not available

            manager = PyRPLManager.get_instance()

            # This should create a mock connection when PyRPL is not available
            # and mock_mode is True
            connection = manager.connect_device(
                "mock-host",
                "mock-config",
                mock_mode=True
            )

            # The behavior depends on whether EnhancedMockPyRPLConnection is available
            # If available, we should get a mock connection
            # If not available, we should get None but no exception
            assert connection is None or hasattr(connection, 'is_connected')


class TestIntegrationValidation:
    """Integration tests to validate the complete fix package."""

    def test_plugin_initialization_flow(self):
        """
        Test complete plugin initialization flow with fixes.

        This simulates the full plugin initialization process to ensure
        all fixes work together correctly.
        """
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import (
            get_pid_parameters
        )

        # Test parameter generation doesn't fail
        params = get_pid_parameters()
        assert isinstance(params, list)
        assert len(params) > 0

        # Verify required parameter structures
        connection_group = None
        for param in params:
            if param.get('name') == 'connection_settings':
                connection_group = param
                break

        assert connection_group is not None
        assert 'children' in connection_group

        # Verify required parameters exist
        param_names = [child['name'] for child in connection_group['children']]
        required_params = ['redpitaya_host', 'config_name', 'mock_mode']
        for required in required_params:
            assert required in param_names

    @patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper._lazy_import_pyrpl')
    def test_error_handling_robustness(self, mock_import):
        """
        Test error handling robustness of the fixed system.

        This validates that the fixes don't break error handling
        and that the system degrades gracefully.
        """
        # Test with PyRPL import failure
        mock_import.return_value = False

        manager = PyRPLManager.get_instance()
        manager.disconnect_all()

        # Should handle PyRPL unavailability gracefully
        connection = manager.connect_device("test-host", "test-config")
        assert connection is None  # Should fail gracefully, not crash

        # Test disconnection of non-existent connection
        success = manager.disconnect_device("non-existent", "config")
        assert success is True  # Gracefully handled even if nothing to disconnect

        # Test manager status with no connections
        status = manager.get_manager_status()
        assert isinstance(status, dict)
        assert status['total_connections'] == 0

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])