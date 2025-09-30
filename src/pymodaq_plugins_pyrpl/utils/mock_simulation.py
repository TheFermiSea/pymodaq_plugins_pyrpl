# -*- coding: utf-8 -*-
"""
Mock Simulation Engine for PyMoDAQ PyRPL Demonstration

This module provides realistic control system simulation for educational and
demonstration purposes. It implements first-order plus dead-time (FOPDT) plant
dynamics that respond to PID controller outputs, creating realistic feedback loops.

Classes:
    SimulatedPlant: FOPDT plant model for PID control simulation
    PlantScenario: Predefined plant configurations for different demonstrations
    MockSimulationEngine: Centralized simulation management

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import logging

import numpy as np

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Predefined demonstration scenarios for educational purposes."""
    STABLE_SYSTEM = "stable_system"
    OSCILLATORY_SYSTEM = "oscillatory_system"
    SLUGGISH_SYSTEM = "sluggish_system"
    NOISY_ENVIRONMENT = "noisy_environment"
    INTEGRATING_PROCESS = "integrating_process"
    CUSTOM = "custom"


@dataclass
class PlantParameters:
    """Parameters defining plant behavior for FOPDT model."""
    gain: float = 1.0                    # Process gain (K)
    time_constant: float = 5.0           # Time constant τ (seconds)
    dead_time: float = 0.0               # Dead time θ (seconds)
    noise_amplitude: float = 0.01        # Process noise standard deviation
    disturbance_amplitude: float = 0.0   # External disturbance amplitude
    integrating: bool = False            # True for integrating processes

    def __post_init__(self):
        """Validate parameters."""
        if self.gain <= 0:
            raise ValueError("Process gain must be positive")
        if self.time_constant <= 0:
            raise ValueError("Time constant must be positive")
        if self.dead_time < 0:
            raise ValueError("Dead time must be non-negative")


