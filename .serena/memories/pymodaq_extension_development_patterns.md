# PyMoDAQ v5 Extension Development Patterns - Standards-Compliant Guide

## PyMoDAQ v5 Architecture Overview

PyMoDAQ v5 introduced **modular package architecture** with specialized components. Extension development must follow v5 patterns for proper integration with the dashboard framework.

## v5-Compliant Extension Architecture

### CustomApp Base Class Implementation
**Pattern**: Standard PyMoDAQ v5 extension inheritance
```python
from pymodaq_gui.utils.custom_app import CustomApp  # v5 import path

class URASHGMicroscopyExtension(CustomApp):
    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        # Access PyMoDAQ's module management system
        self.modules_manager = self.dashboard.modules_manager
        self.available_modules = {}
        self.required_modules = ['MaiTai', 'Elliptec', 'PrimeBSI', 'Newport1830C']
```

**Key v5 Benefits**:
- Automatic PyMoDAQ framework integration
- Standard extension lifecycle management  
- Built-in dashboard module access
- Compliant with PyMoDAQ v5 standards

### Standard Module Access (v5 Dashboard Integration)
**Pattern**: Use PyMoDAQ's built-in module management system
```python
class URASHGMicroscopyExtension(CustomApp):
    def get_required_modules(self):
        """Access modules through PyMoDAQ's standard API"""
        if not self.modules_manager:
            return {}
            
        actuators = self.modules_manager.actuators
        detectors = self.modules_manager.detectors
        
        # Find specific modules loaded in dashboard
        modules = {
            'laser': self.find_module(actuators, 'MaiTai'),
            'rotators': self.find_module(actuators, 'Elliptec'),  
            'camera': self.find_module(detectors, 'PrimeBSI'),
            'power_meter': self.find_module(detectors, 'Newport1830C')
        }
        
        return {k: v for k, v in modules.items() if v is not None}
    
    def find_module(self, module_dict, name_pattern):
        """Find module by name pattern"""
        if not module_dict:
            return None
        for module_name, module in module_dict.items():
            if name_pattern.lower() in module_name.lower():
                return module
        return None
```

**Critical v5 Standards Compliance**:
- ✅ Uses `dashboard.modules_manager` (PyMoDAQ v5 standard)
- ✅ Accesses hardware ONLY through PyMoDAQ plugins  
- ✅ Respects PyMoDAQ module lifecycle
- ❌ NEVER create custom device managers (violates PyMoDAQ standards)

### Extension Entry Points (v5 Configuration)
**Pattern**: Standard PyMoDAQ v5 extension registration
```python
# Required module constants
EXTENSION_NAME = 'μRASHG Microscopy'
CLASS_NAME = 'URASHGMicroscopyExtension'

# pyproject.toml entry point (v5 style)
[project.entry-points."pymodaq.extensions"]
"URASHGMicroscopyExtension" = "package.extensions.module:URASHGMicroscopyExtension"
```

**Configuration Requirements**:
- Entry points in `pyproject.toml` (NOT `plugin_info.toml`)
- Standard extension constants defined
- Extension class inherits from CustomApp
- Located in `extensions/` subdirectory

## Plugin Integration Patterns (v5)

### Hardware Control via PyMoDAQ Plugins
**Pattern**: All hardware access via PyMoDAQ plugins (v5 STANDARD)
```python
def control_laser_wavelength(self, wavelength):
    """Control laser via PyMoDAQ actuator module"""
    modules = self.get_required_modules()
    laser_module = modules.get('laser')
    
    if laser_module:
        # Use PyMoDAQ's DataActuator for single-axis control (v5)
        from pymodaq_data.datamodel.data_actuator import DataActuator
        position = DataActuator(data=[wavelength])
        laser_module.move_abs(position)
        return True
    return False

def acquire_camera_data(self):
    """Acquire data via PyMoDAQ detector module"""
    modules = self.get_required_modules()
    camera_module = modules.get('camera')
    
    if camera_module:
        # Use PyMoDAQ's standard data acquisition
        data = camera_module.grab_data()
        return data
    return None

def control_rotator_positions(self, positions):
    """Control multiple rotators via PyMoDAQ multi-axis plugin"""
    modules = self.get_required_modules()
    rotator_module = modules.get('rotators')
    
    if rotator_module:
        # Use DataActuator for multi-axis control (v5)
        from pymodaq_data.datamodel.data_actuator import DataActuator
        position_data = DataActuator(data=positions)
        rotator_module.move_abs(position_data)
        return True
    return False
```

