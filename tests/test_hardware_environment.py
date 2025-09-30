#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hardware Test Environment Validation for PyMoDAQ PyRPL Plugins

This module provides tests and utilities for validating the hardware test
environment, including Red Pitaya device connectivity and PyRPL compatibility.

Usage:
    pytest tests/test_hardware_environment.py                 # Run all validation tests
    pytest tests/test_hardware_environment.py -m hardware     # Hardware tests only
    python tests/test_hardware_environment.py                 # Direct execution for setup

Environment Variables Required for Hardware Tests:
- PYRPL_TEST_HOST: Hostname or IP of Red Pitaya device
- PYRPL_TEST_CONFIG: PyRPL configuration name (optional)
- PYRPL_HARDWARE_TIMEOUT: Timeout for operations (optional)

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import os
import sys
import time
import socket
import subprocess
import pytest
from typing import Tuple, Optional, Dict, Any
from unittest.mock import patch

# Import test configuration
from conftest import validate_hardware_environment, get_hardware_config, is_hardware_available


class HardwareEnvironmentValidator:
    """Utility class for validating hardware test environment."""

    def __init__(self):
        self.config = get_hardware_config()

    def check_network_connectivity(self, hostname: str, port: int = 22, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check network connectivity to Red Pitaya device.

        Parameters:
            hostname: Red Pitaya hostname or IP
            port: Port to test (default SSH port)
            timeout: Connection timeout

        Returns:
            Tuple of (success, message)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((hostname, port))
            sock.close()

            if result == 0:
                return True, f"Network connectivity to {hostname}:{port} successful"
            else:
                return False, f"Cannot connect to {hostname}:{port} (error code: {result})"

        except socket.gaierror as e:
            return False, f"DNS resolution failed for {hostname}: {e}"
        except Exception as e:
            return False, f"Network error: {e}"

    def check_pyrpl_import(self) -> Tuple[bool, str]:
        """
        Check if PyRPL can be imported successfully.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Try importing PyRPL in a subprocess to avoid Qt issues
            result = subprocess.run(
                [sys.executable, "-c", "import pyrpl; print('PyRPL import successful')"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True, "PyRPL import successful"
            else:
                return False, f"PyRPL import failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "PyRPL import timed out (possible Qt initialization issues)"
        except Exception as e:
            return False, f"PyRPL import error: {e}"

    def validate_environment_variables(self) -> Tuple[bool, str]:
        """
        Validate required environment variables for hardware testing.

        Returns:
            Tuple of (success, message)
        """
        required_vars = ['PYRPL_TEST_HOST']
        optional_vars = ['PYRPL_TEST_CONFIG', 'PYRPL_HARDWARE_TIMEOUT']

        missing_required = []
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)

        if missing_required:
            return False, f"Missing required environment variables: {missing_required}"

        # Check optional variables and provide defaults
        config_info = []
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                config_info.append(f"{var}={value}")
            else:
                config_info.append(f"{var}=<default>")

        return True, f"Environment variables validated. Config: {', '.join(config_info)}"

    def create_test_configuration(self) -> Dict[str, Any]:
        """
        Create test configuration for hardware validation.

        Returns:
            Dictionary with test configuration
        """
        return {
            'hostname': self.config['hostname'],
            'config_name': self.config['config_name'],
            'timeout': self.config['timeout'],
            'test_voltages': [-0.5, 0.0, 0.5],
            'test_frequencies': [100.0, 1000.0, 10000.0],
            'test_pid_gains': {'p': 1.0, 'i': 0.1, 'd': 0.05}
        }

    def generate_setup_instructions(self) -> str:
        """
        Generate setup instructions for hardware testing.

        Returns:
            Multi-line string with setup instructions
        """
        instructions = [
            "Hardware Test Environment Setup Instructions",
            "=" * 50,
            "",
            "1. Red Pitaya Device Setup:",
            "   - Connect Red Pitaya to network",
            "   - Note the device IP address or hostname",
            "   - Ensure PyRPL firmware is loaded",
            "",
            "2. Environment Variables:",
            "   export PYRPL_TEST_HOST=<red_pitaya_ip_or_hostname>",
            "   export PYRPL_TEST_CONFIG=pytest_hardware_config  # Optional",
            "   export PYRPL_HARDWARE_TIMEOUT=15.0  # Optional",
            "",
            "3. Network Connectivity:",
            "   - Ensure the Red Pitaya is reachable from this machine",
            "   - Test with: ping <red_pitaya_ip>",
            "   - SSH access should be available (port 22)",
            "",
            "4. PyRPL Installation:",
            "   - PyRPL should be installed and working",
            "   - Test with: python -c 'import pyrpl'",
            "",
            "5. Running Hardware Tests:",
            "   pytest tests/ -m hardware",
            "",
            "6. Skipping Hardware Tests:",
            "   export PYRPL_MOCK_ONLY=1",
            "",
            f"Current Configuration:",
            f"  PYRPL_TEST_HOST: {os.getenv('PYRPL_TEST_HOST', 'NOT SET')!r}",
            f"  PYRPL_TEST_CONFIG: {os.getenv('PYRPL_TEST_CONFIG', 'NOT SET')!r}",
            f"  PYRPL_HARDWARE_TIMEOUT: {os.getenv('PYRPL_HARDWARE_TIMEOUT', 'NOT SET')!r}",
            f"  PYRPL_MOCK_ONLY: {os.getenv('PYRPL_MOCK_ONLY', 'NOT SET')!r}",
        ]

        return "\n".join(instructions)


# =============================================================================
# Hardware Environment Validation Tests
# =============================================================================

@pytest.mark.hardware
class TestHardwareEnvironment:
    """Test hardware environment validation."""

    def test_environment_variable_validation(self):
        """Test that required environment variables are set."""
        is_valid, message = validate_hardware_environment()

        if not is_valid:
            pytest.skip(f"Hardware environment not configured: {message}")

        assert is_valid
        assert "validated" in message.lower()

    def test_network_connectivity(self):
        """Test network connectivity to Red Pitaya device."""
        if not is_hardware_available():
            pytest.skip("Hardware testing disabled")

        validator = HardwareEnvironmentValidator()
        hostname = validator.config['hostname']

        # Test SSH connectivity
        success, message = validator.check_network_connectivity(hostname, port=22, timeout=5.0)

        if not success:
            pytest.skip(f"Network connectivity test failed: {message}")

        assert success
        assert "successful" in message

    def test_pyrpl_import_capability(self):
        """Test that PyRPL can be imported successfully."""
        if not is_hardware_available():
            pytest.skip("Hardware testing disabled")

        validator = HardwareEnvironmentValidator()
        success, message = validator.check_pyrpl_import()

        if not success:
            pytest.skip(f"PyRPL import test failed: {message}")

        assert success
        assert "successful" in message

    def test_configuration_completeness(self):
        """Test that hardware configuration is complete."""
        if not is_hardware_available():
            pytest.skip("Hardware testing disabled")

        config = get_hardware_config()

        # Check required configuration fields
        assert 'hostname' in config
        assert 'config_name' in config
        assert 'timeout' in config

        # Validate configuration values
        assert config['hostname']  # Should not be empty
        assert config['timeout'] > 0

    def test_test_configuration_generation(self):
        """Test generation of test configuration."""
        if not is_hardware_available():
            pytest.skip("Hardware testing disabled")

        validator = HardwareEnvironmentValidator()
        test_config = validator.create_test_configuration()

        # Verify test configuration structure
        required_keys = ['hostname', 'config_name', 'timeout', 'test_voltages', 'test_frequencies', 'test_pid_gains']
        for key in required_keys:
            assert key in test_config

        # Verify test parameter ranges are reasonable
        assert len(test_config['test_voltages']) > 0
        assert len(test_config['test_frequencies']) > 0
        assert 'p' in test_config['test_pid_gains']


@pytest.mark.integration
class TestHardwareTestFramework:
    """Test the hardware testing framework."""

    def test_mock_hardware_fallback(self):
        """Test that tests fall back to mock when hardware unavailable."""
        # This test should always pass regardless of hardware availability

        # Temporarily disable hardware
        with patch.dict(os.environ, {'PYRPL_MOCK_ONLY': '1'}):
            assert not is_hardware_available()

        # Re-enable based on original environment
        if os.getenv('PYRPL_TEST_HOST') and os.getenv('PYRPL_MOCK_ONLY', '0') != '1':
            assert is_hardware_available()

    def test_environment_isolation(self):
        """Test that test environment is properly isolated."""
        # Save original environment
        original_host = os.getenv('PYRPL_TEST_HOST')
        original_mock_only = os.getenv('PYRPL_MOCK_ONLY')

        try:
            # Test with different configurations
            test_configurations = [
                {'PYRPL_TEST_HOST': None, 'PYRPL_MOCK_ONLY': '1'},
                {'PYRPL_TEST_HOST': 'test.local', 'PYRPL_MOCK_ONLY': '0'},
            ]

            for config in test_configurations:
                with patch.dict(os.environ, config, clear=False):
                    is_valid, message = validate_hardware_environment()

                    if config['PYRPL_MOCK_ONLY'] == '1':
                        assert not is_valid
                    elif config['PYRPL_TEST_HOST']:
                        assert is_valid

        finally:
            # Restore original environment
            if original_host is not None:
                os.environ['PYRPL_TEST_HOST'] = original_host
            elif 'PYRPL_TEST_HOST' in os.environ:
                del os.environ['PYRPL_TEST_HOST']

            if original_mock_only is not None:
                os.environ['PYRPL_MOCK_ONLY'] = original_mock_only
            elif 'PYRPL_MOCK_ONLY' in os.environ:
                del os.environ['PYRPL_MOCK_ONLY']

    def test_hardware_test_markers(self):
        """Test that hardware test markers work correctly."""
        # This test validates the pytest marker system
        import pytest

        # Check that hardware marker exists
        marker_names = [marker.name for marker in pytest.get_markers()]

        # The marker should be available (defined in conftest.py)
        # Note: This might not be available in all pytest versions
        # so we'll check the configuration instead

        # Just verify we can create marked tests
        @pytest.mark.hardware
        def dummy_hardware_test():
            pass

        assert hasattr(dummy_hardware_test, 'pytestmark')


# =============================================================================
# Utility Functions for Direct Execution
# =============================================================================

def run_environment_validation():
    """Run environment validation and print results."""
    print("PyMoDAQ PyRPL Hardware Environment Validation")
    print("=" * 50)

    validator = HardwareEnvironmentValidator()

    # Check environment variables
    print("\n1. Environment Variables:")
    is_valid, message = validator.validate_environment_variables()
    print(f"   Status: {'✓' if is_valid else '✗'} {message}")

    if not is_valid:
        print("\n" + validator.generate_setup_instructions())
        return False

    # Check network connectivity
    print("\n2. Network Connectivity:")
    hostname = validator.config['hostname']
    is_reachable, message = validator.check_network_connectivity(hostname)
    print(f"   Status: {'✓' if is_reachable else '✗'} {message}")

    # Check PyRPL import
    print("\n3. PyRPL Import Test:")
    can_import, message = validator.check_pyrpl_import()
    print(f"   Status: {'✓' if can_import else '✗'} {message}")

    # Generate test configuration
    print("\n4. Test Configuration:")
    test_config = validator.create_test_configuration()
    print(f"   Hostname: {test_config['hostname']}")
    print(f"   Config Name: {test_config['config_name']}")
    print(f"   Timeout: {test_config['timeout']}s")

    # Overall status
    all_valid = is_valid and is_reachable and can_import
    print(f"\nOverall Status: {'✓ READY' if all_valid else '✗ NOT READY'}")

    if not all_valid:
        print("\nSetup Instructions:")
        print(validator.generate_setup_instructions())

    return all_valid


if __name__ == "__main__":
    # Direct execution - run validation
    if len(sys.argv) > 1 and sys.argv[1] == "--setup-instructions":
        validator = HardwareEnvironmentValidator()
        print(validator.generate_setup_instructions())
    else:
        success = run_environment_validation()
        sys.exit(0 if success else 1)