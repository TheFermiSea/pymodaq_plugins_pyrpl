# Architectural Fix Summary

**Date:** 2025-10-07
**Issue:** Config system misuse for plugin parameter defaults
**Solution:** Implement proper PyMoDAQ pattern with static params

---

## Problem Identified

### Anti-Pattern (Before Fix)

PyRPL plugins were using config files as the source for parameter defaults:

```python
# WRONG PATTERN - ASG/PID plugins before fix
def get_asg_parameters():
    config = get_pyrpl_config()  # Loads from disk
    connection_config = config.get_connection_config()
    default_hostname = connection_config.get('default_hostname', '100.107.106.75')

    return [
        {'title': 'RedPitaya Host:', 'name': 'redpitaya_host',
         'value': default_hostname}  # Dynamic from config!
    ]

class DAQ_Move_PyRPL_ASG(DAQ_Move_base):
    params = get_asg_parameters() + comon_parameters_fun(...)
```

**Issues:**
1. ❌ Config file values override parameter defaults
2. ❌ Creates "hidden state" - users can't see what defaults will be used
3. ❌ Config has priority over code fallbacks
4. ❌ Violates PyMoDAQ's "GUI-first" design principle
5. ❌ Makes debugging difficult
6. ❌ Reduces reproducibility

### Correct Pattern (After Fix)

```python
# CORRECT PATTERN - Static params
class DAQ_Move_PyRPL_ASG(DAQ_Move_base):
    # Static parameters with hardcoded defaults
    params = [
        {'title': 'Connection Settings', 'name': 'connection_settings', 'type': 'group', 'children': [
            {'title': 'RedPitaya Host:', 'name': 'redpitaya_host', 'type': 'str',
             'value': '100.107.106.75', 'tip': 'Red Pitaya hostname or IP address'},
            # ... more params
        ]},
        # ... more groups
    ] + comon_parameters_fun(...)
```

**Benefits:**
1. ✅ All defaults visible in code (version controlled)
2. ✅ No hidden state from config files
3. ✅ Users modify in GUI, saved to presets (proper PyMoDAQ flow)
4. ✅ Config files only for package-level settings
5. ✅ Reproducible and predictable behavior

---

## Changes Made

### 1. ASG Plugin (`daq_move_PyRPL_ASG.py`)

**Removed:**
- `get_asg_parameters()` function (lines 72-152)

**Changed:**
- Converted `params` to static list with hardcoded defaults
- Hostname: `100.107.106.75` (hardcoded)
- All signal parameters now have static defaults

### 2. PID Plugin (`daq_move_PyRPL_PID.py`)

**Removed:**
- `get_pid_parameters()` function (lines 56-141)

**Changed:**
- Converted `params` to static list with hardcoded defaults
- Hostname: `100.107.106.75` (hardcoded)
- PID gains now have static defaults (P=0.1, I=0.01, D=0.0)

### 3. Config System (`utils/config.py`)

**Simplified `DEFAULT_PYRPL_CONFIG`:**

Before (includes plugin parameters):
```python
DEFAULT_PYRPL_CONFIG = {
    'connection': {
        'default_hostname': '100.107.106.75',  # ❌ Plugin parameter!
        'connection_timeout': 10.0,
        # ...
    },
    'hardware': {
        'pid_default_gains': {...},  # ❌ Plugin parameter!
        'asg_defaults': {...},       # ❌ Plugin parameter!
        # ...
    },
    # ... more plugin-specific settings
}
```

After (package-level settings only):
```python
DEFAULT_PYRPL_CONFIG = {
    'logging': {
        'enable_debug_logging': False,
        'log_hardware_communications': False,
        'log_file_rotation': True,
        'max_log_files': 10,
        'log_level': 'INFO'
    },
    'performance': {
        'thread_pool_size': 4,
        'connection_pool_max': 5,
        'cache_timeout': 300
    },
    'paths': {
        'config_dir': None,
        'log_dir': None,
        'cache_dir': None
    }
}
```

**Removed Methods:**
- `get_connection_config()`
- `get_hardware_config()`
- `get_acquisition_config()`
- `get_ui_config()`
- `get_default_hostname()`
- `set_default_hostname()`
- `get_pid_defaults()`
- `update_recent_hostname()`
- `get_recent_hostnames()`

**Added Methods:**
- `get_logging_config()`
- `get_performance_config()`
- `get_paths_config()`
- `is_debug_logging_enabled()`
- `enable_debug_logging()`
- `get_log_level()`

