"""
Hardware Tests for PyRPL ASG IPC Plugin

Tests Arbitrary Signal Generator (ASG) with REAL Red Pitaya hardware.
Requires: PYRPL_TEST_HOST=100.107.106.75

Run with: pytest tests/test_plugin_ipc_asg_hardware.py -v -s
"""
import pytest
import time
import threading
import numpy as np
import os

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Hardware configuration
HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_asg_hardware'

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


class TestASGIPCHardware:
    """Test ASG (Arbitrary Signal Generator) with real Red Pitaya hardware."""
    
    def test_hardware_asg_setup(self, shared_manager_hardware):
        """Test basic ASG configuration with real hardware."""
        mgr = shared_manager_hardware
        
        response = mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
    
    def test_hardware_asg_different_waveforms(self, shared_manager_hardware):
        """Test different waveform types on hardware."""
        mgr = shared_manager_hardware
        
        waveforms = ['sin', 'square', 'triangle', 'dc']
        
        for waveform in waveforms:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': waveform,
                'frequency': 1000.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            print(f"Hardware ASG waveform '{waveform}': OK")
            time.sleep(0.1)  # Small delay between hardware changes
    
    def test_hardware_asg_frequency_range(self, shared_manager_hardware):
        """Test different frequency values on hardware."""
        mgr = shared_manager_hardware
        
        frequencies = [100.0, 1000.0, 10000.0, 100000.0, 1e6]
        
        for freq in frequencies:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': freq,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            print(f"Hardware ASG frequency {freq/1e3:.1f} kHz: OK")
            time.sleep(0.1)
    
    def test_hardware_asg_both_channels(self, shared_manager_hardware):
        """Test both ASG channels on hardware."""
        mgr = shared_manager_hardware
        
        for i, channel in enumerate(['asg0', 'asg1']):
            response = mgr.send_command('asg_setup', {
                'channel': channel,
                'waveform': 'sin',
                'frequency': 1000.0 + i * 500.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=10.0)
            
            assert response['status'] == 'ok'
            print(f"Hardware {channel}: OK")
    
    def test_hardware_concurrent_asg_operations(self, shared_manager_hardware):
        """Test concurrent ASG operations on hardware."""
        mgr = shared_manager_hardware
        
        results = {}
        errors = []
        
        def setup_asg(thread_id):
            try:
                channel = 'asg0' if thread_id % 2 == 0 else 'asg1'
                freq = 1000.0 + thread_id * 100.0
                
                response = mgr.send_command('asg_setup', {
                    'channel': channel,
                    'waveform': 'sin',
                    'frequency': freq,
                    'amplitude': 0.5,
                    'offset': 0.0,
                    'trigger_source': 'immediately'
                }, timeout=15.0)
                
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(6):
            t = threading.Thread(target=setup_asg, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 6
        
        print(f"Concurrent hardware ASG operations: {len(results)}/6 succeeded")
    
    def test_hardware_asg_loopback_verification(self, shared_manager_hardware):
        """Test ASG output by reading back via scope (loopback)."""
        mgr = shared_manager_hardware
        
        # Setup ASG to generate signal on output2
        mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 10000.0,  # 10 kHz
            'amplitude': 0.8,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=10.0)
        
        # Wait for signal to stabilize
        time.sleep(0.5)
        
        # Read back via scope on input2 (loopback: output2 → input2)
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in2',
            'timeout': 5.0
        }, timeout=15.0)
        
        assert response['status'] == 'ok'
        voltage = np.array(response['data']['voltage'])
        
        # Verify signal has reasonable amplitude (should see ~0.8V amplitude)
        signal_range = voltage.max() - voltage.min()
        print(f"ASG loopback: Signal range = {signal_range:.3f} V (expected ~1.6V peak-to-peak)")
        
        # Should have significant signal (not just noise)
        assert signal_range > 0.5, "ASG signal too weak in loopback test"
    
    def test_hardware_rapid_asg_updates(self, shared_manager_hardware):
        """Test rapid successive ASG updates on hardware."""
        mgr = shared_manager_hardware
        
        start_time = time.time()
        num_updates = 20
        
        for i in range(num_updates):
            freq = 1000.0 + (i % 5) * 1000.0
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': freq,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=15.0)
            
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_updates} hardware ASG updates in {duration:.2f}s ({num_updates/duration:.1f} Hz)")
    
    def test_hardware_no_memory_leaks(self, shared_manager_hardware):
        """Test that hardware ASG operations don't leak memory."""
        mgr = shared_manager_hardware
        
        num_operations = 30
        for i in range(num_operations):
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0 + (i % 10) * 1000.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=15.0)
            
            assert response['status'] == 'ok'
            
            if i % 10 == 0:
                print(f"Completed {i}/{num_operations} hardware ASG operations")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
