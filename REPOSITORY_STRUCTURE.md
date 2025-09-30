# Repository Structure

Clean and organized structure for the PyMoDAQ PyRPL plugin.

## Directory Layout

```
pymodaq_plugins_pyrpl/
├── README.rst                  # Main project documentation
├── LICENSE                     # MIT License
├── pyproject.toml             # Package configuration
├── plugin_info.toml           # PyMoDAQ plugin metadata
├── uv.lock                    # UV package manager lockfile
│
├── AGENTS.md                  # AI agent instructions
├── REPOSITORY_STRUCTURE.md    # This file
│
├── src/                       # Source code
│   └── pymodaq_plugins_pyrpl/
│       ├── __init__.py
│       ├── daq_move_plugins/     # Actuator plugins
│       │   ├── daq_move_PyRPL_PID.py
│       │   └── daq_move_PyRPL_ASG.py
│       ├── daq_viewer_plugins/   # Detector plugins
│       │   ├── plugins_0D/
│       │   │   ├── daq_0Dviewer_PyRPL.py
│       │   │   └── daq_0Dviewer_PyRPL_IQ.py
│       │   └── plugins_1D/
│       │       └── daq_1Dviewer_PyRPL_Scope.py
│       ├── models/               # PID models
│       │   └── PIDModelPyrpl.py
│       ├── extensions/           # Dashboard extensions
│       └── utils/                # Utility modules
│           ├── pyrpl_wrapper.py        # Connection management
│           ├── pyrpl_fixes.py          # Bug fix module
│           ├── threading.py            # Thread utilities
│           ├── enhanced_mock_connection.py
│           ├── mock_simulation.py
│           └── demo_presets.py
│
├── tests/                     # Test suite
│   ├── conftest.py                   # Pytest configuration
│   ├── test_pyrpl_functionality.py   # Main test suite
│   ├── test_real_hardware_rp_f08d6c.py  # Hardware validation
│   ├── test_comprehensive_coverage.py
│   ├── test_integration_fixes.py
│   └── pyrpl_config/                 # Test configurations
│
├── docs/                      # Documentation
│   ├── README.md                     # Documentation index
│   ├── HARDWARE_TESTING.md          # Hardware test guide ⭐
│   ├── INSTALLATION.md              # Installation guide
│   ├── DEVELOPER_GUIDE.md           # Development guide
│   ├── MOCK_TUTORIAL.md             # Mock mode tutorial
│   └── CONTROL_THEORY_FOUNDATIONS.md
│
├── scripts/                   # Utility scripts
│   └── patch_pyrpl.py               # Automated PyRPL patcher ⭐
│
├── archive/                   # Historical files
│   ├── README.md                    # Archive documentation
│   ├── old_docs/                    # Superseded documentation
│   └── test_scripts/                # Development test scripts
│
├── development_history/       # Historical development files
│   └── README.md                    # Development notes
│
├── venv/                      # Python virtual environment
└── .venv/                     # Alternative venv location

```

⭐ = Most important files for new users

## Key Files

### User-Facing

- **README.rst** - Main project README with overview and quick start
- **docs/HARDWARE_TESTING.md** - Complete hardware setup and testing guide
- **docs/INSTALLATION.md** - Installation instructions
- **scripts/patch_pyrpl.py** - Automated bug fix patcher for PyRPL

### Development

