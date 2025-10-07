# tests/test_contract.py
import pytest
from unittest.mock import patch
import numpy as np

from qtpy.QtCore import QThread

from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

@pytest.fixture
def worker_thread(mock_pyrpl_instance):
    """Fixture to create and manage a PyrplWorker and its QThread."""
    thread = QThread()
    worker = PyrplWorker()
    worker.pyrpl = mock_pyrpl_instance
    worker.moveToThread(thread)
    thread.start()
    yield worker, thread
    thread.quit()
    thread.wait(1000)

@patch('pymodaq_plugins_pyrpl.hardware.pyrpl_worker.StemLab')
def test_connect_success(mock_stemlab_class, mock_pyrpl_instance):
    """Test successful connection to the StemLab instrument."""
    mock_stemlab_class.return_value = mock_pyrpl_instance
    worker = PyrplWorker()
    config = {'hostname': 'mock_host', 'gui': False}
    assert worker.connect(config) is True
    assert worker.pyrpl is not None
    assert worker.get_idn() == 'StemLab on mock_host'

@patch('pymodaq_plugins_pyrpl.hardware.pyrpl_worker.StemLab')
def test_connect_fail(mock_stemlab_class):
    """Test failed connection to the StemLab instrument."""
    mock_stemlab_class.side_effect = ConnectionError("Test Error")
    worker = PyrplWorker()
    config = {'hostname': 'mock_host', 'gui': False}
    assert worker.connect(config) is False
    assert worker.pyrpl is None

def test_disconnect(worker_thread):
    """Test disconnection from the StemLab instrument."""
    worker, thread = worker_thread
    worker.disconnect()
    assert worker.pyrpl is None


def test_acquire_trace(worker_thread, mock_pyrpl_instance):
    """Test acquiring a trace from the scope."""
    worker, thread = worker_thread
    times, data = worker.acquire_trace()
    mock_pyrpl_instance.scope._start_acquisition.assert_called_once()
    assert np.array_equal(times, mock_pyrpl_instance.scope.times)
    assert np.array_equal(data, mock_pyrpl_instance.scope._data_ch1)

def test_set_output_voltage(worker_thread, mock_pyrpl_instance):
    """Test setting the output voltage of an ASG."""
    worker, thread = worker_thread
    worker.set_output_voltage('out1', 1.23)
    mock_pyrpl_instance.asg0.setup.assert_called_with(amplitude=1.23, waveform='dc')

    worker.set_output_voltage('out2', -0.5)
    mock_pyrpl_instance.asg1.setup.assert_called_with(amplitude=-0.5, waveform='dc')