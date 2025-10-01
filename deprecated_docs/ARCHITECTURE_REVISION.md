# Architecture Revision: Using Proper PyMoDAQ Patterns

**Date**: 2025-10-01  
**Insight**: We should use PyMoDAQ's existing patterns, not reinvent them

---

## 🔍 **Discovery: PyMoDAQ Has Better Patterns**

After reviewing PyMoDAQ's TCP/IP API documentation and LECO/ZMQ communication patterns, I discovered we were **partially reinventing the wheel**.

### PyMoDAQ Provides Two Communication Patterns:

#### **Option 1: Built-in TCP Instrument Plugins** ⭐ **RECOMMENDED**
PyMoDAQ already has TCP-based instrument plugins that handle the communication:

- **`DAQ_Viewer_TCP`** - For detectors/viewers
- **`DAQ_Move_TCP`** - For actuators/movers

**How it works:**
```
PyMoDAQ Dashboard
  ↓
DAQ_Viewer_TCP Plugin (built-in)
  ↓
TCP Connection (localhost or remote)
  ↓
Custom TCP Server (your code) → PyRPL → Red Pitaya
```

**Key Classes from PyMoDAQ:**
- `TCPServer` - Abstract base for your server
- `TCPClient` - Handles connection and protocol
- `Grabber` - For data acquisition sessions

**Advantages:**
✅ Uses PyMoDAQ's proven infrastructure
✅ Handles serialization automatically
✅ Settings tree integration
✅ Works within PyMoDAQ ecosystem
✅ No custom plugin code needed!

#### **Option 2: LECO Protocol with ZeroMQ**
For devices/drivers written in other languages (LabView, C++, etc.):

- Uses **LECO protocol** (JSON-RPC over ZeroMQ)
- **Coordinator** routes messages
- **Director** (PyMoDAQ) controls
- **Actor** (your device) responds

**How it works:**
```
PyMoDAQ Director
  ↓
LECO Coordinator (ZMQ router)
  ↓
Actor (your program) → PyRPL → Red Pitaya
```

---

## 🎯 **Recommended Approach: Use DAQ_Viewer_TCP & DAQ_Move_TCP**

### **Why This is Better:**

1. **No Custom Plugins Needed** ❌ DELETE our custom TCP plugins
   - PyMoDAQ provides `DAQ_Viewer_TCP` and `DAQ_Move_TCP`
   - These are BUILT-IN instrument plugins
   - Just configure IP/port in dashboard

2. **Simpler Server** ✅ Keep server, but simplify
   - Server inherits from `TCPServer` (we got this right!)
   - Override specific methods for PyRPL
   - PyMoDAQ handles the protocol

3. **Standard Protocol** ✅ Already using DataToExport
   - PyMoDAQ's serialization works automatically
   - DataToExport/DataWithAxes format correct
   - ThreadCommand for status updates

### **What We Need to Change:**

#### ❌ **REMOVE:**
- `daq_1Dviewer_PyRPL_Scope_TCP.py` - Don't need custom plugin!
- Custom `TCPClientTemplate` wrapper code
- Plugin-side TCP implementation

#### ✅ **KEEP & REFINE:**
- `pyrpl_tcp_server.py` - But simplify it
- Architecture concept (server manages PyRPL)
- Command routing logic

#### 🔄 **MODIFY:**
Server should work with PyMoDAQ's **built-in** TCP instruments:

```python
# Server will receive commands from DAQ_Viewer_TCP / DAQ_Move_TCP
# These are BUILT-IN PyMoDAQ plugins, not custom!

class PyRPLTCPServer(TCPServer):
    """
    Server for PyMoDAQ's built-in TCP instrument plugins.
    
    No custom plugins needed - use DAQ_Viewer_TCP and DAQ_Move_TCP
    from the PyMoDAQ dashboard!
    """
    
    def __init__(self, client_type='GRABBER'):
        super().__init__(client_type=client_type)
        # Initialize PyRPL
        self.pyrpl = Pyrpl(...)
    
    def process_cmds(self, command):
        """
        Process commands from built-in TCP instruments.
        
        Called by PyMoDAQ's TCPServer infrastructure when
        DAQ_Viewer_TCP or DAQ_Move_TCP sends a command.
        """
        if command == 'grab_data':
            # Scope acquisition
            data = self.pyrpl.rp.scope.curve()
            # Return DataToExport
            return self.create_data_to_export(data)
        
        elif command == 'move_abs':
            # ASG/PID control
            value = command.params['value']
            self.pyrpl.rp.asg0.offset = value
            return {'status': 'ok'}
    
    def send_data(self, data: DataToExport):
        """Send data to PyMoDAQ client."""
        # TCPServer handles serialization
        self.socket.send_data(data)
```

---

## 📐 **Revised Architecture**

