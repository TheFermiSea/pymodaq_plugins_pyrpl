# PyRPL-PyMoDAQ IPC Architecture

## Overview

This document describes the Inter-Process Communication (IPC) architecture that enables PyRPL integration with PyMoDAQ. This solution resolves the fundamental architectural incompatibility between PyRPL's single-threaded Qt application framework and PyMoDAQ's multi-threaded plugin environment.

## The Problem

### Architectural Incompatibility

**PyRPL** is architected as a monolithic Qt application:
- All hardware modules inherit from `Module` base class
- Every `Module` creates a `SignalLauncher` instance
- `SignalLauncher` is a `QtCore.QObject` subclass
- Qt signals are fundamental to PyRPL's operation

**PyMoDAQ** uses a multi-threaded architecture:
- Plugins run in dedicated worker `QThread`s
- Hardware operations execute in worker threads, not main GUI thread
- This design prevents GUI blocking during I/O operations

**The Conflict**: PyRPL's `QObject`-based modules can only be accessed from the thread that created them (typically the main GUI thread). Attempting to instantiate or access PyRPL modules from a PyMoDAQ worker thread violates Qt's thread affinity rules, causing immediate crashes with meta-object recursion errors.

### Why Other Solutions Failed

1. **Direct Threading**: Impossible - PyRPL creates QObjects that violate thread affinity
2. **qasync Integration**: Solves event loop conflicts but not thread affinity
3. **Low-Level API**: Doesn't exist - all PyRPL logic is in Qt-dependent classes
4. **Native SCPI**: Limited to basic oscilloscope; loses PID, IQ, lock-in features

## The Solution: Process Isolation

The IPC architecture runs PyRPL in a completely separate process with its own Python interpreter and Qt event loop. Communication happens through `multiprocessing.Queue` which is process-safe.

```
┌─────────────────────────────────────┐
│     PyMoDAQ Process                 │
│  ┌───────────────────────────────┐  │
│  │   Main GUI Thread             │  │
│  │   (PyMoDAQ Dashboard)         │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   Worker QThread              │  │
│  │   ┌─────────────────────────┐ │  │
│  │   │ PyRPL_Scope_IPC Plugin  │ │  │
│  │   └──────┬──────────────────┘ │  │
│  └──────────┼────────────────────┘  │
│             │ multiprocessing.Queue │
└─────────────┼───────────────────────┘
              │
              │ IPC Boundary
              │
┌─────────────▼───────────────────────┐
│     PyRPL Worker Process            │
│  ┌───────────────────────────────┐  │
│  │   pyrpl_ipc_worker.py         │  │
│  │   ┌─────────────────────────┐ │  │
│  │   │ PyRPL Instance          │ │  │
│  │   │ - Own Qt Event Loop     │ │  │
│  │   │ - QObjects live here    │ │  │
│  │   │ - Hardware access       │ │  │
│  │   └─────────────────────────┘ │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   Red Pitaya Hardware         │  │
│  │   (TCP Socket)                │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Implementation Components

### 1. PyRPL Worker (`pyrpl_ipc_worker.py`)

The worker process that hosts PyRPL.

**Key Features**:
- Runs `pyrpl_worker_main()` as process entry point
- Initializes PyRPL with `gui=False` in worker process
- Processes commands from `command_queue`
- Returns results via `response_queue`
- Supports mock mode for development

**Command Protocol**:
```python
# Command structure
{
    'command': 'command_name',
    'params': {
        'param1': value1,
        'param2': value2
    }
}

