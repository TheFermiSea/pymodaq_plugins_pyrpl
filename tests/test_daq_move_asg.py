import unittest
from unittest.mock import Mock, patch, MagicMock

import numpy as np
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

class TestDAQ_Move_PyRPL_asg(unittest.TestCase):
    def setUp(self):
        self.mock_pyrpl = MagicMock()
        self.patcher = patch.dict('sys.modules', {'pyrpl': self.mock_pyrpl})
        self.patcher.start()

        from src.pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_asg import DAQ_Move_PyRPL_asg
        self.plugin = DAQ_Move_PyRPL_asg(parent=None, params_state=None)

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        self.assertIsInstance(self.plugin, DAQ_Move_base)

    def test_ini_stage(self):
        # Mock the PyRPL instance structure
        mock_asg = Mock()
        self.mock_pyrpl.rp.asgs.pop.return_value = mock_asg
        
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
                Mock(value=lambda: True),
                Mock(value=lambda: ['frequency', 'amplitude', 'offset']),
                Mock(value=lambda: 0),
            ]

            self.assertTrue(self.plugin.ini_stage())
            mock_dashboard.get_extension.assert_called_with('PyRPL')
            self.assertEqual(self.plugin.asg, mock_asg)

    def test_move_abs(self):
        self.plugin.asg = Mock()
        self.plugin.emit_status = Mock()

        self.plugin.move_abs([1e6, 0.5, 0.1])

        self.plugin.emit_status.assert_called_once()
        self.assertEqual(self.plugin.asg.frequency, 1e6)
        self.assertEqual(self.plugin.asg.amplitude, 0.5)
        self.assertEqual(self.plugin.asg.offset, 0.1)


if __name__ == '__main__':
    unittest.main()
