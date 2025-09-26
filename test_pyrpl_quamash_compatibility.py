#!/usr/bin/env python3
"""
PyRPL Quamash Compatibility Test

Tests that our qasync-based quamash shim is compatible with PyRPL's
expected quamash usage patterns. This validates that PyRPL can import
and use the shim without errors.
"""

import sys
import logging
import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pyrpl_quamash_test')


def test_quamash_shim_installation():
    """Test that we can install the quamash shim correctly"""

    logger.info("🧪 Testing quamash shim installation...")

    try:
        import qasync

        # Create the same shim as our launcher
        quamash = types.ModuleType("quamash")
        quamash.QEventLoop = qasync.QEventLoop

        # qasync 0.28.0 doesn't have QEventLoopPolicy, create a stub
        class QEventLoopPolicyStub:
            """Stub for QEventLoopPolicy compatibility"""
            pass

        quamash.QEventLoopPolicy = QEventLoopPolicyStub

        from concurrent.futures import ThreadPoolExecutor
        quamash.QThreadExecutor = ThreadPoolExecutor

        # Install in sys.modules
        sys.modules['quamash'] = quamash

        logger.info("✅ Quamash shim installed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to install quamash shim: {e}")
        return False


def test_pyrpl_quamash_import():
    """Test that PyRPL can import our quamash shim"""

    logger.info("🧪 Testing PyRPL quamash import...")

    try:
        # This should use our shim
        import quamash

        # Verify expected attributes exist
        assert hasattr(quamash, 'QEventLoop'), "QEventLoop missing from shim"
        assert hasattr(quamash, 'QEventLoopPolicy'), "QEventLoopPolicy missing from shim"

        logger.info("✅ PyRPL can import quamash shim successfully")
        return True

    except Exception as e:
        logger.error(f"❌ PyRPL quamash import failed: {e}")
        return False


def test_pyrpl_async_utils_import():
    """Test that PyRPL async_utils can import and use quamash"""

    logger.info("🧪 Testing PyRPL async_utils import...")

    try:
        # This will trigger PyRPL's quamash usage in async_utils.py lines 20-21
        import pyrpl.async_utils

        logger.info("✅ PyRPL async_utils imported successfully with quamash shim")
        return True

    except Exception as e:
        logger.error(f"❌ PyRPL async_utils import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pyrpl_set_event_loop():
    """Test that PyRPL's set_event_loop call works"""

    logger.info("🧪 Testing PyRPL event loop setup...")

    try:
        # Simulate PyRPL's usage pattern
        import quamash
        from asyncio import set_event_loop

        # This is what PyRPL does in async_utils.py line 21
        set_event_loop(quamash.QEventLoop())

        logger.info("✅ PyRPL event loop setup successful")
        return True

    except Exception as e:
        logger.error(f"❌ PyRPL event loop setup failed: {e}")
        return False


def main():
    """Run all PyRPL quamash compatibility tests"""

    logger.info("🚀 Starting PyRPL quamash compatibility tests...")

    tests = [
        ("Quamash shim installation", test_quamash_shim_installation),
        ("PyRPL quamash import", test_pyrpl_quamash_import),
        ("PyRPL event loop setup", test_pyrpl_set_event_loop),
        ("PyRPL async_utils import", test_pyrpl_async_utils_import),
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
    logger.info("PYRPL QUAMASH COMPATIBILITY RESULTS:")
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
        logger.info("🎉 PyRPL is fully compatible with our qasync-based quamash shim!")
    else:
        logger.info("⚠️  Some compatibility issues found - may need additional shim features")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)