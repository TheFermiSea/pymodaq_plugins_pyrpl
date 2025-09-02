# Immediate CI Fix Priority for pymodaq_plugins_urashg

## CRITICAL: Fix Parameter Structure First (Causing All CI Failures)

### Root Cause:
`KeyError: 'Parameter Settings has no child named multiaxes'`

### Files to Fix (Priority Order):

1. **daq_2Dviewer_PrimeBSI.py** - Camera plugin
2. **daq_0Dviewer_Newport1830C.py** - Power meter plugin  
3. **daq_move_Elliptec.py** - Rotation mount plugin
4. **daq_move_MaiTai.py** - Laser controller plugin
5. **daq_move_ESP300.py** - Stage controller plugin

### Required Fix for Each Plugin:
Add this parameter structure to EVERY plugin's `params` list:

```python
params = [
    {'title': 'Connection Settings:', 'name': 'connect_settings', 'type': 'group', 'children': [
        # Connection parameters here
    ]},
    {'title': 'Parameter Settings:', 'name': 'parameter_settings', 'type': 'group', 'children': [
        {'title': 'Multiaxes:', 'name': 'multiaxes', 'type': 'group', 'children': [
            {'title': 'Multi-axes:', 'name': 'multi_axes', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
            {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
        ]},
        # Other device-specific parameters
    ]},
    # Other groups (move_settings, etc.)
]
```

### Specific Parameter Requirements by Plugin Type:

#### For DAQ_Move plugins (Elliptec, MaiTai, ESP300):
```python
params = [
    # Connection settings
    {'title': 'Connection Settings:', 'name': 'connect_settings', 'type': 'group', 'children': [...]},
    # Parameter settings (REQUIRED)
    {'title': 'Parameter Settings:', 'name': 'parameter_settings', 'type': 'group', 'children': [
        {'title': 'Multiaxes:', 'name': 'multiaxes', 'type': 'group', 'children': [
            {'title': 'Multi-axes:', 'name': 'multi_axes', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
            {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
        ]},
    ]},
    # Move settings
    {'title': 'Move Settings:', 'name': 'move_settings', 'type': 'group', 'children': [
        {'title': 'Current Position:', 'name': 'current_pos', 'type': 'float', 'value': 0, 'readonly': True},
    ]},
]
```

#### For DAQ_Viewer plugins (PrimeBSI, Newport):
```python
params = [
    # Connection settings  
    {'title': 'Connection Settings:', 'name': 'connect_settings', 'type': 'group', 'children': [...]},
    # Parameter settings (REQUIRED)
    {'title': 'Parameter Settings:', 'name': 'parameter_settings', 'type': 'group', 'children': [
        {'title': 'Multiaxes:', 'name': 'multiaxes', 'type': 'group', 'children': [
            {'title': 'Multi-axes:', 'name': 'multi_axes', 'type': 'list', 'values': ['x', 'y'], 'value': 'x'},
            {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'values': ['x', 'y'], 'value': 'x'},
        ]},
    ]},
    # Acquisition settings
    {'title': 'Acquisition Settings:', 'name': 'acq_settings', 'type': 'group', 'children': [...]},
]
```

## Action Plan:
1. Fix parameter structures in all 5 plugin files
2. Test locally with pytest to verify KeyError is resolved
3. Commit and push to trigger new CI run
4. Address any remaining base class inheritance issues
5. Fix data protocol issues in viewer plugins

This single fix should resolve ~80% of the current CI failures.