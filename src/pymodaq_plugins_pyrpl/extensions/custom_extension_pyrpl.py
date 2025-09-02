from qtpy import QtWidgets
from pymodaq_gui import utils as gutils
from pymodaq_utils.config import Config, ConfigError
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.extensions.utils import CustomExt
from pymodaq_plugins_pyrpl.utils import Config as PluginConfig
import pyrpl

logger = set_logger(get_module_name(__file__))
main_config = Config()
plugin_config = PluginConfig()

EXTENSION_NAME = 'PyRPL'
CLASS_NAME = 'PyRPLExtension'

class PyRPLExtension(CustomExt):
    params = [
        {'title': 'Connection', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Hostname', 'name': 'hostname', 'type': 'str', 'value': '192.168.1.100'},
            {'title': 'Connect', 'name': 'connect', 'type': 'bool_push', 'label': 'Connect'},
            {'title': 'Disconnect', 'name': 'disconnect', 'type': 'bool_push', 'label': 'Disconnect'},
            {'title': 'Status', 'name': 'status', 'type': 'str', 'value': 'Disconnected', 'readonly': True},
        ]},
    ]

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)
        self.pyrpl_instance = None
        self.setup_ui()

    def get_pyrpl_instance(self):
        return self.pyrpl_instance

    def setup_docks(self):
        # Main dock for the extension
        self.docks[EXTENSION_NAME] = gutils.Dock(EXTENSION_NAME)
        self.dockarea.addDock(self.docks[EXTENSION_NAME])
        self.docks[EXTENSION_NAME].addWidget(self.settings_tree)

        # Docks for the different modules
        self.docks['Scope'] = gutils.Dock('Oscilloscope')
        self.docks['SA'] = gutils.Dock('Spectrum Analyzer')
        self.docks['ASG'] = gutils.Dock('ASG')
        self.docks['PID'] = gutils.Dock('PID')

        self.dockarea.addDock(self.docks['Scope'], 'right', self.docks[EXTENSION_NAME])
        self.dockarea.addDock(self.docks['SA'], 'bottom', self.docks['Scope'])
        self.dockarea.addDock(self.docks['ASG'], 'right', self.docks['Scope'])
        self.dockarea.addDock(self.docks['PID'], 'bottom', self.docks['ASG'])

        # Add widgets to the docks
        self.add_module_control(self.docks['Scope'], 'Scope', 'DAQ_1DViewer_PyRPL_scope')
        self.add_module_control(self.docks['SA'], 'SA', 'DAQ_1DViewer_PyRPL_sa')
        self.add_module_control(self.docks['ASG'], 'ASG', 'DAQ_Move_PyRPL_asg')
        self.add_pid_control(self.docks['PID'])

    def add_module_control(self, dock, title, plugin_name):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        label = QtWidgets.QLabel(f'{title} Controls')
        launch_button = QtWidgets.QPushButton(f'Launch {title}')

        layout.addWidget(label)
        layout.addWidget(launch_button)

        dock.addWidget(widget)

        launch_button.clicked.connect(lambda: self.dashboard.load_plugin_by_name(plugin_name, 'daq_viewer' if 'Viewer' in plugin_name else 'daq_move'))

    def add_pid_control(self, dock):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        label = QtWidgets.QLabel('PID Controls')
        launch_button = QtWidgets.QPushButton('Launch PID')

        layout.addWidget(label)
        layout.addWidget(launch_button)

        dock.addWidget(widget)

        launch_button.clicked.connect(lambda: self.dashboard.load_pid_model('PyRPL_PID'))


    def setup_actions(self):
        self.add_action('connect', 'Connect', 'connect', "Connect to RedPitaya")
        self.add_action('disconnect', 'Disconnect', 'disconnect', "Disconnect from RedPitaya")

    def connect_things(self):
        self.settings.child('connection', 'connect').sigValueChanged.connect(self.connect_to_redpitaya)
        self.settings.child('connection', 'disconnect').sigValueChanged.connect(self.disconnect_from_redpitaya)

    def value_changed(self, param):
        pass

    def connect_to_redpitaya(self):
        if self.pyrpl_instance is None:
            hostname = self.settings.child('connection', 'hostname').value()
            try:
                self.pyrpl_instance = pyrpl.Pyrpl(hostname=hostname)
                self.settings.child('connection', 'status').setValue('Connected')
            except Exception as e:
                logger.exception(str(e))
                self.settings.child('connection', 'status').setValue(f'Error: {e}')
        else:
            self.settings.child('connection', 'status').setValue('Already connected')

    def disconnect_from_redpitaya(self):
        if self.pyrpl_instance is not None:
            self.pyrpl_instance = None
            self.settings.child('connection', 'status').setValue('Disconnected')

def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq_gui.utils.loader_utils import load_dashboard_with_preset
    from pymodaq_utils.messenger import messagebox

    app = mkQApp(EXTENSION_NAME)
    try:
        preset_file_name = plugin_config('presets', f'preset_for_{CLASS_NAME.lower()}')
        load_dashboard_with_preset(preset_file_name, EXTENSION_NAME)
        app.exec()
    except ConfigError as e:
        messagebox(f'No entry with name f"preset_for_{CLASS_NAME.lower()}" has been configured'
                   f'in the plugin config file. The toml entry should be:\n'
                   f'[presets]'
                   f"preset_for_{CLASS_NAME.lower()} = {'a name for an existing preset'}"
                   )

if __name__ == '__main__':
    main()
