#!/usr/bin/env python3
"""
PyMoDAQ qasync Monkey Patch Integration

This module monkey patches PyMoDAQ to use qasync for unified Qt/asyncio event loop
integration without modifying PyMoDAQ core code. It intercepts key functions to
establish qasync before any competing event loops can be created.

Usage:
    import pymodaq_qasync_monkey_patch  # Import BEFORE importing pymodaq
    from pymodaq.dashboard import main as pymodaq_main
    pymodaq_main()

Strategy:
    - Patches PyMoDAQ's mkQApp to set up qasync integration
    - Patches QApplication.exec to use qasync event loop
    - Installs quamash compatibility shim for PyRPL
    - Provides fail-safe guards against competing loops

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import sys
import types
import asyncio
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pymodaq_qasync_patch')

# Track patching state
_PATCHING_APPLIED = False
_QASYNC_LOOP_ACTIVE = False


def install_quamash_shim():
    """Install quamash compatibility shim for PyRPL integration."""

    if 'quamash' in sys.modules:
        logger.info("Quamash already in sys.modules, skipping shim installation")
        return

    try:
        import qasync

        # Create quamash module shim
        quamash = types.ModuleType("quamash")
        quamash.QEventLoop = qasync.QEventLoop

        # qasync 0.28.0 doesn't have QEventLoopPolicy, create a stub
        class QEventLoopPolicyStub:
            """Stub for QEventLoopPolicy compatibility"""
            def __init__(self):
                pass

            def new_event_loop(self):
                return qasync.QEventLoop()

        quamash.QEventLoopPolicy = QEventLoopPolicyStub

        # Add ThreadPoolExecutor alias
        try:
            from concurrent.futures import ThreadPoolExecutor
            quamash.QThreadExecutor = ThreadPoolExecutor
        except ImportError:
            logger.warning("ThreadPoolExecutor not available for quamash shim")

        # Install shim in sys.modules
        sys.modules['quamash'] = quamash

        logger.info("✅ Quamash compatibility shim installed")

    except ImportError as e:
        logger.error(f"❌ Failed to install quamash shim: qasync not available: {e}")
        raise RuntimeError("qasync>=0.28.0 is required for PyRPL integration") from e


def patch_mkQApp():
    """Patch PyMoDAQ's mkQApp to set up qasync integration."""

    try:
        import pymodaq_gui.utils.utils as pymodaq_utils
        import qasync

        # Store original function
        original_mkQApp = pymodaq_utils.mkQApp

        def qasync_mkQApp(name: str):
            """Enhanced mkQApp that sets up qasync integration."""
            global _QASYNC_LOOP_ACTIVE

            logger.info(f"Creating QApplication '{name}' with qasync integration...")

            # Create QApplication using original function
            app = original_mkQApp(name)

            # Set up qasync integration if not already done
            if not _QASYNC_LOOP_ACTIVE and not hasattr(app, '_qasync_integrated'):
                try:
                    # Create qasync event loop
                    loop = qasync.QEventLoop(app)
                    asyncio.set_event_loop(loop)

                    # Mark as integrated
                    app._qasync_integrated = True
                    _QASYNC_LOOP_ACTIVE = True

                    logger.info("✅ qasync event loop integration successful")

                except Exception as e:
                    logger.error(f"❌ Failed to set up qasync loop: {e}")
                    # Continue with standard QApplication - graceful degradation

            return app

        # Apply the patch
        pymodaq_utils.mkQApp = qasync_mkQApp
        logger.info("✅ PyMoDAQ mkQApp patched successfully")

    except ImportError as e:
        logger.error(f"❌ Failed to patch mkQApp: {e}")
        raise


