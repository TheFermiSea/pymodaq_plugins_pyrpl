# Troubleshooting PyRPL SSH Connection Issues

## The "Socket is closed" Error

If you see this error when initializing the PyRPL plugins:

```
OSError: Socket is closed
```

This indicates that the SSH connection to the Red Pitaya is closing unexpectedly during PyRPL initialization, typically during FPGA bitstream upload.

## Root Causes

1. **Network Instability**: Packet loss or intermittent connectivity
2. **SSH Timeout**: Long FPGA upload time exceeds SSH keepalive
3. **Firewall/NAT**: Connection tracking timeout
4. **Red Pitaya Load**: Device under heavy load or memory pressure
5. **Multiple Connections**: Another process using the Red Pitaya

## Diagnostic Steps

### 1. Run Connection Test Script

```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
venv/bin/python tests/test_redpitaya_connection.py 100.107.106.75
```

This will test:
- Network connectivity
- SSH authentication
- PyRPL initialization with retry
- Mock mode fallback

### 2. Check Network Stability

```bash
# Test for packet loss
ping -c 50 100.107.106.75

# Check round-trip time consistency
ping -i 0.2 -c 100 100.107.106.75 | grep time=
```

**Good**: <1ms, no packet loss
**Problematic**: >10ms or >5% packet loss

### 3. Verify SSH Connection

```bash
# Direct SSH test
ssh root@100.107.106.75

# If that works, try sustained connection
ssh root@100.107.106.75 "sleep 30"
```

**Default Red Pitaya credentials**: username=`root`, password=`root`

### 4. Check Red Pitaya Status

Once SSH'd in:

```bash
# Check CPU load
uptime

# Check memory
free -h

# Check running processes
ps aux | grep pyrpl
ps aux | grep monitor_server

# Kill any stuck PyRPL processes
killall monitor_server
killall python
```

## Solutions

### Solution 1: Use Mock Mode (Immediate)

Enable mock mode in plugin settings to test without hardware:

1. In PyMoDAQ plugin settings
2. Navigate to `Development` → `Mock Mode`
3. Set to `True`
4. Initialize plugin

This allows you to test the plugin architecture without hardware connectivity issues.

### Solution 2: Improve SSH Keepalive (Recommended)

Create or edit `~/.ssh/config`:

```bash
Host redpitaya
    HostName 100.107.106.75
    User root
    ServerAliveInterval 10
    ServerAliveCountMax 6
    TCPKeepAlive yes
    Compression yes
```

Then use `redpitaya` as the hostname in plugin settings instead of the IP.

### Solution 3: Direct Ethernet Connection

If using WiFi or complex network:

1. Connect Red Pitaya directly to your computer via Ethernet
2. Configure static IP on your computer's Ethernet interface:
   - IP: 192.168.1.100
   - Subnet: 255.255.255.0
3. Configure Red Pitaya:
   ```bash
   ssh root@192.168.1.1
   # Edit /etc/network/interfaces
   ```
4. Update plugin hostname to `192.168.1.1`

### Solution 4: Increase Timeouts in PyRPL

Edit PyRPL's SSH timeout (advanced):

```python
# In your Python environment
import pyrpl.sshshell
pyrpl.sshshell.TIMEOUT = 60  # Increase from default 30s
```

Or create a wrapper script that sets this before importing plugins.

### Solution 5: Use Existing PyRPL Connection

If you can successfully connect via PyRPL GUI but not via plugin:

1. Start PyRPL GUI first:
   ```python
   import pyrpl
   p = pyrpl.Pyrpl('100.107.106.75', gui=True)
   ```

2. Leave GUI running
3. Configure plugin to use same config name

This reuses the established connection.

### Solution 6: Reboot Red Pitaya

Sometimes the device needs a fresh start:

1. Via SSH:
   ```bash
   ssh root@100.107.106.75
   reboot
   ```

2. Or power cycle the device

3. Wait 60 seconds for full boot

4. Try connecting again

### Solution 7: Update Red Pitaya Firmware

Old firmware may have SSH stability issues:

1. Download latest Red Pitaya OS from: https://redpitaya.com/downloads/
2. Flash to SD card
3. Boot Red Pitaya
4. Test connection

### Solution 8: Use Connection Retry in Plugin

The plugin already has retry logic (3 attempts), but you can increase this:

Edit `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`:

```python
# Find this line (around line 80):
max_retries = 3

# Increase to:
max_retries = 5

# And increase retry delay:
retry_delay = 5.0  # from 2.0
```

## Understanding the Initialization Process

PyRPL initialization involves several steps:

1. **SSH Connection** (~1s)
   - Authenticate with Red Pitaya
   - Establish shell session

2. **FPGA Bitstream Upload** (~5-15s)
   - Upload PyRPL FPGA configuration
   - This is where timeouts often occur

3. **Module Initialization** (~2-5s)
   - Initialize scope, PID, ASG, IQ modules
   - Test communication

**Total time**: 10-30 seconds on first connection

**Subsequent connections**: Faster if bitstream already loaded

## Quick Fixes Checklist

- [ ] Run `tests/test_redpitaya_connection.py`
- [ ] Check network with `ping 100.107.106.75`
- [ ] Verify SSH works: `ssh root@100.107.106.75`
- [ ] Kill stuck processes on Red Pitaya
- [ ] Reboot Red Pitaya
- [ ] Try direct Ethernet connection
- [ ] Use mock mode as fallback
- [ ] Configure SSH keepalive in `~/.ssh/config`
- [ ] Check Red Pitaya isn't under heavy load

## When to Use Mock Mode

Use mock mode if:
- Testing plugin functionality without hardware
- Network connectivity is unreliable
- Red Pitaya is temporarily unavailable
- Developing new features
- Teaching/demonstration without hardware

Mock mode provides:
- Instant initialization (<1s)
- Synthetic but realistic data
- All plugin features work
- No network requirements

## Getting Help

If issues persist:

1. Run full diagnostics:
   ```bash
   venv/bin/python tests/test_redpitaya_connection.py 100.107.106.75 > connection_test.log 2>&1
   ```

2. Check PyRPL logs:
   ```bash
   tail -f ~/.pyrpl/pyrpl.log
   ```

3. Enable debug logging in plugin:
   - Plugin settings → Development → Debug Logging = True

4. Share logs with:
   - PyRPL GitHub issues: https://github.com/pyrpl-fpga/pyrpl/issues
   - PyMoDAQ forum: https://pymodaq.cnrs.fr/
   - This plugin repository

## Alternative: Native SCPI Plugin

If PyRPL connection continues to be problematic, consider using the native SCPI-based Red Pitaya plugins in the PyMoDAQ ecosystem:

- `pymodaq_plugins_redpitaya` (separate package)
- Direct SCPI communication (more stable)
- Limited features (basic scope/ASG only)
- No advanced PyRPL modules (PID, IQ)

## Summary

The "Socket is closed" error is a network/SSH stability issue, not a plugin bug. The recommended solutions are:

1. **Short-term**: Use mock mode for development
2. **Medium-term**: Improve network stability (direct Ethernet, SSH config)
3. **Long-term**: Update Red Pitaya firmware, optimize network setup

The plugin's retry logic and error handling will help, but underlying network issues must be addressed for reliable hardware operation.
