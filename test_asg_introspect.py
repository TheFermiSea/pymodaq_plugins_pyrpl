#!/usr/bin/env python
"""Introspect ASG object to see what attributes/methods are available."""
import time
import sys
sys.path.insert(0, 'src')

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

mgr = get_shared_worker_manager()
config = {'hostname': '100.107.106.75', 'config_name': 'test_introspect', 'mock_mode': False}

print("\nConnecting...")
mgr.start_worker(config)
time.sleep(5.0)

try:
    # Send a custom command to introspect the ASG
    print("\nIntrospecting ASG attributes...")
    resp = mgr.send_command('custom_eval', {
        'code': '''
import pyrpl
asg = pyrpl.rp.asg0
attrs = [a for a in dir(asg) if not a.startswith('_')]
result = {}
for attr in attrs:
    try:
        val = getattr(asg, attr)
        if not callable(val):
            result[attr] = str(val)
    except:
        pass
result
'''
    }, timeout=10.0)
    
    if resp['status'] == 'ok':
        print("\nASG Attributes:")
        for key, val in sorted(resp['data'].items()):
            print(f"  {key}: {val}")
    else:
        print(f"Error: {resp}")

finally:
    mgr.shutdown()
    time.sleep(2.0)
