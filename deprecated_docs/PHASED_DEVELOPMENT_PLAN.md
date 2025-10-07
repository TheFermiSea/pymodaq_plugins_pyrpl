# Phased Development Plan: PyRPL-PyMoDAQ Integration

**Date**: 2025-10-01  
**Purpose**: Three-phase approach from prototype to production-ready custom plugin

---

## 🎯 **Overview**

This document outlines a pragmatic, phased approach that balances rapid prototyping with long-term maintainability:

1. **Phase 1**: TCP Architecture (Prototype) - Quick validation
2. **Phase 2**: Custom Plugin (Production) - Centralized, maintainable
3. **Phase 3**: GUI Replication (Full UI) - Rich PyMoDAQ interface

---

## 📋 **Phase 1: TCP Architecture (The "Prototype")**

### **Goal**: Proof of Concept

Get a functional prototype running quickly to validate communication with each PyRPL module.

### **Architecture**:
```
PyMoDAQ Dashboard
├── DAQ_Viewer_TCP "Scope"  (localhost:6341) ┐
├── DAQ_Viewer_TCP "IQ0"    (localhost:6342) │
├── DAQ_Move_TCP   "ASG0"   (localhost:6345) ├─ Multiple servers
└── DAQ_Move_TCP   "PID0"   (localhost:6347) ┘  Shared PyRPL instance
```

### **Implementation**:

**Server Script** (`pyrpl_tcp_server.py`):
```python
#!/usr/bin/env python
"""
TCP Server for PyRPL modules.
Each server instance handles one module type.
"""
import argparse
import threading
from pymodaq.utils.tcp_ip.tcp_server_client import TCPServer
from pyrpl import Pyrpl

# Global singleton for shared PyRPL instance
_shared_pyrpl = None
_pyrpl_lock = threading.Lock()

def get_shared_pyrpl(hostname, config):
    """Get or create the shared PyRPL instance."""
    global _shared_pyrpl
    with _pyrpl_lock:
        if _shared_pyrpl is None:
            print(f"Initializing PyRPL (hostname={hostname}, config={config})")
            _shared_pyrpl = Pyrpl(config=config, hostname=hostname, gui=False)
        return _shared_pyrpl

class PyRPLModuleServer(TCPServer):
    """TCP Server for a specific PyRPL module."""
    
    def __init__(self, module_name, hostname, config):
        # Determine client type based on module
        client_type = 'GRABBER' if module_name in ['scope', 'iq0', 'iq1', 'iq2'] else 'ACTUATOR'
        super().__init__(client_type=client_type)
        
        self.module_name = module_name
        self.pyrpl = get_shared_pyrpl(hostname, config)
        self.module = getattr(self.pyrpl.rp, module_name)
        
        print(f"✓ Server for {module_name} ready")
    
    def process_cmds(self, command):
        """Process commands from PyMoDAQ TCP instruments."""
        # TODO: Implement command processing
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--module', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--hostname', default='100.107.106.75')
    parser.add_argument('--config', default='pymodaq')
    args = parser.parse_args()
    
    # Start server
    # TODO: Configure port and start Qt event loop
```

### **Benefits**:
- ✅ Quick to implement and test
- ✅ Validates PyRPL communication
- ✅ Works with data immediately
- ✅ No plugin development needed initially

### **Limitations**:
- ❌ Multiple server processes to manage
- ❌ Minimal UI (generic TCP instrument controls)
- ❌ Less integrated with PyMoDAQ

### **Deliverables**:
- [ ] Working TCP server script
- [ ] Shared PyRPL singleton implementation
- [ ] Test with 2-3 modules (scope, iq0, asg0)
- [ ] Validate concurrent access

---

## 🚀 **Phase 2: Custom Plugin (The "Production" Version)**

### **Goal**: Centralized, Maintainable Production Code

Once the prototype is validated, develop a proper custom plugin that manages the PyRPL instance internally.

