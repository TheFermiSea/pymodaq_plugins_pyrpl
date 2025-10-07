#!/usr/bin/env python3
"""
Debug script for IQ bandwidth issue in StemLab library.
Investigates why IQ setup is causing division by zero error.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Monkey patch for NumPy compatibility (same as in pyrpl_worker.py)
if not hasattr(np, "float"):
    np.float = np.float64
if not hasattr(np, "int"):
    np.int = np.int_
if not hasattr(np, "complex"):
    np.complex = np.complex128

try:
    from stemlab import StemLab
except ImportError as e:
    print(f"❌ Cannot import StemLab: {e}")
    print(
        "Install with: pip install git+https://github.com/ograsdijk/StemLab.git"
    )
    sys.exit(1)


def debug_iq_setup():
    """Debug IQ module setup issues."""
    print("🔍 Debugging IQ module setup...")

    # Connect to Red Pitaya
    print("\n1. Connecting to Red Pitaya...")
    try:
        config = {
            "reloadfpga": False,
            "autostart": True,
            "timeout": 10,
            "hostname": "100.107.106.75",
        }
        pyrpl = StemLab(**config)
        print("   ✅ Connection successful")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return

    # Inspect IQ module properties
    print("\n2. Inspecting IQ0 module...")
    iq0 = pyrpl.iq0

    try:
        print(f"   Current frequency: {iq0.frequency}")
        print(f"   Current phase: {iq0.phase}")
        print(f"   Current bandwidth: {iq0.bandwidth}")
        print(f"   Current input: {iq0.input}")
    except Exception as e:
        print(f"   ⚠️  Error reading current properties: {e}")

    # Try to understand bandwidth constraints
    print("\n3. Investigating bandwidth constraints...")
    try:
        # Try to access internal bandwidth methods
        if hasattr(iq0, "_MINBW"):
            minbw = iq0._MINBW(iq0)
            print(f"   Minimum bandwidth: {minbw}")
        else:
            print("   _MINBW method not found")

        if hasattr(iq0, "_MAXSHIFT"):
            try:
                maxshift = iq0._MAXSHIFT(iq0)
                print(f"   Maximum shift: {maxshift}")
            except Exception as e:
                print(f"   Error getting maxshift: {e}")

        # Try to get valid frequencies
        if hasattr(iq0, "valid_frequencies"):
            try:
                valid_freqs = list(iq0.valid_frequencies(iq0))
                print(f"   Valid frequencies (first 10): {valid_freqs[:10]}")
            except Exception as e:
                print(f"   Error getting valid frequencies: {e}")

    except Exception as e:
        print(f"   ⚠️  Error investigating constraints: {e}")

    # Try different approaches to setup
    print("\n4. Testing different setup approaches...")

    # Approach 1: Setup without bandwidth
    print("\n   4a. Setup without bandwidth parameter...")
    try:
        iq0.setup(frequency=5e6, phase=0.0, input="in1")
        print("   ✅ Success without bandwidth")
        print(f"      Resulting bandwidth: {iq0.bandwidth}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Approach 2: Set bandwidth separately
    print("\n   4b. Set bandwidth separately...")
    try:
        # First set frequency and input
        iq0.frequency = 5e6
        iq0.phase = 0.0
        iq0.input = "in1"
        print("   ✅ Basic parameters set")

        # Now try to set bandwidth
        print("      Trying to set bandwidth to 1000 Hz...")
        iq0.bandwidth = 1000
        print(f"   ✅ Bandwidth set to: {iq0.bandwidth}")
    except Exception as e:
        print(f"   ❌ Failed setting bandwidth: {e}")

    # Approach 3: Try different bandwidth values
    print("\n   4c. Testing different bandwidth values...")
    test_bandwidths = [10, 100, 1000, 10000, 100000, 1000000]

    for bw in test_bandwidths:
        try:
            iq0.bandwidth = bw
            actual_bw = iq0.bandwidth
            print(f"      Set {bw} Hz → Got {actual_bw} Hz ✅")
            break  # Use the first one that works
        except Exception as e:
            print(f"      {bw} Hz failed: {e}")

    # Approach 4: Use default bandwidth
    print("\n   4d. Using default bandwidth...")
    try:
        iq0.setup(
            frequency=5e6, phase=0.0, input="in1"
        )  # No bandwidth specified
        print("   ✅ Setup with defaults successful")
        print(f"      Default bandwidth: {iq0.bandwidth}")

        # Test frequency and phase changes
        test_frequencies = [1e6, 5e6, 10e6]
        for freq in test_frequencies:
            iq0.frequency = freq
            actual_freq = iq0.frequency
            print(
                f"      Set {freq / 1e6:.1f} MHz → Got {actual_freq / 1e6:.3f} MHz"
            )

        test_phases = [0.0, 90.0, 180.0]
        for phase in test_phases:
            iq0.phase = phase
            actual_phase = iq0.phase
            print(f"      Set {phase}° → Got {actual_phase:.1f}°")

    except Exception as e:
        print(f"   ❌ Default setup failed: {e}")

    print("\n5. Cleanup...")
    try:
        pyrpl.stop()
        print("   ✅ Disconnected")
    except:
        pass


def main():
    print("=" * 70)
    print("           IQ MODULE DEBUG SCRIPT")
    print("=" * 70)
    print("\nThis script debugs IQ bandwidth setup issues.")
    print("Requires Red Pitaya at 100.107.106.75\n")

    try:
        debug_iq_setup()
        print("\n🎯 Debug complete. Check output for working configuration.")
    except KeyboardInterrupt:
        print("\n⏸️  Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Debug failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
