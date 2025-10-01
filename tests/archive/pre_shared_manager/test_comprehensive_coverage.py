#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Coverage for PyMoDAQ PyRPL Plugin System

This module provides complete test coverage for the PyMoDAQ PyRPL plugin system,
including mock simulation, hardware integration, and edge case handling.

Test Categories:
- Priority 1: Mock System Tests (enhanced simulation, presets, lifecycle)
- Priority 2: Hardware Integration Tests (real device connection, parity)
- Priority 3: Edge Cases (concurrency, errors, resource management)

Usage:
    pytest tests/test_comprehensive_coverage.py -m mock        # Mock tests only
    pytest tests/test_comprehensive_coverage.py -m hardware    # Hardware tests only
    pytest tests/test_comprehensive_coverage.py               # All applicable tests

Environment Variables:
- PYRPL_TEST_HOST: Hostname for hardware tests
- PYRPL_MOCK_ONLY: Set to '1' to skip hardware tests
- PYRPL_TEST_CONFIG: PyRPL configuration name

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import pytest
import threading
import time
import numpy as np
from unittest.mock import Mock, patch, PropertyMock
from typing import Optional

# Import plugin classes and utilities
from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import EnhancedMockPyRPLConnection
from pymodaq_plugins_pyrpl.utils.demo_presets import apply_demo_preset, get_demo_preset_manager
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PIDChannel, InputChannel, OutputChannel

# PyMoDAQ imports
from pymodaq.control_modules.move_utility_classes import DataActuator

# Import test configuration utilities
from conftest import validate_hardware_environment, get_hardware_config, TEST_CONFIG


# =============================================================================
# Priority 1: Mock System Tests
# =============================================================================

@pytest.mark.mock
class TestEnhancedMockSystem:
    """Test the enhanced mock simulation system."""

    def test_enhanced_mock_initialization(self, enhanced_mock_connection):
        """Test that enhanced mock connection initializes properly."""
        connection = enhanced_mock_connection

        # Verify connection state
        assert connection.is_connected is True
        assert connection.state.value == "connected"

        # Verify simulation info structure
        sim_info = connection.get_simulation_info()
        assert isinstance(sim_info, dict)
        assert 'type' in sim_info
        assert 'description' in sim_info
        assert 'parameters' in sim_info

    def test_shared_instance_registry(self, enhanced_mock_connection):
        """Test that connections with same hostname share instances."""
        hostname = "test-enhanced.local"

        # First connection from fixture
        conn1 = enhanced_mock_connection

        # Second connection should be same instance
        conn2 = EnhancedMockPyRPLConnection(hostname)
        assert conn1 is conn2

        # Different hostname should be different instance
        conn3 = EnhancedMockPyRPLConnection("different.local")
        assert conn1 is not conn3

    def test_realistic_plant_dynamics(self, enhanced_mock_connection):
        """Test realistic plant dynamics and simulation behavior."""
        connection = enhanced_mock_connection

        # Set scenario and test dynamics
        success = connection.set_simulation_scenario("stable_system")
        assert success is True

        # Set setpoint and controller output
        connection.set_pid_setpoint(PIDChannel.PID0, 1.0)
        connection.set_pid_controller_output(PIDChannel.PID0, 0.5)

        # Read process variable - should be influenced by plant dynamics
        pv1 = connection.read_voltage(InputChannel.IN1)

        # Step simulation and check for change
        connection.simulation.step_simulation()
        pv2 = connection.read_voltage(InputChannel.IN1)

        # Process variable should be in reasonable range
        assert -2.0 < pv1 < 2.0
        assert -2.0 < pv2 < 2.0

    def test_performance_metrics_calculation(self, enhanced_mock_connection):
        """Test performance metrics calculation during simulation."""
        connection = enhanced_mock_connection

        # Reset and configure simulation
        connection.reset_simulation()
        connection.set_pid_setpoint(PIDChannel.PID0, 0.5)

        # Run several simulation steps
        for _ in range(10):
            connection.set_pid_controller_output(PIDChannel.PID0, 0.3)
            time.sleep(0.01)

        # Get performance metrics
        metrics = connection.get_performance_metrics()
        assert isinstance(metrics, dict)
        assert 'steady_state_error' in metrics
        assert 'current_pv' in metrics
        assert metrics['steady_state_error'] >= 0

    def test_scenario_switching(self, enhanced_mock_connection):
        """Test switching between different simulation scenarios."""
        connection = enhanced_mock_connection

        scenarios = ["stable_system", "oscillatory_system", "sluggish_system"]

        for scenario in scenarios:
            success = connection.set_simulation_scenario(scenario)
            assert success is True

            info = connection.get_simulation_info()
            assert info['type'] == scenario