### **Architecture**:
```
PyMoDAQ Dashboard
├── PyRPL Scope (Custom Plugin)  ┐
├── PyRPL IQ0   (Custom Plugin)  │
├── PyRPL ASG0  (Custom Plugin)  ├─ All use shared Pyrpl instance
└── PyRPL PID0  (Custom Plugin)  ┘  Managed by plugin base class
```

### **Key Improvement**: 
**Centralized PyRPL Instance Management** - The plugin itself manages the singleton, not external server scripts.

### **Plugin Structure**:

#### **Shared Base Class** (`pyrpl_plugin_base.py`):
```python
"""
Base class for all PyRPL plugins.
Manages the shared PyRPL instance.
"""
from pyrpl import Pyrpl
import threading

# Global singleton for shared PyRPL instance
_shared_pyrpl = None
_pyrpl_lock = threading.Lock()

class PyRPLPluginBase:
    """Base class for PyRPL plugins with shared instance management."""
    
    @staticmethod
    def get_pyrpl(hostname, config):
        """Get or create the shared PyRPL instance."""
        global _shared_pyrpl
        with _pyrpl_lock:
            if _shared_pyrpl is None:
                print(f"Initializing PyRPL (hostname={hostname}, config={config})")
                _shared_pyrpl = Pyrpl(config=config, hostname=hostname, gui=False)
            return _shared_pyrpl
    
    def get_module(self, module_name):
        """Get a specific PyRPL module."""
        pyrpl = self.get_pyrpl(self.hostname, self.config)
        return getattr(pyrpl.rp, module_name)
```

#### **PID Plugin Example** (`daq_move_PyRPL.py`):
```python
"""
PyMoDAQ plugins for PyRPL actuator modules (PID, ASG).
"""
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun
from .pyrpl_plugin_base import PyRPLPluginBase

class DAQ_Move_PyRPL_PID(DAQ_Move_base, PyRPLPluginBase):
    """Plugin for PyRPL PID Controller."""
    
    _controller_units = 'V'
    is_multiaxes = False
    axes_names = []
    _epsilon = 0.001
    
    params = [
        {'title': 'PyRPL Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya IP:', 'name': 'hostname', 'type': 'str', 'value': '100.107.106.75'},
            {'title': 'Config:', 'name': 'config', 'type': 'str', 'value': 'pymodaq'},
            {'title': 'PID Module:', 'name': 'pid_module', 'type': 'list', 
             'limits': ['pid0', 'pid1', 'pid2'], 'value': 'pid0'},
        ]},
        {'title': 'PID Settings:', 'name': 'pid_settings', 'type': 'group', 'children': [
            {'title': 'Setpoint:', 'name': 'setpoint', 'type': 'float', 'value': 0.0},
            {'title': 'P Gain:', 'name': 'p_gain', 'type': 'float', 'value': 0.0},
            {'title': 'I Gain:', 'name': 'i_gain', 'type': 'float', 'value': 0.0},
            {'title': 'D Gain:', 'name': 'd_gain', 'type': 'float', 'value': 0.0},
        ]},
    ]
    
    def ini_attributes(self):
        self.controller = None
        self.hostname = None
        self.config = None
        self.pid = None
    
    def get_actuator_value(self):
        """Read current PID setpoint."""
        return self.pid.setpoint
    
    def close(self):
        """Clean shutdown."""
        # Don't close the shared PyRPL instance - other plugins may still need it
        pass
    
    def commit_settings(self, param):
        """Called when a setting is changed in the UI."""
        if param.name() == 'setpoint':
            self.pid.setpoint = param.value()
        elif param.name() == 'p_gain':
            self.pid.p = param.value()
        elif param.name() == 'i_gain':
            self.pid.i = param.value()
        elif param.name() == 'd_gain':
            self.pid.d = param.value()
    
    def ini_stage(self, controller=None):
        """Initialize the PID module."""
        self.hostname = self.settings.child('connection', 'hostname').value()
        self.config = self.settings.child('connection', 'config').value()
        module_name = self.settings.child('connection', 'pid_module').value()
        
        # Get the PID module from shared PyRPL instance
        self.pid = self.get_module(module_name)
        
        info = f"Connected to PyRPL {module_name}"
        initialized = True
        return info, initialized
    
    def move_abs(self, position):
        """Set PID setpoint."""
        self.pid.setpoint = position
        self.emit_status(ThreadCommand('Update_Status', ['PID setpoint updated']))
    
    def move_rel(self, position):
        """Relative move - adjust setpoint."""
        current = self.pid.setpoint
        self.move_abs(current + position)
    
    def move_home(self):
        """Home - reset integrator."""
        self.pid.integrator = 0
        self.emit_status(ThreadCommand('Update_Status', ['PID integrator reset']))
    
    def stop_motion(self):
        """Stop - could disable PID output."""
        pass
```

