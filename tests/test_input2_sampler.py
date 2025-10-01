"""Test that we can read from input2."""
import time
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

mgr = get_shared_worker_manager()

config = {
    'hostname': '100.107.106.75',
    'config_name': 'test_input2',
    'mock_mode': False
}

print("\nConnecting...")
mgr.start_worker(config)
time.sleep(5.0)

try:
    # Read from input2 multiple times
    print("\nReading from input2 (10 samples):")
    for i in range(10):
        response = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
        voltage = response['data']
        print(f"  Sample {i+1}: {voltage:.6f} V")
        time.sleep(0.1)
    
    print("\n✓ Input2 sampler working")
    
finally:
    print("\nShutting down...")
    mgr.shutdown()
    time.sleep(2.0)
