#!/usr/bin/env python3
"""
Simple test script to diagnose StemLab connection issues.
"""
import sys
import traceback
from stemlab import StemLab

print("=" * 60)
print("Testing StemLab connection to 100.107.106.75")
print("=" * 60)

# Test 1: Try with default parameters (includes FPGA reload)
print("\nTest 1: Connection with default parameters (reloadfpga=True)...")
try:
    stemlab = StemLab(
        hostname='100.107.106.75',
        user='root',
        password='root',
        timeout=10  # Increase timeout to 10 seconds
    )
    print("✓ SUCCESS: Connected with default parameters")
    print(f"  IDN: StemLab on {stemlab.parameters['hostname']}")
    stemlab.end()
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}: {e}")
    traceback.print_exc()

# Test 2: Try without FPGA reload (skip bitfile upload)
print("\nTest 2: Connection without FPGA reload (reloadfpga=False)...")
try:
    stemlab = StemLab(
        hostname='100.107.106.75',
        user='root',
        password='root',
        timeout=10,
        reloadfpga=False  # Skip FPGA reload
    )
    print("✓ SUCCESS: Connected without FPGA reload")
    print(f"  IDN: StemLab on {stemlab.parameters['hostname']}")

    # Test scope access
    print("  Testing scope access...")
    print(f"  Scope object: {stemlab.scope}")

    stemlab.end()
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}: {e}")
    traceback.print_exc()

# Test 3: Try without autostart
print("\nTest 3: Connection without autostart (autostart=False)...")
try:
    stemlab = StemLab(
        hostname='100.107.106.75',
        user='root',
        password='root',
        timeout=10,
        reloadfpga=False,
        autostart=False  # Don't auto-start the client
    )
    print("✓ SUCCESS: Connected without autostart")
    print(f"  IDN: StemLab on {stemlab.parameters['hostname']}")
    stemlab.end()
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Connection tests complete")
print("=" * 60)
