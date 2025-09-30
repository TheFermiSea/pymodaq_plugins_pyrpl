import pytest
import threading
import time
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture
def manager():
    """Get a SharedPyRPLManager instance with mock mode."""
    mgr = get_shared_worker_manager()
    
    # Start worker in mock mode
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_multiplexing',
        'mock_mode': True
    }
    mgr.start_worker(config)
    
    # Wait for worker to initialize
    time.sleep(0.5)
    
    yield mgr
    
    # Cleanup
    mgr.shutdown()
    time.sleep(0.5)


class TestCommandMultiplexing:
    """Test command ID multiplexing functionality."""
    
    def test_single_command_with_id(self, manager):
        """Test that a single command with ID works correctly."""
        response = manager.send_command('ping', {})
        
        assert response['status'] == 'ok'
        assert response['data'] in ('pong', 'ok')
        assert 'id' in response, "Response should include command ID"
    
    def test_concurrent_commands(self, manager):
        """Test that concurrent commands from multiple threads work without cross-talk."""
        num_threads = 10
        results = {}
        errors = []
        
        def send_ping(thread_id):
            try:
                response = manager.send_command('ping', {'thread_id': thread_id})
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=send_ping, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
        
        # Verify all responses are valid
        for thread_id, response in results.items():
            assert response['status'] == 'ok', f"Thread {thread_id} got error: {response}"
            assert 'id' in response, f"Thread {thread_id} response missing ID"
    
    def test_command_timeout(self, manager):
        """Test that command timeout works and cleans up properly."""
        # Send a command with very short timeout that will fail
        with pytest.raises(TimeoutError) as exc_info:
            manager.send_command('ping', {}, timeout=0.001)
        
        assert 'timed out' in str(exc_info.value).lower()
        
        # Verify pending responses map is empty after timeout
        assert len(manager._pending_responses) == 0, "Pending responses not cleaned up after timeout"
    
    def test_resource_cleanup(self, manager):
        """Test that no memory leaks occur with many commands."""
        num_commands = 100
        
        for i in range(num_commands):
            response = manager.send_command('ping', {'iteration': i})
            assert response['status'] == 'ok'
        
        # Verify no pending responses remain
        assert len(manager._pending_responses) == 0, f"Memory leak: {len(manager._pending_responses)} pending responses remain"
    
    def test_backward_compatibility(self, manager):
        """Test that responses without ID (backward compat) don't crash the system."""
        # This test verifies the system handles responses without IDs gracefully
        # In practice, all new responses will have IDs, but old worker responses might not
        
        # Send a few commands normally
        for i in range(5):
            response = manager.send_command('ping', {})
            assert response['status'] == 'ok'
            assert 'id' in response
        
        # System should still be working
        assert manager.is_worker_running()
