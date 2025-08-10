# PyMoDAQ Extension Development Patterns - Lessons Learned

## Extension Architecture Best Practices

### CustomApp Base Class Implementation
**Pattern**: Inherit from `CustomApp` for comprehensive multi-device extensions
```python
from pymodaq.extensions.custom_app import CustomApp

class URASHGMicroscopyExtension(CustomApp):
    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        # Extension-specific initialization
```

**Key Benefits**:
- Automatic PyMoDAQ framework integration
- Standard extension lifecycle management  
- Built-in dock management capabilities
- Access to dashboard modules and resources

### Dock-Based UI Layout Strategy
**Pattern**: Use specialized docks for different functional areas
```python
self.docks = {}
dock_configs = [
    ('control_panel', 'Control Panel', 'bottom'),
    ('device_control', 'Device Control', 'left'), 
    ('camera_preview', 'Camera Preview', 'right'),
    ('analysis_plots', 'Analysis Plots', 'top'),
    ('status_monitor', 'Status Monitor', 'bottom')
]

for dock_name, title, position in dock_configs:
    self.docks[dock_name] = self.dockarea.add_dock(
        name=dock_name, title=title, position=position
    )
```

**Advantages**:
- Modular UI organization
- User-customizable layout
- Clear separation of functionality
- Professional appearance

### Parameter Tree Organization
**Pattern**: Hierarchical parameter structure with logical grouping
```python
params = [
    {'name': 'experiment', 'type': 'group', 'children': [
        {'name': 'pol_steps', 'type': 'int', 'value': 36, 'min': 1, 'max': 360},
        {'name': 'integration_time', 'type': 'float', 'value': 100.0, 'min': 1.0, 'max': 10000.0, 'suffix': 'ms'},
    ]},
    {'name': 'hardware', 'type': 'group', 'children': [
        {'name': 'camera', 'type': 'group', 'children': [...]},
        {'name': 'rotators', 'type': 'group', 'children': [...]},
    ]},
]
```

**Best Practices**:
- Group related parameters logically
- Include min/max bounds for validation
- Add units with 'suffix' parameter
- Use descriptive parameter names
- Include 'tip' for user guidance

## Device Management Patterns

### Centralized Device Manager
**Pattern**: Single manager class for all device coordination
```python
class URASHGDeviceManager(QObject):
    # Signals for device status updates
    device_status_changed = Signal(str, str)
    device_error = Signal(str, str)
    all_devices_ready = Signal(bool)
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.modules_manager = dashboard.modules_manager
        self.devices = {}
        self.discover_devices()
```

**Key Features**:
- Device discovery and validation
- Status monitoring with Qt signals
- Coordinated multi-device operations
- Safety checking and error handling

### Device Discovery Strategy
**Pattern**: Pattern matching for flexible device detection
```python
REQUIRED_DEVICES = {
    'camera': {
        'type': 'viewer',
        'name_patterns': ['PrimeBSI', 'Camera'],
        'description': 'Primary camera for SHG detection',
        'required': True,
    },
    # ... other devices
}

def _find_device_module(self, device_key, device_config):
    device_type = device_config['type']
    name_patterns = device_config['name_patterns']
    
    modules = self.available_modules.get(device_type, {})
    for module_name in modules.keys():
        for pattern in name_patterns:
            if pattern.lower() in module_name.lower():
                return DeviceInfo(device_key, device_type, module_name)
```

**Advantages**:
- Flexible device naming
- Graceful handling of missing devices
- Clear device type organization
- Extensible device configuration

## Threading and Signal Patterns

### Thread-Safe Measurement Workers
**Pattern**: Use Qt threading with moveToThread for non-blocking operations
```python
class MeasurementWorker(QObject):
    progress_updated = Signal(int, str)
    measurement_complete = Signal(dict)
    error_occurred = Signal(str)
    
    def run_measurement(self):
        try:
            # Long-running measurement operations
            self.progress_updated.emit(50, "Acquiring data...")
            # ... measurement logic
            self.measurement_complete.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))

# Usage in extension
self.worker = MeasurementWorker()
self.measurement_thread = QThread()
self.worker.moveToThread(self.measurement_thread)
self.worker.progress_updated.connect(self.update_progress)
```

**Critical Points**:
- Always use moveToThread, never subclass QThread
- Use Qt signals for thread communication
- Proper cleanup with thread.quit() and thread.wait()
- No direct GUI updates from worker threads

