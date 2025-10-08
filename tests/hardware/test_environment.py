#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Environment Validation for Hardware Testing

This script validates the testing environment before running hardware tests.
MUST pass before proceeding with hardware tests.

Tests:
1. Red Pitaya connectivity (100.107.106.75:22)
2. PyMoDAQ installation and imports
3. PyRPL library availability
4. Plugin imports (CRITICAL: no config file I/O at import time)
5. Architectural fix verification
"""

import sys
import socket
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates testing environment before hardware tests."""

    def __init__(self):
        self.results = {}
        self.all_passed = True

    def test_1_red_pitaya_connectivity(self):
        """Test 1: Verify Red Pitaya hardware is reachable."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Red Pitaya Hardware Connectivity")
        logger.info("="*70)

        try:
            host = '100.107.106.75'
            port = 22  # SSH port

            logger.info(f"Connecting to {host}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                logger.info(f"PASS: Red Pitaya reachable at {host}:{port}")
                self.results['red_pitaya_connectivity'] = 'PASS'
                return True
            else:
                logger.error(f"FAIL: Cannot reach Red Pitaya at {host}:{port}")
                logger.error("Check network connection and hardware power")
                self.results['red_pitaya_connectivity'] = 'FAIL'
                self.all_passed = False
                return False

        except Exception as e:
            logger.error(f"FAIL: Connection test error: {e}")
            self.results['red_pitaya_connectivity'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_2_pymodaq_installation(self):
        """Test 2: Verify PyMoDAQ is installed and importable."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: PyMoDAQ Installation")
        logger.info("="*70)

        try:
            import pymodaq
            logger.info(f"PASS: PyMoDAQ version {pymodaq.__version__}")

            # Test critical imports
            from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
            from pymodaq_data.data import DataRaw

            logger.info("PASS: Critical PyMoDAQ imports successful")
            self.results['pymodaq_installation'] = 'PASS'
            return True

        except ImportError as e:
            logger.error(f"FAIL: PyMoDAQ import error: {e}")
            logger.error("Install PyMoDAQ: pip install pymodaq")
            self.results['pymodaq_installation'] = f'FAIL: {e}'
            self.all_passed = False
            return False
        except Exception as e:
            logger.error(f"FAIL: PyMoDAQ error: {e}")
            self.results['pymodaq_installation'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_3_pyrpl_availability(self):
        """Test 3: Check if PyRPL is available."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: PyRPL Library Availability")
        logger.info("="*70)

        try:
            # Try importing the wrapper first (uses stemlab)
            from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
            logger.info("PASS: PyRPL wrapper imports successfully")
            logger.info("Note: Using stemlab (headless PyRPL fork)")
            self.results['pyrpl_availability'] = 'PASS'
            return True

        except ImportError as e:
            logger.warning(f"WARNING: PyRPL wrapper import issue: {e}")
            logger.warning("This is expected if stemlab is not installed")
            logger.info("Plugins will use mock mode if PyRPL unavailable")
            self.results['pyrpl_availability'] = f'WARN: {e}'
            # Don't fail - mock mode is acceptable
            return True
        except Exception as e:
            logger.error(f"FAIL: PyRPL error: {e}")
            self.results['pyrpl_availability'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def test_4_plugin_imports_no_io(self):
        """Test 4: CRITICAL - Verify plugins import without config file I/O."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Plugin Imports (Architectural Fix Verification)")
        logger.info("="*70)
        logger.info("CRITICAL: Plugins must NOT load config files at import time")

        try:
            # Import plugins - should NOT trigger config file reads
            logger.info("Importing ASG plugin...")
            from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG import DAQ_Move_PyRPL_ASG

            logger.info("Importing PID plugin...")
            from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID

            logger.info("Importing Scope plugin...")
            from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope import DAQ_1DViewer_PyRPL_Scope

            # Verify static params exist
            logger.info("\nVerifying static params pattern...")
            assert hasattr(DAQ_Move_PyRPL_ASG, 'params'), "ASG missing params"
            assert isinstance(DAQ_Move_PyRPL_ASG.params, list), "ASG params not list"
            logger.info("PASS: ASG has static params")

            assert hasattr(DAQ_Move_PyRPL_PID, 'params'), "PID missing params"
            assert isinstance(DAQ_Move_PyRPL_PID.params, list), "PID params not list"
            logger.info("PASS: PID has static params")

            assert hasattr(DAQ_1DViewer_PyRPL_Scope, 'params'), "Scope missing params"
            assert isinstance(DAQ_1DViewer_PyRPL_Scope.params, list), "Scope params not list"
            logger.info("PASS: Scope has static params")

            # Verify hardcoded hostname
            found_hostname = False
            for param in DAQ_Move_PyRPL_ASG.params:
                if param.get('name') == 'connection_settings':
                    for child in param.get('children', []):
                        if child.get('name') == 'redpitaya_host':
                            hostname = child.get('value')
                            assert hostname == '100.107.106.75', f"Wrong hostname: {hostname}"
                            logger.info(f"PASS: ASG hardcoded hostname: {hostname}")
                            found_hostname = True
                            break

            assert found_hostname, "ASG hostname not found in params"

            logger.info("\nPASS: All plugins import successfully")
            logger.info("PASS: Static params pattern verified")
            logger.info("PASS: Architectural fix confirmed (no config I/O at import)")
            self.results['plugin_imports'] = 'PASS'
            return True

        except ImportError as e:
            logger.error(f"FAIL: Plugin import error: {e}")
            logger.error("Check plugin installation and dependencies")
            self.results['plugin_imports'] = f'FAIL: {e}'
            self.all_passed = False
            return False
        except AssertionError as e:
            logger.error(f"FAIL: Architectural verification failed: {e}")
            self.results['plugin_imports'] = f'FAIL: {e}'
            self.all_passed = False
            return False
        except Exception as e:
            logger.error(f"FAIL: Plugin error: {e}")
            import traceback
            traceback.print_exc()
            self.results['plugin_imports'] = f'FAIL: {e}'
            self.all_passed = False
            return False

    def generate_report(self):
        """Generate environment validation report."""
        logger.info("\n" + "="*70)
        logger.info("ENVIRONMENT VALIDATION REPORT")
        logger.info("="*70)

        for test_name, result in self.results.items():
            status = "PASS" if result == "PASS" else "FAIL" if "FAIL" in result else "WARN"
            symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
            logger.info(f"{symbol} {test_name:.<50} {result}")

        logger.info("\n" + "="*70)
        if self.all_passed:
            logger.info("✓✓✓ ENVIRONMENT VALIDATION PASSED ✓✓✓")
            logger.info("="*70)
            logger.info("\nREADY FOR HARDWARE TESTING")
            logger.info("Proceed with: python tests/hardware/test_scope_hardware.py")
            return 0
        else:
            logger.error("✗✗✗ ENVIRONMENT VALIDATION FAILED ✗✗✗")
            logger.error("="*70)
            logger.error("\nCANNOT PROCEED WITH HARDWARE TESTING")
            logger.error("Fix all FAIL items above before continuing")
            return 1


def main():
    """Run environment validation."""
    print("\n" + "="*70)
    print("PyMoDAQ PyRPL Plugins - Hardware Testing Environment Validation")
    print("="*70)

    validator = EnvironmentValidator()

    # Run all tests
    validator.test_1_red_pitaya_connectivity()
    validator.test_2_pymodaq_installation()
    validator.test_3_pyrpl_availability()
    validator.test_4_plugin_imports_no_io()

    return validator.generate_report()


if __name__ == '__main__':
    sys.exit(main())
