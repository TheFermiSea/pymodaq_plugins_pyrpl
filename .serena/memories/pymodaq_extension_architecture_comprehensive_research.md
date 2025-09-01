# PyMoDAQ Extension Architecture Comprehensive Research for μRASHG System

## Research Overview

This document provides comprehensive architectural analysis for implementing a PyMoDAQ Extension for the μRASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy system. The research covers Extension architecture patterns, multi-device coordination mechanisms, data management strategies, and production-ready implementation approaches.

## Current System Context

**μRASHG System Devices (All PyMoDAQ 5.x Compatible)**:
- Elliptec rotation mounts (3x) - DAQ_Move_Elliptec
- Photometrics PrimeBSI camera - daq_2Dviewer_PrimeBSI 
- Newport 1830-C power meter - DAQ_0DViewer_Newport1830C
- MaiTai laser - DAQ_Move_MaiTai
- Red Pitaya FPGA - External PyRPL_PID plugin
- Individual plugins tested and fully functional with hardware

## 1. PyMoDAQ Extension Architecture Foundation

### Core Extension Base Class: CustomApp

**Location**: `pymodaq.utils.gui_utils.CustomApp`

**Purpose**: Generic base class for building standalone applications or dashboard extensions

**Key Features**:
- Automatic parameter tree rendering with QtreeWidget
- Dashboard integration for accessing control modules
- Dock-based UI layout system
- Built-in settings management and persistence

### Extension vs Standalone Applications

**Critical Difference**: 
> "The big difference between extensions and Standalone apps resides in the fact that your dashboard instance is available here, hence all the control modules it contains."

**Extension Benefits**:
- Direct access to dashboard's initialized control modules
- Shared device management through ModulesManager
- Integrated data flow and synchronization
- Common configuration and preset system

### Extension Discovery and Registration

**Required Package Structure**:
```
src/pymodaq_plugins_urashg/
├── extensions/
│   ├── __init__.py
│   └── urashg_microscopy_extension.py
```

**Extension Module Requirements**:
```python
# Three mandatory attributes per extension module
EXTENSION_NAME = 'μRASHG Microscopy'  # Display name in dashboard menu
CLASS_NAME = 'URASHGMicroscopyExtension'  # Class name for instantiation
# Class deriving from CustomApp base class
```

**plugin_info.toml Configuration**:
```toml
[features]
instruments = true      # Has individual device plugins
extensions = true       # Has extension modules ⭐ ENABLE THIS
models = false
h5exporters = false
scanners = false
```

## 2. Multi-Device Coordination Architecture

### ModulesManager System

**Purpose**: Central coordination hub for multi-device management

**Key Capabilities**:
- Selection of actuators and detectors by user
- Internal facilities to manipulate multiple devices
- Probe lists for all data exports from selected detectors
- Test actuator positioning and synchronization

**Access Pattern in Extensions**:
```python
class URASHGMicroscopyExtension(CustomApp):
    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)
        # Access to dashboard's control modules
        self.modules_manager = dashboard.modules_manager
        # Direct device access through dashboard
```

### Dashboard Integration Patterns

**Dashboard Role**: 
> "This is a graphical component that will initialize actuators and detectors given the need of your particular experiment. You configure the dashboard using an interface for quick launch of various configurations."

**Multi-Device Coordination Features**:
- Sequential scans as function of 1, 2...N actuators
- Tabular coordinate lists in actuator phase space
- Synchronized data acquisition from multiple detectors
- Common timing and trigger management

### Device Management Patterns

**Individual Plugin Integration**:
```python
# Extension can coordinate existing plugins:
# - DAQ_Move_Elliptec (3x rotation mounts)
# - daq_2Dviewer_PrimeBSI (camera)
# - DAQ_0DViewer_Newport1830C (power meter)
# - DAQ_Move_MaiTai (laser control)
# - PyRPL_PID (FPGA control)
```

## 3. Extension UI/UX Architecture

### Parameter Tree Integration

**Built-in Settings Tree**: Extensions automatically get settings tree rendering through `self.settings_tree`

**Parameter Definition Pattern**:
```python
class URASHGMicroscopyExtension(CustomApp):
    params = [
        {'title': 'Measurement Settings:', 'name': 'measurement', 'type': 'group', 'children': [
            {'title': 'Polarization Steps:', 'name': 'pol_steps', 'type': 'int', 'value': 36},
            {'title': 'Integration Time (ms):', 'name': 'integration_time', 'type': 'int', 'value': 100},
            {'title': 'Wavelength (nm):', 'name': 'wavelength', 'type': 'int', 'value': 800},
        ]},
        {'title': 'Hardware Settings:', 'name': 'hardware', 'type': 'group', 'children': [
            {'title': 'QWP Device ID:', 'name': 'qwp_id', 'type': 'str', 'value': '0'},
            {'title': 'HWP Incident ID:', 'name': 'hwp_inc_id', 'type': 'str', 'value': '1'},
            {'title': 'HWP Analyzer ID:', 'name': 'hwp_ana_id', 'type': 'str', 'value': '2'},
        ]},
    ]
```

