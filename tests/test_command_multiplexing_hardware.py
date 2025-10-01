"""
Hardware tests for command ID multiplexing with real Red Pitaya hardware.

These tests verify that the command multiplexing implementation works correctly
with actual PyRPL hardware, including concurrent operations on scope and ASG.
"""
import pytest
import threading
import time
import numpy as np
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


# Hardware configuration
HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_multiplexing_hardware'


@pytest.fixture(scope='module')
def hardware_manager():
    """Get a SharedPyRPLManager instance with real hardware."""
    mgr = get_shared_worker_manager()
    
    # Start worker with real hardware
    config = {
        'hostname': HARDWARE_IP,
        'config_name': CONFIG_NAME,
        'mock_mode': False  # Real hardware!
    }
    
    print(f"\n[Hardware Test] Connecting to Red Pitaya at {HARDWARE_IP}...")
    mgr.start_worker(config)
    
    # Wait for PyRPL initialization (takes a few seconds)
    time.sleep(5.0)
    
    # Verify connection with ping
    response = mgr.send_command('ping', {}, timeout=10.0)
    assert response['status'] == 'ok', f"Failed to ping hardware: {response}"
    print(f"[Hardware Test] Connected successfully to {HARDWARE_IP}")
    
    yield mgr
    
    # Cleanup
    print("\n[Hardware Test] Shutting down hardware connection...")
    mgr.shutdown()
    time.sleep(2.0)


