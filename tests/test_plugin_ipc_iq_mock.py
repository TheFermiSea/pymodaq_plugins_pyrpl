"""
Mock Mode Tests for PyRPL IQ IPC Plugin

Tests IQ demodulator (lock-in amplifier) through SharedPyRPLManager.
No hardware required - runs in mock mode.

Tests cover:
- IQ setup and configuration
- Quadrature (I/Q) value readout
- Multiple IQ channels
- Concurrent operations
- Different frequencies and parameters
"""
import pytest
import time
import threading
import numpy as np

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager in mock mode."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_iq_mock',
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


class TestIQIPCMock:
    """Test IQ demodulator via SharedPyRPLManager in mock mode."""
    
    def test_iq_setup(self, shared_manager_mock):
        """Test IQ configuration."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,  # 25 MHz demodulation
            'bandwidth': 1000.0,  # 1 kHz bandwidth
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_iq_get_quadratures(self, shared_manager_mock):
        """Test reading I and Q values."""
        mgr = shared_manager_mock
        
        # Setup first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        # Read quadratures
        response = mgr.send_command('iq_get_quadratures', {
            'channel': 'iq0'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
        assert 'i' in response['data']
        assert 'q' in response['data']
        
        i_value = response['data']['i']
        q_value = response['data']['q']
        
        assert isinstance(i_value, (int, float))
        assert isinstance(q_value, (int, float))
        
        # Calculate magnitude and phase
        magnitude = np.sqrt(i_value**2 + q_value**2)
        phase = np.arctan2(q_value, i_value) * 180.0 / np.pi
        
        print(f"IQ: I={i_value:.6f}, Q={q_value:.6f}, "
              f"Mag={magnitude:.6f}, Phase={phase:.2f}°")
    
    def test_multiple_iq_channels(self, shared_manager_mock):
        """Test all 3 IQ channels."""
        mgr = shared_manager_mock
        
        for channel in ['iq0', 'iq1', 'iq2']:
            # Setup
            mgr.send_command('iq_setup', {
                'channel': channel,
                'frequency': 25e6,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=5.0)
            
            # Read
            response = mgr.send_command('iq_get_quadratures', {
                'channel': channel
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            assert 'i' in response['data']
            assert 'q' in response['data']
            
            print(f"{channel}: I={response['data']['i']:.6f}, Q={response['data']['q']:.6f}")
    
    def test_concurrent_iq_reads(self, shared_manager_mock):
        """Test concurrent IQ readings from multiple threads."""
        mgr = shared_manager_mock
        
        # Setup IQ first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        results = {}
        errors = []
        
        def read_iq(thread_id):
            try:
                response = mgr.send_command('iq_get_quadratures', {
                    'channel': 'iq0'
                }, timeout=5.0)
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_iq, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        
        for thread_id, response in results.items():
            assert response['status'] == 'ok'
            assert 'i' in response['data']
            assert 'q' in response['data']
    
    def test_different_frequencies(self, shared_manager_mock):
        """Test different demodulation frequencies."""
        mgr = shared_manager_mock
        
        frequencies = [1e6, 10e6, 25e6, 50e6]
        
        for freq in frequencies:
            mgr.send_command('iq_setup', {
                'channel': 'iq0',
                'frequency': freq,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=5.0)
            
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"Frequency {freq/1e6:.1f} MHz: OK")
    
    def test_different_bandwidths(self, shared_manager_mock):
        """Test different bandwidth settings."""
        mgr = shared_manager_mock
        
        bandwidths = [100.0, 1000.0, 10000.0]
        
        for bw in bandwidths:
            mgr.send_command('iq_setup', {
                'channel': 'iq0',
                'frequency': 25e6,
                'bandwidth': bw,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=5.0)
            
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"Bandwidth {bw:.0f} Hz: OK")
    
    def test_rapid_iq_reads(self, shared_manager_mock):
        """Test rapid IQ readouts."""
        mgr = shared_manager_mock
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        start_time = time.time()
        num_reads = 50
        
        for i in range(num_reads):
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_reads} IQ reads in {duration:.2f}s ({num_reads/duration:.1f} Hz)")
    
    def test_iq_different_inputs(self, shared_manager_mock):
        """Test IQ with different input sources."""
        mgr = shared_manager_mock
        
        inputs = ['in1', 'in2']
        
        for input_source in inputs:
            mgr.send_command('iq_setup', {
                'channel': 'iq0',
                'frequency': 25e6,
                'bandwidth': 1000.0,
                'input': input_source,
                'output_direct': 'off'
            }, timeout=5.0)
            
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"Input {input_source}: OK")
    
    def test_no_memory_leaks(self, shared_manager_mock):
        """Test that many IQ reads don't leak memory."""
        mgr = shared_manager_mock
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        num_reads = 100
        for i in range(num_reads):
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            
            if i % 20 == 0:
                print(f"Completed {i}/{num_reads} IQ reads")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
