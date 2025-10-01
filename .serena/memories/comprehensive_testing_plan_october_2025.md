# Comprehensive Testing Plan - PyRPL Plugins (October 2025)

## Overview
Complete testing strategy for PyRPL IPC plugins using shared_pyrpl_manager architecture within the PyMoDAQ ecosystem.

## Plugin Architecture

### Production Plugins (IPC with shared_pyrpl_manager)
1. **DAQ_1DViewer_PyRPL_Scope_IPC** - Oscilloscope viewer
2. **DAQ_0DViewer_PyRPL_IQ_IPC** - IQ demodulator viewer  
3. **DAQ_Move_PyRPL_PID_IPC** - PID controller actuator
4. **DAQ_Move_PyRPL_ASG_IPC** - Signal generator actuator

All use `SharedPyRPLManager` singleton with command multiplexing via UUIDs.

### Legacy Plugins (Deprecated - Direct PyRPLManager)
- Old non-IPC versions still exist but should NOT be tested
- Will be removed in future cleanup

## Test Categories

### Category 1: Shared Manager Core (CURRENT - KEEP)
**File**: `tests/test_command_multiplexing.py`
- Mock mode tests
- UUID-based command routing
- Concurrent command handling
- Timeout and cleanup
- Backward compatibility

**File**: `tests/test_command_multiplexing_hardware.py`
- Hardware command multiplexing
- Concurrent scope + ASG operations
- Multi-channel sampling
- Resource cleanup

### Category 2: IPC Worker Core (CURRENT - KEEP)
**File**: `tests/test_ipc_integration.py`
- Worker process lifecycle
- Mock vs hardware modes
- Command handling stress tests
- Process isolation

### Category 3: Hardware Module Tests (CURRENT - KEEP)
**File**: `tests/test_pid_hardware.py`
- PID configuration
- Setpoint read/write
- Multiple PID channels
- Concurrent PID + sampler

### Category 4: PyMoDAQ Plugin Integration (NEW - NEEDED)
**Files to Create**:
1. `tests/test_plugin_ipc_scope_mock.py` - Scope plugin mock mode
2. `tests/test_plugin_ipc_scope_hardware.py` - Scope plugin hardware
3. `tests/test_plugin_ipc_iq_mock.py` - IQ plugin mock mode
4. `tests/test_plugin_ipc_iq_hardware.py` - IQ plugin hardware
5. `tests/test_plugin_ipc_pid_mock.py` - PID plugin mock mode
6. `tests/test_plugin_ipc_pid_hardware.py` - PID plugin hardware
7. `tests/test_plugin_ipc_asg_mock.py` - ASG plugin mock mode
8. `tests/test_plugin_ipc_asg_hardware.py` - ASG plugin hardware

**What to Test**:
- Plugin lifecycle (ini, grab_data, close)
- Parameter changes (commit_settings)
- PyMoDAQ base class compliance
- Data format (DataFromPlugins, Axis)
- Signal emissions
- Error handling
- Multiple plugin instances

### Category 5: Multi-Plugin Coordination (NEW - NEEDED)
**File**: `tests/test_multi_plugin_coordination_ipc.py`
- Multiple viewers + actuators simultaneously
- No blocking between plugins
- Shared worker resource management
- Concurrent data acquisition

### Category 6: Obsolete Tests (ARCHIVE)
**Files to Archive**:
1. `test_real_hardware_rp_f08d6c.py` - Tests old PyRPLManager
2. `test_pyrpl_functionality.py` - Tests old plugins
3. `test_comprehensive_coverage.py` - Old architecture
4. `test_coordinated_simulation_integration.py` - Old mocks
5. `test_unified_plugin_mock_connections.py` - Old plugins
6. `test_mock_demonstration.py` - Old mock patterns
7. `test_singleton_mock_instance.py` - Old singleton tests
8. `test_integration_fixes.py` - Pre-IPC fixes
9. `test_hardware_environment.py` - Old hardware tests
10. `test_redpitaya_connection.py` - Direct connection tests
11. `test_asg_*.py` - ASG debugging scripts
12. `test_scope_asg_concurrent.py` - Old concurrent tests
13. `test_input2_sampler.py` - Debugging scripts
14. `test_diagnose_input2.py` - Debugging scripts

