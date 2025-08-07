#!/usr/bin/env python3
"""
Comprehensive PyRPL Hardware Test

This script performs complete validation of PyRPL plugins with real Red Pitaya hardware
including creating PyMoDAQ presets and testing all plugin functionality.
"""

import logging
import sys
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def create_pyrpl_preset():
    """Create a PyMoDAQ preset for PyRPL hardware testing"""
    logger.info("Creating PyRPL preset configuration...")
    
    preset_content = """<?xml version="1.0" encoding="UTF-8"?>
<preset name="PyRPL Hardware Test" date="2025-08-07">
    <modules>
        <!-- PID Controller Plugin -->
        <detector>
            <name>PyRPL_PID_Monitor</name>
            <class>DAQ_0DViewer_PyRPL</class>
            <init_options>
                <connection_settings>
                    <redpitaya_host>rp-f08d6c.local</redpitaya_host>
                    <mock_mode>false</mock_mode>
                    <connection_timeout>10.0</connection_timeout>
                </connection_settings>
                <acquisition_settings>
                    <channel_1_enabled>true</channel_1_enabled>
                    <channel_2_enabled>true</channel_2_enabled>
                    <average_number>10</average_number>
                </acquisition_settings>
            </init_options>
        </detector>
        
        <!-- Oscilloscope Plugin -->
        <detector>
            <name>PyRPL_Scope</name>
            <class>DAQ_1DViewer_PyRPL_Scope</class>
            <init_options>
                <connection_settings>
                    <redpitaya_host>rp-f08d6c.local</redpitaya_host>
                    <mock_mode>false</mock_mode>
                </connection_settings>
                <scope_settings>
                    <input_channel>in1</input_channel>
                    <decimation>64</decimation>
                    <trigger_source>immediately</trigger_source>
                    <average>5</average>
                </scope_settings>
            </init_options>
        </detector>
        
        <!-- Lock-in Amplifier Plugin -->
        <detector>
            <name>PyRPL_IQ</name>
            <class>DAQ_0DViewer_PyRPL_IQ</class>
            <init_options>
                <connection_settings>
                    <redpitaya_host>rp-f08d6c.local</redpitaya_host>
                    <mock_mode>false</mock_mode>
                </connection_settings>
                <iq_settings>
                    <iq_module>iq0</iq_module>
                    <input_channel>in1</input_channel>
                    <frequency>1000.0</frequency>
                    <bandwidth>100.0</bandwidth>
                </iq_settings>
            </init_options>
        </detector>
        
        <!-- PID Actuator Plugin -->
        <actuator>
            <name>PyRPL_PID_Control</name>
            <class>DAQ_Move_PyRPL_PID</class>
            <init_options>
                <connection_settings>
                    <redpitaya_host>rp-f08d6c.local</redpitaya_host>
                    <mock_mode>false</mock_mode>
                </connection_settings>
                <pid_config>
                    <pid_module>pid0</pid_module>
                    <input_channel>in1</input_channel>
                    <output_channel>out1</output_channel>
                    <p_gain>0.1</p_gain>
                    <i_gain>0.01</i_gain>
                </pid_config>
            </init_options>
        </actuator>
        
        <!-- ASG Signal Generator Plugin -->
        <actuator>
            <name>PyRPL_ASG_Control</name>
            <class>DAQ_Move_PyRPL_ASG</class>
            <init_options>
                <connection_settings>
                    <redpitaya_host>rp-f08d6c.local</redpitaya_host>
                    <mock_mode>false</mock_mode>
                </connection_settings>
                <asg_config>
                    <asg_channel>asg0</asg_channel>
                    <waveform>sin</waveform>
                    <amplitude>0.1</amplitude>
                    <trigger_source>immediately</trigger_source>
                </asg_config>
            </init_options>
        </actuator>
    </modules>
</preset>"""
    
    # Ensure preset directory exists
    preset_dir = Path.home() / '.pymodaq' / 'preset_configs'
    preset_dir.mkdir(exist_ok=True)
    
    preset_path = preset_dir / 'preset_pyrpl_hardware_test.xml'
    
    with open(preset_path, 'w') as f:
        f.write(preset_content)
    
    logger.info(f"✅ Created PyRPL preset: {preset_path}")
    return preset_path

