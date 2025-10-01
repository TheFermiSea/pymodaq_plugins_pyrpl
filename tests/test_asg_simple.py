"""
Simple ASG test with output2 → input2 loopback.
"""
import time
import numpy as np
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


def test_asg_output2():
    """Test that ASG generates a signal on output2."""
    mgr = get_shared_worker_manager()
    
    # Connect
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_asg_simple',
        'mock_mode': False
    }
    
    print("\n[Test] Connecting...")
    mgr.start_worker(config)
    time.sleep(5.0)
    
    try:
        # Configure ASG - output to out2
        print("[Test] Configuring ASG0 to output on out2...")
        asg_config = {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'output_direct': 'out2',
            'trigger_source': 'immediately'  # START the ASG immediately!
        }
        
        response = mgr.send_command('asg_setup', asg_config, timeout=10.0)
        print(f"[Test] ASG response: {response}")
        assert response['status'] == 'ok'
        
        time.sleep(0.5)  # Let signal stabilize
        
        # Acquire scope data from input2
        print("[Test] Acquiring scope on input2...")
        scope_config = {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in2',  # Read from input2
            'timeout': 5.0
        }
        
        response = mgr.send_command('scope_acquire', scope_config, timeout=10.0)
        assert response['status'] == 'ok'
        
        # Analyze signal
        voltage_data = np.array(response['data']['voltage'])
        vmin = voltage_data.min()
        vmax = voltage_data.max()
        vpp = vmax - vmin
        
        print(f"\n[Test Results]")
        print(f"  Vmin: {vmin:.6f} V")
        print(f"  Vmax: {vmax:.6f} V")
        print(f"  Vpp:  {vpp:.6f} V")
        print(f"  Expected: ~1.0V (500mV amplitude sine)")
        
        if vpp > 0.3:
            print(f"\n✓ SUCCESS: ASG signal detected!")
            print(f"✓ Hardware loopback working: output2 → input2")
        else:
            print(f"\n✗ FAIL: No signal detected (Vpp={vpp:.3f}V)")
            print("Check:")
            print("  1. Physical connection output2 → input2")
            print("  2. ASG trigger_source='immediately' setting")
    
    finally:
        print("\n[Test] Shutting down...")
        mgr.shutdown()
        time.sleep(2.0)


if __name__ == '__main__':
    test_asg_output2()
