#!/usr/bin/env python3
"""
Final PyRPL Hardware Test

This script uses the PyMoDAQ PyRPL plugins directly to test real hardware
with the correct Red Pitaya address rp-f08d6c.local
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

def test_pyrpl_plugins():
    """Test PyRPL plugins with real hardware"""
    logger.info("Testing PyMoDAQ PyRPL plugins with real hardware...")
    
    results = {}
    
    # Test 1: PID Plugin
    logger.info("\n1. Testing PID Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
        
        pid_plugin = DAQ_Move_PyRPL_PID()
        
        # Configure for real hardware
        pid_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        pid_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize 
        pid_plugin.ini_stage()
        logger.info("✅ PID plugin initialized")
        
        # Test get position
        position = pid_plugin.get_actuator_value()
        logger.info(f"✅ PID current position: {position}")
        results['PID Plugin'] = "✅ OK"
        
        # Clean up
        pid_plugin.close()
        
    except Exception as e:
        logger.error(f"❌ PID plugin failed: {e}")
        results['PID Plugin'] = f"❌ {e}"
    
    # Test 2: Voltage Monitor Plugin
    logger.info("\n2. Testing Voltage Monitor Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        
        voltage_plugin = DAQ_0DViewer_PyRPL()
        
        # Configure for real hardware  
        voltage_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        voltage_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize
        voltage_plugin.ini_detector()
        logger.info("✅ Voltage Monitor plugin initialized")
        
        # Test data acquisition
        data = voltage_plugin.grab_data()
        logger.info(f"✅ Voltage Monitor data: {len(data)} points")
        for i, data_array in enumerate(data):
            logger.info(f"  Channel {i}: {data_array.data[0]:.6f}V")
        results['Voltage Monitor'] = "✅ OK"
        
        # Clean up
        voltage_plugin.close()
        
    except Exception as e:
        logger.error(f"❌ Voltage Monitor plugin failed: {e}")
        results['Voltage Monitor'] = f"❌ {e}"
    
    # Test 3: ASG Plugin
    logger.info("\n3. Testing ASG Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG
        
        asg_plugin = DAQ_Move_PyRPL_ASG()
        
        # Configure for real hardware
        asg_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        asg_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize
        asg_plugin.ini_stage()
        logger.info("✅ ASG plugin initialized")
        
        # Test get position (frequency)
        frequency = asg_plugin.get_actuator_value()
        logger.info(f"✅ ASG current frequency: {frequency} Hz")
        results['ASG Plugin'] = "✅ OK"
        
        # Clean up
        asg_plugin.close()
        
    except Exception as e:
        logger.error(f"❌ ASG plugin failed: {e}")
        results['ASG Plugin'] = f"❌ {e}"
    
    # Test 4: Scope Plugin
    logger.info("\n4. Testing Scope Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope
        
        scope_plugin = DAQ_1DViewer_PyRPL_Scope()
        
        # Configure for real hardware
        scope_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        scope_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize
        scope_plugin.ini_detector()
        logger.info("✅ Scope plugin initialized")
        
        # Test data acquisition
        data = scope_plugin.grab_data()
        logger.info(f"✅ Scope data: {len(data[0].data)} samples")
        results['Scope Plugin'] = "✅ OK"
        
        # Clean up
        scope_plugin.close()
        
    except Exception as e:
        logger.error(f"❌ Scope plugin failed: {e}")
        results['Scope Plugin'] = f"❌ {e}"
    
    # Test 5: IQ Plugin
    logger.info("\n5. Testing IQ Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ
        
        iq_plugin = DAQ_0DViewer_PyRPL_IQ()
        
        # Configure for real hardware
        iq_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        iq_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize
        iq_plugin.ini_detector()
        logger.info("✅ IQ plugin initialized")
        
        # Test data acquisition
        data = iq_plugin.grab_data()
        logger.info(f"✅ IQ data: {len(data)} points")
        for i, data_array in enumerate(data):
            logger.info(f"  IQ{i}: {data_array.data[0]:.6f}")
        results['IQ Plugin'] = "✅ OK"
        
        # Clean up
        iq_plugin.close()
        
    except Exception as e:
        logger.error(f"❌ IQ plugin failed: {e}")
        results['IQ Plugin'] = f"❌ {e}"
    
    return results

def main():
    """Main test function"""
    logger.info("🔬 PyMoDAQ PyRPL Plugin Hardware Validation")
    logger.info("Red Pitaya Address: rp-f08d6c.local")
    logger.info("="*60)
    
    results = test_pyrpl_plugins()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 HARDWARE VALIDATION RESULTS:")
    logger.info("="*60)
    
    success_count = 0
    total_count = len(results)
    
    for plugin, status in results.items():
        logger.info(f"{plugin:20}: {status}")
        if "✅" in status:
            success_count += 1
    
    logger.info("="*60)
    logger.info(f"Summary: {success_count}/{total_count} plugins successful")
    
    if success_count == total_count:
        logger.info("🎉 ALL PLUGINS WORKING WITH REAL HARDWARE!")
        logger.info("✅ Red Pitaya rp-f08d6c.local fully validated")
        logger.info("✅ PyMoDAQ PyRPL integration ready for use")
    elif success_count > 0:
        logger.info("⚠️  PARTIAL SUCCESS - Some plugins working")
        logger.info("Check individual plugin logs for details")
    else:
        logger.info("❌ NO PLUGINS WORKING - Check hardware connection")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)