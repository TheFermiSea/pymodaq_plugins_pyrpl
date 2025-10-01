#!/usr/bin/env python
"""
Simple test: Read voltages on in1 and in2 while ASG drives out2.
This isolates whether ASG is actually outputting.
"""
import time
import sys
sys.path.insert(0, 'src')

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

def main():
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_asg_sampler',
        'mock_mode': False
    }
    
    print("\n=== ASG Output Test ===")
    print("Connecting to Red Pitaya...")
    mgr.start_worker(config)
    time.sleep(5.0)
    
    try:
        # Step 1: Read baseline voltages (ASG off)
        print("\n1. Baseline readings (ASG off):")
        resp1 = mgr.send_command('sampler_read', {'channel': 'in1'}, timeout=10.0)
        resp2 = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
        print(f"   input1: {resp1['data']:.6f} V")
        print(f"   input2: {resp2['data']:.6f} V")
        
        # Step 2: Configure ASG to output on out2
        print("\n2. Configuring ASG (out2, 1kHz sine, 0.5V amplitude)...")
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
        print(f"   ASG setup: {resp['status']}")
        
        # Step 3: Wait for signal to stabilize
        print("\n3. Waiting 1 second for ASG to stabilize...")
        time.sleep(1.0)
        
        # Step 4: Read voltages rapidly to catch AC variation
        print("\n4. Reading input1 (20 samples @ 5ms intervals):")
        print("   ", end="")
        in1_samples = []
        for i in range(20):
            resp = mgr.send_command('sampler_read', {'channel': 'in1'}, timeout=10.0)
            in1_samples.append(resp['data'])
            print(f"{resp['data']:+.3f} ", end="")
            if (i+1) % 10 == 0:
                print("\n   ", end="")
            time.sleep(0.005)
        
        print("\n\n5. Reading input2 (20 samples @ 5ms intervals):")
        print("   ", end="")
        in2_samples = []
        for i in range(20):
            resp = mgr.send_command('sampler_read', {'channel': 'in2'}, timeout=10.0)
            in2_samples.append(resp['data'])
            print(f"{resp['data']:+.3f} ", end="")
            if (i+1) % 10 == 0:
                print("\n   ", end="")
            time.sleep(0.005)
        
        # Analysis
        print("\n\n=== Analysis ===")
        import statistics
        
        in1_min, in1_max = min(in1_samples), max(in1_samples)
        in1_range = in1_max - in1_min
        in1_std = statistics.stdev(in1_samples) if len(in1_samples) > 1 else 0
        
        in2_min, in2_max = min(in2_samples), max(in2_samples)
        in2_range = in2_max - in2_min
        in2_std = statistics.stdev(in2_samples) if len(in2_samples) > 1 else 0
        
        print(f"\ninput1 (not connected):")
        print(f"  Range: {in1_range:.6f} V (min={in1_min:.3f}, max={in1_max:.3f})")
        print(f"  StdDev: {in1_std:.6f} V")
        
        print(f"\ninput2 (connected to output2):")
        print(f"  Range: {in2_range:.6f} V (min={in2_min:.3f}, max={in2_max:.3f})")
        print(f"  StdDev: {in2_std:.6f} V")
        
        print("\n=== Conclusion ===")
        if in2_range > 0.05 or in2_std > 0.01:
            print("✓ ASG IS OUTPUTTING! Signal detected on input2")
            print(f"  Expected range for 0.5V amplitude sine: ~1.0V")
            print(f"  Measured range: {in2_range:.3f}V")
        else:
            print("✗ ASG NOT OUTPUTTING - No signal on input2")
            print("  Possible causes:")
            print("  - ASG hardware issue")
            print("  - Missing PyRPL configuration step")
            print("  - Physical connection issue")
    
    finally:
        print("\n\nShutting down...")
        mgr.shutdown()
        time.sleep(2.0)

if __name__ == '__main__':
    main()
