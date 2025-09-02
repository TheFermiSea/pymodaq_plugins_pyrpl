# PyMoDAQ Compliance Analysis Report for pymodaq_plugins_urashg

## Executive Summary

This report analyzes the current pymodaq_plugins_urashg implementation against PyMoDAQ v5.x standards and provides specific recommendations for improving compliance and leveraging PyMoDAQ's built-in features.

## Current Implementation Assessment

### Strengths
- **Plugin Functionality**: All individual plugins (Elliptec, ESP300, MaiTai, PrimeBSI, Newport1830C) are working and hardware-tested
- **Test Coverage**: Comprehensive test suite with 37/37 tests passing
- **Extension Framework**: Basic extension structure implemented
- **Parameter Structure**: Core parameter compliance achieved

### Critical Gaps

#### 1. Extension Architecture Compliance (CRITICAL)
**Current State**: Custom extension implementation without proper CustomApp inheritance
**PyMoDAQ Standard**: Extensions should inherit from `pymodaq.extensions.utils.CustomExt` or `pymodaq.utils.gui_utils.CustomApp`
**Impact**: Limited dashboard integration, missing built-in features

#### 2. Data Structure Non-Compliance (CRITICAL)
**Current State**: Custom data handling and limited PyMoDAQ data model usage
**PyMoDAQ Standard**: All data should use DataWithAxes, DataToExport, proper Axis definitions
**Impact**: Incompatible with PyMoDAQ analysis tools, limited export capabilities

#### 3. Multi-Device Coordination (HIGH PRIORITY)
**Current State**: Manual device management in extension
**PyMoDAQ Standard**: Use ModulesManager for centralized device coordination
**Impact**: Missing synchronization features, limited scalability

## Detailed Compliance Analysis

### A. Plugin Discovery and Registration

#### Current Implementation:
```python
# pyproject.toml entry points exist but incomplete
[project.entry-points."pymodaq.daq_move"]
urashg_elliptec = "pymodaq_plugins_urashg.hardware.elliptec:DAQ_Move_Elliptec"
```

#### PyMoDAQ Standard:
```toml
# plugin_info.toml should exist
[features]
instruments = true
extensions = true  # ⭐ Currently missing
models = false
h5exporters = false
scanners = false
```

**Recommendation**: Create `plugin_info.toml` with proper feature flags and enable extension discovery.

### B. Extension Architecture 

#### Current Implementation:
```python
class URASHGMicroscopyExtension:
    def __init__(self, dockarea):
        # Custom initialization without PyMoDAQ base class
```

#### PyMoDAQ Standard:
```python
from pymodaq.extensions.utils import CustomExt

class URASHGMicroscopyExtension(CustomExt):
    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)
        # Access to dashboard.modules_manager for device coordination
```

**Recommendation**: Refactor extension to inherit from CustomExt for proper dashboard integration.

### C. Data Management Architecture

#### Current Implementation:
```python
# Custom data handling with basic numpy arrays
measurement_data = np.array([...])
```

#### PyMoDAQ Standard:
```python
from pymodaq.utils.data import DataWithAxes, DataToExport, Axis

# Proper data structure with metadata
rashg_data = DataWithAxes(
    name='μRASHG_Measurement',
    data=[intensity_array],
    axes=[
        Axis('Polarization', data=angles, units='°'),
        Axis('Wavelength', data=wavelengths, units='nm')
    ],
    units='counts'
)
```

**Recommendation**: Migrate all data handling to PyMoDAQ data structures for compatibility and analysis tool integration.

### D. Device Coordination

#### Current Implementation:
```python
# Manual device instantiation and management
self.elliptec_devices = {}
for device_id in ['0', '1', '2']:
    self.elliptec_devices[device_id] = Elliptec(device_id)
```

#### PyMoDAQ Standard:
```python
# Use ModulesManager for centralized device management
class URASHGMicroscopyExtension(CustomExt):
    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.modules_manager = dashboard.modules_manager
        
    def get_device_data(self):
        # Coordinated data acquisition
        camera_data = self.modules_manager.get_detector_data('PrimeBSI')
        power_data = self.modules_manager.get_detector_data('Newport1830C')
```

