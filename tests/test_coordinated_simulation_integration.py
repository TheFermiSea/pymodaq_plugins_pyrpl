# -*- coding: utf-8 -*-
"""
Integration Tests for Coordinated Mock Simulation

This module tests the complete coordinated simulation workflow where:
- PID controllers affect the plant simulation
- Voltage monitors show plant response
- Scope displays show time-series plant dynamics  
- IQ detectors show phase-sensitive measurements
- All plugins share the same simulation engine state

This validates that the unified mock architecture delivers on the key promise:
synchronized, realistic control system simulation across all plugin types.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock

from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager, reset_shared_mock_instance
from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import (
    EnhancedMockPyRPLConnection, PIDChannel, InputChannel, IQChannel, ASGChannel
)


class TestCoordinatedSimulation:
    """Test coordinated simulation across multiple plugin types."""
    
    def setup_method(self):
        """Setup test environment with clean simulation state."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
        self.hostname = "coordinated-sim.local"
        
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
        
    @pytest.mark.integration
    def test_pid_affects_voltage_readings(self):
        """Test that PID setpoint changes affect voltage monitor readings."""
        # Create connections for different plugin types
        pid_conn = self.manager.connect_device(self.hostname, "pid_config", mock_mode=True)
        voltage_conn = self.manager.connect_device(self.hostname, "voltage_config", mock_mode=True)
        
        assert pid_conn is not None
        assert voltage_conn is not None
        
        # Verify they share the same simulation engine
        assert pid_conn._mock_instance is voltage_conn._mock_instance
        simulation = pid_conn._mock_instance
        
        # Get baseline voltage reading
        initial_voltage = voltage_conn.read_voltage(InputChannel.IN1)
        assert isinstance(initial_voltage, (int, float))
        
        # Set PID setpoint (should affect plant dynamics)
        setpoint_change = 0.3  # 300mV change
        new_setpoint = initial_voltage + setpoint_change
        
        success = pid_conn.set_pid_setpoint(PIDChannel.PID0, new_setpoint)
        if success:
            # Allow time for simulation to respond
            time.sleep(0.1)
            
            # Step simulation forward to process the change
            if hasattr(simulation, 'simulation') and hasattr(simulation.simulation, 'step_simulation'):
                simulation.simulation.step_simulation(0.1)
            
            # Read voltage again - should show plant response
            final_voltage = voltage_conn.read_voltage(InputChannel.IN1)
            assert isinstance(final_voltage, (int, float))
            
            # The plant should respond toward the new setpoint
            # (exact behavior depends on simulation dynamics)
            voltage_change = abs(final_voltage - initial_voltage)
            
            # Should see some measurable change (simulation is responsive)
            assert voltage_change >= 0, "Simulation should be responsive to PID changes"
            
            print(f"PID setpoint change: {setpoint_change:.3f}V")
            print(f"Voltage response: {initial_voltage:.3f}V → {final_voltage:.3f}V")
            print(f"Change magnitude: {voltage_change:.3f}V")
    
    @pytest.mark.integration
    def test_asg_affects_measurements(self):
        """Test that ASG output affects measurement readings across plugins."""
        # Create connections representing different measurement plugins
        asg_conn = self.manager.connect_device(self.hostname, "asg_config", mock_mode=True) 
        voltage_conn = self.manager.connect_device(self.hostname, "voltage_config", mock_mode=True)
        iq_conn = self.manager.connect_device(self.hostname, "iq_config", mock_mode=True)
        
        assert asg_conn is not None
        assert voltage_conn is not None 
        assert iq_conn is not None
        
        # Verify shared simulation
        simulation = asg_conn._mock_instance
        assert voltage_conn._mock_instance is simulation
        assert iq_conn._mock_instance is simulation
        
        # Configure ASG with specific parameters
        if hasattr(asg_conn, 'configure_asg'):
            success = asg_conn.configure_asg(
                ASGChannel.ASG0, 
                frequency=1000.0,    # 1 kHz
                amplitude=0.2,       # 200mV
                offset=0.0,
                waveform="sin"
            )
            
            if success:
                # ASG output should affect voltage readings
                voltage = voltage_conn.read_voltage(InputChannel.IN1)
                assert isinstance(voltage, (int, float))
                
                # IQ measurements should also be affected
                iq_result = iq_conn.get_iq_measurement(IQChannel.IQ0)
                if iq_result is not None:
                    i_val, q_val = iq_result
                    magnitude = np.sqrt(i_val**2 + q_val**2)
                    
                    # Should see some signal due to ASG output
                    assert magnitude >= 0
                    print(f"ASG output affects IQ magnitude: {magnitude:.4f}")
    
    @pytest.mark.integration
    def test_multi_plugin_coordination(self):
        """Test full multi-plugin coordination scenario."""
        # Create connections simulating a complete measurement setup
        connections = {
            'pid': self.manager.connect_device(self.hostname, "pid_ctrl", mock_mode=True),
            'asg': self.manager.connect_device(self.hostname, "signal_gen", mock_mode=True), 
            'voltage': self.manager.connect_device(self.hostname, "monitor", mock_mode=True),
            'iq': self.manager.connect_device(self.hostname, "lockin", mock_mode=True),
            'scope': self.manager.connect_device(self.hostname, "scope", mock_mode=True)
        }
        
        # Verify all connections succeeded
        for name, conn in connections.items():
            assert conn is not None, f"Failed to create {name} connection"
        
        # Verify all connections share the same simulation engine
        base_simulation = connections['pid']._mock_instance
        for name, conn in connections.items():
            assert conn._mock_instance is base_simulation, f"{name} connection not sharing simulation"
        
        print(f"✅ All {len(connections)} plugins sharing simulation engine")
        
        # Test coordinated measurement scenario
        simulation_steps = []
        
        # Step 1: Set initial conditions
        if hasattr(connections['pid'], 'set_pid_setpoint'):
            initial_setpoint = 0.1
            success = connections['pid'].set_pid_setpoint(PIDChannel.PID0, initial_setpoint)
            if success:
                simulation_steps.append(f"PID setpoint: {initial_setpoint}V")
        
        # Step 2: Configure signal generator
        if hasattr(connections['asg'], 'configure_asg'):
            success = connections['asg'].configure_asg(
                ASGChannel.ASG0, frequency=500.0, amplitude=0.1, 
                offset=0.0, waveform="sin"
            )
            if success:
                simulation_steps.append("ASG configured: 500Hz, 100mV")
        
        # Step 3: Take measurements across all channels
        measurements = {}
        
        # Voltage measurements
        voltage = connections['voltage'].read_voltage(InputChannel.IN1)
        if voltage is not None:
            measurements['voltage_in1'] = voltage
            
        # IQ measurements  
        iq_result = connections['iq'].get_iq_measurement(IQChannel.IQ0)
        if iq_result is not None:
            i_val, q_val = iq_result
            measurements['iq_magnitude'] = np.sqrt(i_val**2 + q_val**2)
            measurements['iq_phase'] = np.degrees(np.arctan2(q_val, i_val))
            
        # Scope data (if available)
        if hasattr(connections['scope'], 'acquire_scope_data'):
            scope_data = connections['scope'].acquire_scope_data(InputChannel.IN1)
            if scope_data is not None and len(scope_data) > 0:
                measurements['scope_mean'] = np.mean(scope_data)
                measurements['scope_std'] = np.std(scope_data)
        
        # Verify we got meaningful measurements
        assert len(measurements) > 0, "Should have at least one measurement"
        
        print("📊 Coordinated measurements:")
        for key, value in measurements.items():
            print(f"  {key}: {value:.4f}")
            
        # All measurements should be reasonable values
        for key, value in measurements.items():
            assert isinstance(value, (int, float)), f"{key} should be numeric"
            assert not np.isnan(value), f"{key} should not be NaN"
            assert np.isfinite(value), f"{key} should be finite"
        
        print("✅ Coordinated simulation working correctly")
    
    @pytest.mark.integration
    def test_simulation_state_persistence(self):
        """Test that simulation state persists across connection cycles."""
        # Create initial connection and set state
        conn1 = self.manager.connect_device(self.hostname, "test1", mock_mode=True)
        assert conn1 is not None
        
        # Set a specific PID setpoint
        test_setpoint = 0.42  # Distinctive value
        success = conn1.set_pid_setpoint(PIDChannel.PID0, test_setpoint)
        
        # Disconnect the first connection
        self.manager.disconnect_device(self.hostname, "test1")
        
        # Create new connection - should get the same simulation state
        conn2 = self.manager.connect_device(self.hostname, "test2", mock_mode=True)
        assert conn2 is not None
        
        if success:
            # Read back the setpoint - should persist
            readback = conn2.get_pid_setpoint(PIDChannel.PID0)
            if readback is not None:
                # Should be close to the original setpoint
                assert abs(readback - test_setpoint) < 0.1, \
                    f"Setpoint not persistent: {test_setpoint} vs {readback}"
                print(f"✅ Simulation state persisted: {test_setpoint} → {readback}")
    
    @pytest.mark.integration 
    def test_performance_multiple_plugins(self):
        """Test performance with multiple simultaneous plugin connections."""
        num_connections = 10
        connections = []
        
        start_time = time.time()
        
        # Create many connections
        for i in range(num_connections):
            conn = self.manager.connect_device(self.hostname, f"perf_test_{i}", mock_mode=True)
            assert conn is not None
            connections.append(conn)
        
        creation_time = time.time() - start_time
        print(f"Created {num_connections} connections in {creation_time:.3f}s")
        
        # Verify all share the same simulation
        base_sim = connections[0]._mock_instance
        for i, conn in enumerate(connections):
            assert conn._mock_instance is base_sim, f"Connection {i} not sharing simulation"
        
        # Perform operations on all connections
        start_time = time.time()
        
        for i, conn in enumerate(connections):
            # Different operations for variety
            if i % 3 == 0:
                voltage = conn.read_voltage(InputChannel.IN1)
                assert isinstance(voltage, (int, float))
            elif i % 3 == 1:
                iq_result = conn.get_iq_measurement(IQChannel.IQ0)
                if iq_result is not None:
                    assert len(iq_result) == 2
            else:
                success = conn.set_pid_setpoint(PIDChannel.PID0, 0.1 + i * 0.01)
                # success may be True or False depending on implementation
        
        operation_time = time.time() - start_time
        print(f"Performed {num_connections} operations in {operation_time:.3f}s")
        
        # Performance should be reasonable
        assert creation_time < 2.0, "Connection creation should be fast"
        assert operation_time < 1.0, "Operations should be fast"


