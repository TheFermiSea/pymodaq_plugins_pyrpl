# PyMoDAQ PyRPL Plugin Refactoring Roadmap

This document provides a comprehensive refactoring plan for the `pymodaq_plugins_pyrpl` package to align with PyMoDAQ 5.x standards and follow successful patterns from `pymodaq_plugins_urashg`.

## Executive Summary

The existing PyRPL plugin is well-architected with a sophisticated PyRPL wrapper system, but needs refactoring to:
1. **Follow PyMoDAQ 5.x compliance standards** (class attributes, import patterns, entry points)
2. **Implement comprehensive hardware abstraction** with mock support
3. **Clean up project structure** and documentation
4. **Add missing plugin types** (viewer plugins for IQ and Scope)
5. **Create unified extensions** for complete Red Pitaya control

## Current State Analysis

### Strengths
- **Comprehensive PyRPL wrapper** with thread-safe connection management
- **Advanced compatibility fixes** for Python 3.12+ and Qt6
- **Robust error handling** and logging
- **Production-ready PID plugin** with extensive configuration
- **Hardware validation** confirmed with real Red Pitaya

### Issues to Address
1. **PyMoDAQ 5.x Compliance**: Missing required class attributes and import patterns
2. **Incomplete Plugin Suite**: Only PID move and ASG move plugins exist
3. **Entry Points**: Dynamic entry points need to be explicit
4. **Project Structure**: README.rst needs conversion to README.md
5. **Documentation**: Inconsistent with modern PyMoDAQ standards

## PyRPL Module Mapping to PyMoDAQ Plugins

Based on PyRPL architecture research, here's the optimal mapping:

### Move Plugins (Actuators)
| PyRPL Module | Plugin Class | Function | Status |
|--------------|-------------|----------|--------|
| PID.setpoint | `DAQ_Move_PyRPL_PID` | Hardware PID setpoint control | ✅ Exists |
| ASG.frequency | `DAQ_Move_PyRPL_ASG_Freq` | Signal generator frequency | ⚠️ Needs refactoring |
| ASG.amplitude | `DAQ_Move_PyRPL_ASG_Amp` | Signal generator amplitude | ❌ Missing |
| ASG.phase | `DAQ_Move_PyRPL_ASG_Phase` | Signal generator phase | ❌ Missing |
| IQ.frequency | `DAQ_Move_PyRPL_IQ_Freq` | Lock-in frequency | ❌ Missing |
| IQ.phase | `DAQ_Move_PyRPL_IQ_Phase` | Lock-in phase | ❌ Missing |

### Viewer Plugins (Detectors)
| PyRPL Module | Plugin Class | Data Type | Status |
|--------------|-------------|-----------|--------|
| Scope | `DAQ_1DViewer_PyRPL_Scope` | 1D time series | ❌ Missing |
| IQ (I,Q) | `DAQ_0DViewer_PyRPL_IQ` | 0D lock-in values | ❌ Missing |
| Sampler | `DAQ_0DViewer_PyRPL_Voltage` | 0D voltage monitoring | ❌ Missing |
| Spectrum Analyzer | `DAQ_1DViewer_PyRPL_SA` | 1D frequency spectrum | ❌ Missing |

### Extensions
| Extension | Function | Status |
|-----------|----------|--------|
| `PyRPLManager` | Unified Red Pitaya control | ❌ Missing |
| `PyRPLPIDController` | Advanced PID management | ⚠️ Exists but needs refactoring |

## Refactoring Roadmap

### Phase 1: PyMoDAQ 5.x Compliance
**Priority: Critical**

1. **Update pyproject.toml**
   ```toml
   # Add explicit entry points (no dynamic discovery)
   [project.entry-points."pymodaq.move_plugins"]
   DAQ_Move_PyRPL_PID = "pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID:DAQ_Move_PyRPL_PID"
   DAQ_Move_PyRPL_ASG_Freq = "pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG_Freq:DAQ_Move_PyRPL_ASG_Freq"
   
   [project.entry-points."pymodaq.viewer_plugins"]
   DAQ_0DViewer_PyRPL_Voltage = "pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_Voltage:DAQ_0DViewer_PyRPL_Voltage"
   DAQ_1DViewer_PyRPL_Scope = "pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope:DAQ_1DViewer_PyRPL_Scope"
   
   [project.entry-points."pymodaq.extensions"]
   PyRPLManager = "pymodaq_plugins_pyrpl.extensions.pyrpl_manager"
   ```

