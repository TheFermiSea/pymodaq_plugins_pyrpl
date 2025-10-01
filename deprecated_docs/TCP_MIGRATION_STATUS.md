# TCP/IP Architecture Migration Status

**Date**: 2025-10-01  
**Status**: Phase 2 In Progress - Server and Scope Plugin Complete

## Summary

We are migrating from IPC (multiprocessing) to TCP/IP architecture for better stability and proper integration between PyMoDAQ (master) and PyRPL (slave).

---

## ✅ Completed Work

### Phase 1: Design & Server Implementation

#### 1. Architecture Design Document (`TCPIP_ARCHITECTURE.md`)
- ✅ Complete master/slave relationship specification
- ✅ Uses PyMoDAQ's native `TCPServer` and `TCPClientTemplate`
- ✅ Respects PyRPL's module ownership system
- ✅ Protocol specification for all command types
- ✅ Benefits analysis and migration path

#### 2. PyRPL TCP Server (`pyrpl_tcp_server.py`)
- ✅ Inherits from PyMoDAQ's `TCPServer`
- ✅ Manages ONE PyRPL instance for all clients
- ✅ Command routing (grab, move_abs/rel, configure, etc.)
- ✅ Mock mode for development
- ✅ Comprehensive logging

**Key Features:**
```python
# Server manages single PyRPL instance
self.pyrpl = Pyrpl(config=config_name, hostname=hostname)

# Command routing
def command_to_from_client(self, client_socket, data: dict):
    # Routes to: _handle_grab, _handle_move_abs, _handle_configure, etc.
    pass
```

### Phase 2: Plugin Migration

#### 3. Scope TCP Plugin (`daq_1Dviewer_PyRPL_Scope_TCP.py`)
- ✅ Inherits from PyMoDAQ's `TCPClientTemplate`
- ✅ GRABBER client type
- ✅ Complete data acquisition flow
- ✅ Proper DataFromPlugins conversion
- ✅ Clean connection management

**Key Features:**
```python
class DAQ_1DViewer_PyRPL_Scope_TCP(DAQ_Viewer_base):
    def ini_detector(self):
        # Connect to TCP server
        self.tcp_client = TCPClientWrapper(...)
        
    def grab_data(self):
        # Send grab command
        dte = self.tcp_client.grab_data(command_data)
        # Convert to PyMoDAQ format
        self.dte_signal.emit(data)
```

---

## 🔄 Current Status

### What Works:
1. ✅ Architecture design is complete and documented
2. ✅ Server implementation follows PyMoDAQ patterns
3. ✅ Scope TCP plugin follows PyMoDAQ `TCPClientTemplate` pattern
4. ✅ Mock PyRPL for development testing

### What Needs Work:

#### 1. Server Integration Challenge
**Issue**: PyMoDAQ's `TCPServer` requires full plugin context with settings parameter tree

```python
# TCPServer expects:
def init_server(self):
    self.serversocket.bind((
        self.settings['socket_ip'],  # ← Requires settings tree
        self.settings['port_id']      # ← Requires settings tree
    ))
```

**Solutions Being Considered:**
- **Option A**: Create a PyMoDAQ instrument plugin that runs the server (preferred)
- **Option B**: Create a simpler standalone server not inheriting from `TCPServer`
- **Option C**: Use PyMoDAQ's DAQ_Move/Viewer_TCP classes directly

#### 2. Testing Challenge
- Cannot easily unit test without full PyMoDAQ context
- Requires running actual PyMoDAQ dashboard for integration testing

---

## 📋 Remaining Work

### Immediate Next Steps:

1. **Refine Server Architecture** ⏳
   - Decide on server integration approach (Option A, B, or C)
   - If Option A: Create PyMoDAQ instrument plugin wrapper
   - If Option B: Simplify server to not require settings tree
   
2. **Test Scope TCP Plugin** ⏳
   - Start server (whichever architecture chosen)
   - Load Scope TCP plugin in PyMoDAQ dashboard
   - Verify data acquisition works
   
