import numpy as np
from pymodaq.extensions.pid.utils import PIDModelGeneric, DataToActuatorPID
from pymodaq_data.data import DataToExport, DataCalculated
from pymodaq.utils.data import DataActuator
from typing import List
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class PIDModelPyRPL(PIDModelGeneric):
    """
    PID model for the RedPitaya using the PyRPL library.
    This model directly controls the hardware PID on the RedPitaya.
    """
    limits = dict(max=dict(state=True, value=1),
                  min=dict(state=True, value=-1),)
    konstants = dict(kp=0.1, ki=0.000, kd=0.0000)

    Nsetpoints = 1
    setpoint_ini = [0.]
    setpoints_names = ['Setpoint']

    actuators_name = []  # No actuators are directly controlled by this model
    detectors_name = []  # No detectors are directly controlled by this model

    params = [
        {'title': 'PyRPL Settings', 'name': 'pyrpl_settings', 'type': 'group', 'children': [
            {'title': 'PID Channel', 'name': 'pid_channel', 'type': 'int', 'value': 0},
            {'title': 'Input', 'name': 'pyrpl_input', 'type': 'str', 'value': 'in1'},
            {'title': 'Output', 'name': 'pyrpl_output', 'type': 'str', 'value': 'out1'},
        ]},
    ]

    def __init__(self, pid_controller):
        super().__init__(pid_controller)
        self.pyrpl_instance = None
        self.pid = None

    def update_settings(self, param):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        """
        if self.pid is not None:
            if param.name() in ['kp', 'ki', 'kd']:
                self.pid.kp = self.settings.child('main_settings', 'pid_controls', 'kp').value()
                self.pid.ki = self.settings.child('main_settings', 'pid_controls', 'ki').value()
                self.pid.kd = self.settings.child('main_settings', 'pid_controls', 'kd').value()
            elif param.name() == 'setpoint':
                self.pid.setpoint = self.settings.child('main_settings', 'setpoints', 'setpoint').value()
            elif param.name() == 'pyrpl_input':
                self.pid.input = param.value()
            elif param.name() == 'pyrpl_output':
                self.pid.output_direct = param.value()

    def ini_model(self):
        super().ini_model()
        try:
            # Get the pyrpl instance from the extension
            pyrpl_ext = self.pid_controller.dashboard.get_extension('PyRPL')
            if pyrpl_ext is None:
                raise Exception("PyRPL extension not loaded.")
            self.pyrpl_instance = pyrpl_ext.get_pyrpl_instance()
            if self.pyrpl_instance is None:
                raise Exception("Not connected to RedPitaya.")

            pid_channel = self.settings.child('pyrpl_settings', 'pid_channel').value()
            if pid_channel == 0:
                self.pid = self.pyrpl_instance.rp.pid0
            elif pid_channel == 1:
                self.pid = self.pyrpl_instance.rp.pid1
            else:
                self.pid = self.pyrpl_instance.rp.pid2

            self.update_settings(self.settings) # Apply all settings
        except Exception as e:
            logger.exception(str(e))
            self.pid_controller.status_sig.emit(f'Could not get PyRPL instance: {e}')

    def update_pid(self, dt):
        """
        Bypass the software PID and do nothing.
        The PID loop is running on the hardware.
        """
        pass

    def convert_input(self, measurements: DataToExport):
        """
        Read the error signal from the hardware PID.
        """
        if self.pid is not None:
            # The input to the software PID is the error signal from the hardware PID
            error = self.pid.input.value - self.pid.setpoint
            return DataToExport('pid_input', data=[DataCalculated('pid_input', data=[np.array([error])])])
        else:
            return DataToExport('pid_input', data=[DataCalculated('pid_input', data=[np.array([0.])])])

    def convert_output(self, outputs: List[float], dt: float, stab=True) -> DataToActuatorPID:
        """
        This method is not used for a hardware PID.
        """
        return DataToActuatorPID('pid_output', mode='abs', data=[])

if __name__ == '__main__':
    from pymodaq.extensions.pid.utils import main
    main()
