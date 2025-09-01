from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class DAQ_1DViewer_PyRPL_scope(DAQ_Viewer_base):
    """
    PyMoDAQ plugin for the PyRPL oscilloscope.
    """
    params = comon_parameters + [
        {'title': 'Scope Settings', 'name': 'scope_settings', 'type': 'group', 'children': [
            {'title': 'Channel 1', 'name': 'channel1', 'type': 'str', 'value': 'in1'},
            {'title': 'Channel 2', 'name': 'channel2', 'type': 'str', 'value': 'in2'},
            {'title': 'Decimation', 'name': 'decimation', 'type': 'int', 'value': 1},
            {'title': 'Trigger Source', 'name': 'trigger_source', 'type': 'str', 'value': 'ch1_positive_edge'},
            {'title': 'Trigger Threshold', 'name': 'trigger_threshold', 'type': 'float', 'value': 0.1},
            {'title': 'Trigger Hysteresis', 'name': 'trigger_hysteresis', 'type': 'float', 'value': 0.01},
            {'title': 'Averaging', 'name': 'averaging', 'type': 'bool', 'value': False},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.pyrpl_instance = None
        self.scope = None

    def commit_settings(self, param):
        if self.scope is not None:
            if param.name() == 'channel1':
                self.scope.input1 = param.value()
            elif param.name() == 'channel2':
                self.scope.input2 = param.value()
            elif param.name() == 'decimation':
                self.scope.decimation = param.value()
            elif param.name() == 'trigger_source':
                self.scope.trigger_source = param.value()
            elif param.name() == 'trigger_threshold':
                self.scope.threshold_ch1 = param.value()
            elif param.name() == 'trigger_hysteresis':
                self.scope.hysteresis_ch1 = param.value()
            elif param.name() == 'averaging':
                self.scope.average = param.value()

    def ini_detector(self, controller=None):
        self.status.update(edict=self.settings.odict)

        try:
            pyrpl_ext = self.dashboard.get_extension('PyRPL')
            if pyrpl_ext is None:
                raise Exception("PyRPL extension not loaded.")
            self.pyrpl_instance = pyrpl_ext.get_pyrpl_instance()
            if self.pyrpl_instance is None:
                raise Exception("Not connected to RedPitaya.")

            self.scope = self.pyrpl_instance.rp.scopes.pop('pymodaq_scope')
            self.commit_settings(self.settings)
            self.status.update(message="Connected to RedPitaya.", edict=self.settings.odict)
        except Exception as e:
            logger.exception(str(e))
            self.status.update(message=f"Could not get PyRPL instance: {e}", edict=self.settings.odict)
            return False
        return True

    def close(self):
        if self.scope is not None:
            self.pyrpl_instance.rp.scopes.free(self.scope)

    def grab_data(self, Naverage=1, **kwargs):
        if self.scope is not None:
            try:
                future = self.scope.curve_async()
                ch1_data, ch2_data = future.result()

                x_axis = Axis(data=self.scope.times, label='Time', units='s')

                self.dte_signal.emit(DataFromPlugins(
                    name='PyRPL Scope',
                    data=[ch1_data, ch2_data],
                    dim='Data1D',
                    labels=['Channel 1', 'Channel 2'],
                    x_axis=x_axis,
                ))
            except Exception as e:
                logger.exception(str(e))
                self.dte_signal.emit(DataFromPlugins(name='PyRPL Scope', data=[], dim='Data1D', labels=[]))
        else:
            self.dte_signal.emit(DataFromPlugins(name='PyRPL Scope', data=[], dim='Data1D', labels=[]))

if __name__ == '__main__':
    main(__file__)
