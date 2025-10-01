#!/usr/bin/env python
"""Test different ASG channels and outputs."""
import time
import sys
sys.path.insert(0, 'src')

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

def test_config(asg_channel, output, input_channel):
    """Test one ASG + output configuration."""
    mgr = get_shared_worker_manager()
    config = {'hostname': '100.107.106.75', 'config_name': f'test_{asg_channel}_{output}', 'mock_mode': False}
    
    print(f"\n{'='*60}")
    print(f"Testing: {asg_channel} → {output}, reading from {input_channel}")
    print('='*60)
    
    mgr.start_worker(config)
    time.sleep(5.0)
    
    try:
        # Configure ASG
        asg_config = {
            'channel': asg_channel,
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'output_direct': output,
            'trigger_source': 'immediately'
        }
        resp = mgr.send_command('asg_setup', asg_config, timeout=10.0)
        print(f"ASG setup: {resp['status']}")
        
        time.sleep(1.0)
        
        # Read input
        samples = []
        for _ in range(10):
            resp = mgr.send_command('sampler_read', {'channel': input_channel}, timeout=10.0)
            samples.append(resp['data'])
            time.sleep(0.01)
        
        import statistics
        vmin, vmax = min(samples), max(samples)
        vrange = vmax - vmin
        vstd = statistics.stdev(samples) if len(samples) > 1 else 0
        
        print(f"Results: range={vrange:.6f}V, std={vstd:.6f}V")
        if vrange > 0.05 or vstd > 0.01:
            print("✓ SIGNAL DETECTED!")
            return True
        else:
            print("✗ No signal")
            return False
    
    finally:
        mgr.shutdown()
        time.sleep(2.0)

if __name__ == '__main__':
    print("\n=== ASG Channel & Output Testing ===\n")
    print("Physical setup: cable from output2 → input2")
    
    # Test all combinations
    tests = [
        ('asg0', 'out1', 'in2'),  # Wrong output
        ('asg0', 'out2', 'in2'),  # Current config
        ('asg1', 'out1', 'in2'),  # Different ASG, wrong output  
        ('asg1', 'out2', 'in2'),  # Different ASG, correct output
    ]
    
    results = {}
    for asg_ch, out_ch, in_ch in tests:
        results[f"{asg_ch}→{out_ch}"] = test_config(asg_ch, out_ch, in_ch)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for config, detected in results.items():
        status = "✓ WORKS" if detected else "✗ No signal"
        print(f"{config}: {status}")
