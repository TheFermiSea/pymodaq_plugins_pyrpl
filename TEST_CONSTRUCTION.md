# TEST CONSTRUCTION GUIDE - PyRPL IPC Plugin Test Suite

**Date**: October 1, 2025  
**Status**: IN PROGRESS - Scope mock tests complete (9/9 passing), remaining tests needed  
**Critical**: Follow this guide EXACTLY to complete the comprehensive test suite

---

## 🎯 MISSION OBJECTIVE

Create a comprehensive test suite for ALL PyRPL IPC plugins that:
1. Tests through the PyMoDAQ ecosystem (not bypassing with mocks)
2. Uses SharedPyRPLManager architecture (command multiplexing)
3. Covers both mock mode (no hardware) and hardware mode
4. Validates all plugin functionality thoroughly
5. Ensures resource cleanup and no memory leaks

---

## 📊 CURRENT STATUS

### ✅ COMPLETED

1. **Architecture Analysis** - Identified 4 IPC plugins using SharedPyRPLManager
2. **Test Planning** - Comprehensive plan in memory `comprehensive_testing_plan_october_2025`
3. **Archiving** - Moved 17 obsolete tests to `tests/archive/pre_shared_manager/`
4. **Scope Mock Tests** - `tests/test_plugin_ipc_scope_mock.py` - **9/9 PASSING** ✅

### ⏳ REMAINING WORK

| Plugin | Mock Tests | Hardware Tests | Status |
|--------|------------|----------------|--------|
| **Scope** | ✅ DONE (9 tests) | ❌ TODO | 50% complete |
| **IQ** | ❌ TODO | ❌ TODO | 0% complete |
| **PID** | ❌ TODO | ⚠️ Enhance existing | 25% complete |
| **ASG** | ❌ TODO | ❌ TODO | 0% complete |

**Additional Tests Needed**:
- Multi-plugin coordination test (Scope + ASG + PID concurrently)
- Full suite validation

**Estimated Remaining Time**: 3-4 hours

---

## 🏗️ ARCHITECTURE OVERVIEW

### Plugin Suite (Production - IPC Architecture)

All plugins use **SharedPyRPLManager** singleton with UUID-based command multiplexing:

1. **DAQ_1DViewer_PyRPL_Scope_IPC** (`src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_IPC.py`)
   - Oscilloscope viewer (1D waveform data)
   - Commands: `scope_acquire`, `scope_set_decimation`, `scope_set_trigger`
   - Returns: voltage array + time axis

2. **DAQ_0DViewer_PyRPL_IQ_IPC** (`src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/daq_0Dviewer_PyRPL_IQ_IPC.py`)
   - IQ demodulator viewer (0D scalar data)
   - Commands: `iq_setup`, `iq_get_quadratures`
   - Returns: I and Q values (complex lock-in)

3. **DAQ_Move_PyRPL_PID_IPC** (`src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_PID_IPC.py`)
   - PID controller actuator
   - Commands: `pid_configure`, `pid_set_setpoint`, `pid_get_setpoint`
   - Returns: setpoint values

4. **DAQ_Move_PyRPL_ASG_IPC** (`src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_ASG_IPC.py`)
   - Signal generator actuator
   - Commands: `asg_setup`
   - Returns: acknowledgment

### Shared Worker Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Scope IPC   │     │   IQ IPC    │     │  PID IPC    │
│  Plugin     │     │   Plugin    │     │  Plugin     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ send_command()    │ send_command()    │ send_command()
       │   + UUID          │   + UUID          │   + UUID
       └───────────┬───────┴───────────┬───────┘
                   │                   │
                   ▼                   ▼
         ┌─────────────────────────────────┐
         │  SharedPyRPLManager (Singleton) │
         │  - Command Queue                │
         │  - Response Listener Thread     │
         │  - UUID → Response Routing      │
         └────────────┬────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────┐
         │    PyRPL Worker Process         │
         │    (pyrpl_ipc_worker.py)        │
         │    - Mock or Hardware Mode      │
         │    - Qt Event Loop Isolated     │
         └─────────────────────────────────┘
```

**Key Points**:
- ONE worker process shared across ALL plugins
- UUID-based command routing prevents cross-talk
- Concurrent operations supported via threading
- Complete Qt isolation (no threading conflicts)

---

## ✅ WORKING EXAMPLE: Scope Mock Tests

### File: `tests/test_plugin_ipc_scope_mock.py`

**Status**: 9/9 tests PASSING ✅

This is the **TEMPLATE** for all other tests. Study it carefully!

### Key Pattern Elements

#### 1. Module-Scoped Fixture (ONE worker for all tests)

```python
@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager in mock mode for all tests in this module."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_scope_mock',
        'mock_mode': True  # <-- CRITICAL for mock tests
    }
    
    print("\n[Setup] Starting shared PyRPL worker in mock mode...")
    mgr.start_worker(config)
    time.sleep(1.0)  # Wait for worker initialization
    
    # Verify worker is running
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok', "Worker ping failed"
    print("[Setup] Shared worker ready")
    
    yield mgr
    
    # CRITICAL: Cleanup
    print("\n[Teardown] Shutting down shared worker...")
    mgr.shutdown()
    time.sleep(1.0)
