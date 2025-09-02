# -*- coding: utf-8 -*-
"""
Advanced Threading Utilities for PyMoDAQ PyRPL Plugins

This module provides enhanced threading support for PyRPL plugins using PyMoDAQ's
ThreadCommand system. It includes thread pools, async hardware operations, and
proper error handling while maintaining GUI responsiveness.

Classes:
    ThreadedHardwareManager: Manages threaded hardware operations
    AsyncDataAcquisition: Asynchronous data acquisition with cancellation
    ThreadSafeQueue: Thread-safe queue for hardware commands
"""

import logging
import threading
import queue
import time
import functools
from typing import Any, Callable, Optional, Dict, List, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from enum import Enum

from pymodaq_utils.utils import ThreadCommand

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Status of threaded operations."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ThreadedOperation:
    """Container for threaded operation details."""
    operation_id: str
    function: Callable
    args: tuple
    kwargs: dict
    timeout: float
    status: OperationStatus = OperationStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class ThreadSafeQueue:
    """Thread-safe queue for hardware commands with priority support."""
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize thread-safe queue.
        
        Parameters:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue = queue.PriorityQueue(maxsize=maxsize)
        self._counter = 0
        self._lock = threading.Lock()
    
    def put(self, item: Any, priority: int = 0, timeout: Optional[float] = None) -> bool:
        """
        Put item in queue with optional priority.
        
        Parameters:
            item: Item to put in queue
            priority: Priority (lower number = higher priority)
            timeout: Optional timeout for putting item
            
        Returns:
            True if item was put successfully, False if timeout
        """
        with self._lock:
            counter = self._counter
            self._counter += 1
        
        try:
            self._queue.put((priority, counter, item), timeout=timeout)
            return True
        except queue.Full:
            logger.warning("Queue is full, item not added")
            return False
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """
        Get item from queue.
        
        Parameters:
            timeout: Optional timeout for getting item
            
        Returns:
            Item from queue
            
        Raises:
            queue.Empty: If timeout occurs
        """
        priority, counter, item = self._queue.get(timeout=timeout)
        return item
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """Get approximate queue size."""
        return self._queue.qsize()


