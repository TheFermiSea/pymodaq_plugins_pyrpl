"""
Mock Mode Tests for PyRPL ASG IPC Plugin

Tests Arbitrary Signal Generator (ASG) functionality through SharedPyRPLManager.
No hardware required - runs in mock mode.

Tests cover:
- ASG setup and configuration
- Different waveform types
- Frequency, amplitude, offset settings
- Multiple ASG channels
- Concurrent operations
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
        'config_name': 'test_asg_mock',
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


class TestASGIPCMock:
    """Test ASG (Arbitrary Signal Generator) via SharedPyRPLManager in mock mode."""
    
    def test_asg_setup_basic(self, shared_manager_mock):
        """Test basic ASG configuration."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_asg_different_waveforms(self, shared_manager_mock):
        """Test different waveform types."""
        mgr = shared_manager_mock
        
        waveforms = ['sin', 'square', 'triangle', 'dc']
        
        for waveform in waveforms:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': waveform,
                'frequency': 1000.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG waveform '{waveform}': OK")
    
    def test_asg_frequency_range(self, shared_manager_mock):
        """Test different frequency values."""
        mgr = shared_manager_mock
        
        frequencies = [100.0, 1000.0, 10000.0, 100000.0, 1e6, 10e6]
        
        for freq in frequencies:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': freq,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG frequency {freq/1e3:.1f} kHz: OK")
    
    def test_asg_amplitude_settings(self, shared_manager_mock):
        """Test different amplitude values."""
        mgr = shared_manager_mock
        
        amplitudes = [0.1, 0.25, 0.5, 0.75, 1.0]
        
        for amp in amplitudes:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0,
                'amplitude': amp,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG amplitude {amp:.2f} V: OK")
    
    def test_asg_offset_settings(self, shared_manager_mock):
        """Test different offset values."""
        mgr = shared_manager_mock
        
        offsets = [-1.0, -0.5, 0.0, 0.5, 1.0]
        
        for offset in offsets:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0,
                'amplitude': 0.5,
                'offset': offset,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG offset {offset:+.2f} V: OK")
    
    def test_multiple_asg_channels(self, shared_manager_mock):
        """Test both ASG channels (asg0 and asg1)."""
        mgr = shared_manager_mock
        
        for i, channel in enumerate(['asg0', 'asg1']):
            response = mgr.send_command('asg_setup', {
                'channel': channel,
                'waveform': 'sin',
                'frequency': 1000.0 + i * 500.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"{channel}: OK")
    
    def test_concurrent_asg_operations(self, shared_manager_mock):
        """Test concurrent ASG setups from multiple threads."""
        mgr = shared_manager_mock
        
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
                }, timeout=5.0)
                
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=setup_asg, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        
        print(f"Concurrent ASG operations: {len(results)}/10 succeeded")
    
    def test_asg_trigger_sources(self, shared_manager_mock):
        """Test different trigger sources."""
        mgr = shared_manager_mock
        
        triggers = ['immediately', 'ext_positive_edge', 'ext_negative_edge']
        
        for trigger in triggers:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': trigger
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG trigger '{trigger}': OK")
    
    def test_rapid_asg_updates(self, shared_manager_mock):
        """Test rapid successive ASG updates."""
        mgr = shared_manager_mock
        
        start_time = time.time()
        num_updates = 50
        
        for i in range(num_updates):
            freq = 1000.0 + (i % 10) * 100.0
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': freq,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_updates} ASG updates in {duration:.2f}s ({num_updates/duration:.1f} Hz)")
    
    def test_asg_all_parameters_varied(self, shared_manager_mock):
        """Test varying all ASG parameters simultaneously."""
        mgr = shared_manager_mock
        
        configs = [
            {'waveform': 'sin', 'frequency': 1000.0, 'amplitude': 0.5, 'offset': 0.0},
            {'waveform': 'square', 'frequency': 2000.0, 'amplitude': 0.3, 'offset': 0.1},
            {'waveform': 'triangle', 'frequency': 5000.0, 'amplitude': 0.7, 'offset': -0.2},
            {'waveform': 'dc', 'frequency': 0.0, 'amplitude': 0.0, 'offset': 0.5},
        ]
        
        for config in configs:
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': config['waveform'],
                'frequency': config['frequency'],
                'amplitude': config['amplitude'],
                'offset': config['offset'],
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            print(f"ASG config {config['waveform']}, {config['frequency']:.0f} Hz, "
                  f"{config['amplitude']:.2f} V, {config['offset']:+.2f} V: OK")
    
    def test_no_memory_leaks(self, shared_manager_mock):
        """Test that many ASG operations don't leak memory."""
        mgr = shared_manager_mock
        
        num_operations = 100
        for i in range(num_operations):
            response = mgr.send_command('asg_setup', {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0 + (i % 50) * 100.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            
            if i % 20 == 0:
                print(f"Completed {i}/{num_operations} ASG operations")
        
        # Verify no pending responses
        assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
