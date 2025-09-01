import unittest
from unittest.mock import Mock, patch, MagicMock

import numpy as np
from pymodaq.extensions.pid.utils import PIDModelGeneric
from pymodaq_data.data import DataToExport, DataCalculated

class TestPIDModelPyRPL(unittest.TestCase):
    def setUp(self):
        self.mock_pyrpl = MagicMock()
        self.patcher = patch.dict('sys.modules', {'pyrpl': self.mock_pyrpl})
        self.patcher.start()

        from pymodaq_plugins_pyrpl.models.PIDModelPyRPL import PIDModelPyRPL

        self.pid_controller = Mock()
        self.pid_controller.dashboard.get_extension.return_value.get_pyrpl_instance.return_value = self.mock_pyrpl

        self.pid_model = PIDModelPyRPL(self.pid_controller)
        self.pid_model.settings = Mock()

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        self.assertIsInstance(self.pid_model, PIDModelGeneric)

    def test_ini_model(self):
        self.pid_model.settings.child.side_effect = [
            Mock(value=lambda: 0),  # pid_channel
        ]

        self.pid_model.ini_model()

        self.pid_controller.dashboard.get_extension.assert_called_with('PyRPL')
        self.assertIsNotNone(self.pid_model.pid)
        self.assertEqual(self.pid_model.pid, self.mock_pyrpl.rp.pid0)

    def test_update_settings(self):
        self.pid_model.pid = Mock()

        # Mock the settings
        mock_kp = Mock(value=lambda: 0.5)
        mock_ki = Mock(value=lambda: 0.1)
        mock_kd = Mock(value=lambda: 0.01)
        mock_setpoint = Mock(value=lambda: 1.0)
        mock_input = Mock(value=lambda: 'in2')
        mock_output = Mock(value=lambda: 'out2')

        self.pid_model.settings.child.side_effect = [
            mock_kp, mock_ki, mock_kd, # for kp, ki, kd
            mock_setpoint, # for setpoint
            mock_input, # for pyrpl_input
            mock_output, # for pyrpl_output
        ]

        # Test updating pid constants
        param_kp = Mock(name=lambda: 'kp')
        self.pid_model.update_settings(param_kp)
        self.assertEqual(self.pid_model.pid.kp, 0.5)
        self.assertEqual(self.pid_model.pid.ki, 0.1)
        self.assertEqual(self.pid_model.pid.kd, 0.01)

        # Test updating setpoint
        param_setpoint = Mock(name=lambda: 'setpoint')
        self.pid_model.update_settings(param_setpoint)
        self.assertEqual(self.pid_model.pid.setpoint, 1.0)

        # Test updating input/output
        param_input = Mock(name=lambda: 'pyrpl_input')
        self.pid_model.update_settings(param_input)
        self.assertEqual(self.pid_model.pid.input, 'in2')

        param_output = Mock(name=lambda: 'pyrpl_output')
        self.pid_model.update_settings(param_output)
        self.assertEqual(self.pid_model.pid.output_direct, 'out2')


    def test_convert_input(self):
        self.pid_model.pid = Mock()
        self.pid_model.pid.input.value = 1.5
        self.pid_model.pid.setpoint = 1.0

        data = self.pid_model.convert_input(None)

        self.assertIsInstance(data, DataToExport)
        self.assertEqual(data.name, 'pid_input')
        np.testing.assert_array_equal(data.data[0].data, np.array([0.5]))

if __name__ == '__main__':
    unittest.main()
