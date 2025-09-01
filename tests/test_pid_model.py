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
        # Create a proper mock PID object with all necessary attributes
        pid_mock = Mock()
        pid_mock.kp = 0.0
        pid_mock.ki = 0.0
        pid_mock.kd = 0.0
        pid_mock.setpoint = 0.0
        pid_mock.input = 'in1'
        pid_mock.output_direct = 'out1'
        self.pid_model.pid = pid_mock

        # Mock the settings structure to return expected values
        def mock_child(*args):
            path = '/'.join(args)
            if path == 'main_settings/pid_controls/kp':
                return Mock(value=lambda: 0.5)
            elif path == 'main_settings/pid_controls/ki':
                return Mock(value=lambda: 0.1)
            elif path == 'main_settings/pid_controls/kd':
                return Mock(value=lambda: 0.01)
            elif path == 'main_settings/setpoints/setpoint':
                return Mock(value=lambda: 1.0)
            else:
                return Mock(value=lambda: None)
        
        self.pid_model.settings.child = mock_child

        # Test updating PID constants
        param_kp = Mock()
        param_kp.name.return_value = 'kp'
        self.pid_model.update_settings(param_kp)
        self.assertEqual(self.pid_model.pid.kp, 0.5)
        self.assertEqual(self.pid_model.pid.ki, 0.1)
        self.assertEqual(self.pid_model.pid.kd, 0.01)

        # Test updating setpoint
        param_setpoint = Mock()
        param_setpoint.name.return_value = 'setpoint'
        self.pid_model.update_settings(param_setpoint)
        self.assertEqual(self.pid_model.pid.setpoint, 1.0)

        # Test updating input/output
        param_input = Mock()
        param_input.name.return_value = 'pyrpl_input'
        param_input.value.return_value = 'in2'
        self.pid_model.update_settings(param_input)
        self.assertEqual(self.pid_model.pid.input, 'in2')

        param_output = Mock()
        param_output.name.return_value = 'pyrpl_output'
        param_output.value.return_value = 'out2'
        self.pid_model.update_settings(param_output)
        self.assertEqual(self.pid_model.pid.output_direct, 'out2')


    def test_convert_input(self):
        self.pid_model.pid = Mock()
        self.pid_model.pid.input.value = 1.5
        self.pid_model.pid.setpoint = 1.0

        data = self.pid_model.convert_input(None)

        self.assertIsInstance(data, DataToExport)
        self.assertEqual(data.name, 'pid_input')
        np.testing.assert_array_equal(data.data[0].data[0], np.array([0.5]))

if __name__ == '__main__':
    unittest.main()
