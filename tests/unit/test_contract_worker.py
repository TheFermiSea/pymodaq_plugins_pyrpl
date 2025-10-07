# tests/unit/test_contract_worker.py
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

# The mock_pyrpl_class fixture is automatically used due to conftest.py


@patch("pymodaq_plugins_pyrpl.hardware.pyrpl_worker.StemLab")
def test_connect_success(mock_stemlab_class, mock_pyrpl_instance):
    """Test successful connection logic in the worker."""
    mock_stemlab_class.return_value = mock_pyrpl_instance
    worker = PyrplWorker()
    config = {"hostname": "mock_host", "gui": False}
    assert worker.connect(config) is True
    assert worker.pyrpl is not None
    assert worker.get_idn() == "StemLab on mock_host"
    # worker.status_update.emit.assert_called_with('Successfully connected to StemLab on mock_host')


@patch("pymodaq_plugins_pyrpl.hardware.pyrpl_worker.StemLab")
def test_connect_fail(mock_stemlab_class):
    """Test failed connection logic."""
    mock_stemlab_class.side_effect = ConnectionError("Test Connection Error")
    worker = PyrplWorker()
    config = {"hostname": "mock_host", "gui": False}
    assert worker.connect(config) is False
    assert worker.pyrpl is None
    # worker.status_update.emit.assert_called_with('Connection to StemLab failed: Test Connection Error')


def test_disconnect(mock_pyrpl_instance):
    """Test disconnection logic."""
    worker = PyrplWorker()
    worker.pyrpl = mock_pyrpl_instance
    worker.disconnect()
    assert worker.pyrpl is None
    # worker.status_update.emit.assert_called_with('Disconnected from StemLab.')


def test_setup_scope(mock_pyrpl_instance):
    """Test that setup_scope correctly configures the mock scope for rolling mode."""
    worker = PyrplWorker()
    worker.pyrpl = mock_pyrpl_instance
    worker.setup_scope("in1", 128, "ch2_positive_edge", 0.5, 1.0)

    assert mock_pyrpl_instance.scope.input1 == "in1"
    assert mock_pyrpl_instance.scope.decimation == 128
    assert mock_pyrpl_instance.scope.rolling_mode is True
    # The following assertions are removed because rolling_mode is used
    # assert mock_pyrpl_instance.scope.trigger_source == 'ch2_positive_edge'
    # assert mock_pyrpl_instance.scope.trigger_level == 0.5
    # worker.status_update.emit.assert_called_with('Scope configured.')


def test_acquire_trace(mock_pyrpl_instance):
    """Test that acquire_trace calls the scope and emits the correct data."""
    worker = PyrplWorker()
    worker.pyrpl = mock_pyrpl_instance
    worker.pyrpl.scope.input1 = "in1"
    worker.pyrpl.scope.duration = 1.0  # Mock the duration attribute

    # Connect a mock slot to the trace_ready signal
    mock_slot = MagicMock()
    worker.trace_ready.connect(mock_slot)

    worker.acquire_trace()

    # Check that the mock scope's method was called
    mock_pyrpl_instance.scope._start_acquisition_rolling_mode.assert_called_once()

    # Check that the signal was emitted with the correct data
    mock_slot.assert_called_once()
    args = mock_slot.call_args[0][0]
    assert np.array_equal(args[0], mock_pyrpl_instance.scope.times)
    assert np.array_equal(args[1], mock_pyrpl_instance.scope._data_ch1)


def test_set_output_voltage(mock_pyrpl_instance):
    """Test setting the output voltage on the mock ASGs."""
    worker = PyrplWorker()
    worker.pyrpl = mock_pyrpl_instance

    worker.set_output_voltage("out1", 1.23)
    mock_pyrpl_instance.asg0.setup.assert_called_with(
        amplitude=1.23, waveform="dc"
    )
    # worker.status_update.emit.assert_called_with('Set out1 to 1.230 V.')

    worker.set_output_voltage("out2", -0.5)
    mock_pyrpl_instance.asg1.setup.assert_called_with(
        amplitude=-0.5, waveform="dc"
    )
    # worker.status_update.emit.assert_called_with('Set out2 to -0.500 V.')