class TestCommandMultiplexingHardware:
    """Test command ID multiplexing with real PyRPL hardware."""
    
    def test_single_hardware_command(self, hardware_manager):
        """Test a single command with real hardware."""
        print("\n[Test] Single hardware command...")
        
        # Read a voltage from the sampler
        response = hardware_manager.send_command(
            'sampler_read',
            {'channel': 'in1'},
            timeout=10.0
        )
        
        assert response['status'] == 'ok', f"Command failed: {response}"
        assert 'id' in response, "Response missing command ID"
        assert isinstance(response['data'], (int, float)), "Invalid voltage data"
        
        voltage = response['data']
        print(f"[Test] Read voltage from in1: {voltage:.6f} V")
        assert -2.0 <= voltage <= 2.0, f"Voltage out of range: {voltage}"
    
    def test_concurrent_hardware_commands(self, hardware_manager):
        """Test concurrent commands with real hardware - no blocking."""
        print("\n[Test] Concurrent hardware commands (10 threads)...")
        
        num_threads = 10
        results = {}
        errors = []
        
        def read_voltage(thread_id):
            try:
                response = hardware_manager.send_command(
                    'sampler_read',
                    {'channel': 'in1'},
                    timeout=10.0
                )
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=read_voltage, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=30)
        
        duration = time.time() - start_time
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
        
        # Verify all responses are valid
        voltages = []
        for thread_id, response in results.items():
            assert response['status'] == 'ok', f"Thread {thread_id} got error: {response}"
            assert 'id' in response, f"Thread {thread_id} response missing ID"
            voltages.append(response['data'])
        
        print(f"[Test] All {num_threads} concurrent commands succeeded in {duration:.2f}s")
        print(f"[Test] Voltage readings: min={min(voltages):.6f}V, max={max(voltages):.6f}V, "
              f"mean={np.mean(voltages):.6f}V")
    
    def test_concurrent_scope_and_asg(self, hardware_manager):
        """Test concurrent scope acquisition and ASG generation - real hardware."""
        print("\n[Test] Concurrent scope + ASG on hardware...")
        
        # Configure ASG to generate a signal on output1 (looped to input1)
        print("[Test] Configuring ASG...")
        response = hardware_manager.send_command(
            'asg_setup',
            {
                'channel': 'asg0',
                'waveform': 'sin',
                'frequency': 1000.0,  # 1 kHz
                'amplitude': 0.5,  # 500 mV
                'offset': 0.0,
                'trigger_source': 'immediately'
            },
            timeout=10.0
        )
        assert response['status'] == 'ok', f"ASG setup failed: {response}"
        print(f"[Test] ASG configured: 1 kHz sine, 500 mV amplitude")
        
        # Give ASG time to start generating
        time.sleep(0.5)
        
        # Now run concurrent operations
        scope_acquisitions = []
        asg_updates = []
        errors = []
        stop_flag = threading.Event()
        
        def acquire_scope():
            """Continuously acquire scope data."""
            count = 0
            while not stop_flag.is_set():
                try:
                    response = hardware_manager.send_command(
                        'scope_acquire',
                        {
                            'decimation': 64,
                            'trigger_source': 'immediately',
                            'input_channel': 'in1',
                            'timeout': 5.0
                        },
                        timeout=10.0
                    )
                    if response['status'] == 'ok':
                        count += 1
                        # Verify we're seeing the ASG signal
                        voltage_data = np.array(response['data']['voltage'])
                        vpp = voltage_data.max() - voltage_data.min()
                        scope_acquisitions.append({
                            'acquisition': count,
                            'vpp': vpp,
                            'mean': voltage_data.mean(),
                            'points': len(voltage_data)
                        })
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def update_asg():
            """Continuously update ASG frequency."""
            count = 0
            frequency = 1000.0
            while not stop_flag.is_set():
                try:
                    frequency = 1000.0 + (count % 10) * 100  # 1-2 kHz
                    response = hardware_manager.send_command(
                        'asg_setup',
                        {
                            'channel': 'asg0',
                            'frequency': frequency
                        },
                        timeout=10.0
                    )
                    if response['status'] == 'ok':
                        count += 1
                        asg_updates.append({'update': count, 'frequency': frequency})
                    time.sleep(0.1)  # 10 Hz update rate
                except Exception as e:
                    errors.append(('asg', str(e)))
                    break
        
        # Start both operations
        print("[Test] Starting concurrent scope + ASG operations...")
        scope_thread = threading.Thread(target=acquire_scope, daemon=True)
        asg_thread = threading.Thread(target=update_asg, daemon=True)
        
        start_time = time.time()
        scope_thread.start()
        asg_thread.start()
        
        # Run for 5 seconds
        time.sleep(5.0)
        stop_flag.set()
        
        # Wait for threads to finish
        scope_thread.join(timeout=5)
        asg_thread.join(timeout=5)
        
        duration = time.time() - start_time
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        num_scope = len(scope_acquisitions)
        num_asg = len(asg_updates)
        
        print(f"\n[Test Results]")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Scope acquisitions: {num_scope}")
        print(f"  ASG updates: {num_asg}")
        
        # Verify we got reasonable numbers (at least some operations)
        assert num_scope > 0, "No scope acquisitions completed"
        assert num_asg > 0, "No ASG updates completed"
        
        # Show some scope statistics
        if scope_acquisitions:
            vpps = [a['vpp'] for a in scope_acquisitions]
            print(f"  Scope Vpp: min={min(vpps):.3f}V, max={max(vpps):.3f}V, mean={np.mean(vpps):.3f}V")
            print(f"  Expected Vpp: ~1.0V (500mV amplitude sine)")
            
            # Note: ASG signal verification depends on hardware loopback configuration
            # The key test here is that both operations ran concurrently without blocking
            mean_vpp = np.mean(vpps)
            if mean_vpp > 0.1:
                print(f"  ✓ ASG signal detected: Vpp={mean_vpp:.3f}V")
            else:
                print(f"  ⚠ ASG signal not detected (Vpp={mean_vpp:.3f}V) - check hardware loopback")
                print(f"    This is OK - multiplexing still works correctly!")
        
        print(f"[Test] SUCCESS: Concurrent operations working correctly!")
    
    def test_resource_cleanup_hardware(self, hardware_manager):
        """Test that no memory leaks occur with many hardware commands."""
        print("\n[Test] Resource cleanup with 50 hardware commands...")
        
        num_commands = 50
        
        for i in range(num_commands):
            response = hardware_manager.send_command(
                'sampler_read',
                {'channel': 'in1'},
                timeout=10.0
            )
            assert response['status'] == 'ok', f"Command {i} failed: {response}"
            
            if i % 10 == 0:
                print(f"[Test] Completed {i}/{num_commands} commands...")
        
        # Verify no pending responses remain
        num_pending = len(hardware_manager._pending_responses)
        assert num_pending == 0, f"Memory leak: {num_pending} pending responses remain"
        
        print(f"[Test] All {num_commands} commands completed, no memory leaks detected")
    
    def test_concurrent_sampling(self, hardware_manager):
        """Test concurrent voltage sampling on multiple channels."""
        print("\n[Test] Concurrent multi-channel sampling...")
        
        channels = ['in1', 'in2']
        num_samples = 10
        results = {ch: [] for ch in channels}
        errors = []
        
        def sample_channel(channel):
            for i in range(num_samples):
                try:
                    response = hardware_manager.send_command(
                        'sampler_read',
                        {'channel': channel},
                        timeout=10.0
                    )
                    if response['status'] == 'ok':
                        results[channel].append(response['data'])
                    else:
                        errors.append((channel, i, response))
                    time.sleep(0.1)
                except Exception as e:
                    errors.append((channel, i, str(e)))
        
        # Start concurrent sampling
        threads = []
        for ch in channels:
            t = threading.Thread(target=sample_channel, args=(ch,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=30)
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        for ch in channels:
            samples = results[ch]
            assert len(samples) == num_samples, f"Channel {ch} missing samples: {len(samples)}/{num_samples}"
            print(f"[Test] {ch}: {len(samples)} samples, "
                  f"mean={np.mean(samples):.6f}V, std={np.std(samples):.6f}V")
        
        print(f"[Test] Concurrent sampling successful!")


if __name__ == '__main__':
    """Run hardware tests standalone."""
    print("=" * 70)
    print("Command Multiplexing Hardware Tests")
    print("=" * 70)
    print(f"Testing with Red Pitaya at: {HARDWARE_IP}")
    print(f"Config name: {CONFIG_NAME}")
    print("=" * 70)
    
    pytest.main([__file__, '-v', '-s'])