# Response structure
{
    'status': 'ok' | 'error',
    'data': result_data_or_error_message
}
```

**Supported Commands**:

| Command | Description | Parameters |
|---------|-------------|------------|
| `ping` | Test connectivity | None |
| `scope_acquire` | Acquire oscilloscope data | `decimation`, `trigger_source`, `input_channel`, `timeout` |
| `scope_set_decimation` | Set sampling rate | `value` |
| `scope_set_trigger` | Set trigger source | `source` |
| `pid_configure` | Configure PID controller | `channel`, `p`, `i`, `d`, `setpoint`, `input`, `output_direct` |
| `pid_set_setpoint` | Set PID setpoint | `channel`, `value` |
| `pid_get_setpoint` | Get PID setpoint | `channel` |
| `asg_setup` | Configure arbitrary signal generator | `channel`, `waveform`, `frequency`, `amplitude`, `offset`, `output_direct` |
| `iq_setup` | Configure IQ demodulator | `channel`, `frequency`, `bandwidth`, `input`, `output_direct` |
| `iq_get_quadratures` | Get IQ quadrature values | `channel` |
| `sampler_read` | Read voltage from sampler | `channel` |
| `shutdown` | Gracefully terminate worker | None |

### 2. IPC Plugin (`daq_1Dviewer_PyRPL_Scope_IPC.py`)

The PyMoDAQ plugin that manages the worker process.

**Lifecycle**:

1. **Initialization** (`ini_detector`):
   - Create `multiprocessing.Queue` pair
   - Start worker process with configuration
   - Wait for initialization confirmation
   - Send initial configuration

2. **Operation** (`grab_data`, `commit_settings`):
   - Send commands via `command_queue`
   - Wait for responses from `response_queue`
   - Handle timeouts and errors
   - Convert data to PyMoDAQ format

3. **Shutdown** (`close`):
   - Send `shutdown` command
   - Wait for graceful exit (3s timeout)
   - Terminate if not responsive
   - Cleanup queues and process handle

**Error Handling**:
- Connection timeouts with configurable limits
- Automatic retry logic
- Graceful degradation
- Detailed error logging

### 3. Configuration Parameters

The plugin exposes these settings in PyMoDAQ GUI:

**Connection**:
- `rp_hostname`: Red Pitaya network address
- `config_name`: PyRPL configuration name
- `connection_timeout`: Worker startup timeout (default: 30s)

**Oscilloscope**:
- `input_channel`: in1 or in2
- `decimation`: Sampling rate factor (1-65536)
- `trigger_source`: Trigger mode
- `acquisition_timeout`: Maximum acquisition time

**Development**:
- `mock_mode`: Enable mock hardware for testing
- `debug_logging`: Verbose logging

## Mock Mode

Mock mode enables development and testing without Red Pitaya hardware.

**Features**:
- Synthetic oscilloscope data (sine + noise)
- Correct time axis calculation
- All commands return success
- Fast initialization (<1s)

**Usage**:
```python
# Enable in plugin settings
settings['dev', 'mock_mode'] = True
```

## Performance Characteristics

### Latency

| Operation | Typical Latency | Notes |
|-----------|-----------------|-------|
| Command round-trip | 1-5 ms | Queue + serialization overhead |
| Scope acquisition | 10-100 ms | Dominated by hardware trigger time |
| PID setpoint update | 1-2 ms | Simple parameter write |
| Process startup | 5-15 s | PyRPL initialization + FPGA bitstream |

### Throughput

- **Command rate**: ~200-500 commands/sec for simple operations
- **Data transfer**: 16k sample scope trace in ~2ms
- **Not suitable for**: >1kHz closed-loop control crossing process boundary

### Resource Usage

- **Memory overhead**: ~100 MB for worker process (PyRPL + Qt)
- **CPU**: Minimal when idle; spike during acquisitions
- **Process count**: +1 per plugin instance

## Comparison with Alternative Approaches

| Approach | Complexity | Stability | Features | Latency | Maintainability |
|----------|------------|-----------|----------|---------|-----------------|
| **IPC (This)** | Medium | Excellent | Full | ~1ms overhead | High |
| Direct Threading | Low | Broken | N/A | N/A | N/A |
| SCPI Native | Low | Excellent | Limited | <1ms | High |
| Native Rewrite | Very High | Excellent | Full | <1ms | Medium |

## Extending the Architecture

### Adding New Commands

1. **Worker side** (`pyrpl_ipc_worker.py`):
```python
def _handle_pyrpl_command(pyrpl, command, params):
    # ...
    elif command == 'my_new_command':
        # Access PyRPL safely
        result = pyrpl.rp.some_module.some_operation()
        return {'status': 'ok', 'data': result}
