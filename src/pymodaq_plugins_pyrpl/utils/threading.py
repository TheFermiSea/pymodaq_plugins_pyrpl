# -*- coding: utf-8 -*-
"""Threading helpers that respect PyMoDAQ's Qt event loop precedence."""

from __future__ import annotations

import functools
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from qtpy import QtCore

from pymodaq_utils.utils import ThreadCommand

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Status of threaded operations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class ThreadedOperation:
    """Container describing a queued hardware operation."""

    operation_id: str
    function: Callable
    args: tuple
    kwargs: dict
    timeout: float
    name: str
    status: OperationStatus = OperationStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    completion_event: threading.Event = field(
        default_factory=threading.Event, repr=False, compare=False
    )

    @property
    def duration(self) -> Optional[float]:
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time


class ThreadSafeQueue:
    """Thread-safe queue with priority support for hardware commands."""

    def __init__(self, maxsize: int = 0):
        self._queue = queue.PriorityQueue(maxsize=maxsize)
        self._counter = 0
        self._lock = threading.Lock()

    def put(
        self, item: Any, *, priority: int = 0, timeout: Optional[float] = None
    ) -> bool:
        with self._lock:
            counter = self._counter
            self._counter += 1

        try:
            self._queue.put((priority, counter, item), timeout=timeout)
            return True
        except queue.Full:
            logger.warning("ThreadSafeQueue is full; dropping item")
            return False

    def get(self, timeout: Optional[float] = None) -> Any:
        priority, counter, item = self._queue.get(timeout=timeout)
        return item

    def empty(self) -> bool:
        return self._queue.empty()

    def qsize(self) -> int:
        return self._queue.qsize()


class _OperationWorker(QtCore.QObject):
    """Worker executed in a dedicated QThread to run hardware operations."""

    finished = QtCore.Signal(str, object, object)  # operation_id, result, error

    def __init__(self, operation_id: str, function: Callable, args: tuple, kwargs: dict):
        super().__init__()
        self._operation_id = operation_id
        self._function = function
        self._args = args
        self._kwargs = kwargs

    @QtCore.Slot()
    def run(self) -> None:
        thread = QtCore.QThread.currentThread()
        try:
            if thread.isInterruptionRequested():
                raise InterruptedError("Operation interrupted before execution")

            result = self._function(*self._args, **self._kwargs)

            if thread.isInterruptionRequested():
                raise InterruptedError("Operation interrupted after execution")

            self.finished.emit(self._operation_id, result, None)
        except Exception as exc:  # noqa: BLE001 - propagate to manager
            self.finished.emit(self._operation_id, None, exc)