class ThreadedHardwareManager:
    """
    Manages threaded hardware operations with cancellation and timeout support.
    
    This class provides a clean interface for running hardware operations
    in separate threads while maintaining PyMoDAQ's ThreadCommand pattern
    for status updates and GUI responsiveness.
    """
    
    def __init__(self, max_workers: int = 4, status_callback: Optional[Callable] = None):
        """
        Initialize threaded hardware manager.
        
        Parameters:
            max_workers: Maximum number of worker threads
            status_callback: Callback function for status updates
        """
        self.max_workers = max_workers
        self.status_callback = status_callback
        
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._operations: Dict[str, ThreadedOperation] = {}
        self._operation_counter = 0
        self._lock = threading.Lock()
        
        logger.info(f"ThreadedHardwareManager initialized with {max_workers} workers")
    
    def _emit_status(self, message: str, level: str = 'log') -> None:
        """Emit status update via callback."""
        if self.status_callback:
            try:
                self.status_callback(ThreadCommand('Update_Status', [message, level]))
            except Exception as e:
                logger.error(f"Error emitting status: {e}")
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID."""
        with self._lock:
            self._operation_counter += 1
            return f"op_{self._operation_counter:06d}"
    
    def submit_operation(self,
                        function: Callable,
                        args: tuple = (),
                        kwargs: dict = None,
                        timeout: float = 30.0,
                        operation_name: Optional[str] = None) -> str:
        """
        Submit hardware operation for threaded execution.
        
        Parameters:
            function: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            timeout: Operation timeout in seconds
            operation_name: Optional descriptive name
            
        Returns:
            Operation ID for tracking
        """
        if kwargs is None:
            kwargs = {}
        
        operation_id = self._generate_operation_id()
        operation = ThreadedOperation(
            operation_id=operation_id,
            function=function,
            args=args,
            kwargs=kwargs,
            timeout=timeout
        )
        
        with self._lock:
            self._operations[operation_id] = operation
        
        # Submit to thread pool
        future = self._executor.submit(self._execute_operation, operation)
        
        name = operation_name or function.__name__
        self._emit_status(f"Started threaded operation: {name} ({operation_id})")
        
        logger.debug(f"Submitted operation {operation_id}: {name}")
        return operation_id
    
    def _execute_operation(self, operation: ThreadedOperation) -> Any:
        """Execute operation in thread with error handling."""
        operation.status = OperationStatus.RUNNING
        operation.start_time = time.time()
        
        try:
            # Execute the operation
            result = operation.function(*operation.args, **operation.kwargs)
            
            operation.result = result
            operation.status = OperationStatus.COMPLETED
            operation.end_time = time.time()
            
            self._emit_status(f"Operation {operation.operation_id} completed "
                            f"in {operation.duration:.3f}s")
            
            return result
            
        except Exception as e:
            operation.error = e
            operation.status = OperationStatus.FAILED
            operation.end_time = time.time()
            
            error_msg = f"Operation {operation.operation_id} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._emit_status(error_msg, 'log')
            
            raise
    
    def get_operation_result(self, operation_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get result of completed operation.
        
        Parameters:
            operation_id: Operation ID
            timeout: Optional timeout for waiting
            
        Returns:
            Operation result
            
        Raises:
            KeyError: If operation ID not found
            TimeoutError: If timeout occurs
            Exception: If operation failed
        """
        if operation_id not in self._operations:
            raise KeyError(f"Operation {operation_id} not found")
        
        operation = self._operations[operation_id]
        
        # Wait for completion if still running
        start_wait = time.time()
        while operation.status == OperationStatus.RUNNING:
            if timeout and (time.time() - start_wait) > timeout:
                raise TimeoutError(f"Timeout waiting for operation {operation_id}")
            time.sleep(0.01)
        
        if operation.status == OperationStatus.FAILED:
            raise operation.error
        elif operation.status == OperationStatus.COMPLETED:
            return operation.result
        else:
            raise RuntimeError(f"Operation {operation_id} in unexpected state: {operation.status}")
    
    def wait_for_operation(self, operation_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for operation to complete.
        
        Parameters:
            operation_id: Operation ID
            timeout: Optional timeout
            
        Returns:
            True if operation completed successfully, False otherwise
        """
        try:
            self.get_operation_result(operation_id, timeout)
            return True
        except Exception:
            return False
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel pending or running operation.
        
        Parameters:
            operation_id: Operation ID
            
        Returns:
            True if cancellation successful, False otherwise
        """
        if operation_id not in self._operations:
            return False
        
        operation = self._operations[operation_id]
        
        if operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
            return False
        
        operation.status = OperationStatus.CANCELLED
        self._emit_status(f"Operation {operation_id} cancelled")
        
        return True
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """Get status of operation."""
        if operation_id not in self._operations:
            return None
        return self._operations[operation_id].status
    
    def list_operations(self) -> List[Dict[str, Any]]:
        """List all operations with their status."""
        operations = []
        for op_id, operation in self._operations.items():
            operations.append({
                'id': op_id,
                'status': operation.status.value,
                'function': operation.function.__name__,
                'duration': operation.duration,
                'error': str(operation.error) if operation.error else None
            })
        return operations
    
    def cleanup_completed_operations(self, max_age_seconds: float = 300) -> int:
        """
        Clean up old completed operations.
        
        Parameters:
            max_age_seconds: Maximum age of operations to keep
            
        Returns:
            Number of operations cleaned up
        """
        current_time = time.time()
        to_remove = []
        
        for op_id, operation in self._operations.items():
            if (operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED] and
                operation.end_time and 
                (current_time - operation.end_time) > max_age_seconds):
                to_remove.append(op_id)
        
        for op_id in to_remove:
            del self._operations[op_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old operations")
        
        return len(to_remove)
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """
        Shutdown thread pool and clean up resources.
        
        Parameters:
            wait: Whether to wait for completion
            timeout: Timeout for waiting
        """
        logger.info("Shutting down ThreadedHardwareManager")
        
        # Cancel all pending operations
        for op_id, operation in self._operations.items():
            if operation.status in [OperationStatus.PENDING, OperationStatus.RUNNING]:
                self.cancel_operation(op_id)
        
        # Shutdown executor
        self._executor.shutdown(wait=wait, timeout=timeout)
        
        self._emit_status("ThreadedHardwareManager shut down")


class AsyncDataAcquisition:
    """
    Asynchronous data acquisition with cancellation support.
    
    This class provides a high-level interface for running continuous
    data acquisition in the background while maintaining responsiveness.
    """
    
    def __init__(self, 
                 acquisition_function: Callable,
                 data_callback: Callable,
                 status_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None):
        """
        Initialize async data acquisition.
        
        Parameters:
            acquisition_function: Function that acquires data
            data_callback: Called with acquired data
            status_callback: Called with status updates
            error_callback: Called when errors occur
        """
        self.acquisition_function = acquisition_function
        self.data_callback = data_callback
        self.status_callback = status_callback
        self.error_callback = error_callback
        
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
    def start(self, interval: float = 0.1) -> bool:
        """
        Start continuous data acquisition.
        
        Parameters:
            interval: Acquisition interval in seconds
            
        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            logger.warning("Data acquisition already running")
            return False
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._acquisition_loop,
            args=(interval,),
            daemon=True
        )
        
        self._thread.start()
        self._running = True
        
        if self.status_callback:
            self.status_callback(ThreadCommand('Update_Status', 
                ['Started continuous data acquisition', 'log']))
        
        logger.info(f"Started async data acquisition with {interval}s interval")
        return True
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop data acquisition.
        
        Parameters:
            timeout: Timeout for stopping
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._running:
            return True
        
        logger.info("Stopping async data acquisition")
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            
            if self._thread.is_alive():
                logger.warning("Data acquisition thread did not stop within timeout")
                return False
        
        self._running = False
        
        if self.status_callback:
            self.status_callback(ThreadCommand('Update_Status', 
                ['Stopped continuous data acquisition', 'log']))
        
        return True
    
    def _acquisition_loop(self, interval: float) -> None:
        """Main acquisition loop running in thread."""
        logger.debug("Data acquisition loop started")
        
        while not self._stop_event.is_set():
            try:
                # Acquire data
                data = self.acquisition_function()
                
                if data is not None:
                    # Send data to callback
                    self.data_callback(data)
                
                # Wait for next acquisition (with early exit on stop)
                self._stop_event.wait(timeout=interval)
                
            except Exception as e:
                logger.error(f"Error in data acquisition loop: {e}", exc_info=True)
                
                if self.error_callback:
                    try:
                        self.error_callback(e)
                    except Exception as cb_error:
                        logger.error(f"Error in error callback: {cb_error}")
                
                # Continue loop unless critical error
                self._stop_event.wait(timeout=interval)
        
        logger.debug("Data acquisition loop ended")
    
    @property
    def is_running(self) -> bool:
        """Check if acquisition is running."""
        return self._running and self._thread and self._thread.is_alive()


def threaded_hardware_operation(timeout: float = 30.0, 
                               manager: Optional[ThreadedHardwareManager] = None):
    """
    Decorator for making hardware operations threaded.
    
    Parameters:
        timeout: Operation timeout
        manager: Optional hardware manager instance
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal manager
            
            # Use default manager if none provided
            if manager is None:
                manager = ThreadedHardwareManager(max_workers=2)
            
            # Submit operation
            operation_id = manager.submit_operation(
                function=func,
                args=args,
                kwargs=kwargs,
                timeout=timeout,
                operation_name=func.__name__
            )
            
            # Wait for result
            return manager.get_operation_result(operation_id, timeout=timeout)
        
        return wrapper
    return decorator


if __name__ == '__main__':
    # Test threading utilities
    def test_function(duration: float = 1.0, should_fail: bool = False):
        """Test function for threading."""
        time.sleep(duration)
        if should_fail:
            raise ValueError("Test error")
        return f"Completed after {duration}s"
    
    def status_callback(command: ThreadCommand):
        """Test status callback."""
        print(f"Status: {command.path} - {command.param}")
    
    # Test ThreadedHardwareManager
    print("Testing ThreadedHardwareManager...")
    manager = ThreadedHardwareManager(max_workers=2, status_callback=status_callback)
    
    # Submit some operations
    op1 = manager.submit_operation(test_function, args=(0.5,), operation_name="Quick test")
    op2 = manager.submit_operation(test_function, args=(1.0,), operation_name="Slow test")
    
    # Wait for results
    try:
        result1 = manager.get_operation_result(op1, timeout=2.0)
        result2 = manager.get_operation_result(op2, timeout=2.0)
        print(f"Results: {result1}, {result2}")
    except Exception as e:
        print(f"Error: {e}")
    
    # List operations
    print("Operations:", manager.list_operations())
    
    # Test AsyncDataAcquisition
    print("\nTesting AsyncDataAcquisition...")
    
    def acquire_data():
        """Mock data acquisition."""
        return f"Data at {time.time()}"
    
    def data_callback(data):
        """Mock data callback."""
        print(f"Received: {data}")
    
    acquisition = AsyncDataAcquisition(
        acquisition_function=acquire_data,
        data_callback=data_callback,
        status_callback=status_callback
    )
    
    # Start acquisition
    acquisition.start(interval=0.5)
    time.sleep(2.0)
    acquisition.stop()
    
    # Cleanup
    manager.shutdown()
    
    print("Threading utilities test completed!")