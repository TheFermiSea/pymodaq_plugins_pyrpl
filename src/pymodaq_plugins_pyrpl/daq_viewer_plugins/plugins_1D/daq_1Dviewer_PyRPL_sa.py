from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class DAQ_1DViewer_PyRPL_sa(DAQ_Viewer_base):
    """
    PyMoDAQ plugin for the PyRPL spectrum analyzer.
    """
    params = comon_parameters + [
        {'title': 'Spectrum Analyzer Settings', 'name': 'sa_settings', 'type': 'group', 'children': [
            {'title': 'Input 1', 'name': 'input1', 'type': 'str', 'value': 'in1'},
            {'title': 'Span', 'name': 'span', 'type': 'float', 'value': 1e6},
            {'title': 'RBW', 'name': 'rbw', 'type': 'float', 'value': 1000},
            {'title': 'Window', 'name': 'window', 'type': 'str', 'value': 'blackman'},
            {'title': 'Trace Averages', 'name': 'trace_averages', 'type': 'int', 'value': 1},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.pyrpl_instance = None
        self.sa = None

    def commit_settings(self, param):
        if self.sa is not None:
            if param.name() == 'input1':
                self.sa.input1_baseband = param.value()
            elif param.name() == 'span':
                self.sa.span = param.value()
            elif param.name() == 'rbw':
                self.sa.rbw = param.value()
            elif param.name() == 'window':
                self.sa.window = param.value()
            elif param.name() == 'trace_averages':
                self.sa.trace_averages = param.value()

    def ini_detector(self, controller=None):
        self.status.update(edict=self.settings.saveState())

        try:
            pyrpl_ext = self.dashboard.get_extension('PyRPL')
            if pyrpl_ext is None:
                raise Exception("PyRPL extension not loaded.")
            self.pyrpl_instance = pyrpl_ext.get_pyrpl_instance()
            if self.pyrpl_instance is None:
                raise Exception("Not connected to RedPitaya.")

            self.sa = self.pyrpl_instance.spectrumanalyzer
            self.commit_settings(self.settings)
            self.status.update(message="Connected to RedPitaya.", edict=self.settings.saveState())
        except Exception as e:
            logger.exception(str(e))
            self.status.update(message=f"Could not get PyRPL instance: {e}", edict=self.settings.saveState())
            return False
        return True

    def close(self):
        pass # The SA is a software module, no need to free it

    def grab_data(self, Naverage=1, **kwargs):
        if self.sa is not None:
            try:
                ch1_data, _, _, _ = self.sa.curve()

                x_axis = Axis(data=self.sa.frequencies, label='Frequency', units='Hz')

                self.dte_signal.emit(DataFromPlugins(
                    name='PyRPL Spectrum Analyzer',
                    data=[ch1_data],
                    dim='Data1D',
                    labels=['Spectrum'],
                    x_axis=x_axis,
                ))
            except Exception as e:
                logger.exception(str(e))
                self.dte_signal.emit(DataFromPlugins(name='PyRPL Spectrum Analyzer', data=[], dim='Data1D', labels=[]))
        else:
            self.dte_signal.emit(DataFromPlugins(name='PyRPL Spectrum Analyzer', data=[], dim='Data1D', labels=[]))


if __name__ == '__main__':
    main(__file__)
