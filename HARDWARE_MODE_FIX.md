# Hardware Mode Issues & Solutions

## Current Issue

**Error**: `ZeroDivisionError: float division by zero` in PyRPL's Network Analyzer module

**Root Cause**: Corrupted PyRPL configuration file (`/Users/briansquires/pyrpl_user_dir/config/pymodaq.yml`)

**Status**: Config file backed up and cleared (Sept 30, 2025)

---

## ✅ Solution 1: Use Mock Mode (RECOMMENDED)

Mock mode works perfectly - use it for all testing and development:

### In PyMoDAQ Settings:
```
Development
├── Mock Mode: ☑ TRUE      ← CHECK THIS!
└── Debug Logging: ☐ False
```

**Benefits**:
- Instant initialization (<1s)
- No hardware issues
- Perfect for testing plugin functionality
- Confirmed working with 16,384 point waveforms

---

## Solution 2: Fresh Config for Hardware

The corrupted config has been backed up to:
- `pymodaq_corrupted_YYYYMMDD_HHMMSS.yml`

**Next time you try hardware mode**, PyRPL will create a fresh config automatically.

### Steps:
1. **Uncheck Mock Mode** in plugin settings
2. Click **Init. Detector**
3. Wait **10-30 seconds** for PyRPL initialization
4. PyRPL will create new `pymodaq.yml` automatically

---

## Solution 3: Pre-Initialize PyRPL (Most Reliable)

This avoids the PyRPL initialization issues entirely:

### Terminal 1: Start PyRPL First
```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
source venv/bin/activate  # or .venv

python
>>> import pyrpl
>>> p = pyrpl.Pyrpl(hostname='100.107.106.75', config='pymodaq_hw', gui=False)
# Wait for full initialization (10-30s)
# Leave this running!
```

### Terminal 2: Start PyMoDAQ
```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl  
uv run dashboard
```

### In PyMoDAQ:
- Set Config Name to: `pymodaq_hw` (same as Terminal 1!)
- Uncheck Mock Mode
- Initialize detector

The plugin will reuse the existing PyRPL session.

---

##Known PyRPL Issues

### Network Analyzer Division by Zero
This is a **PyRPL bug**, not our plugin issue. It happens when:
- Config file has invalid values
- Network Analyzer module can't initialize properly
- `_MINBW()` returns 0, causing division by zero

**Workarounds**:
1. Use Mock Mode ✅
2. Delete corrupted config (done)
3. Pre-initialize PyRPL
4. Disable Network Analyzer module (not recommended)

### SSH Socket Closing
Separate issue - PyRPL's SSH connection times out during FPGA upload.

**Solutions**: See `SSH_CONNECTION_FIX.md`

---

## Recommended Workflow

### For Development & Testing
**Always use Mock Mode**:
- Fast iteration
- No hardware dependencies
- Confirmed working
- Full plugin functionality

### For Real Experiments
1. **First**: Test everything in Mock Mode
2. **Then**: Switch to hardware mode
3. **Use**: Pre-initialize method (Solution 3)
4. **Or**: Be patient with fresh config creation

---

## Current Status

| Mode | Status | Notes |
|------|--------|-------|
| **Mock Mode** | ✅ Working | Use this! |
| **Hardware Mode** | ⚠️ Config issue | Cleared, needs fresh init |
| **Pre-Initialize** | ✅ Should work | Most reliable for hardware |

---

## If Hardware Mode Still Fails

### Option A: Different Config Name
Try a completely fresh config:
```python
# Plugin settings
PyRPL Config Name: fresh_config_20250930
```

### Option B: Minimal Config
Create minimal config manually at `/Users/briansquires/pyrpl_user_dir/config/minimal_hardware.yml`:

```yaml
pyrpl:
  name: minimal_hardware
  modules: []  # Don't load Network Analyzer
  
redpitaya:
  hostname: 100.107.106.75
  port: 2222
  user: root
  password: root
  gui: false
```

Then use config name: `minimal_hardware`

### Option C: Check PyRPL Version
```bash
pip show pyrpl
```

If it's an old version, consider updating (though this might introduce other issues).

---

## Debug Commands

### Check Config Files
```bash
ls -la /Users/briansquires/pyrpl_user_dir/config/
```

### View Config
```bash
cat /Users/briansquires/pyrpl_user_dir/config/pymodaq.yml
```

### Delete All Configs (Nuclear Option)
```bash
# BACKUP FIRST!
cd /Users/briansquires/pyrpl_user_dir/config
mkdir ../config_backup_$(date +%Y%m%d)
cp *.yml ../config_backup_$(date +%Y%m%d)/
rm *.yml *.yml.bak
```

---

## The Bottom Line

**For now, use Mock Mode** - it works perfectly and lets you test all plugin functionality.

When you're ready for real hardware:
1. Try fresh config (automatic on next init)
2. If that fails, use pre-initialize method
3. If that fails, report to PyRPL developers (it's their bug, not ours)

The IPC architecture is sound - the issue is PyRPL's configuration corruption, which is a known PyRPL problem.

---

**Last Updated**: September 30, 2025
**Corrupted Config**: Backed up
**Mock Mode**: ✅ Confirmed Working
**Hardware Mode**: Ready to retry with fresh config
