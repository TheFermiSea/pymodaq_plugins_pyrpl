# PyMoDAQ v5 Import Compliance - Complete Reference Guide

## v5 Migration Overview

PyMoDAQ v5 introduced **modular package architecture** that breaks the monolithic `pymodaq` package into specialized components. This requires updating import statements throughout existing codebases.

## Complete Import Mapping Reference

### Core PyMoDAQ Components

| **Component** | **v4 Import** | **v5 Import** | **Priority** |
|---------------|---------------|---------------|--------------|
| **CustomApp** | `from pymodaq.utils.gui_utils import CustomApp` | `from pymodaq_gui.utils.custom_app import CustomApp` | **CRITICAL** |
| **ThreadCommand** | `from pymodaq.utils.daq_utils import ThreadCommand` | `from pymodaq_utils.daq_utils import ThreadCommand` | **CRITICAL** |
| **DataActuator** | `from pymodaq.utils.data import DataActuator` | `from pymodaq_data.datamodel.data_actuator import DataActuator` | **CRITICAL** |
| **DataWithAxes** | `from pymodaq.utils.data import DataWithAxes, Axis` | `from pymodaq_data.datamodel import DataWithAxes, Axis` | **CRITICAL** |
| **DataSource** | `from pymodaq_data.data import DataSource` | `from pymodaq_data.datamodel import DataSource` | **CRITICAL** |
| **Parameter** | `from pymodaq.utils.parameter import Parameter` | `from pymodaq_utils.parameter import Parameter` | **HIGH** |
| **Logger** | `from pymodaq.utils.logger import set_logger` | `from pymodaq_utils.logger import set_logger` | **HIGH** |
| **Config** | `from pymodaq.utils.config import Config` | `from pymodaq_utils.config import Config` | **HIGH** |
| **BaseEnum** | `from pymodaq.utils.enums import BaseEnum` | `from pymodaq_utils.enums import BaseEnum` | **MEDIUM** |

### Plugin Base Classes

| **Plugin Type** | **v4 Import** | **v5 Import** | **Notes** |
|-----------------|---------------|---------------|-----------|
| **Move Plugin** | `from pymodaq.control_modules.move_utility_classes import DAQ_Move_base` | `from pymodaq.control_modules.move_utility_classes import DAQ_Move_base` | **No change** |
| **Viewer Plugin** | `from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base` | `from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base` | **No change** |

### Data Structures (Critical Path Changes)

```python
# ❌ WRONG v5 paths (common mistakes)
from pymodaq_data.data import DataWithAxes, Axis, DataSource  # INCORRECT
from pymodaq.utils.data import DataToExport  # OLD v4 path

# ✅ CORRECT v5 paths  
from pymodaq_data.datamodel import DataWithAxes, Axis, DataSource, DataToExport
from pymodaq_data.datamodel.data_actuator import DataActuator
```

## Package Structure Dependencies

### Required Dependencies (v5)
```toml
# pyproject.toml dependencies
dependencies = [
    "pymodaq>=5.0.0",           # Core framework
    "pymodaq-gui",              # GUI components  
    "pymodaq-data",             # Data structures
    "pymodaq-utils",            # Utilities
]
```

### Entry Points Configuration (v5)
```toml
# Correct v5 entry points structure
[project.entry-points."pymodaq.plugins"]
package_name = "your_plugin_package"

[project.entry-points."pymodaq.move_plugins"]
"DAQ_Move_YourDevice" = "your_package.daq_move_plugins.daq_move_YourDevice:DAQ_Move_YourDevice"

[project.entry-points."pymodaq.viewer_plugins"]  
"DAQ_2DViewer_YourCamera" = "your_package.daq_viewer_plugins.plugins_2D.daq_2Dviewer_YourCamera:DAQ_2DViewer_YourCamera"

[project.entry-points."pymodaq.extensions"]
"YourExtension" = "your_package.extensions.your_extension:YourExtension"
```

## Migration Automation Scripts

### Critical Import Fixes Script
```bash
#!/bin/bash
# pymodaq_v5_migration.sh - Apply critical v5 import fixes

echo "🔧 Applying PyMoDAQ v5 import compliance fixes..."

# 1. Fix CustomApp imports (Extension loading)
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.gui_utils import CustomApp/from pymodaq_gui.utils.custom_app import CustomApp/g' {} \;

# 2. Fix ThreadCommand imports (Plugin communication)  
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.daq_utils import ThreadCommand/from pymodaq_utils.daq_utils import ThreadCommand/g' {} \;

# 3. Fix DataActuator imports (Actuator control)
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.data import DataActuator/from pymodaq_data.datamodel.data_actuator import DataActuator/g' {} \;

# 4. Fix Parameter imports (Settings management)
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.parameter import Parameter/from pymodaq_utils.parameter import Parameter/g' {} \;

# 5. Fix Logger imports  
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.logger import set_logger/from pymodaq_utils.logger import set_logger/g' {} \;

# 6. Fix Config imports
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.config import Config/from pymodaq_utils.config import Config/g' {} \;

# 7. Fix data structure imports (combined)
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.data import DataWithAxes, Axis/from pymodaq_data.datamodel import DataWithAxes, Axis/g' {} \;

# 8. Fix critical data path error (specific to some packages)
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq_data\.data import/from pymodaq_data.datamodel import/g' {} \;

# 9. Fix enum imports
find src/ -name "*.py" -exec sed -i \
  's/from pymodaq\.utils\.enums import BaseEnum/from pymodaq_utils.enums import BaseEnum/g' {} \;

echo "✅ Critical import fixes applied!"
```

