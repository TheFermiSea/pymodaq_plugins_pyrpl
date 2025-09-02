# PyMoDAQ Plugin Architecture Reference

## Plugin Base Classes and Imports

### Move Plugins
```python
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,  # Note: lowercase 'b'
    DataActuator,
)
```

### Viewer Plugins
```python
from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base,  # Note: lowercase 'b'
    comon_parameters,
)
```

## Required Parameter Structure

### Move Plugins - Mandatory multiaxes Group
```python
params = [
    # Other parameters...
    
    # CRITICAL: multiaxes MUST be at top level
    {
        "title": "Multiaxes:",
        "name": "multiaxes",
        "type": "group",
        "children": [
            {
                "title": "Multi-axes:",
                "name": "multi_axes",
                "type": "list",
                "values": ["Axis1", "Axis2", "Axis3"],  # Device-specific
                "value": "Axis1",
            },
            {
                "title": "Axis:",
                "name": "axis", 
                "type": "list",
                "values": ["Axis1", "Axis2", "Axis3"],  # Same as multi_axes
                "value": "Axis1",
            },
            {
                "title": "Master/Slave:",
                "name": "multi_status",
                "type": "list",
                "values": ["Master", "Slave"],
                "value": "Master",
            },
        ],
    },
    
    # Other parameters...
]
```

## Required Plugin Properties

### Move Plugins
```python
class DAQ_Move_PluginName(DAQ_Move_base):
    is_multiaxes = True  # or False for single axis
    _axis_names = ["Axis1", "Axis2"]  # Device-specific names
    
    @property
    def axis_names(self) -> List[str]:
        """Return list of available axis names for PyMoDAQ."""
        return self._axis_names
```

## Plugin Lifecycle Methods

### Initialization
- `__init__(self, parent=None, params_state=None)`
- `ini_stage_init(self, old_controller=None, new_controller=None, slave_controller=None)`
- `init_hardware(self, controller=None)` - Custom hardware initialization

### Key PyMoDAQ Properties
- `self.settings.child('multiaxes', 'axis')` - Current axis selection
- `self.settings.child('multiaxes', 'multi_status')` - Master/Slave status
- `self.is_master` - Property based on multi_status
- `self.axis_names` - List of available axes

## Common Pitfalls

1. **Parameter Structure**: Do NOT nest multiaxes under parameter_settings
2. **Base Class Names**: Use lowercase 'b' in DAQ_Move_base/DAQ_Viewer_base
3. **Missing Properties**: Always implement axis_names property for move plugins
4. **Missing Parameters**: multi_status parameter is required in multiaxes group
5. **Import Errors**: Remember to import List from typing if using type hints