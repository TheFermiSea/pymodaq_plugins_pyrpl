#!/usr/bin/env python3
"""
Debug the patching process
"""

# Step 1: Import compatibility patches
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
print("✓ Wrapper imported")

# Step 2: Import PyRPL
import pyrpl
import pyrpl.attributes as pyrpl_attrs
print(f"✓ PyRPL imported (version: {pyrpl.__version__})")

# Step 3: Check what's available
print("\nInspecting pyrpl.attributes:")
print(f"  Has FrequencyRegister: {hasattr(pyrpl_attrs, 'FrequencyRegister')}")

if hasattr(pyrpl_attrs, 'FrequencyRegister'):
    FR = pyrpl_attrs.FrequencyRegister
    print(f"  FrequencyRegister type: {type(FR)}")
    print(f"  FrequencyRegister attributes: {[a for a in dir(FR) if not a.startswith('__')][:20]}")
    
    # Check for _MAXSHIFT method
    print(f"\n  Looking for _MAXSHIFT or similar:")
    for attr in dir(FR):
        if 'max' in attr.lower() or 'shift' in attr.lower():
            val = getattr(FR, attr)
            print(f"    {attr}: {type(val)}")
    
    # Check for _MINBW method
    print(f"\n  Looking for _MINBW or similar:")
    for attr in dir(FR):
        if 'min' in attr.lower() or 'bw' in attr.lower():
            val = getattr(FR, attr)
            print(f"    {attr}: {type(val)}")

# Now try to patch
print("\n\nAttempting to apply patches...")
from pymodaq_plugins_pyrpl.utils import pyrpl_fixes
result = pyrpl_fixes._patch_frequency_register_zero_division()
print(f"Patch result: {result}")
