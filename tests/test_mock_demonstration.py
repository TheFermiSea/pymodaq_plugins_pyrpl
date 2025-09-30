#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for PyMoDAQ PyRPL Mock Demonstration System

This test module validates the enhanced mock demonstration system including
simulation engine, preset management, and plugin integration for educational
PID control demonstrations.

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import pytest
import time
import numpy as np
from unittest.mock import MagicMock, patch

# Import the demonstration system components
from src.pymodaq_plugins_pyrpl.utils.mock_simulation import (
    get_simulation_engine, ScenarioType, SimulatedPlant, PlantParameters
)
from src.pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import (
    EnhancedMockPyRPLConnection, create_enhanced_mock_connection
)
from src.pymodaq_plugins_pyrpl.utils.demo_presets import (
    get_demo_preset_manager, DemoPreset, apply_demo_preset
)

# Import PyRPL wrapper enums
try:
    from src.pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import (
        PIDChannel, InputChannel, OutputChannel
    )
except ImportError:
    # Fallback for testing environment
    from enum import Enum

    class PIDChannel(Enum):
        PID0 = "pid0"

    class InputChannel(Enum):
        IN1 = "in1"

    class OutputChannel(Enum):
        OUT1 = "out1"


class TestSimulationEngine:
    """Test the core simulation engine functionality."""

    def test_simulation_engine_singleton(self):
        """Test that simulation engine is a singleton."""
        engine1 = get_simulation_engine()
        engine2 = get_simulation_engine()
        assert engine1 is engine2, "Simulation engine should be singleton"

    def test_plant_scenarios(self):
        """Test different plant scenarios are configured correctly."""
        engine = get_simulation_engine()

        test_scenarios = [
            ScenarioType.STABLE_SYSTEM,
            ScenarioType.OSCILLATORY_SYSTEM,
            ScenarioType.SLUGGISH_SYSTEM,
            ScenarioType.NOISY_ENVIRONMENT,
            ScenarioType.INTEGRATING_PROCESS
        ]

        for scenario in test_scenarios:
            engine.set_scenario(scenario, reset_plant=True)
            info = engine.get_scenario_info()

            assert info['type'] == scenario.value
            assert 'parameters' in info
            assert info['parameters']['gain'] > 0

            # Note: integrating flag would be checked via plant parameters if needed

    def test_plant_simulation_step(self):
        """Test plant simulation dynamics."""
        engine = get_simulation_engine()
        engine.set_scenario(ScenarioType.STABLE_SYSTEM, reset_plant=True)

        # Set setpoint and step simulation
        engine.set_setpoint(1.0)
        initial_pv = engine.get_process_variable()

        # Apply controller output and step
        engine.set_controller_output(0.5)
        engine.step_simulation()

        # Process variable should change towards setpoint
        new_pv = engine.get_process_variable()
        assert new_pv != initial_pv, "Process variable should change after step"

    def test_performance_metrics(self):
        """Test performance metrics calculation."""
        engine = get_simulation_engine()
        engine.set_scenario(ScenarioType.STABLE_SYSTEM, reset_plant=True)

        # Reset metrics and run simulation
        engine.reset_simulation()
        engine.set_setpoint(1.0)

        # Run several simulation steps
        for _ in range(10):
            engine.set_controller_output(0.5)
            engine.step_simulation()
            time.sleep(0.01)  # Small delay for realistic timing

        metrics = engine.get_performance_metrics()

        assert 'steady_state_error' in metrics
        assert 'current_pv' in metrics
        assert metrics['steady_state_error'] >= 0
        assert isinstance(metrics['current_pv'], float)

    def test_simulation_history(self):
        """Test simulation history tracking."""
        engine = get_simulation_engine()
        engine.reset_simulation()

        # Generate some history
        for i in range(5):
            engine.set_setpoint(float(i))
            engine.set_controller_output(0.1 * i)
            engine.step_simulation()

        history = engine.get_history(samples=10)

        assert 'pv' in history
        assert 'setpoint' in history
        assert 'input' in history
        assert 'time' in history
        assert len(history['pv']) <= 10


