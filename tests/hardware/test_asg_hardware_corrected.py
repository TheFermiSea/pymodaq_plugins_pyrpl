#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CORRECTED Hardware Testing for PyRPL ASG (Arbitrary Signal Generator) Plugin

This script tests the ASG plugin with REAL Red Pitaya hardware.
Must be run ONLY after test_environment.py passes.

Hardware: Red Pitaya at 100.107.106.75
Plugin: DAQ_Move_PyRPL_ASG
Mode: LV (±1V confirmed)

CRITICAL: ASG controls FREQUENCY (Hz), not voltage directly.
- Frequency: Set via move_abs() / move_rel() (0.1 Hz to 62.5 MHz)
- Amplitude: Set via parameters (0-1V peak)
- Offset: Set via parameters (±1V DC offset)

Physical Setup:
- OUT1 connected to IN1 (loopback via BNC cable)
- LV mode (±1V) confirmed on both channels

Tests:
1. Plugin initialization
2. Hardware connection
3. Set output frequency (safe frequencies)
4. Read current frequency
5. Frequency sweep
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

# Test parameters (safe for LV mode)
TEST_FREQUENCIES = [100.0, 1000.0, 5000.0, 10000.0]  # Hz
TEST_AMPLITUDE = 0.1  # 0.1V peak (safe for LV mode)
TEST_OFFSET = 0.0     # No DC offset