### **New Simplified Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│              PyMoDAQ Dashboard (MASTER)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Built-in Instrument Plugins (no custom code!)   │  │
│  │  - DAQ_Viewer_TCP (Scope, IQ)                    │  │
│  │  - DAQ_Move_TCP (ASG, PID)                       │  │
│  │                                                    │  │
│  │  Just configure:                                  │  │
│  │  - IP: localhost                                  │  │
│  │  - Port: 6341                                     │  │
│  │  - Detector/Actuator type                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          │
                   TCP (localhost:6341)
                   PyMoDAQ Protocol
                          │
┌─────────────────────────┼───────────────────────────────┐
│        PyRPL TCP Server Process (SLAVE)                 │
│  ┌──────────────────────▼───────────────────────────┐  │
│  │  PyRPLTCPServer (inherits TCPServer)             │  │
│  │  - Receives commands from built-in plugins       │  │
│  │  - Routes to PyRPL modules                       │  │
│  │  - Returns DataToExport                          │  │
│  └──────────────────────┬───────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐  │
│  │  PyRPL Instance                                   │  │
│  │  - ONE Pyrpl() for entire server                 │  │
│  │  - Manages scope, iq, asg, pid modules           │  │
│  └──────────────────────┬───────────────────────────┘  │
└─────────────────────────┼───────────────────────────────┘
                          │
                    SSH Connection
                          │
                          ▼
                   Red Pitaya FPGA
```

### **How User Will Use It:**

1. **Start PyRPL Server Once:**
   ```bash
   python pyrpl_tcp_server.py --hostname 100.107.106.75
   # Server starts, loads PyRPL, listens on port 6341
   ```

2. **In PyMoDAQ Dashboard:**
   - Add detector: Select **DAQ_Viewer_TCP** (built-in!)
   - Configure:
     - IP: `localhost`
     - Port: `6341`
     - Detector type: `0D` or `1D`
   - Init → It connects to PyRPL server → Ready!

3. **No Custom Plugin Installation Needed!** 🎉

---

## 🔄 **Migration Plan**

### **Phase 1: Simplify Server** ⏳

1. Update `pyrpl_tcp_server.py` to work with built-in TCP instruments
2. Override correct methods from `TCPServer`:
   - `process_cmds()` - Handle grab, move, etc.
   - `command_to_from_client()` - Route commands
   - `send_data()` - Send DataToExport

3. Test server initialization

### **Phase 2: Remove Custom Plugins** ⏳

1. Delete `daq_1Dviewer_PyRPL_Scope_TCP.py`
2. Remove custom TCP client wrapper code
3. Update documentation to use built-in plugins

### **Phase 3: Testing** ⏳

1. Start PyRPL TCP server
2. Open PyMoDAQ dashboard
3. Add `DAQ_Viewer_TCP` instrument
4. Configure connection
5. Test data acquisition

### **Phase 4: Documentation** ⏳

1. Update README with simplified workflow
2. Document server configuration
3. Show dashboard setup screenshots
4. Test with all 4 module types

---

## 💡 **Key Insights**

### **What We Learned:**

1. **PyMoDAQ Already Has TCP Instruments** ⭐
   - `DAQ_Viewer_TCP` for detectors
   - `DAQ_Move_TCP` for actuators
   - These are BUILT-IN, production-ready

2. **Our Server Approach Was Correct** ✅
   - Inheriting from `TCPServer` is right
   - Managing one PyRPL instance is right
   - Just need to work with built-in clients

3. **We Were Reinventing the Client Side** ❌
   - Don't need custom plugins!
   - PyMoDAQ provides the client
   - Just configure IP/port

4. **LECO/ZMQ is for Other Languages** ℹ️
   - When device driver is in C++/LabView/etc.
   - PyRPL is Python, so standard TCP works
   - LECO adds complexity we don't need

### **Advantages of This Approach:**

✅ **Simpler**: No custom plugin installation
✅ **Standard**: Uses PyMoDAQ's built-in instruments
✅ **Maintainable**: Less code to maintain
✅ **Flexible**: Easy to add more modules
✅ **Documented**: PyMoDAQ's docs cover built-in TCP
✅ **Supported**: Uses official PyMoDAQ patterns

---

## 📚 **References**

- [PyMoDAQ TCP/IP API](https://pymodaq.cnrs.fr/en/latest/api/utility_api/tcp_ip.html)
- [Pluginless LECO Communication](https://pymodaq.cnrs.fr/en/latest/tutorials/pluginless_leco_communication.html)
- [TCP Communication User Guide](https://pymodaq.cnrs.fr/en/latest/user_folder/tcpip.html)

---

## 🎯 **Action Items**

1. ✅ Research PyMoDAQ's actual TCP patterns
2. ✅ Understand built-in TCP instruments
3. ⏳ Refactor server to work with `DAQ_Viewer_TCP` / `DAQ_Move_TCP`
4. ⏳ Remove custom plugin code
5. ⏳ Test with PyMoDAQ dashboard
6. ⏳ Update all documentation

---

**Status**: Architecture simplified - using PyMoDAQ's built-in patterns  
**Next**: Refactor server to work with built-in TCP instruments  
**Impact**: Removes ~500 lines of unnecessary custom plugin code!