**Archive Location**: `tests/archive/pre_shared_manager/`

## Test Matrix

### Mock Mode Tests (No Hardware Required)
| Plugin | Basic | Concurrent | Multi-Instance | Error Handling |
|--------|-------|------------|----------------|----------------|
| Scope_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |
| IQ_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |
| PID_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |
| ASG_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |

### Hardware Tests (Red Pitaya Required)
| Plugin | Basic | Concurrent | Real Signals | Long Duration |
|--------|-------|------------|--------------|---------------|
| Scope_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |
| IQ_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |
| PID_IPC | ✅ Exists | ✅ Create | ✅ Create | ✅ Create |
| ASG_IPC | ✅ Create | ✅ Create | ✅ Create | ✅ Create |

## Test Requirements

### All Tests Must:
1. Use `SharedPyRPLManager.get_shared_worker_manager()`
2. Test within PyMoDAQ plugin lifecycle (ini → grab/move → close)
3. Verify DataFromPlugins format
4. Check signal emissions
5. Test both mock and hardware modes
6. Include cleanup and resource checks
7. Use proper pytest fixtures from conftest.py

### Mock Tests Must:
- Complete in < 5 seconds
- Not require network/hardware
- Test full functionality
- Use `mock_mode: True` config

### Hardware Tests Must:
- Use `HARDWARE_IP = '100.107.106.75'`
- Include connectivity checks
- Handle timeouts gracefully
- Mark with `@pytest.mark.hardware`
- Skip if `PYRPL_TEST_HOST` not set

## Success Criteria

### Phase 1: Archive Obsolete (Complete in 30 min)
- [x] Create archive directory structure
- [ ] Move 13 obsolete test files
- [ ] Create ARCHIVE_README.md documenting why

### Phase 2: Create Plugin Tests (Complete in 2-3 hours)
- [ ] 4 mock test files (Scope, IQ, PID, ASG)
- [ ] 4 hardware test files
- [ ] Multi-plugin coordination test
- [ ] All tests pass

### Phase 3: Run Full Suite (Complete in 30 min)
- [ ] Mock tests: All pass (< 1 min total)
- [ ] Hardware tests: All pass (5-10 min total)
- [ ] No test conflicts or resource leaks
- [ ] 100% success rate

### Phase 4: Documentation (Complete in 30 min)
- [ ] Update README testing section
- [ ] Update TESTING.md with new structure
- [ ] Document test execution commands
- [ ] Add CI/CD recommendations

## Execution Plan

1. **Archive obsolete tests** (30 min)
2. **Create Scope IPC tests** - mock + hardware (30 min)
3. **Create IQ IPC tests** - mock + hardware (30 min)
4. **Create PID IPC tests** - mock + hardware (30 min)
5. **Create ASG IPC tests** - mock + hardware (30 min)
6. **Create multi-plugin test** (30 min)
7. **Run full suite** - validate all pass (30 min)
8. **Update documentation** (30 min)

**Total Estimated Time**: 4 hours

## Key Insights

### Why Archive Old Tests?
- Test OLD plugin architecture (direct PyRPLManager)
- Do NOT test shared_pyrpl_manager
- Cause confusion about what's current
- May fail due to architectural changes

### Why New Tests Needed?
- Must test WITHIN PyMoDAQ ecosystem
- Old tests bypass PyMoDAQ plugin lifecycle
- Need to verify base class compliance
- Must test shared manager with multiple plugins

### Critical Testing Principle
**"Test the system as it will be used"** - All tests must instantiate actual PyMoDAQ plugin classes and exercise them through their PyMoDAQ interfaces, not bypass with direct API calls.

## Commands

### Run Mock Tests Only
```bash
uv run pytest tests/test_*_mock.py -v
```

### Run Hardware Tests Only
```bash
export PYRPL_TEST_HOST=100.107.106.75
uv run pytest tests/test_*_hardware.py -v -s
```

### Run All Tests
```bash
uv run pytest tests/ -v --ignore=tests/archive/
```

### Run Specific Plugin
```bash
uv run pytest tests/test_plugin_ipc_scope_*.py -v
```