class ASGHardwareTestCorrected:
    """Tests ASG plugin with real Red Pitaya hardware (CORRECTED)."""

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

            # Verify units
            assert self.plugin._controller_units == 'Hz', "ASG should control frequency in Hz"
            assert self.plugin._axis_names == ['Frequency'], "ASG axis should be Frequency"

            logger.info("[PASS] Plugin initialized successfully")
            logger.info(f"  Plugin class: {self.plugin.__class__.__name__}")
            logger.info(f"  Controller units: {self.plugin._controller_units}")
            logger.info(f"  Axis name: {self.plugin._axis_names[0]}")

            self.results['plugin_initialization'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Plugin initialization error: {e}")
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
            logger.error("[SKIP] Plugin not initialized")
            self.results['hardware_connection'] = 'SKIP'
            return False

        try:
            logger.info("Connecting to Red Pitaya at 100.107.106.75...")

            # Initialize hardware connection
            info = self.plugin.ini_stage()

            logger.info(f"Connection info: {info}")

            # Verify controller was created
            assert self.plugin.controller is not None, "Controller not created"

            logger.info("[PASS] Successfully connected to Red Pitaya hardware")
            logger.info(f"  Controller type: {type(self.plugin.controller).__name__}")

            self.results['hardware_connection'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Hardware connection error: {e}")
            import traceback
            traceback.print_exc()
            self.results['hardware_connection'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_3_configure_signal_params(self):
        """Test 3: Configure ASG signal parameters (amplitude, offset)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Configure Signal Parameters")
        logger.info("="*70)
        logger.info(f"LV Mode: Amplitude={TEST_AMPLITUDE}V, Offset={TEST_OFFSET}V")

        if not self.plugin or not self.plugin.controller:
            logger.error("[SKIP] Hardware not connected")
            self.results['configure_signal'] = 'SKIP'
            return False

        try:
            # Get parameters
            amplitude_param = self.plugin.settings.child('signal_params', 'amplitude')
            offset_param = self.plugin.settings.child('signal_params', 'offset')

            # Set safe values for LV mode
            amplitude_param.setValue(TEST_AMPLITUDE)
            offset_param.setValue(TEST_OFFSET)

            logger.info(f"  Amplitude set to: {TEST_AMPLITUDE}V")
            logger.info(f"  Offset set to: {TEST_OFFSET}V")

            logger.info("[PASS] Signal parameters configured")

            self.results['configure_signal'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Signal configuration error: {e}")
            import traceback
            traceback.print_exc()
            self.results['configure_signal'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_4_set_frequencies(self):
        """Test 4: Set ASG output frequencies."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: ASG Frequency Control")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("[SKIP] Hardware not connected")
            self.results['set_frequencies'] = 'SKIP'
            return False

        try:
            logger.info(f"\nTesting {len(TEST_FREQUENCIES)} frequency setpoints...")

            for frequency in TEST_FREQUENCIES:
                logger.info(f"  Setting frequency to {frequency} Hz...")

                # Move to absolute frequency
                self.plugin.move_abs(frequency)

                # Small delay for settling
                import time
                time.sleep(0.1)

                # Read back frequency
                actual_freq = self.plugin.get_actuator_value()
                logger.info(f"    Set to {frequency} Hz, readback: {actual_freq:.2f} Hz")

                # Verify within tolerance
                tolerance = self.plugin._epsilon  # 1 Hz
                assert abs(actual_freq - frequency) <= tolerance, \
                    f"Frequency error: expected {frequency} Hz, got {actual_freq:.2f} Hz"

            logger.info(f"\n[PASS] All frequency setpoints successful")
            logger.info(f"  Tested frequencies: {TEST_FREQUENCIES}")

            self.results['set_frequencies'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Frequency control error: {e}")
            import traceback
            traceback.print_exc()
            self.results['set_frequencies'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_5_frequency_sweep(self):
        """Test 5: Test frequency sweep functionality."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: ASG Frequency Sweep")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("[SKIP] Hardware not connected")
            self.results['frequency_sweep'] = 'SKIP'
            return False

        try:
            logger.info("Testing smooth frequency sweep...")

            # Create sweep from 100 Hz to 10 kHz
            sweep_points = 10
            frequencies = np.linspace(100, 10000, sweep_points)

            logger.info(f"Sweeping through {sweep_points} points (100 Hz to 10 kHz)...")

            import time
            for i, frequency in enumerate(frequencies):
                self.plugin.move_abs(frequency)
                time.sleep(0.05)
                logger.info(f"  Step {i+1}/{sweep_points}: {frequency:.1f} Hz")

            # Return to 1 kHz
            self.plugin.move_abs(1000.0)
            logger.info("  Returned to 1000 Hz")

            logger.info("\n[PASS] Frequency sweep successful")

            self.results['frequency_sweep'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Frequency sweep error: {e}")
            import traceback
            traceback.print_exc()
            self.results['frequency_sweep'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_6_graceful_shutdown(self):
        """Test 6: Graceful shutdown and cleanup."""
        logger.info("\n" + "="*70)
        logger.info("TEST 6: Graceful Shutdown")
        logger.info("="*70)

        if not self.plugin:
            logger.error("[SKIP] Plugin not initialized")
            self.results['graceful_shutdown'] = 'SKIP'
            return False

        try:
            logger.info("Setting frequency to 1 kHz before shutdown...")
            if self.plugin.controller:
                self.plugin.move_abs(1000.0)  # Safe default frequency

            logger.info("Closing plugin connection...")
            self.plugin.close()

            logger.info("[PASS] Plugin closed successfully")

            self.results['graceful_shutdown'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"[FAIL] Shutdown error: {e}")
            import traceback
            traceback.print_exc()
            self.results['graceful_shutdown'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def generate_report(self):
        """Generate hardware test report."""
        logger.info("\n" + "="*70)
        logger.info("ASG HARDWARE TEST REPORT (CORRECTED)")
        logger.info("="*70)
        logger.info(f"Test config: Amplitude={TEST_AMPLITUDE}V, Offset={TEST_OFFSET}V (LV mode)")
        logger.info("="*70)

        for test_name, result in self.results.items():
            if result == "PASS":
                symbol = "[PASS]"
            elif result == "SKIP":
                symbol = "[SKIP]"
            else:
                symbol = "[FAIL]"

            logger.info(f"{symbol} {test_name:.<50} {result}")

        logger.info("\n" + "="*70)
        if self.all_passed and 'SKIP' not in self.results.values():
            logger.info("[OK] ASG HARDWARE TESTS PASSED")
            logger.info("="*70)
            logger.info("\nASG plugin is READY for frequency control with Red Pitaya")
            logger.info(f"Validated frequency range: {min(TEST_FREQUENCIES)}-{max(TEST_FREQUENCIES)} Hz")
            logger.info(f"Amplitude: {TEST_AMPLITUDE}V, Offset: {TEST_OFFSET}V")
            return 0
        elif 'SKIP' in self.results.values():
            logger.warning("[WARN] SOME TESTS SKIPPED")
            logger.warning("="*70)
            return 1
        else:
            logger.error("[FAIL] ASG HARDWARE TESTS FAILED")
            logger.error("="*70)
            return 1


def main():
    """Run corrected ASG hardware tests."""
    print("\n" + "="*70)
    print("PyMoDAQ PyRPL Plugins - ASG Hardware Testing (CORRECTED)")
    print("Hardware: Red Pitaya at 100.107.106.75 (LV mode)")
    print(f"Test Config: Amplitude={TEST_AMPLITUDE}V, Offset={TEST_OFFSET}V")
    print("="*70)

    tester = ASGHardwareTestCorrected()

    # Run all tests in sequence
    tester.test_1_plugin_initialization()
    tester.test_2_hardware_connection()
    tester.test_3_configure_signal_params()
    tester.test_4_set_frequencies()
    tester.test_5_frequency_sweep()
    tester.test_6_graceful_shutdown()

    return tester.generate_report()


if __name__ == '__main__':
    sys.exit(main())