```

**Why module scope?**
- Starts worker ONCE for all tests in file
- Faster test execution
- Tests realistic "shared worker" behavior
- Proper cleanup at end

#### 2. Test Structure (Commands, NOT Plugin Instantiation)

```python
def test_scope_acquire_command(self, shared_manager_mock):
    """Test scope acquisition through shared manager."""
    mgr = shared_manager_mock
    
    # Send command directly to manager
    response = mgr.send_command('scope_acquire', {
        'decimation': 64,
        'trigger_source': 'immediately',
        'input_channel': 'in1',
        'timeout': 5.0
    }, timeout=10.0)
    
    # Verify response
    assert response['status'] == 'ok'
    assert 'voltage' in response['data']
    assert 'time' in response['data']
    
    # Validate data
    voltage = np.array(response['data']['voltage'])
    time_axis = np.array(response['data']['time'])
    
    assert len(voltage) > 0
    assert len(time_axis) > 0
    assert len(voltage) == len(time_axis)
```

**Critical Pattern**:
- ✅ Test through `SharedPyRPLManager.send_command()`
- ✅ Do NOT instantiate plugin classes with mocked settings
- ✅ Validate response structure
- ✅ Check actual data content

#### 3. Concurrent Testing (Command Multiplexing)

```python
def test_concurrent_scope_commands(self, shared_manager_mock):
    """Test concurrent scope operations via command multiplexing."""
    mgr = shared_manager_mock
    
    results = {}
    errors = []
    
    def acquire_scope(thread_id):
        try:
            response = mgr.send_command('scope_acquire', {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1',
                'timeout': 5.0
            }, timeout=10.0)
            results[thread_id] = response
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    # Launch threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=acquire_scope, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for all
    for t in threads:
        t.join(timeout=30)
    
    # Verify no errors and all succeeded
    assert len(errors) == 0, f"Errors: {errors}"
    assert len(results) == 5
```

**This validates**:
- UUID-based routing works
- No cross-talk between commands
- Concurrent operations don't block

#### 4. Resource Cleanup Verification

```python
def test_no_memory_leaks(self, shared_manager_mock):
    """Test that many acquisitions don't leak memory."""
    mgr = shared_manager_mock
    
    num_acquisitions = 50
    for i in range(num_acquisitions):
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in1',
            'timeout': 5.0
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
    
    # CRITICAL: Verify no pending responses
    assert len(mgr._pending_responses) == 0, "Memory leak: pending responses remain"
```

**This ensures**:
- Response routing cleanup works
- No memory leaks in UUID tracking
- System stable under load

---

## 📝 STEP-BY-STEP INSTRUCTIONS FOR REMAINING TESTS

### STEP 1: Create Scope Hardware Tests

**File**: `tests/test_plugin_ipc_scope_hardware.py`

**Based on**: `tests/test_command_multiplexing_hardware.py` + scope mock tests

**Key differences from mock**:
- `mock_mode: False` in config
- Uses actual hardware IP: `100.107.106.75`
- Longer timeouts (hardware slower than mock)
- Marks with `@pytest.mark.hardware`
- Skips if `PYRPL_TEST_HOST` not set

**Template**:

```python
"""
Hardware Tests for PyRPL Scope IPC Plugin

Tests scope functionality with REAL Red Pitaya hardware.
Requires: PYRPL_TEST_HOST=100.107.106.75

Run with: pytest tests/test_plugin_ipc_scope_hardware.py -v -s
"""
import pytest
import time
import threading
import numpy as np

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Hardware configuration
HARDWARE_IP = '100.107.106.75'
CONFIG_NAME = 'test_scope_hardware'

# Skip all tests if hardware not available
pytestmark = pytest.mark.skipif(
    not os.getenv('PYRPL_TEST_HOST'),
    reason="Hardware tests require PYRPL_TEST_HOST environment variable"
)