class TestEnhancedMockConnection:
    """Test the enhanced mock connection system."""

    def test_shared_instances(self):
        """Test that connections with same hostname share instances."""
        hostname = "test.pyrpl.local"

        conn1 = EnhancedMockPyRPLConnection(hostname)
        conn2 = EnhancedMockPyRPLConnection(hostname)

        assert conn1 is conn2, "Same hostname should return same instance"

    def test_different_hostnames(self):
        """Test that different hostnames get different instances."""
        conn1 = EnhancedMockPyRPLConnection("host1.local")
        conn2 = EnhancedMockPyRPLConnection("host2.local")

        assert conn1 is not conn2, "Different hostnames should return different instances"

    def test_voltage_reading(self):
        """Test voltage reading functionality."""
        conn = EnhancedMockPyRPLConnection("test.pyrpl.local")

        # Test IN1 (process variable)
        voltage_in1 = conn.read_voltage(InputChannel.IN1)
        assert isinstance(voltage_in1, float)
        assert -2.0 < voltage_in1 < 2.0  # Reasonable voltage range

        # Test IN2 (independent signal)
        voltage_in2 = conn.read_voltage(InputChannel.IN2)
        assert isinstance(voltage_in2, float)
        assert -2.0 < voltage_in2 < 2.0

    def test_pid_control(self):
        """Test PID control functionality."""
        conn = EnhancedMockPyRPLConnection("test.pyrpl.local")

        # Set PID setpoint
        success = conn.set_pid_setpoint(PIDChannel.PID0, 0.5)
        assert success, "Setting PID setpoint should succeed"

        # Get PID setpoint
        setpoint = conn.get_pid_setpoint(PIDChannel.PID0)
        assert setpoint == 0.5, "Retrieved setpoint should match set value"

        # Set controller output
        success = conn.set_pid_controller_output(PIDChannel.PID0, 0.3)
        assert success, "Setting controller output should succeed"

    def test_simulation_scenario_control(self):
        """Test simulation scenario management."""
        conn = EnhancedMockPyRPLConnection("test.pyrpl.local")

        # Test scenario changing
        success = conn.set_simulation_scenario(ScenarioType.OSCILLATORY_SYSTEM)
        assert success, "Setting simulation scenario should succeed"

        info = conn.get_simulation_info()
        assert info['type'] == ScenarioType.OSCILLATORY_SYSTEM.value

    def test_connection_info(self):
        """Test connection information retrieval."""
        hostname = "test.pyrpl.local"
        conn = EnhancedMockPyRPLConnection(hostname)

        info = conn.get_connection_info()

        assert info['hostname'] == hostname
        assert info['is_mock'] is True
        assert info['state'] == 'connected'
        assert 'simulation_scenario' in info


class TestDemoPresets:
    """Test the demonstration preset system."""

    def test_preset_manager_initialization(self):
        """Test that preset manager initializes with default presets."""
        manager = get_demo_preset_manager()
        presets = manager.list_presets()

        assert len(presets) > 0, "Should have default presets"
        assert "stable_basic" in presets
        assert "oscillatory_challenge" in presets
        assert "integrating_level" in presets

    def test_preset_retrieval(self):
        """Test preset retrieval and information."""
        manager = get_demo_preset_manager()

        preset = manager.get_preset("stable_basic")
        assert preset is not None
        assert preset.name == "Stable System - Basic PID"
        assert preset.scenario_type == ScenarioType.STABLE_SYSTEM
        assert preset.pid_p_gain > 0
        assert preset.pid_i_gain >= 0

    def test_preset_info(self):
        """Test preset information formatting."""
        manager = get_demo_preset_manager()

        info = manager.get_preset_info("stable_basic")
        assert info is not None
        assert 'name' in info
        assert 'description' in info
        assert 'scenario' in info
        assert 'pid_settings' in info

    def test_nonexistent_preset(self):
        """Test handling of nonexistent presets."""
        manager = get_demo_preset_manager()

        preset = manager.get_preset("nonexistent_preset")
        assert preset is None

        info = manager.get_preset_info("nonexistent_preset")
        assert info is None

    def test_demo_scenario_guide(self):
        """Test demonstration scenario guide generation."""
        manager = get_demo_preset_manager()

        guide = manager.create_demo_scenario_guide()
        assert isinstance(guide, str)
        assert len(guide) > 100  # Should be substantial content
        assert "PyMoDAQ PyRPL Mock Demonstration" in guide
        assert "stable_basic" in guide


