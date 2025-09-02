# PyMoDAQ Plugin Parameter Structure Standards

## Critical Parameter Requirements

### Standard Parameter Groups Required by PyMoDAQ:

1. **Connection Settings Group**:
```python
{'title': 'Connection Settings:', 'name': 'connect_settings', 'type': 'group', 'children': [
    {'title': 'Communication:', 'name': 'communication', 'type': 'list', 'values': ['Serial', 'Ethernet'], 'value': 'Serial'},
    {'title': 'Serial Port:', 'name': 'com_port', 'type': 'str', 'value': 'COM1'},
    {'title': 'Baud Rate:', 'name': 'baud_rate', 'type': 'int', 'value': 9600},
]}
```

2. **Parameter Settings Group** (CRITICAL - Missing causes CI failures):
```python
{'title': 'Parameter Settings:', 'name': 'parameter_settings', 'type': 'group', 'children': [
    {'title': 'Multiaxes:', 'name': 'multiaxes', 'type': 'group', 'children': [
        {'title': 'Multi-axes:', 'name': 'multi_axes', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
        {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'values': ['x', 'y', 'z'], 'value': 'x'},
    ]},
    # Other parameters specific to the device
]}
```

3. **Move Settings Group** (for DAQ_Move plugins):
```python
{'title': 'Move Settings:', 'name': 'move_settings', 'type': 'group', 'children': [
    {'title': 'Current Position:', 'name': 'current_pos', 'type': 'float', 'value': 0, 'readonly': True},
    {'title': 'Speed:', 'name': 'speed', 'type': 'float', 'value': 1.0},
    {'title': 'Acceleration:', 'name': 'acceleration', 'type': 'float', 'value': 1.0},
]}
```

## Common Parameter Types:
- `'int'`, `'float'`, `'str'`, `'bool'` - Basic data types
- `'list'` - Dropdown selection (requires 'values' key)
- `'group'` - Container for other parameters (requires 'children' key)
- `'action'` - Button that triggers a function
- `'color'` - Color picker widget

## Parameter Access in Code:
```python
# In commit_settings() method:
def commit_settings(self, param):
    if param.name() == 'speed':
        speed_value = param.value()
        # Send to hardware
    elif param.name() == 'axis':
        axis_value = param.value()
        # Configure hardware axis

# Getting parameter values:
port = self.settings.child('connect_settings', 'com_port').value()
speed = self.settings.child('move_settings', 'speed').value()
```

## Critical Notes:
- The 'multiaxes' parameter group is REQUIRED by PyMoDAQ framework
- Missing this causes `KeyError: 'Parameter Settings has no child named multiaxes'`
- All parameter names must be lowercase with underscores
- Parameter hierarchy must match PyMoDAQ expectations