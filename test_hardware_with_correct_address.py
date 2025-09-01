#!/usr/bin/env python3
"""
Test PyRPL Hardware Connection with Correct Address

This script tests the PyRPL connection using the correct Red Pitaya address
rp-f08d6c.local and validates all hardware modules.
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_pyrpl_connection():
    """Test basic PyRPL connection with correct address"""
    logger.info("Testing PyRPL connection to rp-f08d6c.local...")
    
    try:
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
        
        # Test connection
        manager = PyRPLManager()
        connection = manager.get_connection('rp-f08d6c.local')
        
        logger.info("✅ PyRPL connection successful!")
        logger.info(f"Connected to: {connection.hostname}")
        logger.info(f"PyRPL instance: {connection.pyrpl}")
        
        # Test basic hardware access
        if hasattr(connection.pyrpl, 'rp'):
            logger.info("✅ Red Pitaya hardware accessible")
            
            # Test sampler (voltage reading)
            if hasattr(connection.pyrpl.rp, 'sampler'):
                voltage = connection.pyrpl.rp.sampler.in1
                logger.info(f"✅ Input 1 voltage: {voltage:.6f} V")
            
        connection.disconnect()
        logger.info("✅ Connection closed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ PyRPL connection failed: {e}")
        return False

def test_all_hardware_modules():
    """Test all PyRPL hardware modules"""
    logger.info("Testing all PyRPL hardware modules...")
    
    try:
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
        
        manager = PyRPLManager()
        connection = manager.get_connection('rp-f08d6c.local')
        rp = connection.pyrpl.rp
        
        results = {}
        
        # Test PID modules
        for i in range(3):
            try:
                pid = getattr(rp, f'pid{i}')
                pid.setpoint = 0.0  # Safe setpoint
                pid.output_direct = 'off'  # Ensure output is off
                results[f'PID{i}'] = "✅ OK"
                logger.info(f"✅ PID{i} module operational")
            except Exception as e:
                results[f'PID{i}'] = f"❌ Error: {e}"
                logger.error(f"❌ PID{i} failed: {e}")
        
        # Test ASG modules
        for i in range(2):
            try:
                asg = getattr(rp, f'asg{i}')
                asg.setup(frequency=1000, amplitude=0.1, offset=0.0, waveform='sin')
                results[f'ASG{i}'] = "✅ OK"
                logger.info(f"✅ ASG{i} module operational")
            except Exception as e:
                results[f'ASG{i}'] = f"❌ Error: {e}"
                logger.error(f"❌ ASG{i} failed: {e}")
        
        # Test Scope
        try:
            scope = rp.scope
            scope.input1 = 'in1'
            scope.input2 = 'in2' 
            scope.decimation = 64
            results['Scope'] = "✅ OK"
            logger.info("✅ Scope module operational")
        except Exception as e:
            results['Scope'] = f"❌ Error: {e}"
            logger.error(f"❌ Scope failed: {e}")
        
        # Test IQ modules
        for i in range(3):
            try:
                iq = getattr(rp, f'iq{i}')
                iq.setup(frequency=1000, bandwidth=10)
                results[f'IQ{i}'] = "✅ OK"
                logger.info(f"✅ IQ{i} module operational")
            except Exception as e:
                results[f'IQ{i}'] = f"❌ Error: {e}"
                logger.error(f"❌ IQ{i} failed: {e}")
        
        # Test Sampler
        try:
            sampler = rp.sampler
            voltage1 = sampler.in1
            voltage2 = sampler.in2
            results['Sampler'] = "✅ OK"
            logger.info(f"✅ Sampler operational - IN1: {voltage1:.6f}V, IN2: {voltage2:.6f}V")
        except Exception as e:
            results['Sampler'] = f"❌ Error: {e}"
            logger.error(f"❌ Sampler failed: {e}")
        
        connection.disconnect()
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("HARDWARE MODULE TEST RESULTS:")
        logger.info("="*50)
        for module, status in results.items():
            logger.info(f"{module:10}: {status}")
        
        success_count = sum(1 for status in results.values() if "✅" in status)
        total_count = len(results)
        logger.info(f"\nOverall: {success_count}/{total_count} modules successful")
        
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"❌ Hardware module test failed: {e}")
        return False

def test_plugin_integration():
    """Test PyMoDAQ plugin integration with real hardware"""
    logger.info("Testing PyMoDAQ plugin integration...")
    
    try:
        # Test PID plugin
        logger.info("Testing PID plugin...")
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
        
        pid_plugin = DAQ_Move_PyRPL_PID()
        pid_plugin.settings.child('redpitaya_host').setValue('rp-f08d6c.local')
        pid_plugin.settings.child('mock_mode').setValue(False)  # Real hardware
        pid_plugin.ini_stage()
        
        # Test basic operations
        current_pos = pid_plugin.get_actuator_value()
        logger.info(f"✅ PID plugin - Current position: {current_pos}")
        
        pid_plugin.close()
        logger.info("✅ PID plugin test successful")
        
        # Test Voltage Monitor plugin
        logger.info("Testing Voltage Monitor plugin...")
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        
        voltage_plugin = DAQ_0DViewer_PyRPL()
        voltage_plugin.settings.child('redpitaya_host').setValue('rp-f08d6c.local')
        voltage_plugin.settings.child('mock_mode').setValue(False)  # Real hardware
        voltage_plugin.ini_detector()
        
        # Test data acquisition
        data = voltage_plugin.grab_data()
        logger.info(f"✅ Voltage Monitor plugin - Data acquired: {len(data)} points")
        
        voltage_plugin.close()
        logger.info("✅ Voltage Monitor plugin test successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin integration test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting PyRPL Hardware Tests with Correct Address (rp-f08d6c.local)")
    logger.info("="*60)
    
    # Test 1: Basic connection
    logger.info("\n1. Testing basic PyRPL connection...")
    connection_ok = test_pyrpl_connection()
    
    if not connection_ok:
        logger.error("❌ Basic connection failed - aborting further tests")
        return False
    
    # Test 2: Hardware modules
    logger.info("\n2. Testing hardware modules...")
    modules_ok = test_all_hardware_modules()
    
    # Test 3: Plugin integration 
    logger.info("\n3. Testing plugin integration...")
    plugins_ok = test_plugin_integration()
    
    # Final results
    logger.info("\n" + "="*60)
    logger.info("FINAL TEST RESULTS:")
    logger.info("="*60)
    logger.info(f"Basic Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    logger.info(f"Hardware Modules: {'✅ PASS' if modules_ok else '❌ FAIL'}")
    logger.info(f"Plugin Integration: {'✅ PASS' if plugins_ok else '❌ FAIL'}")
    
    all_passed = connection_ok and modules_ok and plugins_ok
    logger.info(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)