2. **Add Required Class Attributes** to all plugins
   ```python
   class DAQ_Move_PyRPL_PID(DAQ_Move_base):
       _controller_units = "V"  # ✅ Already exists
       is_multiaxes = False     # ✅ Already exists
       _axis_names = ["Setpoint"]  # ✅ Already exists
       _epsilon = 0.001         # ✅ Already exists
   ```

3. **Fix Import Patterns**
   ```python
   # Current (incorrect for 5.x)
   from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
   
   # Correct for PyMoDAQ 5.x
   from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun
   from pymodaq_utils.utils import ThreadCommand
   from pymodaq_gui.parameter import Parameter
   ```

### Phase 2: Plugin Suite Completion
**Priority: High**

1. **Create Missing Viewer Plugins**

   **DAQ_0DViewer_PyRPL_Voltage** (voltage monitoring)
   ```python
   class DAQ_0DViewer_PyRPL_Voltage(DAQ_Viewer_base):
       params = [
           {'title': 'Channels', 'name': 'channels', 'type': 'group', 'children': [
               {'title': 'Monitor IN1', 'name': 'monitor_in1', 'type': 'bool', 'value': True},
               {'title': 'Monitor IN2', 'name': 'monitor_in2', 'type': 'bool', 'value': False},
               {'title': 'Monitor PID Output', 'name': 'monitor_pid', 'type': 'bool', 'value': False},
           ]},
           {'title': 'Sampling Rate (Hz)', 'name': 'sampling_rate', 'type': 'float', 
            'value': 10.0, 'min': 0.1, 'max': 1000.0},
       ]
       
       def grab_data(self):
           voltages = []
           if self.settings.child('channels', 'monitor_in1').value():
               v1 = self.controller.read_voltage(InputChannel.IN1)
               voltages.append(v1 if v1 is not None else 0.0)
           # ... similar for other channels
   ```

   **DAQ_1DViewer_PyRPL_Scope** (oscilloscope)
   ```python
   class DAQ_1DViewer_PyRPL_Scope(DAQ_Viewer_base):
       params = [
           {'title': 'Input Channel', 'name': 'input_channel', 'type': 'list',
            'limits': ['in1', 'in2'], 'value': 'in1'},
           {'title': 'Decimation', 'name': 'decimation', 'type': 'list',
            'limits': [1, 8, 64, 1024, 8192, 65536], 'value': 64},
           {'title': 'Averages', 'name': 'averages', 'type': 'int', 
            'value': 1, 'min': 1, 'max': 1000},
       ]
       
       def grab_data(self):
           time_axis, voltage_data = self.controller.acquire_scope_data()
           return [DataFromPlugins(name='Scope', data=[voltage_data], axes=[time_axis])]
   ```

2. **Create Additional Move Plugins**

   **DAQ_Move_PyRPL_ASG_Freq**, **DAQ_Move_PyRPL_ASG_Amp** (split current ASG plugin)
   **DAQ_Move_PyRPL_IQ_Freq**, **DAQ_Move_PyRPL_IQ_Phase** (lock-in control)

### Phase 3: Hardware Abstraction Enhancement
**Priority: High**

1. **Create Mock Hardware Controllers** (following URASHG pattern)
   ```python
   # src/pymodaq_plugins_pyrpl/hardware/pyrpl/mock_controllers.py
   class MockPyRPLConnection:
       def __init__(self):
           self.mock_voltages = {'in1': 0.1, 'in2': 0.2}
           self.mock_pid_setpoints = {'pid0': 0.0, 'pid1': 0.0, 'pid2': 0.0}
           self.mock_scope_data = np.sin(np.linspace(0, 2*np.pi, 16384))
       
       def read_voltage(self, channel):
           return self.mock_voltages.get(channel.value, 0.0) + np.random.normal(0, 0.01)
       
       def acquire_scope_data(self):
           time_axis = np.linspace(0, 1e-3, 16384)  # 1ms duration
           noise = np.random.normal(0, 0.02, 16384)
           return time_axis, self.mock_scope_data + noise
   ```

2. **Enhance PyRPL Wrapper** with Mock Support
   ```python
   class PyRPLConnection:
       def __init__(self, connection_info: ConnectionInfo):
           # ... existing code ...
           self.mock_mode = connection_info.get('mock_mode', False)
           if self.mock_mode:
               from .mock_controllers import MockPyRPLConnection
               self._mock_controller = MockPyRPLConnection()
       
       def connect(self, status_callback=None):
           if self.mock_mode:
               self.state = ConnectionState.CONNECTED
               return True
           # ... existing hardware connection code ...
   ```

