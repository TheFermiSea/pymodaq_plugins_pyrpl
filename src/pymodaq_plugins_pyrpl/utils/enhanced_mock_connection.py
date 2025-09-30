# -*- coding: utf-8 -*-
"""
Enhanced Mock PyRPL Connection for Realistic Control System Demonstration

This module provides an enhanced MockPyRPLConnection that integrates with the
simulation engine to create realistic PID control demonstrations. It replaces
the basic mock implementations with sophisticated plant dynamics and shared
state management.

Classes:
    EnhancedMockPyRPLConnection: Advanced mock connection with simulation engine
    MockPIDController: Simulated PID controller for demonstration
    MockChannelState: State tracking for individual hardware channels

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import time
import logging
from typing import Dict, Optional, Tuple, List, Union
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# Import PyRPL enums from wrapper
try:
    from .pyrpl_wrapper import (
        ConnectionState, PIDChannel, InputChannel, OutputChannel,
        ASGChannel, ASGWaveform, IQChannel, IQOutputDirect,
        ScopeTriggerSource
    )
except ImportError:
    # Fallback definitions if wrapper not available
    from enum import Enum

    class ConnectionState(Enum):
        CONNECTED = "connected"
        DISCONNECTED = "disconnected"

    class PIDChannel(Enum):
        PID0 = "pid0"
        PID1 = "pid1"
        PID2 = "pid2"

    class InputChannel(Enum):
        IN1 = "in1"
        IN2 = "in2"

    class OutputChannel(Enum):
        OUT1 = "out1"
        OUT2 = "out2"
    
    class ASGChannel(Enum):
        ASG0 = "asg0"
        ASG1 = "asg1"
    
    class ASGWaveform(Enum):
        SIN = "sin"
        COS = "cos"
        RAMP = "ramp"
        SQUARE = "square"
        NOISE = "noise"
        DC = "dc"
    
    class IQChannel(Enum):
        IQ0 = "iq0"
        IQ1 = "iq1"
        IQ2 = "iq2"
    
    class IQOutputDirect(Enum):
        OFF = "off"
        OUT1 = "out1"
        OUT2 = "out2"
    
    class ScopeTriggerSource(Enum):
        IMMEDIATELY = "immediately"
        CH1_POSITIVE_EDGE = "ch1_positive_edge"
        CH1_NEGATIVE_EDGE = "ch1_negative_edge"

# Import simulation engine
from .mock_simulation import get_simulation_engine, ScenarioType

logger = logging.getLogger(__name__)


@dataclass
class MockPIDState:
    """State tracking for individual PID controllers."""
    setpoint: float = 0.0
    input_channel: InputChannel = InputChannel.IN1
    output_channel: OutputChannel = OutputChannel.OUT1
    p_gain: float = 1.0
    i_gain: float = 0.1
    d_gain: float = 0.0
    enabled: bool = False
    last_update: float = field(default_factory=time.time)


@dataclass
class MockASGState:
    """State tracking for ASG (Arbitrary Signal Generator) modules."""
    frequency: float = 1000.0
    amplitude: float = 0.1
    offset: float = 0.0
    waveform: str = "sin"
    enabled: bool = False
    trigger_source: str = "immediately"


@dataclass
class MockIQState:
    """State tracking for IQ (Lock-in Amplifier) modules."""
    frequency: float = 1000.0
    bandwidth: float = 100.0
    phase: float = 0.0
    gain: float = 1.0
    input_channel: InputChannel = InputChannel.IN1
    enabled: bool = False


@dataclass
class MockScopeState:
    """State tracking for oscilloscope module."""
    input_channel: InputChannel = InputChannel.IN1
    decimation: int = 64
    trigger_source: str = "immediately"
    trigger_delay: int = 0
    trigger_level: float = 0.0
    average: int = 1
    last_acquisition: float = field(default_factory=time.time)


class EnhancedMockPyRPLConnection:
    """
    Enhanced mock PyRPL connection with realistic control system simulation.

    This class provides a comprehensive simulation environment that includes:
    - Realistic plant dynamics via simulation engine
    - Individual channel state tracking
    - Time-synchronized updates across all mock plugins
    - Educational scenario support
    - Performance metrics calculation
    """

    # Class-level registry for shared instances (hostname-based)
    _instances: Dict[str, 'EnhancedMockPyRPLConnection'] = {}
    _simulation_engine = None

    def __new__(cls, hostname: str):
        """
        Ensure shared instances per hostname for coordinated simulation.

        This implements a registry pattern where all plugins connecting to
        the same mock hostname share the same connection instance.
        """
        if hostname not in cls._instances:
            instance = super(EnhancedMockPyRPLConnection, cls).__new__(cls)
            cls._instances[hostname] = instance
            logger.info(f"Created new EnhancedMockPyRPLConnection for {hostname}")
        return cls._instances[hostname]

    def __init__(self, hostname: str):
        """Initialize enhanced mock connection."""
        # Prevent re-initialization of shared instances
        if hasattr(self, '_initialized'):
            return

        self.hostname = hostname
        self.is_connected = True
        self.state = ConnectionState.CONNECTED
        self.connection_time = time.time()

        # Get shared simulation engine
        if EnhancedMockPyRPLConnection._simulation_engine is None:
            EnhancedMockPyRPLConnection._simulation_engine = get_simulation_engine()
        self.simulation = EnhancedMockPyRPLConnection._simulation_engine

        # Initialize mock hardware state
        self.pid_states = {
            PIDChannel.PID0: MockPIDState(),
            PIDChannel.PID1: MockPIDState(input_channel=InputChannel.IN2),
            PIDChannel.PID2: MockPIDState(output_channel=OutputChannel.OUT2)
        }

        self.asg_states = {
            ASGChannel.ASG0: MockASGState(),
            ASGChannel.ASG1: MockASGState(frequency=2000.0)
        }

        self.iq_states = {
            IQChannel.IQ0: MockIQState(),
            IQChannel.IQ1: MockIQState(input_channel=InputChannel.IN2),
            IQChannel.IQ2: MockIQState(frequency=2000.0)
        }

        self.scope_state = MockScopeState()

        # Voltage monitoring simulation
        self.base_voltages = {
            InputChannel.IN1: 0.5,  # Default base voltage for IN1
            InputChannel.IN2: 0.3   # Default base voltage for IN2
        }

        self._initialized = True
        logger.info(f"EnhancedMockPyRPLConnection initialized for {hostname}")

    def _normalize_input_channel(self, channel) -> InputChannel:
        """Return a canonical InputChannel instance from various representations."""
        # Direct enum instance
        if isinstance(channel, InputChannel):
            return channel

        # String value ("in1")
        if isinstance(channel, str):
            try:
                return InputChannel(channel)
            except ValueError:
                return InputChannel[channel.upper()]

        # Enum-like object with .value attribute (possibly from alternate definition)
        value = getattr(channel, 'value', None)
        if isinstance(value, str):
            try:
                return InputChannel(value)
            except ValueError:
                try:
                    return InputChannel[value.upper()]
                except (KeyError, ValueError):
                    pass

        # Enum-like object with .name attribute
        name = getattr(channel, 'name', None)
        if isinstance(name, str):
            try:
                return InputChannel[name]
            except KeyError:
                try:
                    return InputChannel[name.upper()]
                except (KeyError, ValueError):
                    pass

        raise KeyError(channel)

    def read_voltage(self, channel: InputChannel) -> float:
        """
        Read simulated voltage with realistic plant dynamics.

        For IN1: Returns simulation engine process variable (plant output)
        For IN2: Returns base voltage with noise (independent signal)
        """
        channel = self._normalize_input_channel(channel)

        if channel == InputChannel.IN1:
            # IN1 shows the plant output (process variable)
            pv = self.simulation.get_process_variable()
            # Add small measurement noise
            noise = np.random.normal(0, 0.002)  # 2mV measurement noise
            return pv + noise
        else:
            # IN2 shows independent signal with realistic variations
            base = self.base_voltages.get(channel)
            if base is None:
                # Fallback for dynamically created channels, default to IN2 base
                base = self.base_voltages.setdefault(channel, 0.3)
            # Slowly varying baseline + noise
            drift = 0.05 * np.sin(time.time() * 0.1)  # Slow drift
            noise = np.random.normal(0, 0.01)  # 10mV noise
            return base + drift + noise

    def set_pid_setpoint(self, channel: PIDChannel, setpoint: float) -> bool:
        """Set PID setpoint and update simulation."""
        if channel not in self.pid_states:
            return False

        # Update local state
        self.pid_states[channel].setpoint = setpoint
        self.pid_states[channel].last_update = time.time()

        # Update simulation engine setpoint
        # For demonstration, assume PID0 is the main controller
        if channel == PIDChannel.PID0:
            self.simulation.set_setpoint(setpoint)
            # Step simulation to update plant
            self.simulation.step_simulation()

        logger.debug(f"Mock PID {channel.value} setpoint set to {setpoint:.3f}V")
        return True

    def get_pid_setpoint(self, channel: PIDChannel) -> Optional[float]:
        """Get current PID setpoint."""
        if channel not in self.pid_states:
            return None
        return self.pid_states[channel].setpoint

    def set_pid_controller_output(self, channel: PIDChannel, output: float) -> bool:
        """
        Set PID controller output (from PyMoDAQ PID model).

        This is called when PyMoDAQ's PID model calculates a new output
        based on the error between setpoint and process variable.
        """
        if channel not in self.pid_states:
            return False

        # Update simulation engine with new controller output
        # For demonstration, assume PID0 is the main controller
        if channel == PIDChannel.PID0:
            self.simulation.set_controller_output(output)
            # Step simulation to update plant response
            self.simulation.step_simulation()

        logger.debug(f"Mock PID {channel.value} controller output set to {output:.3f}V")
        return True

    def configure_pid(self, channel: PIDChannel, p_gain: float, i_gain: float,
                     d_gain: float, input_channel: InputChannel,
                     output_channel: OutputChannel) -> bool:
        """Configure PID controller parameters."""
        if channel not in self.pid_states:
            return False

        state = self.pid_states[channel]
        state.p_gain = p_gain
        state.i_gain = i_gain
        state.d_gain = d_gain
        state.input_channel = input_channel
        state.output_channel = output_channel

        logger.debug(f"Mock PID {channel.value} configured: P={p_gain}, I={i_gain}, D={d_gain}")
        return True

    def get_pid_configuration(self, channel: PIDChannel) -> Optional[Dict]:
        """Get PID configuration parameters."""
        if channel not in self.pid_states:
            return None

        state = self.pid_states[channel]
        return {
            'p_gain': state.p_gain,
            'i_gain': state.i_gain,
            'd_gain': state.d_gain,
            'input_channel': state.input_channel.value,
            'output_channel': state.output_channel.value,
            'setpoint': state.setpoint,
            'enabled': state.enabled
        }

    def enable_pid_output(self, channel: PIDChannel, enabled: bool) -> bool:
        """Enable/disable PID output."""
        if channel not in self.pid_states:
            return False

        self.pid_states[channel].enabled = enabled

        # If disabling main controller, set output to zero
        if not enabled and channel == PIDChannel.PID0:
            self.simulation.set_controller_output(0.0)
            self.simulation.step_simulation()

        logger.debug(f"Mock PID {channel.value} output {'enabled' if enabled else 'disabled'}")
        return True

    def configure_asg(self, channel: ASGChannel, frequency: float, amplitude: float,
                     offset: float, waveform: str) -> bool:
        """Configure ASG parameters."""
        if channel not in self.asg_states:
            return False

        state = self.asg_states[channel]
        state.frequency = frequency
        state.amplitude = amplitude
        state.offset = offset
        state.waveform = waveform

        logger.debug(f"Mock ASG {channel.value} configured: {frequency}Hz, {amplitude}V, {waveform}")
        return True

    def get_asg_frequency(self, channel: ASGChannel) -> Optional[float]:
        """Get ASG frequency."""
        if channel not in self.asg_states:
            return None
        return self.asg_states[channel].frequency

    def set_asg_frequency(self, channel: ASGChannel, frequency: float) -> bool:
        """Set ASG frequency."""
        if channel not in self.asg_states:
            return False
        self.asg_states[channel].frequency = frequency
        return True

    def configure_iq(self, channel: IQChannel, config) -> bool:
        """Configure IQ module (simplified for mock)."""
        if channel not in self.iq_states:
            return False

        state = self.iq_states[channel]
        if hasattr(config, 'frequency'):
            state.frequency = config.frequency
        if hasattr(config, 'bandwidth'):
            state.bandwidth = config.bandwidth
        if hasattr(config, 'phase'):
            state.phase = config.phase

        logger.debug(f"Mock IQ {channel.value} configured")
        return True

    def get_iq_measurement(self, channel: IQChannel) -> Optional[Tuple[float, float]]:
        """Get mock I/Q measurement with realistic lock-in behavior."""
        if channel not in self.iq_states:
            return None

        state = self.iq_states[channel]

        # Simulate lock-in measurement with signal at reference frequency
        signal_amplitude = 0.1  # Assume 100mV signal
        phase_noise = np.random.normal(0, 0.1)  # Phase noise
        amplitude_noise = np.random.normal(1.0, 0.05)  # 5% amplitude noise

        i_component = signal_amplitude * amplitude_noise * np.cos(np.radians(state.phase + phase_noise))
        q_component = signal_amplitude * amplitude_noise * np.sin(np.radians(state.phase + phase_noise))

        return (i_component, q_component)

    def configure_scope(self, channel: InputChannel, decimation: int = 64,
                       trigger_source: str = "immediately") -> bool:
        """Configure scope parameters."""
        self.scope_state.input_channel = channel
        self.scope_state.decimation = decimation
        self.scope_state.trigger_source = trigger_source
        logger.debug(f"Mock scope configured: channel={channel.value}, decimation={decimation}")
        return True

    def acquire_scope_data(self, channel: InputChannel, decimation: int = 64,
                          samples: int = 16384) -> np.ndarray:
        """
        Acquire simulated scope data showing plant dynamics.

        This generates a time series showing the recent history of the
        selected input channel, which can display control system response.
        """
        # Get simulation history
        history = self.simulation.get_history(samples=samples)

        if channel == InputChannel.IN1:
            # IN1 shows plant output (process variable)
            if len(history['pv']) > 0:
                data = history['pv']
            else:
                # No history yet, generate flat line at current PV
                pv = self.simulation.get_process_variable()
                data = np.full(samples, pv)
        else:
            # IN2 shows controller output or setpoint
            if len(history['input']) > 0:
                data = history['input']
            else:
                # No history yet, generate zero line
                data = np.zeros(samples)

        # Add measurement noise
        noise = np.random.normal(0, 0.005, len(data))  # 5mV scope noise
        return data + noise

    def set_simulation_scenario(self, scenario: Union[str, ScenarioType]) -> bool:
        """Change the simulation scenario for educational demonstrations."""
        try:
            if isinstance(scenario, str):
                scenario_type = ScenarioType(scenario)
            else:
                scenario_type = scenario

            self.simulation.set_scenario(scenario_type, reset_plant=True)
            logger.info(f"Simulation scenario changed to {scenario_type.value}")
            return True

        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid scenario: {e}")
            return False

    def get_simulation_info(self) -> Dict:
        """Get current simulation scenario and performance information."""
        return self.simulation.get_scenario_info()

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get control performance metrics."""
        return self.simulation.get_performance_metrics()

    def reset_simulation(self):
        """Reset simulation to initial state."""
        self.simulation.reset_simulation()

        # Reset all mock hardware states
        for state in self.pid_states.values():
            state.setpoint = 0.0
            state.enabled = False

        logger.info("Simulation and mock hardware reset")

    def get_connection_info(self) -> Dict:
        """Get information about the mock connection."""
        return {
            'hostname': self.hostname,
            'state': self.state.value,
            'connected_since': self.connection_time,
            'is_mock': True,
            'simulation_scenario': self.simulation.get_current_scenario().value,
            'active_pids': [ch.value for ch, state in self.pid_states.items() if state.enabled]
        }

    def disconnect(self, status_callback=None):
        """Disconnect mock connection."""
        self.is_connected = False
        self.state = ConnectionState.DISCONNECTED
        logger.info(f"Mock connection to {self.hostname} disconnected")

    @classmethod
    def get_shared_instance(cls, hostname: str) -> 'EnhancedMockPyRPLConnection':
        """Get shared instance for hostname (for external access)."""
        return cls._instances.get(hostname)

    @classmethod
    def list_active_connections(cls) -> List[str]:
        """List all active mock connections."""
        return [hostname for hostname, conn in cls._instances.items() if conn.is_connected]

    @classmethod
    def reset_all_simulations(cls):
        """Reset all active mock simulations."""
        for connection in cls._instances.values():
            if connection.is_connected:
                connection.reset_simulation()


# Convenience functions for backward compatibility and easy access
def create_enhanced_mock_connection(hostname: str) -> EnhancedMockPyRPLConnection:
    """Create or get enhanced mock connection for hostname."""
    return EnhancedMockPyRPLConnection(hostname)


def get_mock_connection(hostname: str) -> Optional[EnhancedMockPyRPLConnection]:
    """Get existing mock connection for hostname."""
    return EnhancedMockPyRPLConnection.get_shared_instance(hostname)


def list_mock_connections() -> List[str]:
    """List all active mock connections."""
    return EnhancedMockPyRPLConnection.list_active_connections()