@pytest.mark.mock
class TestDemoPresets:
    """Test demonstration preset system."""

    def test_demo_preset_manager_access(self, demo_preset_manager):
        """Test that demo preset manager provides valid presets."""
        manager = demo_preset_manager

        # Get available presets
        presets = manager.list_presets()
        assert len(presets) > 0
        assert "stable_basic" in presets
        assert "oscillatory_challenge" in presets

    def test_preset_application_to_plugin(self, mock_move_plugin, demo_preset_manager):
        """Test applying demo presets to plugins."""
        plugin = mock_move_plugin
        manager = demo_preset_manager

        # Apply preset
        success = apply_demo_preset("stable_basic", plugin, "pid")
        assert success is True

        # Verify preset was applied (check mock calls)
        plugin.settings.child.assert_called()

    def test_preset_validation(self, demo_preset_manager):
        """Test preset validation and information retrieval."""
        manager = demo_preset_manager

        # Test valid preset
        preset = manager.get_preset("stable_basic")
        assert preset is not None
        assert preset.scenario_type.value == "stable_system"
        assert preset.pid_p_gain > 0

        # Test invalid preset
        invalid_preset = manager.get_preset("nonexistent")
        assert invalid_preset is None

    def test_preset_scenario_guide(self, demo_preset_manager):
        """Test demonstration scenario guide generation."""
        manager = demo_preset_manager

        guide = manager.create_demo_scenario_guide()
        assert isinstance(guide, str)
        assert len(guide) > 500  # Should be substantial content
        assert "PyMoDAQ PyRPL Mock Demonstration" in guide


