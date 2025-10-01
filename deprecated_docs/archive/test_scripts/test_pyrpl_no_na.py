#!/usr/bin/env python3
"""
Test PyRPL connection avoiding Network Analyzer initialization issues
"""

import sys
import os

# Apply compatibility patches FIRST
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
print("Compatibility patches applied")

# Now import PyRPL
import pyrpl
print(f"PyRPL version: {pyrpl.__version__}")

# Try connecting with a config that minimizes module initialization
HOST = "100.107.106.75"
print(f"\nConnecting to {HOST} (avoiding network analyzer)...")

# Create a minimal config file to avoid network analyzer issues
import tempfile
import yaml
from pathlib import Path

config_dir = Path.home() / "pyrpl_user_dir" / "config"
config_dir.mkdir(parents=True, exist_ok=True)
config_file = config_dir / "test_minimal.yml"

# Minimal config that might avoid the network analyzer issue
minimal_config = {
    'network_analyzer': {
        'rbw': 1000.0,  # Set a non-zero resolution bandwidth
        'points': 1001,
        'start_freq': 1000.0,
        'stop_freq': 10000.0
    }
}

with open(config_file, 'w') as f:
    yaml.dump(minimal_config, f)

print(f"Created minimal config at: {config_file}")

try:
    p = pyrpl.Pyrpl(
        hostname=HOST,
        gui=False,
        reloadserver=False,
        reloadfpga=False,
        timeout=10,
        config='test_minimal'
    )
    print("✓ Connection successful!")
    
    # Try accessing the device
    rp = p.rp
    print(f"✓ Got Red Pitaya object: {type(rp)}")
    
    # Try reading voltage
    sampler = rp.sampler
    v1 = sampler.in1
    v2 = sampler.in2
    print(f"✓ IN1 voltage: {v1:.6f}V")
    print(f"✓ IN2 voltage: {v2:.6f}V")
    
    # Test ASG
    asg0 = rp.asg0
    print(f"✓ ASG0 available: {type(asg0)}")
    
    # Test PID
    pid0 = rp.pid0
    print(f"✓ PID0 available: {type(pid0)}")
    
    # Test Scope
    scope = rp.scope
    print(f"✓ Scope available: {type(scope)}")
    
    print("\n✅ All basic hardware modules accessible!")
    
except Exception as e:
    print(f"\n✗ Connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