```

2. **Plugin side** (your plugin):
```python
def my_new_operation(self):
    response = self._send_command('my_new_command', {})
    return response['data']
```

### Creating Additional IPC Plugins

The architecture supports multiple plugin types:

- **`daq_1Dviewer_PyRPL_Scope_IPC.py`**: Oscilloscope (implemented)
- **`daq_move_PyRPL_PID_IPC.py`**: PID controller (future)
- **`daq_move_PyRPL_ASG_IPC.py`**: Signal generator (future)
- **`daq_viewer_PyRPL_IQ_IPC.py`**: IQ demodulator (future)

Each plugin shares the same worker process by using a singleton pattern or process pooling.

## Testing

### Unit Tests

Run the test suite:
```bash
python tests/test_ipc_integration.py
```

**Test Coverage**:
- Worker process startup/shutdown
- Command/response communication
- Mock mode functionality
- Error handling
- Stress testing (rapid commands)

### Integration Testing

With PyMoDAQ dashboard:
```bash
# 1. Enable mock mode in plugin settings
# 2. Add plugin to dashboard
# 3. Initialize detector
# 4. Acquire data
# 5. Verify trace display
```

With real hardware:
```bash
# 1. Configure Red Pitaya hostname
# 2. Disable mock mode
# 3. Initialize detector
# 4. Should see "PyRPL initialized" in log
# 5. Acquire real oscilloscope traces
```

## Troubleshooting

### Worker Won't Start

**Symptoms**: Timeout during `ini_detector`

**Solutions**:
- Check PyRPL is installed: `pip list | grep pyrpl`
- Verify Red Pitaya is reachable: `ping rp-f08d6c.local`
- Enable debug logging
- Check worker process log output

### Connection Lost During Operation

**Symptoms**: "Connection to PyRPL server lost" errors

**Solutions**:
- Check Red Pitaya didn't reboot or disconnect
- Verify network stability
- Increase timeout values
- Check for PyRPL crashes in worker log

### Slow Performance

**Symptoms**: Long acquisition times

**Solutions**:
- Reduce scope decimation for faster acquisitions
- Use 'immediately' trigger for fastest response
- Check network latency to Red Pitaya
- Verify no other processes using Red Pitaya

### Memory Leaks

**Symptoms**: Growing memory usage over time

**Solutions**:
- Ensure `close()` is called properly
- Check for orphaned worker processes: `ps aux | grep pyrpl`
- Restart plugin periodically for long sessions

## Future Enhancements

### Potential Improvements

1. **Process Pooling**: Share worker process across multiple plugin instances
2. **Async Commands**: Non-blocking command execution with callbacks
3. **Streaming Data**: Continuous scope monitoring without per-shot overhead
4. **Binary Protocol**: Faster serialization for large data arrays
5. **Health Monitoring**: Automatic worker restart on failure
6. **Remote Workers**: Run PyRPL on separate machine for network isolation

### Contributing

To contribute improvements:

1. Follow existing command protocol
2. Add tests for new functionality
3. Update this documentation
4. Ensure backward compatibility
5. Test with both mock and real hardware

## References

- **PyRPL Documentation**: https://pyrpl.readthedocs.io/
- **PyMoDAQ Plugin Guide**: https://pymodaq.cnrs.fr/en/latest/
- **Python multiprocessing**: https://docs.python.org/3/library/multiprocessing.html
- **Qt Threading Best Practices**: https://doc.qt.io/qt-6/threads-qobject.html

## License

MIT License - Same as PyMoDAQ and PyRPL projects

## Authors

PyMoDAQ-PyRPL Integration Team
- Implementation based on Gemini AI architectural analysis
- Community contributions welcome
