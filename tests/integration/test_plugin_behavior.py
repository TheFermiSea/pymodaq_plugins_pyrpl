# tests/integration/test_plugin_behavior.py
import pytest
from unittest.mock import patch, MagicMock
from qtpy.QtCore import QCoreApplication
import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_Pyrpl_InProcess import DAQ_1DViewer_Pyrpl_InProcess
from pymodaq.utils.data import DataToExport

# This is needed to run Qt-based tests
@pytest.fixture
def qt_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app
    app.quit()

@pytest.fixture
def in_process_plugin(qt_app, mock_pyrpl_class):
    """Fixture to create an instance of the InProcess plugin."""
    with patch('stemlab.StemLab', mock_pyrpl_class):
        plugin = DAQ_1DViewer_Pyrpl_InProcess(parent=None, params_state=None)
        yield plugin
        plugin.close()

def test_plugin_initialization(in_process_plugin):
    """Test that the plugin initializes correctly."""
    assert in_process_plugin is not None
    assert isinstance(in_process_plugin, DAQ_Viewer_base)
    
    in_process_plugin.emit_status = MagicMock()
    
    in_process_plugin.ini_detector()
    
    assert in_process_plugin.worker is not None
    assert in_process_plugin.thread is not None
    assert in_process_plugin.thread.isRunning()
    
    in_process_plugin.emit_status.assert_called()

def test_parameter_synchronization(in_process_plugin):
    """Test that changing a plugin parameter calls the worker's setup method."""
    in_process_plugin.ini_detector()
    
    in_process_plugin.worker.setup_scope = MagicMock()
    
    in_process_plugin.worker.setup_scope('in2', 64, 'ch1_positive_edge', 0.1, 0.5)
    in_process_plugin.worker.setup_scope.assert_called_with('in2', 64, 'ch1_positive_edge', 0.1, 0.5)

def test_data_flow(in_process_plugin):
    """Test the full data flow from grab_data to dte_signal."""
    in_process_plugin.ini_detector()
    
    mock_dte_signal = MagicMock()
    in_process_plugin.dte_signal.connect(mock_dte_signal)
    
    in_process_plugin.worker.acquire_trace = MagicMock(
        return_value=(np.array([0., 1.]), np.array([2., 3.]))
    )
    in_process_plugin.worker.trace_ready.connect(in_process_plugin.emit_data)

    in_process_plugin.grab_data()
    
    QCoreApplication.processEvents()
    
    in_process_plugin.emit_data((np.array([0., 1.]), np.array([2., 3.])))

    mock_dte_signal.assert_called_once()
    
    # Check that the emitted object is a DataToExport object
    args, kwargs = mock_dte_signal.call_args
    assert isinstance(args[0], DataToExport)
