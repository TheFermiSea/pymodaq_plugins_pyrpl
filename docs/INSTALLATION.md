# Installation Guide

This guide provides step-by-step instructions for installing and setting up the PyMoDAQ PyRPL plugin for Red Pitaya STEMlab devices.

## Quick Start

**For users who want to get started immediately:**

1. **Install the plugin:**
   ```bash
   pip install pymodaq_plugins_pyrpl
   ```

2. **Install PyRPL:**
   ```bash
   # Use the provided script (recommended)
   ./install-pyrpl
   ```

3. **Test with mock mode** (no hardware required):
   ```bash
   python -m pymodaq.dashboard
   # Add PyRPL plugins with mock_mode: True
   ```

4. **Connect real hardware** (optional):
   - Set your Red Pitaya hostname: `rp-f08d6c.local` (tested configuration)
   - Set mock_mode: False

## Detailed Installation

### Prerequisites

Before installing the plugin, ensure you have:

- **Python 3.8+** (tested with 3.8, 3.9, 3.10, 3.11, 3.12)
- **PyMoDAQ 5.0.0+**
- **Git** (for source installation)
- **Network access** (for Red Pitaya connection)

### Operating System Support

| OS | Status | Notes |
|---|---|---|
| **Linux** | ✅ **Recommended** | Ubuntu 20.04/22.04 LTS tested |
| **Windows** | ✅ Supported | Windows 10+ |
| **macOS** | ✅ Supported | macOS 10.15+ |

### Step 1: Install PyMoDAQ Framework

If you don't have PyMoDAQ installed:

```bash
pip install pymodaq[complete]
```

Verify installation:
```bash
python -c "import pymodaq; print(f'PyMoDAQ version: {pymodaq.__version__}')"
```

### Step 2: Install PyMoDAQ PyRPL Plugin

Choose one installation method:

#### Option A: From PyPI (Recommended)

```bash
pip install pymodaq_plugins_pyrpl
```

#### Option B: From Source (Development)

```bash
git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
cd pymodaq_plugins_pyrpl
pip install -e .
```

#### Option C: Using uv (Modern Package Manager)

```bash
git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
cd pymodaq_plugins_pyrpl
uv sync
```

### Step 3: Install PyRPL Library

The PyRPL library is required for Red Pitaya communication. Choose the installation method that works best for your system:

#### Method 1: Automated Script (Recommended)

```bash
# Navigate to plugin directory
cd pymodaq_plugins_pyrpl

# Run installation script
./install-pyrpl
```

#### Method 2: Python Module

```bash
python src/pymodaq_plugins_pyrpl/install_pyrpl.py
```

#### Method 3: Manual Installation

```bash
# Install PyRPL with dependencies
pip install --no-deps pyrpl>=0.9.3.0
pip install nose paramiko pyyaml scp numpy pandas scipy pyqtgraph qtpy PyQt5 quamash
```

### Step 4: Verify Installation

1. **Check plugin is installed:**
   ```bash
   pip list | grep pymodaq_plugins_pyrpl
   ```

2. **Test PyRPL import:**
   ```bash
   python -c "import pyrpl; print('PyRPL OK')"
   ```

3. **Verify plugin loading:**
   ```bash
   python -c "
   from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
   print('Plugin loading: OK')
   "
   ```

4. **Run plugin tests:**
   ```bash
   cd pymodaq_plugins_pyrpl
   python -m pytest tests/ -k "test_mock"  # Mock tests only
   ```

## Hardware Setup

### Red Pitaya Network Configuration

1. **Connect Red Pitaya to your network** via Ethernet

2. **Find Red Pitaya IP address:**
   ```bash
   # Common default hostnames:
   ping rp-f08d6c.local  # Verified working configuration
   ping 192.168.1.100    # Common default IP
   ```

