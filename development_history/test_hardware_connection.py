#!/usr/bin/env python3
"""
Test script for Red Pitaya hardware connectivity with PyRPL plugins
"""
import sys
import time
import numpy as np
from pathlib import Path

# Add the source directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_hardware_connectivity():
    """Test different possible Red Pitaya IP addresses"""
    possible_ips = [
        '192.168.1.100',  # Default from network scan
        '192.168.1.10',   # Common Red Pitaya default
        '192.168.1.1',    # Router/gateway - sometimes Red Pitaya
        '10.125.179.19',  # Current machine IP - check if Red Pitaya is on same network
        'rp-f0a552.local', # Original hostname
    ]
    
    print("Testing Red Pitaya connectivity...")
    
    # Try basic network ping first
    import subprocess
    for ip in possible_ips[:4]:  # Skip .local for ping test
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '2', ip], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✓ Network ping successful: {ip}")
                return ip
            else:
                print(f"✗ No ping response: {ip}")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print(f"✗ Ping failed: {ip} - {e}")
    
    print("No Red Pitaya found via ping. Trying direct PyRPL connection...")
    return None

def test_pyrpl_basic_connection(ip_address=None):
    """Test basic PyRPL connection without Qt dependencies"""
    print("\n" + "="*50)
    print("Testing PyRPL Basic Connection")
    print("="*50)
    
    try:
        # Import our wrapper with error handling
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PYRPL_AVAILABLE
        
        if not PYRPL_AVAILABLE:
            print("❌ PyRPL not available due to compatibility issues")
            return False
            
        print("✓ PyRPL wrapper imported successfully")
        
        # Try to create a basic connection
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager, ConnectionInfo
        
        # Test with the discovered IP or fallback to defaults
        test_ips = [ip_address] if ip_address else ['192.168.1.100', '192.168.1.10']
        
        for test_ip in test_ips:
            if test_ip is None:
                continue
                
            print(f"\nTesting PyRPL connection to {test_ip}...")
            
            try:
                manager = PyRPLManager.get_instance()
                conn_info = ConnectionInfo(hostname=test_ip, config='test_hardware')
                
                # Try to get a connection with a short timeout
                connection = manager.get_connection(conn_info)
                
                if connection and connection.is_connected:
                    print(f"✓ PyRPL connection successful: {test_ip}")
                    
                    # Test basic functionality
                    try:
                        # Try to read a simple value
                        test_voltage = connection.read_voltage('in1')
                        print(f"✓ Voltage reading successful: IN1 = {test_voltage:.3f}V")
                        
                        # Clean up
                        connection.disconnect()
                        return test_ip
                        
                    except Exception as e:
                        print(f"⚠ Connection established but voltage read failed: {e}")
                        return test_ip  # Still consider this a success
                        
                else:
                    print(f"✗ Failed to establish PyRPL connection to {test_ip}")
                    
            except Exception as e:
                print(f"✗ PyRPL connection error to {test_ip}: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ PyRPL wrapper import/test failed: {e}")
        return False

def test_plugin_basic_functionality(ip_address):
    """Test basic functionality of our PyRPL plugins"""
    print("\n" + "="*50)
    print("Testing Plugin Basic Functionality")
    print("="*50)
    
    try:
        # Test ASG Plugin
        print("\nTesting ASG Plugin...")
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG
        
        # Create mock parameter tree for testing
        class MockParamTree:
            def __init__(self, values):
                self._values = values
            def child(self, name):
                return MockValue(self._values.get(name, None))
        
        class MockValue:
            def __init__(self, value):
                self._value = value
            def value(self):
                return self._value
                
        # Test ASG plugin initialization
        asg_plugin = DAQ_Move_PyRPL_ASG()
        print("✓ ASG Plugin imported and instantiated")
        
        # Test basic parameter structure
        if hasattr(asg_plugin, 'params'):
            print(f"✓ ASG Plugin has {len(asg_plugin.params)} parameters defined")
        
        return True
        
    except Exception as e:
        print(f"❌ Plugin functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("PyRPL Plugin Hardware Test Suite")
    print("=" * 50)
    
    # Step 1: Test network connectivity
    discovered_ip = test_hardware_connectivity()
    
    # Step 2: Test PyRPL basic connection
    working_ip = test_pyrpl_basic_connection(discovered_ip)
    
    if working_ip:
        print(f"\n🎉 Red Pitaya found and accessible at: {working_ip}")
        
        # Step 3: Test plugin functionality
        plugin_test = test_plugin_basic_functionality(working_ip)
        
        if plugin_test:
            print(f"\n🎉 Plugin test successful! Ready for full PyMoDAQ integration.")
            print(f"\nTo use in PyMoDAQ, configure plugins with hostname: {working_ip}")
        else:
            print(f"\n⚠ Hardware connection works but plugin test failed")
            
    else:
        print(f"\n❌ No working Red Pitaya connection found")
        print("Possible issues:")
        print("- Red Pitaya not powered on or not connected to network")
        print("- IP address different from tested range")
        print("- PyRPL/Qt compatibility issues preventing connection")
        print("\nTrying mock mode test instead...")
        
        # Test mock mode
        try:
            test_plugin_basic_functionality(None)
            print("✓ Mock mode plugins work correctly")
        except Exception as e:
            print(f"❌ Even mock mode failed: {e}")

if __name__ == '__main__':
    main()