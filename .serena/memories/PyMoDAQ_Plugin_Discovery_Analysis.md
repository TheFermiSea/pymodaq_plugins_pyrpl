# PyMoDAQ Plugin Loading Pipeline Analysis

## Current Issue Summary
- `get_plugins('daq_move')` returns 9 plugins including URASHG plugins
- `get_plugins('daq_viewer')` returns 0 plugins despite discovery logs
- `ModulesManager().actuators` and `ModulesManager().detectors` both return empty lists
- PyMoDAQ logs show successful discovery but plugins don't appear in Dashboard UI

## Key Findings from PyMoDAQ Codebase Research

### 1. Plugin Discovery Architecture

**Entry Points System**: PyMoDAQ uses Python entry points for plugin discovery:
- Entry points defined in `pyproject.toml` under specific group names:
  - `pymodaq.move_plugins` for actuator plugins
  - `pymodaq.viewer_plugins` for detector plugins
- Discovery relies on `pkg_resources` or `importlib.metadata` entry point scanning

**Plugin Naming Convention Requirements**:
- Actuator Plugin Script: `daq_move_Xxxx`
- Actuator Plugin Class: `DAQ_Move_Xxxx`
- Detector Plugin Script: `daq_NDviewer_Xxxx` (N=0, 1, 2)
- Detector Plugin Class: `DAQ_NDViewer_Xxxx`

### 2. Discovery Pipeline Architecture

**Two-Layer System Identified**:
1. **`get_plugins()` Function**: Low-level entry point discovery
   - Scans entry points and returns plugin classes
   - Works independently of UI layer
   - Used for basic plugin enumeration

2. **`ModulesManager` Class**: High-level plugin management
   - Manages instantiation and lifecycle of plugin modules
   - Responsible for UI integration and Dashboard display
   - Contains `.actuators` and `.detectors` attributes for active modules

### 3. Critical Pipeline Components

**ModulesManager Responsibilities**:
- Manages various PyMoDAQ modules (DAQ movers and viewers)
- Handles instantiation, configuration, and lifecycle
- Acts as bridge between discovered plugins and Dashboard UI
- Contains logic for converting discovered plugins into UI-ready modules

**Dashboard Integration**:
- Dashboard uses ModulesManager to populate actuator/detector lists
- Dashboard UI depends on ModulesManager's populated lists
- Dashboard menu "Preset Modes" creates XML configurations based on available modules

### 4. Identified Disconnect Points

**Plugin Discovery vs. UI Display Pipeline**:
```
Entry Points → get_plugins() → [SUCCESS: 9 move, 0 viewer plugins found]
                    ↓
               ModulesManager → [FAILURE: Empty lists]
                    ↓
               Dashboard UI → [RESULT: No plugins shown]
```

**Potential Failure Points**:
1. **Import Errors**: Plugins discovered but fail to import properly
2. **Class Validation**: Plugins found but don't meet ModulesManager's validation criteria
3. **Threading Issues**: UI thread not receiving module updates
4. **Preset Dependencies**: ModulesManager may require preset configuration to populate lists

### 5. PyMoDAQ 5.1.0a0 Known Issues

**Alpha Version Problems**:
- PyMoDAQ 5.1.0a0 has entry point parsing bugs
- Extension discovery specifically broken (treats `module:class` as single module name)
- Core plugin discovery may have similar parsing issues
- Alpha versions known for incomplete plugin integration

### 6. ModulesManager Integration Pattern

**Expected Flow**:
- ModulesManager should populate `.actuators` and `.detectors` during initialization
- These lists should be populated from successfully imported plugins
- Dashboard reads these lists to create UI elements
- Preset Manager uses these lists for configuration

**Current Failure Pattern**:
- Entry points discovered correctly (get_plugins works)
- ModulesManager fails to populate internal lists
- Dashboard sees empty module lists
- UI displays no available plugins

## Root Cause Hypothesis

**Primary Suspect**: PyMoDAQ 5.1.0a0 Alpha Version Issues
- Entry point parsing bugs affecting core plugin discovery
- ModulesManager may have incomplete integration with plugin discovery
- Alpha version instability affecting plugin-to-UI pipeline

**Secondary Issues**:
- Plugin validation failures in ModulesManager
- Missing preset configuration requirements
- Import/class instantiation errors not properly logged