class ThreadedHardwareManager(QtCore.QObject):
    """Runs hardware operations in Qt-managed threads to avoid event-loop conflicts."""

    def __init__(self, max_workers: int = 4, status_callback: Optional[Callable] = None):
        super().__init__()
        self.max_workers = max(1, max_workers)
        self.status_callback = status_callback

        self._operations: Dict[str, ThreadedOperation] = {}
        self._operation_counter = 0
        self._threads: Dict[str, QtCore.QThread] = {}
        self._workers: Dict[str, _OperationWorker] = {}
        self._pending: List[Tuple[str, Callable, tuple, dict]] = []
        self._lock = threading.Lock()

        logger.info(
            "ThreadedHardwareManager initialized with Qt threads (%d max)",
            self.max_workers,
        )

    def _emit_status(self, message: str, level: str = "log") -> None:
        if self.status_callback is None:
            return
        try:
            self.status_callback(ThreadCommand("Update_Status", [message, level]))
        except Exception as exc:  # noqa: BLE001 - best effort
            logger.error("Error emitting status callback: %s", exc)

    def _next_operation_id(self) -> str:
        with self._lock:
            self._operation_counter += 1
            return f"op_{self._operation_counter:06d}"

    def submit_operation(
        self,
        *,
        function: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        timeout: float = 30.0,
        operation_name: Optional[str] = None,
    ) -> str:
        if kwargs is None:
            kwargs = {}

        operation_id = self._next_operation_id()
        operation = ThreadedOperation(
            operation_id=operation_id,
            function=function,
            args=args,
            kwargs=kwargs,
            timeout=timeout,
            name=operation_name or function.__name__,
        )

        with self._lock:
            self._operations[operation_id] = operation
            should_queue = len(self._threads) >= self.max_workers
            if should_queue:
                self._pending.append((operation_id, function, args, kwargs))

        if should_queue:
            self._emit_status(
                f"Queued threaded operation: {operation.name} ({operation_id})"
            )
            logger.debug("Queued operation %s due to worker limit", operation_id)
            return operation_id

        self._start_operation_thread(operation_id, function, args, kwargs)
        return operation_id

    def _start_operation_thread(
        self, operation_id: str, function: Callable, args: tuple, kwargs: dict
    ) -> None:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return
            operation.status = OperationStatus.RUNNING
            operation.start_time = time.time()

        worker = _OperationWorker(operation_id, function, args, kwargs)
        thread = QtCore.QThread()
        thread.setObjectName(f"PyRPL-HW-{operation_id}")

        worker.moveToThread(thread)
        thread.started.connect(worker.run, QtCore.Qt.QueuedConnection)
        worker.finished.connect(self._handle_operation_finished, QtCore.Qt.QueuedConnection)
        worker.finished.connect(worker.deleteLater, QtCore.Qt.QueuedConnection)
        thread.finished.connect(thread.deleteLater, QtCore.Qt.QueuedConnection)

        with self._lock:
            self._threads[operation_id] = thread
            self._workers[operation_id] = worker

        self._emit_status(
            f"Started threaded operation: {operation.name} ({operation.operation_id})"
        )
        logger.debug("Starting QThread for operation %s", operation_id)
        thread.start()

    @QtCore.Slot(str, object, object)
    def _handle_operation_finished(
        self, operation_id: str, result: Any, error: Optional[Exception]
    ) -> None:
        with self._lock:
            operation = self._operations.get(operation_id)
            thread = self._threads.pop(operation_id, None)
            self._workers.pop(operation_id, None)

        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            thread.quit()

        if operation is None:
            return

        operation.end_time = time.time()

        if error is None:
            operation.result = result
            operation.status = OperationStatus.COMPLETED
            self._emit_status(
                f"Operation {operation.name} ({operation.operation_id}) completed in "
                f"{operation.duration:.3f}s"
            )
        elif isinstance(error, InterruptedError):
            operation.error = None
            operation.status = OperationStatus.CANCELLED
            self._emit_status(
                f"Operation {operation.name} ({operation.operation_id}) cancelled"
            )
        else:
            operation.error = error
            operation.status = OperationStatus.FAILED
            self._emit_status(
                f"Operation {operation.name} ({operation.operation_id}) failed: {error}"
            )
            logger.error(
                "Threaded operation %s failed", operation.operation_id, exc_info=error
            )

        operation.completion_event.set()
        self._start_next_pending_operation()

    def _start_next_pending_operation(self) -> None:
        with self._lock:
            if not self._pending or len(self._threads) >= self.max_workers:
                return
            operation_id, function, args, kwargs = self._pending.pop(0)
        self._start_operation_thread(operation_id, function, args, kwargs)

    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        operation = self._operations.get(operation_id)
        if operation is None:
            return None
        return operation.status

    def get_operation_result(
        self, operation_id: str, timeout: Optional[float] = None
    ) -> Any:
        operation = self._operations.get(operation_id)
        if operation is None:
            raise KeyError(f"Operation {operation_id} not found")

        if operation.status in {OperationStatus.PENDING, OperationStatus.RUNNING}:
            wait_timeout = timeout if timeout is not None else operation.timeout
            success = operation.completion_event.wait(wait_timeout)
            if not success:
                raise TimeoutError(f"Timeout waiting for operation {operation_id}")

        if operation.status is OperationStatus.COMPLETED:
            return operation.result
        if operation.status is OperationStatus.CANCELLED:
            raise RuntimeError(f"Operation {operation_id} was cancelled")
        if operation.status is OperationStatus.FAILED and operation.error is not None:
            raise operation.error

        raise RuntimeError(
            f"Operation {operation_id} ended in unexpected state {operation.status}"
        )

    def wait_for_operation(
        self, operation_id: str, timeout: Optional[float] = None
    ) -> bool:
        try:
            self.get_operation_result(operation_id, timeout)
            return True
        except Exception:  # noqa: BLE001 - callers only need boolean
            return False

    def cancel_operation(self, operation_id: str) -> bool:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return False

            if operation.status is OperationStatus.PENDING:
                for index, pending in enumerate(list(self._pending)):
                    if pending[0] == operation_id:
                        self._pending.pop(index)
                        break
                operation.status = OperationStatus.CANCELLED
                operation.end_time = time.time()
                operation.completion_event.set()
                self._emit_status(
                    f"Operation {operation.name} ({operation.operation_id}) cancelled"
                )
                return True

            thread = self._threads.get(operation_id)
            if thread is None or not thread.isRunning():
                return False

            thread.requestInterruption()

        self._emit_status(
            f"Cancellation requested for {operation.name} ({operation.operation_id})"
        )
        return True

    def list_operations(self) -> List[Dict[str, Any]]:
        summary: List[Dict[str, Any]] = []
        with self._lock:
            for operation in self._operations.values():
                summary.append(
                    {
                        "id": operation.operation_id,
                        "name": operation.name,
                        "status": operation.status.value,
                        "duration": operation.duration,
                        "error": str(operation.error) if operation.error else None,
                    }
                )
        return summary

    def cleanup_completed_operations(self, max_age_seconds: float = 300) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            for operation_id in list(self._operations.keys()):
                operation = self._operations[operation_id]
                if (
                    operation.status in {OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED}
                    and operation.end_time is not None
                    and (now - operation.end_time) > max_age_seconds
                ):
                    removed += 1
                    self._operations.pop(operation_id)
        if removed:
            logger.debug("Cleaned up %d completed operations", removed)
        return removed

    def shutdown(self, timeout: float = 30.0) -> None:
        logger.info("Shutting down ThreadedHardwareManager")

        with self._lock:
            threads = list(self._threads.items())

        for operation_id, thread in threads:
            if thread is None:
                continue
            thread.requestInterruption()
            thread.quit()
            if not thread.wait(int(timeout * 1000)):
                logger.warning(
                    "Thread %s did not terminate cleanly during shutdown", operation_id
                )

        with self._lock:
            for operation in self._operations.values():
                if operation.status in {OperationStatus.PENDING, OperationStatus.RUNNING}:
                    operation.status = OperationStatus.CANCELLED
                    operation.end_time = time.time()
                    operation.completion_event.set()

        self._threads.clear()
        self._workers.clear()
        self._pending.clear()
        self._emit_status("Threaded hardware manager shut down")


