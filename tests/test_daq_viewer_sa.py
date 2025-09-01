import unittest
from unittest.mock import Mock, patch, MagicMock

import numpy as np
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq.utils.data import DataFromPlugins
from pymodaq_data.data import Axis

class TestDAQ_1DViewer_PyRPL_sa(unittest.TestCase):
    def setUp(self):
        self.mock_pyrpl = MagicMock()
        self.patcher = patch.dict('sys.modules', {'pyrpl': self.mock_pyrpl})
        self.patcher.start()

        from src.pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_sa import DAQ_1DViewer_PyRPL_sa
        self.plugin = DAQ_1DViewer_PyRPL_sa(parent=None, params_state=None)

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        self.assertIsInstance(self.plugin, DAQ_Viewer_base)

    def test_ini_detector(self):
        # Mock the PyRPL spectrum analyzer
        mock_sa = Mock()
        self.mock_pyrpl.spectrumanalyzer = mock_sa
        
        # Mock the dashboard and extension
        mock_dashboard = Mock()
        mock_extension = Mock()
        mock_extension.get_pyrpl_instance.return_value = self.mock_pyrpl
        mock_dashboard.get_extension.return_value = mock_extension
        self.plugin.dashboard = mock_dashboard
        
        # Mock commit_settings method
        self.plugin.commit_settings = Mock()
        
        # Mock the settings structure properly
        with patch.object(self.plugin.settings, 'child') as mock_child:
            mock_child.side_effect = [
                Mock(value=lambda: 'Master'),
                Mock(value=lambda: '192.168.1.100'),
            ]

            self.assertTrue(self.plugin.ini_detector())
            mock_dashboard.get_extension.assert_called_with('PyRPL')
            self.assertEqual(self.plugin.sa, mock_sa)

    def test_grab_data(self):
        self.plugin.sa = Mock()
        self.plugin.sa.curve.return_value = (np.array([1, 2, 3]), None, None, None)
        self.plugin.sa.frequencies = np.array([0, 1, 2])

        self.plugin.dte_signal = Mock()
        self.plugin.grab_data()

        self.plugin.dte_signal.emit.assert_called_once()
        data = self.plugin.dte_signal.emit.call_args[0][0]
        self.assertIsInstance(data, DataFromPlugins)
        self.assertEqual(data.name, 'PyRPL Spectrum Analyzer')
        self.assertEqual(len(data.data), 1)
        np.testing.assert_array_equal(data.data[0], np.array([1, 2, 3]))


if __name__ == '__main__':
    unittest.main()