### Real-Time Status Monitoring
**Pattern**: Timer-based status updates with Qt signals
```python
class URASHGDeviceManager(QObject):
    def __init__(self):
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_all_device_status)
        self.status_timer.setInterval(5000)  # 5 seconds
    
    def update_all_device_status(self):
        for device_key in self.devices.keys():
            old_status = self.devices[device_key].status
            new_status = self.check_device_status(device_key)
            if old_status != new_status:
                self.device_status_changed.emit(device_key, new_status.value)
```

**Benefits**:
- Non-blocking status updates
- Real-time user feedback
- Early error detection
- System health monitoring

## Data Structure Patterns

### PyMoDAQ 5.x Data Structures
**Pattern**: Proper DataWithAxes usage with source specification
```python
from pymodaq.utils.data import DataWithAxes, Axis, DataSource

def create_measurement_data(self, image_data, x_axis, y_axis):
    return DataWithAxes(
        'RASHG_Measurement',
        data=[image_data],
        axes=[
            Axis('x', data=x_axis, units='pixels'),
            Axis('y', data=y_axis, units='pixels')
        ],
        units='counts',
        source=DataSource.raw  # Required for PyMoDAQ 5.x
    )
```

### DataActuator Patterns
**CRITICAL**: Different patterns for single vs multi-axis devices
```python
# Single-axis devices (MaiTai laser)
def move_abs(self, position: Union[float, DataActuator]):
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # Use .value()!

# Multi-axis devices (Elliptec rotators)  
def move_abs(self, positions: Union[List[float], DataActuator]):
    if isinstance(positions, DataActuator):
        target_array = positions.data[0]  # Use .data[0]!
```

**Common Mistake**: Using `.data[0][0]` for single-axis devices causes UI failures!

## Configuration Management

### JSON-Based Configuration
**Pattern**: Hierarchical configuration with validation
```python
def save_configuration(self, filepath: str):
    config = {
        'experiment': {
            'pol_steps': self.settings.child('experiment', 'pol_steps').value(),
            'integration_time': self.settings.child('experiment', 'integration_time').value(),
        },
        'hardware': {
            'camera': {
                'roi': self.get_camera_roi_settings(),
            },
        },
        # ... other sections
    }
    
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)

def load_configuration(self, filepath: str):
    with open(filepath, 'r') as f:
        config = json.load(f)
    
    # Validate configuration structure
    self.validate_configuration(config)
    
    # Apply configuration to parameters
    self.apply_configuration(config)
```

### Configuration Validation
**Pattern**: Type and range checking for loaded configurations
```python
def validate_configuration(self, config: dict):
    errors = []
    
    # Check required sections
    required_sections = ['experiment', 'hardware']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate parameter values
    if 'experiment' in config:
        pol_steps = config['experiment'].get('pol_steps', 0)
        if not isinstance(pol_steps, int) or pol_steps < 1 or pol_steps > 360:
            errors.append(f"Invalid pol_steps: {pol_steps}")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {errors}")
```

## Analysis and Curve Fitting

### RASHG Model Implementation
**Pattern**: Scipy-based curve fitting with error handling
```python
from scipy.optimize import curve_fit

def rashg_model(angle, I0, phi, offset):
    """RASHG intensity model: I = I0 * sin^2(2*(angle - phi)) + offset"""
    angle_rad = np.deg2rad(angle)
    phi_rad = np.deg2rad(phi)
    return I0 * np.sin(2 * (angle_rad - phi_rad))**2 + offset

def fit_rashg_curve(self, angles, intensities):
    try:
        # Initial parameter guess
        I0_guess = np.max(intensities) - np.min(intensities)
        phi_guess = angles[np.argmax(intensities)] / 2  # Approximate phase
        offset_guess = np.min(intensities)
        
        popt, pcov = curve_fit(
            rashg_model, 
            angles, 
            intensities, 
            p0=[I0_guess, phi_guess, offset_guess]
        )
        
        # Calculate fitting quality metrics
        residuals = intensities - rashg_model(angles, *popt)
        r_squared = 1 - (np.sum(residuals**2) / np.sum((intensities - np.mean(intensities))**2))
        
        return {
            'parameters': popt,
            'covariance': pcov,
            'r_squared': r_squared,
            'success': True
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

### Data Quality Assessment
**Pattern**: Comprehensive data validation before analysis
```python
def assess_data_quality(self, angles, intensities):
    issues = []
    
    # Check for empty data
    if len(angles) == 0 or len(intensities) == 0:
        issues.append("Empty data arrays provided")
        return issues
    
    # Check array length matching
    if len(angles) != len(intensities):
        issues.append(f"Array length mismatch: {len(angles)} vs {len(intensities)}")
    
    # Check minimum data points
    if len(angles) < 18:
        issues.append(f"Insufficient data points: {len(angles)} < 18")
    
    # Check angle coverage
    if len(angles) > 1:
        angle_range = np.max(angles) - np.min(angles)
        if angle_range < 90:
            issues.append(f"Insufficient angle coverage: {angle_range:.1f}° < 90°")
    
    # Check for reasonable intensity values
    if len(intensities) > 0:
        if np.max(intensities) <= 0:
            issues.append("All intensity values are non-positive")
    
    return issues
