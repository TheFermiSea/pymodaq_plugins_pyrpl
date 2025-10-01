"""
Hardware Tests for PyRPL IQ IPC Plugin

Tests IQ demodulator (lock-in amplifier) with REAL Red Pitaya hardware.
Requires: PYRPL_TEST_HOST=100.107.106.75

Run with: pytest tests/test_plugin_ipc_iq_hardware.py -v -s
"""
import pytest
import time
import threading
import numpy as np
import os

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Hardware configuration
HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_iq_hardware'

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


class TestIQIPCHardware:
    """Test IQ demodulator with real Red Pitaya hardware."""
    
    def test_hardware_iq_setup(self, shared_manager_hardware):
        """Test IQ configuration with real hardware."""
        mgr = shared_manager_hardware
        
        response = mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
    
    def test_hardware_iq_get_quadratures(self, shared_manager_hardware):
        """Test reading I and Q values from hardware."""
        mgr = shared_manager_hardware
        
        # Setup first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=10.0)
        
        # Read quadratures
        response = mgr.send_command('iq_get_quadratures', {
            'channel': 'iq0'
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
        assert 'i' in response['data']
        assert 'q' in response['data']
        
        i_value = response['data']['i']
        q_value = response['data']['q']
        
        assert isinstance(i_value, (int, float))
        assert isinstance(q_value, (int, float))
        
        # Hardware validation: values should be in reasonable range
        assert abs(i_value) < 10.0, "I value out of expected range"
        assert abs(q_value) < 10.0, "Q value out of expected range"
        
        # Calculate magnitude and phase
        magnitude = np.sqrt(i_value**2 + q_value**2)
        phase = np.arctan2(q_value, i_value) * 180.0 / np.pi
        
        print(f"Hardware IQ: I={i_value:.6f}, Q={q_value:.6f}, "
              f"Mag={magnitude:.6f}, Phase={phase:.2f}°")
    
    def test_hardware_multiple_iq_channels(self, shared_manager_hardware):
        """Test all 3 IQ channels with hardware."""
        mgr = shared_manager_hardware
        
        for channel in ['iq0', 'iq1', 'iq2']:
            # Setup
            mgr.send_command('iq_setup', {
                'channel': channel,
                'frequency': 25e6,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=10.0)
            
            # Read
            response = mgr.send_command('iq_get_quadratures', {
                'channel': channel
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            assert 'i' in response['data']
            assert 'q' in response['data']
            
            print(f"Hardware {channel}: I={response['data']['i']:.6f}, Q={response['data']['q']:.6f}")
    
    def test_hardware_concurrent_iq_reads(self, shared_manager_hardware):
        """Test concurrent IQ readings from hardware."""
        mgr = shared_manager_hardware
        
        # Setup IQ first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=10.0)
        
        results = {}
        errors = []
        
        def read_iq(thread_id):
            try:
                response = mgr.send_command('iq_get_quadratures', {
                    'channel': 'iq0'
                }, timeout=10.0)
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_iq, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        
        print(f"Concurrent hardware IQ reads: {len(results)}/10 succeeded")
    
    def test_hardware_different_frequencies(self, shared_manager_hardware):
        """Test different demodulation frequencies on hardware."""
        mgr = shared_manager_hardware
        
        frequencies = [1e6, 10e6, 25e6, 50e6]
        
        for freq in frequencies:
            mgr.send_command('iq_setup', {
                'channel': 'iq0',
                'frequency': freq,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=10.0)
            
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            print(f"Hardware frequency {freq/1e6:.1f} MHz: OK")
    
    def test_hardware_input2_channel(self, shared_manager_hardware):
        """Test IQ with input2 (loopback configured)."""
        mgr = shared_manager_hardware
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in2',
            'output_direct': 'off'
        }, timeout=10.0)
        
        response = mgr.send_command('iq_get_quadratures', {
            'channel': 'iq0'
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
        print(f"Hardware input2 IQ: I={response['data']['i']:.6f}, Q={response['data']['q']:.6f}")
    
    def test_hardware_rapid_iq_reads(self, shared_manager_hardware):
        """Test rapid successive IQ reads on hardware."""
        mgr = shared_manager_hardware
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=10.0)
        
        start_time = time.time()
        num_reads = 30
        
        for i in range(num_reads):
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=10.0)
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_reads} hardware IQ reads in {duration:.2f}s ({num_reads/duration:.1f} Hz)")
    
    def test_hardware_no_memory_leaks(self, shared_manager_hardware):
        """Test that hardware IQ reads don't leak memory."""
        mgr = shared_manager_hardware
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=10.0)
        
        num_reads = 50
        for i in range(num_reads):
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            
            if i % 10 == 0:
                print(f"Completed {i}/{num_reads} hardware IQ reads")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
