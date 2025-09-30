#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for PyRPL IPC integration.

This script tests the complete IPC architecture:
1. Worker process startup
2. Command/response communication
3. Mock mode functionality
4. Error handling
5. Graceful shutdown

Run with: python tests/test_ipc_integration.py
"""

import time
import multiprocessing
from multiprocessing import Queue
from queue import Empty

from pymodaq_plugins_pyrpl.utils.pyrpl_ipc_worker import pyrpl_worker_main


def test_mock_mode():
    """Test worker in mock mode (no hardware required)."""
    print("\n" + "="*60)
    print("TEST 1: Mock Mode Worker")
    print("="*60)
    
    cmd_queue = Queue()
    resp_queue = Queue()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test',
        'mock_mode': True
    }
    
    # Start worker process
    print("Starting worker process...")
    worker = multiprocessing.Process(
        target=pyrpl_worker_main,
        args=(cmd_queue, resp_queue, config),
        daemon=True
    )
    worker.start()
    
    try:
        # Wait for initialization
        print("Waiting for initialization...")
        response = resp_queue.get(timeout=10.0)
        assert response['status'] == 'ok', f"Init failed: {response}"
        print(f"✓ Worker initialized: {response['data']}")
        
        # Test ping
        print("\nTesting ping...")
        cmd_queue.put({'command': 'ping', 'params': {}})
        response = resp_queue.get(timeout=2.0)
        assert response['status'] == 'ok', f"Ping failed: {response}"
        assert response['data'] == 'pong', f"Wrong ping response: {response['data']}"
        print("✓ Ping successful")
        
        # Test scope acquisition
        print("\nTesting scope acquisition...")
        cmd_queue.put({
            'command': 'scope_acquire',
            'params': {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }
        })
        response = resp_queue.get(timeout=7.0)
        assert response['status'] == 'ok', f"Acquisition failed: {response}"
        
        data = response['data']
        assert 'voltage' in data, "No voltage data"
        assert 'time' in data, "No time data"
        assert len(data['voltage']) > 0, "Empty voltage data"
        assert len(data['time']) == len(data['voltage']), "Mismatched data lengths"
        
        print(f"✓ Acquired {len(data['voltage'])} data points")
        print(f"  Time span: {data['time'][0]:.6f} to {data['time'][-1]:.6f} s")
        print(f"  Voltage range: {min(data['voltage']):.3f} to {max(data['voltage']):.3f} V")
        
        # Test configuration commands
        print("\nTesting configuration commands...")
        
        # Decimation
        cmd_queue.put({
            'command': 'scope_set_decimation',
            'params': {'value': 128}
        })
        response = resp_queue.get(timeout=2.0)
        assert response['status'] == 'ok', f"Set decimation failed: {response}"
        print("✓ Decimation set")
        
        # Trigger source
        cmd_queue.put({
            'command': 'scope_set_trigger',
            'params': {'source': 'ch1_positive_edge'}
        })
        response = resp_queue.get(timeout=2.0)
        assert response['status'] == 'ok', f"Set trigger failed: {response}"
        print("✓ Trigger source set")
        
        # Test PID commands
        print("\nTesting PID commands...")
        cmd_queue.put({
            'command': 'pid_configure',
            'params': {
                'channel': 'pid0',
                'p': 0.1,
                'i': 10.0,
                'setpoint': 0.5
            }
        })
        response = resp_queue.get(timeout=2.0)
        assert response['status'] == 'ok', f"PID configure failed: {response}"
        print("✓ PID configured")
        
        # Test unknown command
        print("\nTesting error handling...")
        cmd_queue.put({
            'command': 'invalid_command',
            'params': {}
        })
        response = resp_queue.get(timeout=2.0)
        assert response['status'] == 'error', "Should return error for invalid command"
        print(f"✓ Error handling works: {response['data']}")
        
        # Test shutdown
        print("\nTesting graceful shutdown...")
        cmd_queue.put({'command': 'shutdown', 'params': {}})
        
        # Worker should exit gracefully
        worker.join(timeout=5.0)
        if worker.is_alive():
            print("✗ Worker did not shutdown gracefully")
            worker.terminate()
            worker.join()
        else:
            print("✓ Worker shutdown gracefully")
        
        print("\n" + "="*60)
        print("TEST 1 PASSED: All mock mode tests successful")
        print("="*60)
        
        return True
        
    except Empty:
        print("✗ TIMEOUT: No response from worker")
        return False
        
    except AssertionError as e:
        print(f"✗ ASSERTION FAILED: {e}")
        return False
        
    except Exception as e:
        print(f"✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Ensure cleanup
        if worker.is_alive():
            worker.terminate()
            worker.join()


def test_process_lifecycle():
    """Test worker process lifecycle management."""
    print("\n" + "="*60)
    print("TEST 2: Process Lifecycle")
    print("="*60)
    
    cmd_queue = Queue()
    resp_queue = Queue()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test',
        'mock_mode': True
    }
    
    # Start worker
    print("Starting worker...")
    worker = multiprocessing.Process(
        target=pyrpl_worker_main,
        args=(cmd_queue, resp_queue, config),
        daemon=True
    )
    worker.start()
    
    try:
        # Wait for init
        response = resp_queue.get(timeout=10.0)
        assert response['status'] == 'ok'
        print("✓ Worker started")
        
        # Verify process is alive
        assert worker.is_alive(), "Worker process died unexpectedly"
        print("✓ Worker process is alive")
        
        # Send shutdown
        cmd_queue.put({'command': 'shutdown', 'params': {}})
        
        # Wait for graceful exit
        worker.join(timeout=5.0)
        
        if not worker.is_alive():
            print("✓ Worker terminated gracefully")
        else:
            print("✗ Worker did not terminate")
            worker.terminate()
            worker.join()
            return False
        
        # Check exit code
        if worker.exitcode == 0:
            print("✓ Worker exit code is 0 (clean exit)")
        else:
            print(f"⚠ Worker exit code: {worker.exitcode}")
        
        print("\n" + "="*60)
        print("TEST 2 PASSED: Process lifecycle management works")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join()


def test_stress():
    """Stress test with rapid commands."""
    print("\n" + "="*60)
    print("TEST 3: Stress Test (Rapid Commands)")
    print("="*60)
    
    cmd_queue = Queue()
    resp_queue = Queue()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test',
        'mock_mode': True
    }
    
    # Start worker
    print("Starting worker...")
    worker = multiprocessing.Process(
        target=pyrpl_worker_main,
        args=(cmd_queue, resp_queue, config),
        daemon=True
    )
    worker.start()
    
    try:
        # Wait for init
        response = resp_queue.get(timeout=10.0)
        assert response['status'] == 'ok'
        print("✓ Worker started")
        
        # Send many rapid commands
        num_commands = 50
        print(f"\nSending {num_commands} rapid ping commands...")
        
        start_time = time.time()
        
        for i in range(num_commands):
            cmd_queue.put({'command': 'ping', 'params': {}})
        
        # Receive all responses
        success_count = 0
        for i in range(num_commands):
            response = resp_queue.get(timeout=5.0)
            if response['status'] == 'ok' and response['data'] == 'pong':
                success_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"✓ Received {success_count}/{num_commands} responses")
        print(f"  Time: {elapsed:.3f}s ({num_commands/elapsed:.1f} commands/s)")
        
        assert success_count == num_commands, f"Lost {num_commands - success_count} responses"
        
        # Shutdown
        cmd_queue.put({'command': 'shutdown', 'params': {}})
        worker.join(timeout=5.0)
        
        print("\n" + "="*60)
        print("TEST 3 PASSED: Stress test successful")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*12 + "PyRPL IPC Integration Test Suite" + " "*13 + "║")
    print("╚" + "="*58 + "╝")
    
    results = []
    
    # Run tests
    results.append(("Mock Mode Worker", test_mock_mode()))
    results.append(("Process Lifecycle", test_process_lifecycle()))
    results.append(("Stress Test", test_stress()))
    
    # Summary
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*21 + "TEST SUMMARY" + " "*25 + "║")
    print("╠" + "="*58 + "╣")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        padding = " " * (40 - len(name))
        print(f"║  {name}{padding}{status}  ║")
        if not passed:
            all_passed = False
    
    print("╚" + "="*58 + "╝")
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! IPC integration is working correctly.\n")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED. Please review the output above.\n")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