3. **Configure static IP (recommended):**

   **Via Web Interface:**
   - Open web browser: `http://rp-f08d6c.local` or `http://[IP_ADDRESS]`
   - Go to System → Network
   - Set static IP configuration

   **Via SSH:**
   ```bash
   ssh root@rp-f08d6c.local
   # Edit network configuration
   nano /opt/redpitaya/www/conf/network.conf
   ```

4. **Test connection:**
   ```bash
   # Test network connectivity
   ping rp-f08d6c.local

   # Test PyRPL connection
   python -c "
   import pyrpl
   rp = pyrpl.Pyrpl(hostname='rp-f08d6c.local', config='test')
   print('Red Pitaya connection: OK')
   rp.close()
   "
   ```

### PyMoDAQ Configuration

1. **Launch PyMoDAQ Dashboard:**
   ```bash
   python -m pymodaq.dashboard
   ```

2. **Add PyRPL plugins:**
   - Click "Add" → "Move" → "DAQ_Move_PyRPL_PID"
   - Click "Add" → "Detector" → "DAQ_0DViewer_PyRPL"

3. **Configure connection:**
   - Set **RedPitaya Host**: `rp-f08d6c.local` (or your IP)
   - Set **mock_mode**: `False` (for real hardware)
   - Configure channels and parameters

## Troubleshooting

### Common Installation Issues

**PyRPL Installation Fails:**
```bash
# Try with explicit Qt version
pip install PyQt5==5.15.6
pip install pyrpl>=0.9.3.0
```

**Import Errors:**
```bash
# Check Python environment
python -c "import sys; print(sys.path)"

# Reinstall in development mode
pip uninstall pymodaq_plugins_pyrpl
pip install -e .
```

**Plugin Not Found in PyMoDAQ:**
```bash
# Check entry points
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('pymodaq.plugins'):
    if 'pyrpl' in ep.name.lower():
        print(f'Found: {ep.name} -> {ep.module_name}')
"
```

### Hardware Connection Issues

**Cannot Connect to Red Pitaya:**
1. Check network connectivity: `ping rp-f08d6c.local`
2. Try IP address instead of hostname
3. Check firewall settings
4. Ensure SSH is enabled on Red Pitaya

**PyRPL Connection Errors:**
1. Use mock mode for testing: `mock_mode: True`
2. Check PyRPL version: `pip list | grep pyrpl`
3. Try different configuration name: `config_name: 'test_config'`

### Python Version Compatibility

**Python 3.12 Issues:**
The plugin includes automatic fixes for Python 3.12+ compatibility:
- `collections.Mapping` → `collections.abc.Mapping`
- `np.complex` → `complex`
- Qt timer float/int conversion

**Qt Version Conflicts:**
```bash
# Use PyQt5 for best compatibility
pip install PyQt5
```

## Development Setup

For developers who want to contribute or modify the plugin:

1. **Clone and setup development environment:**
   ```bash
   git clone https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl.git
   cd pymodaq_plugins_pyrpl

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows

   # Install in development mode
   pip install -e .[dev]
   ```

2. **Run tests:**
   ```bash
   # All tests
   python -m pytest tests/

   # Mock tests only (no hardware needed)
   pytest tests/ -k "not test_real_hardware"

   # Test parallel execution
   pytest -n auto tests/
   ```

3. **Code quality checks:**
   ```bash
   # Linting
   flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

## Next Steps

After successful installation:

1. **Try mock mode tutorial:** [Mock Mode Tutorial](MOCK_TUTORIAL.md)
2. **Read plugin documentation:** See `README.rst` for complete usage examples
3. **Explore hardware validation:** Check `COMPLETE_HARDWARE_VALIDATION.md`
4. **Join community:** PyMoDAQ forum at https://pymodaq.cnrs.fr/

## Getting Help

- **Documentation:** https://pymodaq.readthedocs.io/
- **Issues:** https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl/issues
- **PyMoDAQ Forum:** https://pymodaq.cnrs.fr/
- **PyRPL Documentation:** https://pyrpl.readthedocs.io/