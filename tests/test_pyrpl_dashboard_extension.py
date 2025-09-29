# -*- coding: utf-8 -*-
"""
Test suite for PyRPL Dashboard Extension.

This module tests the PyRPL Dashboard extension functionality including
connection monitoring, device management, and integration with PyRPLManager.

Author: Generated for PyMoDAQ Integration
License: MIT
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from qtpy import QtWidgets, QtCore
import time

# Import PyMoDAQ components
from pymodaq_gui import utils as gutils


class TestPyRPLDashboardExtension(unittest.TestCase):
    """Test PyRPL Dashboard Extension functionality."""

    def setUp(self):
        """Setup test environment."""
        # Mock PyRPL to prevent import errors
        self.mock_pyrpl = MagicMock()
        self.patcher = patch.dict('sys.modules', {'pyrpl': self.mock_pyrpl})
        self.patcher.start()

        # Create QApplication if needed
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])

        # Mock PyRPL manager
        self.mock_manager = Mock()
        self.mock_manager.get_manager_status.return_value = {
            'connections': {},
            'total_connections': 0,
            'manager_created_at': time.time()
        }

        # Import extension after mocking
        with patch('pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard.get_pyrpl_manager',
                  return_value=self.mock_manager):
            from pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard import DAQ_PyRPL_Dashboard_Extension

            # Create extension instance
            self.dashboard = Mock()
            self.dockarea = gutils.DockArea()
            self.extension = DAQ_PyRPL_Dashboard_Extension(self.dockarea, self.dashboard)

    def tearDown(self):
        """Cleanup after tests."""
        self.patcher.stop()
        if hasattr(self.extension, 'quit_extension'):
            self.extension.quit_extension()

    def test_extension_initialization(self):
        """Test extension initializes correctly."""
        self.assertIsNotNone(self.extension)
        self.assertIsNotNone(self.extension.pyrpl_manager)
        self.assertTrue(hasattr(self.extension, 'connection_table'))
        self.assertTrue(hasattr(self.extension, 'settings'))

    def test_extension_has_required_components(self):
        """Test extension has all required UI components."""
        # Check docks
        self.assertTrue(hasattr(self.extension, 'dashboard_dock'))

        # Check widgets
        self.assertIsNotNone(self.extension.connection_table)
        self.assertIsNotNone(self.extension.param_tree)

        # Check LEDs and status indicators
        self.assertTrue(hasattr(self.extension, 'manager_led'))
        self.assertTrue(hasattr(self.extension, 'monitor_led'))

    def test_connection_table_setup(self):
        """Test connection table is properly configured."""
        table = self.extension.connection_table

        # Check headers
        expected_headers = ['Hostname', 'Status', 'Config', 'Ref Count', 'Connected Since', 'Actions']
        actual_headers = [table.horizontalHeaderItem(i).text()
                         for i in range(table.columnCount())]
        self.assertEqual(actual_headers, expected_headers)

        # Check table properties
        self.assertTrue(table.alternatingRowColors())
        self.assertTrue(table.isSortingEnabled())

    def test_parameter_structure(self):
        """Test parameter tree structure."""
        settings = self.extension.settings

        # Check main groups exist
        group_names = [child.name() for child in settings.children()]
        self.assertIn('dashboard_settings', group_names)
        self.assertIn('new_connection', group_names)

        # Check dashboard settings children
        dashboard_group = settings.child('dashboard_settings')
        dashboard_children = [child.name() for child in dashboard_group.children()]
        self.assertIn('update_rate', dashboard_children)
        self.assertIn('auto_refresh', dashboard_children)

    def test_monitoring_toggle(self):
        """Test monitoring start/stop functionality."""
        # Initially should be monitoring
        self.assertTrue(self.extension.is_monitoring)

        # Stop monitoring
        self.extension.stop_monitoring()
        self.assertFalse(self.extension.is_monitoring)

        # Start monitoring
        self.extension.start_monitoring()
        self.assertTrue(self.extension.is_monitoring)

    def test_refresh_status(self):
        """Test status refresh functionality."""
        # Setup mock manager response
        mock_status = {
            'connections': {
                'rp-test.local': {
                    'is_connected': True,
                    'config_name': 'test_config',
                    'ref_count': 1,
                    'connected_since': time.time()
                }
            },
            'total_connections': 1
        }
        self.mock_manager.get_manager_status.return_value = mock_status

        # Refresh status
        self.extension.refresh_status()

        # Verify manager was called
        self.mock_manager.get_manager_status.assert_called()

    def test_connection_table_update(self):
        """Test connection table updates with status data."""
        # Create mock status data
        status = {
            'connections': {
                'rp-test.local': {
                    'is_connected': True,
                    'config_name': 'test_config',
                    'ref_count': 2,
                    'connected_since': time.time()
                },
                'rp-mock.local': {
                    'is_connected': False,
                    'config_name': 'mock_config',
                    'ref_count': 0,
                    'connected_since': 'Unknown'
                }
            }
        }

        # Update table
        self.extension.update_connection_table(status)

        # Verify table contents
        table = self.extension.connection_table
        self.assertEqual(table.rowCount(), 2)

        # Check first row (connected device)
        self.assertEqual(table.item(0, 0).text(), 'rp-test.local')
        self.assertEqual(table.item(0, 1).text(), 'Connected')
        self.assertEqual(table.item(0, 2).text(), 'test_config')
        self.assertEqual(table.item(0, 3).text(), '2')

    def test_new_device_connection_validation(self):
        """Test new device connection input validation."""
        # Test empty hostname
        self.extension.settings.child('new_connection', 'hostname').setValue('')

        with patch('qtpy.QtWidgets.QMessageBox.warning') as mock_warning:
            self.extension.connect_new_device()
            mock_warning.assert_called()

    @patch('qtpy.QtWidgets.QMessageBox.question')
    def test_device_disconnect_warning(self, mock_question):
        """Test device disconnect warning for devices in use."""
        # Setup mock manager with device in use
        self.mock_manager.get_manager_status.return_value = {
            'connections': {
                'rp-test.local': {
                    'is_connected': True,
                    'ref_count': 2  # Device in use
                }
            }
        }

        # Mock user choosing "No"
        mock_question.return_value = QtWidgets.QMessageBox.No

        # Attempt disconnect
        self.extension.disconnect_device('rp-test.local')

        # Verify warning was shown
        mock_question.assert_called()
        # Verify disconnect was not called (user said no)
        self.mock_manager.disconnect_device.assert_not_called()

    def test_extension_actions_exist(self):
        """Test that all expected actions are created."""
        actions = self.extension.dockarea.toolbar.actions()
        action_texts = [action.text() for action in actions if action.text()]

        # Should have the main actions (text may vary, check they exist)
        self.assertTrue(len(action_texts) > 0)

    def test_manager_unavailable_handling(self):
        """Test extension handles unavailable PyRPL manager."""
        # Create extension without manager
        with patch('pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard.get_pyrpl_manager',
                  side_effect=Exception("Manager unavailable")):
            from pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard import DAQ_PyRPL_Dashboard_Extension

            extension = DAQ_PyRPL_Dashboard_Extension(self.dockarea, self.dashboard)

            # Should handle gracefully
            self.assertIsNone(extension.pyrpl_manager)
            self.assertFalse(extension.is_monitoring)

    def test_parameter_change_handling(self):
        """Test parameter change handling."""
        # Test update rate change
        self.extension.start_monitoring()
        old_interval = self.extension.refresh_timer.interval()

        # Change update rate
        self.extension.settings.child('dashboard_settings', 'update_rate').setValue(2000)

        # Should restart monitoring with new interval
        self.assertTrue(self.extension.is_monitoring)

    def test_disconnect_all_confirmation(self):
        """Test disconnect all devices shows confirmation."""
        # Setup mock manager with multiple devices
        self.mock_manager.get_manager_status.return_value = {
            'connections': {
                'rp-1.local': {'ref_count': 1},
                'rp-2.local': {'ref_count': 0}
            }
        }

        with patch('qtpy.QtWidgets.QMessageBox.question',
                  return_value=QtWidgets.QMessageBox.No) as mock_question:
            self.extension.disconnect_all_devices()
            mock_question.assert_called()

    def test_extension_cleanup(self):
        """Test extension cleans up properly on quit."""
        # Start monitoring
        self.extension.start_monitoring()
        self.assertTrue(self.extension.is_monitoring)

        # Quit extension
        self.extension.quit_extension()

        # Should stop monitoring
        self.assertFalse(self.extension.is_monitoring)


@pytest.mark.integration
class TestPyRPLDashboardIntegration:
    """Integration tests for PyRPL Dashboard Extension."""

    def test_extension_discovery(self):
        """Test that extension can be discovered by PyMoDAQ."""
        # This test verifies the extension follows PyMoDAQ patterns
        from pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard import (
            EXTENSION_NAME, CLASS_NAME, DAQ_PyRPL_Dashboard_Extension
        )

        # Check metadata exists
        assert EXTENSION_NAME == "PyRPL Dashboard"
        assert CLASS_NAME == "DAQ_PyRPL_Dashboard_Extension"

        # Check class exists and inherits correctly
        from pymodaq.extensions.utils import CustomExt
        assert issubclass(DAQ_PyRPL_Dashboard_Extension, CustomExt)

    def test_extension_import(self):
        """Test extension can be imported without errors."""
        try:
            from pymodaq_plugins_pyrpl.extensions.daq_extension_pyrpl_dashboard import DAQ_PyRPL_Dashboard_Extension
            assert DAQ_PyRPL_Dashboard_Extension is not None
        except ImportError as e:
            pytest.fail(f"Extension import failed: {e}")


if __name__ == '__main__':
    unittest.main()