def patch_qapp_exec():
    """Patch QApplication.exec to use qasync event loop."""

    try:
        from qtpy import QtWidgets
        import qasync

        # Store original exec methods
        original_exec = getattr(QtWidgets.QApplication, 'exec', None)
        original_exec_ = getattr(QtWidgets.QApplication, 'exec_', None)

        def qasync_exec(self):
            """Enhanced exec that uses qasync event loop."""
            global _QASYNC_LOOP_ACTIVE

            logger.info("Starting QApplication with qasync event loop...")

            # Check if qasync loop is already set up
            try:
                current_loop = asyncio.get_running_loop()
                if isinstance(current_loop, qasync.QEventLoop):
                    logger.info("qasync loop already running, using run_forever()")
                    current_loop.run_forever()
                    return 0
            except RuntimeError:
                # No running loop, which is expected
                pass

            # Set up qasync loop if not already done
            if not hasattr(self, '_qasync_integrated'):
                try:
                    loop = qasync.QEventLoop(self)
                    asyncio.set_event_loop(loop)
                    self._qasync_integrated = True
                    _QASYNC_LOOP_ACTIVE = True
                    logger.info("✅ qasync loop set up in exec()")
                except Exception as e:
                    logger.error(f"❌ Failed to set up qasync in exec(): {e}")
                    # Fall back to original exec
                    if original_exec:
                        return original_exec(self)
                    elif original_exec_:
                        return original_exec_(self)
                    else:
                        raise RuntimeError("No exec method available")

            # Run the qasync event loop
            try:
                loop = asyncio.get_event_loop()
                if isinstance(loop, qasync.QEventLoop):
                    logger.info("Starting qasync event loop...")
                    with loop:
                        loop.run_forever()
                    return 0
                else:
                    logger.warning("Event loop is not qasync, falling back to original exec")
                    if original_exec:
                        return original_exec(self)
                    elif original_exec_:
                        return original_exec_(self)
            except Exception as e:
                logger.error(f"❌ qasync loop failed: {e}")
                # Fall back to original exec
                if original_exec:
                    return original_exec(self)
                elif original_exec_:
                    return original_exec_(self)
                raise

        # Apply patches
        if original_exec:
            QtWidgets.QApplication.exec = qasync_exec
            logger.info("✅ QApplication.exec patched successfully")
        if original_exec_:
            QtWidgets.QApplication.exec_ = qasync_exec
            logger.info("✅ QApplication.exec_ patched successfully")

    except ImportError as e:
        logger.error(f"❌ Failed to patch QApplication.exec: {e}")
        raise


def validate_environment():
    """Validate that required dependencies are available."""

    logger.info("Validating environment for qasync integration...")

    # Check qasync availability
    try:
        import qasync
        logger.info(f"✅ qasync available, version: {getattr(qasync, '__version__', 'unknown')}")
    except ImportError as e:
        raise RuntimeError(
            "qasync>=0.28.0 is required for PyMoDAQ-PyRPL integration. "
            f"Install with: pip install 'qasync>=0.28.0'. Error: {e}"
        ) from e

    # Check Qt availability
    try:
        from qtpy import QtWidgets
        logger.info("✅ Qt bindings available via qtpy")
    except ImportError as e:
        raise RuntimeError(f"Qt bindings not available: {e}") from e

    # Warn if Qt already imported
    qt_modules = ['PyQt6', 'PyQt5', 'PySide6', 'PySide2']
    early_qt = [m for m in qt_modules if m in sys.modules]
    if early_qt:
        logger.warning(f"⚠️  Qt modules {early_qt} already imported - patching may be less effective")

    logger.info("✅ Environment validation successful")


def apply_patches():
    """Apply all monkey patches for qasync integration."""
    global _PATCHING_APPLIED

    if _PATCHING_APPLIED:
        logger.info("Patches already applied, skipping")
        return

    logger.info("🚀 Applying PyMoDAQ qasync monkey patches...")

    try:
        # Step 1: Validate environment
        validate_environment()

        # Step 2: Install quamash compatibility shim
        install_quamash_shim()

        # Step 3: Patch PyMoDAQ's mkQApp function
        patch_mkQApp()

        # Step 4: Patch QApplication.exec methods
        patch_qapp_exec()

        _PATCHING_APPLIED = True
        logger.info("✅ All patches applied successfully!")
        logger.info("🎉 PyMoDAQ is now ready for PyRPL integration without event loop conflicts!")

    except Exception as e:
        logger.error(f"❌ Failed to apply patches: {e}")
        raise


def is_patched() -> bool:
    """Check if patches have been applied."""
    return _PATCHING_APPLIED


def get_status() -> dict:
    """Get current patching status."""
    return {
        'patches_applied': _PATCHING_APPLIED,
        'qasync_loop_active': _QASYNC_LOOP_ACTIVE,
        'quamash_shim_installed': 'quamash' in sys.modules,
    }


# Auto-apply patches on import
logger.info("PyMoDAQ qasync monkey patch module imported")
apply_patches()


if __name__ == '__main__':
    print("PyMoDAQ qasync Monkey Patch")
    print("Status:", get_status())
    print("\nTo use:")
    print("1. Import this module BEFORE importing pymodaq")
    print("2. Then import and run PyMoDAQ normally")
    print("\nExample:")
    print("    import pymodaq_qasync_monkey_patch")
    print("    from pymodaq.dashboard import main")
    print("    main()")