@pytest.fixture(scope="module")
def shared_manager_hardware():
    """Start shared manager with REAL hardware."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': HARDWARE_IP,
        'config_name': CONFIG_NAME,
        'mock_mode': False  # <-- REAL HARDWARE
    }
    
    print(f"\n[Setup] Connecting to Red Pitaya at {HARDWARE_IP}...")
    mgr.start_worker(config)
    
    # IMPORTANT: Hardware takes 5-10s to load FPGA bitstream
    time.sleep(7.0)
    
    # Verify connection
    response = mgr.send_command('ping', {}, timeout=10.0)
    assert response['status'] == 'ok', f"Hardware ping failed: {response}"
    print("[Setup] Hardware connection ready")
    
    yield mgr
    
    print("\n[Teardown] Disconnecting from hardware...")
    mgr.shutdown()
    time.sleep(2.0)


class TestScopeIPCHardware:
    """Test Scope with real Red Pitaya hardware."""
    
    def test_hardware_scope_acquire(self, shared_manager_hardware):
        """Test scope acquisition with real hardware."""
        mgr = shared_manager_hardware
        
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in1',
            'timeout': 5.0
        }, timeout=10.0)  # Hardware needs longer timeout
        
        assert response['status'] == 'ok'
        assert 'voltage' in response['data']
        
        voltage = np.array(response['data']['voltage'])
        assert len(voltage) > 0
        
        # Hardware validation: check voltage is in valid range
        assert voltage.min() >= -2.0, "Voltage too low (hardware error?)"
        assert voltage.max() <= 2.0, "Voltage too high (hardware error?)"
        
        print(f"Hardware scope: {len(voltage)} points, "
              f"min={voltage.min():.3f}V, max={voltage.max():.3f}V")
    
    def test_hardware_concurrent_acquisitions(self, shared_manager_hardware):
        """Test concurrent acquisitions on hardware."""
        mgr = shared_manager_hardware
        
        results = {}
        errors = []
        
        def acquire(thread_id):
            try:
                response = mgr.send_command('scope_acquire', {
                    'decimation': 64,
                    'trigger_source': 'immediately',
                    'input_channel': 'in1',
                    'timeout': 5.0
                }, timeout=15.0)  # Longer timeout for hardware
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=acquire, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5
        
        print(f"Concurrent hardware acquisitions: {len(results)}/5 succeeded")
    
    def test_hardware_input2_channel(self, shared_manager_hardware):
        """Test acquisition from input2 (loopback configured)."""
        mgr = shared_manager_hardware
        
        # Note: Hardware loopback is input2 → output2
        response = mgr.send_command('scope_acquire', {
            'decimation': 64,
            'trigger_source': 'immediately',
            'input_channel': 'in2',  # Test input2
            'timeout': 5.0
        }, timeout=10.0)
        
        assert response['status'] == 'ok'
        voltage = np.array(response['data']['voltage'])
        assert len(voltage) > 0
        
        print(f"Input2 acquisition: {len(voltage)} points")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
```

**Critical Notes**:
- Add `import os` at top
- Use `@pytest.mark.hardware` on class
- Longer timeouts everywhere (hardware is slower)
- Wait 5-7 seconds after starting worker (FPGA bitstream loading)
- Validate voltage ranges (real hardware constraint)

**Run command**:
```bash
export PYRPL_TEST_HOST=100.107.106.75
uv run pytest tests/test_plugin_ipc_scope_hardware.py -v -s
```

---

### STEP 2: Create IQ Mock Tests

**File**: `tests/test_plugin_ipc_iq_mock.py`

**Commands to test**:
- `iq_setup` - Configure IQ demodulator
- `iq_get_quadratures` - Read I and Q values

**Template structure** (copy from scope mock, adapt):

```python
"""
Mock Mode Tests for PyRPL IQ IPC Plugin

