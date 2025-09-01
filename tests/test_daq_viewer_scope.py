import unittest
from unittest.mock import Mock, patch, MagicMock

import numpy as np
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq_data.data import DataFromPlugins, Axis

class TestDAQ_1DViewer_PyRPL_scope(unittest.TestCase):
    def setUp(self):
        self.mock_pyrpl = MagicMock()
        self.patcher = patch.dict('sys.modules', {'pyrpl': self.mock_pyrpl})
        self.patcher.start()

        from src.pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_scope import DAQ_1DViewer_PyRPL_scope
        self.plugin = DAQ_1DViewer_PyRPL_scope(parent=None, params_state=None)

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        self.assertIsInstance(self.plugin, DAQ_Viewer_base)

    def test_ini_detector(self):
        self.plugin.settings.child.side_effect = [
            Mock(value=lambda: 'Master'),
            Mock(value=lambda: '192.168.1.100'),
        ]

        self.assertTrue(self.plugin.ini_detector())
        self.mock_pyrpl.Pyrpl.assert_called_with(hostname='192.168.1.100')

    def test_grab_data(self):
        self.plugin.scope = Mock()
        self.plugin.scope.curve_async.return_value.result.return_value = (np.array([1, 2, 3]), np.array([4, 5, 6]))
        self.plugin.scope.times = np.array([0, 1, 2])

        self.plugin.dte_signal = Mock()
        self.plugin.grab_data()

        self.plugin.dte_signal.emit.assert_called_once()
        data = self.plugin.dte_signal.emit.call_args[0][0]
        self.assertIsInstance(data, DataFromPlugins)
        self.assertEqual(data.name, 'PyRPL Scope')
        self.assertEqual(len(data.data), 2)
        np.testing.assert_array_equal(data.data[0], np.array([1, 2, 3]))
        np.testing.assert_array_equal(data.data[1], np.array([4, 5, 6]))


if __name__ == '__main__':
    unittest.main()