### Dock-Based Layout System

**Mandatory Method**: `setup_docks()`
```python
def setup_docks(self):
    """Define dock layout for Extension UI"""
    # Control panel dock
    self.docks['Control'] = gutils.Dock('μRASHG Control')
    self.dockarea.addDock(self.docks['Control'])
    
    # Live preview dock
    self.docks['Preview'] = gutils.Dock('Live Preview')
    self.dockarea.addDock(self.docks['Preview'], 'right', self.docks['Control'])
    
    # Data visualization dock
    self.docks['Results'] = gutils.Dock('RASHG Results')
    self.dockarea.addDock(self.docks['Results'], 'bottom', self.docks['Preview'])
```

### Action Management System

**Mandatory Method**: `setup_actions()`
```python
def setup_actions(self):
    """Define user actions and toolbar buttons"""
    self.add_action('start_measurement', 'Start μRASHG', 'play', 
                   "Start polarimetric measurement", checkable=True)
    self.add_action('stop_measurement', 'Stop', 'stop', 
                   "Stop current measurement")
    self.add_action('save_data', 'Save', 'SaveAs', 
                   "Save measurement results")
    self.add_action('load_config', 'Load Config', 'Open', 
                   "Load measurement configuration")
```

### Menu Integration

**Optional Method**: `setup_menu()`
```python
def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
    """Create menu structure"""
    file_menu = menubar.addMenu('File')
    self.affect_to('load_config', file_menu)
    self.affect_to('save_data', file_menu)
    
    measurement_menu = menubar.addMenu('Measurement')
    self.affect_to('start_measurement', measurement_menu)
    self.affect_to('stop_measurement', measurement_menu)
```

## 4. Data Management Architecture

### PyMoDAQ 5.x Data Structures

**Primary Data Types**:
- `DataWithAxes`: Core data container with metadata and axis information
- `DataToExport`: Multi-channel data collection for export/saving
- `Axis`: Dimensional axis definition with units and scaling

**Data Creation Pattern**:
```python
from pymodaq.utils.data import DataWithAxes, Axis, DataSource

# Create measurement data
rashg_data = DataWithAxes(
    name='μRASHG_Measurement',
    data=[intensity_array],
    axes=[
        Axis('Polarization', data=polarization_angles, units='°'),
        Axis('Wavelength', data=wavelength_axis, units='nm')
    ],
    units='counts',
    source=DataSource.raw
)
```

### HDF5 Export System

**Core Architecture**: Built on H5Backend wrapper around pytables, h5py, and h5pyd

**Data Organization Hierarchy**:
```
HDF5 File Structure:
├── Detector_Node/
│   ├── CH00/ (Camera data)
│   │   ├── Data
│   │   ├── Axes
│   │   └── Metadata
│   ├── CH01/ (Power meter data)
│   └── Navigation_Axes/ (Shared polarization axis)
├── Actuator_Node/
│   ├── Elliptec_Positions/
│   └── MaiTai_Wavelength/
└── Experiment_Metadata/
```

**Advanced Data Management Classes**:
- `AxisSaverLoader`: Axis-specific save/load operations
- `DataSaverLoader`: DataWithAxes save/load with metadata
- `DataToExportSaver`: Multi-device data collection export
- `DataLoader`: Specialized loading with navigation axes

### FAIR Data Compliance

**Key Features**:
- Hierarchical binary format with experimental metadata
- FAIR compliant (Findable, Accessible, Interoperable, Reusable)
- Integrated H5Browser for file exploration and visualization
- Extended arrays for scan data population
- Enlargeable arrays for unknown final lengths

### Multi-Device Data Synchronization

**Data Flow Pattern**:
```python
# Coordinate multiple device data streams
def collect_synchronized_data(self):
    """Collect data from all devices with common timing"""
    # Trigger camera acquisition
    camera_data = self.modules_manager.get_detector_data('PrimeBSI')
    
    # Read power meter
    power_data = self.modules_manager.get_detector_data('Newport1830C')
    
    # Get actuator positions
    qwp_pos = self.modules_manager.get_actuator_value('Elliptec_QWP')
    hwp_inc_pos = self.modules_manager.get_actuator_value('Elliptec_HWP_Inc')
    
    # Create synchronized data export
    export_data = DataToExport(name='μRASHG_Synchronized')
    export_data.append(camera_data)
    export_data.append(power_data)
```

