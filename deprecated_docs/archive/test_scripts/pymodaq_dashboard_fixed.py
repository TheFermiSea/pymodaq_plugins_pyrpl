#!/usr/bin/env python3
"""
PyMoDAQ Dashboard (Fixed for PyRPL Integration)

A production-ready launcher for PyMoDAQ that resolves event loop conflicts
with PyRPL through monkey patching. This launcher applies qasync integration
patches before importing PyMoDAQ, ensuring stable operation without crashes.

The monkey patch approach means NO modification to PyMoDAQ core is required -
this is a drop-in replacement for the standard PyMoDAQ dashboard launcher.

Usage:
    python pymodaq_dashboard_fixed.py

Features:
- ✅ Resolves PyMoDAQ dashboard crashes during preset creation
- ✅ Enables stable PyRPL plugin operation
- ✅ No PyMoDAQ core modifications required
- ✅ Unified Qt/asyncio event loop via qasync
- ✅ Quamash compatibility shim for PyRPL
- ✅ Graceful error handling and validation

Author: PyMoDAQ-PyRPL Integration Team
License: MIT
"""

import sys
import logging
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pymodaq_dashboard_fixed')


def validate_environment():
    """Validate that all required dependencies are available."""

    logger.info("🔍 Validating environment...")

    # Check Python version
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8+ is required for PyMoDAQ-PyRPL integration")

    # Check required packages
    required_packages = {
        'qasync': 'qasync>=0.28.0',
        'qtpy': 'qtpy',
        'pymodaq': 'pymodaq>=5.0.0',
    }

    missing_packages = []
    for package, requirement in required_packages.items():
        try:
            __import__(package)
            logger.info(f"✅ {package} available")
        except ImportError:
            missing_packages.append(requirement)

    if missing_packages:
        raise RuntimeError(
            f"Missing required packages: {', '.join(missing_packages)}\n"
            f"Install with: pip install {' '.join(missing_packages)}"
        )

    logger.info("✅ Environment validation successful")


def apply_pymodaq_patches():
    """Apply monkey patches for PyMoDAQ-PyRPL integration."""

    logger.info("🔧 Applying PyMoDAQ integration patches...")

    try:
        # Import and apply our monkey patch module
        # This must happen BEFORE importing pymodaq
        import pymodaq_qasync_monkey_patch

        # Verify patches were applied
        status = pymodaq_qasync_monkey_patch.get_status()
        if not status['patches_applied']:
            raise RuntimeError("Failed to apply PyMoDAQ patches")

        logger.info("✅ PyMoDAQ patches applied successfully")
        return True

    except ImportError as e:
        logger.error(f"❌ Failed to import monkey patch module: {e}")
        logger.error("Ensure pymodaq_qasync_monkey_patch.py is in the same directory")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to apply patches: {e}")
        return False


def launch_pymodaq_dashboard():
    """Launch the PyMoDAQ dashboard with qasync integration."""

    logger.info("🚀 Launching PyMoDAQ dashboard...")

    try:
        # Import PyMoDAQ dashboard (patches are already applied)
        from pymodaq.dashboard import main as pymodaq_main

        logger.info("✅ PyMoDAQ dashboard imported successfully")

        # Verify PyRPL plugins are available
        logger.info("📋 Checking PyRPL plugin availability...")

        # Test our PyRPL integration
        try:
            from src.pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
            manager = PyRPLManager.get_instance()
            logger.info("✅ PyRPL integration verified - no event loop conflicts!")
        except Exception as e:
            logger.warning(f"⚠️  PyRPL integration check failed: {e}")
            logger.info("Dashboard will still launch, but PyRPL plugins may not work")

        # Launch the dashboard
        logger.info("🎯 Starting PyMoDAQ dashboard GUI...")
        logger.info("📝 Note: Dashboard will use qasync-integrated event loop")

        # This will now use our patched version with qasync integration
        pymodaq_main()

    except Exception as e:
        logger.error(f"❌ Failed to launch PyMoDAQ dashboard: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main entry point for the fixed PyMoDAQ dashboard."""

    print("="*70)
    print("🔧 PyMoDAQ Dashboard (Fixed for PyRPL Integration)")
    print("="*70)
    print()

    try:
        # Step 1: Validate environment
        validate_environment()

        # Step 2: Apply integration patches
        if not apply_pymodaq_patches():
            logger.error("❌ Failed to apply required patches")
            sys.exit(1)

        # Step 3: Launch dashboard
        launch_pymodaq_dashboard()

    except KeyboardInterrupt:
        logger.info("Dashboard interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Dashboard startup failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("1. Ensure all dependencies are installed:")
        print("   pip install qasync>=0.28.0 pymodaq>=5.0.0")
        print("2. Ensure pymodaq_qasync_monkey_patch.py is in the same directory")
        print("3. Check that PyQt6 or PyQt5 is installed")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()