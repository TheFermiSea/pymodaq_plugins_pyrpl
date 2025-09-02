# PyMoDAQ Architecture Patterns and Best Practices

## Core Plugin Architecture

### 1. Base Classes and Inheritance
- **DAQ_Move plugins**: Must inherit from `DAQ_Move_base` (not `DAQ_Move_Base` - lowercase 'b')
- **DAQ_Viewer plugins**: Must inherit from `DAQ_Viewer_base` (not `DAQ_Viewer_Base`)
- **Extensions**: Must inherit from `CustomApp` from `pymodaq_gui.utils.custom_app`

### 2. Plugin Structure Requirements
```python
# Required class attributes
class DAQ_Move_XXX(DAQ_Move_base):
    # For multi-axis devices
    _axis_names = ['Xaxis', 'Yaxis', 'Zaxis']  # or dict format
    _controller_units = ['mm', 'mm', 'mm']     # must match axis count
    _epsilons = [0.001, 0.001, 0.001]         # must match axis count
    
    # Hardware averaging capability
    hardware_averaging = True  # enables hardware averaging if supported
    
    # Live mode capability
    live_mode_available = True  # enables continuous data streaming
```

### 3. Parameter Structure (Critical)
PyMoDAQ plugins require specific parameter structure:

**For Multi-axis Move plugins:**
```python
params = [
    # CRITICAL: multiaxes MUST be at top level for PyMoDAQ discovery
    {
        'title': 'Multiaxes:',
        'name': 'multiaxes',
        'type': 'group',
        'children': [
            {
                'title': 'Multi-axes:',
                'name': 'multi_axes',
                'type': 'list',
                'values': ['X Stage', 'Y Stage', 'Z Focus'],
                'value': 'X Stage',
            },
            {
                'title': 'Axis:',
                'name': 'axis',
                'type': 'list',
                'values': ['X Stage', 'Y Stage', 'Z Focus'],
                'value': 'X Stage',
            },
            {
                'title': 'Master/Slave:',
                'name': 'multi_status',
                'type': 'list',
                'values': ['Master', 'Slave'],
                'value': 'Master',
            },
        ],
    },
    # Connection settings group
    {
        'title': 'Connection Settings:',
        'name': 'connect_settings',  # Standard name
        'type': 'group',
        'children': [
            {
                'title': 'Mock Mode:',
                'name': 'mock_mode',
                'type': 'bool',
                'value': False,
            },
            # ... other connection parameters
        ],
    },
]
```

**For Viewer plugins:**
```python
params = [
    # Settings group (standard for viewers)
    {
        'title': 'Settings:',
        'name': 'Settings',
        'type': 'group',
        'children': [
            {
                'title': 'Connection Settings:',
                'name': 'connect_settings',
                'type': 'group',
                'children': [
                    {
                        'title': 'Mock Mode:',
                        'name': 'mock_mode',
                        'type': 'bool',
                        'value': False,
                    },
                    # ... other parameters
                ],
            },
        ],
    },
]
```

## Data Handling Patterns

### 1. Correct Data Structures
PyMoDAQ 5.x uses specific data structures:

```python
# Import correct data classes
from pymodaq_data.data import DataRaw, DataWithAxes, DataToExport, Axis
from pymodaq_data.data.utils import DataSource, DataDim, DataDistribution

# Create proper data with axes
data = DataWithAxes(
    'mydata',
    source=DataSource['raw'],
    dim=DataDim['Data2D'],
    distribution=DataDistribution['uniform'],
    data=[np.array([[1,2,3], [4,5,6]])],
    axes=[
        Axis('vaxis', index=0, data=np.array([-1, 1])),
        Axis('haxis', index=1, data=np.array([10, 11, 12]))
    ]
)

# Emit data properly
self.dte_signal.emit(DataToExport('measurement', data=[data]))
```

### 2. Plugin Data Emission
```python
# Correct way to emit data from plugins
from pymodaq_data.data import DataToExport, DataRaw, Axis

# Create axis if needed
x_axis = Axis(label='Wavelength', units='nm', data=vector_X)

# Create DataToExport with properly structured data
dte = DataToExport('mydata', data=[
    DataRaw(name='Camera', data=[data2D_0, data2D_1],
            axes=[x_axis, y_axis]),
    DataRaw(name='Spectrum', data=[data1D_0, data1D_1],
            axes=[x_axis], labels=['label0', 'label1']),
    DataRaw(name='Current', data=[data0D_0, data0D_1])
])

# Emit using proper signal
self.dte_signal.emit(dte)
```

