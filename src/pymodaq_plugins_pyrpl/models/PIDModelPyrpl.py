import numpy as np
import pyrpl
from pymodaq.extensions.pid.utils import PIDModelGeneric, DataToActuatorPID, main
from pymodaq_data.data import DataToExport, DataCalculated

from pymodaq.utils.data import DataActuator
from pymodaq.utils.daq_utils import ThreadCommand

from typing import List


class PIDModelPyrpl(PIDModelGeneric):
    """
    PID model for the Red Pitaya, using the PyRPL library.
    This model does not use any external detectors or actuators, but communicates
    directly with the Red Pitaya.
    """
    limits = dict(max=dict(state=True, value=1),
                  min=dict(state=True, value=-1),)
    konstants = dict(kp=0.1, ki=0.000, kd=0.0000)

    Nsetpoints = 1  # number of setpoints
    setpoint_ini = [0.0]  # number and values of initial setpoints
    setpoints_names = ['Setpoint']  # number and names of setpoints

    actuators_name = []  # names of actuator's control modules involved in the PID
    detectors_name = []  # names of detector's control modules involved in the PID

    params = [
        {'title': 'RedPitaya Host:', 'name': 'redpitaya_host', 'type': 'str', 'value': 'rp-f0a552.local'},
        {'title': 'Input channel:', 'name': 'input_channel', 'type': 'list', 'limits': ['in1', 'in2'], 'value': 'in1'},
        {'title': 'Output channel:', 'name': 'output_channel', 'type': 'list', 'limits': ['out1', 'out2'], 'value': 'out1'},
    ]  # list of dict to initialize specific Parameters

    def __init__(self, pid_controller):
        super().__init__(pid_controller)
        self.pyrpl_config = 'pymodaq'
        self.pyrpl = None
        self.redpitaya = None

    def update_settings(self, param):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        Parameters
        ----------
        param: (Parameter) instance of Parameter object
        """
        if param.name() == 'redpitaya_host':
            self.ini_model()

    def ini_model(self):
        super().ini_model()

        # add here other specifics initialization if needed
        try:
            self.pid_controller.emit_status(ThreadCommand('Update_Status', [f"Connecting to RedPitaya at {self.settings.child('redpitaya_host').value()}", 'log']))
            self.pyrpl = pyrpl.Pyrpl(config=self.pyrpl_config,
                                     hostname=self.settings.child('redpitaya_host').value())
            self.redpitaya = self.pyrpl.redpitaya
            self.pid_controller.emit_status(ThreadCommand('Update_Status', ["RedPitaya connected", 'log']))
        except Exception as e:
            self.pid_controller.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))

    def convert_input(self, measurements: DataToExport):
        """
        Convert the measurements in the units to be fed to the PID (same dimensionality as the setpoint)
        Parameters
        ----------
        measurements: DataToExport
            Data from the declared detectors from which the model extract a value of the same units as the setpoint

        Returns
        -------
        InputFromDetector: the converted input in the setpoints units

        """

        # For pyrpl, we don't use a detector, we read directly from the redpitaya
        if self.redpitaya is not None:
            input_channel = self.settings.child('input_channel').value()
            if hasattr(self.redpitaya, 'sampler'):
                val = getattr(self.redpitaya.sampler, input_channel)
                return DataToExport('pid inputs',
                                    data=[DataCalculated('pid calculated',
                                                         data=[np.array([val])])])
        return DataToExport('pid inputs', data=[DataCalculated('pid calculated', data=[np.array([0.0])])])


    def convert_output(self, outputs: List[float], dt: float, stab=True) -> DataToActuatorPID:
        """
        Convert the output of the PID in units to be fed into the actuator
        Parameters
        ----------
        outputs: List of float
            output value from the PID from which the model extract a value of the same units as the actuator
        dt: float
            Ellapsed time since the last call to this function
        stab: bool

        Returns
        -------
        OutputToActuator: the converted output

        """
        # For pyrpl, we don't use an actuator, we write directly to the redpitaya
        if self.redpitaya is not None and hasattr(self.redpitaya, 'sampler'):
            output_channel = self.settings.child('output_channel').value()
            current_val = getattr(self.redpitaya.sampler, output_channel)
            setattr(self.redpitaya.sampler, output_channel, current_val + outputs[0])


        # The PID actuator is not used, so we send an empty DataToActuatorPID
        return DataToActuatorPID('pid output', mode='rel', data=[])


if __name__ == '__main__':
    main("BeamSteeringMockNoModel.xml")  # some preset configured with the right actuators and detectors
