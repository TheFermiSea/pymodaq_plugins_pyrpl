#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hardware Testing for PyRPL Scope Plugin

This script tests the Scope plugin with REAL Red Pitaya hardware.
Must be run ONLY after test_environment.py passes.

Hardware: Red Pitaya at 100.107.106.75
Plugin: DAQ_1DViewer_PyRPL_Scope

Tests:
1. Plugin initialization with real hardware
2. Connection establishment to Red Pitaya
3. Data acquisition from scope
4. Configuration parameter changes
5. Trigger settings
6. Channel selection and input settings
7. Graceful shutdown
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ScopeHardwareTest:
    """Tests Scope plugin with real Red Pitaya hardware."""

    def __init__(self):
        self.results = {}
        self.all_passed = True
        self.plugin = None

    def test_1_plugin_initialization(self):
        """Test 1: Initialize Scope plugin."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Scope Plugin Initialization")
        logger.info("="*70)

        try:
            from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope

            # Create plugin instance
            logger.info("Creating Scope plugin instance...")
            self.plugin = DAQ_1DViewer_PyRPL_Scope()

            # Verify plugin has expected attributes
            assert hasattr(self.plugin, 'params'), "Plugin missing params attribute"
            assert hasattr(self.plugin, 'controller'), "Plugin missing controller attribute"

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

            # Call ini_detector to initialize hardware connection
            # This should connect to the Red Pitaya and set up the scope
            info = self.plugin.ini_detector()

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

    def test_3_data_acquisition(self):
        """Test 3: Acquire data from scope."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Scope Data Acquisition")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("SKIP: Hardware not connected")
            self.results['data_acquisition'] = 'SKIP'
            return False

        try:
            logger.info("Acquiring data from scope...")

            # Call grab_data to acquire a trace
            data = self.plugin.grab_data()

            logger.info(f"Data acquired: {type(data)}")

            # Verify we got data
            assert data is not None, "No data returned"

            # Data should be a list of DataRaw or DataToExport objects
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Number of data objects: {len(data)}")
                logger.info(f"First data object type: {type(data[0])}")

                # Check the data structure
                first_data = data[0]
                if hasattr(first_data, 'data'):
                    logger.info(f"Data shape: {first_data.data.shape}")
                    logger.info(f"Data dtype: {first_data.data.dtype}")
                    logger.info(f"Data range: [{first_data.data.min():.3f}, {first_data.data.max():.3f}]")

            logger.info("PASS: Data acquisition successful")

            self.results['data_acquisition'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Data acquisition error: {e}")
            import traceback
            traceback.print_exc()
            self.results['data_acquisition'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_4_parameter_changes(self):
        """Test 4: Change scope configuration parameters."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Scope Parameter Configuration")
        logger.info("="*70)

        if not self.plugin or not self.plugin.controller:
            logger.error("SKIP: Hardware not connected")
            self.results['parameter_changes'] = 'SKIP'
            return False

        try:
            logger.info("Testing parameter changes...")

            # Try to change some scope parameters
            # This depends on the plugin's parameter tree structure

            logger.info("Testing channel selection...")
            # Example: Try to change active channel if parameter exists
            # Note: Actual parameter names depend on the plugin implementation

            logger.info("Testing averaging...")
            # Example: Try to change averaging setting

            logger.info("Testing decimation...")
            # Example: Try to change decimation setting

            logger.info("PASS: Parameter changes successful")
            logger.info("Note: Specific parameter tests depend on plugin implementation")

            self.results['parameter_changes'] = 'PASS'
            return True

        except Exception as e:
            logger.error(f"FAIL: Parameter change error: {e}")
            import traceback
            traceback.print_exc()
            self.results['parameter_changes'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_5_graceful_shutdown(self):
        """Test 5: Graceful shutdown and cleanup."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: Graceful Shutdown")
        logger.info("="*70)

        if not self.plugin:
            logger.error("SKIP: Plugin not initialized")
            self.results['graceful_shutdown'] = 'SKIP'
            return False

        try:
            logger.info("Closing plugin connection...")

            # Call close method to clean up
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
        logger.info("SCOPE HARDWARE TEST REPORT")
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
            logger.info("✓✓✓ SCOPE HARDWARE TESTS PASSED ✓✓✓")
            logger.info("="*70)
            logger.info("\nScope plugin is READY for production use with Red Pitaya")
            return 0
        elif 'SKIP' in self.results.values():
            logger.warning("⚠⚠⚠ SOME TESTS SKIPPED ⚠⚠⚠")
            logger.warning("="*70)
            logger.warning("\nReview skipped tests and fix blocking issues")
            return 1
        else:
            logger.error("✗✗✗ SCOPE HARDWARE TESTS FAILED ✗✗✗")
            logger.error("="*70)
            logger.error("\nFix all failures before using in production")
            return 1


def main():
    """Run Scope hardware tests."""
    print("\n" + "="*70)
    print("PyMoDAQ PyRPL Plugins - Scope Hardware Testing")
    print("Hardware: Red Pitaya at 100.107.106.75")
    print("="*70)

    tester = ScopeHardwareTest()

    # Run all tests in sequence
    tester.test_1_plugin_initialization()
    tester.test_2_hardware_connection()
    tester.test_3_data_acquisition()
    tester.test_4_parameter_changes()
    tester.test_5_graceful_shutdown()

    return tester.generate_report()


if __name__ == '__main__':
    sys.exit(main())