## Extension Architecture

### 1. CustomApp Inheritance
Extensions must properly inherit from CustomApp:

```python
from pymodaq_gui.utils.custom_app import CustomApp

class MyExtension(CustomApp):
    # Parameter tree structure
    params = [
        {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
            {'title': 'Base path:', 'name': 'base_path', 'type': 'browsepath'},
            # ... other parameters
        ]},
    ]
    
    def __init__(self, dockarea, dashboard=None):
        super().__init__(dockarea)  # Only pass dockarea to parent
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        pass
    
    def setup_actions(self):
        """Setup menu actions"""
        self.add_action('quit', 'Quit', 'close2', "Quit program")
    
    def setup_docks(self):
        """Setup dock widgets"""
        self.dock_settings = gutils.Dock('Settings', size=(350, 350))
        self.dockarea.addDock(self.dock_settings, 'left')
    
    def connect_things(self):
        """Connect signals and slots"""
        pass
    
    def value_changed(self, param):
        """Handle parameter changes"""
        pass
```

## Device Manager Patterns

### 1. Built-in Device Management
PyMoDAQ provides built-in device management through:
- **Dashboard module**: Central hub for device coordination
- **Module Manager**: For selecting and synchronizing devices
- **Preset Manager**: For saving/loading device configurations

### 2. Avoid Custom Device Managers
Instead of custom device managers, use PyMoDAQ's built-in systems:
- Use Dashboard presets to define device ensembles
- Use Module Manager for device coordination
- Leverage Dashboard's Master/Slave device relationships
- Use extension architecture for complex workflows

## Threading and Signals

### 1. Proper Threading Patterns
```python
from qtpy.QtCore import QObject, Signal, QThread

class MeasurementWorker(QObject):
    """Proper worker class for threaded operations"""
    finished = Signal()
    error = Signal(str)
    progress = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def run_measurement(self):
        """Main measurement loop in separate thread"""
        try:
            # Measurement logic here
            self.progress.emit(50)
            # More measurement logic
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
```

### 2. Signal Patterns
```python
# Standard PyMoDAQ signals for extensions
class MyExtension(CustomApp):
    # Define custom signals
    measurement_progress = Signal(int)
    device_status_changed = Signal(str, str)
    error_occurred = Signal(str)
    
    def __init__(self, dockarea, dashboard=None):
        super().__init__(dockarea)
        self.setup_signals()
    
    def setup_signals(self):
        """Connect internal signals"""
        self.measurement_progress.connect(self.update_progress)
```

## Configuration Management

### 1. Proper Configuration Classes
```python
from pathlib import Path
from pymodaq.utils.config import BaseConfig

class Config(BaseConfig):
    """Main configuration class for plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"
```

### 2. Parameter Management
Use PyMoDAQ's parameter system for configuration:
```python
# Access parameters properly
value = self.settings.child('connect_settings', 'mock_mode').value()

# Set parameter values
self.settings.child('multiaxes', 'axis').setValue(2)

# Alternative syntax
value = self.settings['connect_settings', 'mock_mode']
```

## Package Structure

### 1. Correct Import Patterns
```python
# PyMoDAQ 5.x import structure
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq_data.data import DataRaw, DataWithAxes, DataToExport
from pymodaq_gui.utils.custom_app import CustomApp
```

### 2. Plugin Discovery Requirements
For proper plugin discovery:
- Use correct naming: `daq_move_XXX.py`, `DAQ_Move_XXX` class
- Use correct parameter structure (multiaxes at top level for move plugins)
- Use correct base class imports
- Follow PyMoDAQ naming conventions

## Key Takeaways

1. **Don't reinvent the wheel**: Use PyMoDAQ's built-in device management
2. **Follow parameter structure**: Critical for plugin discovery
3. **Use proper data structures**: DataWithAxes, DataToExport, etc.
4. **Inherit from correct base classes**: DAQ_Move_base, DAQ_Viewer_base, CustomApp
5. **Leverage existing infrastructure**: Dashboard, Module Manager, Preset system
6. **Use standard naming conventions**: Essential for PyMoDAQ integration