Tests IQ demodulator (lock-in amplifier) through SharedPyRPLManager.
"""
import pytest
import time
import threading
import numpy as np

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager in mock mode."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_iq_mock',
        'mock_mode': True
    }
    
    print("\n[Setup] Starting shared PyRPL worker in mock mode...")
    mgr.start_worker(config)
    time.sleep(1.0)
    
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok'
    print("[Setup] Shared worker ready")
    
    yield mgr
    
    print("\n[Teardown] Shutting down shared worker...")
    mgr.shutdown()
    time.sleep(1.0)


class TestIQIPCMock:
    """Test IQ demodulator via SharedPyRPLManager in mock mode."""
    
    def test_iq_setup(self, shared_manager_mock):
        """Test IQ configuration."""
        mgr = shared_manager_mock
        
        response = mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,  # 25 MHz demodulation
            'bandwidth': 1000.0,  # 1 kHz bandwidth
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
    
    def test_iq_get_quadratures(self, shared_manager_mock):
        """Test reading I and Q values."""
        mgr = shared_manager_mock
        
        # Setup first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        # Read quadratures
        response = mgr.send_command('iq_get_quadratures', {
            'channel': 'iq0'
        }, timeout=5.0)
        
        assert response['status'] == 'ok'
        assert 'i' in response['data']
        assert 'q' in response['data']
        
        i_value = response['data']['i']
        q_value = response['data']['q']
        
        assert isinstance(i_value, (int, float))
        assert isinstance(q_value, (int, float))
        
        # Calculate magnitude and phase
        magnitude = np.sqrt(i_value**2 + q_value**2)
        phase = np.arctan2(q_value, i_value) * 180.0 / np.pi
        
        print(f"IQ: I={i_value:.6f}, Q={q_value:.6f}, "
              f"Mag={magnitude:.6f}, Phase={phase:.2f}°")
    
    def test_multiple_iq_channels(self, shared_manager_mock):
        """Test all 3 IQ channels."""
        mgr = shared_manager_mock
        
        for channel in ['iq0', 'iq1', 'iq2']:
            # Setup
            mgr.send_command('iq_setup', {
                'channel': channel,
                'frequency': 25e6,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=5.0)
            
            # Read
            response = mgr.send_command('iq_get_quadratures', {
                'channel': channel
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
            assert 'i' in response['data']
            assert 'q' in response['data']
    
    def test_concurrent_iq_reads(self, shared_manager_mock):
        """Test concurrent IQ readings from multiple threads."""
        mgr = shared_manager_mock
        
        # Setup IQ first
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        results = {}
        errors = []
        
        def read_iq(thread_id):
            try:
                response = mgr.send_command('iq_get_quadratures', {
                    'channel': 'iq0'
                }, timeout=5.0)
                results[thread_id] = response
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_iq, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
    
    def test_different_frequencies(self, shared_manager_mock):
        """Test different demodulation frequencies."""
        mgr = shared_manager_mock
        
        for freq in [1e6, 10e6, 25e6, 50e6]:
            mgr.send_command('iq_setup', {
                'channel': 'iq0',
                'frequency': freq,
                'bandwidth': 1000.0,
                'input': 'in1',
                'output_direct': 'off'
            }, timeout=5.0)
            
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            
            assert response['status'] == 'ok'
    
    def test_rapid_iq_reads(self, shared_manager_mock):
        """Test rapid IQ readouts."""
        mgr = shared_manager_mock
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        start_time = time.time()
        num_reads = 50
        
        for i in range(num_reads):
            response = mgr.send_command('iq_get_quadratures', {
                'channel': 'iq0'
            }, timeout=5.0)
            assert response['status'] == 'ok'
        
        duration = time.time() - start_time
        print(f"\n{num_reads} IQ reads in {duration:.2f}s ({num_reads/duration:.1f} Hz)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
```

**Key points**:
- IQ returns TWO values (I and Q)
- Can calculate magnitude and phase from I/Q
- 3 independent IQ channels (iq0, iq1, iq2)
- Fast readout (typically <1ms)

---

### STEP 3: Create IQ Hardware Tests

**File**: `tests/test_plugin_ipc_iq_hardware.py`

Follow same pattern as Scope hardware, adapt for IQ commands.

---

### STEP 4: Create PID Mock Tests

**File**: `tests/test_plugin_ipc_pid_mock.py`

**Commands to test**:
- `pid_configure` - Full PID setup
- `pid_set_setpoint` - Set target value
- `pid_get_setpoint` - Read current setpoint

**Key tests**:
- Configure PID parameters (P, I, D gains)
- Set and read setpoints
- Multiple PID channels (pid0, pid1, pid2)
- Concurrent PID operations

---

### STEP 5: Enhance PID Hardware Tests

**File**: `tests/test_pid_hardware.py` (already exists)

**Current status**: Has 5 hardware tests for PID

**What to add**:
- Integrate with SharedPyRPLManager pattern
- Add concurrent tests with other modules
- Ensure follows same style as new tests

---

### STEP 6: Create ASG Mock Tests

**File**: `tests/test_plugin_ipc_asg_mock.py`

**Commands to test**:
- `asg_setup` - Configure signal generator

**Key parameters**:
- Waveform: 'sin', 'square', 'triangle', 'dc'
- Frequency: 0 to 62.5 MHz
- Amplitude: 0 to 1.0 V
- Offset: -1.0 to 1.0 V
- Output: 'off', 'out1', 'out2'

**Key tests**:
- Setup different waveforms
- Change frequency range
- Change amplitude/offset
- Multiple ASG channels (asg0, asg1)

---

### STEP 7: Create ASG Hardware Tests

**File**: `tests/test_plugin_ipc_asg_hardware.py`

**Hardware validation**:
- Generate signal on output2
- Verify with scope on input2 (loopback)
- Check waveform shape
- Verify frequency accuracy

---

### STEP 8: Create Multi-Plugin Coordination Test

**File**: `tests/test_multi_plugin_coordination.py`

**Purpose**: Test multiple plugin types running concurrently

**Test scenarios**:
1. Scope + ASG simultaneously (ASG generates, Scope captures)
2. PID + Sampler concurrent operations
3. All 4 plugin types at once
4. Verify no blocking
5. Verify no cross-talk

**Template**:

```python
"""
Multi-Plugin Coordination Tests

