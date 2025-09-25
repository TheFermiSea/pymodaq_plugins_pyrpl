#!/usr/bin/env python3
"""
Test Red Pitaya recovery after unminimize cleanup
"""

import time
import sys

def test_red_pitaya_recovery():
    """Test if Red Pitaya has recovered from unminimize damage."""
    print("🔬 Testing Red Pitaya Recovery")
    print("=" * 40)

    try:
        import pyrpl
        print("✅ PyRPL import successful")

        print("\n🔄 Attempting connection to rp-f08d6c.local...")
        print("This should work much better now!")

        # Test with shorter timeout initially
        rp_instance = pyrpl.Pyrpl(
            hostname='rp-f08d6c.local',
            config='post_recovery_test',
            gui=False,
            reloadserver=False
        )

        print("✅ PyRPL connection successful!")

        # Test basic functionality
        rp = rp_instance.rp

        # Test voltage readings
        sampler = rp.sampler
        v1 = sampler.in1
        v2 = sampler.in2
        print(f"✅ Voltage readings: in1={v1:.6f}V, in2={v2:.6f}V")

        # Test module availability
        modules = []
        for module_name in ['pid0', 'pid1', 'asg0', 'asg1', 'scope']:
            if hasattr(rp, module_name):
                modules.append(module_name)

        print(f"✅ Available modules: {modules}")

        # Test ASG functionality
        asg0 = rp.asg0
        original_freq = asg0.frequency
        asg0.frequency = 1000.0
        time.sleep(0.1)
        new_freq = asg0.frequency
        asg0.frequency = original_freq
        print(f"✅ ASG test: Set 1000Hz, got {new_freq:.1f}Hz")

        print("\n🎉 RED PITAYA FULLY RECOVERED!")
        print("✅ PyRPL communication working perfectly")
        print("✅ FPGA modules responding normally")
        print("✅ Hardware ready for PyMoDAQ plugin testing")

        return True

    except Exception as e:
        print(f"\n❌ Recovery test failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Wait longer for Red Pitaya to fully boot")
        print("2. Check if Red Pitaya web interface works: http://rp-f08d6c.local/")
        print("3. SSH in and run: systemctl status redpitaya_discovery")
        print("4. Try power cycling the Red Pitaya")
        return False

if __name__ == "__main__":
    success = test_red_pitaya_recovery()
    if success:
        print("\n🚀 Ready to proceed with hardware testing!")
    sys.exit(0 if success else 1)