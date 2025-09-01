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
        self.plugin.settings.child.side_effect = [
            Mock(value=lambda: True),
            Mock(value=lambda: ['frequency', 'amplitude', 'offset']),
            Mock(value=lambda: '192.168.1.100'),
            Mock(value=lambda: 0),
        ]

        self.assertTrue(self.plugin.ini_stage())
        self.mock_pyrpl.Pyrpl.assert_called_with(hostname='192.168.1.100')

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