- **AGENTS.md** - Instructions for AI agents working on the codebase
- **docs/DEVELOPER_GUIDE.md** - Architecture and development guide
- **tests/** - Comprehensive test suite
- **src/pymodaq_plugins_pyrpl/** - Plugin implementation

### Configuration

- **pyproject.toml** - Python package configuration (build, dependencies)
- **plugin_info.toml** - PyMoDAQ plugin metadata (entry points, features)
- **tests/conftest.py** - Pytest configuration and fixtures

## Source Code Organization

### Plugin Types

```
daq_move_plugins/          # Actuator plugins (control)
├── daq_move_PyRPL_PID.py    # PID setpoint control
└── daq_move_PyRPL_ASG.py    # Signal generator control

daq_viewer_plugins/        # Detector plugins (measurement)
├── plugins_0D/              # Scalar measurements
│   ├── daq_0Dviewer_PyRPL.py      # Voltage monitoring
│   └── daq_0Dviewer_PyRPL_IQ.py   # Lock-in amplifier
└── plugins_1D/              # Array measurements
    └── daq_1Dviewer_PyRPL_Scope.py  # Oscilloscope

models/                    # PID models
└── PIDModelPyrpl.py         # Direct hardware PID model

extensions/                # Dashboard extensions
└── (future extensions)

utils/                     # Shared utilities
├── pyrpl_wrapper.py         # Connection management & pooling
├── pyrpl_fixes.py           # PyRPL bug fixes
├── threading.py             # Thread-safe operations
└── mock_simulation.py       # Mock hardware simulation
```

### Utility Modules

- **pyrpl_wrapper.py** - `PyRPLManager` and `PyRPLConnection` classes
  - Connection pooling
  - Thread safety
  - Hardware/mock mode switching

- **pyrpl_fixes.py** - PyRPL bug fix module
  - ZeroDivisionError fix
  - IndexError fix
  - Applied automatically on import

- **threading.py** - Thread utilities
  - Thread-safe operations
  - Async/sync bridging

- **mock_simulation.py** - Mock hardware
  - Realistic signal simulation
  - Configurable waveforms
  - Noise models

## Documentation Organization

### Primary Docs (docs/)

1. **README.md** - Documentation index and navigation
2. **HARDWARE_TESTING.md** - Hardware setup, bugs, testing, troubleshooting
3. **INSTALLATION.md** - Installation for all platforms
4. **DEVELOPER_GUIDE.md** - Architecture, development workflow
5. **MOCK_TUTORIAL.md** - Using mock mode for development
6. **CONTROL_THEORY_FOUNDATIONS.md** - PID theory and algorithms

### Archive (archive/)

Historical and superseded files preserved for reference:

- **old_docs/** - Old documentation versions
  - HARDWARE_TEST_REPORT.md
  - HARDWARE_TEST_FINAL_STATUS.md
  - HARDWARE_VALIDATION.md

- **test_scripts/** - Development test scripts
  - test_hardware_connection.py
  - test_pyrpl_simple.py
  - test_pid_only.py
  - etc.

## Testing Structure

```
tests/
├── conftest.py                      # Pytest config, fixtures, markers
├── test_pyrpl_functionality.py      # Main test suite
├── test_real_hardware_rp_f08d6c.py # Hardware validation ⭐
├── test_comprehensive_coverage.py   # Coverage tests
├── test_integration_fixes.py        # Integration tests
└── pyrpl_config/                    # Test PyRPL configs
```

### Test Markers

- `@pytest.mark.mock` - Mock hardware tests (no hardware needed)
- `@pytest.mark.hardware` - Real hardware tests (requires PYRPL_TEST_HOST)
- `@pytest.mark.integration` - Integration tests with PyMoDAQ
- `@pytest.mark.slow` - Long-running tests

## Development Workflow

### For New Contributors

1. Read **README.rst** for project overview
2. Follow **docs/INSTALLATION.md** to set up environment
3. Read **docs/DEVELOPER_GUIDE.md** for architecture
4. Run tests: `pytest tests/` (mock tests run without hardware)
5. Make changes, add tests, update docs
6. Submit PR with description

### For Hardware Testing

1. Read **docs/HARDWARE_TESTING.md** thoroughly
2. Set up Red Pitaya network connection
3. Install PyRPL: `pip install --no-deps git+https://github.com/pyrpl-fpga/pyrpl.git`
4. Patch PyRPL: `python scripts/patch_pyrpl.py`
5. Set environment: `export PYRPL_TEST_HOST=<your_rp_ip>`
6. Run tests: `pytest tests/test_real_hardware_rp_f08d6c.py -m hardware`

### For Documentation Updates

1. Edit files in `docs/` directory
2. Update `docs/README.md` index if adding new files
3. Update main `README.rst` if changing key information
4. Keep `AGENTS.md` updated for AI agents

## File Naming Conventions

### Source Code

- **Plugins:** `daq_{move|viewer}_PyRPL_<Module>.py`
- **Models:** `<Name>ModelPyrpl.py`
- **Utils:** `lowercase_with_underscores.py`

### Documentation

- **Guides:** `UPPERCASE_WITH_UNDERSCORES.md`
- **Index:** `README.md`
- **Markdown format** for all docs

### Tests

- **Test files:** `test_<description>.py`
- **Fixtures:** `conftest.py`
- **Test functions:** `def test_<what_it_tests>():`

## Important Notes

### Do Not Modify

- `.git/` - Git repository data
- `venv/`, `.venv/` - Virtual environments (recreated on setup)
- `dist/` - Build artifacts (generated)
- `__pycache__/`, `*.pyc` - Python cache (auto-generated)
- `.pytest_cache/` - Pytest cache
- `uv.lock` - Package lockfile (managed by UV)

### Keep for AI Agents

- **AGENTS.md** - Agent-specific instructions
- **REPOSITORY_STRUCTURE.md** - This file
- **development_history/** - Historical context

### Archive Policy

Files moved to `archive/` when:
- Superseded by better documentation
- Experimental/one-time use
- Historical reference value
- Not part of current workflow

Never archive if:
- Used by CI/CD
- Referenced by current docs
- Part of public API
- Actively maintained

## Quick Reference

### Most Important Files for Users

1. `README.rst` - Start here
2. `docs/HARDWARE_TESTING.md` - Hardware setup
3. `scripts/patch_pyrpl.py` - Fix PyRPL bugs
4. `docs/INSTALLATION.md` - Installation

### Most Important Files for Developers

1. `AGENTS.md` - AI agent guidelines
2. `docs/DEVELOPER_GUIDE.md` - Architecture
3. `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py` - Core functionality
4. `tests/conftest.py` - Test configuration

### Quick Commands

```bash
# Install
pip install -e .

# Patch PyRPL
python scripts/patch_pyrpl.py

# Test (mock)
pytest tests/

# Test (hardware)
export PYRPL_TEST_HOST=100.107.106.75
pytest tests/ -m hardware

# Documentation
cd docs && ls -la
```

## Maintenance

This repository structure should be maintained to keep:
- Clean separation of concerns
- Clear documentation paths
- Easy navigation for new users
- Efficient workflow for developers
- Historical context preserved

Last updated: January 30, 2025
