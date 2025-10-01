# Archived Tests - Pre-Shared Manager Architecture

**Date Archived**: October 1, 2025  
**Reason**: These tests target the OLD plugin architecture that does NOT use `shared_pyrpl_manager`

## Why These Tests Were Archived

### Architectural Change
In September 2025, the PyRPL plugin architecture was completely redesigned to use:
- **SharedPyRPLManager** - Single worker process shared across all plugins
- **Command ID Multiplexing** - UUID-based concurrent command routing
- **IPC Architecture** - Complete process isolation for Qt compatibility

### Old Architecture (Tested by These Files)
These archived tests target plugins that:
- Created individual PyRPL worker processes per plugin
- Used direct `PyRPLManager` wrapper class
- Had threading/Qt conflicts
- Lacked command multiplexing

### Current Architecture (NOT Tested Here)
Production plugins now:
- Share ONE `SharedPyRPLManager` instance
- Use `get_shared_worker_manager()` singleton
- Support concurrent operations via UUID command routing
- Have complete Qt isolation

## Archived Test Files

### Category: Old Plugin Tests
1. **test_real_hardware_rp_f08d6c.py** (917 lines)
   - Tests old PyRPLManager wrapper directly
   - Does not test SharedPyRPLManager
   - Tests deprecated plugin architecture

2. **test_pyrpl_functionality.py** (1,452 lines)
   - Extensive tests for old plugin classes
   - Custom mock implementations
   - Old wrapper and threading tests

3. **test_comprehensive_coverage.py** (631 lines)
   - Tests old mock system
   - Old plugin lifecycle
   - Deprecated demo presets

4. **test_unified_plugin_mock_connections.py** (398 lines)
   - Tests old plugin mock connections
   - Pre-IPC architecture

5. **test_mock_demonstration.py** (404 lines)
   - Old mock patterns demonstration
   - Not relevant to IPC architecture

6. **test_singleton_mock_instance.py** (398 lines)
   - Tests old singleton pattern
   - Superseded by SharedPyRPLManager

7. **test_integration_fixes.py** (327 lines)
   - Integration fixes for pre-IPC architecture
   - Issues no longer relevant

8. **test_hardware_environment.py** (404 lines)
   - Old hardware testing patterns
   - Superseded by command_multiplexing_hardware tests

9. **test_coordinated_simulation_integration.py** (517 lines)
   - Old coordinated simulation
   - Pre-IPC mock coordination

10. **test_integration.py** (90 lines)
    - Basic integration tests for old architecture

### Category: Connection Tests
11. **test_redpitaya_connection.py** (307 lines)
    - Direct Red Pitaya connection tests
    - Now handled by SharedPyRPLManager

### Category: Debugging Scripts
12. **test_asg_direct.py** (35 lines)
13. **test_asg_simple.py** (71 lines)
14. **test_asg_output2_loopback.py** (307 lines)
15. **test_scope_asg_concurrent.py** (122 lines)
16. **test_input2_sampler.py** (24 lines)
17. **test_diagnose_input2.py** (60 lines)
    - Various debugging scripts from development
    - Used to diagnose specific hardware issues
    - No longer needed with stable IPC architecture

**Total Archived**: 17 files, ~6,000 lines of code

## Current Test Suite

The active test suite now focuses on:

### Core Shared Manager Tests
- `test_command_multiplexing.py` - Mock mode multiplexing
- `test_command_multiplexing_hardware.py` - Hardware multiplexing
- `test_ipc_integration.py` - IPC worker core

### Plugin-Specific Tests (IPC Versions)
- `test_plugin_ipc_scope_mock.py` / `_hardware.py` - Scope plugin
- `test_plugin_ipc_iq_mock.py` / `_hardware.py` - IQ plugin
- `test_plugin_ipc_pid_mock.py` / `_hardware.py` - PID plugin
- `test_plugin_ipc_asg_mock.py` / `_hardware.py` - ASG plugin
- `test_pid_hardware.py` - PID hardware tests

### Integration Tests
- `test_multi_plugin_coordination_ipc.py` - Multi-plugin coordination

## Key Differences

### Old Tests (Archived)
```python
# Directly instantiate PyRPLManager
from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager

manager = PyRPLManager()
connection = manager.connect_device(hostname, config_name)
```

### New Tests (Current)
```python
# Use shared manager singleton
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

manager = get_shared_worker_manager()
manager.start_worker(config)
response = manager.send_command('scope_acquire', params, timeout=5.0)
```

## Migration Guide

If you need to understand old test patterns:

1. **Read archived tests** for historical context
2. **DO NOT run** archived tests - they will likely fail
3. **Refer to current tests** in `tests/` for correct patterns
4. **Use SharedPyRPLManager** for all new tests

## Documentation References

- **Architecture**: `docs/SHARED_WORKER_ARCHITECTURE.md`
- **IPC Details**: `docs/IPC_ARCHITECTURE.md`
- **Implementation**: `COMMAND_MULTIPLEXING_IMPLEMENTATION.md`
- **Testing Plan**: Memory `comprehensive_testing_plan_october_2025`

## Questions?

If you need to understand why a specific test was archived or how to test equivalent functionality in the new architecture, see:
- Current test examples in `tests/`
- `comprehensive_testing_plan_october_2025` memory
- Implementation docs in root directory

---
**Archive Created**: October 1, 2025  
**Archived By**: Factory AI Development Agent  
**Reason**: Architectural redesign to SharedPyRPLManager with command multiplexing
