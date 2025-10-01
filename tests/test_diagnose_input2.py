"""Diagnostic test for input2."""
import time
import numpy as np
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

mgr = get_shared_worker_manager()
config = {'hostname': '100.107.106.75', 'config_name': 'test_diag', 'mock_mode': False}

print("\nConnecting...")
mgr.start_worker(config)
time.sleep(5.0)

try:
    print("\n=== Diagnostic Test ===")
    print("1. Reading sampler from input2 (10 samples):")
    for i in range(10):
        resp = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
        print(f"   Sample {i+1}: {resp['data']:.6f} V")
        time.sleep(0.1)
    
    print("\n2. Configuring ASG0 → output2, trigger=immediately:")
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
    print(f"   ASG configured: {resp['status']}")
    
    print("\n3. Waiting 1 second for ASG to stabilize...")
    time.sleep(1.0)
    
    print("\n4. Reading sampler from input2 again (should see AC signal if loopback works):")
    for i in range(10):
        resp = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
        print(f"   Sample {i+1}: {resp['data']:.6f} V")
        time.sleep(0.05)
    
    print("\n5. Acquiring scope from input2:")
    scope_config = {
        'decimation': 64,
        'trigger_source': 'immediately',
        'input_channel': 'in2',
        'timeout': 5.0
    }
    resp = mgr.send_command('scope_acquire', scope_config, timeout=10.0)
    voltage_data = np.array(resp['data']['voltage'])
    vpp = voltage_data.max() - voltage_data.min()
    print(f"   Scope Vpp: {vpp:.6f} V")
    
    print("\n=== Conclusion ===")
    if vpp > 0.1:
        print(f"✓ ASG signal detected! Vpp={vpp:.3f}V")
    else:
        print(f"✗ No ASG signal on input2")
        print("  - If sampler shows 0V: cable may not be connected")
        print("  - If sampler shows varying V: ASG may be working but scope settings wrong")

finally:
    print("\nShutting down...")
    mgr.shutdown()
    time.sleep(2.0)
