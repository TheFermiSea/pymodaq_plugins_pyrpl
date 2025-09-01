from pymodaq.extensions.utils import CustomExt
from qtpy import QtWidgets
from pymodaq_gui.utils.dock import Dock
from .utils import PyrplManager
from .pid_widget import PIDWidget

class DAQ_Pyrpl_Manager(CustomExt):
    """
    PyMoDAQ extension for managing PyRPL functionalities.
    """

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        self.pyrpl_manager = PyrplManager()
        self.setup_ui()

    def setup_actions(self):
        """
        Setup the actions for the extension's toolbar.
        """
        self.add_action('quit', 'Quit', 'close2')

    def setup_docks(self):
        """
        Setup the docks for the extension.
        """
        self.dock = Dock("PyRPL Manager", self.dockarea)
        self.dockarea.addDock(self.dock)

        widget = QtWidgets.QWidget()
        self.dock.addWidget(widget)

        # Add a text input for the hostname
        self.hostname_label = QtWidgets.QLabel("Hostname:")
        self.hostname_input = QtWidgets.QLineEdit("rp-f08c6d.local")

        # Add a button to connect to the Red Pitaya
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setCheckable(True)

        # Add a status label
        self.status_label = QtWidgets.QLabel("Disconnected")

        # Create the PID widget
        self.pid_widget = PIDWidget()
        self.pid_dock = Dock("PID Control", self.dockarea)
        self.pid_dock.addWidget(self.pid_widget)
        self.dockarea.addDock(self.pid_dock, 'right', self.dock)


        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.hostname_label, 0, 0)
        layout.addWidget(self.hostname_input, 0, 1)
        layout.addWidget(self.connect_button, 1, 0, 1, 2)
        layout.addWidget(self.status_label, 2, 0, 1, 2)
        widget.setLayout(layout)


    def connect_things(self):
        """
        Connect the signals and slots.
        """
        self.connect_action('quit', self.quit_fun)
        self.connect_button.clicked.connect(self.connect_to_pyrpl)

    def connect_to_pyrpl(self):
        """
        Connect to the Red Pitaya using PyRPL.
        """
        if self.connect_button.isChecked():
            hostname = self.hostname_input.text()
            if self.pyrpl_manager.connect(hostname):
                self.status_label.setText(f"Connected to {hostname}")
                self.connect_button.setText("Disconnect")
            else:
                self.status_label.setText(f"Failed to connect to {hostname}")
                self.connect_button.setChecked(False)
        else:
            self.pyrpl_manager.disconnect()
            self.status_label.setText("Disconnected")
            self.connect_button.setText("Connect")

    def quit_fun(self):
        """Quit the extension and disconnect from PyRPL."""
        self.pyrpl_manager.disconnect()
        self.dock.close()