class _AcquisitionWorker(QtCore.QObject):
    """Worker that polls hardware from a Qt-managed thread."""

    data_ready = QtCore.Signal(object)
    error = QtCore.Signal(object)
    status = QtCore.Signal(str, str)

    def __init__(self, acquisition_function: Callable, interval: float):
        super().__init__()
        self._acquisition_function = acquisition_function
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.PreciseTimer)
        self._timer.timeout.connect(self._poll_once, QtCore.Qt.QueuedConnection)
        self.set_interval(interval)

    @QtCore.Slot(float)
    def set_interval(self, interval: float) -> None:
        self._interval_ms = max(1, int(max(interval, 0.001) * 1000))
        if self._timer.isActive():
            self._timer.start(self._interval_ms)

    @QtCore.Slot()
    def start(self) -> None:
        if self._timer.isActive():
            return
        self.status.emit("Started continuous data acquisition", "log")
        self._timer.start(self._interval_ms)

    @QtCore.Slot()
    def stop(self) -> None:
        if not self._timer.isActive():
            return
        self._timer.stop()
        self.status.emit("Stopped continuous data acquisition", "log")

    @QtCore.Slot()
    def _poll_once(self) -> None:
        thread = QtCore.QThread.currentThread()
        if thread.isInterruptionRequested():
            self.stop()
            return
        try:
            data = self._acquisition_function()
            if data is not None:
                self.data_ready.emit(data)
        except Exception as exc:  # noqa: BLE001 - forward to callbacks
            self.error.emit(exc)


