#!/usr/bin/env python3
"""
Validate the structure and imports of the new Red Pitaya plugins.
This script tests plugin initialization without requiring real hardware.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all plugins can be imported without errors."""
    print("=" * 70)
    print("TESTING PLUGIN IMPORTS")
    print("=" * 70)

    errors = []

    # Test DAQ_Move_RedPitaya import
    print("\n[1/3] Testing DAQ_Move_RedPitaya import...")
    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_RedPitaya import DAQ_Move_RedPitaya
        print("✓ DAQ_Move_RedPitaya imported successfully")
    except Exception as e:
        print(f"✗ Failed to import DAQ_Move_RedPitaya:")
        print(f"  {type(e).__name__}: {e}")
        traceback.print_exc()
        errors.append(("DAQ_Move_RedPitaya import", e))

    # Test DAQ_1DViewer_RedPitaya import
    print("\n[2/3] Testing DAQ_1DViewer_RedPitaya import...")
    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_RedPitaya import DAQ_1DViewer_RedPitaya
        print("✓ DAQ_1DViewer_RedPitaya imported successfully")
    except Exception as e:
        print(f"✗ Failed to import DAQ_1DViewer_RedPitaya:")
        print(f"  {type(e).__name__}: {e}")
        traceback.print_exc()
        errors.append(("DAQ_1DViewer_RedPitaya import", e))

    # Test PyrplWorker import
    print("\n[3/3] Testing PyrplWorker import...")
    try:
        from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker
        print("✓ PyrplWorker imported successfully")
    except Exception as e:
        print(f"✗ Failed to import PyrplWorker:")
        print(f"  {type(e).__name__}: {e}")
        traceback.print_exc()
        errors.append(("PyrplWorker import", e))

    return errors

