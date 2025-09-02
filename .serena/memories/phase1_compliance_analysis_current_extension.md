# Phase 1 Compliance Analysis - Current Extension Implementation

## Current Extension Analysis (urashg_microscopy_extension.py)

### ✅ CORRECT: Base Class and Import
- **Import**: `from pymodaq_gui.utils.custom_app import CustomApp` ✅ (PyMoDAQ v5 compliant)
- **Inheritance**: `class URASHGMicroscopyExtension(CustomApp):` ✅ (Correct for v5)

### ❌ CONSTRUCTOR ISSUES: 
**Current Constructor (Line 192)**:
```python
def __init__(self, dockarea=None, dashboard=None):
    super().__init__(dockarea)  # ❌ Wrong: missing dashboard parameter
```

**Should be (PyMoDAQ v5 Standard)**:
```python
def __init__(self, dockarea=None, dashboard=None):
    super().__init__(dockarea, dashboard)  # ✅ Both parameters required
```

### ❌ DATA STRUCTURE COMPLIANCE:
**Current Issues**:
- DataWithAxes imported but not properly used in measurement logic
- Mock measurement doesn't create proper PyMoDAQ data structures
- Missing DataSource parameter (required for v5)

**Required Changes**:
```python
from pymodaq_data.datamodel import DataWithAxes, Axis, DataSource

def create_measurement_data(self, image_data, angles):
    return DataWithAxes(
        'RASHG_Measurement',
        data=[image_data],
        axes=[Axis('Polarization', data=angles, units='°')],
        units='counts',
        source=DataSource.raw  # ✅ Required for v5
    )
```

### ❌ MODULES_MANAGER INTEGRATION:
**Current Issue (Line 295)**:
```python
if hasattr(self.dashboard, "modules_manager"):
    modules_manager = self.dashboard.modules_manager
    # Add module detection logic here when PyMoDAQ is fully available
```

**Should be**:
```python
def get_required_modules(self):
    """Access modules through PyMoDAQ's standard API"""
    if not self.dashboard or not hasattr(self.dashboard, 'modules_manager'):
        return {}
        
    modules_manager = self.dashboard.modules_manager
    
    # Find specific modules loaded in dashboard
    modules = {
        'camera': self.find_module(modules_manager.detectors, 'PrimeBSI'),
        'power_meter': self.find_module(modules_manager.detectors, 'Newport'),
        'laser': self.find_module(modules_manager.actuators, 'MaiTai'),
        'rotators': self.find_module(modules_manager.actuators, 'Elliptec'),
    }
    
    return {k: v for k, v in modules.items() if v is not None}
```

### ✅ ALREADY CORRECT:
- Extension metadata (name, description, author, version)
- Parameter tree structure 
- Signal definitions
- UI setup patterns
- Logging integration

## Phase 1 Required Changes Summary

### 1. Constructor Fix (CRITICAL)
Fix super().__init__() call to pass both parameters

### 2. DataWithAxes Implementation (CRITICAL) 
Add proper data structure creation in measurement logic

### 3. Modules Manager Integration (HIGH)
Implement proper module detection and access patterns

### 4. Import Path Updates (MEDIUM)
Update imports to use proper v5 paths consistently

## Implementation Priority
1. **Fix constructor** - Prevents extension from loading properly
2. **Add DataWithAxes usage** - Core v5 compliance requirement  
3. **Implement modules_manager integration** - Required for device coordination
4. **Update measurement logic** - Use proper PyMoDAQ data structures

## Current Status Assessment
- **Base architecture**: ✅ Correct (CustomApp inheritance)
- **Entry points**: ✅ Correct (plugin_info.toml has extension entry)
- **Constructor**: ❌ Missing dashboard parameter in super() call
- **Data structures**: ❌ Not using DataWithAxes properly 
- **Module integration**: ❌ Placeholder implementation only