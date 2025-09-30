#!/usr/bin/env python3
"""
Simple PyRPL connection test with full error reporting
"""

import sys
import traceback

# Apply compatibility patches FIRST
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
print("Compatibility patches applied")

# Now import PyRPL
import pyrpl
print(f"PyRPL version: {pyrpl.__version__}")

# Try connecting
HOST = "100.107.106.75"
print(f"\nConnecting to {HOST}...")

try:
    p = pyrpl.Pyrpl(
        hostname=HOST,
        gui=False,
        reloadserver=False,
        reloadfpga=False,
        timeout=10,
        config='simple_test'
    )
    print("✓ Connection successful!")
    
    # Try accessing the device
    rp = p.rp
    print(f"✓ Got Red Pitaya object: {type(rp)}")
    
    # Try reading voltage
    sampler = rp.sampler
    v1 = sampler.in1
    print(f"✓ IN1 voltage: {v1:.6f}V")
    
except Exception as e:
    print(f"\n✗ Connection failed:")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