class SimulatedPlant:
    """
    First-order plus dead-time (FOPDT) plant simulation.

    Implements the discrete-time model:
    For normal processes: PV(k+1) = PV(k) + (K*u(k) - PV(k)) * dt/τ + noise
    For integrating processes: PV(k+1) = PV(k) + K*u(k)*dt + noise

    Where:
    - PV = Process Variable (output)
    - u = Controller output (input)
    - K = Process gain
    - τ = Time constant
    - dt = Time step
    """

    def __init__(self, parameters: PlantParameters):
        """
        Initialize the simulated plant.

        Parameters
        ----------
        parameters : PlantParameters
            Plant configuration parameters
        """
        self.params = parameters
        self.pv = 0.0  # Process variable (current output)
        self.last_controller_output = 0.0
        self.last_update_time = time.time()

        # Dead time buffer (stores delayed inputs)
        if self.params.dead_time > 0:
            max_delay_samples = int(self.params.dead_time / 0.1) + 10  # Assume max 100ms timesteps
            self.delay_buffer = deque(maxlen=max_delay_samples)
            # Initialize buffer with zeros
            for _ in range(max_delay_samples):
                self.delay_buffer.append(0.0)
        else:
            self.delay_buffer = None

        # Time series data for visualization
        self.max_history = 1000
        self.time_history = deque(maxlen=self.max_history)
        self.pv_history = deque(maxlen=self.max_history)
        self.input_history = deque(maxlen=self.max_history)
        self.setpoint_history = deque(maxlen=self.max_history)

        # Disturbance generation
        self.disturbance_frequency = 0.1  # Hz
        self.disturbance_phase = 0.0

        logger.info(f"SimulatedPlant initialized: K={self.params.gain}, "
                   f"τ={self.params.time_constant}s, θ={self.params.dead_time}s")

    def step(self, controller_output: float, setpoint: float = 0.0, dt: Optional[float] = None) -> float:
        """
        Update plant state for one time step.

        Parameters
        ----------
        controller_output : float
            Control signal from PID controller
        setpoint : float, optional
            Current setpoint for history tracking
        dt : float, optional
            Time step in seconds. If None, calculated from real time.

        Returns
        -------
        float
            Updated process variable value
        """
        current_time = time.time()

        if dt is None:
            dt = current_time - self.last_update_time
            # Limit dt to reasonable values to prevent simulation instability
            dt = max(0.001, min(dt, 1.0))

        # Handle dead time if present
        if self.delay_buffer is not None:
            self.delay_buffer.append(controller_output)
            # Calculate delay in samples
            delay_samples = int(self.params.dead_time / dt)
            if delay_samples < len(self.delay_buffer):
                effective_input = self.delay_buffer[-delay_samples-1]
            else:
                effective_input = 0.0  # Still in dead time
        else:
            effective_input = controller_output

        # Generate external disturbance
        disturbance = 0.0
        if self.params.disturbance_amplitude > 0:
            self.disturbance_phase += 2 * np.pi * self.disturbance_frequency * dt
            disturbance = self.params.disturbance_amplitude * np.sin(self.disturbance_phase)

        # Update process variable based on plant type
        if self.params.integrating:
            # Integrating process: rate of change proportional to input
            self.pv += (self.params.gain * effective_input + disturbance) * dt
        else:
            # First-order process: exponential approach to steady state
            steady_state = self.params.gain * effective_input + disturbance
            self.pv += (steady_state - self.pv) * (dt / self.params.time_constant)

        # Add process noise
        if self.params.noise_amplitude > 0:
            noise = np.random.normal(0, self.params.noise_amplitude)
            self.pv += noise

        # Update history
        self.time_history.append(current_time)
        self.pv_history.append(self.pv)
        self.input_history.append(controller_output)
        self.setpoint_history.append(setpoint)

        self.last_controller_output = controller_output
        self.last_update_time = current_time

        return self.pv

    def reset(self, initial_pv: float = 0.0):
        """
        Reset plant to initial conditions.

        Parameters
        ----------
        initial_pv : float
            Initial process variable value
        """
        self.pv = initial_pv
        self.last_controller_output = 0.0
        self.last_update_time = time.time()
        self.disturbance_phase = 0.0

        # Clear delay buffer
        if self.delay_buffer is not None:
            for i in range(len(self.delay_buffer)):
                self.delay_buffer[i] = 0.0

        # Clear history
        self.time_history.clear()
        self.pv_history.clear()
        self.input_history.clear()
        self.setpoint_history.clear()

        logger.debug(f"Plant reset to PV={initial_pv}")

    def get_history(self, samples: Optional[int] = None) -> Dict[str, np.ndarray]:
        """
        Get historical data for plotting.

        Parameters
        ----------
        samples : int, optional
            Number of recent samples to return. If None, return all.

        Returns
        -------
        dict
            Dictionary with 'time', 'pv', 'input', 'setpoint' arrays
        """
        if not self.time_history:
            return {
                'time': np.array([]),
                'pv': np.array([]),
                'input': np.array([]),
                'setpoint': np.array([])
            }

        if samples is None:
            samples = len(self.time_history)
        else:
            samples = min(samples, len(self.time_history))

        # Convert to relative time (seconds from start)
        time_array = np.array(list(self.time_history)[-samples:])
        if len(time_array) > 0:
            time_array = time_array - time_array[0]

        return {
            'time': time_array,
            'pv': np.array(list(self.pv_history)[-samples:]),
            'input': np.array(list(self.input_history)[-samples:]),
            'setpoint': np.array(list(self.setpoint_history)[-samples:])
        }

    def get_settling_metrics(self, setpoint: float, tolerance: float = 0.02) -> Dict[str, float]:
        """
        Calculate control performance metrics.

        Parameters
        ----------
        setpoint : float
            Target setpoint value
        tolerance : float
            Settling tolerance as fraction of setpoint

        Returns
        -------
        dict
            Performance metrics including settling time, overshoot, etc.
        """
        if len(self.pv_history) < 10:
            return {}

        pv_array = np.array(list(self.pv_history))
        time_array = np.array(list(self.time_history))

        # Calculate settling time
        settling_band = abs(setpoint * tolerance)
        settled_indices = np.where(np.abs(pv_array - setpoint) <= settling_band)[0]

        metrics = {
            'steady_state_error': abs(pv_array[-1] - setpoint) if len(pv_array) > 0 else float('inf'),
            'current_pv': pv_array[-1] if len(pv_array) > 0 else 0.0,
        }

        if len(settled_indices) > 0:
            # Find the last time it left the settling band
            last_unsettled = 0
            for i in range(len(pv_array) - 1, -1, -1):
                if abs(pv_array[i] - setpoint) > settling_band:
                    last_unsettled = i
                    break

            if last_unsettled < len(time_array) - 1:
                settling_time = time_array[-1] - time_array[last_unsettled]
                metrics['settling_time'] = settling_time

        # Calculate overshoot
        if setpoint != 0:
            max_pv = np.max(pv_array)
            overshoot = max(0, (max_pv - setpoint) / abs(setpoint) * 100)
            metrics['overshoot_percent'] = overshoot

        return metrics


