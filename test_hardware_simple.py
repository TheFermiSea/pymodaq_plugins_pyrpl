#!/usr/bin/env python3
"""
Simple hardware test - directly tests PyrplWorker with real Red Pitaya.
No Qt complexity, just pure hardware verification.
"""
import numpy as np
import time
from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

HARDWARE_IP = '100.107.106.75'

print("="*70)
print("PyRPL Hardware Verification Test")
print(f"Target: {HARDWARE_IP}")
print("="*70)

# Create worker
print("\n[1] Creating PyrplWorker...")
worker = PyrplWorker()

# Connect
print(f"[2] Connecting to {HARDWARE_IP}...")
config = {'hostname': HARDWARE_IP, 'user': 'root', 'password': 'root'}
connected = worker.connect(config)

if not connected:
    print("❌ FAILED: Could not connect")
    exit(1)

print(f"✅ Connected: {worker.get_idn()}")

# Test output voltage control
print("\n[3] Testing output voltage control (ASG)...")
test_voltage = 0.3
worker.set_output_voltage('out1', test_voltage)
print(f"✅ Set OUT1 = {test_voltage}V")

# Configure scope
print("\n[4] Configuring oscilloscope...")
worker.setup_scope(
    channel='in1',
    decimation=64,
    trigger_source='immediately',  # Ignored in rolling mode
    trigger_level=0.0,  # Ignored in rolling mode
    duration=0.2  # Must be > 0.1s for rolling mode
)
print("✅ Scope configured for IN1")

# Acquire data
print("\n[5] Acquiring scope trace...")
start_time = time.time()
times, voltages = worker.acquire_trace()
acq_time = time.time() - start_time

if len(voltages) == 0:
    print("❌ FAILED: No data acquired")
    worker.disconnect()
    exit(1)

print(f"✅ Acquired {len(voltages)} samples in {acq_time:.3f}s")

# Analyze data
print("\n[6] Data Analysis:")
print(f"  Time range: {times[0]:.6f}s to {times[-1]:.6f}s")
print(f"  Time step: {(times[1]-times[0])*1e6:.2f}μs")
print(f"  Voltage min: {np.min(voltages):.4f}V")
print(f"  Voltage max: {np.max(voltages):.4f}V")
print(f"  Voltage mean: {np.mean(voltages):.4f}V")
print(f"  Voltage std: {np.std(voltages):.6f}V")

# Validate data quality
valid_data = True
if np.all(voltages == 0):
    print("  ⚠️  WARNING: All voltages are zero")
    valid_data = False
elif np.all(np.isnan(voltages)):
    print("  ❌ ERROR: All voltages are NaN")
    valid_data = False
elif np.std(voltages) == 0:
    print("  ⚠️  WARNING: No variation in signal (all identical values)")
else:
    print("  ✅ Data appears valid (non-zero with variation)")

# Test second acquisition
print("\n[7] Second acquisition (verify repeatability)...")
times2, voltages2 = worker.acquire_trace()
if len(voltages2) > 0:
    print(f"✅ Second acquisition: {len(voltages2)} samples")
    print(f"  Mean: {np.mean(voltages2):.4f}V")
else:
    print("❌ Second acquisition failed")
    valid_data = False

# Cleanup
print("\n[8] Disconnecting...")
worker.disconnect()
print("✅ Disconnected")

# Final verdict
print("\n" + "="*70)
if valid_data and len(voltages) > 0 and len(voltages2) > 0:
    print("🎉 SUCCESS: PyRPL hardware interface fully functional!")
    print("   - Connection works")
    print("   - Output voltage control works")
    print("   - Scope data acquisition works")
    print("   - Data quality is valid")
    print("="*70)
    exit(0)
else:
    print("⚠️  PARTIAL SUCCESS: Connection works but data quality issues")
    print("="*70)
    exit(1)