**v5 Standards Compliance Benefits**:
- ✅ Uses PyMoDAQ's plugin system exclusively
- ✅ Respects module lifecycle and initialization
- ✅ Standard data structures (DataActuator)
- ✅ Integrates with PyMoDAQ's signal system
- ✅ No direct hardware communication

## v5 Data Structure Patterns

### PyMoDAQ v5 Data Structures (CRITICAL)
**Pattern**: Proper v5 data structure usage
```python
from pymodaq_data.datamodel import DataWithAxes, Axis, DataSource  # v5 paths
from pymodaq_data.datamodel.data_actuator import DataActuator      # v5 specific

def create_measurement_data(self, image_data, x_axis, y_axis):
    """Create PyMoDAQ v5 compliant data structure"""
    return DataWithAxes(
        'RASHG_Measurement',
        data=[image_data],
        axes=[
            Axis('x', data=x_axis, units='pixels'),
            Axis('y', data=y_axis, units='pixels')
        ],
        units='counts',
        source=DataSource.raw  # Required for PyMoDAQ v5
    )

def create_polarimetry_data(self, intensities, angles):
    """Create data for polarimetric measurements"""
    return DataWithAxes(
        'Polarimetric_SHG',
        data=[intensities],
        axes=[Axis('Polarization', data=angles, units='°')],
        units='counts',
        source=DataSource.raw
    )
```

### DataActuator Usage Patterns (v5 CRITICAL)
**Pattern**: Different usage for single vs multi-axis devices
```python
# Single-axis devices (MaiTai laser) - v5 PATTERN
def move_single_axis_device(self, position_value):
    """Control single-axis device (laser wavelength)"""
    from pymodaq_data.datamodel.data_actuator import DataActuator  # v5 path
    position = DataActuator(data=[position_value])  # Single value in list
    
    modules = self.get_required_modules()
    laser = modules.get('laser')
    if laser:
        laser.move_abs(position)

# Multi-axis devices (Elliptec rotators) - v5 PATTERN  
def move_multi_axis_device(self, position_array):
    """Control multi-axis device (3 rotators)"""
    from pymodaq_data.datamodel.data_actuator import DataActuator  # v5 path
    positions = DataActuator(data=position_array)  # Array of positions
    
    modules = self.get_required_modules()
    rotators = modules.get('rotators')
    if rotators:
        rotators.move_abs(positions)
```

**CRITICAL v5 Pattern Notes**:
```python
# In plugin implementation (not extension):
# Single-axis plugins: use position.value()
# Multi-axis plugins: use positions.data[0]
```

## Threading and Communication (v5)

### Thread-Safe Operations with v5 Imports
**Pattern**: Use Qt threading with proper v5 import paths
```python
from qtpy.QtCore import QObject, QThread, Signal
from pymodaq_utils.daq_utils import ThreadCommand  # v5 import path

class MeasurementWorker(QObject):
    progress_updated = Signal(int, str)
    measurement_complete = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, extension):
        super().__init__()
        self.extension = extension
        
    def run_measurement(self):
        """Execute measurement sequence using PyMoDAQ v5 modules"""
        try:
            # Access modules through extension's PyMoDAQ integration
            modules = self.extension.get_required_modules()
            
            self.progress_updated.emit(10, "Initializing devices...")
            
            # Use PyMoDAQ modules for hardware control
            camera = modules.get('camera')
            rotators = modules.get('rotators')
            
            if not camera or not rotators:
                self.error_occurred.emit("Required modules not available")
                return
                
            self.progress_updated.emit(50, "Acquiring data...")
            # ... measurement logic using PyMoDAQ modules
            
            self.measurement_complete.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

# Usage in extension
def start_measurement(self):
    """Start measurement in separate thread"""
    self.worker = MeasurementWorker(self)
    self.measurement_thread = QThread()
    self.worker.moveToThread(self.measurement_thread)
    
    # Connect signals
    self.worker.progress_updated.connect(self.update_progress)
    self.worker.measurement_complete.connect(self.on_measurement_complete)
    self.worker.error_occurred.connect(self.on_measurement_error)
    
    # Start thread
    self.measurement_thread.started.connect(self.worker.run_measurement)
    self.measurement_thread.start()
```