class PlantScenario:
    """Predefined plant scenarios for educational demonstrations."""

    SCENARIOS = {
        ScenarioType.STABLE_SYSTEM: PlantParameters(
            gain=0.8,
            time_constant=3.0,
            dead_time=0.1,
            noise_amplitude=0.005,
            disturbance_amplitude=0.02
        ),
        ScenarioType.OSCILLATORY_SYSTEM: PlantParameters(
            gain=2.5,
            time_constant=1.0,
            dead_time=0.2,
            noise_amplitude=0.01,
            disturbance_amplitude=0.05
        ),
        ScenarioType.SLUGGISH_SYSTEM: PlantParameters(
            gain=1.0,
            time_constant=15.0,
            dead_time=0.5,
            noise_amplitude=0.008,
            disturbance_amplitude=0.03
        ),
        ScenarioType.NOISY_ENVIRONMENT: PlantParameters(
            gain=1.2,
            time_constant=4.0,
            dead_time=0.1,
            noise_amplitude=0.05,  # High noise
            disturbance_amplitude=0.1
        ),
        ScenarioType.INTEGRATING_PROCESS: PlantParameters(
            gain=0.1,
            time_constant=1.0,  # Not used for integrating process
            dead_time=0.0,
            noise_amplitude=0.01,
            disturbance_amplitude=0.02,
            integrating=True
        )
    }

    @classmethod
    def get_scenario(cls, scenario_type: ScenarioType) -> PlantParameters:
        """Get parameters for a predefined scenario."""
        return cls.SCENARIOS.get(scenario_type, cls.SCENARIOS[ScenarioType.STABLE_SYSTEM])

    @classmethod
    def get_scenario_description(cls, scenario_type: ScenarioType) -> str:
        """Get human-readable description of scenario."""
        descriptions = {
            ScenarioType.STABLE_SYSTEM: "Easy to tune, stable response, good for learning PID basics",
            ScenarioType.OSCILLATORY_SYSTEM: "High gain, prone to oscillation, challenging tuning",
            ScenarioType.SLUGGISH_SYSTEM: "Slow response, demonstrates integral windup issues",
            ScenarioType.NOISY_ENVIRONMENT: "High noise, shows filtering and derivative kick effects",
            ScenarioType.INTEGRATING_PROCESS: "Level/flow control, requires special tuning approach",
            ScenarioType.CUSTOM: "User-defined parameters"
        }
        return descriptions.get(scenario_type, "Unknown scenario")

    @classmethod
    def get_tuning_suggestions(cls, scenario_type: ScenarioType) -> Dict[str, float]:
        """Get suggested PID tuning parameters for each scenario."""
        suggestions = {
            ScenarioType.STABLE_SYSTEM: {"P": 1.0, "I": 0.2, "D": 0.1},
            ScenarioType.OSCILLATORY_SYSTEM: {"P": 0.3, "I": 0.05, "D": 0.02},
            ScenarioType.SLUGGISH_SYSTEM: {"P": 0.5, "I": 0.01, "D": 0.0},
            ScenarioType.NOISY_ENVIRONMENT: {"P": 0.8, "I": 0.1, "D": 0.0},  # Avoid derivative in noise
            ScenarioType.INTEGRATING_PROCESS: {"P": 0.2, "I": 0.05, "D": 0.0},
            ScenarioType.CUSTOM: {"P": 1.0, "I": 0.1, "D": 0.05}
        }
        return suggestions.get(scenario_type, {"P": 1.0, "I": 0.1, "D": 0.05})


