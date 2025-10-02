# tests/conftest.py
import pytest
from unittest.mock import MagicMock, PropertyMock
import numpy as np

@pytest.fixture
def mock_pyrpl_instance():
    """
    Provides a sophisticated mock of a StemLab object instance.
    This can be used to simulate hardware behavior in unit and integration tests.
    """
    stemlab = MagicMock()

    # Mock the hostname parameter
    stemlab.parameters = {'hostname': 'mock_host'}

    # Mock the Scope
    scope = MagicMock()
    scope.times = np.array([0.0, 0.1, 0.2])
    scope._data_ch1 = np.array([1.0, 2.0, 3.0])
    scope.curve_ready.return_value = True
    stemlab.scope = scope

    # Mock the ASGs
    asg0 = MagicMock()
    asg1 = MagicMock()
    stemlab.asg0 = asg0
    stemlab.asg1 = asg1

    return stemlab

@pytest.fixture
def mock_pyrpl_class(mock_pyrpl_instance):
    """
    Provides a mock of the StemLab class itself. When instantiated,
    it returns the sophisticated mock_pyrpl_instance.
    """
    mock_class = MagicMock(return_value=mock_pyrpl_instance)
    return mock_class