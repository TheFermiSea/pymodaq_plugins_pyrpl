# PyMoDAQ-PyRPL TCP/IP Architecture Design

## Overview

This document describes the TCP/IP architecture for integrating PyRPL with PyMoDAQ, where **PyMoDAQ acts as the master** controlling **PyRPL as the slave**.

## Architecture Principles

### PyMoDAQ as Master
- PyMoDAQ Dashboard orchestrates all hardware control
- PyMoDAQ plugins are lightweight TCP clients
- PyMoDAQ controls timing, sequencing, and data acquisition
- Uses PyMoDAQ's native TCP/IP infrastructure (`TCPClientTemplate`)

### PyRPL as Slave
- PyRPL runs in a separate server process
- Manages ONE PyRPL instance connected to Red Pitaya
- Responds to commands from PyMoDAQ plugins
- Handles low-level FPGA module management
- PyRPL's module system manages resource allocation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PyMoDAQ Dashboard (MASTER)                    │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │
│  │ Scope Plugin   │ │  IQ Plugin     │ │ ASG/PID Plugins│          │
│  │ (GRABBER)      │ │ (GRABBER)      │ │ (ACTUATOR)     │          │
│  │                │ │                │ │                │          │
│  │ TCPClient      │ │ TCPClient      │ │ TCPClient      │          │
│  │ Template       │ │ Template       │ │ Template       │          │
│  └────────┬───────┘ └────────┬───────┘ └────────┬───────┘          │
└───────────┼──────────────────┼──────────────────┼──────────────────┘
            │                  │                  │
            └──────────────────┴──────────────────┘
                               │
                    TCP/IP (localhost:6341)
                    PyMoDAQ Standard Protocol
                               │
