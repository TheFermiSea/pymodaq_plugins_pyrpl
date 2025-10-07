# Hardware Testing Quick Start

**Phase 2 plugins are ready for hardware testing!**

---

## Quick Setup (5 minutes)

### 1. Find Your Red Pitaya

```bash
# If using mDNS hostname (easiest):
ping rp-f08d6c.local

# Or scan your network for Red Pitaya:
nmap -sn 192.168.1.0/24 | grep -i "red pitaya"
```

**Note down your hostname or IP address!**

---

### 2. Configure Test Scripts

Edit these files and update `RED_PITAYA_HOST`:

```bash
cd tests/hardware

# Edit all test scripts:
# 1. test_phase2_base.py
# 2. test_phase2_pid_plugin.py
# 3. test_phase2_all_plugins.py

# Change this line:
RED_PITAYA_HOST = 'rp-f08d6c.local'  # ← Your hostname/IP here
```

---

### 3. Run Tests

**Option A: Quick Test (2 minutes)**
```bash
python tests/hardware/test_phase2_base.py
```

**Option B: Full Suite (10-15 minutes)**
```bash
python tests/hardware/run_all_tests.py
```

**Option C: Individual Tests**
```bash
python tests/hardware/test_phase2_base.py           # Base functionality
python tests/hardware/test_phase2_pid_plugin.py     # PID plugin
python tests/hardware/test_phase2_all_plugins.py    # All plugins together
```

---

## Expected Results

### ✅ Success

```
====================================================================
TEST SUMMARY
====================================================================
✅ PASS: Singleton Creation
✅ PASS: Configuration Tracking
✅ PASS: Module Access
✅ PASS: Thread Safety
✅ PASS: Hardware Communication
✅ PASS: Cleanup

6/6 tests passed (100%)

🎉 All tests PASSED!
```

**If you see this** → Phase 2 plugins are working perfectly!

---

### ⚠️ Partial Success

```
5/6 tests passed (83%)
⚠️ 1 test(s) failed. Review errors above.
```

**If you see this** → Most features work, review what failed.

---

### ❌ Failure

```
❌ FAIL: Cannot connect to Red Pitaya at rp-xxx.local
```

**Common Issues**:
1. **Wrong hostname**: Try IP address instead
2. **Network issue**: Check `ping rp-xxx.local`
3. **Red Pitaya off**: Power cycle the device
4. **Firewall**: Temporarily disable firewall

---

## What to Test

### Priority 1: Core Functionality ⭐⭐⭐
```bash
python tests/hardware/test_phase2_base.py
```

**Must pass for Phase 2 to be viable.**

---

### Priority 2: Plugin Features ⭐⭐
```bash
python tests/hardware/test_phase2_pid_plugin.py
```

**Should pass for production use.**

---

### Priority 3: Integration ⭐
```bash
python tests/hardware/test_phase2_all_plugins.py
```

**Nice to have, validates multi-plugin scenarios.**

---

## Troubleshooting

### Can't Connect

```python
# Try this quick diagnostic:
from pyrpl import Pyrpl
p = Pyrpl(config='test', hostname='YOUR_HOSTNAME_HERE')
# If this works, tests should too
```

---

### Tests Hang

- Press `Ctrl+C` to abort
- Check network latency
- Try wired connection instead of WiFi

---

### Import Errors

```bash
# Install missing packages:
pip install pymodaq pyrpl
# Or with uv:
uv pip install pymodaq pyrpl
```

---

## After Testing

### If Tests Pass ✅

1. **Document results**: Save test output
2. **Use plugins**: Open PyMoDAQ dashboard and add plugins
3. **Celebrate**: Phase 2 is production-ready! 🎉

### If Tests Fail ❌

1. **Save logs**: `python run_all_tests.py 2>&1 | tee test_log.txt`
2. **Report issues**: Include full logs and Red Pitaya model
3. **Review**: Check `tests/hardware/README.md` for detailed troubleshooting

---

## Next Steps

### Using Plugins in PyMoDAQ

```bash
# 1. Launch dashboard
python -m pymodaq.dashboard

# 2. Add plugins:
#    - Actuators → "PyRPL PID" or "PyRPL ASG Direct"
#    - Viewers → "PyRPL Scope" or "PyRPL IQ"

# 3. Configure:
#    - Set hostname to your Red Pitaya
#    - Click "Initialize"
#    - Start using!
```

---

## Documentation

- **Detailed testing guide**: `tests/hardware/README.md`
- **Phase 2 implementation**: `PHASE2_IMPLEMENTATION_GUIDE.md`
- **Complete summary**: `PHASE2_COMPLETE_SUMMARY.md`

---

## Support

**Issues?** Check:
1. Red Pitaya is accessible: `ping rp-xxx.local`
2. PyRPL works: Test with PyRPL GUI first
3. Scripts configured: Hostname set correctly
4. Dependencies installed: `pip list | grep pymodaq`

**Still stuck?** Open a GitHub issue with:
- Test output (full logs)
- Red Pitaya model
- Network setup (WiFi/Ethernet)
- Python/PyMoDAQ/PyRPL versions

---

**Ready to test? Let's go!** 🚀

```bash
cd tests/hardware
python run_all_tests.py
```

**Good luck!** 🔬✨