**Critical v5 Threading Points**:
- Always use moveToThread, never subclass QThread
- Use Qt signals for thread communication
- Access PyMoDAQ modules through extension reference
- Use proper v5 import paths for ThreadCommand
- No direct GUI updates from worker threads

## Parameter Management (v5)

### Parameter Tree Organization
**Pattern**: v5-compliant parameter structure
```python
from pymodaq_utils.parameter import Parameter  # v5 import path

params = [
    {'name': 'experiment', 'type': 'group', 'children': [
        {'name': 'pol_steps', 'type': 'int', 'value': 36, 'min': 1, 'max': 360},
        {'name': 'integration_time', 'type': 'float', 'value': 100.0, 
         'min': 1.0, 'max': 10000.0, 'suffix': 'ms'},
        {'name': 'wavelength', 'type': 'float', 'value': 800.0, 
         'min': 750.0, 'max': 920.0, 'suffix': 'nm'},
    ]},
    {'name': 'hardware', 'type': 'group', 'children': [
        {'name': 'camera', 'type': 'group', 'children': [
            {'name': 'roi_width', 'type': 'int', 'value': 512},
            {'name': 'roi_height', 'type': 'int', 'value': 512},
        ]},
        {'name': 'rotators', 'type': 'group', 'children': [
            {'name': 'qwp_address', 'type': 'int', 'value': 2},
            {'name': 'hwp_inc_address', 'type': 'int', 'value': 3},
            {'name': 'hwp_ana_address', 'type': 'int', 'value': 8},
        ]},
    ]},
]
```

**v5 Parameter Best Practices**:
- Group related parameters logically
- Include min/max bounds for validation
- Add units with 'suffix' parameter
- Use descriptive parameter names
- Include 'tip' for user guidance

## Error Handling Patterns (v5)

### Comprehensive Error Handling with v5 Standards
**Pattern**: Multi-level error handling with user feedback
```python
from pymodaq_utils.logger import set_logger, get_module_name  # v5 imports

logger = set_logger(get_module_name(__file__))

def safe_module_operation(self, operation_func, module_name, *args, **kwargs):
    """Safely execute operations on PyMoDAQ modules"""
    try:
        modules = self.get_required_modules()
        module = modules.get(module_name)
        
        if not module:
            error_msg = f"Module '{module_name}' not available - ensure it's loaded in dashboard"
            logger.error(error_msg)
            if hasattr(self, 'log_message'):
                self.log_message(error_msg, level='error')
            return None, error_msg
            
        logger.info(f"Starting {operation_func.__name__} on {module_name}")
        result = operation_func(module, *args, **kwargs)
        logger.info(f"Successfully completed {operation_func.__name__}")
        return result, None
        
    except Exception as e:
        error_msg = f"Error in {operation_func.__name__} on {module_name}: {e}"
        logger.error(error_msg, exc_info=True)
        if hasattr(self, 'log_message'):
            self.log_message(error_msg, level='error')
        return None, error_msg
```