class AsyncDataAcquisition:
    """Continuous acquisition helper built on Qt threads and timers."""

    def __init__(
        self,
        *,
        acquisition_function: Callable,
        data_callback: Callable,
        status_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
    ) -> None:
        self.acquisition_function = acquisition_function
        self.data_callback = data_callback
        self.status_callback = status_callback
        self.error_callback = error_callback

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[_AcquisitionWorker] = None
        self._running = False

    def start(self, interval: float = 0.1) -> bool:
        if self._running:
            logger.warning("AsyncDataAcquisition already running")
            return False

        self._thread = QtCore.QThread()
        self._thread.setObjectName("PyRPL-Acquisition")
        self._worker = _AcquisitionWorker(self.acquisition_function, interval)
        self._worker.moveToThread(self._thread)

        self._worker.data_ready.connect(self._handle_data, QtCore.Qt.QueuedConnection)
        self._worker.error.connect(self._handle_error, QtCore.Qt.QueuedConnection)
        self._worker.status.connect(self._handle_status, QtCore.Qt.QueuedConnection)

        self._thread.started.connect(self._worker.start, QtCore.Qt.QueuedConnection)
        self._thread.finished.connect(self._thread.deleteLater, QtCore.Qt.QueuedConnection)
        self._thread.finished.connect(self._cleanup_worker, QtCore.Qt.QueuedConnection)

        self._thread.start()
        self._running = True
        logger.info("Started async data acquisition using Qt QThread")
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        if not self._running:
            return True

        if self._worker is not None:
            QtCore.QMetaObject.invokeMethod(
                self._worker, "stop", QtCore.Qt.QueuedConnection
            )

        if self._thread is not None:
            self._thread.requestInterruption()
            self._thread.quit()
            finished = self._thread.wait(int(timeout * 1000))
            if not finished:
                logger.warning("Acquisition thread did not stop within timeout")
                return False

        self._cleanup_worker()
        self._running = False
        return True

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._thread = None

    def _handle_data(self, data: Any) -> None:
        try:
            self.data_callback(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in data callback: %s", exc, exc_info=True)

    def _handle_error(self, error: Exception) -> None:
        logger.error("Error during async acquisition: %s", error, exc_info=True)
        if self.error_callback is not None:
            try:
                self.error_callback(error)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error in acquisition error callback: %s", exc)

    def _handle_status(self, message: str, level: str) -> None:
        if self.status_callback is None:
            return
        try:
            self.status_callback(ThreadCommand("Update_Status", [message, level]))
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in acquisition status callback: %s", exc)

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.isRunning()


def threaded_hardware_operation(
    *, timeout: float = 30.0, manager: Optional[ThreadedHardwareManager] = None
) -> Callable:
    """Decorator that executes the wrapped function via :class:`ThreadedHardwareManager`."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal manager
            if manager is None:
                manager = ThreadedHardwareManager(max_workers=2)
            operation_id = manager.submit_operation(
                function=func,
                args=args,
                kwargs=kwargs,
                timeout=timeout,
                operation_name=func.__name__,
            )
            return manager.get_operation_result(operation_id, timeout=timeout)

        return wrapper

    return decorator


if __name__ == "__main__":
    import sys

    app = QtCore.QCoreApplication(sys.argv)

    def test_function(duration: float = 0.2, should_fail: bool = False) -> str:
        time.sleep(duration)
        if should_fail:
            raise ValueError("Test error")
        return f"Completed after {duration}s"

    manager = ThreadedHardwareManager(max_workers=2)
    op = manager.submit_operation(function=test_function, args=(0.2,), operation_name="test")
    print("Operation result:", manager.get_operation_result(op, timeout=1.0))
    manager.shutdown()

    acquisition = AsyncDataAcquisition(
        acquisition_function=lambda: f"tick-{time.time()}",
        data_callback=lambda data: print("data", data),
    )
    acquisition.start(0.1)
    QtCore.QTimer.singleShot(500, lambda: acquisition.stop())
    QtCore.QTimer.singleShot(700, app.quit)
    sys.exit(app.exec())