"""
Multi-Plugin Coordination Tests

Tests that multiple IPC plugins can operate concurrently through
the SharedPyRPLManager without blocking or cross-talk.

This validates the core command multiplexing architecture by running
Scope, IQ, PID, and ASG plugins simultaneously.
"""
import pytest
import time
import threading

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager for multi-plugin tests."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_multi_plugin',
        'mock_mode': True
    }
    
    print("\n[Setup] Starting shared worker for multi-plugin tests...")
    mgr.start_worker(config)
    time.sleep(1.0)
    
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok'
    
    yield mgr
    
    print("\n[Teardown] Shutting down shared worker...")
    mgr.shutdown()
    time.sleep(1.0)


class TestMultiPluginCoordination:
    """Test concurrent operation of multiple plugin types."""
    
    def test_scope_and_asg_concurrent(self, shared_manager_mock):
        """Test Scope and ASG running simultaneously."""
        mgr = shared_manager_mock
        
        # Setup ASG to generate signal
        mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=5.0)
        
        scope_results = []
        asg_updates = []
        errors = []
        stop_flag = threading.Event()
        
        def acquire_scope():
            while not stop_flag.is_set():
                try:
                    response = mgr.send_command('scope_acquire', {
                        'decimation': 64,
                        'trigger_source': 'immediately',
                        'input_channel': 'in1',
                        'timeout': 5.0
                    }, timeout=10.0)
                    if response['status'] == 'ok':
                        scope_results.append(response)
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def update_asg():
            freq = 1000.0
            while not stop_flag.is_set():
                try:
                    freq = 1000.0 + (len(asg_updates) % 10) * 100
                    response = mgr.send_command('asg_setup', {
                        'channel': 'asg0',
                        'frequency': freq,
                        'waveform': 'sin',
                        'amplitude': 0.5,
                        'offset': 0.0,
                        'trigger_source': 'immediately'
                    }, timeout=5.0)
                    if response['status'] == 'ok':
                        asg_updates.append(freq)
                    time.sleep(0.1)
                except Exception as e:
                    errors.append(('asg', str(e)))
                    break
        
        # Start both
        scope_thread = threading.Thread(target=acquire_scope, daemon=True)
        asg_thread = threading.Thread(target=update_asg, daemon=True)
        
        scope_thread.start()
        asg_thread.start()
        
        # Run for 3 seconds
        time.sleep(3.0)
        stop_flag.set()
        
        scope_thread.join(timeout=5)
        asg_thread.join(timeout=5)
        
        # Verify both ran successfully
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(scope_results) > 0, "Scope didn't acquire"
        assert len(asg_updates) > 0, "ASG didn't update"
        
        print(f"\nConcurrent Scope+ASG: Scope={len(scope_results)} acquisitions, "
              f"ASG={len(asg_updates)} updates")
    
    def test_scope_and_iq_concurrent(self, shared_manager_mock):
        """Test Scope and IQ running simultaneously."""
        mgr = shared_manager_mock
        
        # Setup IQ
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        scope_results = []
        iq_results = []
        errors = []
        stop_flag = threading.Event()
        
        def acquire_scope():
            while not stop_flag.is_set():
                try:
                    response = mgr.send_command('scope_acquire', {
                        'decimation': 64,
                        'trigger_source': 'immediately',
                        'input_channel': 'in1',
                        'timeout': 5.0
                    }, timeout=10.0)
                    if response['status'] == 'ok':
                        scope_results.append(response)
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def read_iq():
            while not stop_flag.is_set():
                try:
                    response = mgr.send_command('iq_get_quadratures', {
                        'channel': 'iq0'
                    }, timeout=5.0)
                    if response['status'] == 'ok':
                        iq_results.append(response)
                    time.sleep(0.05)
                except Exception as e:
                    errors.append(('iq', str(e)))
                    break
        
        scope_thread = threading.Thread(target=acquire_scope, daemon=True)
        iq_thread = threading.Thread(target=read_iq, daemon=True)
        
        scope_thread.start()
        iq_thread.start()
        
        time.sleep(3.0)
        stop_flag.set()
        
        scope_thread.join(timeout=5)
        iq_thread.join(timeout=5)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(scope_results) > 0, "Scope didn't acquire"
        assert len(iq_results) > 0, "IQ didn't read"
        
        print(f"\nConcurrent Scope+IQ: Scope={len(scope_results)}, IQ={len(iq_results)}")
    
    def test_pid_and_iq_concurrent(self, shared_manager_mock):
        """Test PID and IQ running simultaneously."""
        mgr = shared_manager_mock
        
        # Setup PID and IQ
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        pid_results = []
        iq_results = []
        errors = []
        stop_flag = threading.Event()
        
        def update_pid():
            setpoint = 0.0
            while not stop_flag.is_set():
                try:
                    setpoint = (len(pid_results) % 10) * 0.1
                    mgr.send_command('pid_set_setpoint', {
                        'channel': 'pid0',
                        'value': setpoint
                    }, timeout=5.0)
                    
                    response = mgr.send_command('pid_get_setpoint', {
                        'channel': 'pid0'
                    }, timeout=5.0)
                    if response['status'] == 'ok':
                        pid_results.append(response)
                    time.sleep(0.1)
                except Exception as e:
                    errors.append(('pid', str(e)))
                    break
        
        def read_iq():
            while not stop_flag.is_set():
                try:
                    response = mgr.send_command('iq_get_quadratures', {
                        'channel': 'iq0'
                    }, timeout=5.0)
                    if response['status'] == 'ok':
                        iq_results.append(response)
                    time.sleep(0.05)
                except Exception as e:
                    errors.append(('iq', str(e)))
                    break
        
        pid_thread = threading.Thread(target=update_pid, daemon=True)
        iq_thread = threading.Thread(target=read_iq, daemon=True)
        
        pid_thread.start()
        iq_thread.start()
        
        time.sleep(3.0)
        stop_flag.set()
        
        pid_thread.join(timeout=5)
        iq_thread.join(timeout=5)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(pid_results) > 0, "PID didn't operate"
        assert len(iq_results) > 0, "IQ didn't read"
        
        print(f"\nConcurrent PID+IQ: PID={len(pid_results)}, IQ={len(iq_results)}")
    
    def test_all_four_plugins_concurrent(self, shared_manager_mock):
        """Test Scope + IQ + PID + ASG all running concurrently."""
        mgr = shared_manager_mock
        
        # Setup all modules
        mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=5.0)
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        results = {'scope': 0, 'iq': 0, 'pid': 0, 'asg': 0}
        errors = []
        stop_flag = threading.Event()
        
        def run_scope():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('scope_acquire', {
                        'decimation': 64,
                        'trigger_source': 'immediately',
                        'input_channel': 'in1',
                        'timeout': 5.0
                    }, timeout=10.0)
                    if resp['status'] == 'ok':
                        results['scope'] += 1
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def run_iq():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('iq_get_quadratures', {
                        'channel': 'iq0'
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['iq'] += 1
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(('iq', str(e)))
                    break
        
        def run_pid():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('pid_get_setpoint', {
                        'channel': 'pid0'
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['pid'] += 1
                    time.sleep(0.05)
                except Exception as e:
                    errors.append(('pid', str(e)))
                    break
        
        def run_asg():
            freq = 1000.0
            while not stop_flag.is_set():
                try:
                    freq = 1000.0 + (results['asg'] % 10) * 100
                    resp = mgr.send_command('asg_setup', {
                        'channel': 'asg0',
                        'frequency': freq,
                        'waveform': 'sin',
                        'amplitude': 0.5,
                        'offset': 0.0,
                        'trigger_source': 'immediately'
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['asg'] += 1
                    time.sleep(0.1)
                except Exception as e:
                    errors.append(('asg', str(e)))
                    break
        
        # Start all threads
        threads = [
            threading.Thread(target=run_scope, daemon=True),
            threading.Thread(target=run_iq, daemon=True),
            threading.Thread(target=run_pid, daemon=True),
            threading.Thread(target=run_asg, daemon=True)
        ]
        
        for t in threads:
            t.start()
        
        # Run for 5 seconds
        time.sleep(5.0)
        stop_flag.set()
        
        for t in threads:
            t.join(timeout=5)
        
        # Verify all ran
        assert len(errors) == 0, f"Errors: {errors}"
        
        for plugin, count in results.items():
            assert count > 0, f"{plugin} didn't execute"
            print(f"{plugin}: {count} operations")
        
        print(f"\nAll 4 plugins ran concurrently successfully!")
        print(f"Total operations: {sum(results.values())}")
    
    def test_no_command_cross_talk(self, shared_manager_mock):
        """Test that commands don't interfere (UUID routing works)."""
        mgr = shared_manager_mock
        
        # Send many commands rapidly from different "plugins"
        results = {
            'scope': [],
            'iq': [],
            'pid': [],
            'asg': []
        }
        errors = []
        
        # Setup
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.5,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        def send_commands(plugin_type, count):
            try:
                for i in range(count):
                    if plugin_type == 'scope':
                        resp = mgr.send_command('scope_acquire', {
                            'decimation': 64,
                            'trigger_source': 'immediately',
                            'input_channel': 'in1',
                            'timeout': 5.0
                        }, timeout=10.0)
                        results['scope'].append(resp)
                    
                    elif plugin_type == 'iq':
                        resp = mgr.send_command('iq_get_quadratures', {
                            'channel': 'iq0'
                        }, timeout=5.0)
                        results['iq'].append(resp)
                    
                    elif plugin_type == 'pid':
                        resp = mgr.send_command('pid_get_setpoint', {
                            'channel': 'pid0'
                        }, timeout=5.0)
                        results['pid'].append(resp)
                    
                    elif plugin_type == 'asg':
                        resp = mgr.send_command('asg_setup', {
                            'channel': 'asg0',
                            'frequency': 1000.0 + i * 100,
                            'waveform': 'sin',
                            'amplitude': 0.5,
                            'offset': 0.0,
                            'trigger_source': 'immediately'
                        }, timeout=5.0)
                        results['asg'].append(resp)
                    
            except Exception as e:
                errors.append((plugin_type, str(e)))
        
        # Launch all threads simultaneously
        threads = [
            threading.Thread(target=send_commands, args=('scope', 5)),
            threading.Thread(target=send_commands, args=('iq', 10)),
            threading.Thread(target=send_commands, args=('pid', 10)),
            threading.Thread(target=send_commands, args=('asg', 8))
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        # Verify no errors and correct counts
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results['scope']) == 5
        assert len(results['iq']) == 10
        assert len(results['pid']) == 10
        assert len(results['asg']) == 8
        
        # Verify all responses are correct type (no cross-talk)
        for resp in results['scope']:
            assert 'voltage' in resp['data'], "Scope response corrupted"
        
        for resp in results['iq']:
            assert 'i' in resp['data'] and 'q' in resp['data'], "IQ response corrupted"
        
        for resp in results['pid']:
            assert isinstance(resp['data'], (int, float)), "PID response corrupted"
        
        print("\nNo cross-talk detected - UUID routing working correctly!")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