### Phase 4: Project Structure Modernization
**Priority: Medium**

1. **Convert README.rst to README.md** (follow URASHG format)
   - Remove excessive formatting and emojis
   - Focus on technical content
   - Add clear installation and usage sections
   - Include PyMoDAQ 5.x compliance status

2. **Update pyproject.toml Structure**
   ```toml
   [project]
   name = "pymodaq_plugins_pyrpl"
   description = "PyMoDAQ plugin package for Red Pitaya STEMlab using PyRPL library"
   dependencies = [
       "pymodaq>=5.0.18",
       "pymodaq-gui>=5.0.24", 
       "pymodaq-data>=5.0.25",
       "pymodaq-utils>=1.0.9",
       "pyrpl>=0.9.5.0",
       "numpy>=1.20.0",
       "scipy>=1.7.0",
   ]
   
   [project.optional-dependencies]
   dev = [
       "pytest>=6.0",
       "pytest-cov>=2.0",
       "pytest-qt>=4.0",
       "black>=21.0",
       "flake8>=3.9",
       "isort>=5.0",
   ]
   ```

3. **Create CLAUDE.md** following URASHG pattern
   - Development commands (uv-based)
   - Architecture overview
   - Plugin entry points
   - Testing strategies
   - PyRPL-specific considerations

### Phase 5: Extension Development
**Priority: Medium**

1. **Create Unified PyRPL Manager Extension**
   ```python
   # src/pymodaq_plugins_pyrpl/extensions/pyrpl_manager.py
   class PyRPLManagerExtension(CustomApp):
       def __init__(self):
           # 5-panel layout similar to URASHG
           # - Control Panel: PID/ASG/IQ configuration
           # - Scope Display: Real-time oscilloscope
           # - Lock-in Display: I/Q measurements
           # - Status Panel: Connection and module status
           # - Advanced Controls: Spectrum analyzer, etc.
   ```

2. **Enhance PID Extension** with unified interface
   - Integrate with main PyRPL manager
   - Add advanced PID tuning features
   - Real-time performance monitoring

### Phase 6: Testing and Validation
**Priority: High**

1. **Create Comprehensive Test Suite** (follow URASHG patterns)
   ```python
   # tests/test_pymodaq_compliance.py
   def test_plugin_structure():
       """Test PyMoDAQ 5.x compliance for all plugins."""
       
   def test_mock_mode():
       """Test all plugins work in mock mode."""
       
   def test_hardware_integration():
       """Test with real Red Pitaya hardware."""
   ```

2. **Add Development Scripts**
   ```bash
   # Development commands using uv
   uv pip install -e .[dev]
   uv run pytest tests/
   uv run black src/
   uv run flake8 src/
   ```

## Implementation Priority

### Critical (Week 1-2)
1. PyMoDAQ 5.x compliance fixes
2. Entry points in pyproject.toml
3. Required class attributes
4. Import pattern fixes

### High Priority (Week 3-4)
1. Missing viewer plugins (Scope, IQ, Voltage)
2. Mock hardware controllers
3. Enhanced hardware abstraction
4. README.md conversion

### Medium Priority (Week 5-6)
1. Additional move plugins (ASG amplitude/phase, IQ controls)
2. Unified extension development
3. Project structure cleanup
4. CLAUDE.md creation

### Future Enhancements
1. Advanced spectrum analyzer plugin
2. Network analyzer functionality
3. Multi-device coordination
4. Performance optimization

## Success Metrics

- **Compliance**: 100% PyMoDAQ 5.x compliance tests passing
- **Plugin Discovery**: All plugins discoverable by PyMoDAQ framework
- **Mock Mode**: Complete functionality without hardware
- **Hardware Validation**: All plugins tested with real Red Pitaya
- **Documentation**: Professional, consistent documentation
- **Code Quality**: Clean, maintainable code following PyMoDAQ patterns

## Migration Strategy

1. **Backup Current State**: Create development branch
2. **Incremental Refactoring**: Implement changes in phases
3. **Continuous Testing**: Maintain functionality throughout refactoring
4. **Documentation Updates**: Keep documentation synchronized
5. **Community Review**: Gather feedback on architecture decisions

This refactoring will transform the PyRPL plugin into a comprehensive, production-ready solution that exemplifies PyMoDAQ 5.x best practices while maintaining the sophisticated PyRPL integration that makes it unique.