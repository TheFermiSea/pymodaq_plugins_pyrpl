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
        'config_name': 'test_concurrent',
        'mock_mode': True
    }
    mgr.start_worker(config)
    
    # Wait for worker to initialize
    time.sleep(0.5)
    
    yield mgr
    
    # Cleanup
    mgr.shutdown()
    time.sleep(0.5)


def test_scope_and_asg_concurrent(manager):
    """
    Test concurrent scope acquisition and ASG parameter updates.
    
    This simulates a realistic experimental scenario where:
    - Scope continuously acquires data (~50 ms cadence)
    - ASG parameters are updated concurrently (~100 ms cadence)
    - Both operations should proceed without blocking or interference
    """
    duration = 5.0  # seconds
    scope_cadence = 0.05  # 50 ms
    asg_cadence = 0.1  # 100 ms
    
    scope_count = 0
    asg_count = 0
    scope_errors = []
    asg_errors = []
    stop_event = threading.Event()
    
    def scope_acquisition_loop():
        """Continuously acquire scope data."""
        nonlocal scope_count
        while not stop_event.is_set():
            try:
                response = manager.send_command('scope_acquire', {
                    'decimation': 64,
                    'trigger_source': 'immediately',
                    'input_channel': 'in1'
                }, timeout=5.0)
                
                assert response['status'] == 'ok'
                assert 'data' in response
                assert 'voltage' in response['data']
                assert 'time' in response['data']
                
                scope_count += 1
                time.sleep(scope_cadence)
                
            except Exception as e:
                scope_errors.append(str(e))
                break
    
    def asg_update_loop():
        """Continuously update ASG parameters."""
        nonlocal asg_count
        frequency = 1000.0  # Start at 1 kHz
        
        while not stop_event.is_set():
            try:
                response = manager.send_command('asg_setup', {
                    'channel': 'asg0',
                    'waveform': 'sine',
                    'frequency': frequency,
                    'amplitude': 0.5,
                    'offset': 0.0
                }, timeout=5.0)
                
                assert response['status'] == 'ok'
                
                asg_count += 1
                frequency += 100.0  # Increment frequency
                time.sleep(asg_cadence)
                
            except Exception as e:
                asg_errors.append(str(e))
                break
    
    # Start both loops
    scope_thread = threading.Thread(target=scope_acquisition_loop)
    asg_thread = threading.Thread(target=asg_update_loop)
    
    scope_thread.start()
    asg_thread.start()
    
    # Run for specified duration
    time.sleep(duration)
    stop_event.set()
    
    # Wait for threads to finish
    scope_thread.join(timeout=2)
    asg_thread.join(timeout=2)
    
    # Calculate expected counts (with tolerance for timing variance)
    expected_scope_count = int(duration / scope_cadence)
    expected_asg_count = int(duration / asg_cadence)
    
    tolerance = 0.2  # 20% tolerance
    
    # Verify results
    assert len(scope_errors) == 0, f"Scope errors: {scope_errors}"
    assert len(asg_errors) == 0, f"ASG errors: {asg_errors}"
    
    assert scope_count >= expected_scope_count * (1 - tolerance), \
        f"Scope count too low: {scope_count} vs expected ~{expected_scope_count}"
    
    assert asg_count >= expected_asg_count * (1 - tolerance), \
        f"ASG count too low: {asg_count} vs expected ~{expected_asg_count}"
    
    print(f"\nConcurrent operation successful:")
    print(f"  Scope acquisitions: {scope_count} (expected ~{expected_scope_count})")
    print(f"  ASG updates: {asg_count} (expected ~{expected_asg_count})")
    print(f"  Duration: {duration}s")
    print(f"  No blocking or interference detected!")
