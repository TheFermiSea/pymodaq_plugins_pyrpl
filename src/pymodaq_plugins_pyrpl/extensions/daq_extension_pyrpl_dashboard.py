"""PyRPL Dashboard Extension for PyMoDAQ."""

import logging
from typing import Dict, Optional

from pymodaq.extensions.utils import CustomExt
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.utils.dock import Dock
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QThread, Signal, Slot

from ..hardware.connection import PyrplConnectionWorker
from .pyrpl_manager.pid_widget import PIDWidget


logger = logging.getLogger(__name__)


class DAQ_PyRPL_Dashboard_Extension(CustomExt):
    """Dashboard extension providing PyRPL connection overview."""

    do_connect = Signal(str)

    params = [
        {
            'title': 'New Connection',
            'name': 'new_connection',
            'type': 'group',
            'children': [
                {
                    'title': 'Hostname:',
                    'name': 'hostname',
                    'type': 'str',
                    'value': '192.168.1.100',
                    'tip': 'Hostname or IP address of the Red Pitaya'
                },
                {
                    'title': 'Connect',
                    'name': 'connect',
                    'type': 'bool_push',
                    'label': 'Connect'
                },
            ]
        }
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        self.pyrpl_instances: Dict[str, object] = {}
        self.settings: Optional[Parameter] = None
        self.param_tree: Optional[ParameterTree] = None
        self.connection_table: Optional[QtWidgets.QTableWidget] = None

        self.setup_ui()
        self.setup_thread()

    def setup_thread(self):
        self.thread = QThread()
        self.worker = PyrplConnectionWorker()
        self.worker.moveToThread(self.thread)

        self.do_connect.connect(self.worker.connect_to_redpitaya)
        self.worker.connection_success.connect(self.on_connection_success)
        self.worker.connection_error.connect(self.on_connection_error)

        self.thread.start()

    def setup_actions(self):
        """Configure toolbar actions."""
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

        # Connection table
        self.connection_table = QtWidgets.QTableWidget(0, 3)
        self.connection_table.setHorizontalHeaderLabels([
            'Hostname', 'Status', 'Disconnect'
        ])
        header = self.connection_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        main_layout.addWidget(self.param_tree)
        main_layout.addWidget(self.connection_table)

        dock_widget.setLayout(main_layout)
        self.dashboard_dock.addWidget(dock_widget)

        # PID dock
        self.pid_dock = Dock("PID Control", self.dockarea)
        self.pid_widget = PIDWidget()
        self.pid_dock.addWidget(self.pid_widget)
        self.dockarea.addDock(self.pid_dock, 'right', self.dashboard_dock)


    def connect_things(self):
        """Connect UI actions and worker signals."""
        self.connect_action('quit', self.quit_extension)
        self.settings.child('new_connection', 'connect').sigValueChanged.connect(self.connect_device)

    def connect_device(self):
        hostname = self.settings.child('new_connection', 'hostname').value()
        if hostname not in self.pyrpl_instances:
            self.do_connect.emit(hostname)

    @Slot(object)
    def on_connection_success(self, pyrpl_instance):
        hostname = pyrpl_instance.hostname
        self.pyrpl_instances[hostname] = pyrpl_instance
        self.update_connection_table()

    @Slot(str)
    def on_connection_error(self, error_message):
        logger.error(error_message)
        self.update_connection_table()

    def update_connection_table(self):
        """Refresh the connection table."""
        if self.connection_table is None:
            return

        self.connection_table.setRowCount(len(self.pyrpl_instances))

        for row, (hostname, instance) in enumerate(self.pyrpl_instances.items()):
            status = 'Connected' if instance is not None else 'Error'
            self.connection_table.setItem(row, 0, QtWidgets.QTableWidgetItem(hostname))
            self.connection_table.setItem(row, 1, QtWidgets.QTableWidgetItem(status))

            disconnect_btn = QtWidgets.QPushButton('Disconnect')
            disconnect_btn.clicked.connect(lambda _, h=hostname: self.disconnect_device(h))
            self.connection_table.setCellWidget(row, 2, disconnect_btn)

    def disconnect_device(self, hostname: str):
        if hostname in self.pyrpl_instances:
            instance = self.pyrpl_instances.pop(hostname)
            if instance is not None:
                instance.end()
            self.update_connection_table()

    def quit_extension(self) -> None:
        """Cleanup and close dashboards."""
        try:
            for hostname in list(self.pyrpl_instances.keys()):
                self.disconnect_device(hostname)
            self.thread.quit()
            self.thread.wait(5000)

            if self.dashboard_dock is not None:
                self.dashboard_dock.close()

            logger.info('PyRPL Dashboard Extension closed')
        except Exception as exc:
            logger.error('Error closing dashboard extension: %s', exc)