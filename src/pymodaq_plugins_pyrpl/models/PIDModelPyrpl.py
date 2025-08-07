import numpy as np
from pymodaq.extensions.pid.utils import PIDModelGeneric, DataToActuatorPID, main
from pymodaq_data.data import DataToExport, DataCalculated

from pymodaq.utils.data import DataActuator
from pymodaq.utils.daq_utils import ThreadCommand

from typing import List, Optional

# Import the centralized PyRPL wrapper
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import (
    PyRPLConnection, get_pyrpl_manager, InputChannel, OutputChannel, 
    PIDChannel, PIDConfiguration, connect_redpitaya, disconnect_redpitaya
)


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
        {'title': 'PID channel:', 'name': 'pid_channel', 'type': 'list', 'limits': ['pid0', 'pid1', 'pid2'], 'value': 'pid0'},
        {'title': 'Use hardware PID:', 'name': 'use_hardware_pid', 'type': 'bool', 'value': True},
        {'title': 'P gain:', 'name': 'p_gain', 'type': 'float', 'value': 0.1},
        {'title': 'I gain:', 'name': 'i_gain', 'type': 'float', 'value': 0.01},
        {'title': 'D gain:', 'name': 'd_gain', 'type': 'float', 'value': 0.0},
        {'title': 'Voltage limit min:', 'name': 'voltage_limit_min', 'type': 'float', 'value': -1.0},
        {'title': 'Voltage limit max:', 'name': 'voltage_limit_max', 'type': 'float', 'value': 1.0},
    ]  # list of dict to initialize specific Parameters

    def __init__(self, pid_controller):
        super().__init__(pid_controller)
        self.pyrpl_config = 'pymodaq'
        self.pyrpl_connection: Optional[PyRPLConnection] = None
        self.manager = get_pyrpl_manager()
        self.current_hostname: Optional[str] = None

    def update_settings(self, param):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        Parameters
        ----------
        param: (Parameter) instance of Parameter object
        """
        if param.name() == 'redpitaya_host':
            self.ini_model()
        elif param.name() in ['use_hardware_pid', 'p_gain', 'i_gain', 'd_gain', 
                             'input_channel', 'output_channel', 'pid_channel',
                             'voltage_limit_min', 'voltage_limit_max']:
            # Update PID configuration when relevant parameters change
            self._update_pid_configuration()

    def ini_model(self):
        super().ini_model()

        # Disconnect from previous connection if hostname changed
        hostname = self.settings.child('redpitaya_host').value()
        if self.current_hostname and self.current_hostname != hostname:
            self._disconnect_current()
            
        self.current_hostname = hostname

        # Connect using the centralized manager
        try:
            def status_callback(cmd):
                self.pid_controller.emit_status(cmd)
                
            self.pyrpl_connection = connect_redpitaya(
                hostname=hostname,
                config_name=self.pyrpl_config,
                status_callback=status_callback
            )
            
            if self.pyrpl_connection and self.pyrpl_connection.is_connected:
                # Configure hardware PID if enabled
                self._update_pid_configuration()
            else:
                error_msg = "Failed to connect to Red Pitaya"
                if self.pyrpl_connection and self.pyrpl_connection.last_error:
                    error_msg += f": {self.pyrpl_connection.last_error}"
                self.pid_controller.emit_status(ThreadCommand('Update_Status', [error_msg, 'log']))
                
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

        # Read voltage directly from Red Pitaya using the centralized wrapper
        if self.pyrpl_connection and self.pyrpl_connection.is_connected:
            input_channel_name = self.settings.child('input_channel').value()
            input_channel = InputChannel.IN1 if input_channel_name == 'in1' else InputChannel.IN2
            
            voltage = self.pyrpl_connection.read_voltage(input_channel)
            if voltage is not None:
                return DataToExport('pid inputs',
                                    data=[DataCalculated('pid calculated',
                                                         data=[np.array([voltage])])])
        
        # Return zero if no connection or read failed
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
        if self.pyrpl_connection and self.pyrpl_connection.is_connected:
            use_hardware_pid = self.settings.child('use_hardware_pid').value()
            
            if use_hardware_pid:
                # When using hardware PID, update the setpoint instead of direct output
                pid_channel_name = self.settings.child('pid_channel').value()
                pid_channel = getattr(PIDChannel, pid_channel_name.upper())
                
                # Get current setpoint and add the PID output to it
                current_setpoint = self.pyrpl_connection.get_pid_setpoint(pid_channel)
                if current_setpoint is not None:
                    new_setpoint = current_setpoint + outputs[0]
                    
                    # Apply voltage limits
                    voltage_min = self.settings.child('voltage_limit_min').value()
                    voltage_max = self.settings.child('voltage_limit_max').value()
                    new_setpoint = np.clip(new_setpoint, voltage_min, voltage_max)
                    
                    self.pyrpl_connection.set_pid_setpoint(pid_channel, new_setpoint)
            else:
                # Fallback to direct sampler manipulation (legacy mode)
                redpitaya = self.pyrpl_connection.redpitaya
                if redpitaya is not None and hasattr(redpitaya, 'sampler'):
                    output_channel = self.settings.child('output_channel').value()
                    current_val = getattr(redpitaya.sampler, output_channel)
                    setattr(redpitaya.sampler, output_channel, current_val + outputs[0])

        # The PID actuator is not used, so we send an empty DataToActuatorPID
        return DataToActuatorPID('pid output', mode='rel', data=[])

    def _update_pid_configuration(self):
        """Update the hardware PID configuration with current settings."""
        if not (self.pyrpl_connection and self.pyrpl_connection.is_connected):
            return

        use_hardware_pid = self.settings.child('use_hardware_pid').value()
        if not use_hardware_pid:
            return

        try:
            # Get configuration parameters
            pid_channel_name = self.settings.child('pid_channel').value()
            pid_channel = getattr(PIDChannel, pid_channel_name.upper())
            
            input_channel_name = self.settings.child('input_channel').value()
            input_channel = InputChannel.IN1 if input_channel_name == 'in1' else InputChannel.IN2
            
            output_channel_name = self.settings.child('output_channel').value()
            output_channel = OutputChannel.OUT1 if output_channel_name == 'out1' else OutputChannel.OUT2
            
            # Create PID configuration
            config = PIDConfiguration(
                setpoint=0.0,  # Initial setpoint, will be updated by PyMoDAQ
                p_gain=self.settings.child('p_gain').value(),
                i_gain=self.settings.child('i_gain').value(),
                d_gain=self.settings.child('d_gain').value(),
                input_channel=input_channel,
                output_channel=output_channel,
                voltage_limit_min=self.settings.child('voltage_limit_min').value(),
                voltage_limit_max=self.settings.child('voltage_limit_max').value(),
                enabled=True
            )
            
            # Apply configuration to hardware
            success = self.pyrpl_connection.configure_pid(pid_channel, config)
            
            if success:
                self.pid_controller.emit_status(ThreadCommand('Update_Status', 
                    [f"Configured hardware PID {pid_channel_name}", 'log']))
            else:
                self.pid_controller.emit_status(ThreadCommand('Update_Status', 
                    [f"Failed to configure hardware PID {pid_channel_name}", 'log']))
                    
        except Exception as e:
            self.pid_controller.emit_status(ThreadCommand('Update_Status', 
                [f"Error configuring PID: {str(e)}", 'log']))

    def _disconnect_current(self):
        """Disconnect from current Red Pitaya device."""
        if self.current_hostname:
            try:
                def status_callback(cmd):
                    self.pid_controller.emit_status(cmd)
                    
                disconnect_redpitaya(self.current_hostname, self.pyrpl_config, status_callback)
                
            except Exception as e:
                self.pid_controller.emit_status(ThreadCommand('Update_Status', 
                    [f"Error disconnecting: {str(e)}", 'log']))
            finally:
                self.pyrpl_connection = None
                self.current_hostname = None

    def close(self):
        """Clean up resources when closing the model."""
        self._disconnect_current()

    def __del__(self):
        """Ensure proper cleanup on destruction."""
        try:
            self.close()
        except:
            pass  # Avoid errors during garbage collection


if __name__ == '__main__':
    main("BeamSteeringMockNoModel.xml")  # some preset configured with the right actuators and detectors