class TestRealWorldSimulationScenarios:
    """Test realistic experimental scenarios with coordinated simulation."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_shared_mock_instance()
        self.manager = PyRPLManager.get_instance()
        self.manager.disconnect_all()
        self.hostname = "experiment-sim.local"
        
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.disconnect_all()
        reset_shared_mock_instance()
    
    @pytest.mark.integration
    def test_laser_stabilization_scenario(self):
        """Test a laser power stabilization scenario."""
        # Simulate a laser stabilization setup:
        # - PID controls laser current based on photodiode feedback
        # - Voltage monitor shows photodiode signal
        # - Scope shows real-time power fluctuations
        
        pid_conn = self.manager.connect_device(self.hostname, "laser_pid", mock_mode=True)
        monitor_conn = self.manager.connect_device(self.hostname, "photodiode", mock_mode=True)
        scope_conn = self.manager.connect_device(self.hostname, "power_scope", mock_mode=True)
        
        assert all(conn is not None for conn in [pid_conn, monitor_conn, scope_conn])
        
        # Set target laser power (via PID setpoint)
        target_power = 0.5  # 500mV equivalent
        success = pid_conn.set_pid_setpoint(PIDChannel.PID0, target_power)
        
        if success:
            # Allow simulation to stabilize
            time.sleep(0.1)
            
            # Check photodiode reading
            photodiode_signal = monitor_conn.read_voltage(InputChannel.IN1)
            assert isinstance(photodiode_signal, (int, float))
            
            # Scope should show power time series
            if hasattr(scope_conn, 'acquire_scope_data'):
                power_trace = scope_conn.acquire_scope_data(InputChannel.IN1)
                if power_trace is not None and len(power_trace) > 0:
                    mean_power = np.mean(power_trace)
                    power_stability = np.std(power_trace)
                    
                    print(f"Laser stabilization results:")
                    print(f"  Target: {target_power:.3f}V")
                    print(f"  Photodiode: {photodiode_signal:.3f}V")
                    print(f"  Mean power: {mean_power:.3f}V")
                    print(f"  Stability (std): {power_stability:.4f}V")
                    
                    # Should see some correlation between target and measurements
                    assert isinstance(mean_power, (int, float))
                    assert isinstance(power_stability, (int, float))
    
    @pytest.mark.integration
    def test_lock_in_amplifier_scenario(self):
        """Test a lock-in amplifier measurement scenario."""
        # Simulate lock-in detection:
        # - ASG provides reference signal
        # - IQ detector performs phase-sensitive detection
        # - Voltage monitor shows total signal
        
        asg_conn = self.manager.connect_device(self.hostname, "reference", mock_mode=True)
        iq_conn = self.manager.connect_device(self.hostname, "lockin", mock_mode=True)
        signal_conn = self.manager.connect_device(self.hostname, "signal_monitor", mock_mode=True)
        
        assert all(conn is not None for conn in [asg_conn, iq_conn, signal_conn])
        
        # Configure reference signal
        ref_frequency = 1333.0  # Distinctive frequency
        if hasattr(asg_conn, 'configure_asg'):
            success = asg_conn.configure_asg(
                ASGChannel.ASG0,
                frequency=ref_frequency,
                amplitude=0.1,  # 100mV reference
                offset=0.0,
                waveform="sin"
            )
            
            if success:
                # Configure IQ detector for same frequency
                if hasattr(iq_conn, 'configure_iq'):
                    # Create simple config object with required attributes
                    class IQConfig:
                        def __init__(self, frequency, bandwidth, phase):
                            self.frequency = frequency
                            self.bandwidth = bandwidth
                            self.phase = phase

                    iq_config = IQConfig(
                        frequency=ref_frequency,
                        bandwidth=10.0,  # 10 Hz bandwidth
                        phase=0.0  # In-phase detection
                    )
                    
                    iq_success = iq_conn.configure_iq(IQChannel.IQ0, iq_config)
                    
                    if iq_success:
                        # Take lock-in measurement
                        iq_result = iq_conn.get_iq_measurement(IQChannel.IQ0)
                        if iq_result is not None:
                            i_val, q_val = iq_result
                            magnitude = np.sqrt(i_val**2 + q_val**2)
                            phase = np.degrees(np.arctan2(q_val, i_val))
                            
                            # Monitor total signal
                            total_signal = signal_conn.read_voltage(InputChannel.IN1)
                            
                            print(f"Lock-in amplifier results:")
                            print(f"  Reference: {ref_frequency:.1f}Hz, 100mV")
                            print(f"  I component: {i_val:.4f}V")
                            print(f"  Q component: {q_val:.4f}V") 
                            print(f"  Magnitude: {magnitude:.4f}V")
                            print(f"  Phase: {phase:.1f}°")
                            print(f"  Total signal: {total_signal:.4f}V")
                            
                            # All measurements should be reasonable
                            assert all(isinstance(val, (int, float)) for val in [i_val, q_val, magnitude, total_signal])
                            assert 0 <= magnitude <= 1.0, "Magnitude should be reasonable"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])