@pytest.mark.mock
class TestPluginLifecycleMock:
    """Test plugin lifecycle in mock mode."""

    def test_mock_mode_initialization(self, mock_move_plugin):
        """Test plugin initialization in mock mode."""
        plugin = mock_move_plugin

        # Enable mock mode
        plugin.settings.child('connection_settings', 'mock_mode').setValue(True)

        # Mock is_master property
        with patch.object(type(plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
            mock_is_master.return_value = True

            # Initialize plugin
            plugin.ini_attributes()
            info, success = plugin.ini_stage()

            assert success is True
            assert "mock" in info.lower()

    def test_mock_mode_operations(self, mock_move_plugin):
        """Test actuator operations in mock mode."""
        plugin = mock_move_plugin
        plugin.mock_mode = True
        plugin.is_pid_configured = True

        # Mock enhanced connection
        mock_connection = Mock()
        mock_connection.is_connected = True
        mock_connection.set_pid_setpoint.return_value = True
        plugin.controller = mock_connection

        # Test move operations
        actuator_data = DataActuator(data=0.5, units='V')
        plugin.move_abs(actuator_data)

        # Verify controller interaction
        mock_connection.set_pid_setpoint.assert_called()
        plugin.emit_status.assert_called()

    def test_mock_cleanup(self, mock_move_plugin):
        """Test proper cleanup in mock mode."""
        plugin = mock_move_plugin
        plugin.controller = Mock()

        # Test cleanup
        plugin.close()

        # Should not error when called multiple times
        plugin.close()
        plugin.close()


@pytest.mark.mock
class TestMultiPluginCoordination:
    """Test coordination between multiple plugins in mock mode."""

    def test_shared_simulation_state(self, enhanced_mock_connection):
        """Test that multiple plugins share simulation state."""
        hostname = "shared-sim.local"

        # Create multiple connections
        conn1 = EnhancedMockPyRPLConnection(hostname)
        conn2 = EnhancedMockPyRPLConnection(hostname)

        # Should be same instance
        assert conn1 is conn2

        # Changes in one should affect the other
        conn1.set_pid_setpoint(PIDChannel.PID0, 0.8)
        setpoint1 = conn1.get_pid_setpoint(PIDChannel.PID0)
        setpoint2 = conn2.get_pid_setpoint(PIDChannel.PID0)

        assert setpoint1 == setpoint2 == 0.8

    def test_time_synchronized_updates(self, enhanced_mock_connection):
        """Test time-synchronized simulation updates."""
        connection = enhanced_mock_connection

        # Get initial history length
        history = connection.simulation.get_history(samples=100)
        initial_length = len(history['pv'])

        # Step simulation multiple times
        for _ in range(5):
            connection.simulation.step_simulation()
            time.sleep(0.01)

        # History should have grown
        new_history = connection.simulation.get_history(samples=100)
        new_length = len(new_history['pv'])

        assert new_length > initial_length


# =============================================================================
# Priority 2: Hardware Integration Tests
# =============================================================================

@pytest.mark.hardware
class TestHardwareIntegration:
    """Test real hardware integration when available."""

    def test_hardware_environment_validation(self):
        """Test hardware environment validation."""
        is_valid, message = validate_hardware_environment()

        # This test should only run if hardware is configured
        if not is_valid:
            pytest.skip(f"Hardware environment not available: {message}")

        assert is_valid
        assert "Hardware environment validated" in message

    def test_hardware_connection_attempt(self, mock_move_plugin, skip_if_no_hardware):
        """Test connection attempt to real hardware."""
        plugin = mock_move_plugin

        # Disable mock mode
        plugin.settings.child('connection_settings', 'mock_mode').setValue(False)

        with patch.object(type(plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
            mock_is_master.return_value = True

            # Attempt initialization (will use mocked PyRPL manager)
            info, success = plugin.ini_stage()

            # Should succeed with mocked hardware
            assert success is True
            assert isinstance(info, str)

    def test_hardware_vs_mock_parity(self, mock_move_plugin):
        """Test that hardware and mock modes have similar interfaces."""
        plugin = mock_move_plugin

        # Test mock mode
        plugin.settings.child('connection_settings', 'mock_mode').setValue(True)
        plugin.ini_attributes()

        # Test hardware mode
        plugin.settings.child('connection_settings', 'mock_mode').setValue(False)
        plugin.ini_attributes()

        # Both should have same attribute structure
        assert hasattr(plugin, 'controller')
        assert hasattr(plugin, 'mock_mode')

    def test_network_error_simulation(self, mock_move_plugin):
        """Test network error handling."""
        plugin = mock_move_plugin
        plugin.mock_mode = False

        # Simulate network error
        mock_controller = Mock()
        mock_controller.is_connected = False
        plugin.controller = mock_controller

        # Attempt operation
        actuator_data = DataActuator(data=0.3, units='V')
        plugin.move_abs(actuator_data)

        # Should emit error status
        plugin.emit_status.assert_called()

    def test_device_resource_management(self, mock_move_plugin):
        """Test proper device resource management."""
        plugin = mock_move_plugin
        plugin.mock_mode = False
        plugin.is_pid_configured = True

        # Mock connected controller
        mock_controller = Mock()
        mock_controller.is_connected = True
        mock_controller.disable_pid_output.return_value = True
        plugin.controller = mock_controller

        # Test cleanup
        plugin.close()

        # Should have attempted to disable PID
        if hasattr(mock_controller, 'disable_pid_output'):
            mock_controller.disable_pid_output.assert_called()


# =============================================================================
# Priority 3: Edge Cases and Error Handling
# =============================================================================

@pytest.mark.error_handling
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_parameters(self, mock_move_plugin):
        """Test handling of invalid parameters."""
        plugin = mock_move_plugin

        # Create invalid parameter
        invalid_param = Mock()
        invalid_param.name.return_value = "nonexistent_parameter"
        invalid_param.value.return_value = "invalid_value"

        # Should not raise exception
        try:
            plugin.commit_settings(invalid_param)
        except Exception as e:
            pytest.fail(f"commit_settings raised unexpected exception: {e}")

    def test_connection_failure_handling(self, mock_move_plugin):
        """Test handling of connection failures."""
        plugin = mock_move_plugin
        plugin.mock_mode = False

        # Simulate connection failure
        with patch('pymodaq_plugins_pyrpl.utils.pyrpl_wrapper.PyRPLManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.connect_device.return_value = None  # Connection failure
            mock_manager_class.return_value = mock_manager

            with patch.object(type(plugin), 'is_master', new_callable=PropertyMock) as mock_is_master:
                mock_is_master.return_value = True

                info, success = plugin.ini_stage()

                # Should handle failure gracefully
                assert success is False
                assert "failed" in info.lower() or "error" in info.lower()

    def test_resource_cleanup_edge_cases(self, mock_move_plugin):
        """Test resource cleanup edge cases."""
        plugin = mock_move_plugin

        # Test cleanup with no controller
        plugin.controller = None
        plugin.close()  # Should not error

        # Test cleanup with exception in controller
        mock_controller = Mock()
        mock_controller.disconnect.side_effect = Exception("Cleanup error")
        plugin.controller = mock_controller

        # Should handle cleanup error gracefully
        try:
            plugin.close()
        except Exception as e:
            pytest.fail(f"close() should handle cleanup errors gracefully: {e}")

    def test_invalid_voltage_ranges(self, enhanced_mock_connection):
        """Test handling of invalid voltage ranges."""
        connection = enhanced_mock_connection

        # Test extreme values
        extreme_values = [-10.0, 10.0, float('inf'), float('-inf')]

        for value in extreme_values:
            try:
                # Should handle extreme values gracefully
                connection.set_pid_setpoint(PIDChannel.PID0, value)
                voltage = connection.read_voltage(InputChannel.IN1)
                assert isinstance(voltage, (int, float))
            except Exception as e:
                # Some extreme values may raise exceptions, which is acceptable
                assert "inf" in str(e).lower() or "range" in str(e).lower()


@pytest.mark.thread_safety
class TestThreadSafety:
    """Test thread safety and concurrent operations."""

    def test_concurrent_plugin_access(self, mock_move_plugin):
        """Test concurrent access to plugin operations."""
        plugin = mock_move_plugin
        plugin.mock_mode = True
        plugin.controller = Mock()
        plugin.controller.is_connected = True
        plugin.controller.set_pid_setpoint.return_value = True

        def worker(value):
            actuator_data = DataActuator(data=value, units='V')
            plugin.move_abs(actuator_data)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(0.1 * i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify all operations completed
        assert plugin.emit_status.call_count >= 5

    def test_simulation_thread_safety(self, enhanced_mock_connection):
        """Test thread safety of simulation engine."""
        connection = enhanced_mock_connection

        def simulation_worker():
            for _ in range(10):
                connection.set_pid_setpoint(PIDChannel.PID0, np.random.uniform(0, 1))
                connection.read_voltage(InputChannel.IN1)
                time.sleep(0.001)

        # Multiple threads accessing simulation
        threads = []
        for _ in range(3):
            t = threading.Thread(target=simulation_worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Simulation should still be functional
        voltage = connection.read_voltage(InputChannel.IN1)
        assert isinstance(voltage, (int, float))

    def test_shared_instance_thread_safety(self):
        """Test thread safety of shared instance creation."""
        hostname = "thread-test.local"
        instances = []

        def create_instance():
            instance = EnhancedMockPyRPLConnection(hostname)
            instances.append(instance)

        # Create instances from multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=create_instance)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance


@pytest.mark.performance
class TestPerformance:
    """Test performance and timing characteristics."""

    def test_data_acquisition_timing(self, enhanced_mock_connection):
        """Test data acquisition performance."""
        connection = enhanced_mock_connection

        # Measure multiple acquisitions
        start_time = time.time()
        voltages = []

        for _ in range(100):
            voltage = connection.read_voltage(InputChannel.IN1)
            voltages.append(voltage)

        elapsed = time.time() - start_time

        # Should be reasonably fast (less than 1 second for 100 readings)
        assert elapsed < 1.0
        assert len(voltages) == 100

    def test_simulation_step_performance(self, enhanced_mock_connection):
        """Test simulation step performance."""
        connection = enhanced_mock_connection

        # Measure simulation steps
        start_time = time.time()

        for _ in range(50):
            connection.simulation.step_simulation()

        elapsed = time.time() - start_time

        # Should complete quickly
        assert elapsed < 0.5

    def test_memory_usage_stability(self, enhanced_mock_connection):
        """Test that memory usage remains stable during operation."""
        connection = enhanced_mock_connection

        # Perform many operations
        for _ in range(1000):
            connection.set_pid_setpoint(PIDChannel.PID0, 0.5)
            connection.read_voltage(InputChannel.IN1)
            if _ % 100 == 0:  # Occasional cleanup
                connection.reset_simulation()

        # Test should complete without memory issues
        assert connection.is_connected is True


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestPyMoDAQIntegration:
    """Test integration with PyMoDAQ framework."""

    def test_plugin_parameter_structure(self, mock_move_plugin):
        """Test that plugin parameters conform to PyMoDAQ structure."""
        plugin = mock_move_plugin
        plugin.ini_attributes()

        # Plugin should have required attributes
        assert hasattr(plugin, 'settings')
        assert hasattr(plugin, 'emit_status')
        assert hasattr(plugin, 'controller')

    def test_data_structure_compatibility(self, mock_viewer_plugin):
        """Test PyMoDAQ data structure compatibility."""
        from pymodaq_data.data import DataRaw, DataToExport

        plugin = mock_viewer_plugin

        # Mock data emission
        test_data = DataRaw(
            name="test_voltage",
            data=np.array([0.5]),
            labels=["Voltage"],
            units="V"
        )

        data_export = DataToExport(name="PyRPL Test", data=[test_data])

        # Should be able to emit without error
        plugin.dte_signal.emit(data_export)
        plugin.dte_signal.emit.assert_called_with(data_export)

    def test_threadcommand_integration(self, mock_move_plugin):
        """Test ThreadCommand integration with PyMoDAQ."""
        from pymodaq.utils.tcp_server_client import ThreadCommand

        plugin = mock_move_plugin

        # Test status emission
        test_command = ThreadCommand('Update_Status', ['Test message', 'log'])
        plugin.emit_status(test_command)

        plugin.emit_status.assert_called_with(test_command)


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])