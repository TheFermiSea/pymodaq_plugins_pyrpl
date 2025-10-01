# PyMoDAQ PyRPL Plugins

PyMoDAQ plugins for Red Pitaya control via PyRPL, enabling advanced signal processing, lock-in amplification, PID control, and arbitrary signal generation.

## Features

- **Shared Worker Architecture** - Single PyRPL instance shared across all plugins
- **Command Multiplexing** - Concurrent operations from multiple plugins without blocking
- **Hardware Modules Supported**:
  - 🔬 **Scope** - Oscilloscope waveform acquisition
  - 📊 **ASG** - Arbitrary signal generator  
  - 🎛️ **PID** - PID controller with multiple channels
  - 📡 **IQ** - Lock-in amplifier (I/Q demodulation)
  - 📈 **Sampler** - High-speed voltage sampling

## Quick Start

```python
from pymodaq_plugins_pyrpl.utils.shared_pyrpl_manager import get_shared_worker_manager

# Get shared manager (singleton)
mgr = get_shared_worker_manager()

# Start worker
config = {
    'hostname': '100.107.106.75',  # Your Red Pitaya IP
    'config_name': 'my_experiment',
    'mock_mode': False
}
mgr.start_worker(config)

# Read voltage from input
response = mgr.send_command('sampler_read', {'channel': 'in1'}, timeout=5.0)
print(f"Voltage: {response['data']} V")

# Acquire scope trace
response = mgr.send_command('scope_acquire', {
    'decimation': 64,
    'input_channel': 'in1',
    'trigger_source': 'immediately'
}, timeout=10.0)

# Cleanup
mgr.shutdown()
```

See [QUICK_START.md](QUICK_START.md) for complete examples.

## Documentation

### Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Quick start guide with examples
- **[COMMAND_MULTIPLEXING_SUMMARY.md](COMMAND_MULTIPLEXING_SUMMARY.md)** - Command multiplexing feature documentation

### Technical Documentation (docs/)
- **[INSTALLATION.md](docs/INSTALLATION.md)** - Installation instructions
- **[IPC_ARCHITECTURE.md](docs/IPC_ARCHITECTURE.md)** - IPC architecture overview
- **[ARCHITECTURE_REVIEW.md](docs/ARCHITECTURE_REVIEW.md)** - Command multiplexing architecture
- **[SHARED_WORKER_ARCHITECTURE.md](docs/SHARED_WORKER_ARCHITECTURE.md)** - Shared worker design
- **[THREADING_ARCHITECTURE.md](docs/THREADING_ARCHITECTURE.md)** - Threading model
- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** - Developer guide
- **[HARDWARE_TESTING.md](docs/HARDWARE_TESTING.md)** - Hardware testing procedures
- **[MOCK_TUTORIAL.md](docs/MOCK_TUTORIAL.md)** - Mock mode tutorial
- **[TROUBLESHOOTING_SSH_CONNECTION.md](docs/TROUBLESHOOTING_SSH_CONNECTION.md)** - SSH connection troubleshooting
- **[PYMODAQ_SETUP_GUIDE.md](docs/PYMODAQ_SETUP_GUIDE.md)** - PyMoDAQ setup guide

See [docs/README.md](docs/README.md) for complete documentation index.

## Requirements

- Python 3.10+
- PyMoDAQ 4.0+
- PyRPL
- Red Pitaya STEMlab 125-14 (or compatible)

## Installation

```bash
# Clone repository
git clone https://github.com/TheFermiSea/pymodaq_plugins_pyrpl.git
cd pymodaq_plugins_pyrpl

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Architecture

This plugin suite uses a **shared worker architecture** where all plugins communicate with a single PyRPL instance running in a separate process. This design:

- Prevents PyRPL instance conflicts
- Enables concurrent operations via UUID-based command multiplexing
- Isolates Qt event loops for stability
- Provides thread-safe command routing

See [docs/SHARED_WORKER_ARCHITECTURE.md](docs/SHARED_WORKER_ARCHITECTURE.md) for details.

## Testing

```bash
# Run all tests
uv run pytest

# Run specific test suites
uv run pytest tests/test_command_multiplexing.py  # Mock tests
uv run pytest tests/test_command_multiplexing_hardware.py  # Hardware tests
uv run pytest tests/test_pid_hardware.py  # PID hardware tests
```

## Key Features

### Command ID Multiplexing

Multiple plugins can send commands concurrently without blocking:

```python
import threading

def plugin_a():
    response = mgr.send_command('sampler_read', {'channel': 'in1'})
    
def plugin_b():
    response = mgr.send_command('sampler_read', {'channel': 'in2'})

# Both run concurrently without interference
t1 = threading.Thread(target=plugin_a)
t2 = threading.Thread(target=plugin_b)
t1.start(); t2.start()
t1.join(); t2.join()
```

### FPGA Bitstream

PyRPL requires loading its custom FPGA bitstream to the Red Pitaya. This happens automatically on first connection (~5-7 seconds). The bitstream enables PyRPL's advanced signal processing modules.

## Production Status

✅ **Production Ready**

- 15/15 tests passing (mock + hardware + PID)
- Concurrent operations validated
- Thread-safe implementation
- Comprehensive test coverage
- Hardware validation complete

## Known Limitations

1. **First Connection Time**: ~5-7 seconds for FPGA bitstream loading
2. **PyRPL Close Warning**: Harmless "no attribute 'close'" warning on shutdown
3. **Init Warnings**: "no pyrpl instance" warnings during FPGA load are normal

## Contributing

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for development guidelines.

## License

MIT License - see LICENSE file for details.

## Credits

Developed as part of PyMoDAQ plugin ecosystem.

## Support

- **Issues**: GitHub Issues
- **Documentation**: See docs/ directory
- **Historical Context**: See archive/ directory for development history

## Changelog

### Latest (Current)
- ✅ Command ID multiplexing for concurrent operations
- ✅ FPGA bitstream loading fix (critical)
- ✅ PID hardware support
- ✅ Comprehensive test suite (15/15 passing)
- ✅ Production-ready deployment

See git history for complete changelog.