### Configuration Cleanup Script
```bash
#!/bin/bash
# Remove v4 obsolete files

# Remove obsolete plugin_info.toml (v5 uses pyproject.toml only)
if [ -f "plugin_info.toml" ]; then
    echo "🗑️  Removing obsolete plugin_info.toml..."
    rm plugin_info.toml
fi

# Optional: Remove legacy code directories
if [ -d "legacy/" ] || [ -d "old/" ] || [ -d "*_v4/" ]; then
    echo "⚠️  Legacy directories found - manual review recommended"
fi

echo "🧹 Configuration cleanup completed!"
```

## Validation and Testing

### Import Validation Script
```python
#!/usr/bin/env python3
# test_v5_imports.py - Validate all critical v5 imports

def test_v5_imports():
    """Test all critical PyMoDAQ v5 imports"""
    
    critical_imports = [
        "from pymodaq_gui.utils.custom_app import CustomApp",
        "from pymodaq_utils.daq_utils import ThreadCommand", 
        "from pymodaq_data.datamodel.data_actuator import DataActuator",
        "from pymodaq_data.datamodel import DataWithAxes, Axis, DataSource",
        "from pymodaq_utils.parameter import Parameter",
        "from pymodaq_utils.logger import set_logger",
        "from pymodaq_utils.config import Config",
    ]
    
    results = []
    for import_stmt in critical_imports:
        try:
            exec(import_stmt)
            results.append(f"✅ {import_stmt}")
        except ImportError as e:
            results.append(f"❌ {import_stmt}: {e}")
    
    # Print results
    print("PyMoDAQ v5 Import Validation Results:")
    print("=" * 50)
    for result in results:
        print(result)
    
    # Overall status
    failed = [r for r in results if r.startswith("❌")]
    if failed:
        print(f"\n🚨 {len(failed)} import failures detected!")
        return False
    else:
        print(f"\n🎉 All {len(results)} critical imports successful!")
        return True

if __name__ == "__main__":
    success = test_v5_imports()
    exit(0 if success else 1)
```

### Plugin Discovery Test
```python
#!/usr/bin/env python3
# test_plugin_discovery.py - Verify plugin discovery works

def test_plugin_discovery():
    """Test that PyMoDAQ v5 can discover plugins"""
    
    try:
        from pymodaq.utils.daq_utils import get_plugins
        
        plugins = get_plugins()
        
        print("Plugin Discovery Results:")
        print("=" * 30)
        print(f"Move plugins found: {len(plugins.get('move', {}))}")
        for name in plugins.get('move', {}):
            print(f"  - {name}")
            
        print(f"Viewer plugins found: {len(plugins.get('viewer', {}))}")  
        for name in plugins.get('viewer', {}):
            print(f"  - {name}")
            
        print(f"Extensions found: {len(plugins.get('extensions', {}))}")
        for name in plugins.get('extensions', {}):
            print(f"  - {name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Plugin discovery failed: {e}")
        return False

if __name__ == "__main__":
    success = test_plugin_discovery()
    exit(0 if success else 1)
```

## Common Migration Issues & Solutions

### Issue 1: CustomApp Import Failure
**Problem**: Extension fails to load with `ImportError: cannot import name 'CustomApp'`
**Solution**: Update to `from pymodaq_gui.utils.custom_app import CustomApp`
**Impact**: Breaks extension loading completely

### Issue 2: Data Structure Path Error  
**Problem**: `ImportError: cannot import name 'DataSource' from 'pymodaq_data.data'`
**Solution**: Use `from pymodaq_data.datamodel import DataSource`
**Impact**: Breaks data handling and plugin functionality

### Issue 3: ThreadCommand Communication Failure
**Problem**: Plugin communication errors, status updates not working
**Solution**: Update to `from pymodaq_utils.daq_utils import ThreadCommand`
**Impact**: Breaks plugin→dashboard communication

### Issue 4: DataActuator Control Issues
**Problem**: Actuator movement commands fail
**Solution**: Use `from pymodaq_data.datamodel.data_actuator import DataActuator`  
**Impact**: Breaks hardware control completely

## Best Practices for v5 Compliance

### 1. Systematic Approach
- **Phase 1**: Fix CRITICAL imports first (CustomApp, ThreadCommand, DataActuator)
- **Phase 2**: Fix HIGH priority imports (Parameter, Logger, Config)
- **Phase 3**: Fix MEDIUM priority imports (enums, utilities)

### 2. Validation Strategy
- **Test imports** after each phase
- **Verify plugin discovery** works
- **Test basic functionality** with hardware (if available)
- **Check for deprecation warnings** in logs

### 3. Configuration Management
- **Remove obsolete files** (`plugin_info.toml`)
- **Update dependencies** in `pyproject.toml`
- **Verify entry points** are v5-compliant
- **Clean up legacy directories**

## Migration Success Criteria

### ✅ Migration Complete When:
1. **All import statements use v5 paths**
2. **Plugin discovery finds all plugins**
3. **Extensions load in dashboard**  
4. **Hardware communication functions**
5. **No v4 deprecation warnings**

### Expected Benefits:
- **Future compatibility** with PyMoDAQ roadmap
- **Access to v5 features** and improvements
- **Professional distribution** readiness
- **Community ecosystem** integration

## Conclusion

PyMoDAQ v5 import compliance is primarily about **systematic import path updates**. The modular architecture provides better maintainability and feature access. Projects with correct plugin architecture (base classes, entry points) require only import path maintenance - the hard design work is already compatible.