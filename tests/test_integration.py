# -*- coding: utf-8 -*-
"""
Integration tests for the PyMoDAQ PyRPL plugin.

This module tests the integration of the PyRPL plugins with the PyMoDAQ
dashboard and other extensions.

Author: Claude Code
License: MIT
"""

import pytest
from pymodaq.dashboard import DashBoard
from qtpy import QtWidgets
import sys
import os
from pathlib import Path
from pymodaq.utils.gui_utils import DockArea

@pytest.fixture
def app(qtbot):
    """Create a QApplication instance."""
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication(sys.argv)
    yield qapp

@pytest.fixture
def preset_file_path():
    """Create a preset file for the test and return its path."""
    preset_content = """
<preset>
    <detectors>
        <det00>
            <name>PyRPL_Scope</name>
            <init>False</init>
            <params>
                <main_settings>
                    <DAQ_type type="list">DAQ1D</DAQ_type>
                    <detector_type type="list">PyRPL_Scope</detector_type>
                </main_settings>
                <detector_settings>
                    <connection>
                        <mock_mode type="bool">True</mock_mode>
                    </connection>
                </detector_settings>
            </params>
        </det00>
    </detectors>
    <actuators>
        <move00>
            <name>PyRPL_PID</name>
            <init>False</init>
            <params>
                <main_settings>
                    <move_type type="list">PyRPL_PID</move_type>
                </main_settings>
                <move_settings>
                    <connection_settings>
                        <mock_mode type="bool">True</mock_mode>
                    </connection_settings>
                </move_settings>
            </params>
        </move00>
        <move01>
            <name>PyRPL_ASG</name>
            <init>False</init>
            <params>
                <main_settings>
                    <move_type type="list">PyRPL_ASG</move_type>
                </main_settings>
                <move_settings>
                    <connection_settings>
                        <mock_mode type="bool">True</mock_mode>
                    </connection_settings>
                </move_settings>
            </params>
        </move01>
    </actuators>
</preset>
"""
    preset_path = Path("tests/test_preset.xml").absolute()
    with open(preset_path, "w") as f:
        f.write(preset_content)
    yield preset_path
    os.remove(preset_path)


@pytest.mark.integration
def test_dashboard_loading(app, qtbot, preset_file_path):
    """Test if the plugins can be loaded into the dashboard."""
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    dashboard = DashBoard(area)
    win.show()
    qtbot.addWidget(win)

    dashboard.set_preset_mode(preset_file_path)

    assert len(dashboard.detector_modules) == 1
    assert len(dashboard.actuators_modules) == 2
    assert dashboard.detector_modules[0].title == "PyRPL_Scope"
    assert dashboard.actuators_modules[0].title == "PyRPL_PID"
    assert dashboard.actuators_modules[1].title == "PyRPL_ASG"

    win.close()
