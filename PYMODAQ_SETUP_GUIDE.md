# Step-by-Step: Using PyRPL_Scope_IPC in PyMoDAQ

## The plugin works! (Confirmed by automated tests)

The standalone test shows mock mode works perfectly. If it's not working in PyMoDAQ, it's likely a configuration or discovery issue.

## Step-by-Step Setup

### 1. Launch PyMoDAQ Dashboard

```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
source venv/bin/activate  # or: source .venv/bin/activate
python -m pymodaq.dashboard
```

### 2. Create New Preset or Load Existing

- Click "Preset Manager" (or similar)
- Create new preset or open existing one

### 3. Add Detector

Click "Add Detector" and look for:
- **Name**: `PyRPL_Scope_IPC` (with underscore and _IPC suffix)
- **NOT**: `PyRPL_Scope` (without _IPC - that's the broken version)

**If you don't see `PyRPL_Scope_IPC` in the list:**
1. Close PyMoDAQ
2. Reinstall plugin:
   ```bash
   pip uninstall pymodaq_plugins_pyrpl
   pip install -e .
   ```
3. Relaunch PyMoDAQ

### 4. Configure Plugin Settings

Once the detector is added, find these settings in the parameter tree:

```
Detector Settings
└── Connection
    ├── Red Pitaya Hostname: 100.107.106.75
    ├── PyRPL Config Name: pymodaq
    └── Connection Timeout (s): 30.0
└── Oscilloscope
    ├── Input Channel: in1
    ├── Decimation: 64
    ├── Trigger Source: immediately
    └── Acquisition Timeout (s): 5.0
└── Development
    ├── Mock Mode: ☑ TRUE  ← ENABLE THIS FOR TESTING
    └── Debug Logging: ☐ False
```

**Critical**: Make sure `Mock Mode` is checked/True!

### 5. Initialize Detector

- Click "Init. Detector" button (usually a green play icon)
- Watch the Logger panel for messages:
  ```
  [INFO] Initializing PyRPL IPC connection...
  [INFO] Starting PyRPL worker process...
  [INFO] Mock mode enabled - skipping PyRPL initialization
  [INFO] PyRPL worker initialized: Mock mode initialized
  [INFO] PyRPL initialization complete
  ```

**If you see SSH/Socket errors**: Mock mode is NOT enabled. Go back to settings.

**Expected time**: <5 seconds for mock mode

### 6. Acquire Data

- Click "Grab" button (camera icon)
- You should see a waveform appear (sine wave with noise, 16k points)

### 7. Troubleshooting Checklist

| Issue | Solution |
|-------|----------|
| Plugin not in list | Reinstall: `pip install -e .` |
| Wrong plugin name | Must be `PyRPL_Scope_IPC` (with _IPC) |
| SSH/Socket errors | Mock mode not enabled in settings |
| No mock mode option | Using wrong (old) plugin |
| Initialization hangs | Check Logger for actual error |
| No data displayed | Check PyMoDAQ viewer is configured |

## Common Mistakes

### ❌ Wrong Plugin
- Using `PyRPL_Scope` instead of `PyRPL_Scope_IPC`
- The old non-IPC plugin is broken

### ❌ Mock Mode Not Enabled
- Default is False (hardware mode)
- Must explicitly check the box for mock mode

### ❌ Wrong Python Environment
- PyMoDAQ must be launched from the venv with the plugin installed
- If using system Python, plugin won't be found

## Verification Test

Run this before trying PyMoDAQ:

```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
venv/bin/python test_mock_initialization.py
```

If this passes (it should!), the plugin works and the issue is with PyMoDAQ configuration.

## Still Not Working?

Please provide:
1. Screenshot of PyMoDAQ showing the plugin in detector list
2. Screenshot of the plugin settings showing Mock Mode checkbox
3. Copy of Logger output when you click "Init. Detector"
4. Output of: `venv/bin/pip list | grep pymodaq`

With that info, I can pinpoint exactly what's wrong.

## Expected Behavior (Mock Mode)

When working correctly:
- Init time: <5 seconds
- Logger shows "Mock mode initialized"
- Grab shows sine wave (0.5V amplitude, 1ms duration)
- 16,384 data points per acquisition
- Can repeatedly grab without errors