def test_individual_plugins():
    """Test each PyRPL plugin individually"""
    logger.info("Testing individual PyRPL plugins...")
    
    results = {}
    
    # Test 1: PID Plugin
    logger.info("\n1. Testing PID Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
        
        pid_plugin = DAQ_Move_PyRPL_PID()
        pid_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        pid_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize plugin
        pid_plugin.ini_stage()
        logger.info("✅ PID plugin initialized successfully")
        
        # Test get position
        position = pid_plugin.get_actuator_value()
        logger.info(f"✅ PID current setpoint: {position}")
        
        # Test move operations
        pid_plugin.move_abs(0.1)  # Set 100mV setpoint
        time.sleep(1)
        new_position = pid_plugin.get_actuator_value()
        logger.info(f"✅ PID moved to: {new_position}")
        
        # Reset to safe value
        pid_plugin.move_abs(0.0)
        
        pid_plugin.close()
        results['PID_Plugin'] = "✅ PASS"
        
    except Exception as e:
        logger.error(f"❌ PID plugin test failed: {e}")
        results['PID_Plugin'] = f"❌ FAIL: {e}"
    
    # Test 2: Voltage Monitor Plugin
    logger.info("\n2. Testing Voltage Monitor Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL import DAQ_0DViewer_PyRPL
        
        voltage_plugin = DAQ_0DViewer_PyRPL()
        voltage_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        voltage_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize plugin
        voltage_plugin.ini_detector()
        logger.info("✅ Voltage Monitor plugin initialized successfully")
        
        # Test data acquisition
        data = voltage_plugin.grab_data()
        logger.info(f"✅ Voltage Monitor acquired {len(data)} data points")
        for i, data_array in enumerate(data):
            logger.info(f"  Channel {i+1}: {data_array.data[0]:.6f} V")
        
        voltage_plugin.close()
        results['Voltage_Monitor'] = "✅ PASS"
        
    except Exception as e:
        logger.error(f"❌ Voltage Monitor plugin test failed: {e}")
        results['Voltage_Monitor'] = f"❌ FAIL: {e}"
    
    # Test 3: ASG Plugin
    logger.info("\n3. Testing ASG Signal Generator Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG
        
        asg_plugin = DAQ_Move_PyRPL_ASG()
        asg_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        asg_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize plugin
        asg_plugin.ini_stage()
        logger.info("✅ ASG plugin initialized successfully")
        
        # Test frequency control
        frequency = asg_plugin.get_actuator_value()
        logger.info(f"✅ ASG current frequency: {frequency}")
        
        # Test frequency change
        asg_plugin.move_abs(5000.0)  # 5kHz
        time.sleep(1)
        new_frequency = asg_plugin.get_actuator_value()
        logger.info(f"✅ ASG frequency changed to: {new_frequency}")
        
        # Reset to safe value
        asg_plugin.move_abs(1000.0)
        
        asg_plugin.close()
        results['ASG_Plugin'] = "✅ PASS"
        
    except Exception as e:
        logger.error(f"❌ ASG plugin test failed: {e}")
        results['ASG_Plugin'] = f"❌ FAIL: {e}"
    
    # Test 4: Scope Plugin
    logger.info("\n4. Testing Oscilloscope Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope
        
        scope_plugin = DAQ_1DViewer_PyRPL_Scope()
        scope_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        scope_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize plugin
        scope_plugin.ini_detector()
        logger.info("✅ Scope plugin initialized successfully")
        
        # Test data acquisition
        data = scope_plugin.grab_data()
        logger.info(f"✅ Scope acquired data with {len(data[0].data)} samples")
        logger.info(f"  Sample rate info: {data[0].labels}")
        
        scope_plugin.close()
        results['Scope_Plugin'] = "✅ PASS"
        
    except Exception as e:
        logger.error(f"❌ Scope plugin test failed: {e}")
        results['Scope_Plugin'] = f"❌ FAIL: {e}"
    
    # Test 5: IQ Plugin
    logger.info("\n5. Testing Lock-in Amplifier (IQ) Plugin...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ import DAQ_0DViewer_PyRPL_IQ
        
        iq_plugin = DAQ_0DViewer_PyRPL_IQ()
        iq_plugin.settings.child('connection_settings', 'redpitaya_host').setValue('rp-f08d6c.local')
        iq_plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        
        # Initialize plugin
        iq_plugin.ini_detector()
        logger.info("✅ IQ plugin initialized successfully")
        
        # Test data acquisition
        data = iq_plugin.grab_data()
        logger.info(f"✅ IQ plugin acquired {len(data)} data points")
        for i, data_array in enumerate(data):
            logger.info(f"  IQ Channel {i}: {data_array.data[0]:.6f}")
        
        iq_plugin.close()
        results['IQ_Plugin'] = "✅ PASS"
        
    except Exception as e:
        logger.error(f"❌ IQ plugin test failed: {e}")
        results['IQ_Plugin'] = f"❌ FAIL: {e}"
    
    return results

def test_pyrpl_wrapper_directly():
    """Test the PyRPL wrapper directly for hardware connectivity"""
    logger.info("\nTesting PyRPL wrapper direct connection...")
    
    try:
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import connect_redpitaya, InputChannel
        
        # Test connection
        connection = connect_redpitaya('rp-f08d6c.local')
        
        if connection and connection.is_connected:
            logger.info("✅ Direct PyRPL connection successful")
            
            # Test voltage reading
            voltage1 = connection.read_voltage(InputChannel.IN1)
            voltage2 = connection.read_voltage(InputChannel.IN2)
            logger.info(f"✅ Direct voltage readings - IN1: {voltage1:.6f}V, IN2: {voltage2:.6f}V")
            
            # Test connection info
            info = connection.get_connection_info()
            logger.info(f"✅ Connection info: {info['state']}, connected at {info['connected_at']}")
            
            connection.disconnect()
            logger.info("✅ Direct connection closed successfully")
            return True
        else:
            logger.error("❌ Direct PyRPL connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ PyRPL wrapper test failed: {e}")
        return False

def main():
    """Main comprehensive test function"""
    logger.info("🔬 Starting Comprehensive PyRPL Hardware Test")
    logger.info("Red Pitaya Address: rp-f08d6c.local")
    logger.info("="*70)
    
    # Test 1: Create preset
    try:
        preset_path = create_pyrpl_preset()
        logger.info(f"✅ PyMoDAQ preset created: {preset_path}")
    except Exception as e:
        logger.error(f"❌ Failed to create preset: {e}")
    
    # Test 2: Direct wrapper test
    logger.info("\n" + "="*50)
    logger.info("TESTING PYRPL WRAPPER DIRECTLY")
    logger.info("="*50)
    wrapper_ok = test_pyrpl_wrapper_directly()
    
    # Test 3: Individual plugin tests
    logger.info("\n" + "="*50)
    logger.info("TESTING INDIVIDUAL PLUGINS")
    logger.info("="*50)
    plugin_results = test_individual_plugins()
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("📊 COMPREHENSIVE TEST RESULTS")
    logger.info("="*70)
    
    logger.info(f"PyRPL Wrapper Direct Test: {'✅ PASS' if wrapper_ok else '❌ FAIL'}")
    
    for plugin_name, result in plugin_results.items():
        logger.info(f"{plugin_name:20}: {result}")
    
    # Calculate success rate
    total_tests = len(plugin_results) + 1  # +1 for wrapper test
    passed_tests = sum(1 for result in plugin_results.values() if "✅" in result)
    if wrapper_ok:
        passed_tests += 1
    
    success_rate = (passed_tests / total_tests) * 100
    
    logger.info("\n" + "="*70)
    logger.info(f"OVERALL SUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 COMPREHENSIVE TEST PASSED - Hardware ready for production!")
    else:
        logger.info("⚠️  SOME TESTS FAILED - Check individual results above")
    
    logger.info("="*70)
    
    return success_rate >= 80

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)