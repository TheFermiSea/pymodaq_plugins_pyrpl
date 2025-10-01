"""
Test ASG functionality with output2 → input2 loopback configuration.

Hardware setup:
- output2 connected to input2 (physical loopback)
- input1 and output1 not connected
"""
import pytest
import time
import numpy as np
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_asg_loopback'


@pytest.fixture(scope='module')
def hardware_manager():
    """Get a SharedPyRPLManager instance with real hardware."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': HARDWARE_IP,
        'config_name': CONFIG_NAME,
        'mock_mode': False
    }
    
    print(f"\n[ASG Test] Connecting to Red Pitaya at {HARDWARE_IP}...")
    mgr.start_worker(config)
    time.sleep(5.0)  # Wait for PyRPL initialization
    
    response = mgr.send_command('ping', {}, timeout=10.0)
    assert response['status'] == 'ok', f"Failed to ping hardware: {response}"
    print(f"[ASG Test] Connected successfully")
    
    yield mgr
    
    print("\n[ASG Test] Shutting down...")
    mgr.shutdown()
    time.sleep(2.0)


class TestASGOutput2Loopback:
    """Test ASG with output2→input2 loopback."""
    
    def test_asg_generates_sine_wave(self, hardware_manager):
        """Test that ASG generates a detectable sine wave on output2."""
        print("\n[Test] Testing ASG sine wave generation on output2...")
        
        # Step 1: Configure ASG on output2 (using asg1 which routes to output2)
        print("[Test] Configuring ASG1 (output2)...")
        asg_config = {
            'channel': 'asg1',  # asg1 → output2
            'waveform': 'sin',
            'frequency': 1000.0,  # 1 kHz
            'amplitude': 0.5,     # 500 mV amplitude
            'offset': 0.0,
            'trigger_source': 'immediately'
        }
        
        response = hardware_manager.send_command('asg_setup', asg_config, timeout=10.0)
        assert response['status'] == 'ok', f"ASG setup failed: {response}"
        print(f"[Test] ASG configured: {asg_config['frequency']} Hz, {asg_config['amplitude']}V amplitude")
        
        # Step 2: Wait for signal to stabilize
        time.sleep(0.5)
        
        # Step 3: Acquire scope data on input2
        print("[Test] Acquiring scope data from input2...")
        scope_config = {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in2',  # Read from input2 (connected to output2)
            'timeout': 5.0
        }
        
        response = hardware_manager.send_command('scope_acquire', scope_config, timeout=10.0)
        assert response['status'] == 'ok', f"Scope acquisition failed: {response}"
        
        # Step 4: Analyze the acquired signal
        voltage_data = np.array(response['data']['voltage'])
        time_data = np.array(response['data']['time'])
        
        vmin = voltage_data.min()
        vmax = voltage_data.max()
        vpp = vmax - vmin
        vmean = voltage_data.mean()
        vrms = np.sqrt(np.mean(voltage_data**2))
        
        print(f"\n[Test Results]")
        print(f"  Samples acquired: {len(voltage_data)}")
        print(f"  Time span: {time_data[-1]:.6f} s")
        print(f"  Vmin: {vmin:.6f} V")
        print(f"  Vmax: {vmax:.6f} V")
        print(f"  Vpp:  {vpp:.6f} V (peak-to-peak)")
        print(f"  Vmean: {vmean:.6f} V")
        print(f"  Vrms: {vrms:.6f} V")
        print(f"  Expected Vpp: ~1.0 V (500mV amplitude sine)")
        
        # Verify signal is present
        assert vpp > 0.3, f"ASG signal too weak or not present: Vpp={vpp:.3f}V (expected >0.3V)"
        assert vpp < 2.0, f"ASG signal too strong: Vpp={vpp:.3f}V (expected <2.0V)"
        
        # For a sine wave with 0.5V amplitude, Vpp should be ~1.0V
        print(f"\n[Test] ✓ ASG signal detected successfully!")
        print(f"[Test] ✓ Hardware loopback working: output2 → input2")
    
    def test_asg_frequency_sweep(self, hardware_manager):
        """Test ASG at multiple frequencies."""
        print("\n[Test] Testing ASG frequency sweep on output2...")
        
        frequencies = [500.0, 1000.0, 2000.0, 5000.0]  # Hz
        results = []
        
        for freq in frequencies:
            print(f"\n[Test] Testing {freq} Hz...")
            
            # Configure ASG
            asg_config = {
                'channel': 'asg1',
                'waveform': 'sin',
                'frequency': freq,
                'amplitude': 0.5,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }
            
            response = hardware_manager.send_command('asg_setup', asg_config, timeout=10.0)
            assert response['status'] == 'ok', f"ASG setup failed at {freq} Hz"
            
            time.sleep(0.2)  # Let signal stabilize
            
            # Acquire scope data
            scope_config = {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in2',
                'timeout': 5.0
            }
            
            response = hardware_manager.send_command('scope_acquire', scope_config, timeout=10.0)
            assert response['status'] == 'ok', f"Scope failed at {freq} Hz"
            
            voltage_data = np.array(response['data']['voltage'])
            vpp = voltage_data.max() - voltage_data.min()
            
            results.append({'frequency': freq, 'vpp': vpp})
            print(f"  {freq} Hz: Vpp = {vpp:.3f} V")
            
            # Verify signal present at each frequency
            assert vpp > 0.3, f"Signal too weak at {freq} Hz: Vpp={vpp:.3f}V"
        
        print(f"\n[Test Results Summary]")
        print(f"  Tested frequencies: {len(frequencies)}")
        for r in results:
            print(f"    {r['frequency']:>6.0f} Hz: Vpp = {r['vpp']:.3f} V")
        
        print(f"\n[Test] ✓ ASG works at all tested frequencies!")
    
    def test_asg_amplitude_control(self, hardware_manager):
        """Test ASG amplitude control."""
        print("\n[Test] Testing ASG amplitude control...")
        
        amplitudes = [0.1, 0.3, 0.5, 0.7]  # Volts
        results = []
        
        for amp in amplitudes:
            print(f"\n[Test] Testing {amp}V amplitude...")
            
            # Configure ASG
            asg_config = {
                'channel': 'asg1',
                'waveform': 'sin',
                'frequency': 1000.0,
                'amplitude': amp,
                'offset': 0.0,
                'trigger_source': 'immediately'
            }
            
            response = hardware_manager.send_command('asg_setup', asg_config, timeout=10.0)
            assert response['status'] == 'ok', f"ASG setup failed at {amp}V"
            
            time.sleep(0.2)
            
            # Acquire scope data
            scope_config = {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in2',
                'timeout': 5.0
            }
            
            response = hardware_manager.send_command('scope_acquire', scope_config, timeout=10.0)
            assert response['status'] == 'ok', f"Scope failed at {amp}V"
            
            voltage_data = np.array(response['data']['voltage'])
            vpp = voltage_data.max() - voltage_data.min()
            expected_vpp = amp * 2  # Peak-to-peak for sine wave
            
            results.append({
                'amplitude': amp,
                'vpp_measured': vpp,
                'vpp_expected': expected_vpp,
                'error': abs(vpp - expected_vpp) / expected_vpp * 100
            })
            
            print(f"  Amplitude: {amp}V")
            print(f"    Measured Vpp: {vpp:.3f}V")
            print(f"    Expected Vpp: {expected_vpp:.3f}V")
            print(f"    Error: {results[-1]['error']:.1f}%")
        
        print(f"\n[Test Results Summary]")
        for r in results:
            print(f"  {r['amplitude']:.1f}V → Vpp {r['vpp_measured']:.3f}V "
                  f"(expected {r['vpp_expected']:.3f}V, error {r['error']:.1f}%)")
        
        # Check that amplitude scales roughly linearly
        for r in results:
            assert r['vpp_measured'] > 0.1, f"Signal too weak at {r['amplitude']}V"
            assert r['error'] < 50, f"Amplitude error too large: {r['error']:.1f}%"
        
        print(f"\n[Test] ✓ ASG amplitude control working!")
    
    def test_asg_waveform_types(self, hardware_manager):
        """Test different ASG waveform types."""
        print("\n[Test] Testing ASG waveform types...")
        
        waveforms = ['sin', 'halframp', 'ramp']
        results = []
        
        for waveform in waveforms:
            print(f"\n[Test] Testing {waveform} waveform...")
            
            # Configure ASG
            asg_config = {
                'channel': 'asg0',
                'waveform': waveform,
                'frequency': 1000.0,
                'amplitude': 0.5,
                'offset': 0.0,
                'output_direct': 'out2',
                'trigger_source': 'immediately'
            }
            
            response = hardware_manager.send_command('asg_setup', asg_config, timeout=10.0)
            assert response['status'] == 'ok', f"ASG setup failed for {waveform}"
            
            time.sleep(0.2)
            
            # Acquire scope data
            scope_config = {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in2',
                'timeout': 5.0
            }
            
            response = hardware_manager.send_command('scope_acquire', scope_config, timeout=10.0)
            assert response['status'] == 'ok', f"Scope failed for {waveform}"
            
            voltage_data = np.array(response['data']['voltage'])
            vpp = voltage_data.max() - voltage_data.min()
            
            results.append({'waveform': waveform, 'vpp': vpp})
            print(f"  {waveform}: Vpp = {vpp:.3f}V")
            
            assert vpp > 0.3, f"{waveform} waveform too weak: Vpp={vpp:.3f}V"
        
        print(f"\n[Test Results Summary]")
        for r in results:
            print(f"  {r['waveform']:>10s}: Vpp = {r['vpp']:.3f}V")
        
        print(f"\n[Test] ✓ All waveform types working!")


if __name__ == '__main__':
    """Run ASG loopback tests."""
    print("=" * 70)
    print("ASG Output2 → Input2 Loopback Test")
    print("=" * 70)
    print(f"Hardware: {HARDWARE_IP}")
    print(f"Configuration: output2 → input2 loopback")
    print("=" * 70)
    
    pytest.main([__file__, '-v', '-s'])
