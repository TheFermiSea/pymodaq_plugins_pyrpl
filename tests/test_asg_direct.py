"""
Test ASG by directly checking what PyRPL shows for ASG state.
"""
import time
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

mgr = get_shared_worker_manager()
config = {'hostname': '100.107.106.75', 'config_name': 'test_asg_direct', 'mock_mode': False}

print("\nConnecting...")
mgr.start_worker(config)
time.sleep(5.0)

try:
    print("\nConfiguring ASG...")
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
    print(f"ASG setup: {resp['status']}")
    
    print("\nWaiting 2 seconds...")
    time.sleep(2.0)
    
    print("\nReading sampler from input2:")
    for i in range(20):
        resp = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
        print(f"  {resp['data']:.6f}V", end="  ")
        if (i+1) % 5 == 0:
            print()
        time.sleep(0.001)  # 1ms between samples - should see AC variation

finally:
    print("\n\nShutting down...")
    mgr.shutdown()
    time.sleep(2.0)