#### **Scope Plugin Example** (`daq_viewer_PyRPL.py`):
```python
"""
PyMoDAQ plugins for PyRPL detector modules (Scope, IQ).
"""
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq_data import DataFromPlugins, Axis, DataToExport
from .pyrpl_plugin_base import PyRPLPluginBase
import numpy as np

class DAQ_1Dviewer_PyRPL_Scope(DAQ_Viewer_base, PyRPLPluginBase):
    """Plugin for PyRPL Scope."""
    
    params = comon_parameters + [
        {'title': 'PyRPL Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'Red Pitaya IP:', 'name': 'hostname', 'type': 'str', 'value': '100.107.106.75'},
            {'title': 'Config:', 'name': 'config', 'type': 'str', 'value': 'pymodaq'},
        ]},
        {'title': 'Scope Settings:', 'name': 'scope_settings', 'type': 'group', 'children': [
            {'title': 'Input Channel:', 'name': 'input_channel', 'type': 'list',
             'limits': ['in1', 'in2'], 'value': 'in1'},
            {'title': 'Duration (µs):', 'name': 'duration', 'type': 'float', 'value': 1000.0},
            {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
             'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge'], 
             'value': 'immediately'},
        ]},
    ]
    
    def ini_attributes(self):
        self.controller = None
        self.hostname = None
        self.config = None
        self.scope = None
    
    def commit_settings(self, param):
        """Update scope settings when UI changes."""
        if param.name() == 'input_channel':
            self.scope.input = param.value()
        elif param.name() == 'duration':
            self.scope.duration = param.value() / 1e6  # Convert µs to seconds
        elif param.name() == 'trigger_source':
            self.scope.trigger_source = param.value()
    
    def ini_detector(self, controller=None):
        """Initialize the scope."""
        self.hostname = self.settings.child('connection', 'hostname').value()
        self.config = self.settings.child('connection', 'config').value()
        
        # Get the scope module from shared PyRPL instance
        self.scope = self.get_module('scope')
        
        # Apply initial settings
        self.scope.input = self.settings.child('scope_settings', 'input_channel').value()
        self.scope.duration = self.settings.child('scope_settings', 'duration').value() / 1e6
        
        info = "Connected to PyRPL Scope"
        initialized = True
        self.status.update(edict(initialized=initialized, info=info, controller=self.scope))
        return self.status
    
    def close(self):
        """Clean shutdown."""
        # Don't close shared PyRPL instance
        pass
    
    def grab_data(self, Naverage=1, **kwargs):
        """Acquire scope trace."""
        # Trigger acquisition
        self.scope.trigger()
        
        # Wait for completion
        while self.scope.is_running():
            QtWidgets.QApplication.processEvents()
        
        # Get data
        data = self.scope.curve()
        times = self.scope.times  # Time axis
        
        # Create DataFromPlugins object
        data_out = DataFromPlugins(
            name='PyRPL Scope',
            data=[data],
            axes=[Axis('Time', 's', data=times)],
            labels=['Voltage']
        )
        
        self.data_grabed_signal.emit([DataToExport('PyRPL Scope', data=[data_out])])
```

### **Benefits**:
- ✅ Centralized PyRPL instance management
- ✅ Standard PyMoDAQ plugin structure
- ✅ Easier to maintain and extend
- ✅ No external server processes
- ✅ Better integrated with PyMoDAQ

