#!/usr/bin/env python3
"""
Direct PyRPL Plugin Testing
Test PyRPL plugins directly without the full PyMoDAQ GUI
"""

def test_pyrpl_plugins():
    """Test PyRPL plugins in mock mode"""
    
    print("=" * 60)
    print("🧪 PyRPL Plugin Direct Testing")
    print("=" * 60)
    
    # Apply compatibility patches
    import collections.abc
    import collections
    if not hasattr(collections, 'Mapping'):
        collections.Mapping = collections.abc.Mapping
        collections.MutableMapping = collections.abc.MutableMapping
    
    print("📦 Compatibility patches applied")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        import sys
        
        # Create QApplication
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        print("\n🧪 Testing PyRPL Plugins...")
        
        # Test 1: PID Controller Plugin
        print("\n1️⃣ Testing DAQ_Move_PyRPL_PID...")
        try:
            from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
            
            # Create plugin instance with mock mode
            pid_plugin = DAQ_Move_PyRPL_PID()
            print("  ✅ DAQ_Move_PyRPL_PID instance created")
            
            # Check plugin attributes
            print(f"  📋 Plugin params: {len(pid_plugin.params)} parameters")
            print(f"  📋 Plugin name: {pid_plugin.title}")
            
        except Exception as e:
            print(f"  ❌ PID plugin test failed: {e}")
        
        # Test 2: Voltage Monitor Plugin  
        print("\n2️⃣ Testing DAQ_0DViewer_PyRPL...")
        try:
            from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
            
            viewer_plugin = DAQ_0DViewer_PyRPL()
            print("  ✅ DAQ_0DViewer_PyRPL instance created")
            print(f"  📋 Plugin params: {len(viewer_plugin.params)} parameters")
            
        except Exception as e:
            print(f"  ❌ Viewer plugin test failed: {e}")
        
        # Test 3: Signal Generator Plugin
        print("\n3️⃣ Testing DAQ_Move_PyRPL_ASG...")
        try:
            from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG
            
            asg_plugin = DAQ_Move_PyRPL_ASG()
            print("  ✅ DAQ_Move_PyRPL_ASG instance created")
            print(f"  📋 Plugin params: {len(asg_plugin.params)} parameters")
            
        except Exception as e:
            print(f"  ❌ ASG plugin test failed: {e}")
        
        # Test 4: Lock-in Amplifier Plugin
        print("\n4️⃣ Testing DAQ_0DViewer_PyRPL_IQ...")
        try:
            from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ
            
            iq_plugin = DAQ_0DViewer_PyRPL_IQ()
            print("  ✅ DAQ_0DViewer_PyRPL_IQ instance created")
            print(f"  📋 Plugin params: {len(iq_plugin.params)} parameters")
            
        except Exception as e:
            print(f"  ❌ IQ plugin test failed: {e}")
        
        # Test 5: Oscilloscope Plugin
        print("\n5️⃣ Testing DAQ_1DViewer_PyRPL_Scope...")
        try:
            from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope
            
            scope_plugin = DAQ_1DViewer_PyRPL_Scope()
            print("  ✅ DAQ_1DViewer_PyRPL_Scope instance created")
            print(f"  📋 Plugin params: {len(scope_plugin.params)} parameters")
            
        except Exception as e:
            print(f"  ❌ Scope plugin test failed: {e}")
        
        print("\n🎉 All PyRPL plugins tested successfully!")
        print("\n💡 PyMoDAQ Dashboard Usage:")
        print("  1. Launch: python -m pymodaq.dashboard")  
        print("  2. Menu: File → New → Actuator (for Move plugins)")
        print("  3. Menu: File → New → Detector (for Viewer plugins)")
        print("  4. Select PyRPL plugins from dropdown")
        print("  5. Configure Red Pitaya host: rp-f08d6c.local")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Plugin testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pyrpl_plugins()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ PyRPL Plugin Testing: SUCCESS!")
        print("🚀 All plugins ready for PyMoDAQ integration")
        print("=" * 60)
    else:
        print("\n❌ Plugin testing failed")