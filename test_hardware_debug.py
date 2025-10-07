#!/usr/bin/env python3
"""
Debug version of hardware test with verbose logging.
"""
import numpy as np
import time
import logging
from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

HARDWARE_IP = '100.107.106.75'

print("="*70)
print("PyRPL Hardware Debug Test")
print(f"Target: {HARDWARE_IP}")
print("="*70)

# Create worker
print("\n[1] Creating PyrplWorker...")
worker = PyrplWorker()

# Track status messages
status_messages = []
def status_handler(msg):
    status_messages.append(msg)
    print(f"  STATUS: {msg}")

worker.status_update.connect(status_handler)

# Connect
print(f"[2] Connecting to {HARDWARE_IP}...")
config = {'hostname': HARDWARE_IP, 'user': 'root', 'password': 'root'}
connected = worker.connect(config)

if not connected:
    print("❌ FAILED: Could not connect")
    exit(1)

print(f"✅ Connected: {worker.get_idn()}")

# Configure scope with more verbose setup
print("\n[3] Configuring oscilloscope...")
print("  Setting up scope parameters:")
print("    channel: in1")
print("    decimation: 64")
print("    trigger_source: immediately")
print("    trigger_level: 0.0")

worker.setup_scope(
    channel='in1',
    decimation=64,
    trigger_source='immediately',
    trigger_level=0.0,
    duration=0.01
)

# Check scope state before acquisition
scope = worker.pyrpl.scope
print(f"\n[4] Scope state before acquisition:")
print(f"  input1: {scope.input1}")
print(f"  decimation: {scope.decimation}")
print(f"  trigger_source: {scope.trigger_source}")
print(f"  trigger_level: {scope.trigger_level}")

# Acquire data with detailed monitoring
print("\n[5] Starting acquisition...")
start_time = time.time()

# Manually replicate acquire_trace logic with more logging
try:
    print("  Calling _start_acquisition()...")
    scope._start_acquisition()

    print("  Waiting for acquisition to complete...")
    timeout = 10.0
    loop_start = time.time()
    iteration = 0

    while scope._curve_acquiring():
        iteration += 1
        elapsed = time.time() - loop_start

        if iteration % 10 == 0:  # Log every 100ms
            print(f"    Iteration {iteration} (t={elapsed:.2f}s): trigger_armed={scope._trigger_armed}, curve_acquiring=True")

        if elapsed > timeout:
            print(f"  ⚠️  TIMEOUT after {elapsed:.2f}s and {iteration} iterations")
            print(f"  Final state: trigger_armed={scope._trigger_armed}")
            break

        time.sleep(0.01)

    if not scope._curve_acquiring():
        print(f"  ✓ Acquisition complete after {iteration} iterations ({time.time()-loop_start:.3f}s)")

    # Get the data
    print("\n[6] Retrieving data...")
    if scope.input1 == 'in1':
        data = scope._data_ch1
        print(f"  Using channel 1 data")
    else:
        data = scope._data_ch2
        print(f"  Using channel 2 data")

    times = scope.times

    print(f"  Retrieved {len(data)} samples")
    print(f"  Time array length: {len(times)}")

    if len(data) > 0:
        print(f"\n[7] Data analysis:")
        print(f"  Time range: {times[0]:.6f}s to {times[-1]:.6f}s")
        print(f"  Voltage min: {np.min(data):.4f}V")
        print(f"  Voltage max: {np.max(data):.4f}V")
        print(f"  Voltage mean: {np.mean(data):.4f}V")
        print(f"  Voltage std: {np.std(data):.6f}V")
        print(f"  First 10 samples: {data[:10]}")
    else:
        print("  ❌ No data retrieved!")

except Exception as e:
    print(f"\n❌ Exception during acquisition: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
print("\n[8] Disconnecting...")
worker.disconnect()

print("\n" + "="*70)
print("Debug test complete")
print("="*70)
