"""
Mock Mode Tests for PyRPL Scope IPC Plugin - Using Shared Manager

These tests verify scope functionality through the SharedPyRPLManager
in mock mode (no hardware required).

Tests cover:
- SharedPyRPLManager integration
- Scope acquisition commands
- Parameter changes (decimation, trigger)
- Concurrent operations
- Resource cleanup

All tests use the shared manager architecture with mock PyRPL backend.
"""
import pytest
import time
import threading
import numpy as np

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager in mock mode for all tests in this module."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_scope_mock',
        'mock_mode': True
    }
    
    print("\n[Setup] Starting shared PyRPL worker in mock mode...")
    mgr.start_worker(config)
    time.sleep(1.0)
    
    # Verify worker is running
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok', "Worker ping failed"
    print("[Setup] Shared worker ready")
    
    yield mgr
    
    print("\n[Teardown] Shutting down shared worker...")
    mgr.shutdown()
    time.sleep(1.0)


class TestSharedManagerScopeMock:
    """Test Scope commands via SharedPyRPLManager in mock mode."""
    
    def test_scope_acquire_command(self, shared_manager_mock):
        """Test scope acquisition through shared manager."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in1',
            'timeout': 5.0
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
        assert 'voltage' in response['data']
        assert 'time' in response['data']
        
        voltage = np.array(response['data']['voltage'])
        time_axis = np.array(response['data']['time'])
        
        assert len(voltage) > 0
        assert len(time_axis) > 0
        assert len(voltage) == len(time_axis)
    
    def test_scope_set_decimation(self, shared_manager_mock):
        """Test changing decimation setting."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('scope_set_decimation', {
            'value': 128
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_scope_set_trigger(self, shared_manager_mock):
        """Test changing trigger source."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('scope_set_trigger', {
            'source': 'ch1_positive_edge'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_multiple_scope_acquisitions(self, shared_manager_mock):
        """Test multiple sequential acquisitions."""
        mgr = shared_manager_mock
        
        num_acquisitions = 10
        for i in range(num_acquisitions):
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            assert 'voltage' in response['data']
    
    def test_concurrent_scope_commands(self, shared_manager_mock):
        """Test concurrent scope operations via command multiplexing."""
        mgr = shared_manager_mock
        
        results = {}
        errors = []
        
        def acquire_scope(thread_id):
            try:
                response = mgr.send_command('scope_acquire', {
                    'decimation': 64,
                    'trigger_source': 'immediately',
                    'input_channel': 'in1',
                    'timeout': 5.0
                }, timeout=10.0)
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=acquire_scope, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all
        for t in threads:
            t.join(timeout=30)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5
        
        for thread_id, response in results.items():
            assert response['status'] == 'ok'
            assert 'voltage' in response['data']
    
    def test_scope_different_channels(self, shared_manager_mock):
        """Test acquiring from different input channels."""
        mgr = shared_manager_mock
        
        for channel in ['in1', 'in2']:
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': channel,
                'timeout': 5.0
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            assert 'voltage' in response['data']
    
    def test_scope_different_decimations(self, shared_manager_mock):
        """Test different decimation values."""
        mgr = shared_manager_mock
        
        for decimation in [32, 64, 128, 256]:
            # Set decimation
            mgr.send_command('scope_set_decimation', {'value': decimation}, timeout=5.0)
            
            # Acquire
            response = mgr.send_command('scope_acquire', {
                'decimation': decimation,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
    
    def test_rapid_acquisitions(self, shared_manager_mock):
        """Test rapid successive acquisitions."""
        mgr = shared_manager_mock
        
        start_time = time.time()
        num_acquisitions = 20
        
        for i in range(num_acquisitions):
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_acquisitions} acquisitions in {duration:.2f}s ({num_acquisitions/duration:.1f} Hz)")
    
    def test_no_memory_leaks(self, shared_manager_mock):
        """Test that many acquisitions don't leak memory."""
        mgr = shared_manager_mock
        
        num_acquisitions = 50
        for i in range(num_acquisitions):
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            
            if i % 10 == 0:
                print(f"Completed {i}/{num_acquisitions} acquisitions")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
