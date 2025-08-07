#!/usr/bin/env python3
"""
PyMoDAQ PyRPL Integration Launcher
Applies compatibility patches and launches PyMoDAQ with PyRPL plugins
"""

def apply_compatibility_patches():
    """Apply all necessary compatibility patches"""
    print("🔧 Applying compatibility patches...")
    
    # 1. PyRPL Python 3.12 compatibility
    import collections.abc
    import collections
    if not hasattr(collections, 'Mapping'):
        collections.Mapping = collections.abc.Mapping
        collections.MutableMapping = collections.abc.MutableMapping
        print("  ✅ PyRPL collections compatibility applied")
    
    # 2. Verify PyQtGraph DockLabel is available
    try:
        from pyqtgraph.dockarea import DockLabel
        print("  ✅ PyQtGraph DockLabel compatibility confirmed")
    except ImportError:
        print("  ❌ PyQtGraph DockLabel missing - run the DockLabel fix first")
        return False
    
    return True

def launch_pymodaq():
    """Launch PyMoDAQ Dashboard"""
    print("\n🚀 Launching PyMoDAQ Dashboard with PyRPL plugins...")
    
    try:
        # Import and launch PyMoDAQ
        import sys
        
        # Ensure we don't pass unwanted arguments to PyMoDAQ
        original_argv = sys.argv.copy()
        sys.argv = ['dashboard']
        
        # Import and run the dashboard main function
        from pymodaq.dashboard import main as dashboard_main
        
        print("🎉 PyMoDAQ Dashboard starting...")
        print("\n📦 Available PyRPL Plugins:")
        print("  🎵 DAQ_Move_PyRPL_ASG - Signal Generator Control")
        print("  🎛️  DAQ_Move_PyRPL_PID - PID Controller Setpoints") 
        print("  📡 DAQ_0DViewer_PyRPL - Voltage Monitoring")
        print("  🔒 DAQ_0DViewer_PyRPL_IQ - Lock-in Amplifier")
        print("  📊 DAQ_1DViewer_PyRPL_Scope - Oscilloscope")
        print("\n📡 Hardware Configuration:")
        print("  • Red Pitaya IP: rp-f08d6c.local (verified)")
        print("  • Mock mode available for testing")
        print("\n💡 Usage:")
        print("  1. Click 'Add Actuator' or 'Add Detector'")
        print("  2. Select PyRPL plugins from dropdown")
        print("  3. Configure Red Pitaya host: rp-f08d6c.local")
        print("  4. Enable mock mode if no hardware")
        
        # Launch the dashboard
        dashboard_main()
        
        # Restore original argv
        sys.argv = original_argv
        
    except Exception as e:
        print(f"\n❌ Dashboard launch failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main launcher function"""
    print("=" * 60)
    print("🎉 PyMoDAQ PyRPL Integration Launcher")
    print("=" * 60)
    
    # Apply compatibility patches
    if not apply_compatibility_patches():
        print("\n❌ Compatibility patches failed!")
        print("💡 Run the PyQtGraph DockLabel fix first:")
        print("   python /home/maitai/pymodaq_plugins_pyrpl/pyqtgraph_compat.py")
        return
    
    # Launch PyMoDAQ
    if launch_pymodaq():
        print("\n✅ PyMoDAQ launched successfully!")
    else:
        print("\n❌ PyMoDAQ launch failed!")

if __name__ == "__main__":
    main()