class MockSimulationEngine:
    """
    Centralized simulation engine for coordinating mock plugins.

    This singleton class manages the shared simulation state between
    multiple PyMoDAQ plugins, ensuring they all interact with the same
    simulated plant and maintain synchronized timing.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MockSimulationEngine, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize simulation engine (called only once)."""
        if self._initialized:
            return

        self.plant = SimulatedPlant(PlantScenario.get_scenario(ScenarioType.STABLE_SYSTEM))
        self.current_scenario = ScenarioType.STABLE_SYSTEM
        self.controller_output = 0.0
        self.setpoint = 0.0
        self.is_running = False

        # Thread safety
        self.state_lock = threading.Lock()

        self._initialized = True
        logger.info("MockSimulationEngine initialized with stable system scenario")

    def set_scenario(self, scenario_type: ScenarioType, reset_plant: bool = True):
        """
        Change simulation scenario.

        Parameters
        ----------
        scenario_type : ScenarioType
            New scenario to load
        reset_plant : bool
            Whether to reset plant state to initial conditions
        """
        with self.state_lock:
            self.current_scenario = scenario_type
            parameters = PlantScenario.get_scenario(scenario_type)
            self.plant = SimulatedPlant(parameters)

            if reset_plant:
                self.plant.reset()
                self.controller_output = 0.0
                self.setpoint = 0.0

            logger.info(f"Simulation scenario changed to {scenario_type.value}")

    def set_controller_output(self, output: float):
        """Set the controller output value."""
        with self.state_lock:
            self.controller_output = output

    def set_setpoint(self, setpoint: float):
        """Set the current setpoint for tracking."""
        with self.state_lock:
            self.setpoint = setpoint

    def get_process_variable(self) -> float:
        """Get current process variable value."""
        with self.state_lock:
            return self.plant.pv

    def step_simulation(self, dt: Optional[float] = None) -> float:
        """
        Advance simulation by one time step.

        Parameters
        ----------
        dt : float, optional
            Time step in seconds

        Returns
        -------
        float
            Updated process variable value
        """
        with self.state_lock:
            return self.plant.step(self.controller_output, self.setpoint, dt)

    def get_history(self, samples: Optional[int] = None) -> Dict[str, np.ndarray]:
        """Get historical simulation data."""
        with self.state_lock:
            return self.plant.get_history(samples)

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current control performance metrics."""
        with self.state_lock:
            return self.plant.get_settling_metrics(self.setpoint)

    def reset_simulation(self, initial_pv: float = 0.0):
        """Reset simulation to initial state."""
        with self.state_lock:
            self.plant.reset(initial_pv)
            self.controller_output = 0.0
            self.setpoint = 0.0
            logger.debug("Simulation reset")

    def get_current_scenario(self) -> ScenarioType:
        """Get currently active scenario."""
        return self.current_scenario

    def get_scenario_info(self) -> Dict[str, Union[str, Dict[str, float]]]:
        """Get information about current scenario."""
        return {
            'type': self.current_scenario.value,
            'description': PlantScenario.get_scenario_description(self.current_scenario),
            'tuning_suggestions': PlantScenario.get_tuning_suggestions(self.current_scenario),
            'parameters': {
                'gain': self.plant.params.gain,
                'time_constant': self.plant.params.time_constant,
                'dead_time': self.plant.params.dead_time,
                'noise_amplitude': self.plant.params.noise_amplitude
            }
        }


# Convenience function for getting the singleton instance
def get_simulation_engine() -> MockSimulationEngine:
    """Get the global simulation engine instance."""
    return MockSimulationEngine()