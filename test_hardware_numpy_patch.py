#!/usr/bin/env python3
"""
Hardware test with numpy compatibility patch for StemLab library.
"""
import numpy as np
import time
import logging

# Monkey-patch numpy to add back the deprecated np.float alias
# This works around StemLab library's use of deprecated numpy types
if not hasattr(np, 'float'):
    np.float = np.float64
if not hasattr(np, 'int'):
    np.int = np.int_
if not hasattr(np, 'complex'):
    np.complex = np.complex128

from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HARDWARE_IP = '100.107.106.75'

print("="*70)
print("PyRPL Hardware Test with NumPy Compatibility Patch")
print(f"Target: {HARDWARE_IP}")
print("="*70)

worker = PyrplWorker()

# Track status
status_messages = []
def status_handler(msg):
    status_messages.append(msg)
    print(f"STATUS: {msg}")

worker.status_update.connect(status_handler)

# Connect
print("\n[1] Connecting...")
config = {'hostname': HARDWARE_IP, 'user': 'root', 'password': 'root'}
if not worker.connect(config):
    print("❌ Connection failed")
    exit(1)

print(f"✅ Connected: {worker.get_idn()}")

# Try different trigger configurations
scope = worker.pyrpl.scope

print("\n[2] Testing scope configurations...")

# Configuration 1: Using the scope's curve() method (higher-level API)
print("\n  Test 1: Using curve() method (recommended API)...")
try:
    scope.input1 = 'in1'
    scope.decimation = 64
    scope.trigger_source = 'immediately'
    scope.trigger_level = 0.0

    print(f"  Config: input1={scope.input1}, decimation={scope.decimation}")
    print(f"          trigger_source={scope.trigger_source}")

    # Use the higher-level curve() API instead of _start_acquisition()
    print("  Calling scope.curve()...")
    start_time = time.time()
    data = scope.curve()
    elapsed = time.time() - start_time

    print(f"  ✓ Got data in {elapsed:.3f}s: {len(data)} samples")
    print(f"  Data range: min={np.min(data):.4f}V, max={np.max(data):.4f}V")
    print(f"  Mean: {np.mean(data):.4f}V, Std: {np.std(data):.6f}V")

except Exception as e:
    print(f"  ✗ Failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
print("\n[3] Disconnecting...")
worker.disconnect()

print("\n" + "="*70)
print("Test complete")
print("="*70)
