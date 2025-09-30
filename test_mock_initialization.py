#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test PyRPL_Scope_IPC plugin initialization in mock mode.

This simulates what PyMoDAQ does when you click "Init. Detector"
"""

import sys
from PyQt6 import QtWidgets, QtCore

def test_plugin_mock_mode():
    """Test plugin initialization in mock mode."""
    
    print("="*60)
    print("Testing PyRPL_Scope_IPC Plugin - Mock Mode")
    print("="*60)
    
    # Create QApplication (required by PyMoDAQ)
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    print("\n1. Importing plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope_IPC import DAQ_1DViewer_PyRPL_Scope_IPC
        print("   ✓ Plugin imported successfully")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n2. Creating plugin instance...")
    try:
        plugin = DAQ_1DViewer_PyRPL_Scope_IPC()
        print("   ✓ Plugin instance created")
    except Exception as e:
        print(f"   ✗ Instance creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n3. Enabling mock mode...")
    try:
        plugin.settings.child('dev', 'mock_mode').setValue(True)
        mock_enabled = plugin.settings['dev', 'mock_mode']
        print(f"   ✓ Mock mode enabled: {mock_enabled}")
    except Exception as e:
        print(f"   ✗ Mock mode setting failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n4. Initializing detector...")
    try:
        status = plugin.ini_detector()
        print(f"   Status: {status}")
        
        if status.initialized:
            print(f"   ✓ Initialization successful!")
            print(f"   Info: {status.info}")
        else:
            print(f"   ✗ Initialization failed!")
            print(f"   Info: {status.info}")
            return False
            
    except Exception as e:
        print(f"   ✗ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n5. Testing data acquisition...")
    try:
        # Connect signal to capture data
        data_received = []
        
        def on_data(data_list):
            print(f"   ✓ Data received: {len(data_list)} channel(s)")
            for data in data_list:
                print(f"      - {data.name}: {len(data.data[0])} points")
            data_received.append(data_list)
        
        plugin.data_grabed_signal.connect(on_data)
        
        # Trigger acquisition
        plugin.grab_data()
        
        # Process events to let signal propagate
        app.processEvents()
        
        if data_received:
            print("   ✓ Data acquisition successful!")
        else:
            print("   ✗ No data received")
            return False
            
    except Exception as e:
        print(f"   ✗ Data acquisition error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n6. Closing plugin...")
    try:
        plugin.close()
        print("   ✓ Plugin closed successfully")
    except Exception as e:
        print(f"   ⚠ Close warning: {e}")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED - Mock mode works correctly!")
    print("="*60)
    
    return True


if __name__ == '__main__':
    success = test_plugin_mock_mode()
    sys.exit(0 if success else 1)
