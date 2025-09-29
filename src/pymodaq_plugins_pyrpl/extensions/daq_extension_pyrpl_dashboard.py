# -*- coding: utf-8 -*-
"""
PyMoDAQ Extension: PyRPL Dashboard

A minimal dashboard extension for monitoring and managing PyRPL device connections
within the PyMoDAQ framework. This extension provides a centralized view of all
Red Pitaya connections managed by the PyRPLManager singleton.

Features:
    - Real-time connection status monitoring
    - Device reference count tracking
    - Basic connection management (connect/disconnect)
    - Integration with existing PyRPLManager architecture
    - Mock mode support for development

Author: Generated for PyMoDAQ Integration
License: MIT
"""

import time
from typing import Optional, Dict, List
from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import QObject, Signal, QTimer, Slot

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.utils.widgets import QLED, LabelWithFont
from pymodaq_gui.utils.dock import Dock
from pymodaq.extensions.utils import CustomExt

# Import PyRPL wrapper utilities
from ..utils.pyrpl_wrapper import get_pyrpl_manager, PyRPLManager

logger = set_logger(get_module_name(__file__))

# Extension metadata for PyMoDAQ discovery
EXTENSION_NAME = "PyRPL Dashboard"
CLASS_NAME = "DAQ_PyRPL_Dashboard_Extension"