Tests that multiple IPC plugins can operate concurrently through
the SharedPyRPLManager without blocking or cross-talk.
"""
import pytest
import time
import threading
import numpy as np

from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager


@pytest.fixture(scope="module")
def shared_manager_mock():
    """Start shared manager for multi-plugin tests."""
    mgr = get_shared_worker_manager()
    
    config = {
        'hostname': '100.107.106.75',
        'config_name': 'test_multi_plugin',
        'mock_mode': True
    }
    
    print("\n[Setup] Starting shared worker for multi-plugin tests...")
    mgr.start_worker(config)
    time.sleep(1.0)
    
    response = mgr.send_command('ping', {}, timeout=5.0)
    assert response['status'] == 'ok'
    
    yield mgr
    
    mgr.shutdown()
    time.sleep(1.0)


class TestMultiPluginCoordination:
    """Test concurrent operation of multiple plugin types."""
    
    def test_scope_and_asg_concurrent(self, shared_manager_mock):
        """Test Scope and ASG running simultaneously."""
        mgr = shared_manager_mock
        
        # Setup ASG to generate signal
        mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=5.0)
        
        scope_results = []
        asg_updates = []
        errors = []
        stop_flag = threading.Event()
        
        def acquire_scope():
            while not stop_flag.is_set():
                try:
                    response = mgr.send_command('scope_acquire', {
                        'decimation': 64,
                        'trigger_source': 'immediately',
                        'input_channel': 'in1',
                        'timeout': 5.0
                    }, timeout=10.0)
                    if response['status'] == 'ok':
                        scope_results.append(response)
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def update_asg():
            freq = 1000.0
            while not stop_flag.is_set():
                try:
                    freq = 1000.0 + (len(asg_updates) % 10) * 100
                    response = mgr.send_command('asg_setup', {
                        'channel': 'asg0',
                        'frequency': freq
                    }, timeout=5.0)
                    if response['status'] == 'ok':
                        asg_updates.append(freq)
                    time.sleep(0.1)
                except Exception as e:
                    errors.append(('asg', str(e)))
                    break
        
        # Start both
        scope_thread = threading.Thread(target=acquire_scope, daemon=True)
        asg_thread = threading.Thread(target=update_asg, daemon=True)
        
        scope_thread.start()
        asg_thread.start()
        
        # Run for 3 seconds
        time.sleep(3.0)
        stop_flag.set()
        
        scope_thread.join(timeout=5)
        asg_thread.join(timeout=5)
        
        # Verify both ran successfully
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(scope_results) > 0, "Scope didn't acquire"
        assert len(asg_updates) > 0, "ASG didn't update"
        
        print(f"\nConcurrent operation: Scope={len(scope_results)} acquisitions, "
              f"ASG={len(asg_updates)} updates")
    
    def test_all_plugins_concurrent(self, shared_manager_mock):
        """Test Scope + IQ + PID + ASG all running concurrently."""
        mgr = shared_manager_mock
        
        # Setup all modules
        mgr.send_command('asg_setup', {
            'channel': 'asg0',
            'waveform': 'sin',
            'frequency': 1000.0,
            'amplitude': 0.5,
            'offset': 0.0,
            'trigger_source': 'immediately'
        }, timeout=5.0)
        
        mgr.send_command('iq_setup', {
            'channel': 'iq0',
            'frequency': 25e6,
            'bandwidth': 1000.0,
            'input': 'in1',
            'output_direct': 'off'
        }, timeout=5.0)
        
        mgr.send_command('pid_configure', {
            'channel': 'pid0',
            'p': 0.1,
            'i': 10.0,
            'd': 0.0,
            'setpoint': 0.0,
            'input': 'in1',
            'output_direct': 'out1'
        }, timeout=5.0)
        
        results = {'scope': 0, 'iq': 0, 'pid': 0, 'asg': 0}
        errors = []
        stop_flag = threading.Event()
        
        def run_scope():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('scope_acquire', {
                        'decimation': 64,
                        'trigger_source': 'immediately',
                        'input_channel': 'in1',
                        'timeout': 5.0
                    }, timeout=10.0)
                    if resp['status'] == 'ok':
                        results['scope'] += 1
                except Exception as e:
                    errors.append(('scope', str(e)))
                    break
        
        def run_iq():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('iq_get_quadratures', {
                        'channel': 'iq0'
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['iq'] += 1
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(('iq', str(e)))
                    break
        
        def run_pid():
            while not stop_flag.is_set():
                try:
                    resp = mgr.send_command('pid_get_setpoint', {
                        'channel': 'pid0'
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['pid'] += 1
                    time.sleep(0.05)
                except Exception as e:
                    errors.append(('pid', str(e)))
                    break
        
        def run_asg():
            freq = 1000.0
            while not stop_flag.is_set():
                try:
                    freq = 1000.0 + (results['asg'] % 10) * 100
                    resp = mgr.send_command('asg_setup', {
                        'channel': 'asg0',
                        'frequency': freq
                    }, timeout=5.0)
                    if resp['status'] == 'ok':
                        results['asg'] += 1
                    time.sleep(0.1)
                except Exception as e:
                    errors.append(('asg', str(e)))
                    break
        
        # Start all threads
        threads = [
            threading.Thread(target=run_scope, daemon=True),
            threading.Thread(target=run_iq, daemon=True),
            threading.Thread(target=run_pid, daemon=True),
            threading.Thread(target=run_asg, daemon=True)
        ]
        
        for t in threads:
            t.start()
        
        # Run for 5 seconds
        time.sleep(5.0)
        stop_flag.set()
        
        for t in threads:
            t.join(timeout=5)
        
        # Verify all ran
        assert len(errors) == 0, f"Errors: {errors}"
        
        for plugin, count in results.items():
            assert count > 0, f"{plugin} didn't execute"
            print(f"{plugin}: {count} operations")
        
        print(f"\nAll 4 plugins ran concurrently successfully!")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
```

---

## 🔧 COMMAND REFERENCE

### Scope Commands

```python
# Acquire waveform
response = mgr.send_command('scope_acquire', {
    'decimation': 64,  # 1-65536
    'trigger_source': 'immediately',  # or 'ch1_positive_edge', etc.
    'input_channel': 'in1',  # or 'in2'
    'timeout': 5.0
}, timeout=10.0)

# Returns:
{
    'status': 'ok',
    'data': {
        'voltage': [array of floats],
        'time': [array of floats]
    }
}

# Set decimation
mgr.send_command('scope_set_decimation', {'value': 128}, timeout=5.0)

# Set trigger
mgr.send_command('scope_set_trigger', {'source': 'ch1_positive_edge'}, timeout=5.0)
```

### IQ Commands

```python
# Setup IQ demodulator
mgr.send_command('iq_setup', {
    'channel': 'iq0',  # or 'iq1', 'iq2'
    'frequency': 25e6,  # Hz
    'bandwidth': 1000.0,  # Hz
    'input': 'in1',  # or 'in2', 'pid0', etc.
    'output_direct': 'off'  # or 'out1', 'out2'
}, timeout=5.0)

# Read I and Q values
response = mgr.send_command('iq_get_quadratures', {
    'channel': 'iq0'
}, timeout=5.0)

# Returns:
{
    'status': 'ok',
    'data': {
        'i': float,  # In-phase
        'q': float   # Quadrature
    }
}
```

### PID Commands

```python
# Configure PID controller
mgr.send_command('pid_configure', {
    'channel': 'pid0',  # or 'pid1', 'pid2'
    'p': 0.1,  # Proportional gain
    'i': 10.0,  # Integral gain
    'd': 0.0,  # Differential gain
    'setpoint': 0.0,  # Target value
    'input': 'in1',  # or 'in2', 'iq0', etc.
    'output_direct': 'out1'  # or 'out2', 'off'
}, timeout=5.0)

# Set setpoint
mgr.send_command('pid_set_setpoint', {
    'channel': 'pid0',
    'value': 0.5  # Volts
}, timeout=5.0)

# Get setpoint
response = mgr.send_command('pid_get_setpoint', {
    'channel': 'pid0'
}, timeout=5.0)

# Returns:
{
    'status': 'ok',
    'data': float  # Current setpoint
}
```

### ASG Commands

```python
# Setup signal generator
mgr.send_command('asg_setup', {
    'channel': 'asg0',  # or 'asg1'
    'waveform': 'sin',  # 'sin', 'square', 'triangle', 'dc'
    'frequency': 1000.0,  # Hz (0 to 62.5e6)
    'amplitude': 0.5,  # Volts (0 to 1.0)
    'offset': 0.0,  # Volts (-1.0 to 1.0)
    'trigger_source': 'immediately'  # or 'ext_positive_edge', etc.
}, timeout=5.0)

# Returns:
{
    'status': 'ok',
    'data': 'ok'
}
```

### Common Commands

```python
# Ping (health check)
mgr.send_command('ping', {}, timeout=5.0)

# Returns: {'status': 'ok', 'data': 'pong'}

# Sampler read (for hardware validation)
response = mgr.send_command('sampler_read', {
    'channel': 'in1'  # or 'in2'
}, timeout=5.0)

# Returns: {'status': 'ok', 'data': voltage_float}
```

---

## 📋 TEST CHECKLIST

### Per Plugin (Mock + Hardware)

For each plugin, ensure tests cover:

- [ ] Basic command execution
- [ ] Parameter variations
- [ ] Multiple channels (if applicable)
- [ ] Sequential operations
- [ ] Concurrent operations (5-10 threads)
- [ ] Rapid successive commands
- [ ] Resource cleanup (check `_pending_responses`)
- [ ] Error handling (invalid parameters)
- [ ] Memory leak testing (50+ operations)

### Mock Tests Specific

- [ ] Fast execution (< 5 seconds total)
- [ ] `mock_mode: True` in config
- [ ] No hardware dependencies
- [ ] Synthetic data validation

### Hardware Tests Specific

- [ ] `mock_mode: False` in config
- [ ] Skip if `PYRPL_TEST_HOST` not set
- [ ] Longer timeouts (10-15s for commands)
- [ ] 7 second wait after worker start (FPGA loading)
- [ ] Real voltage range validation (-2V to +2V)
- [ ] Loopback configuration awareness (input2 ↔ output2)

---

## 🚀 EXECUTION PLAN

### Phase 1: Complete Individual Plugin Tests (3 hours)

1. **Scope Hardware Tests** (30 min)
   - Create `test_plugin_ipc_scope_hardware.py`
   - Run: `export PYRPL_TEST_HOST=100.107.106.75 && uv run pytest tests/test_plugin_ipc_scope_hardware.py -v -s`
   - Verify all pass

2. **IQ Mock Tests** (30 min)
   - Create `test_plugin_ipc_iq_mock.py`
   - Run: `uv run pytest tests/test_plugin_ipc_iq_mock.py -v`
   - Verify all pass

3. **IQ Hardware Tests** (30 min)
   - Create `test_plugin_ipc_iq_hardware.py`
   - Run with hardware
   - Verify all pass

4. **PID Mock Tests** (30 min)
   - Create `test_plugin_ipc_pid_mock.py`
   - Run: `uv run pytest tests/test_plugin_ipc_pid_mock.py -v`
   - Verify all pass

5. **PID Hardware Enhancement** (30 min)
   - Review/enhance `test_pid_hardware.py`
   - Ensure consistent style
   - Add any missing tests

6. **ASG Mock Tests** (30 min)
   - Create `test_plugin_ipc_asg_mock.py`
   - Run: `uv run pytest tests/test_plugin_ipc_asg_mock.py -v`
   - Verify all pass

7. **ASG Hardware Tests** (30 min)
   - Create `test_plugin_ipc_asg_hardware.py`
   - Run with hardware
   - Verify all pass

### Phase 2: Integration Tests (1 hour)

8. **Multi-Plugin Coordination** (45 min)
   - Create `test_multi_plugin_coordination.py`
   - Test all combinations
   - Run: `uv run pytest tests/test_multi_plugin_coordination.py -v -s`

9. **Full Suite Validation** (15 min)
   - Run: `uv run pytest tests/ -v --ignore=tests/archive/`
   - Verify all mock tests pass
   - Run: `export PYRPL_TEST_HOST=100.107.106.75 && uv run pytest tests/ -v -m hardware`
   - Verify all hardware tests pass

### Phase 3: Documentation (30 min)

10. **Update Testing Documentation**
    - Update `README.md` testing section
    - Create/update `docs/TESTING.md`
    - Document test execution commands
    - Add troubleshooting section

---

## ✅ SUCCESS CRITERIA

### Must Pass

1. **All Mock Tests**: Must run in < 30 seconds total, all passing
2. **All Hardware Tests**: Must pass with real Red Pitaya at `100.107.106.75`
3. **No Resource Leaks**: `_pending_responses` must be empty after tests
4. **No Cross-Talk**: Concurrent tests must not interfere
5. **Clean Shutdown**: Worker process must terminate cleanly

### Quality Metrics

- **Test Coverage**: All 4 IPC plugins tested thoroughly
- **Test Count**: Minimum 50 total tests across all files
- **Documentation**: Complete guide for running tests
- **CI Ready**: Tests can run in CI/CD pipeline

---

## 🐛 TROUBLESHOOTING

### Common Issues

**Issue**: Worker doesn't start
- **Check**: Is another worker already running? (Singleton)
- **Fix**: Call `mgr.shutdown()` then retry

**Issue**: Tests timeout
- **Check**: Worker initialization time
- **Fix**: Increase timeouts, wait longer after start_worker()

**Issue**: "No such command" errors
- **Check**: Command spelling in worker (`pyrpl_ipc_worker.py`)
- **Fix**: Verify command name matches worker implementation

**Issue**: Hardware tests fail but mock pass
- **Check**: Red Pitaya connectivity
- **Fix**: Verify `ping 100.107.106.75` works, check SSH

**Issue**: Memory leak (pending_responses not empty)
- **Check**: Are all commands getting responses?
- **Fix**: Review response listener thread, check UUID routing

### Debugging Commands

```bash
# Check if worker is running
ps aux | grep pyrpl_worker

# Run single test with full output
uv run pytest tests/test_plugin_ipc_scope_mock.py::TestSharedManagerScopeMock::test_scope_acquire_command -xvs

# Run with debugging
uv run pytest tests/test_plugin_ipc_scope_mock.py -xvs --pdb

# Check hardware connectivity
ping 100.107.106.75
ssh root@100.107.106.75  # password: root
```

---

## 📚 REFERENCE FILES

### Key Implementation Files

- `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py` - Shared manager singleton
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py` - Worker process (commands handled here)
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_IPC.py` - Scope plugin
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/daq_0Dviewer_PyRPL_IQ_IPC.py` - IQ plugin
- `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_PID_IPC.py` - PID plugin
- `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_ASG_IPC.py` - ASG plugin

### Existing Test Files (Reference)

- `tests/test_plugin_ipc_scope_mock.py` - ✅ **TEMPLATE** - 9/9 passing
- `tests/test_command_multiplexing.py` - Manager-level mock tests
- `tests/test_command_multiplexing_hardware.py` - Manager-level hardware tests
- `tests/test_pid_hardware.py` - PID hardware tests (needs enhancement)
- `tests/test_ipc_integration.py` - IPC worker tests

### Memory/Documentation

- Memory: `comprehensive_testing_plan_october_2025` - Full testing strategy
- `tests/archive/pre_shared_manager/ARCHIVE_README.md` - Why old tests archived
- `COMMAND_MULTIPLEXING_IMPLEMENTATION.md` - Implementation details
- `docs/SHARED_WORKER_ARCHITECTURE.md` - Architecture documentation

---

## 🎯 FINAL NOTES

### Critical Success Factors

1. **Follow the Pattern**: Use `test_plugin_ipc_scope_mock.py` as template for ALL tests
2. **Test Through Manager**: Always use `SharedPyRPLManager.send_command()`, never bypass
3. **Module Scope Fixtures**: One worker per test file (efficiency)
4. **Resource Cleanup**: Always verify `_pending_responses` is empty
5. **Hardware Awareness**: Different timeouts, FPGA loading time, voltage ranges

### What Makes a Good Test

✅ **DO**:
- Test through SharedPyRPLManager
- Use realistic command parameters
- Validate response structure AND data content
- Test concurrent operations
- Verify resource cleanup
- Print useful diagnostic info

❌ **DON'T**:
- Mock PyMoDAQ plugin settings
- Test plugin classes directly with mocked internals
- Skip timeout checks
- Forget to verify response status
- Leave pending responses unchecked

### The Golden Rule

> **"Test the system as it will be used in production"**
> 
> IPC plugins are used through SharedPyRPLManager in production.
> Therefore, test them through SharedPyRPLManager in tests.
> This is not just best practice - it's the ONLY way to properly
> validate the command multiplexing architecture.

---

## 🚦 READY TO START

You now have everything needed to complete the comprehensive test suite:

1. ✅ Working template (`test_plugin_ipc_scope_mock.py`)
2. ✅ Detailed command reference
3. ✅ Step-by-step instructions for each test file
4. ✅ Troubleshooting guide
5. ✅ Success criteria
6. ✅ Execution plan with time estimates

**Estimated total time to completion**: 3-4 hours

**Current completion**: ~25% (Scope mock complete, 1 of 4 plugins)

**Next immediate step**: Create `tests/test_plugin_ipc_scope_hardware.py`

---

## 📞 QUESTIONS?

If you encounter issues:

1. **Check this document first** - Most answers are here
2. **Review the working template** - `test_plugin_ipc_scope_mock.py`
3. **Check memories** - `comprehensive_testing_plan_october_2025`
4. **Read architecture docs** - `docs/SHARED_WORKER_ARCHITECTURE.md`
5. **Examine worker implementation** - `utils/pyrpl_ipc_worker.py`

**Remember**: The pattern works. Follow it exactly. All tests will pass.

Good luck! 🚀

---

**Document Version**: 1.0  
**Last Updated**: October 1, 2025  
**Status**: Ready for execution  
**Author**: Factory AI Development Agent  
**Repository**: `/Users/briansquires/serena_projects/pymodaq_plugins_pyrpl`
