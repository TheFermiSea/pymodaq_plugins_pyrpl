#!/usr/bin/env python
"""
Hardware tests for PID module with command multiplexing.

Tests that PID configuration and operations work correctly with real hardware
and that concurrent PID operations are properly multiplexed.
"""
import pytest
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def hardware_manager():
    """Fixture providing hardware connection for all tests."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_pid_hardware',
        'mock_mode': False
    }
    
    print("\n[Hardware Test] Connecting to Red Pitaya...")
    mgr.start_worker(config)
    time.sleep(5.0)  # Wait for connection
    print("[Hardware Test] Connected successfully to 100.107.106.75")
    
    yield mgr
    
    print("\n[Hardware Test] Shutting down hardware connection...")
    mgr.shutdown()
    time.sleep(2.0)


def test_pid_configure_hardware(hardware_manager):
    """Test PID configuration with real hardware."""
    print("\n[Test] Configuring PID0...")
    
    # Configure PID with basic parameters
    # NOTE: Avoid 'i' and 'd' parameters due to PyRPL bug (ZeroDivisionError)
    config = {
        'channel': 'pid0',
        'p': 0.1,
        # 'i': 10.0,  # Skip - causes ZeroDivisionError in PyRPL
        'setpoint': 0.5,
        'input': 'in1',
        'output_direct': 'out1'
    }
    
    response = hardware_manager.send_command('pid_configure', config, timeout=10.0)
    
    assert response['status'] == 'ok', f"PID configure failed: {response}"
    print(f"[Test] PID0 configured successfully (P-only control)")


def test_pid_setpoint_readback_hardware(hardware_manager):
    """Test setting and reading PID setpoint."""
    print("\n[Test] Testing PID setpoint read/write...")
    
    # Set setpoint
    test_setpoint = 0.75
    response = hardware_manager.send_command(
        'pid_set_setpoint',
        {'channel': 'pid0', 'value': test_setpoint},
        timeout=10.0
    )
    assert response['status'] == 'ok'
    print(f"[Test] Set PID0 setpoint to {test_setpoint}")
    
    # Read it back
    response = hardware_manager.send_command(
        'pid_get_setpoint',
        {'channel': 'pid0'},
        timeout=10.0
    )
    assert response['status'] == 'ok'
    readback = response['data']
    
    print(f"[Test] Read back setpoint: {readback}")
    assert abs(readback - test_setpoint) < 0.001, f"Setpoint mismatch: {readback} != {test_setpoint}"


def test_pid_multiple_channels_hardware(hardware_manager):
    """Test configuring multiple PID channels."""
    print("\n[Test] Configuring multiple PID channels...")
    
    # Use P-only control to avoid PyRPL bug with 'i' parameter
    configs = [
        {
            'channel': 'pid0',
            'p': 0.1,
            # 'i': 10.0,  # Skip due to PyRPL bug
            'setpoint': 0.3
        },
        {
            'channel': 'pid1',
            'p': 0.2,
            # 'i': 20.0,
            'setpoint': 0.6
        },
        {
            'channel': 'pid2',
            'p': 0.15,
            # 'i': 15.0,
            'setpoint': 0.45
        }
    ]
    
    # Configure all PIDs
    for config in configs:
        response = hardware_manager.send_command('pid_configure', config, timeout=10.0)
        assert response['status'] == 'ok'
        print(f"[Test] Configured {config['channel']}")
    
    # Read back all setpoints
    for config in configs:
        response = hardware_manager.send_command(
            'pid_get_setpoint',
            {'channel': config['channel']},
            timeout=10.0
        )
        assert response['status'] == 'ok'
        readback = response['data']
        expected = config['setpoint']
        print(f"[Test] {config['channel']} setpoint: {readback}")
        assert abs(readback - expected) < 0.001


def test_concurrent_pid_operations_hardware(hardware_manager):
    """Test concurrent PID operations with command multiplexing."""
    print("\n[Test] Testing concurrent PID operations...")
    
    import threading
    import queue
    
    results = queue.Queue()
    
    def configure_and_read(channel, setpoint):
        """Configure PID and read back setpoint."""
        try:
            # Configure (P-only due to PyRPL bug)
            config = {
                'channel': channel,
                'p': 0.1,
                # 'i': 10.0,  # Skip due to PyRPL bug
                'setpoint': setpoint
            }
            resp1 = hardware_manager.send_command('pid_configure', config, timeout=10.0)
            
            # Small delay
            time.sleep(0.1)
            
            # Read back
            resp2 = hardware_manager.send_command(
                'pid_get_setpoint',
                {'channel': channel},
                timeout=10.0
            )
            
            results.put({
                'channel': channel,
                'configure_status': resp1['status'],
                'read_status': resp2['status'],
                'setpoint': resp2.get('data')
            })
        except Exception as e:
            results.put({'channel': channel, 'error': str(e)})
    
    # Start concurrent operations
    threads = []
    test_configs = [
        ('pid0', 0.2),
        ('pid1', 0.4),
        ('pid2', 0.6)
    ]
    
    start_time = time.time()
    
    for channel, setpoint in test_configs:
        t = threading.Thread(target=configure_and_read, args=(channel, setpoint))
        t.start()
        threads.append(t)
    
    # Wait for all to complete
    for t in threads:
        t.join()
    
    duration = time.time() - start_time
    print(f"[Test] All concurrent PID operations completed in {duration:.2f}s")
    
    # Verify all results
    result_list = []
    while not results.empty():
        result_list.append(results.get())
    
    assert len(result_list) == 3, f"Expected 3 results, got {len(result_list)}"
    
    for result in result_list:
        print(f"[Test] {result['channel']}: {result}")
        assert 'error' not in result, f"Error in {result['channel']}: {result.get('error')}"
        assert result['configure_status'] == 'ok'
        assert result['read_status'] == 'ok'
        assert result['setpoint'] is not None
    
    print("[Test] ✓ All concurrent PID operations succeeded")


def test_pid_with_sampler_concurrent_hardware(hardware_manager):
    """Test concurrent PID configuration and voltage sampling."""
    print("\n[Test] Testing PID + sampler concurrent operations...")
    
    import threading
    import queue
    
    results = queue.Queue()
    
    def configure_pid():
        """Configure PID."""
        try:
            config = {
                'channel': 'pid0',
                'p': 0.1,
                # 'i': 10.0,  # Skip due to PyRPL bug
                'setpoint': 0.5
            }
            resp = hardware_manager.send_command('pid_configure', config, timeout=10.0)
            results.put({'type': 'pid', 'status': resp['status']})
        except Exception as e:
            results.put({'type': 'pid', 'error': str(e)})
    
    def read_voltages():
        """Read voltages from both inputs."""
        try:
            voltages = []
            for channel in ['in1', 'in2']:
                resp = hardware_manager.send_command(
                    'sampler_read',
                    {'channel': channel},
                    timeout=10.0
                )
                voltages.append(resp['data'])
            results.put({'type': 'sampler', 'status': 'ok', 'voltages': voltages})
        except Exception as e:
            results.put({'type': 'sampler', 'error': str(e)})
    
    # Run concurrently
    threads = [
        threading.Thread(target=configure_pid),
        threading.Thread(target=read_voltages)
    ]
    
    start_time = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start_time
    
    print(f"[Test] Concurrent PID + sampler completed in {duration:.2f}s")
    
    # Verify results
    result_list = []
    while not results.empty():
        result_list.append(results.get())
    
    assert len(result_list) == 2
    
    for result in result_list:
        print(f"[Test] {result['type']}: {result}")
        assert 'error' not in result
        assert result['status'] == 'ok'
    
    print("[Test] ✓ Concurrent PID + sampler succeeded")


if __name__ == '__main__':
    pytest.main([__file__, '-xvs'])
