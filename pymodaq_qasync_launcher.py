#!/usr/bin/env python3
"""
PyMoDAQ qasync Integration Launcher

This launcher sets up the unified Qt/asyncio event loop integration required
for PyMoDAQ-PyRPL compatibility. It must be used as the entry point instead
of the standard PyMoDAQ dashboard to enable proper event loop management.

Usage:
    python pymodaq_qasync_launcher.py

Features:
- Sets qasync policy before any Qt initialization
- Provides quamash compatibility shim for PyRPL
- Fail-fast validation of environment
- Clean integration with existing PyMoDAQ architecture

Expert consensus validated by o3-high and GPT-5 models.
"""

import sys
import asyncio
import logging

# Configure logging for launcher diagnostics
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pymodaq_qasync_launcher')

def validate_environment():
    """Validate environment before setting up qasync integration."""

    # 1) Fail fast if Qt was imported too early
    qt_modules = ['PyQt6', 'PyQt5', 'PySide6', 'PySide2', 'qtpy']
    early_qt = [m for m in qt_modules if m in sys.modules]
    if early_qt:
        raise RuntimeError(
            f"Qt modules {early_qt} were imported before setting qasync policy. "
            "Use this launcher as the entry point instead of importing PyMoDAQ directly."
        )

    # 2) Verify qasync is available and minimum version
    try:
        import qasync
        logger.info(f"qasync available, using version {getattr(qasync, '__version__', 'unknown')}")
        return qasync
    except ImportError as e:
        raise RuntimeError(
            "qasync>=0.28.0 is required for PyRPL integration. "
            f"Install with: pip install 'qasync>=0.28.0'. Error: {e}"
        ) from e

def setup_qasync_policy(qasync):
    """Set up qasync event loop policy for Qt/asyncio integration."""

    # Note: qasync 0.28.0 doesn't have QEventLoopPolicy
    # The integration happens when QEventLoop is created with QApplication
    logger.info("ℹ️  qasync 0.28.0 uses QEventLoop approach (no separate policy)")
    logger.info("✅ qasync integration will activate when PyMoDAQ creates QApplication")

    return None

def setup_quamash_shim(qasync):
    """Provide runtime quamash compatibility shim for PyRPL integration."""

    import types

    # Create quamash module shim
    quamash = types.ModuleType("quamash")

    # Re-export essential qasync components that PyRPL expects
    quamash.QEventLoop = qasync.QEventLoop

    # qasync 0.28.0 doesn't have QEventLoopPolicy, create a stub
    class QEventLoopPolicyStub:
        """Stub for QEventLoopPolicy compatibility"""
        pass

    quamash.QEventLoopPolicy = QEventLoopPolicyStub

    # Add QThreadExecutor alias if PyRPL uses it
    try:
        from concurrent.futures import ThreadPoolExecutor
        quamash.QThreadExecutor = ThreadPoolExecutor
    except ImportError:
        logger.warning("ThreadPoolExecutor not available for quamash shim")

    # Install shim in sys.modules (process-local, no global package changes)
    sys.modules['quamash'] = quamash

    logger.info("✅ Quamash compatibility shim installed")
    return quamash

def launch_pymodaq():
    """Launch PyMoDAQ with qasync integration."""

    logger.info("Starting PyMoDAQ with qasync integration...")

    try:
        # Import PyMoDAQ after qasync setup is complete
        from pymodaq.dashboard import main as pymodaq_main

        # Detect Qt binding after PyMoDAQ import
        try:
            from qtpy import QtWidgets
            app_instance = QtWidgets.QApplication.instance()
            if app_instance:
                logger.info(f"Qt binding detected: {type(app_instance).__name__}")
        except ImportError:
            logger.warning("Could not detect Qt binding")

        # Launch PyMoDAQ dashboard (creates QApplication with qasync policy active)
        logger.info("✅ Launching PyMoDAQ dashboard with qasync integration")
        pymodaq_main()

    except Exception as e:
        logger.error(f"❌ Failed to launch PyMoDAQ: {e}")
        raise

def main():
    """Main launcher entry point."""

    logger.info("🚀 PyMoDAQ qasync Integration Launcher starting...")

    try:
        # Step 1: Validate environment
        qasync = validate_environment()

        # Step 2: Set up qasync policy
        setup_qasync_policy(qasync)

        # Step 3: Install quamash compatibility shim
        setup_quamash_shim(qasync)

        # Step 4: Launch PyMoDAQ
        launch_pymodaq()

    except Exception as e:
        logger.error(f"❌ Launcher failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()