┌──────────────────────────────┼──────────────────────────────────────┐
│              PyRPL TCP Server Process (SLAVE)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PyMoDAQPyRPLServer (inherits PyMoDAQ's TCPServer)           │  │
│  │  - Accepts multiple client connections                        │  │
│  │  - Deserializes PyMoDAQ commands                             │  │
│  │  - Routes to appropriate PyRPL modules                        │  │
│  │  - Serializes responses using PyMoDAQ protocol               │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │  PyRPL Instance Manager                                       │  │
│  │  - ONE Pyrpl() instance for entire server                    │  │
│  │  - Module ownership management (PyRPL's .pop() context)      │  │
│  │  - Module state preservation                                  │  │
│  │  - FPGA register synchronization                             │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │  PyRPL Hardware Modules                                       │  │
│  │  - pyrpl.rp.scope (HardwareModule)                           │  │
│  │  - pyrpl.rp.iq0/iq1/iq2 (HardwareModule)                     │  │
│  │  - pyrpl.rp.asg0/asg1 (HardwareModule)                       │  │
│  │  - pyrpl.rp.pid0/pid1/pid2 (HardwareModule)                  │  │
│  │                                                               │  │
│  │  Each module:                                                 │  │
│  │  - Has attributes synchronized with FPGA registers            │  │
│  │  - Uses PyRPL's ownership system for resource management     │  │
│  │  - Maintains state in PyRPL config file                      │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│                    PyRPL.Pyrpl() instance                            │
│                              │                                       │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                    SSH Connection (managed by PyRPL)
                    monitor_server protocol
                               │
                               ▼
                    Red Pitaya FPGA (100.107.106.75)
                    - 125 MHz DSP modules
                    - Analog I/O (14-bit)
                    - FPGA bitstream loaded once at server startup
```

## Key Design Decisions

### 1. PyMoDAQ's TCP/IP Infrastructure
**Use existing classes, not custom implementations:**
- `TCPClientTemplate` - Base class for plugin TCP clients
- `TCPServer` - Base class for PyRPL server
- PyMoDAQ's serialization protocol (commands, DataToExport, etc.)

### 2. PyRPL Module Ownership
**Respect PyRPL's resource management:**
```python
# PyRPL's ownership pattern
with pyrpl.rp.scope.pop('pymodaq_scope_client') as scope:
    scope.input1 = 'in1'
    scope.trigger_source = 'immediately'
    data = scope.curve()
# Scope automatically freed when context exits
```

### 3. One PyRPL Instance
**Server manages singleton PyRPL instance:**
- Created at server startup
- FPGA bitstream loaded ONCE
- SSH connection maintained by PyRPL
- All clients share same PyRPL instance via server

### 4. Client Types
**Follow PyMoDAQ conventions:**
- **GRABBER** (Scope, IQ) - Acquire data, send `DataToExport`
- **ACTUATOR** (ASG, PID) - Set values, respond to `move_abs/rel`

## Implementation Components

### 1. PyRPL TCP Server (`src/pymodaq_plugins_pyrpl/utils/pyrpl_tcp_server.py`)

```python
from pymodaq.utils.tcp_ip.tcp_server_client import TCPServer
from pyrpl import Pyrpl

class PyMoDAQPyRPLServer(TCPServer):
    """
    TCP Server that exposes PyRPL modules to PyMoDAQ clients.
    
    Inherits from PyMoDAQ's TCPServer to leverage:
    - Message serialization/deserialization
    - Client connection management
    - Command routing infrastructure
    
    Manages ONE PyRPL instance shared by all clients.
    """
    
    def __init__(self, hostname, config_name, port=6341):
        super().__init__(port=port)
        
        # Initialize PyRPL (ONCE for entire server)
        self.pyrpl = Pyrpl(config=config_name, hostname=hostname)
        
        # Track module ownership per client
        self.client_modules = {}  # {client_id: {module_name: module_instance}}
    
    def process_client_command(self, client_socket, command, data):
        """
        Process commands from PyMoDAQ clients.
        
        Commands follow PyMoDAQ protocol:
        - 'set_info': Parameter configuration (deserialize XML)
        - 'grab': Acquire data (Scope/IQ)
        - 'move_abs/rel': Set actuator value (ASG/PID)
        - 'stop_motion': Stop actuator
        """
        # Implementation routes to appropriate PyRPL module
        pass
```

### 2. Plugin TCP Clients

Each plugin inherits from `TCPClientTemplate`:

```python
from pymodaq.utils.tcp_ip.tcp_server_client import TCPClientTemplate

class DAQ_1Dviewer_PyRPL_Scope_TCP(DAQ_Viewer_base, TCPClientTemplate):
    """
    PyMoDAQ Scope plugin using TCP/IP to communicate with PyRPL server.
    
    Client Type: GRABBER
    - Sends acquisition commands to server
    - Receives DataToExport containing scope traces
    """
    
    def __init__(self):
        TCPClientTemplate.__init__(
            self,
            ipaddress='localhost',
            port=6341,
            client_type='GRABBER'
        )
        DAQ_Viewer_base.__init__(self, ...)
    
    def grab_data(self, **kwargs):
        """Request data acquisition from PyRPL server."""
        # Send command via TCP
        # Receive DataToExport from server
        pass
```

## Protocol Specification

### PyMoDAQ → PyRPL Server Commands

#### GRABBER Commands (Scope, IQ)
```python
# Configuration
Command: 'set_info'
Data: Parameter XML string

# Acquisition
Command: 'grab'
Data: {'module': 'scope', 'config': {...}}

# Server Response
Command: 'Done'
Data: DataToExport with acquired traces
```

#### ACTUATOR Commands (ASG, PID)
```python
# Configuration
Command: 'set_info'
Data: Parameter XML string

# Move to absolute position
Command: 'move_abs'
Data: {'module': 'asg0', 'value': 0.5}

# Server Response
Command: 'move_done'
Data: Current position

# Stop motion
Command: 'stop_motion'
Data: {'module': 'asg0'}
```

### PyRPL Module Mapping

| PyMoDAQ Plugin | PyRPL Module | Client Type | Operations |
|----------------|--------------|-------------|------------|
| Scope | `pyrpl.rp.scope` | GRABBER | curve(), setup() |
| IQ | `pyrpl.rp.iq0/1/2` | GRABBER | iq(), setup() |
| ASG | `pyrpl.rp.asg0/1` | ACTUATOR | setup(), voltage |
| PID | `pyrpl.rp.pid0/1/2` | ACTUATOR | setup(), setpoint |

## Benefits of This Architecture

### ✅ PyMoDAQ as Master
1. **Dashboard Control**: PyMoDAQ orchestrates all acquisition/actuation
2. **Standard Protocol**: Uses PyMoDAQ's proven TCP/IP infrastructure
3. **Native Integration**: Plugins use standard PyMoDAQ patterns
4. **Parameter Sync**: PyMoDAQ parameter tree controls PyRPL modules

### ✅ PyRPL as Slave
1. **Encapsulation**: PyRPL complexity hidden in server process
2. **Resource Management**: PyRPL's ownership system prevents conflicts
3. **State Preservation**: PyRPL config file maintains module states
4. **FPGA Abstraction**: PyRPL handles low-level FPGA communication

### ✅ Stability Improvements
1. **Isolated SSH**: SSH connection managed by stable server process
2. **One FPGA Load**: Bitstream loaded once at server startup
3. **No IPC Complexity**: Standard TCP/IP replaces multiprocessing
4. **Clean Reconnection**: Clients can disconnect/reconnect freely

### ✅ Scalability
1. **Multiple Clients**: Server handles concurrent plugin connections
2. **Remote Capable**: Can run server on different machine if needed
3. **Standard Protocol**: Other software can connect using PyMoDAQ protocol
4. **Modular**: Easy to add new PyRPL modules as plugins

## Migration Path

### Phase 1: Create Server ✅
- Implement PyMoDAQPyRPLServer inheriting TCPServer
- Initialize PyRPL instance at server startup
- Implement command routing to PyRPL modules

### Phase 2: Update Plugins
- Replace IPC code with TCPClientTemplate
- Implement PyMoDAQ command handlers
- Test each plugin individually

### Phase 3: Integration Testing
- Test with dashboard preset
- Verify concurrent operation
- Validate FPGA stability

### Phase 4: Documentation & Cleanup
- Document server startup procedure
- Update README with new architecture
- Archive old IPC implementation

## Server Startup

```bash
# Start PyRPL TCP server
cd src/pymodaq_plugins_pyrpl/utils
python pyrpl_tcp_server.py --hostname 100.107.106.75 --config pymodaq --port 6341

# Or in mock mode for development
python pyrpl_tcp_server.py --mock
```

## Configuration

Server configuration in `pymodaq_plugins_pyrpl_server.yml`:
```yaml
server:
  port: 6341
  host: 'localhost'
  
pyrpl:
  hostname: '100.107.106.75'
  config_name: 'pymodaq'
  
modules:
  scope:
    owner_timeout: 30.0
  iq:
    instances: ['iq0', 'iq1', 'iq2']
  asg:
    instances: ['asg0', 'asg1']
  pid:
    instances: ['pid0', 'pid1', 'pid2']
```

## Error Handling

### Server Errors
- SSH connection loss → Attempt reconnection, notify all clients
- PyRPL module error → Return error message to requesting client
- Module ownership conflict → Queue request or reject with clear message

### Client Errors
- Connection timeout → Retry with exponential backoff
- Command error → Display in PyMoDAQ log
- Data format error → Validate before sending

## Security Considerations

1. **Local Only (Default)**: Server binds to localhost only
2. **Red Pitaya SSH**: Managed by PyRPL with proper authentication
3. **No Credentials in Code**: Configuration file stores sensitive data
4. **Client Validation**: Server validates client type on connection

## Future Enhancements

1. **Authentication**: Add client authentication for remote servers
2. **Monitoring**: Health check endpoint for server status
3. **Load Balancing**: Multiple Red Pitaya support
4. **Caching**: Cache frequently accessed PyRPL module states
5. **Async**: Convert to async/await for better concurrency

---

**Author**: Droid (Factory AI)  
**Date**: 2025-10-01  
**Status**: Design Complete - Ready for Implementation
