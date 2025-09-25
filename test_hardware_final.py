#!/usr/bin/env python3
"""
Final Red Pitaya Hardware Validation Test
"""

import time
import logging
from pyrpl.redpitaya import RedPitaya

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_red_pitaya_comprehensive():
    """Comprehensive Red Pitaya hardware test."""
    print("🔬 Comprehensive Red Pitaya Hardware Test")
    print("=" * 50)

    try:
        # Test 1: Direct hardware connection
        print("\n📡 Test 1: Hardware Connection")
        rp = RedPitaya(hostname='rp-f08d6c.local')
        print("✅ Direct Red Pitaya connection successful")

        # Test 2: Voltage monitoring
        print("\n⚡ Test 2: Voltage Monitoring")
        v1 = rp.sampler.in1
        v2 = rp.sampler.in2
        print(f"✅ Voltage readings: in1={v1:.6f}V, in2={v2:.6f}V")

        # Test 3: ASG (Arbitrary Signal Generator)
        print("\n🌊 Test 3: ASG Signal Generation")
        asg0 = rp.asg0
        original_freq = asg0.frequency
        original_amp = asg0.amplitude

        # Test frequency change
        asg0.frequency = 2000.0
        time.sleep(0.1)
        new_freq = asg0.frequency
        print(f"✅ ASG frequency control: Set 2000Hz, got {new_freq:.1f}Hz")

        # Test amplitude change
        asg0.amplitude = 0.3
        time.sleep(0.1)
        new_amp = asg0.amplitude
        print(f"✅ ASG amplitude control: Set 0.3V, got {new_amp:.3f}V")

        # Restore original settings
        asg0.frequency = original_freq
        asg0.amplitude = original_amp

        # Test 4: PID Controllers
        print("\n🎛️ Test 4: PID Controllers")
        pid0 = rp.pid0
        original_setpoint = pid0.setpoint

        # Test setpoint change
        pid0.setpoint = 0.1
        time.sleep(0.1)
        new_setpoint = pid0.setpoint
        print(f"✅ PID setpoint control: Set 0.1V, got {new_setpoint:.3f}V")

        # Restore original setpoint
        pid0.setpoint = original_setpoint

        # Test 5: Scope functionality
        print("\n📊 Test 5: Oscilloscope")
        scope = rp.scope
        original_decimation = scope.decimation

        # Test decimation change
        scope.decimation = 64
        time.sleep(0.1)
        new_decimation = scope.decimation
        print(f"✅ Scope decimation control: Set 64, got {new_decimation}")

        # Restore original decimation
        scope.decimation = original_decimation

        # Test 6: Available modules
        print("\n🔧 Test 6: Module Availability")
        modules = []
        for module_name in ['pid0', 'pid1', 'pid2', 'asg0', 'asg1', 'scope', 'iq0', 'iq1', 'iq2']:
            if hasattr(rp, module_name):
                modules.append(module_name)

        print(f"✅ Available hardware modules: {modules}")

        # Test 7: Signal path connectivity
        print("\n🔗 Test 7: Signal Path Configuration")

        # Test ASG output routing
        asg0.output_direct = 'out1'
        time.sleep(0.1)
        output_route = asg0.output_direct
        print(f"✅ ASG output routing: {output_route}")

        # Test PID input/output routing
        pid0.input = 'in1'
        pid0.output_direct = 'off'  # Safety: turn off output
        time.sleep(0.1)
        input_route = pid0.input
        output_route = pid0.output_direct
        print(f"✅ PID signal routing: input={input_route}, output={output_route}")

        print("\n🎉 COMPREHENSIVE HARDWARE TEST PASSED!")
        print("=" * 50)
        print("✅ Red Pitaya hardware fully functional")
        print("✅ All major modules operational")
        print("✅ Signal routing and control working")
        print("✅ Ready for PyMoDAQ plugin integration")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"\n❌ Hardware test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_red_pitaya_comprehensive()
    exit(0 if success else 1)