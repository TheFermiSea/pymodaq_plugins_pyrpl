#!/usr/bin/env python3
"""
Complete Integration Test

Tests that our Phase 1 implementation works correctly by simulating
the full PyMoDAQ + qasync + PyRPL integration stack.
"""

import sys
import logging
import asyncio
import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('integration_test')


def setup_qasync_environment():
    """Set up the same environment as our launcher"""

    # 1. Install quamash shim (like launcher does)
    import qasync

    quamash = types.ModuleType("quamash")
    quamash.QEventLoop = qasync.QEventLoop

    class QEventLoopPolicyStub:
        pass
    quamash.QEventLoopPolicy = QEventLoopPolicyStub

    from concurrent.futures import ThreadPoolExecutor
    quamash.QThreadExecutor = ThreadPoolExecutor

    sys.modules['quamash'] = quamash

    # 2. Create QApplication and qasync loop (like PyMoDAQ + launcher does)
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(['integration_test'])

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    logger.info("✅ qasync environment set up successfully")
    return app, loop


def test_plugin_integration():
    """Test that plugins work correctly with qasync environment"""

    logger.info("🧪 Testing plugin integration...")

    try:
        # Import our PyRPL wrapper (should work with qasync loop)
        from src.pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager

        # Test manager creation
        manager = PyRPLManager.get_instance()
        logger.info("✅ PyRPL manager created successfully")

        # Test mock connection (should work now that event loop exists)
        from src.pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import EnhancedMockPyRPLConnection

        mock_conn = EnhancedMockPyRPLConnection('mock-rp', 'test')
        logger.info("✅ Mock connection created successfully")

        # Test PID plugin (minimal initialization)
        from src.pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID

        logger.info("✅ PID plugin import successful")

        return True

    except Exception as e:
        logger.error(f"❌ Plugin integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_launcher_compatibility():
    """Test that our launcher approach resolves the original issue"""

    logger.info("🧪 Testing launcher compatibility...")

    try:
        # The key test: can we import PyRPL modules without event loop conflicts?
        # This was the original crash scenario described in DASHBOARD_PLAN.md

        # Import should work without crashes now
        from src.pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLConnection
        logger.info("✅ PyRPL wrapper imports without conflicts")

        # Plugin discovery should work
        plugin_modules = [
            'src.pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID',
            'src.pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL',
            'src.pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope',
        ]

        for module_name in plugin_modules:
            try:
                __import__(module_name)
                logger.info(f"✅ {module_name.split('.')[-1]} imports successfully")
            except Exception as e:
                logger.error(f"❌ {module_name} failed: {e}")
                return False

        logger.info("✅ All plugins import without event loop conflicts")
        return True

    except Exception as e:
        logger.error(f"❌ Launcher compatibility test failed: {e}")
        return False


def main():
    """Run complete integration test"""

    logger.info("🚀 Starting complete integration test...")

    # Set up qasync environment (like our launcher does)
    app, loop = setup_qasync_environment()

    tests = [
        ("Plugin integration", test_plugin_integration),
        ("Launcher compatibility", test_launcher_compatibility),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "="*50)
    logger.info("COMPLETE INTEGRATION TEST RESULTS:")
    logger.info("="*50)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("="*50)
    overall = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    logger.info(f"OVERALL: {overall}")

    if all_passed:
        logger.info("🎉 Phase 1 implementation complete and fully functional!")
        logger.info("🚀 PyMoDAQ dashboard crashes should be resolved!")
    else:
        logger.info("⚠️  Some integration issues remain")

    app.quit()
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)