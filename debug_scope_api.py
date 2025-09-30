#!/usr/bin/env python3
"""
Debug script to inspect PyRPL Scope API
This will connect to the Red Pitaya and show what methods/properties are available
"""
import sys
from pyrpl import Pyrpl

print("Connecting to Red Pitaya...")
p = Pyrpl(
    hostname='100.107.106.75',
    config='debug_test',
    gui=False,
    reloadserver=False,
    reloadfpga=False
)

print("\n" + "="*80)
print("PYRPL SCOPE OBJECT INSPECTION")
print("="*80)

scope = p.rp.scope

print("\n1. Scope object type:")
print(f"   {type(scope)}")

print("\n2. All attributes and methods:")
attrs = [attr for attr in dir(scope) if not attr.startswith('_')]
for attr in sorted(attrs):
    print(f"   - {attr}")

print("\n3. Callable methods:")
methods = [attr for attr in attrs if callable(getattr(scope, attr))]
for method in sorted(methods):
    print(f"   - {method}()")

print("\n4. Properties/attributes:")
properties = [attr for attr in attrs if not callable(getattr(scope, attr))]
for prop in sorted(properties):
    try:
        val = getattr(scope, prop)
        print(f"   - {prop} = {val}")
    except Exception as e:
        print(f"   - {prop} (error accessing: {e})")

print("\n5. Looking for data acquisition methods:")
data_methods = [attr for attr in attrs if any(word in attr.lower() 
    for word in ['data', 'curve', 'acquire', 'run', 'trigger', 'single', 'get'])]
print("   Potential data acquisition methods:")
for method in sorted(data_methods):
    print(f"   - {method}")

print("\n6. Testing scope configuration:")
try:
    scope.input1 = 'in1'
    scope.decimation = 64
    scope.trigger_source = 'immediately'
    print("   ✓ Configuration successful")
    print(f"   - input1: {scope.input1}")
    print(f"   - decimation: {scope.decimation}")
    print(f"   - trigger_source: {scope.trigger_source}")
except Exception as e:
    print(f"   ✗ Configuration failed: {e}")

print("\n7. Looking for the correct way to get data:")
print("   Trying different approaches...")

# Try approach 1: data_avg
try:
    print("\n   Approach 1: scope.data_avg")
    data = scope.data_avg
    print(f"   ✓ SUCCESS! data_avg returned {type(data)} with shape {data.shape if hasattr(data, 'shape') else 'N/A'}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Try approach 2: get_curve
try:
    print("\n   Approach 2: scope.get_curve()")
    data = scope.get_curve()
    print(f"   ✓ SUCCESS! get_curve() returned {type(data)} with shape {data.shape if hasattr(data, 'shape') else 'N/A'}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Try approach 3: single
try:
    print("\n   Approach 3: scope.single()")
    data = scope.single()
    print(f"   ✓ SUCCESS! single() returned {type(data)} with shape {data.shape if hasattr(data, 'shape') else 'N/A'}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Try approach 4: continuous
try:
    print("\n   Approach 4: scope.continuous()")
    scope.continuous()
    print(f"   ✓ continuous() executed")
    # Then try to get data
    if hasattr(scope, 'data_avg'):
        data = scope.data_avg
        print(f"   ✓ data_avg after continuous: {type(data)} with shape {data.shape if hasattr(data, 'shape') else 'N/A'}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

print("\n" + "="*80)
print("INSPECTION COMPLETE")
print("="*80)
