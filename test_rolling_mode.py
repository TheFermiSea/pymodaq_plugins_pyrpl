#!/usr/bin/env python3
"""
Test StemLab scope using rolling_mode instead of trigger-based acquisition.
Rolling mode continuously acquires data without waiting for triggers.
"""
import numpy as np
import time
import logging

# NumPy compatibility patch
if not hasattr(np, 'float'):
    np.float = np.float64

from stemlab import StemLab

logging.basicConfig(level=logging.INFO)
logging.getLogger('paramiko').setLevel(logging.WARNING)

print("="*70)
print("StemLab Scope Rolling Mode Test")
print("="*70)

# Connect
print("\n[1] Connecting...")
s = StemLab(hostname='100.107.106.75', user='root', password='root',
            reloadfpga=False, timeout=10)
print(f"✓ Connected to {s.parameters['hostname']}")

scope = s.scope

# Configure for rolling mode
print("\n[2] Configuring scope for rolling mode...")
scope.input1 = 'in1'
scope.ch1_active = True
scope.ch2_active = False
scope.decimation = 64
scope.duration = 0.2  # >0.1s required for rolling mode
scope.rolling_mode = True

print(f"  input1: {scope.input1}")
print(f"  decimation: {scope.decimation}")
print(f"  duration: {scope.duration}s")
print(f"  rolling_mode: {scope.rolling_mode}")
print(f"  rolling_mode_allowed: {scope._rolling_mode_allowed()}")
print(f"  is_rolling_mode_active: {scope._is_rolling_mode_active()}")

#Try acquiring in rolling mode
print("\n[3] Starting rolling mode acquisition...")
scope._start_acquisition_rolling_mode()

# Wait a bit for data to accumulate
time.sleep(0.5)

# Try to get data
print("\n[4] Reading data...")
try:
    data = scope._data_ch1
    times = scope.times

    print(f"✓ Got {len(data)} samples")
    print(f"  Time range: {times[0]:.6f}s to {times[-1]:.6f}s")
    print(f"  Voltage min: {np.min(data):.4f}V")
    print(f"  Voltage max: {np.max(data):.4f}V")
    print(f"  Voltage mean: {np.mean(data):.4f}V")
    print(f"  Voltage std: {np.std(data):.6f}V")

    if len(data) > 0 and np.std(data) > 0:
        print("\n🎉 SUCCESS: Rolling mode acquisition works!")
    else:
        print("\n⚠️ Data acquired but may be invalid (all zeros or constant)")

except Exception as e:
    print(f"✗ Failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
print("\n[5] Disconnecting...")
s.end()
print("✓ Disconnected")