## 5. Production-Ready Implementation Patterns

### Extension Template Structure

**Based on PyMoDAQ Template Analysis**:
```python
from qtpy import QtWidgets
from pymodaq_gui import utils as gutils
from pymodaq_utils.config import Config, ConfigError
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path
from pymodaq.extensions.utils import CustomExt
from pymodaq_plugins_urashg.utils import Config as PluginConfig

logger = set_logger(get_module_name(__file__))

EXTENSION_NAME = 'μRASHG Microscopy'
CLASS_NAME = 'URASHGMicroscopyExtension'

class URASHGMicroscopyExtension(CustomExt):
    params = [
        # Parameter tree definition
    ]
    
    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)
        self.setup_ui()
        
    def setup_docks(self):
        """Implement dock layout"""
        
    def setup_actions(self):
        """Implement user actions"""
        
    def connect_things(self):
        """Connect signals and slots"""
        
    def value_changed(self, param):
        """Handle parameter changes"""
```

### Configuration and Preset Integration

**Plugin Configuration**: Access through `PluginConfig()` instance
**Dashboard Presets**: Integration with PyMoDAQ preset system
**Settings Persistence**: Automatic parameter tree state saving

### Error Handling and Logging

**Logging Pattern**:
```python
logger = set_logger(get_module_name(__file__))

try:
    # Extension operations
    logger.info("μRASHG measurement started")
except Exception as e:
    logger.error(f"Measurement failed: {e}")
```

### Testing and Validation

**Extension Testing Strategy**:
- Mock device testing for development
- Hardware integration testing with real devices
- Dashboard integration verification
- Data export validation with HDF5 files

## 6. Specific μRASHG Implementation Recommendations

### Device Coordination Strategy

**Sequential Polarization Control**:
1. QWP rotation for circular polarization states
2. HWP incident rotation for linear polarization variation
3. HWP analyzer rotation for detection polarization analysis
4. Camera integration time synchronization
5. Power meter readings for normalization

### Measurement Workflow Integration

**Based on Existing Experiment Framework**:
- Leverage existing `URASHGBaseExperiment` patterns
- Integrate with established calibration data loading
- Maintain compatibility with existing data structures
- Preserve hardware abstraction patterns

### Data Visualization Integration

**Real-time Plotting**:
- Live RASHG polar plot updates
- Camera ROI preview with overlay
- Power stability monitoring
- Wavelength-dependent measurements

### Performance Optimization

**Multi-threading Considerations**:
- Background data acquisition threads
- Non-blocking UI updates during measurements
- Efficient data buffering for continuous acquisition
- Hardware polling optimization

## 7. Entry Point Configuration

### plugin_info.toml Setup

```toml
[features]
instruments = true
extensions = true     # ⭐ Enable extensions
models = false
h5exporters = false
scanners = false

[urls]
package-url = 'https://github.com/yourusername/pymodaq_plugins_urashg'
```

### pyproject.toml Entry Points

```toml
[project.entry-points."pymodaq.extensions"]
urashg_microscopy = "pymodaq_plugins_urashg.extensions"
```

## 8. Migration Path from Current System

### Phase 1: Extension Framework Setup
- Create extensions directory structure
- Implement basic CustomApp-derived class
- Configure entry points and discovery

### Phase 2: Device Integration
- Integrate existing working plugins through ModulesManager
- Implement coordinated device control
- Establish synchronized data acquisition

### Phase 3: Advanced Features
- Real-time visualization and analysis
- Advanced measurement sequences
- Data export and analysis integration
- Performance optimization and testing

### Phase 4: Production Deployment
- Comprehensive testing with hardware
- Documentation and user guides
- Integration with existing experiment workflows
- Performance validation and optimization

## Conclusion

The PyMoDAQ Extension architecture provides a robust framework for implementing sophisticated multi-device microscopy systems. The μRASHG Extension can leverage the existing plugin infrastructure while providing coordinated control and advanced data management capabilities. The research indicates clear implementation pathways with production-ready patterns and comprehensive integration strategies.

**Key Success Factors**:
- CustomApp base class provides solid foundation
- ModulesManager enables seamless multi-device coordination
- HDF5 system supports complex experimental data structures
- Extension discovery mechanism integrates with PyMoDAQ ecosystem
- Existing device plugins provide tested hardware interfaces

**Next Steps**: Proceed with Extension implementation following the documented patterns and architectural guidelines.