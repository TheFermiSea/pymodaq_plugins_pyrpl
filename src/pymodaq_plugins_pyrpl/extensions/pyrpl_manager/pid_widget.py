from qtpy import QtWidgets
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D

class PIDWidget(QtWidgets.QWidget):
    """
    Widget for controlling the PID.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setup_ui()

    def setup_ui(self):
        """
        Setup the UI for the PID widget.
        """
        # Create the UI elements
        self.p_label = QtWidgets.QLabel("P:")
        self.p_input = QtWidgets.QDoubleSpinBox()
        self.i_label = QtWidgets.QLabel("I:")
        self.i_input = QtWidgets.QDoubleSpinBox()
        self.d_label = QtWidgets.QLabel("D:")
        self.d_input = QtWidgets.QDoubleSpinBox()

        self.enable_button = QtWidgets.QPushButton("Enable PID")
        self.enable_button.setCheckable(True)

        self.plot = Viewer1D()

        # Create the layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.p_label, 0, 0)
        layout.addWidget(self.p_input, 0, 1)
        layout.addWidget(self.i_label, 1, 0)
        layout.addWidget(self.i_input, 1, 1)
        layout.addWidget(self.d_label, 2, 0)
        layout.addWidget(self.d_input, 2, 1)
        layout.addWidget(self.enable_button, 3, 0, 1, 2)
        layout.addWidget(self.plot, 4, 0, 1, 2)

        self.setLayout(layout)