**Recommendation**: Leverage ModulesManager for device coordination and synchronized measurements.

## Specific Implementation Recommendations

### 1. Extension Architecture Migration (Priority: CRITICAL)

```python
# File: src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py

from pymodaq.extensions.utils import CustomExt
from pymodaq_gui import utils as gutils
from pymodaq.utils.data import DataWithAxes, DataToExport, Axis

EXTENSION_NAME = 'μRASHG Microscopy'
CLASS_NAME = 'URASHGMicroscopyExtension'

class URASHGMicroscopyExtension(CustomExt):
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
    
    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)
        self.modules_manager = dashboard.modules_manager
        self.setup_ui()
        
    def setup_docks(self):
        """Define dock layout for Extension UI"""
        self.docks['Control'] = gutils.Dock('μRASHG Control')
        self.dockarea.addDock(self.docks['Control'])
        
        self.docks['Preview'] = gutils.Dock('Live Preview')
        self.dockarea.addDock(self.docks['Preview'], 'right', self.docks['Control'])
        
    def setup_actions(self):
        """Define user actions and toolbar buttons"""
        self.add_action('start_measurement', 'Start μRASHG', 'play', 
                       "Start polarimetric measurement", checkable=True)
        self.add_action('stop_measurement', 'Stop', 'stop', 
                       "Stop current measurement")
```

### 2. Data Structure Compliance (Priority: CRITICAL)

```python
# Migrate measurement data creation
def create_rashg_data(self, intensity_data, polarization_angles):
    """Create PyMoDAQ compliant data structure"""
    return DataWithAxes(
        name='μRASHG_Measurement',
        data=[intensity_data],
        axes=[
            Axis('Polarization', data=polarization_angles, units='°', 
                 description='Incident polarization angle')
        ],
        units='counts',
        labels=['Intensity']
    )

def export_synchronized_data(self, camera_data, power_data, positions):
    """Export multi-device synchronized data"""
    export_data = DataToExport(name='μRASHG_Synchronized_Measurement')
    export_data.append(camera_data)
    export_data.append(power_data)
    
    # Add position metadata
    for device_id, position in positions.items():
        export_data.append(DataWithAxes(
            name=f'Elliptec_{device_id}_Position',
            data=[position],
            units='°'
        ))
    
    return export_data
```

### 3. Plugin Discovery Configuration (Priority: HIGH)

```toml
# File: plugin_info.toml (CREATE THIS FILE)
[features]
instruments = true      # Has device plugins
extensions = true       # Has extension modules ⭐ ADD THIS
models = false
h5exporters = false
scanners = false

[urls]
package-url = 'https://github.com/yourusername/pymodaq_plugins_urashg'
documentation = 'https://pymodaq-plugins-urashg.readthedocs.io/'

[metadata]
authors = ["Your Name <email@example.com>"]
description = "PyMoDAQ plugins for μRASHG microscopy system with Elliptec mounts, cameras, and lasers"
```

### 4. Hardware Abstraction Improvement (Priority: HIGH)

```python
# File: src/pymodaq_plugins_urashg/utils/hardware_manager.py (CREATE)
from pymodaq_utils.config import Config
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class URASHGHardwareManager:
    """Centralized hardware management following PyMoDAQ patterns"""
    
    def __init__(self):
        self.config = Config()
        self.devices = {}
        self.device_states = {}
        
    def initialize_elliptec_devices(self, device_ids):
        """Initialize Elliptec devices with proper error handling"""
        for device_id in device_ids:
            try:
                # Use existing plugin classes
                device = self.create_device_instance('DAQ_Move_Elliptec', device_id)
                self.devices[f'elliptec_{device_id}'] = device
                logger.info(f"Initialized Elliptec device {device_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Elliptec {device_id}: {e}")
                
    def coordinate_measurement_sequence(self, sequence_params):
        """Coordinate multi-device measurement sequence"""
        # Implement synchronized measurement logic
        pass
```