def test_move_plugin_structure():
    """Test DAQ_Move_RedPitaya class structure and attributes."""
    print("\n" + "=" * 70)
    print("TESTING DAQ_Move_RedPitaya STRUCTURE")
    print("=" * 70)

    errors = []

    try:
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_RedPitaya import DAQ_Move_RedPitaya

        # Check required class attributes
        print("\n[1/5] Checking required class attributes...")
        required_attrs = ['_controller_units', 'is_multiaxes', '_axis_names', '_epsilon', '_units']
        for attr in required_attrs:
            if hasattr(DAQ_Move_RedPitaya, attr):
                value = getattr(DAQ_Move_RedPitaya, attr)
                print(f"  ✓ {attr}: {value if not isinstance(value, list) or len(value) < 5 else f'{type(value).__name__} with {len(value)} items'}")
            else:
                print(f"  ✗ Missing attribute: {attr}")
                errors.append(("DAQ_Move_RedPitaya missing attribute", attr))

        # Check axis names count
        print("\n[2/5] Validating axis configuration...")
        if len(DAQ_Move_RedPitaya._axis_names) == 21:
            print(f"  ✓ Correct number of axes: 21")
        else:
            print(f"  ✗ Expected 21 axes, found {len(DAQ_Move_RedPitaya._axis_names)}")
            errors.append(("DAQ_Move_RedPitaya axis count", f"Expected 21, got {len(DAQ_Move_RedPitaya._axis_names)}"))

        # Check units match axes
        if len(DAQ_Move_RedPitaya._units) == len(DAQ_Move_RedPitaya._axis_names):
            print(f"  ✓ Units list matches axis count")
        else:
            print(f"  ✗ Units count ({len(DAQ_Move_RedPitaya._units)}) doesn't match axes ({len(DAQ_Move_RedPitaya._axis_names)})")
            errors.append(("DAQ_Move_RedPitaya units mismatch", "Units and axes count differ"))

        # Check required methods exist
        print("\n[3/5] Checking required methods...")
        required_methods = ['ini_attributes', 'ini_stage', 'get_actuator_value', 'move_abs', 'commit_settings', 'close']
        for method in required_methods:
            if hasattr(DAQ_Move_RedPitaya, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing method: {method}")
                errors.append(("DAQ_Move_RedPitaya missing method", method))

        # Check helper methods
        print("\n[4/5] Checking helper methods...")
        helper_methods = ['_create_asg_params', '_create_pid_params', '_create_iq_params']
        for method in helper_methods:
            if hasattr(DAQ_Move_RedPitaya, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing helper: {method}")
                errors.append(("DAQ_Move_RedPitaya missing helper", method))

        # Test ini_attributes (should create params)
        print("\n[5/5] Testing ini_attributes()...")
        try:
            DAQ_Move_RedPitaya.ini_attributes()
            if hasattr(DAQ_Move_RedPitaya, 'params') and len(DAQ_Move_RedPitaya.params) > 0:
                print(f"  ✓ Parameters created: {len(DAQ_Move_RedPitaya.params)} top-level groups")
            else:
                print(f"  ✗ Parameters not created properly")
                errors.append(("DAQ_Move_RedPitaya ini_attributes", "params not created"))
        except Exception as e:
            print(f"  ✗ ini_attributes() failed: {e}")
            errors.append(("DAQ_Move_RedPitaya ini_attributes", e))

    except Exception as e:
        print(f"\n✗ Failed to test DAQ_Move_RedPitaya structure: {e}")
        traceback.print_exc()
        errors.append(("DAQ_Move_RedPitaya structure test", e))

    return errors

def test_viewer_plugin_structure():
    """Test DAQ_1DViewer_RedPitaya class structure and attributes."""
    print("\n" + "=" * 70)
    print("TESTING DAQ_1DViewer_RedPitaya STRUCTURE")
    print("=" * 70)

    errors = []

    try:
        from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_RedPitaya import DAQ_1DViewer_RedPitaya

        # Check required methods
        print("\n[1/3] Checking required methods...")
        required_methods = ['ini_attributes', 'ini_detector', 'grab_data', 'commit_settings', 'close']
        for method in required_methods:
            if hasattr(DAQ_1DViewer_RedPitaya, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing method: {method}")
                errors.append(("DAQ_1DViewer_RedPitaya missing method", method))

        # Check helper methods
        print("\n[2/3] Checking helper methods...")
        if hasattr(DAQ_1DViewer_RedPitaya, '_setup_scope_hardware'):
            print(f"  ✓ _setup_scope_hardware()")
        else:
            print(f"  ✗ Missing helper: _setup_scope_hardware")
            errors.append(("DAQ_1DViewer_RedPitaya missing helper", "_setup_scope_hardware"))

        # Test ini_attributes
        print("\n[3/3] Testing ini_attributes()...")
        try:
            DAQ_1DViewer_RedPitaya.ini_attributes()
            if hasattr(DAQ_1DViewer_RedPitaya, 'params') and len(DAQ_1DViewer_RedPitaya.params) > 0:
                print(f"  ✓ Parameters created: {len(DAQ_1DViewer_RedPitaya.params)} top-level groups")

                # Check for mode parameter
                mode_found = False
                for param in DAQ_1DViewer_RedPitaya.params:
                    if param.get('name') == 'mode_group':
                        mode_found = True
                        print(f"  ✓ Mode selection group found")
                        break

                if not mode_found:
                    print(f"  ✗ Mode selection group not found")
                    errors.append(("DAQ_1DViewer_RedPitaya params", "mode_group missing"))
            else:
                print(f"  ✗ Parameters not created properly")
                errors.append(("DAQ_1DViewer_RedPitaya ini_attributes", "params not created"))
        except Exception as e:
            print(f"  ✗ ini_attributes() failed: {e}")
            errors.append(("DAQ_1DViewer_RedPitaya ini_attributes", e))

    except Exception as e:
        print(f"\n✗ Failed to test DAQ_1DViewer_RedPitaya structure: {e}")
        traceback.print_exc()
        errors.append(("DAQ_1DViewer_RedPitaya structure test", e))

    return errors

def test_pyrpl_worker_methods():
    """Test PyrplWorker has all required methods."""
    print("\n" + "=" * 70)
    print("TESTING PyrplWorker METHODS")
    print("=" * 70)

    errors = []

    try:
        from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

        print("\n[1/4] Checking ASG methods...")
        asg_methods = ['setup_asg', 'set_asg_frequency', 'set_asg_amplitude', 'set_asg_offset']
        for method in asg_methods:
            if hasattr(PyrplWorker, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing: {method}")
                errors.append(("PyrplWorker missing ASG method", method))

        print("\n[2/4] Checking PID methods...")
        pid_methods = ['setup_pid', 'set_pid_setpoint', 'set_pid_p', 'set_pid_i', 'reset_pid_integrator']
        for method in pid_methods:
            if hasattr(PyrplWorker, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing: {method}")
                errors.append(("PyrplWorker missing PID method", method))

        print("\n[3/4] Checking IQ methods...")
        iq_methods = ['setup_iq', 'set_iq_frequency', 'set_iq_phase']
        for method in iq_methods:
            if hasattr(PyrplWorker, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing: {method}")
                errors.append(("PyrplWorker missing IQ method", method))

        print("\n[4/4] Checking sampler methods...")
        sampler_methods = ['get_sampler_value', 'get_iq_data', 'get_pid_data']
        for method in sampler_methods:
            if hasattr(PyrplWorker, method):
                print(f"  ✓ {method}()")
            else:
                print(f"  ✗ Missing: {method}")
                errors.append(("PyrplWorker missing sampler method", method))

    except Exception as e:
        print(f"\n✗ Failed to test PyrplWorker methods: {e}")
        traceback.print_exc()
        errors.append(("PyrplWorker method test", e))

    return errors

def main():
    """Run all validation tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "RED PITAYA PLUGIN VALIDATION" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")

    all_errors = []

    # Run tests
    all_errors.extend(test_imports())
    all_errors.extend(test_move_plugin_structure())
    all_errors.extend(test_viewer_plugin_structure())
    all_errors.extend(test_pyrpl_worker_methods())

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    if len(all_errors) == 0:
        print("\n✓ ALL TESTS PASSED!")
        print("\nThe plugins are structurally correct and ready for hardware testing.")
        print("\nNext steps:")
        print("  1. Connect to Red Pitaya at 100.107.106.75")
        print("  2. Launch PyMoDAQ dashboard")
        print("  3. Add DAQ_Move_RedPitaya and DAQ_1DViewer_RedPitaya plugins")
        print("  4. Test all modes and functionalities")
        return 0
    else:
        print(f"\n✗ FOUND {len(all_errors)} ERROR(S):\n")
        for i, (context, error) in enumerate(all_errors, 1):
            print(f"{i}. {context}")
            print(f"   {error}\n")
        print("\nPlease fix the errors above before proceeding to hardware testing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