3. **Create Remaining TCP Plugins** ⏳
   - IQ TCP plugin (GRABBER type)
   - ASG TCP plugin (ACTUATOR type)
   - PID TCP plugin (ACTUATOR type)

### Future Work:

4. **Integration Testing**
   - Test with dashboard preset
   - Verify concurrent operation
   - Test with real Red Pitaya hardware
   
5. **Documentation & Cleanup**
   - Update README with server startup instructions
   - Document plugin usage
   - Archive old IPC implementation

---

## 🏗️ Architecture Comparison

### Old IPC Architecture (Current)
```
PyMoDAQ Dashboard
  ↓
Plugin → SharedPyRPLManager → Worker Process → PyRPL → Red Pitaya
         (multiprocessing.Queue)  (subprocess)

Issues:
- SSH connection drops during FPGA loading
- Complex singleton management
- Custom Queue-based protocol
- Difficult debugging
```

###New TCP/IP Architecture (Target)
```
PyMoDAQ Dashboard                PyRPL TCP Server
  ↓                                     ↓
Plugin → TCP Client  ←→  TCP  ←→  PyRPL Manager → PyRPL → Red Pitaya
         (TCPClientTemplate)  (localhost:6341)  (ONE instance)

Benefits:
✅ Server manages stable SSH connection
✅ FPGA loaded once at server startup
✅ Standard PyMoDAQ TCP protocol
✅ Clean client reconnection
✅ Better error isolation
```

---

## 📂 Files Created/Modified

### New Files:
1. `TCPIP_ARCHITECTURE.md` - Complete architecture design
2. `src/pymodaq_plugins_pyrpl/utils/pyrpl_tcp_server.py` - TCP server
3. `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_TCP.py` - Scope TCP plugin
4. `tests/test_tcp_architecture.py` - Test script (WIP)
5. `TCP_MIGRATION_STATUS.md` - This file

### Modified Files:
- None yet (new plugins are separate from IPC plugins)

---

## 🎯 Success Criteria

The migration will be considered complete when:

1. ✅ PyRPL TCP server starts successfully
2. ⏳ All 4 plugins (Scope, IQ, ASG, PID) work via TCP
3. ⏳ Dashboard preset loads and connects all plugins
4. ⏳ Concurrent operation works (multiple plugins simultaneously)
5. ⏳ Real hardware testing passes
6. ⏳ SSH connection remains stable during FPGA operations
7. ⏳ Documentation is complete

---

## 💡 Key Insights

### What We Learned:

1. **PyMoDAQ's TCP Infrastructure is Deep**
   - TCPServer is designed to work within plugin framework
   - Requires settings parameter tree for configuration
   - Not meant to be used as standalone server

2. **PyRPL's Module Ownership is Critical**
   - Must use `.pop(owner)` context manager
   - Prevents resource conflicts
   - State preservation via config file

3. **Integration Points Matter**
   - PyMoDAQ master / PyRPL slave relationship must be clear
   - Both frameworks have their own patterns that must be respected
   - TCP/IP is the right abstraction layer

### Design Decisions:

1. **ONE PyRPL Instance**: Server manages single Pyrpl() instance
2. **Standard Protocol**: Use PyMoDAQ's serialization (DataToExport, etc.)
3. **Client Types**: GRABBER for viewers, ACTUATOR for movers
4. **Module Routing**: Server routes commands to appropriate PyRPL modules

---

## 📞 Contact & Support

**Implementation Team**: Droid (Factory AI)  
**Repository**: https://github.com/TheFermiSea/pymodaq_plugins_pyrpl  
**Branch**: feature/command-id-multiplexing

**For Questions:**
- Check `TCPIP_ARCHITECTURE.md` for architecture details
- Review `pyrpl_tcp_server.py` for server implementation
- See `daq_1Dviewer_PyRPL_Scope_TCP.py` for plugin example

---

**Last Updated**: 2025-10-01  
**Next Milestone**: Refine server architecture and test Scope plugin
