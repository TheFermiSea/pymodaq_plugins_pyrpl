# Quick Fix: SSH "Socket is closed" Error

## Problem

PyRPL initialization fails with `OSError: Socket is closed` during FPGA bitstream upload. This is a known issue with PyRPL's SSH connection timing out during long operations.

## Immediate Solution: Use Existing PyRPL Session

Instead of letting the plugin initialize PyRPL (which times out), **start PyRPL first** and keep it running:

### Step 1: Start PyRPL in Terminal

```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
source venv/bin/activate  # Or: source .venv/bin/activate

# Start Python
python

# In Python:
import pyrpl
p = pyrpl.Pyrpl(hostname='100.107.106.75', config='pymodaq', gui=False)
# Wait for this to complete (10-30 seconds)
# Once initialized, leave this Python session running
```

### Step 2: Launch PyMoDAQ

In a **separate terminal**:

```bash
# With the PyRPL session still running in terminal 1
python -m pymodaq.dashboard
```

### Step 3: Configure Plugin

1. Add PyRPL_Scope_IPC plugin
2. Configure settings:
   - Hostname: `100.107.106.75`
   - Config name: `pymodaq` (IMPORTANT: same as Step 1)
   - Mock mode: `False`
3. Initialize detector

The plugin will reuse the existing PyRPL connection instead of creating a new one.

## Alternative: SSH Keepalive Configuration

Edit `~/.ssh/config`:

```bash
Host 100.107.106.75
    ServerAliveInterval 5
    ServerAliveCountMax 12
    TCPKeepAlive yes
```

This keeps SSH alive during long operations.

## Alternative: Increase Connection Timeout

Edit `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`:

Find line ~80 and change:

```python
# FROM:
max_retries = 3
retry_delay = 2.0

# TO:
max_retries = 5
retry_delay = 5.0
```

## Test First with Mock Mode

Before fighting with hardware:

1. In plugin settings: `Development` → `Mock Mode` = `True`
2. Initialize detector
3. Should work immediately
4. Acquire data (synthetic signals)

Once working in mock mode, switch to hardware.

## Root Cause

The issue is PyRPL's SSH connection to the Red Pitaya closing during FPGA bitstream upload (~10-15 seconds). This can be caused by:

- Network latency/instability
- SSH keepalive timeout
- Firewall NAT tracking timeout  
- Red Pitaya under load

The retry logic in the worker helps, but the underlying network stability issue needs to be addressed.

## Need More Help?

See full troubleshooting guide: `docs/TROUBLESHOOTING_SSH_CONNECTION.md`

Or run diagnostics:
```bash
venv/bin/python tests/test_redpitaya_connection.py 100.107.106.75
```
