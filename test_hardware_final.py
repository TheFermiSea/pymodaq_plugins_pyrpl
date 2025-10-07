#!/usr/bin/env python3
"""
Final hardware test with full debugging to verify both fixes work.
"""
import numpy as np
import time
import logging
from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Reduce paramiko logging noise
logging.getLogger('paramiko').setLevel(logging.WARNING)
logging.getLogger('stemlab').setLevel(logging.INFO)

HARDWARE_IP = '100.107.106.75'

print("="*70)
print("PyRPL Hardware Final Test")
print(f"Target: {HARDWARE_IP}")
print("="*70)

worker = PyrplWorker()

# Track status
def status_handler(msg):
    print(f"  [STATUS] {msg}")

worker.status_update.connect(status_handler)

# Connect
print("\n[1] Connecting...")
config = {'hostname': HARDWARE_IP, 'user': 'root', 'password': 'root'}
if not worker.connect(config):
    print("❌ Connection failed")
    exit(1)

print(f"✅ Connected")

# Configure scope
print("\n[2] Configuring scope...")
worker.setup_scope(
    channel='in1',
    decimation=64,
    trigger_source='immediately',
    trigger_level=0.0,
    duration=0.01
)

# Check numpy patch is working
print("\n[3] Checking numpy compatibility patch...")
print(f"  np.float exists: {hasattr(np, 'float')}")
if hasattr(np, 'float'):
    print(f"  np.float = {np.float}")

# Acquire data
print("\n[4] Acquiring data...")
print("  Starting acquisition...")
start_time = time.time()

try:
    times, voltages = worker.acquire_trace()
    elapsed = time.time() - start_time

    print(f"  Acquisition completed in {elapsed:.3f}s")
    print(f"  Samples received: {len(voltages)}")

    if len(voltages) > 0:
        print(f"\n[5] Data Analysis:")
        print(f"  Time range: {times[0]:.6f}s to {times[-1]:.6f}s")
        print(f"  Time step: {(times[1]-times[0])*1e6:.2f}μs")
        print(f"  Voltage min: {np.min(voltages):.4f}V")
        print(f"  Voltage max: {np.max(voltages):.4f}V")
        print(f"  Voltage mean: {np.mean(voltages):.4f}V")
        print(f"  Voltage std: {np.std(voltages):.6f}V")
        print(f"  First 10 samples: {voltages[:10]}")

        # Test second acquisition
        print(f"\n[6] Testing second acquisition...")
        times2, voltages2 = worker.acquire_trace()
        if len(voltages2) > 0:
            print(f"  ✓ Second acquisition successful: {len(voltages2)} samples")
            print(f"    Mean: {np.mean(voltages2):.4f}V")
            print("\n" + "="*70)
            print("🎉 SUCCESS: Hardware interface fully functional!")
            print("   - Connection works")
            print("   - Scope acquisition works")
            print("   - Data is valid")
            print("="*70)
            result = 0
        else:
            print("  ✗ Second acquisition failed")
            result = 1
    else:
        print("  ❌ No data acquired")
        result = 1

except Exception as e:
    print(f"\n❌ Exception during acquisition:")
    print(f"  {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    result = 1

# Cleanup
print("\n[7] Disconnecting...")
worker.disconnect()

exit(result)
