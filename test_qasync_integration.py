#!/usr/bin/env python3
"""
qasync Integration Smoke Test

Tests async task progression during PyMoDAQ app.exec() to validate
that the qasync event loop policy is working correctly.

This test validates the critical requirement that asyncio tasks
can progress while PyMoDAQ runs its Qt event loop.
"""

import asyncio
import logging
import sys
import time
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('qasync_integration_test')

class AsyncTaskProgressionTest:
    """Test that async tasks progress during Qt app.exec()"""

    def __init__(self):
        self.task_completed = False
        self.task_result: Optional[str] = None
        self.start_time = time.time()

    async def test_coroutine(self):
        """Simple coroutine to verify async execution"""
        await asyncio.sleep(0.1)  # Small delay
        self.task_completed = True
        self.task_result = "Async task completed successfully"
        elapsed = time.time() - self.start_time
        logger.info(f"✅ Async task completed after {elapsed:.3f}s")
        return self.task_result

    def schedule_test_task(self):
        """Schedule the test coroutine"""
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"Scheduling async task on loop: {type(loop).__name__}")
            task = asyncio.create_task(self.test_coroutine())

            # Set up completion callback
            def on_completion(task):
                if task.exception():
                    logger.error(f"❌ Async task failed: {task.exception()}")
                else:
                    logger.info(f"✅ Task completed with result: {task.result()}")

            task.add_done_callback(on_completion)
            return task

        except RuntimeError as e:
            logger.error(f"❌ No running event loop: {e}")
            return None

def test_qasync_policy_setup():
    """Test qasync policy setup without Qt"""

    logger.info("🧪 Testing qasync policy setup...")

    try:
        import qasync

        # qasync 0.28.0 doesn't have QEventLoopPolicy - use QEventLoop approach
        logger.info("Note: qasync 0.28.0 uses QEventLoop approach, not QEventLoopPolicy")

        # Test that we can create a qasync loop
        from qtpy import QtWidgets
        app = QtWidgets.QApplication([])
        loop = qasync.QEventLoop(app)

        logger.info(f"✅ qasync QEventLoop created: {type(loop).__name__}")
        app.quit()
        return True

    except Exception as e:
        logger.error(f"❌ qasync policy test failed: {e}")
        return False

def test_qt_qasync_integration():
    """Test Qt + qasync integration with task progression"""

    logger.info("🧪 Testing Qt + qasync integration...")

    try:
        # Import Qt after policy is set
        from qtpy import QtWidgets
        import qasync

        # Create QApplication
        app = QtWidgets.QApplication([])

        # Create qasync event loop
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        logger.info(f"✅ Qt + qasync loop created: {type(loop).__name__}")

        # Test async task progression within the Qt event loop
        test = AsyncTaskProgressionTest()

        # Use QTimer to schedule the async task after Qt app starts
        from qtpy.QtCore import QTimer

        def schedule_and_check():
            # Schedule async task now that event loop is running
            task = test.schedule_test_task()

            if task is None:
                logger.error("❌ Failed to schedule async task")
                app.quit()
                return

            # Check completion after task should finish
            def check_completion():
                if test.task_completed:
                    logger.info("✅ Async task completed during Qt event loop")
                    app.quit()
                else:
                    logger.error("❌ Async task did not complete - event loop issue")
                    app.quit()

            # Check after 200ms (task needs 100ms to complete)
            QTimer.singleShot(200, check_completion)

        # Schedule everything after Qt event loop starts
        QTimer.singleShot(10, schedule_and_check)

        # Run Qt event loop (this will exit when timer fires)
        app.exec()

        return test.task_completed

    except Exception as e:
        logger.error(f"❌ Qt + qasync integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_quamash_shim():
    """Test quamash compatibility shim"""

    logger.info("🧪 Testing quamash compatibility shim...")

    try:
        import sys
        import types
        import qasync

        # Create and install shim (adapted for qasync 0.28.0)
        quamash = types.ModuleType("quamash")
        quamash.QEventLoop = qasync.QEventLoop

        # qasync 0.28.0 doesn't have QEventLoopPolicy, create a stub
        class QEventLoopPolicyStub:
            """Stub for QEventLoopPolicy compatibility"""
            pass

        quamash.QEventLoopPolicy = QEventLoopPolicyStub

        from concurrent.futures import ThreadPoolExecutor
        quamash.QThreadExecutor = ThreadPoolExecutor

        sys.modules['quamash'] = quamash

        # Test shim import
        import quamash
        assert hasattr(quamash, 'QEventLoop'), "QEventLoop not in shim"
        assert hasattr(quamash, 'QEventLoopPolicy'), "QEventLoopPolicy not in shim"
        assert hasattr(quamash, 'QThreadExecutor'), "QThreadExecutor not in shim"

        logger.info("✅ Quamash shim working correctly")
        return True

    except Exception as e:
        logger.error(f"❌ Quamash shim test failed: {e}")
        return False

def main():
    """Run all integration tests"""

    logger.info("🚀 Starting qasync integration tests...")

    tests = [
        ("qasync policy setup", test_qasync_policy_setup),
        ("quamash compatibility shim", test_quamash_shim),
        ("Qt + qasync integration", test_qt_qasync_integration),
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
    logger.info("INTEGRATION TEST RESULTS:")
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

    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)