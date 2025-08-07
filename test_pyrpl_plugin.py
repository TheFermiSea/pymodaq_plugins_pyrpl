#!/usr/bin/env python
"""
Test script for the PyRPL 0D Viewer Plugin

This script validates the plugin functionality in mock mode without requiring
actual Red Pitaya hardware.
"""

import sys
import os
import numpy as np

# Add source path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_plugin_structure():
    """Test basic plugin structure and imports."""
    print("=== Testing Plugin Structure ===")
    
    try:
        # Test basic PyMoDAQ imports
        from pymodaq_data import DataRaw, DataToExport
        print("✓ PyMoDAQ data classes available")
        
        # Test basic plugin structure (without full initialization)
        import pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL as plugin_module
        print("✓ Plugin module imported successfully")
        
        # Check required classes
        assert hasattr(plugin_module, 'DAQ_0DViewer_PyRPL')
        assert hasattr(plugin_module, 'MockPyRPLConnection')
        print("✓ Required classes found")
        
        return True
        
    except Exception as e:
        print(f"✗ Structure test failed: {e}")
        return False

def test_mock_connection():
    """Test mock connection functionality."""
    print("\n=== Testing Mock Connection ===")
    
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import MockPyRPLConnection
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import InputChannel, PIDChannel
        
        # Create mock connection
        mock_conn = MockPyRPLConnection('test-host')
        print("✓ Mock connection created")
        
        # Test voltage reading
        voltage1 = mock_conn.read_voltage(InputChannel.IN1)
        voltage2 = mock_conn.read_voltage(InputChannel.IN2)
        print(f"✓ Mock voltages: IN1={voltage1:.3f}V, IN2={voltage2:.3f}V")
        
        # Test PID setpoint reading
        setpoint = mock_conn.get_pid_setpoint(PIDChannel.PID0)
        print(f"✓ Mock PID setpoint: {setpoint:.3f}V")
        
        # Test disconnect
        mock_conn.disconnect()
        print("✓ Mock disconnect successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock connection test failed: {e}")
        return False

def test_data_structure():
    """Test PyMoDAQ data structure creation."""
    print("\n=== Testing Data Structure ===")
    
    try:
        from pymodaq_data import DataRaw, DataToExport
        
        # Test creating 0D data as plugin would
        test_channels = ['Input 1 (V)', 'Input 2 (V)', 'PID PID0 Setpoint (V)']
        test_voltages = [0.523, 0.298, 0.501]
        
        data_list = []
        for channel, voltage in zip(test_channels, test_voltages):
            data = DataRaw(
                name=channel,
                data=np.array([voltage]),
                labels=[channel], 
                units='V'
            )
            data_list.append(data)
            print(f"✓ Created data for {channel}: {voltage:.3f}V")
        
        # Test export structure
        export_data = DataToExport(name='PyRPL Monitor', data=data_list)
        print(f"✓ Export data structure created with {len(export_data.data)} channels")
        
        return True
        
    except Exception as e:
        print(f"✗ Data structure test failed: {e}")
        return False

def test_plugin_parameters():
    """Test plugin parameter structure."""
    print("\n=== Testing Plugin Parameters ===")
    
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        
        # Create plugin instance (minimal initialization)
        plugin = DAQ_0DViewer_PyRPL()
        plugin.ini_attributes()
        print("✓ Plugin instance created")
        
        # Test parameter structure
        params = plugin.params
        print(f"✓ Parameters defined: {len(params)} groups")
        
        # Find and validate specific parameter groups
        param_groups = {param.get('name'): param for param in params if param.get('name')}
        
        required_groups = ['connection', 'channels', 'acquisition']
        for group in required_groups:
            if group in param_groups:
                children = param_groups[group].get('children', [])
                print(f"✓ Found {group} group with {len(children)} parameters")
            else:
                print(f"✗ Missing parameter group: {group}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Parameter test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("PyRPL 0D Viewer Plugin Test Suite")
    print("=" * 40)
    
    tests = [
        test_plugin_structure,
        test_mock_connection, 
        test_data_structure,
        test_plugin_parameters
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Plugin is ready for use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)