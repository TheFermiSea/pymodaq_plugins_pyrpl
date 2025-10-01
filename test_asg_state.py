#!/usr/bin/env python
"""Check ASG state after setup."""
import time
import sys
sys.path.insert(0, 'src')

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

mgr = get_shared_worker_manager()
config = {'hostname': '100.107.106.75', 'config_name': 'test_state', 'mock_mode': False}

print("\nConnecting...")
mgr.start_worker(config)
time.sleep(5.0)

try:
    print("\nConfiguring ASG with setup()...")
    asg_config = {
        'channel': 'asg0',
        'waveform': 'sin',
        'frequency': 1000.0,
        'amplitude': 0.5,
        'offset': 0.0,
        'output_direct': 'out2',
        'trigger_source': 'immediately'
    }
    resp = mgr.send_command('asg_setup', asg_config, timeout=10.0)
    print(f"Setup result: {resp['status']}")
    
    print("\nNow checking if signal appears...")
    time.sleep(1.0)
    
    # Check sampler
    resp = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
    print(f"Input2 voltage: {resp['data']:.6f}V")

finally:
    mgr.shutdown()
    time.sleep(2.0)
