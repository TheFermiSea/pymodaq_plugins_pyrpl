"""PyRPL Dashboard Extension for PyMoDAQ."""

import logging
from typing import Dict, Optional

from pymodaq.extensions.utils import CustomExt
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.utils.dock import Dock
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Slot

from ..utils.pyrpl_wrapper import PyRPLManager


logger = logging.getLogger(__name__)


class DAQ_PyRPL_Dashboard_Extension(CustomExt):
    """Dashboard extension providing PyRPL connection overview."""

    params = [
        {
            'title': 'Dashboard Settings',
            'name': 'dashboard_settings',
            'type': 'group',
            'children': [
                {
                    'title': 'Auto Refresh:',
                    'name': 'auto_refresh',
                    'type': 'bool',
                    'value': True,
                    'tip': 'Use PyRPL manager signals for immediate updates'
                },
                {
                    'title': 'Update Rate (ms):',
                    'name': 'update_rate',
                    'type': 'int',
                    'value': 2000,
                    'min': 250,
                    'max': 10000,
                    'step': 250,
                    'tip': 'Polling interval when auto refresh is disabled'
                }
            ]
        },
        {
            'title': 'New Connection',
            'name': 'new_connection',
            'type': 'group',
            'children': [
                {
                    'title': 'Config Name:',
                    'name': 'config_name',
                    'type': 'str',
                    'value': 'pymodaq_pyrpl',
                    'tip': 'Default configuration name for new connections'
                }
            ]
        }
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        self.pyrpl_manager: Optional[PyRPLManager] = PyRPLManager.get_instance()
        self.settings: Optional[Parameter] = None
        self.param_tree: Optional[ParameterTree] = None
        self.connection_table: Optional[QtWidgets.QTableWidget] = None
        self.refresh_button: Optional[QtWidgets.QPushButton] = None
        self.monitor_toggle_button: Optional[QtWidgets.QPushButton] = None
        self.monitor_label: Optional[QtWidgets.QLabel] = None
        self.configure_buttons = []
        self.is_monitoring = False

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setSingleShot(False)
        self.refresh_timer.timeout.connect(self.refresh_status)

        self.setup_ui()
        self.start_monitoring()

    def setup_actions(self):
        """Configure toolbar actions."""
        self.add_action('refresh', 'Refresh Status', 'refresh')
        self.add_action('toggle_monitor', 'Toggle Monitoring', 'timer', checkable=True)
        self.add_action('quit', 'Quit Extension', 'close2')

    def setup_docks(self):
        """Create dashboard dock with parameter tree and connection table."""
        self.dashboard_dock = Dock('PyRPL Dashboard', self.dockarea)
        self.dockarea.addDock(self.dashboard_dock)

        dock_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()

        # Parameter tree
        self.param_tree = ParameterTree()
        self.settings = Parameter.create(name='Dashboard', type='group', children=self.params)
        self.param_tree.setParameters(self.settings, showTop=False)

        # Controls layout
        controls_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton('Refresh')
        self.monitor_toggle_button = QtWidgets.QPushButton('Start Monitoring')
        status_text = QtWidgets.QLabel('Status:')
        self.monitor_label = QtWidgets.QLabel('Stopped')

        controls_layout.addWidget(self.refresh_button)
        controls_layout.addWidget(self.monitor_toggle_button)
        controls_layout.addStretch()
        controls_layout.addWidget(status_text)
        controls_layout.addWidget(self.monitor_label)

        # Connection table
        self.connection_table = QtWidgets.QTableWidget(0, 5)
        self.connection_table.setHorizontalHeaderLabels([
            'Hostname', 'Config', 'State', 'Last Error', 'Configure'
        ])
        header = self.connection_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        main_layout.addWidget(self.param_tree)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.connection_table)

        dock_widget.setLayout(main_layout)
        self.dashboard_dock.addWidget(dock_widget)

    def connect_things(self):
        """Connect UI actions and PyRPL manager signals."""
        self.connect_action('refresh', self.refresh_status)
        self.connect_action('toggle_monitor', self.toggle_monitoring)
        self.connect_action('quit', self.quit_extension)

        self.refresh_button.clicked.connect(self.refresh_status)
        self.monitor_toggle_button.clicked.connect(self.toggle_monitoring)

        if self.settings is not None:
            self.settings.sigTreeStateChanged.connect(self.parameter_changed_slot)

        if self.pyrpl_manager is not None:
            self.pyrpl_manager.status_updated.connect(self.update_connection_table)

    @Slot(dict)
    def update_connection_table(self, status: Optional[Dict[str, Dict]] = None):
        """Refresh the connection table using manager status."""
        if self.connection_table is None:
            return

        if status is None and self.pyrpl_manager is not None:
            status = self.pyrpl_manager.get_manager_status()

        if status is None:
            return

        connections = status.get('connections', {})
        self.connection_table.setRowCount(len(connections))
        self.configure_buttons.clear()

        for row, (key, info) in enumerate(connections.items()):
            hostname = info.get('hostname', key.split(':')[0] if ':' in key else key)
            config_name = info.get('config_name', key.split(':')[1] if ':' in key else '')
            state = info.get('state', 'unknown')
            last_error = info.get('last_error') or ''

            self.connection_table.setItem(row, 0, QtWidgets.QTableWidgetItem(hostname))
            self.connection_table.setItem(row, 1, QtWidgets.QTableWidgetItem(config_name))
            self.connection_table.setItem(row, 2, QtWidgets.QTableWidgetItem(state))
            self.connection_table.setItem(row, 3, QtWidgets.QTableWidgetItem(last_error))

            configure_btn = QtWidgets.QPushButton('Configure')
            configure_btn.clicked.connect(
                lambda _, host=hostname, config=config_name: self.configure_device(host, config)
            )
            self.configure_buttons.append(configure_btn)
            self.connection_table.setCellWidget(row, 4, configure_btn)

    def configure_device(self, hostname: str, config_name: Optional[str] = None) -> None:
        """Handle requests to configure a device."""
        if self.pyrpl_manager is None:
            return

        default_config = 'pymodaq_pyrpl'
        if self.settings is not None:
            default_config = self.settings['new_connection', 'config_name']

        config = config_name or default_config
        connections = self.pyrpl_manager.get_all_connections()
        connection_key = f"{hostname}:{config}"
        connection = connections.get(connection_key)

        if connection and connection.is_connected:
            logger.info("Configuration for %s requested.", hostname)
            QtWidgets.QMessageBox.information(
                None,
                'Configure Device',
                f'Configuration for {hostname} would open here.'
            )
        else:
            logger.warning("Cannot configure %s, not connected.", hostname)

    def refresh_status(self) -> None:
        """Manually refresh connection status."""
        if self.pyrpl_manager is None:
            return

        status = self.pyrpl_manager.get_manager_status()
        self.update_connection_table(status)

    def start_monitoring(self) -> None:
        """Enable monitoring using signals or polling based on configuration."""
        if self.settings is None:
            return

        auto_refresh = self.settings['dashboard_settings', 'auto_refresh']
        update_rate = self.settings['dashboard_settings', 'update_rate']

        if auto_refresh:
            self.refresh_timer.stop()
            self.monitor_label.setText('Real-time (Signals)')
        else:
            self.refresh_timer.start(update_rate)
            self.monitor_label.setText('Running (Polling)')

        self.is_monitoring = True
        self.monitor_toggle_button.setText('Stop Monitoring')
        self.get_action('toggle_monitor').setChecked(True)

        # Refresh once to populate UI immediately
        self.refresh_status()

    def stop_monitoring(self) -> None:
        """Disable monitoring."""
        self.refresh_timer.stop()
        self.monitor_label.setText('Stopped')
        self.is_monitoring = False
        self.monitor_toggle_button.setText('Start Monitoring')
        self.get_action('toggle_monitor').setChecked(False)

    def toggle_monitoring(self) -> None:
        """Toggle monitoring state."""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def parameter_changed_slot(self, param, changes):
        """React to dashboard parameter changes."""
        for param_item, change, data in changes:
            path = self.settings.childPath(param_item)
            if path is not None:
                child_name = '.'.join(path)
            else:
                child_name = param_item.name()

            if child_name == 'dashboard_settings.auto_refresh':
                if self.is_monitoring:
                    self.start_monitoring()
            elif child_name == 'dashboard_settings.update_rate':
                if self.is_monitoring and not self.settings['dashboard_settings', 'auto_refresh']:
                    self.refresh_timer.start(int(data))

    def quit_extension(self) -> None:
        """Cleanup and close dashboards."""
        try:
            if self.is_monitoring:
                self.stop_monitoring()

            if self.dashboard_dock is not None:
                self.dashboard_dock.close()

            logger.info('PyRPL Dashboard Extension closed')
        except Exception as exc:
            logger.error('Error closing dashboard extension: %s', exc)