class DAQ_PyRPL_Dashboard_Extension(CustomExt):
    """
    PyMoDAQ Extension for PyRPL Device Dashboard.

    This extension provides a centralized dashboard for monitoring and managing
    Red Pitaya device connections via the PyRPLManager singleton. It offers
    real-time status updates and basic connection management without interfering
    with the working plugin architecture.
    """

    # Signals for internal communication
    connection_status_changed = Signal(str, bool)  # hostname, connected
    manager_status_updated = Signal(dict)

    params = [
        {
            'title': 'Dashboard Settings',
            'name': 'dashboard_settings',
            'type': 'group',
            'expanded': True,
            'children': [
                {
                    'title': 'Update Rate (ms):',
                    'name': 'update_rate',
                    'type': 'int',
                    'value': 1000,
                    'min': 500,
                    'max': 5000,
                    'step': 100,
                    'tip': 'Dashboard refresh rate in milliseconds'
                },
                {
                    'title': 'Auto-refresh:',
                    'name': 'auto_refresh',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Enable automatic dashboard updates'
                }
            ]
        },
        {
            'title': 'New Connection',
            'name': 'new_connection',
            'type': 'group',
            'expanded': False,
            'children': [
                {
                    'title': 'Hostname:',
                    'name': 'hostname',
                    'type': 'str',
                    'value': 'rp-f08d6c.local',
                    'tip': 'Red Pitaya hostname or IP address'
                },
                {
                    'title': 'Config Name:',
                    'name': 'config_name',
                    'type': 'str',
                    'value': 'pymodaq_dashboard',
                    'tip': 'PyRPL configuration name'
                },
                {
                    'title': 'Connect Device',
                    'name': 'connect_device',
                    'type': 'action',
                    'tip': 'Connect to new Red Pitaya device'
                }
            ]
        }
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        # Initialize attributes
        self.pyrpl_manager: Optional[PyRPLManager] = None
        self.refresh_timer: Optional[QTimer] = None
        self.connection_table: Optional[QtWidgets.QTableWidget] = None

        # Status tracking
        self.is_monitoring = False
        self.last_status = {}

        # Get PyRPL manager instance
        try:
            self.pyrpl_manager = get_pyrpl_manager()
            logger.info("Connected to PyRPL manager")
        except Exception as e:
            logger.warning(f"Could not connect to PyRPL manager: {e}")
            self.pyrpl_manager = None

        # Setup the extension
        self.setup_ui()
        self.setup_signals()

        # Start monitoring if manager is available
        if self.pyrpl_manager:
            self.start_monitoring()

        logger.info("PyRPL Dashboard Extension initialized")

    def setup_actions(self):
        """Setup toolbar actions."""
        self.add_action('refresh', 'Refresh Status', 'refresh', checkable=False)
        self.add_action('monitor', 'Toggle Monitoring', 'timer', checkable=True, checked=True)
        self.add_action('clear_all', 'Disconnect All (Dangerous)', 'close2')
        self.add_action('quit', 'Close Dashboard', 'close')

    def setup_docks(self):
        """Setup docking interface."""
        # Main dashboard dock
        self.dashboard_dock = Dock("PyRPL Device Dashboard", self.dockarea)
        self.dockarea.addDock(self.dashboard_dock)

        # Create main widget
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()

        # Parameter tree for settings
        self.param_tree = ParameterTree()
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.param_tree.setParameters(self.settings, showTop=False)

        # Manager status summary
        status_frame = QtWidgets.QFrame()
        status_layout = QtWidgets.QGridLayout()

        # Manager status indicators
        self.manager_led = QLED()
        self.manager_label = LabelWithFont('Manager Available', font_size=10)
        status_layout.addWidget(QtWidgets.QLabel('PyRPL Manager:'), 0, 0)
        status_layout.addWidget(self.manager_led, 0, 1)
        status_layout.addWidget(self.manager_label, 0, 2)

        # Monitoring status
        self.monitor_led = QLED()
        self.monitor_label = LabelWithFont('Monitoring', font_size=10)
        status_layout.addWidget(QtWidgets.QLabel('Monitoring:'), 1, 0)
        status_layout.addWidget(self.monitor_led, 1, 1)
        status_layout.addWidget(self.monitor_label, 1, 2)

        status_frame.setLayout(status_layout)
        status_frame.setFrameStyle(QtWidgets.QFrame.Box)

        # Connection table
        self.connection_table = QtWidgets.QTableWidget()
        self.setup_connection_table()

        # Add widgets to main layout
        main_layout.addWidget(QtWidgets.QLabel('<b>Settings</b>'))
        main_layout.addWidget(self.param_tree)
        main_layout.addWidget(QtWidgets.QLabel('<b>Manager Status</b>'))
        main_layout.addWidget(status_frame)
        main_layout.addWidget(QtWidgets.QLabel('<b>Active Connections</b>'))
        main_layout.addWidget(self.connection_table)

        main_widget.setLayout(main_layout)
        self.dashboard_dock.addWidget(main_widget)

        # Update initial status
        self.update_manager_status()

    def setup_connection_table(self):
        """Setup the connection status table."""
        if not self.connection_table:
            return

        # Set up columns
        headers = ['Hostname', 'Status', 'Config', 'Ref Count', 'Connected Since', 'Actions']
        self.connection_table.setColumnCount(len(headers))
        self.connection_table.setHorizontalHeaderLabels(headers)

        # Configure table
        self.connection_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.connection_table.setAlternatingRowColors(True)
        self.connection_table.setSortingEnabled(True)

        # Set column widths
        header = self.connection_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(headers) - 1):
            header.setDefaultSectionSize(120)

    def connect_things(self):
        """Connect signals and slots."""
        # Toolbar actions
        self.connect_action('refresh', self.refresh_status)
        self.connect_action('monitor', self.toggle_monitoring)
        self.connect_action('clear_all', self.disconnect_all_devices)
        self.connect_action('quit', self.quit_extension)

        # Parameter changes
        self.settings.sigTreeStateChanged.connect(self.parameter_changed_slot)

        # Internal signals
        self.manager_status_updated.connect(self.update_connection_table)

    def setup_signals(self):
        """Setup internal signal connections."""
        pass  # Additional signal setup if needed

    def start_monitoring(self):
        """Start automatic status monitoring."""
        if not self.pyrpl_manager:
            return

        if self.refresh_timer is None:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_status)

        update_rate = self.settings['dashboard_settings', 'update_rate']
        self.refresh_timer.start(update_rate)

        self.is_monitoring = True
        self.monitor_led.set_as_true()
        self.monitor_label.setText('Running')

        logger.info(f"Started dashboard monitoring with {update_rate}ms interval")

    def stop_monitoring(self):
        """Stop automatic status monitoring."""
        if self.refresh_timer:
            self.refresh_timer.stop()

        self.is_monitoring = False
        self.monitor_led.set_as_false()
        self.monitor_label.setText('Stopped')

        logger.info("Stopped dashboard monitoring")

    def toggle_monitoring(self):
        """Toggle monitoring on/off."""
        if self.is_monitoring:
            self.stop_monitoring()
            self.get_action('monitor').setChecked(False)
        else:
            self.start_monitoring()
            self.get_action('monitor').setChecked(True)

    def refresh_status(self):
        """Refresh manager and connection status."""
        if not self.pyrpl_manager:
            return

        try:
            # Get current manager status
            status = self.pyrpl_manager.get_manager_status()
            self.manager_status_updated.emit(status)
            self.last_status = status

        except Exception as e:
            logger.error(f"Error refreshing status: {e}")

    def update_manager_status(self):
        """Update manager status indicators."""
        if self.pyrpl_manager:
            self.manager_led.set_as_true()
            self.manager_label.setText('Available')
        else:
            self.manager_led.set_as_false()
            self.manager_label.setText('Unavailable')

    @Slot(dict)
    def update_connection_table(self, status: Dict):
        """Update the connection table with current status."""
        if not self.connection_table:
            return

        try:
            connections = status.get('connections', {})

            # Clear current table
            self.connection_table.setRowCount(0)

            # Add rows for each connection
            for hostname, conn_info in connections.items():
                row = self.connection_table.rowCount()
                self.connection_table.insertRow(row)

                # Hostname
                self.connection_table.setItem(row, 0, QtWidgets.QTableWidgetItem(hostname))

                # Status
                is_connected = conn_info.get('is_connected', False)
                status_text = 'Connected' if is_connected else 'Disconnected'
                status_item = QtWidgets.QTableWidgetItem(status_text)
                if is_connected:
                    status_item.setBackground(QtGui.QColor(144, 238, 144))  # Light green
                else:
                    status_item.setBackground(QtGui.QColor(255, 182, 193))  # Light red
                self.connection_table.setItem(row, 1, status_item)

                # Config name
                config_name = conn_info.get('config_name', 'Unknown')
                self.connection_table.setItem(row, 2, QtWidgets.QTableWidgetItem(config_name))

                # Reference count
                ref_count = conn_info.get('ref_count', 0)
                ref_item = QtWidgets.QTableWidgetItem(str(ref_count))
                if ref_count > 0:
                    ref_item.setBackground(QtGui.QColor(255, 255, 0))  # Yellow for active use
                self.connection_table.setItem(row, 3, ref_item)

                # Connected since
                connected_since = conn_info.get('connected_since', 'Unknown')
                if isinstance(connected_since, float):
                    connected_since = time.strftime('%H:%M:%S', time.localtime(connected_since))
                self.connection_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(connected_since)))

                # Actions (disconnect button)
                disconnect_btn = QtWidgets.QPushButton('Disconnect')
                disconnect_btn.clicked.connect(lambda checked, h=hostname: self.disconnect_device(h))
                if ref_count > 0:
                    disconnect_btn.setStyleSheet("background-color: orange")
                    disconnect_btn.setToolTip(f"Warning: {ref_count} plugin(s) using this connection")
                self.connection_table.setCellWidget(row, 5, disconnect_btn)

            # Resize columns to content
            self.connection_table.resizeColumnsToContents()

        except Exception as e:
            logger.error(f"Error updating connection table: {e}")

    def parameter_changed_slot(self, param, changes):
        """Handle parameter changes."""
        for param_change, change, data in changes:
            path = self.settings.childPath(param_change)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param_change.name()

            logger.debug(f"Parameter changed: {childName} = {data}")

            # Handle monitoring rate changes
            if childName == 'dashboard_settings.update_rate' and self.is_monitoring:
                self.stop_monitoring()
                self.start_monitoring()

            # Handle auto-refresh toggle
            elif childName == 'dashboard_settings.auto_refresh':
                if data and not self.is_monitoring:
                    self.start_monitoring()
                elif not data and self.is_monitoring:
                    self.stop_monitoring()

            # Handle connect device action
            elif childName == 'new_connection.connect_device':
                self.connect_new_device()

    def connect_new_device(self):
        """Connect to a new Red Pitaya device."""
        if not self.pyrpl_manager:
            QtWidgets.QMessageBox.warning(None, 'PyRPL Manager Error',
                                        'PyRPL Manager is not available')
            return

        try:
            hostname = self.settings['new_connection', 'hostname']
            config_name = self.settings['new_connection', 'config_name']

            if not hostname.strip():
                QtWidgets.QMessageBox.warning(None, 'Invalid Input',
                                            'Please enter a valid hostname')
                return

            # Connect to device
            connection = self.pyrpl_manager.connect_device(
                hostname=hostname,
                config_name=config_name,
                connection_timeout=10.0,
                status_callback=None
            )

            if connection and connection.is_connected:
                logger.info(f"Successfully connected to {hostname}")
                self.refresh_status()  # Update display immediately
            else:
                QtWidgets.QMessageBox.warning(None, 'Connection Failed',
                                            f'Failed to connect to {hostname}')

        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            QtWidgets.QMessageBox.critical(None, 'Connection Error',
                                         f'Error connecting to device:\n{str(e)}')

    def disconnect_device(self, hostname: str):
        """Disconnect a specific device with safety checks."""
        if not self.pyrpl_manager:
            return

        try:
            # Get connection info
            status = self.pyrpl_manager.get_manager_status()
            connections = status.get('connections', {})

            if hostname not in connections:
                QtWidgets.QMessageBox.information(None, 'Device Not Found',
                                                f'Device {hostname} is not connected')
                return

            conn_info = connections[hostname]
            ref_count = conn_info.get('ref_count', 0)

            # Warn if device is in use
            if ref_count > 0:
                reply = QtWidgets.QMessageBox.question(
                    None, 'Disconnect Warning',
                    f'Device {hostname} is currently being used by {ref_count} plugin(s).\n'
                    f'Disconnecting may cause errors in those plugins.\n\n'
                    f'Do you want to proceed?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )

                if reply != QtWidgets.QMessageBox.Yes:
                    return

            # Disconnect device
            success = self.pyrpl_manager.disconnect_device(hostname)

            if success:
                logger.info(f"Disconnected device: {hostname}")
                self.refresh_status()  # Update display immediately
            else:
                QtWidgets.QMessageBox.warning(None, 'Disconnect Failed',
                                            f'Failed to disconnect {hostname}')

        except Exception as e:
            logger.error(f"Error disconnecting device {hostname}: {e}")
            QtWidgets.QMessageBox.critical(None, 'Disconnect Error',
                                         f'Error disconnecting device:\n{str(e)}')

    def disconnect_all_devices(self):
        """Disconnect all devices with confirmation."""
        if not self.pyrpl_manager:
            return

        try:
            status = self.pyrpl_manager.get_manager_status()
            connections = status.get('connections', {})

            if not connections:
                QtWidgets.QMessageBox.information(None, 'No Connections',
                                                'No devices are currently connected')
                return

            # Count devices in use
            devices_in_use = sum(1 for conn in connections.values()
                               if conn.get('ref_count', 0) > 0)

            # Confirmation dialog
            message = f'This will disconnect {len(connections)} device(s).'
            if devices_in_use > 0:
                message += f'\n\n{devices_in_use} device(s) are currently in use by plugins.'
                message += '\nThis action may cause errors in those plugins.'
            message += '\n\nAre you sure you want to proceed?'

            reply = QtWidgets.QMessageBox.question(
                None, 'Disconnect All Devices',
                message,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply != QtWidgets.QMessageBox.Yes:
                return

            # Disconnect all devices
            disconnected_count = 0
            for hostname in list(connections.keys()):
                if self.pyrpl_manager.disconnect_device(hostname):
                    disconnected_count += 1

            logger.info(f"Disconnected {disconnected_count}/{len(connections)} devices")
            self.refresh_status()  # Update display immediately

        except Exception as e:
            logger.error(f"Error disconnecting all devices: {e}")
            QtWidgets.QMessageBox.critical(None, 'Disconnect Error',
                                         f'Error disconnecting devices:\n{str(e)}')

    def quit_extension(self):
        """Quit extension and cleanup."""
        try:
            # Stop monitoring
            if self.is_monitoring:
                self.stop_monitoring()

            # Close docks
            if hasattr(self, 'dashboard_dock'):
                self.dashboard_dock.close()

            logger.info("PyRPL Dashboard Extension closed")

        except Exception as e:
            logger.error(f"Error closing extension: {e}")