#!/usr/bin/env python3
"""
Test PyMoDAQ plugin initialization in mock mode
"""
import sys
import time
from pathlib import Path

# Add the source directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_asg_plugin_initialization():
    """Test ASG plugin initialization similar to how PyMoDAQ would do it"""
    print("="*60)
    print("Testing ASG Plugin Initialization (PyMoDAQ-style)")
    print("="*60)
    
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG
        from pymodaq_gui.parameter import Parameter, ParameterTree
        
        # Create plugin instance
        plugin = DAQ_Move_PyRPL_ASG()
        print("✓ ASG Plugin instantiated")
        
        # Initialize attributes (this is called by PyMoDAQ)
        plugin.ini_attributes()
        print("✓ Plugin attributes initialized")
        
        # Create parameter tree (this simulates PyMoDAQ's parameter setup)
        param_tree = ParameterTree()
        plugin.settings = param_tree.setParameters({'name': 'Settings', 'type': 'group', 'children': plugin.params}, show_top=False)
        print("✓ Parameter tree created")
        
        # Enable mock mode
        plugin.settings.child('dev_settings', 'mock_mode').setValue(True)
        print("✓ Mock mode enabled")
        
        # Initialize stage (this is what PyMoDAQ calls)
        info = plugin.ini_stage()
        print(f"✓ Stage initialized: {info}")
        
        # Test basic operations
        if plugin.mock_mode:
            print("\nTesting basic operations in mock mode:")
            
            # Test move absolute
            plugin.move_abs(1000.0)  # 1kHz
            current_freq = plugin.get_actuator_value()
            print(f"✓ Move absolute to 1kHz: current = {current_freq}Hz")
            
            # Test move relative
            plugin.move_rel(500.0)  # +500Hz
            new_freq = plugin.get_actuator_value()
            print(f"✓ Move relative +500Hz: current = {new_freq}Hz")
            
            # Test move home
            plugin.move_home()
            home_freq = plugin.get_actuator_value()
            print(f"✓ Move home: current = {home_freq}Hz")
        
        # Clean shutdown
        plugin.close()
        print("✓ Plugin closed cleanly")
        
        return True
        
    except Exception as e:
        print(f"❌ ASG Plugin initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scope_plugin_basic():
    """Test scope plugin basic functionality"""
    print("\n" + "="*60)
    print("Testing Scope Plugin Basic Functionality")
    print("="*60)
    
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope
        
        # Create plugin instance
        plugin = DAQ_1DViewer_PyRPL_Scope()
        print("✓ Scope Plugin instantiated")
        
        # Initialize attributes
        plugin.ini_attributes()
        print("✓ Plugin attributes initialized")
        
        # Check basic attributes
        print(f"✓ Plugin has {len(plugin.params)} parameters")
        
        return True
        
    except Exception as e:
        print(f"❌ Scope Plugin test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run plugin initialization tests"""
    print("PyMoDAQ PyRPL Plugin Initialization Test Suite")
    print("=" * 60)
    
    # Test ASG plugin
    asg_ok = test_asg_plugin_initialization()
    
    # Test Scope plugin
    scope_ok = test_scope_plugin_basic()
    
    # Summary
    print("\n" + "="*60)
    print("Plugin Initialization Test Results")
    print("="*60)
    print(f"ASG Plugin Test: {'✓ PASS' if asg_ok else '✗ FAIL'}")
    print(f"Scope Plugin Test: {'✓ PASS' if scope_ok else '✗ FAIL'}")
    
    if asg_ok and scope_ok:
        print(f"\n🎉 All plugin initialization tests PASSED!")
        print("✓ Plugins ready for PyMoDAQ Dashboard integration")
        print("✓ Mock mode fully functional")
        print("\nNext steps:")
        print("1. Launch PyMoDAQ Dashboard: python -m pymodaq.dashboard") 
        print("2. Add PyRPL plugins in mock mode")
        print("3. Test with real hardware when PyRPL/Qt issue resolved")
    else:
        print(f"\n❌ Some plugin initialization tests failed")

if __name__ == '__main__':
    main()