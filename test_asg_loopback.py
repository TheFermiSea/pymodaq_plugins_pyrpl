#!/usr/bin/env python3
"""
Test script to generate a signal with ASG and capture it with Scope
This verifies the complete signal path works correctly.
"""
from pyrpl import Pyrpl
import time
import numpy as np
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

print("="*80)
print("PyRPL ASG → Scope Loopback Test")
print("="*80)

# Connect to Red Pitaya
print("\n1. Connecting to Red Pitaya at 100.107.106.75...")
p = Pyrpl(hostname='100.107.106.75', config='loopback_test', gui=False, reloadfpga=False)
print("   ✓ Connected")

# Configure ASG (Arbitrary Signal Generator) on output 1
print("\n2. Configuring ASG to output 1kHz sine wave on OUT1...")
asg = p.rp.asg0
asg.output_direct = 'out1'  # Output to physical OUT1
asg.waveform = 'sin'        # Sine wave
asg.frequency = 1000        # 1 kHz
asg.amplitude = 0.5         # 0.5V amplitude
asg.offset = 0.0            # No DC offset
asg.trigger_source = 'immediately'  # Start immediately

print(f"   ✓ ASG configured:")
print(f"     - Output: OUT1")
print(f"     - Waveform: {asg.waveform}")
print(f"     - Frequency: {asg.frequency} Hz")
print(f"     - Amplitude: {asg.amplitude} V")

# Give the signal time to stabilize
time.sleep(0.1)

# Configure Scope to capture from input 1
print("\n3. Configuring Scope to capture from IN1...")
scope = p.rp.scope
scope.input1 = 'in1'        # Read from physical IN1
scope.decimation = 64       # 125 MHz / 64 = ~1.95 MHz sample rate
scope.trigger_source = 'immediately'  # Trigger immediately

print(f"   ✓ Scope configured:")
print(f"     - Input: IN1")
print(f"     - Decimation: {scope.decimation}")
print(f"     - Sample rate: {125e6/scope.decimation:.2e} Hz")
print(f"     - Duration: {scope.duration} s")

# Acquire data
print("\n4. Acquiring scope data...")
data = scope._data_ch1  # Read data directly from property
times = scope.times

print(f"   ✓ Acquired {len(data)} points")
print(f"     - Min: {data.min():.6f} V")
print(f"     - Max: {data.max():.6f} V")
print(f"     - Mean: {data.mean():.6f} V")
print(f"     - Std: {data.std():.6f} V")
print(f"     - Peak-to-peak: {data.max() - data.min():.6f} V")

# Calculate expected amplitude
expected_pk_pk = 2 * asg.amplitude
print(f"     - Expected Vpp: {expected_pk_pk:.6f} V")

# Plot the results
if HAS_MATPLOTLIB:
    print("\n5. Plotting waveform...")
    plt.figure(figsize=(12, 6))

    # Plot full waveform
    plt.subplot(2, 1, 1)
    plt.plot(times * 1000, data, 'b-', linewidth=0.5)
    plt.xlabel('Time (ms)')
    plt.ylabel('Voltage (V)')
    plt.title(f'ASG → Scope Loopback Test: {asg.frequency} Hz sine wave')
    plt.grid(True)

    # Plot zoomed view (first 10 cycles)
    plt.subplot(2, 1, 2)
    period = 1.0 / asg.frequency
    zoom_time = 10 * period  # Show 10 periods
    zoom_idx = np.where(times <= zoom_time)[0]
    plt.plot(times[zoom_idx] * 1000, data[zoom_idx], 'b-', linewidth=1)
    plt.xlabel('Time (ms)')
    plt.ylabel('Voltage (V)')
    plt.title(f'Zoomed: First 10 cycles')
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('asg_scope_loopback.png', dpi=150)
    print("   ✓ Saved plot to: asg_scope_loopback.png")
else:
    print("\n5. Skipping plot (matplotlib not available)")

# Verify signal is detected
signal_detected = (data.max() - data.min()) > 0.1  # At least 100mV peak-to-peak
if signal_detected:
    print("\n" + "="*80)
    print("✓✓✓ SUCCESS - Signal detected on scope!")
    print("    Connect a wire from OUT1 to IN1 to see the full loopback signal")
    print("="*80)
else:
    print("\n" + "="*80)
    print("⚠ WARNING - Signal level very low")
    print("   Make sure to connect OUT1 to IN1 with a wire or BNC cable")
    print("="*80)

# Turn off ASG
print("\n6. Cleaning up...")
asg.output_direct = 'off'
print("   ✓ ASG turned off")

print("\nTest complete!")