### 4. Config File (`/Library/Application Support/.pymodaq/pymodaq_plugins_pyrpl.toml`)

**Updated to simplified structure:**
```toml
# PyMoDAQ PyRPL Plugin Configuration
# This file contains PACKAGE-LEVEL settings only
# Plugin parameters (hostnames, gains, etc.) are defined in plugin classes
# and configured via PyMoDAQ GUI (saved to presets)

[logging]
enable_debug_logging = false
log_hardware_communications = false
log_file_rotation = true
max_log_files = 10
log_level = "INFO"

[performance]
thread_pool_size = 4
connection_pool_max = 5
cache_timeout = 300

[paths]
# Paths are auto-detected if not specified
```

---

## Verification

### Code Changes Verified:
- ✅ `get_asg_parameters()` removed from ASG plugin
- ✅ `get_pid_parameters()` removed from PID plugin
- ✅ ASG `params` now static with hardcoded defaults
- ✅ PID `params` now static with hardcoded defaults
- ✅ Config system simplified to package-level settings only
- ✅ Config file updated to simplified structure

### Expected Behavior:
1. **Plugin Discovery:** Plugins will be discovered normally via entry points
2. **Parameter Display:** All parameters visible in PyMoDAQ GUI with correct defaults
3. **Configuration Flow:**
   - User opens plugin in PyMoDAQ Dashboard
   - Sees default hostname: `100.107.106.75`
   - Can modify in GUI
   - Changes saved to **preset file** (NOT config file)
   - Next load uses preset values (user's last settings)
4. **Config File Purpose:**
   - Only affects package-level behavior (logging, performance)
   - Does NOT affect plugin parameter defaults
   - Cannot create "hidden state" for instrument settings

---

## Files Cleaned Up

Removed temporary analysis files:
- `/tmp/proper_plugin_pattern.md` - Analysis artifact
- `test_plugin_validation.py` - Temporary validation script
- `test_hostname_fix.py` - Temporary hostname verification
- `DEEP_ANALYSIS_REPORT.md` - Deep analysis report
- `PLUGIN_VERIFICATION_REPORT.md` - Plugin structure verification

---

## Testing Recommendations

### 1. PyMoDAQ Discovery Test
```bash
# Verify plugins are discovered
pymodaq_plugin_manager -l
# Should show: DAQ_Move_PyRPL_ASG, DAQ_Move_PyRPL_PID, DAQ_1DViewer_PyRPL_Scope
```

### 2. Parameter Test (PyMoDAQ Dashboard)
1. Open PyMoDAQ Dashboard
2. Add "DAQ_Move_PyRPL_ASG" actuator
3. Check "Connection Settings" → "RedPitaya Host"
4. Should show: `100.107.106.75` (hardcoded default)
5. Modify to different value
6. Save preset
7. Close and reopen
8. Should show YOUR modified value (from preset), not config file

### 3. Hardware Test
- Mock mode: Should work identically
- Hardware mode: Should connect to `100.107.106.75` (or user's preset value)

---

## Architectural Principles

### Proper PyMoDAQ Pattern
1. **Plugin Parameters:**
   - Defined as static `params` class variable
   - Hardcoded defaults in code (version controlled)
   - Users modify via GUI
   - Saved to preset files (user-specific)
   - NO dependency on config files

2. **Config Files:**
   - ONLY for package/application-level settings
   - Logging configuration
   - Performance tuning
   - Path overrides
   - NOT for instrument-specific parameters

3. **User Flow:**
   ```
   Code (defaults) → GUI (user modifies) → Preset (user saves) → GUI (loads preset)
   ```

   NOT:
   ```
   Config file (loads) → Code (overrides) → GUI (shows value) ❌
   ```

---

## References

**Correct Pattern Examples:**
- `pymodaq_plugins_mock/daq_move_plugins/daq_move_Mock.py` - Reference implementation
- `daq_1Dviewer_PyRPL_Scope.py` - Already correct (static params)

**Key Insight from Analysis:**
> "The config system design prioritizes disk state over code defaults. When a config key EXISTS in the loaded config, the fallback value in `get()` is NEVER used. This creates unpredictable behavior when config files contain stale data."

---

## Status

✅ **Architectural Fix Complete**

All plugins now follow PyMoDAQ's proper pattern:
- Static parameters with hardcoded defaults
- No config file dependency for parameters
- Config system simplified to package-level settings only
- Clean separation of concerns

**Ready for hardware testing with Red Pitaya at 100.107.106.75**
