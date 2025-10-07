# PyRPL-PyMoDAQ TCP Architecture

## Overview

PyRPL integration uses **automatic TCP server architecture** to cleanly separate PyRPL (with its quirks) from PyMoDAQ's main process.

## Architecture Diagram

```
┌─────────────────────────────────────┐
│   PyMoDAQ Dashboard (Main Process)  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  TCP Client Plugin         │   │
│  │  (Auto-starts server)      │───┼───┐
│  └─────────────────────────────┘   │   │
│                                     │   │ TCP
│  ┌─────────────────────────────┐   │   │ Port 6341
│  │  TCP Client Plugin         │───┼───┤
│  │  (Reuses existing server)  │   │   │
│  └─────────────────────────────┘   │   │
└─────────────────────────────────────┘   │
                                          │
┌─────────────────────────────────────────┼──┐
│   PyRPL TCP Server (Auto-Started)       │  │
│                                          │  │
│  ┌────────────────────────────────────┐ │  │
│  │  PyRPL Instance (Single Shared)   │ │  │
│  │  - Handles all PyQt/async issues  │ │  │
│  │  - Manages Red Pitaya connection  │ │  │
│  └────────────────────────────────────┘ │  │
└──────────────────────────────────────────┘  │
                   │                          │
                   │ SSH                      │
                   ▼                          │
    ┌──────────────────────────┐              │
    │   Red Pitaya Hardware    │◄─────────────┘
    └──────────────────────────┘
```

## Key Features

### 1. **Automatic Server Management**
- ✅ Server auto-starts when first plugin initializes
- ✅ Multiple plugins share single server instance  
- ✅ Server auto-stops when last plugin closes
- ✅ No manual server management required!

### 2. **Clean Separation**
- ✅ PyRPL runs in separate process (avoids Qt conflicts)
- ✅ PyMoDAQ never imports PyRPL directly
- ✅ Clean TCP protocol for all communication
- ✅ No multiprocessing complexity

### 3. **Robust Operation**
- ✅ Detects existing server (won't start duplicate)
- ✅ Timeout handling for slow connections
- ✅ Graceful cleanup on exit
- ✅ Reference counting prevents premature shutdown

## Usage

### Quick Start (No Manual Setup!)

1. **Launch PyMoDAQ Dashboard**:
   ```bash
   uv run dashboard
   ```

2. **Add TCP Plugin**:
   - Click "+" to add viewer/actuator
   - Select: **PyRPL Scope (TCP)** or **PyRPL ASG (TCP)**
   - Configure:
     - Server IP: `localhost` (for mock) or server machine IP
     - Server Port: `6341` (default)
     - Connection Timeout: `10.0` seconds

3. **Initialize Plugin**:
   - Click "Initialize" button
   - Plugin automatically:
     1. Checks if server is running
     2. Starts server if needed (takes ~5-10 seconds)
     3. Connects and configures module
   - Done! No manual server management!

### Configuration

**Mock Mode (No Hardware)**:
- Server IP: `localhost`
- Automatically starts in mock mode
- Perfect for development/testing

**Real Hardware**:
- Server IP: `localhost` (if running on same machine)
- Or: Remote machine IP (if server runs elsewhere)
- Configure Red Pitaya IP in plugin settings (TODO: expose this)

## Available Plugins

### Current TCP Plugins

1. **PyRPL Scope (TCP)** - `DAQ_1DViewer_PyRPL_Scope_TCP`
   - 1D oscilloscope viewer
   - Configurable sampling, triggering
   - Auto-server startup enabled ✅

### Coming Soon

- **PyRPL ASG (TCP)** - Signal generator (move actuator)
- **PyRPL PID (TCP)** - PID controller (move actuator)  
- **PyRPL IQ (TCP)** - IQ demodulator (0D viewer)

## Technical Details

### Server Lifecycle

```python
# Plugin 1 initializes
plugin1.ini_detector()
→ TCPServerManager.ensure_server_running()
→ No server found, starting...
→ Server starts (PID: 12345)
→ Plugin connects

# Plugin 2 initializes
plugin2.ini_detector()
→ TCPServerManager.ensure_server_running()
→ Server already running (clients: 1 → 2)
→ Plugin connects (reuses server)

# Plugin 1 closes
plugin1.close()
→ TCPServerManager.release_server()
→ Client count: 2 → 1
→ Server stays running (other clients active)

# Plugin 2 closes
plugin2.close()
→ TCPServerManager.release_server()
→ Client count: 1 → 0
→ Server auto-stops (no clients)
```

### Files

**Core Architecture**:
- `utils/tcp_server_manager.py` - Auto-server management
- `utils/pyrpl_tcp_server.py` - PyRPL TCP server implementation

**TCP Client Plugins**:
- `daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_TCP.py`

## Advantages Over IPC

### Old IPC Architecture ❌
- Complex multiprocessing queues
- Hard to debug communication issues
- Tight coupling between plugin and worker
- Manual process management

### New TCP Architecture ✅
- Standard TCP protocol (well-understood)
- Easy to debug with netstat/tcpdump
- Clean separation (can run on different machines!)
- Automatic server lifecycle management
- Industry-standard approach

## Testing

### Test Auto-Server Startup
```bash
python test_auto_server.py
```

### Test Server Directly
```bash
# Mock mode
python -m pymodaq_plugins_pyrpl.utils.pyrpl_tcp_server --mock

# Real hardware
python -m pymodaq_plugins_pyrpl.utils.pyrpl_tcp_server \
    --hostname 100.107.106.75 \
    --config pymodaq
```

## Troubleshooting

### Server Won't Start

**Check logs**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Common issues**:
1. **Port already in use**: Another server running on 6341
   - Solution: Kill existing server or use different port
2. **PyRPL import fails**: Missing dependencies
   - Solution: Run `./install-pyrpl` script
3. **Red Pitaya unreachable**: Network/SSH issues
   - Solution: Verify Red Pitaya IP, ping test, SSH test

### Plugin Won't Connect

1. **Check server is running**: `netstat -an | grep 6341`
2. **Check firewall**: Allow port 6341
3. **Check timeout**: Increase connection timeout in settings

## Future Enhancements

### Phase 3 (TCP Completion)
- [ ] Add Red Pitaya IP to plugin settings
- [ ] Implement remaining TCP plugins (ASG, PID, IQ)
- [ ] Add server health monitoring
- [ ] Implement reconnection logic

### Phase 4 (Production Ready)
- [ ] Add authentication/encryption
- [ ] Implement server discovery (ZeroConf/mDNS)
- [ ] Add performance metrics
- [ ] Create unified configuration GUI

## Credits

**Architecture**: TCP-based client-server with auto-management  
**Latest PyRPL**: v0.9.6.0 from main branch (Sept 2025)  
**Python**: 3.12 compatible  
**PyMoDAQ**: v5.0+  

## License

MIT License - See LICENSE file for details