class TestIntegratedDemonstration:
    """Test integrated demonstration system functionality."""

    def test_mock_plugin_simulation(self):
        """Test mock plugin with simulation integration."""
        # Create mock plugin with essential attributes
        mock_plugin = MagicMock()
        mock_plugin.__class__.__name__ = "DAQ_Move_PyRPL_PID"

        # Mock settings structure
        mock_settings = MagicMock()
        mock_plugin.settings = mock_settings

        # Mock the child method to return mock parameter objects
        def mock_child(*args):
            mock_param = MagicMock()
            mock_param.setValue = MagicMock()
            return mock_param

        mock_settings.child = mock_child

        # Test preset application
        success = apply_demo_preset("stable_basic", mock_plugin)
        assert success, "Applying demo preset should succeed"

    def test_coordinated_simulation(self):
        """Test coordinated simulation across multiple mock connections."""
        hostname = "demo.pyrpl.local"

        # Create multiple connections to same hostname
        conn1 = EnhancedMockPyRPLConnection(hostname)
        conn2 = EnhancedMockPyRPLConnection(hostname)

        assert conn1 is conn2, "Should share same connection instance"

        # Test that simulation state is shared
        conn1.set_simulation_scenario(ScenarioType.STABLE_SYSTEM)
        conn1.set_pid_setpoint(PIDChannel.PID0, 1.0)

        # Step simulation and check both connections see same state
        conn1.simulation.step_simulation()

        pv1 = conn1.read_voltage(InputChannel.IN1)
        pv2 = conn2.read_voltage(InputChannel.IN1)

        # Allow for small differences due to measurement noise
        assert abs(pv1 - pv2) < 0.01, "Both connections should see approximately same process variable"

    def test_realistic_control_loop(self):
        """Test realistic control loop simulation."""
        conn = EnhancedMockPyRPLConnection("demo.pyrpl.local")

        # Configure for stable system
        conn.set_simulation_scenario(ScenarioType.STABLE_SYSTEM)
        conn.reset_simulation()

        # Set target
        setpoint = 0.8
        conn.set_pid_setpoint(PIDChannel.PID0, setpoint)

        # Simulate control loop
        process_variables = []
        for i in range(20):
            # Read process variable
            pv = conn.read_voltage(InputChannel.IN1)
            process_variables.append(pv)

            # Simple P controller for testing
            error = setpoint - pv
            controller_output = 0.5 * error  # P gain = 0.5

            # Apply controller output
            conn.set_pid_controller_output(PIDChannel.PID0, controller_output)

            # Small delay
            time.sleep(0.01)

        # Verify system shows some movement (may not converge in just 20 steps with noise)
        # Check that there's some variation in process variables
        pv_std = np.std(process_variables)
        assert pv_std > 0.001, "Process variable should show some variation during control"

        # Check that final values are within reasonable range
        assert -2.0 < process_variables[-1] < 2.0, "Final process variable should be within reasonable range"

    def test_performance_monitoring(self):
        """Test performance monitoring during simulation."""
        conn = EnhancedMockPyRPLConnection("demo.pyrpl.local")

        # Reset and configure
        conn.reset_simulation()
        conn.set_simulation_scenario(ScenarioType.STABLE_SYSTEM)
        conn.set_pid_setpoint(PIDChannel.PID0, 1.0)

        # Run simulation steps
        for _ in range(15):
            conn.set_pid_controller_output(PIDChannel.PID0, 0.5)
            time.sleep(0.01)

        # Get performance metrics
        metrics = conn.get_performance_metrics()

        assert 'steady_state_error' in metrics
        assert 'current_pv' in metrics
        assert metrics['steady_state_error'] >= 0  # Should have some error
        assert isinstance(metrics['current_pv'], float)

    def test_scenario_comparison(self):
        """Test comparing different scenarios."""
        conn = EnhancedMockPyRPLConnection("demo.pyrpl.local")

        scenarios = [ScenarioType.STABLE_SYSTEM, ScenarioType.OSCILLATORY_SYSTEM]
        scenario_responses = {}

        for scenario in scenarios:
            conn.set_simulation_scenario(scenario)
            conn.reset_simulation()
            conn.set_pid_setpoint(PIDChannel.PID0, 1.0)

            # Run brief simulation
            responses = []
            for _ in range(10):
                pv = conn.read_voltage(InputChannel.IN1)
                responses.append(pv)
                conn.set_pid_controller_output(PIDChannel.PID0, 0.5)
                time.sleep(0.005)

            scenario_responses[scenario] = responses

        # Different scenarios should produce different responses
        stable_response = scenario_responses[ScenarioType.STABLE_SYSTEM]
        oscillatory_response = scenario_responses[ScenarioType.OSCILLATORY_SYSTEM]

        # Calculate response differences
        diff = np.mean(np.abs(np.array(stable_response) - np.array(oscillatory_response)))
        assert diff > 0.01, "Different scenarios should produce measurably different responses"


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])