### Safety Validation with v5 Patterns
**Pattern**: Parameter and state validation before operations
```python
def validate_measurement_settings(self):
    """Validate settings before starting measurement"""
    violations = []
    
    # Check required modules are loaded
    modules = self.get_required_modules()
    required_modules = ['camera', 'rotators']
    for module_name in required_modules:
        if not modules.get(module_name):
            violations.append(f"Required module '{module_name}' not loaded in dashboard")
    
    # Parameter validation
    if hasattr(self, 'settings'):
        pol_steps = self.settings.child('experiment', 'pol_steps').value()
        if pol_steps < 10:
            violations.append(f"Too few polarization steps: {pol_steps} < 10")
            
        integration_time = self.settings.child('experiment', 'integration_time').value()
        if integration_time > 10000:  # 10 seconds
            violations.append(f"Integration time too long: {integration_time}ms")
    
    return violations
```

## Configuration Management (v5)

### v5-Compliant Configuration Files
**Pattern**: Only use pyproject.toml for v5
```toml
# pyproject.toml (v5 standard - ONLY configuration file needed)
[project]
name = "pymodaq-plugins-yourpackage"
version = "1.0.0"
dependencies = [
    "pymodaq>=5.0.0",
    "pymodaq-gui",  
    "pymodaq-data",
    "pymodaq-utils",
]

[project.entry-points."pymodaq.move_plugins"]
"DAQ_Move_YourDevice" = "package.daq_move_plugins.daq_move_YourDevice:DAQ_Move_YourDevice"

[project.entry-points."pymodaq.viewer_plugins"]  
"DAQ_2DViewer_YourCamera" = "package.daq_viewer_plugins.plugins_2D.daq_2Dviewer_YourCamera:DAQ_2DViewer_YourCamera"

[project.entry-points."pymodaq.extensions"]
"YourExtension" = "package.extensions.your_extension:YourExtension"
```

**CRITICAL v5 Configuration Rules**:
- ❌ **NO** `plugin_info.toml` (obsolete in v5)
- ✅ **USE** `pyproject.toml` exclusively
- ✅ **SPECIFY** v5 modular dependencies
- ✅ **CONFIGURE** proper entry points

## Key v5 Development Guidelines

### PyMoDAQ v5 Standards Compliance (CRITICAL)
1. **✅ USE**: `dashboard.modules_manager` for all hardware access
2. **✅ USE**: v5 import paths (`pymodaq_gui`, `pymodaq_data`, `pymodaq_utils`)
3. **✅ USE**: PyMoDAQ plugins exclusively for device communication  
4. **✅ USE**: Standard CustomApp inheritance patterns
5. **✅ USE**: DataWithAxes with `source=DataSource.raw`
6. **❌ NEVER**: Create custom device managers (violates v5 standards)
7. **❌ NEVER**: Use v4 import paths
8. **❌ NEVER**: Access hardware directly bypassing PyMoDAQ plugins

### Extension Development Best Practices (v5)
1. **Module Dependency**: Extensions depend on plugins being loaded in dashboard first
2. **Error Handling**: Always check if required modules are available
3. **Threading**: Use Qt threading patterns for non-blocking operations
4. **Data Structures**: Follow PyMoDAQ v5 data structure requirements exactly
5. **Configuration**: Use only `pyproject.toml` (no `plugin_info.toml`)

### Common v5 Migration Pitfalls to Avoid
1. **Old Import Paths**: Using v4 import paths breaks functionality
2. **Data Structure Paths**: `pymodaq_data.data` vs `pymodaq_data.datamodel` confusion
3. **Configuration Files**: Keeping obsolete `plugin_info.toml`
4. **Custom Device Managers**: These violate v5 standards and cause integration issues
5. **Direct Hardware Access**: Always go through PyMoDAQ plugins

### Success Factors for PyMoDAQ v5 Extensions
1. **Standards First**: Follow PyMoDAQ v5 patterns exactly - no custom approaches
2. **Plugin Integration**: Seamless integration with PyMoDAQ's plugin ecosystem
3. **User Experience**: Standard PyMoDAQ workflow (load plugins, then launch extension)
4. **Testing**: Comprehensive testing including PyMoDAQ integration validation
5. **Import Compliance**: All imports use v5 paths

This guide provides PyMoDAQ v5 standards-compliant patterns for professional extension development that integrates seamlessly with the PyMoDAQ ecosystem while maintaining all framework benefits and standards compliance.