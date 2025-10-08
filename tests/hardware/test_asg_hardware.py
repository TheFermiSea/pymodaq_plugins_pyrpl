#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hardware Testing for PyRPL ASG (Arbitrary Signal Generator) Plugin

This script tests the ASG plugin with REAL Red Pitaya hardware.
Must be run ONLY after test_environment.py passes.

Hardware: Red Pitaya at 100.107.106.75
Plugin: DAQ_Move_PyRPL_ASG

CRITICAL SAFETY NOTE:
Device may be in HV mode (±20V) or LV mode (±1V). We use conservative
voltage levels (±0.1V max) that are SAFE for both modes.

Tests:
1. Plugin initialization
2. Hardware connection
3. Set output voltage (safe range)
4. Read current voltage
5. Voltage ramping
6. Graceful shutdown
"""

import sys
import logging
import numpy as np
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# SAFETY: Maximum voltage for testing (safe for both HV and LV modes)
MAX_SAFE_VOLTAGE = 0.1  # ±0.1V is safe regardless of jumper configuration


class ASGHardwareTest:
    """Tests ASG plugin with real Red Pitaya hardware."""

    def __init__(self):
        self.results = {}
        self.all_passed = True
        self.plugin = None

    def test_1_plugin_initialization(self):
        """Test 1: Initialize ASG plugin."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: ASG Plugin Initialization")
        logger.info("="*70)

        try:
            from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG

            # Create plugin instance
            logger.info("Creating ASG plugin instance...")
            self.plugin = DAQ_Move_PyRPL_ASG()

            # Verify plugin attributes
            assert hasattr(self.plugin, 'params'), "Plugin missing params"
            assert hasattr(self.plugin, 'controller'), "Plugin missing controller"

            logger.info("PASS: Plugin initialized successfully")
            logger.info(f"Plugin class: {self.plugin.__class__.__name__}")

            self.results['plugin_initialization'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Plugin initialization error: {e}")
            import traceback
            traceback.print_exc()
            self.results['plugin_initialization'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_2_hardware_connection(self):
        """Test 2: Connect to Red Pitaya hardware."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: Red Pitaya Hardware Connection")
        logger.info("="*70)

        if not self.plugin:
            logger.error("SKIP: Plugin not initialized")
            self.results['hardware_connection'] = 'SKIP'
            return False

        try:
            logger.info("Connecting to Red Pitaya at 100.107.106.75...")

            # Initialize hardware connection
            info = self.plugin.ini_stage()

            logger.info(f"Connection info: {info}")

            # Verify controller was created
            assert self.plugin.controller is not None, "Controller not created"

            logger.info("PASS: Successfully connected to Red Pitaya hardware")
            logger.info(f"Controller type: {type(self.plugin.controller).__name__}")

            self.results['hardware_connection'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Hardware connection error: {e}")
            import traceback
            traceback.print_exc()
            self.results['hardware_connection'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_3_set_output_voltage(self):
        """Test 3: Set ASG output voltage (safe range)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: ASG Output Voltage Control")
        logger.info("="*70)
        logger.info(f"SAFETY: Using max voltage ±{MAX_SAFE_VOLTAGE}V (safe for HV/LV modes)")

        if not self.plugin or not self.plugin.controller:
            logger.error("SKIP: Hardware not connected")
            self.results['set_output_voltage'] = 'SKIP'
            return False

        try:
            # Test voltage values (all within safe range)
            test_voltages = [0.0, 0.05, -0.05, 0.1, -0.1, 0.0]

            logger.info(f"\nTesting {len(test_voltages)} voltage setpoints...")

            for voltage in test_voltages:
                logger.info(f"  Setting voltage to {voltage:+.3f}V...")

                # Move to absolute voltage
                self.plugin.move_abs(voltage)

                # Small delay for settling
                import time
                time.sleep(0.1)

                logger.info(f"    ✓ Set to {voltage:+.3f}V")

            logger.info("\nPASS: All voltage setpoints successful")
            logger.info(f"Tested range: ±{MAX_SAFE_VOLTAGE}V")

            self.results['set_output_voltage'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Voltage control error: {e}")
            import traceback
            traceback.print_exc()
            self.results['set_output_voltage'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_4_read_voltage(self):
        """Test 4: Read current output voltage."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: ASG Voltage Readback")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("SKIP: Hardware not connected")
            self.results['read_voltage'] = 'SKIP'
            return False

        try:
            logger.info("Reading current output voltage...")

            # Get current actuator value
            voltage = self.plugin.get_actuator_value()

            logger.info(f"Current voltage: {voltage:.6f}V")

            # Verify voltage is within safe range
            assert abs(voltage) <= MAX_SAFE_VOLTAGE * 1.1, \
                f"Voltage {voltage}V exceeds safe range ±{MAX_SAFE_VOLTAGE}V"

            logger.info("PASS: Voltage readback successful")

            self.results['read_voltage'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Voltage readback error: {e}")
            import traceback
            traceback.print_exc()
            self.results['read_voltage'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_5_voltage_ramp(self):
        """Test 5: Test voltage ramping functionality."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: ASG Voltage Ramping")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("SKIP: Hardware not connected")
            self.results['voltage_ramp'] = 'SKIP'
            return False

        try:
            logger.info("Testing smooth voltage ramp...")

            # Create ramp from -0.1V to +0.1V
            ramp_points = 10
            voltages = np.linspace(-MAX_SAFE_VOLTAGE, MAX_SAFE_VOLTAGE, ramp_points)

            logger.info(f"Ramping through {ramp_points} points...")

            import time
            for i, voltage in enumerate(voltages):
                self.plugin.move_abs(voltage)
                time.sleep(0.05)
                logger.info(f"  Step {i+1}/{ramp_points}: {voltage:+.3f}V")

            # Return to zero
            self.plugin.move_abs(0.0)
            logger.info("  Returned to 0.000V")

            logger.info("\nPASS: Voltage ramping successful")

            self.results['voltage_ramp'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Voltage ramping error: {e}")
            import traceback
            traceback.print_exc()
            self.results['voltage_ramp'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_6_graceful_shutdown(self):
        """Test 6: Graceful shutdown and cleanup."""
        logger.info("\n" + "="*70)
        logger.info("TEST 6: Graceful Shutdown")
        logger.info("="*70)

        if not self.plugin:
            logger.error("SKIP: Plugin not initialized")
            self.results['graceful_shutdown'] = 'SKIP'
            return False

        try:
            logger.info("Setting output to 0V before shutdown...")
            if self.plugin.controller:
                self.plugin.move_abs(0.0)

            logger.info("Closing plugin connection...")
            self.plugin.close()

            logger.info("PASS: Plugin closed successfully")

            self.results['graceful_shutdown'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Shutdown error: {e}")
            import traceback
            traceback.print_exc()
            self.results['graceful_shutdown'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def generate_report(self):
        """Generate hardware test report."""
        logger.info("\n" + "="*70)
        logger.info("ASG HARDWARE TEST REPORT")
        logger.info("="*70)
        logger.info(f"Safety limit: ±{MAX_SAFE_VOLTAGE}V (HV/LV mode agnostic)")
        logger.info("="*70)

        for test_name, result in self.results.items():
            if result == "PASS":
                symbol = "✓"
            elif result == "SKIP":
                symbol = "⊘"
            else:
                symbol = "✗"

            logger.info(f"{symbol} {test_name:.<50} {result}")

        logger.info("\n" + "="*70)
        if self.all_passed and 'SKIP' not in self.results.values():
            logger.info("✓✓✓ ASG HARDWARE TESTS PASSED ✓✓✓")
            logger.info("="*70)
            logger.info("\nASG plugin is READY for production use with Red Pitaya")
            logger.info(f"Validated voltage range: ±{MAX_SAFE_VOLTAGE}V")
            logger.info("NOTE: Higher voltages not tested due to unknown HV mode status")
            return 0
        elif 'SKIP' in self.results.values():
            logger.warning("⚠⚠⚠ SOME TESTS SKIPPED ⚠⚠⚠")
            logger.warning("="*70)
            return 1
        else:
            logger.error("✗✗✗ ASG HARDWARE TESTS FAILED ✗✗✗")
            logger.error("="*70)
            return 1


def main():
    """Run ASG hardware tests."""
    print("\n" + "="*70)
    print("PyMoDAQ PyRPL Plugins - ASG Hardware Testing")
    print("Hardware: Red Pitaya at 100.107.106.75")
    print(f"Safety Mode: Max voltage ±{MAX_SAFE_VOLTAGE}V (HV/LV agnostic)")
    print("="*70)

    tester = ASGHardwareTest()

    # Run all tests in sequence
    tester.test_1_plugin_initialization()
    tester.test_2_hardware_connection()
    tester.test_3_set_output_voltage()
    tester.test_4_read_voltage()
    tester.test_5_voltage_ramp()
    tester.test_6_graceful_shutdown()

    return tester.generate_report()


if __name__ == '__main__':
    sys.exit(main())