### **Deliverables**:
- [ ] PyRPLPluginBase class with singleton management
- [ ] PID plugin (DAQ_Move_PyRPL_PID)
- [ ] ASG plugin (DAQ_Move_PyRPL_ASG)
- [ ] Scope plugin (DAQ_1Dviewer_PyRPL_Scope)
- [ ] IQ plugin (DAQ_0Dviewer_PyRPL_IQ)
- [ ] Test all plugins in dashboard

---

## 🎨 **Phase 3: GUI Replication (Full UI)**

### **Goal**: Replicate PyRPL's GUI in PyMoDAQ

Create a rich, module-specific interface using PyMoDAQ's settings tree and custom widgets.

### **PID Controller UI**:

**Settings Tree**:
```python
params = [
    # ... connection settings ...
    {'title': 'PID Settings:', 'name': 'pid_settings', 'type': 'group', 'children': [
        {'title': 'Setpoint:', 'name': 'setpoint', 'type': 'float', 'value': 0.0, 'suffix': 'V'},
        {'title': 'P Gain:', 'name': 'p', 'type': 'float', 'value': 0.0},
        {'title': 'I Gain:', 'name': 'i', 'type': 'float', 'value': 0.0},
        {'title': 'D Gain:', 'name': 'd', 'type': 'float', 'value': 0.0},
        {'title': 'Input Filter:', 'name': 'inputfilter', 'type': 'list',
         'limits': ['off', '10kHz', '100kHz', '1MHz']},
        {'title': 'Integrator:', 'name': 'integrator', 'type': 'float', 'value': 0.0, 'readonly': True},
    ]},
    {'title': 'Input/Output:', 'name': 'io', 'type': 'group', 'children': [
        {'title': 'Input:', 'name': 'input', 'type': 'list',
         'limits': ['in1', 'in2', 'iq0', 'iq1', 'iq2']},
        {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
         'limits': ['off', 'out1', 'out2']},
    ]},
    {'title': 'Actions:', 'name': 'actions', 'type': 'group', 'children': [
        {'title': 'Reset Integrator', 'name': 'reset_int', 'type': 'action'},
        {'title': 'Enable PID', 'name': 'enable', 'type': 'bool', 'value': False},
    ]},
]
```

**Live Monitoring**:
- Use DAQ_Viewer to display PID input, output, and error signals
- Update in real-time (continuous acquisition mode)

### **Scope UI**:

**Settings Tree**:
```python
params = [
    # ... connection settings ...
    {'title': 'Scope Settings:', 'name': 'scope_settings', 'type': 'group', 'children': [
        {'title': 'Input Channel:', 'name': 'input', 'type': 'list',
         'limits': ['in1', 'in2', 'asg0', 'asg1', 'pid0', 'pid1', 'pid2']},
        {'title': 'Duration:', 'name': 'duration', 'type': 'float', 'value': 1000.0, 'suffix': 'µs'},
        {'title': 'Trigger Source:', 'name': 'trigger_source', 'type': 'list',
         'limits': ['immediately', 'ch1_positive_edge', 'ch1_negative_edge',
                    'ch2_positive_edge', 'ch2_negative_edge', 'ext_positive_edge']},
        {'title': 'Trigger Level:', 'name': 'threshold', 'type': 'float', 'value': 0.0, 'suffix': 'V'},
        {'title': 'Trigger Delay:', 'name': 'trigger_delay', 'type': 'float', 'value': 0.0, 'suffix': 'µs'},
        {'title': 'Averaging:', 'name': 'average', 'type': 'bool', 'value': False},
    ]},
    {'title': 'Display:', 'name': 'display', 'type': 'group', 'children': [
        {'title': 'Rolling Mode:', 'name': 'rolling_mode', 'type': 'bool', 'value': False},
        {'title': 'XY Mode:', 'name': 'xy_mode', 'type': 'bool', 'value': False},
    ]},
]
```

### **ASG UI**:

