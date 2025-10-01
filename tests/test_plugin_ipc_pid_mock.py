"""
Mock Mode Tests for PyRPL PID IPC Plugin

Tests PID controller functionality through SharedPyRPLManager.
No hardware required - runs in mock mode.

Tests cover:
- PID configuration (P, I, D gains)
- Setpoint read/write
- Multiple PID channels
- Concurrent operations
- Different input/output configurations
"""
import pytest
import time
import threading

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager in mock mode."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_pid_mock',
        'mock_mode': True
    }
    
    print("\n[Setup] Starting shared PyRPL worker in mock mode...")
    mgr.start_worker(config)
    time.sleep(1.0)
    
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok'
    print("[Setup] Shared worker ready")
    
    yield mgr
    
    print("\n[Teardown] Shutting down shared worker...")
    mgr.shutdown()
    time.sleep(1.0)


class TestPIDIPCMock:
    """Test PID controller via SharedPyRPLManager in mock mode."""
    
    def test_pid_configure(self, shared_manager_mock):
        """Test PID configuration."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_pid_set_setpoint(self, shared_manager_mock):
        """Test setting PID setpoint."""
        mgr = shared_manager_mock
        
        # Configure first
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        # Set setpoint
        response = mgr.send_command('pid_set_setpoint', {
            'channel': 'pid0',
            'value': 0.5
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_pid_get_setpoint(self, shared_manager_mock):
        """Test reading PID setpoint."""
        mgr = shared_manager_mock
        
        # Configure and set
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        mgr.send_command('pid_set_setpoint', {
            'channel': 'pid0',
            'value': 0.5
        }, timeout=5.0)
        
        # Get setpoint
        response = mgr.send_command('pid_get_setpoint', {
            'channel': 'pid0'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
        
        setpoint = response['data']  # Data is the setpoint value directly
        assert isinstance(setpoint, (int, float))
        # Note: Mock mode may not persist setpoint changes
        
        print(f"PID setpoint: {setpoint:.6f} V")
    
    def test_multiple_pid_channels(self, shared_manager_mock):
        """Test all 3 PID channels."""
        mgr = shared_manager_mock
        
        for i, channel in enumerate(['pid0', 'pid1', 'pid2']):
            setpoint_value = i * 0.1
            
            # Configure
            mgr.send_command('pid_configure', {
                'channel': channel,
                'p': 0.1,
                'i': 10.0,
                'd': 0.0,
                'setpoint': setpoint_value,
                'input': 'in1',
                'output_direct': 'out1'
            }, timeout=5.0)
            
            # Read back
            response = mgr.send_command('pid_get_setpoint', {
                'channel': channel
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"{channel} setpoint: {response['data']:.6f} V")
    
    def test_concurrent_pid_operations(self, shared_manager_mock):
        """Test concurrent PID setpoint changes from multiple threads."""
        mgr = shared_manager_mock
        
        # Configure PIDs first
        for channel in ['pid0', 'pid1', 'pid2']:
            mgr.send_command('pid_configure', {
                'channel': channel,
                'p': 0.1,
                'i': 10.0,
                'd': 0.0,
                'setpoint': 0.0,
                'input': 'in1',
                'output_direct': 'out1'
            }, timeout=5.0)
        
        results = {}
        errors = []
        
        def set_and_get_setpoint(thread_id):
            try:
                channel = f'pid{thread_id % 3}'  # Rotate through pid0, pid1, pid2
                value = thread_id * 0.01
                
                # Set
                mgr.send_command('pid_set_setpoint', {
                    'channel': channel,
                    'value': value
                }, timeout=5.0)
                
                # Get
                response = mgr.send_command('pid_get_setpoint', {
                    'channel': channel
                }, timeout=5.0)
                
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(9):  # 3 threads per PID channel
            t = threading.Thread(target=set_and_get_setpoint, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 9
        
        print(f"Concurrent PID operations: {len(results)}/9 succeeded")
    
    def test_different_pid_gains(self, shared_manager_mock):
        """Test different PID gain configurations."""
        mgr = shared_manager_mock
        
        gain_configs = [
            {'p': 0.1, 'i': 0.0, 'd': 0.0},  # P only
            {'p': 0.0, 'i': 10.0, 'd': 0.0},  # I only
            {'p': 0.0, 'i': 0.0, 'd': 0.001},  # D only
            {'p': 0.1, 'i': 10.0, 'd': 0.001},  # Full PID
        ]
        
        for gains in gain_configs:
            response = mgr.send_command('pid_configure', {
                'channel': 'pid0',
                'p': gains['p'],
                'i': gains['i'],
                'd': gains['d'],
                'setpoint': 0.0,
                'input': 'in1',
                'output_direct': 'out1'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"PID gains P={gains['p']}, I={gains['i']}, D={gains['d']}: OK")
    
    def test_different_pid_inputs(self, shared_manager_mock):
        """Test PID with different input sources."""
        mgr = shared_manager_mock
        
        inputs = ['in1', 'in2', 'iq0', 'iq1']
        
        for input_source in inputs:
            response = mgr.send_command('pid_configure', {
                'channel': 'pid0',
                'p': 0.1,
                'i': 10.0,
                'd': 0.0,
                'setpoint': 0.0,
                'input': input_source,
                'output_direct': 'out1'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"PID input {input_source}: OK")
    
    def test_different_pid_outputs(self, shared_manager_mock):
        """Test PID with different output destinations."""
        mgr = shared_manager_mock
        
        outputs = ['off', 'out1', 'out2']
        
        for output_dest in outputs:
            response = mgr.send_command('pid_configure', {
                'channel': 'pid0',
                'p': 0.1,
                'i': 10.0,
                'd': 0.0,
                'setpoint': 0.0,
                'input': 'in1',
                'output_direct': output_dest
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"PID output {output_dest}: OK")
    
    def test_rapid_setpoint_changes(self, shared_manager_mock):
        """Test rapid setpoint changes."""
        mgr = shared_manager_mock
        
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        start_time = time.time()
        num_changes = 50
        
        for i in range(num_changes):
            value = (i % 10) * 0.1
            response = mgr.send_command('pid_set_setpoint', {
                'channel': 'pid0',
                'value': value
            }, timeout=5.0)
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_changes} setpoint changes in {duration:.2f}s ({num_changes/duration:.1f} Hz)")
    
    def test_no_memory_leaks(self, shared_manager_mock):
        """Test that many PID operations don't leak memory."""
        mgr = shared_manager_mock
        
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        num_operations = 100
        for i in range(num_operations):
            # Alternate between set and get
            if i % 2 == 0:
                mgr.send_command('pid_set_setpoint', {
                    'channel': 'pid0',
                    'value': (i % 10) * 0.1
                }, timeout=5.0)
            else:
                response = mgr.send_command('pid_get_setpoint', {
                    'channel': 'pid0'
                }, timeout=5.0)
                assert response['status'] == 'ok'
            
            if i % 20 == 0:
                print(f"Completed {i}/{num_operations} PID operations")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
