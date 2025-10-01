#!/usr/bin/env python3
"""
Test PyRPL connection with all bug fixes applied
"""

import sys

# Step 1: Apply compatibility patches from wrapper
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
print("✓ Compatibility patches applied")

# Step 2: Import the fixes module (but don't apply yet)
from pymodaq_plugins_pyrpl.utils import pyrpl_fixes

# Step 3: Import PyRPL (this triggers the import)
import pyrpl
print(f"✓ PyRPL imported (version: {pyrpl.__version__})")

# Step 4: NOW apply the fixes IMMEDIATELY after PyRPL import, BEFORE creating Pyrpl()
pyrpl_fixes.apply_all_patches()
print("✓ PyRPL bug fixes applied")

# Step 4: Test connection
HOST = "100.107.106.75"
print(f"\nConnecting to {HOST}...")

try:
    p = pyrpl.Pyrpl(
        hostname=HOST,
        gui=False,
        reloadserver=False,
        reloadfpga=False,
        timeout=10,
        config='test_with_fixes'
    )
    print("✓ Connection successful!")
    
    # Test hardware access
    rp = p.rp
    print(f"✓ Red Pitaya object: {type(rp)}")
    
    # Test voltage reading
    sampler = rp.sampler
    v1 = sampler.in1
    v2 = sampler.in2
    print(f"✓ IN1: {v1:.6f}V")
    print(f"✓ IN2: {v2:.6f}V")
    
    # Test modules
    print(f"✓ PID0: {type(rp.pid0)}")
    print(f"✓ ASG0: {type(rp.asg0)}")
    print(f"✓ Scope: {type(rp.scope)}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