### 5. Testing Infrastructure Enhancement (Priority: MEDIUM)

```python
# File: tests/test_extension_pymodaq_compliance.py (ENHANCE)
import pytest
from pymodaq.utils.data import DataWithAxes
from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

class TestPyMoDAQCompliance:
    
    def test_data_structure_compliance(self):
        """Test that generated data follows PyMoDAQ standards"""
        extension = URASHGMicroscopyExtension(mock_dockarea, mock_dashboard)
        data = extension.create_rashg_data([1, 2, 3], [0, 90, 180])
        
        assert isinstance(data, DataWithAxes)
        assert len(data.axes) == 1
        assert data.axes[0].units == '°'
        assert data.units == 'counts'
        
    def test_modules_manager_integration(self):
        """Test ModulesManager integration"""
        extension = URASHGMicroscopyExtension(mock_dockarea, mock_dashboard)
        assert hasattr(extension, 'modules_manager')
        assert extension.modules_manager is not None
```

## Implementation Priority and Timeline

### Phase 1: Critical Fixes (1-2 weeks)
1. **Create plugin_info.toml** with proper feature flags
2. **Refactor extension class** to inherit from CustomExt
3. **Implement basic DataWithAxes** data structure compliance
4. **Update entry points** for extension discovery

### Phase 2: Architecture Improvements (2-3 weeks)
1. **Implement ModulesManager integration** for device coordination
2. **Create centralized hardware manager** following PyMoDAQ patterns
3. **Add proper dock layout system** with setup_docks()
4. **Implement action management** with setup_actions()

### Phase 3: Advanced Features (3-4 weeks)
1. **Full data export compliance** with DataToExport
2. **HDF5 integration** for proper data persistence
3. **Real-time visualization** with PyMoDAQ plotting tools
4. **Configuration system migration** to pymodaq_utils.config

### Phase 4: Testing and Validation (1-2 weeks)
1. **Enhanced test suite** with PyMoDAQ compliance tests
2. **Integration testing** with dashboard
3. **Documentation updates** for new architecture
4. **Performance optimization** and validation

## Risk Assessment and Mitigation

### High Risk Items
1. **Breaking existing functionality** during architecture migration
   - **Mitigation**: Incremental migration with extensive testing
2. **Hardware compatibility issues** with new abstraction layers
   - **Mitigation**: Maintain existing hardware interfaces, add new layers gradually

### Medium Risk Items
1. **User interface changes** requiring retraining
   - **Mitigation**: Maintain familiar workflows while adding new features
2. **Performance impact** from additional abstraction layers
   - **Mitigation**: Performance testing and optimization during implementation

## Success Metrics

### Technical Metrics
- [ ] All tests pass (currently 37/37)
- [ ] Extension discoverable in PyMoDAQ dashboard
- [ ] Data structures compatible with PyMoDAQ analysis tools
- [ ] ModulesManager integration functional
- [ ] HDF5 export working with proper metadata

### User Experience Metrics
- [ ] No loss of existing functionality
- [ ] Improved measurement workflow efficiency
- [ ] Better data management and export capabilities
- [ ] Enhanced multi-device coordination

## Conclusion

The pymodaq_plugins_urashg codebase has solid hardware functionality but requires significant architectural improvements to achieve full PyMoDAQ compliance. The recommended migration path provides a structured approach to implementing PyMoDAQ standards while preserving existing functionality. Key benefits of compliance include:

1. **Better Integration**: Seamless dashboard integration and device coordination
2. **Enhanced Data Management**: Proper data structures for analysis and export
3. **Future Compatibility**: Alignment with PyMoDAQ v5+ standards and features
4. **Improved User Experience**: Leveraging PyMoDAQ's built-in UI and workflow patterns
5. **Community Standards**: Following established PyMoDAQ plugin patterns

The implementation should be prioritized based on critical compliance issues first, followed by architectural improvements and advanced features. Regular testing and validation throughout the migration process will ensure successful compliance achievement.