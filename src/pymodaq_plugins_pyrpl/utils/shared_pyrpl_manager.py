"""
Shared PyRPL Worker Manager

This module ensures that only ONE PyRPL worker process is created and shared
across ALL PyMoDAQ plugins (Scope, ASG, PID, IQ, etc.).

The worker process hosts the PyRPL instance which manages the Red Pitaya hardware.
All plugins communicate with this single worker via their own command/response queues.
"""
import logging
import multiprocessing
from multiprocessing import Process, Queue
from typing import Optional, Dict, Tuple
import atexit
import uuid
import threading
import queue

logger = logging.getLogger(__name__)


class SharedPyRPLManager:
    """
    Singleton manager for the shared PyRPL worker process.
    
    All PyMoDAQ plugins should use this manager to get access to the
    PyRPL worker instead of creating their own worker processes.
    """
    
    _instance: Optional['SharedPyRPLManager'] = None
    _lock = multiprocessing.Lock()
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the manager (only runs once due to singleton)."""
        if self._initialized:
            return
            
        self.worker_process: Optional[Process] = None
        self.worker_config: Optional[Dict] = None
        self.is_running = False
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None
        
        # Lock to serialize command/response pairs from multiple plugins
        self.command_lock = multiprocessing.Lock()
        
        # Command ID multiplexing infrastructure
        self._pending_responses: Dict[str, Tuple[threading.Event, dict]] = {}
        self._response_lock = threading.Lock()
        self._response_listener_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        
        self._initialized = True
        logger.info("SharedPyRPLManager initialized")
    
    def start_worker(self, config: Dict) -> Tuple[Queue, Queue]:
        """
        Start the shared PyRPL worker process if not already running.
        
        Returns the shared command and response queues that ALL plugins use.
        
        Args:
            config: PyRPL configuration dict with keys:
                - hostname: Red Pitaya IP/hostname
                - config_name: PyRPL config name
                - mock_mode: Boolean for mock mode
        
        Returns:
            Tuple of (command_queue, response_queue) for the shared worker
        """
        with self._lock:
            # If worker already running with same config, return existing queues
            if self.is_running and self.worker_config == config:
                logger.info("PyRPL worker already running, returning existing queues")
                return self.command_queue, self.response_queue
            
            # If worker running with different config, warn and return existing
            if self.is_running and self.worker_config != config:
                logger.warning(
                    f"PyRPL worker already running with different config.\n"
                    f"  Existing: {self.worker_config}\n"
                    f"  Requested: {config}\n"
                    f"  Returning existing worker queues."
                )
                return self.command_queue, self.response_queue
            
            # Start new worker with SHARED queues
            try:
                from .pyrpl_ipc_worker import pyrpl_worker_main
                
                # Create shared queues that ALL plugins will use
                self.command_queue = Queue()
                self.response_queue = Queue()
                
                self.worker_process = Process(
                    target=pyrpl_worker_main,
                    args=(self.command_queue, self.response_queue, config),
                    daemon=True,
                    name="PyRPL-Worker"
                )
                self.worker_process.start()
                self.worker_config = config
                self.is_running = True
                
                # Reset shutdown event and start response listener thread
                self._shutdown_event.clear()  # Reset shutdown signal
                
                # Start or restart response listener thread
                if not self._response_listener_thread or not self._response_listener_thread.is_alive():
                    self._response_listener_thread = threading.Thread(
                        target=self._response_listener,
                        daemon=True,
                        name="PyRPL-ResponseListener",
                    )
                    self._response_listener_thread.start()
                    logger.info("Response listener thread started")
                
                logger.info(f"Started shared PyRPL worker process (PID: {self.worker_process.pid})")
                return self.command_queue, self.response_queue
                
            except Exception as e:
                logger.error(f"Failed to start PyRPL worker: {e}")
                raise
    
    def _response_listener(self):
        """
        Background thread that listens for responses from the worker process.
        
        This thread continuously monitors the response_queue and routes responses
        to the appropriate pending command based on the command ID.
        """
        while not self._shutdown_event.is_set():
            try:
                response = self.response_queue.get(timeout=0.1)
                cmd_id = response.get('id')
                
                if cmd_id:
                    # Response has an ID - route to waiting command
                    with self._response_lock:
                        pending = self._pending_responses.pop(cmd_id, None)
                    
                    if pending:
                        event, result_container = pending
                        result_container['response'] = response
                        event.set()
                    else:
                        logger.warning(f"Response for unknown id: {cmd_id}")
                else:
                    # Backward-compat: response without id (old worker or init message)
                    logger.debug("Response without id received (backward compatible)")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Response listener error: {e}")
    
    def send_command(self, command: str, params: Dict, timeout: float = 5.0) -> Dict:
        """
        Send a command to the shared worker and wait for response.
        
        Uses command ID multiplexing to support concurrent commands from multiple plugins.
        Each command gets a unique UUID that is used to route responses back to the caller.
        
        Args:
            command: Command name (e.g., 'scope_acquire', 'asg_setup')
            params: Command parameters dict
            timeout: Timeout in seconds to wait for response
        
        Returns:
            Response dict with 'status' and 'data' keys
        
        Raises:
            RuntimeError: If worker not running
            TimeoutError: If no response within timeout
        """
        if not self.is_worker_running():
            raise RuntimeError("PyRPL worker not running")
        
        # Check worker is alive
        if not self.worker_process.is_alive():
            raise RuntimeError("PyRPL worker process has died")
        
        # Validate timeout
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            timeout = 5.0
        
        # Generate unique command ID
        cmd_id = str(uuid.uuid4())
        event = threading.Event()
        result_container: Dict = {}
        
        # Register pending response
        with self._response_lock:
            self._pending_responses[cmd_id] = (event, result_container)
        
        try:
            # Send command with ID
            self.command_queue.put({
                'command': command,
                'params': params,
                'id': cmd_id
            })
            
            # Wait for response
            if event.wait(timeout):
                return result_container['response']
            
            raise TimeoutError(f"Command '{command}' timed out after {timeout}s")
            
        finally:
            # Always cleanup pending response (prevents memory leaks)
            with self._response_lock:
                self._pending_responses.pop(cmd_id, None)
    
    def get_worker_process(self) -> Optional[Process]:
        """Get the shared worker process."""
        return self.worker_process
    
    def is_worker_running(self) -> bool:
        """Check if worker process is running."""
        with self._lock:
            if not self.is_running or self.worker_process is None:
                return False
            return self.worker_process.is_alive()
    
    def shutdown(self):
        """Shutdown the shared worker process and response listener."""
        # Signal listener thread to stop
        self._shutdown_event.set()
        
        # Wait for listener thread to exit
        if self._response_listener_thread and self._response_listener_thread.is_alive():
            self._response_listener_thread.join(timeout=2)
            logger.info("Response listener thread stopped")
        
        # Shutdown worker process
        with self._lock:
            if self.worker_process is not None and self.worker_process.is_alive():
                logger.info("Shutting down shared PyRPL worker...")
                
                # Send shutdown command
                try:
                    self.command_queue.put({'command': 'shutdown', 'params': {}}, timeout=1)
                except Exception:
                    pass  # Queue might be full or broken
                
                self.worker_process.join(timeout=5)
                
                if self.worker_process.is_alive():
                    logger.warning("Worker didn't terminate gracefully, terminating...")
                    self.worker_process.terminate()
                    self.worker_process.join(timeout=2)
                
                if self.worker_process.is_alive():
                    logger.warning("Worker didn't terminate, killing...")
                    self.worker_process.kill()
                
                self.worker_process = None
                self.is_running = False
                self.worker_config = None
                logger.info("Shared PyRPL worker shut down")


# Global instance
_manager = SharedPyRPLManager()


def get_shared_worker_manager() -> SharedPyRPLManager:
    """Get the global SharedPyRPLManager instance."""
    return _manager
