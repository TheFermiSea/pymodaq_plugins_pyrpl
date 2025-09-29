"""Lightweight PyQt4 compatibility shim backed by qtpy bindings."""

from __future__ import annotations

import sys
from types import ModuleType

from qtpy import QtCore as _QtCore
from qtpy import QtGui as _QtGui
from qtpy import QtWidgets as _QtWidgets

__all__ = ["QtCore", "QtGui", "QtWidgets"]


def _clone_module(source: ModuleType, name: str) -> ModuleType:
    clone = ModuleType(name)
    clone.__dict__.update(source.__dict__)
    return clone


QtCore = _clone_module(_QtCore, "PyQt4.QtCore")
QtGui = _clone_module(_QtGui, "PyQt4.QtGui")
QtWidgets = _clone_module(_QtWidgets, "PyQt4.QtWidgets")

# Provide legacy QApplication access on QtGui
QtGui.QApplication = QtWidgets.QApplication  # type: ignore[attr-defined]

try:
    _original_set_interval = QtCore.QTimer.setInterval

    def _set_interval_compat(timer, msec):  # type: ignore[override]
        try:
            return _original_set_interval(timer, int(msec))
        except (TypeError, ValueError):
            return _original_set_interval(timer, 1000)

    QtCore.QTimer.setInterval = _set_interval_compat  # type: ignore[assignment]
except AttributeError:
    pass

_MODULE_PREFIX = __name__ + "."
sys.modules.setdefault(_MODULE_PREFIX + "QtCore", QtCore)
sys.modules.setdefault(_MODULE_PREFIX + "QtGui", QtGui)
sys.modules.setdefault(_MODULE_PREFIX + "QtWidgets", QtWidgets)

_IS_SHIM = True