```

## Error Handling and Safety

### Comprehensive Error Handling
**Pattern**: Multi-level error handling with user feedback
```python
def safe_device_operation(self, operation_func, device_name, *args, **kwargs):
    try:
        logger.info(f"Starting {operation_func.__name__} on {device_name}")
        result = operation_func(*args, **kwargs)
        logger.info(f"Successfully completed {operation_func.__name__}")
        return result, None
        
    except TimeoutError as e:
        error_msg = f"Timeout during {operation_func.__name__} on {device_name}: {e}"
        logger.error(error_msg)
        self.show_error_message(error_msg)
        return None, error_msg
        
    except ConnectionError as e:
        error_msg = f"Connection failed for {device_name}: {e}"
        logger.error(error_msg)
        self.show_error_message(error_msg)
        return None, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error in {operation_func.__name__}: {e}"
        logger.error(error_msg, exc_info=True)
        self.show_error_message(error_msg)
        return None, error_msg
```

### Safety Interlocks
**Pattern**: Parameter validation before operations
```python
def check_safety_limits(self, settings):
    violations = []
    
    # Power limits
    max_power = settings.child('hardware', 'safety', 'max_power').value()
    if max_power > 90.0:
        violations.append(f"Power limit too high: {max_power}% (max: 90%)")
    
    # Timeout settings
    movement_timeout = settings.child('hardware', 'safety', 'movement_timeout').value()
    if movement_timeout > 60.0:
        violations.append(f"Movement timeout too long: {movement_timeout}s")
    
    # ROI size validation
    roi_width = settings.child('hardware', 'camera', 'roi', 'width').value()
    roi_height = settings.child('hardware', 'camera', 'roi', 'height').value()
    if roi_width * roi_height > 2048 * 2048:
        violations.append(f"ROI too large: {roi_width}x{roi_height}")
    
    return violations
```

## Testing Strategies

### Comprehensive Test Suite Structure
**Pattern**: Multiple test levels with clear separation
```python
def run_comprehensive_tests():
    tests = [
        ("Extension Import and Initialization", test_extension_import),
        ("Parameter Tree Structure", test_parameter_validation),
        ("Device Manager Logic", test_device_manager),
        ("Device Control Methods", test_device_controls),
        ("Measurement Sequences", test_measurement_framework),
        ("Configuration Management", test_config_save_load),
        ("Analysis and Curve Fitting", test_analysis_functions),
        ("Error Handling", test_error_cases)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
    
    return passed, len(tests)
```

### Mock-Based Testing  
**Pattern**: Comprehensive mocking for hardware-independent testing
```python
class MockSettings:
    def __init__(self, values_dict):
        self.values = values_dict
    
    def child(self, *path):
        return MockParameter(self.values.get('.'.join(path), 0))

class MockParameter:
    def __init__(self, value):
        self._value = value
    
    def value(self):
        return self._value

# Usage in tests
mock_settings = MockSettings({
    'experiment.pol_steps': 36,
    'experiment.integration_time': 100.0,
})
```

## Key Development Lessons

### Critical Success Factors
1. **PyMoDAQ Standards Compliance**: Following PyMoDAQ patterns exactly is essential
2. **Threading Safety**: Proper Qt threading prevents crashes and ensures stability
3. **Comprehensive Testing**: 8-level test suite catches issues before production
4. **Device Abstraction**: Clean separation between plugins and hardware controllers
5. **Configuration Management**: Professional configuration system enhances usability

### Common Pitfalls to Avoid
1. **DataActuator Pattern Mixing**: Single vs multi-axis patterns are different!
2. **Threading Violations**: Never update GUI directly from worker threads
3. **Resource Leaks**: Always implement proper cleanup methods
4. **Parameter Validation**: Validate all user inputs before operations
5. **Error Handling**: Silent failures lead to user confusion and data loss

### Performance Optimization Tips
1. **Signal Batching**: Batch similar signals to reduce UI update frequency
2. **Data Caching**: Cache expensive calculations and device queries
3. **Lazy Loading**: Load complex components only when needed
4. **Memory Management**: Clean up large data arrays promptly
5. **Status Polling**: Use reasonable intervals for device status updates (5s recommended)

This comprehensive pattern guide provides the foundation for developing professional-grade PyMoDAQ extensions that integrate seamlessly with the framework while providing advanced functionality for research applications.