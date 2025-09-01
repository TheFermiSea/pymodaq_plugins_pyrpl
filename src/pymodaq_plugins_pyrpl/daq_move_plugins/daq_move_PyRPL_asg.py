from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class DAQ_Move_PyRPL_asg(DAQ_Move_base):
    """
    PyMoDAQ plugin for the PyRPL Arbitrary Signal Generator.
    """
    _controller_units = 'V'
    is_multiaxes = True
    axes_names = ['frequency', 'amplitude', 'offset']
    _epsilon = 0.01

    params = [
        {'title': 'PyRPL Settings', 'name': 'pyrpl_settings', 'type': 'group', 'children': [
            {'title': 'ASG Channel', 'name': 'asg_channel', 'type': 'int', 'value': 0},
        ]},
        {'title': 'ASG Settings', 'name': 'asg_settings', 'type': 'group', 'children': [
            {'title': 'Waveform', 'name': 'waveform', 'type': 'str', 'value': 'sin'},
            {'title': 'Output', 'name': 'output_direct', 'type': 'str', 'value': 'out1'},
        ]},
    ] + comon_parameters_fun(is_multiaxes, axes_names)

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.pyrpl_instance = None
        self.asg = None

    def get_actuator_value(self):
        if self.asg is not None:
            pos = [self.asg.frequency, self.asg.amplitude, self.asg.offset]
            return pos
        else:
            return [0, 0, 0]

    def move_abs(self, value):
        self.check_position(value)

    def move_rel(self, value):
        # get current position
        current_position = self.get_actuator_value()
        # calculate new position
        new_position = [current_position[i] + value[i] for i in range(len(value))]
        self.check_position(new_position)

    def move_home(self):
        self.move_abs([0, 0, 0])

    def check_position(self, position):
        if self.asg is not None:
            try:
                if position[0] is not None:
                    self.asg.frequency = position[0]
                if position[1] is not None:
                    self.asg.amplitude = position[1]
                if position[2] is not None:
                    self.asg.offset = position[2]
                self.emit_status(ThreadCommand('check_position', [position]))
            except Exception as e:
                logger.exception(str(e))
                self.emit_status(ThreadCommand('move_abs', [f'Error: {e}']))
        else:
            self.emit_status(ThreadCommand('move_abs', ['No ASG connected']))


    def commit_settings(self, param):
        if self.asg is not None:
            if param.name() == 'waveform':
                self.asg.waveform = param.value()
            elif param.name() == 'output_direct':
                self.asg.output_direct = param.value()

    def ini_stage(self, controller=None):
        self.status.update(edict=self.settings.saveState())
        if self.settings.child('multiaxes', 'ismultiaxes').value():
            self.is_multiaxes = True
            self.axes_names = self.settings.child('multiaxes', 'multi_axes_names').value()

        asg_channel = self.settings.child('pyrpl_settings', 'asg_channel').value()
        try:
            pyrpl_ext = self.dashboard.get_extension('PyRPL')
            if pyrpl_ext is None:
                raise Exception("PyRPL extension not loaded.")
            self.pyrpl_instance = pyrpl_ext.get_pyrpl_instance()
            if self.pyrpl_instance is None:
                raise Exception("Not connected to RedPitaya.")

            if asg_channel == 0:
                self.asg = self.pyrpl_instance.rp.asgs.pop('pymodaq_asg0')
            else:
                self.asg = self.pyrpl_instance.rp.asgs.pop('pymodaq_asg1')
            self.commit_settings(self.settings)
            self.status.update(message="Connected to RedPitaya.", edict=self.settings.saveState())
        except Exception as e:
            logger.exception(str(e))
            self.status.update(message=f"Could not get PyRPL instance: {e}", edict=self.settings.saveState())
            return False
        return True

    def ini_attributes(self):
        """Initialize plugin attributes"""
        self.asg = None
        self.pyrpl_instance = None

    def stop_motion(self):
        """Stop ASG output"""
        if self.asg is not None:
            self.asg.output_direct = 'off'
            logger.info("ASG output stopped")

    def close(self):
        if self.asg is not None:
            self.pyrpl_instance.rp.asgs.free(self.asg)

if __name__ == '__main__':
    main(__file__)
