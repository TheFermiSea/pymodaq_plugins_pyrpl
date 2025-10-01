"""
Hardware Tests for PyRPL Scope IPC Plugin

Tests scope functionality with REAL Red Pitaya hardware.
Requires: PYRPL_TEST_HOST=100.107.106.75

Run with: pytest tests/test_plugin_ipc_scope_hardware.py -v -s
"""
import pytest
import time
import threading
import numpy as np
import os

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Hardware configuration
HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_scope_hardware'

# Skip all tests if hardware not available
pytestmark = pytest.mark.skipif(
    not os.getenv('PYRPL_TEST_HOST'),
    reason="Hardware tests require PYRPL_TEST_HOST environment variable"
)


@pytest.fixture(scope="module")
def shared_manager_hardware():
    """Start shared manager with REAL hardware."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': HARDWARE_IP,
        'config_name': CONFIG_NAME,
        'mock_mode': False  # REAL HARDWARE
    }
    
    print(f"\n[Setup] Connecting to Red Pitaya at {HARDWARE_IP}...")
    mgr.start_worker(config)
    
    # IMPORTANT: Hardware takes 5-10s to load FPGA bitstream
    time.sleep(7.0)
    
    # Verify connection
    response = mgr.send_command('ping', {}, timeout=10.0)
    assert response['status'] == 'ok', f"Hardware ping failed: {response}"
    print("[Setup] Hardware connection ready")
    
    yield mgr
    
    print("\n[Teardown] Disconnecting from hardware...")
    mgr.shutdown()
    time.sleep(2.0)


class TestScopeIPCHardware:
    """Test Scope with real Red Pitaya hardware."""
    
    def test_hardware_scope_acquire(self, shared_manager_hardware):
        """Test scope acquisition with real hardware."""
        mgr = shared_manager_hardware
        
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
        
        # Hardware validation: check voltage is in valid range
        assert voltage.min() >= -2.0, "Voltage too low (hardware error?)"
        assert voltage.max() <= 2.0, "Voltage too high (hardware error?)"
        
        print(f"Hardware scope: {len(voltage)} points, "
              f"min={voltage.min():.3f}V, max={voltage.max():.3f}V")
    
    def test_hardware_concurrent_acquisitions(self, shared_manager_hardware):
        """Test concurrent acquisitions on hardware."""
        mgr = shared_manager_hardware
        
        results = {}
        errors = []
        
        def acquire(thread_id):
            try:
                response = mgr.send_command('scope_acquire', {
                    'decimation': 64,
                    'trigger_source': 'immediately',
                    'input_channel': 'in1',
                    'timeout': 5.0
                }, timeout=15.0)
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=acquire, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5
        
        for thread_id, response in results.items():
            assert response['status'] == 'ok'
            voltage = np.array(response['data']['voltage'])
            assert len(voltage) > 0
        
        print(f"Concurrent hardware acquisitions: {len(results)}/5 succeeded")
    
    def test_hardware_input2_channel(self, shared_manager_hardware):
        """Test acquisition from input2 (loopback configured)."""
        mgr = shared_manager_hardware
        
        # Note: Hardware loopback is input2 → output2
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in2',
            'timeout': 5.0
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
        voltage = np.array(response['data']['voltage'])
        assert len(voltage) > 0
        
        print(f"Input2 acquisition: {len(voltage)} points")
    
    def test_hardware_different_decimations(self, shared_manager_hardware):
        """Test different decimation values on hardware."""
        mgr = shared_manager_hardware
        
        for decimation in [32, 64, 128, 256]:
            response = mgr.send_command('scope_acquire', {
                'decimation': decimation,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=15.0)
            
            assert response['status'] == 'ok'
            voltage = np.array(response['data']['voltage'])
            assert len(voltage) > 0
            
            print(f"Decimation {decimation}: {len(voltage)} points")
    
    def test_hardware_trigger_modes(self, shared_manager_hardware):
        """Test trigger mode on hardware."""
        mgr = shared_manager_hardware
        
        # Only test 'immediately' trigger - edge triggers may not work on all hardware setups
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in1',
            'timeout': 5.0
        }, timeout=15.0)
        
        assert response['status'] == 'ok'
        print("Trigger 'immediately': OK")
    
    def test_hardware_rapid_acquisitions(self, shared_manager_hardware):
        """Test rapid successive acquisitions on hardware."""
        mgr = shared_manager_hardware
        
        start_time = time.time()
        num_acquisitions = 10
        
        for i in range(num_acquisitions):
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=15.0)
            
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_acquisitions} hardware acquisitions in {duration:.2f}s "
              f"({num_acquisitions/duration:.1f} Hz)")
    
    def test_hardware_no_memory_leaks(self, shared_manager_hardware):
        """Test that hardware acquisitions don't leak memory."""
        mgr = shared_manager_hardware
        
        num_acquisitions = 30
        for i in range(num_acquisitions):
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=15.0)
            
            assert response['status'] == 'ok'
            
            if i % 10 == 0:
                print(f"Completed {i}/{num_acquisitions} hardware acquisitions")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
