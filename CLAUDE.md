# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pymodaq_plugins_pyrpl` integrates Red Pitaya STEMlab (via PyRPL library) into the PyMoDAQ framework for laser power stabilization. The plugin uses Red Pitaya's hardware PID controller for real-time control while providing PyMoDAQ's GUI, logging, and scanning capabilities.

## Development Commands

### Building and Testing
```bash
# Install in development mode
pip install -e .

# Run tests (basic structure validation)
python -m pytest tests/

# Run specific test file directly
python tests/test_plugin_package_structure.py

# Test a specific plugin (if hardware available)
python -m pytest tests/test_pyrpl_functionality.py -k test_real_hardware_connection

# Build package (uses hatch + custom metadata hook)
python -m build
```

## Architecture Overview

**Hybrid approach**: Uses Red Pitaya's hardware PID for real-time control + PyMoDAQ for GUI/logging.

**Key components**:
- `src/pymodaq_plugins_pyrpl/utils/pyrpl_wrapper.py` - centralized PyRPL communication
- `src/pymodaq_plugins_pyrpl/daq_move_plugins/` - PID controller plugins (setpoint control)
- `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/` - monitoring plugins (signal acquisition)  
- `src/pymodaq_plugins_pyrpl/models/PIDModelPyrpl.py` - existing PID model implementation

## Current Implementation Status

**Completed**:
- `PIDModelPyrpl.py` - Direct PyRPL PID model for PyMoDAQ PID extension
- Basic plugin structure from template

**To be implemented** (see `ai_docs/DETAILED_IMPLEMENTATION_GUIDE.md`):
- PyRPL wrapper utility
- DAQ_Move_PyRPL_PID plugin (PID setpoint control)
- DAQ_0DViewer_PyRPL plugin (signal monitoring)

## PyMoDAQ Plugin Conventions

**Plugin naming**: 
- Move plugins: `DAQ_Move_PluginName` class in `daq_move_PluginName.py`
- Viewer plugins: `DAQ_XDViewer_PluginName` class in `daq_XDviewer_PluginName.py`

**Required methods**:
- Move plugins: `ini_attributes`, `get_actuator_value`, `close`, `commit_settings`, `ini_stage`, `move_abs`, `move_home`, `move_rel`, `stop_motion`
- Viewer plugins: `ini_attributes`, `grab_data`, `close`, `commit_settings`, `ini_detector`

**Units**: Must use valid Pint units (validated by tests)

## Key PyRPL Integration Points

**Connection**: Use hostname (e.g., 'rp-f0a552.local' or IP address)
**PID control**: 
- `pid.setpoint` = target voltage
- `pid.p`, `pid.i` = gains
- `pid.input`, `pid.output_direct` = routing

**Voltage reading**: `rp.scope.voltage_in1` or `rp.sampler.in1`

## Development Notes

- Red Pitaya voltage range: ±1V (use external amplifiers/attenuators as needed)
- Always disable PID outputs before disconnecting (`pid.output_direct = 'off'`)
- The `pymodaq_plugins_template` package provides the structural template
- Both template and pyrpl-specific packages coexist in `src/`
- Package uses hatch build system with custom metadata hook (`hatch_build.py`)
- Entry points are dynamically generated from plugin structure

## File References

Detailed implementation guides are in `ai_docs/`:
- `DETAILED_IMPLEMENTATION_GUIDE.md` - comprehensive development roadmap
- `RED_PITAYA_PYRPL_INTEGRATION_ARCHITECTURE.md` - architectural overview

## Tooling for Shell Interactions

**Finding FILES**: use `fd` or built-in `find`
**Finding TEXT/strings**: use `rg` (ripgrep) - faster than grep
**Finding CODE STRUCTURE**: use `ast-grep` for semantic code search
**Selecting from multiple results**: pipe to `fzf` for interactive selection
**JSON processing**: use `jq`
**YAML/XML processing**: use `yq`

These tools significantly improve search efficiency and accuracy when available.