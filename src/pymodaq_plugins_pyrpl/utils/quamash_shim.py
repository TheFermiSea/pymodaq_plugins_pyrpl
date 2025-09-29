"""Minimal quamash compatibility shim backed by qasync.

This module installs a PyQt6-friendly replacement for the legacy
``quamash`` package that ships with PyRPL.  The shim exposes the limited
API surface that PyRPL relies on while delegating the actual event loop
implementation to ``qasync``.
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Optional

_SHIM_FLAG = "_pymodaq_pyrpl_quamash_shim"


def ensure_quamash_shim(logger: Optional[logging.Logger] = None):
    """Install (or return) the qasync-backed quamash shim module."""

    existing = sys.modules.get("quamash")
    if existing and getattr(existing, _SHIM_FLAG, False):
        return existing

    try:
        import qasync
        from qtpy import QtWidgets
    except ImportError as exc:  # pragma: no cover - dependent on optional deps
        if logger:
            logger.error("qasync and qtpy are required for PyRPL integration: %s", exc)
        return None

    original_quamash = existing
    module = types.ModuleType("quamash")
    module.__dict__["__all__"] = ["QEventLoop", "QEventLoopPolicy", "QThreadExecutor"]
    module.__dict__["_original_quamash"] = original_quamash
    module.__dict__[_SHIM_FLAG] = True

    class QEventLoop(qasync.QEventLoop):  # type: ignore[misc]
        def __init__(self, app=None):
            qt_app = app
            if qt_app is None:
                qt_app = QtWidgets.QApplication.instance()
            if qt_app is None:
                qt_app = QtWidgets.QApplication(["pymodaq-pyrpl"])
            super().__init__(qt_app)

    class QEventLoopPolicy:
        def new_event_loop(self):
            qt_app = QtWidgets.QApplication.instance()
            if qt_app is None:
                qt_app = QtWidgets.QApplication(["pymodaq-pyrpl"])
            return QEventLoop(qt_app)

    try:
        from concurrent.futures import ThreadPoolExecutor as QThreadExecutor
    except ImportError:  # pragma: no cover - stdlib always available
        QThreadExecutor = None  # type: ignore[assignment]

    module.QEventLoop = QEventLoop
    module.QEventLoopPolicy = QEventLoopPolicy
    module.QThreadExecutor = QThreadExecutor

    if original_quamash is not None:
        def __getattr__(name: str):
            return getattr(original_quamash, name)

        module.__getattr__ = __getattr__  # type: ignore[attr-defined]

    sys.modules["quamash"] = module
    return module


__all__ = ["ensure_quamash_shim"]
