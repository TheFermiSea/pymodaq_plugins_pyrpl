# PyMoDAQ Plugin Compliance Issues and Fixes

## Critical Issues Identified by Gemini Analysis

### 1. Package Structure Non-Compliance
**Issue**: Current structure doesn't match PyMoDAQ template standards
**Required Structure**:
```
src/
└── pymodaq_plugins_urashg/
    ├── __init__.py
    ├── daq_move_plugins/
    │   ├── __init__.py
    │   └── daq_move_*.py
    └── daq_viewer_plugins/
        ├── __init__.py
        ├── plugins_0D/
        ├── plugins_1D/
        └── plugins_2D/
```

### 2. Parameter Tree Issues
**Current CI Error**: `KeyError: 'Parameter Settings has no child named multiaxes'`
**Root Cause**: Plugins don't follow PyMoDAQ ParameterTree standards

**Required Fix**:
```python
# In plugin parameter definitions
params = [
    {'title': 'Parameter Settings', 'name': 'parameter_settings', 'type': 'group', 'children': [
        {'title': 'Multiaxes', 'name': 'multiaxes', 'type': 'group', 'children': [
            # Add multiaxes configuration
        ]},
        # Other standard PyMoDAQ parameters
    ]}
]
```

### 3. Base Class Inheritance Problems  
**Issue**: Plugins don't properly inherit from PyMoDAQ base classes
**Required**:
- DAQ_Move plugins: inherit from `DAQ_Move_Base`
- DAQ_Viewer plugins: inherit from `DAQ_Viewer_Base` (with 0D/1D/2D variants)

### 4. Data Protocol Non-Compliance (Viewers)
**Issue**: Data not packaged in PyMoDAQ data objects
**Required**: Use `DataFromPlugins`, `DataToExport`, `Axis` objects and emit via `data_grabed_signal`

## Priority Fix Order
1. Fix parameter tree structure (resolves CI failures)
2. Standardize package structure  
3. Implement proper base class inheritance
4. Fix data protocol for viewer plugins
5. Add proper entry points in pyproject.toml