**Settings Tree**:
```python
params = [
    # ... connection settings ...
    {'title': 'Signal Generator:', 'name': 'asg_settings', 'type': 'group', 'children': [
        {'title': 'Waveform:', 'name': 'waveform', 'type': 'list',
         'limits': ['sin', 'square', 'triangle', 'halframp', 'ramp', 'noise', 'dc']},
        {'title': 'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 1000.0, 'suffix': 'Hz'},
        {'title': 'Amplitude:', 'name': 'amplitude', 'type': 'float', 'value': 1.0, 'suffix': 'V'},
        {'title': 'Offset:', 'name': 'offset', 'type': 'float', 'value': 0.0, 'suffix': 'V'},
        {'title': 'Phase:', 'name': 'phase', 'type': 'float', 'value': 0.0, 'suffix': '°'},
    ]},
    {'title': 'Output:', 'name': 'output', 'type': 'group', 'children': [
        {'title': 'Output Direct:', 'name': 'output_direct', 'type': 'list',
         'limits': ['off', 'out1', 'out2', 'both']},
    ]},
    {'title': 'Actions:', 'name': 'actions', 'type': 'group', 'children': [
        {'title': 'Start', 'name': 'start', 'type': 'action'},
        {'title': 'Stop', 'name': 'stop', 'type': 'action'},
    ]},
]
```

### **Implementation Pattern**:

```python
def commit_settings(self, param):
    """Map PyMoDAQ settings to PyRPL module properties."""
    # Navigate the parameter tree
    if param.parent().name() == 'pid_settings':
        # PID parameter changed
        if param.name() == 'setpoint':
            self.pid.setpoint = param.value()
        elif param.name() == 'p':
            self.pid.p = param.value()
        # ... etc for all parameters
    
    elif param.parent().name() == 'actions':
        # Action button pressed
        if param.name() == 'reset_int':
            self.pid.integrator = 0
            self.emit_status(ThreadCommand('Update_Status', ['Integrator reset']))
        elif param.name() == 'enable':
            if param.value():
                self.pid.output_direct = 'out1'  # Enable output
            else:
                self.pid.output_direct = 'off'   # Disable output
```

### **Benefits**:
- ✅ Rich, module-specific UI
- ✅ Replicates PyRPL GUI functionality
- ✅ Consistent with PyMoDAQ ecosystem
- ✅ Real-time control and monitoring
- ✅ All PyRPL features accessible

### **Deliverables**:
- [ ] Complete settings trees for all modules
- [ ] Action button handlers
- [ ] Live data plotting for PID/Scope
- [ ] Advanced features (XY mode, rolling mode, etc.)
- [ ] User documentation

---

## 📊 **Phase Comparison**

| Aspect | Phase 1 (TCP) | Phase 2 (Plugin) | Phase 3 (Full UI) |
|--------|---------------|------------------|-------------------|
| **Implementation Time** | 1-2 weeks | 2-4 weeks | 4-6 weeks |
| **PyRPL Management** | External servers | Plugin-managed | Plugin-managed |
| **UI Richness** | Minimal (generic TCP) | Basic (standard settings) | Full (replicated GUI) |
| **Maintainability** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **User Experience** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Integration** | Loose | Tight | Native |

---

## 🎯 **Recommendation**

### **Start with Phase 1** (Current TCP approach):
- Quick validation of concept
- Tests communication patterns
- Gets you working data immediately

### **Transition to Phase 2** once validated:
- More maintainable long-term
- Better PyMoDAQ integration
- Cleaner architecture

### **Implement Phase 3** for production use:
- Full feature parity with PyRPL GUI
- Best user experience
- Production-ready system

---

## ✅ **Current Status**

**Phase 1** (In Progress):
- ✅ Architecture designed (MULTI_MODULE_ARCHITECTURE.md)
- ⏳ TCP server implementation needed
- ⏳ Shared PyRPL singleton needed
- ⏳ Testing with multiple modules

**Phase 2** (Not Started):
- ⏳ Plugin structure design
- ⏳ PyRPLPluginBase implementation
- ⏳ Individual module plugins

**Phase 3** (Not Started):
- ⏳ Complete settings trees
- ⏳ Action handlers
- ⏳ Live plotting

---

**This phased approach balances rapid prototyping with long-term production quality!**
