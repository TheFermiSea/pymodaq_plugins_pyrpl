# PyRPL Multi-Module Implementation Roadmap

## Current Status: ✅ Single Module Working

The Scope IPC plugin successfully acquires real data from Red Pitaya hardware at 100.107.106.75.

**Working:**
- Hardware connection established
- IPC worker process functional
- Scope data acquisition with proper channel selection
- Signal statistics logging (Vmin, Vmax, Vpp)
- Hardware loopback verified (OUT1 → IN1 showing ~40mV signal)

**Not Working:**
- Using Scope + ASG simultaneously (preset `pyrpl_IPC_test` fails with "wrong control sequence from server")
- Reason: Each plugin creates its own PyRPL worker → hardware conflict

---

## Goal: Multiple Modules Working Simultaneously

Enable Scope + ASG + PID + IQ to work together in the same PyMoDAQ dashboard.

---

## Implementation Steps

### Phase 1: Migrate Scope Plugin ⏳

**File:** `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope_IPC.py`

**Changes:**
1. Import SharedPyRPLManager:
   ```python
   from ...utils.shared_pyrpl_manager import get_shared_worker_manager
   ```

2. In `__init__()`, remove queue/process initialization:
   ```python
   # REMOVE:
   self.command_queue = None
   self.response_queue = None
   self.worker_process = None
   
   # ADD:
   self.pyrpl_manager = None
   ```

3. In `ini_detector()`, use shared manager:
   ```python
   # Get shared manager
   self.pyrpl_manager = get_shared_worker_manager()
   
   # Start worker (or get existing)
   config = {
       'hostname': self.settings['connection', 'rp_hostname'],
       'config_name': self.settings['connection', 'config_name'],
       'mock_mode': self.settings['dev', 'mock_mode']
   }
   
   try:
       cmd_q, resp_q = self.pyrpl_manager.start_worker(config)
       # Wait for init response from worker
       response = resp_q.get(timeout=30)
       if response['status'] != 'ok':
           raise ConnectionError(f"Worker init failed: {response['data']}")
   except Exception as e:
       # Handle error
       ...
   ```

4. Replace all `_send_command()` calls:
   ```python
   # BEFORE:
   def _send_command(self, command, params):
       self.command_queue.put({'command': command, 'params': params})
       return self.response_queue.get(timeout=5)
   
   # AFTER:
   def _send_command(self, command, params):
       return self.pyrpl_manager.send_command(command, params, timeout=5)
   ```

5. In `close()`, remove shutdown logic:
   ```python
   # REMOVE:
   if self.worker_process:
       self.command_queue.put({'command': 'shutdown'})
       self.worker_process.join(timeout=5)
   
   # Manager handles cleanup automatically
   ```

**Testing:**
- ✅ Scope still works with single plugin
- ✅ No regression in functionality

---

### Phase 2: Migrate ASG Plugin ⏳

**File:** `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_ASG_IPC.py`

**Changes:** Same pattern as Scope plugin:
1. Import SharedPyRPLManager
2. Use `self.pyrpl_manager` instead of own queues
3. Replace `_send_command()` with `manager.send_command()`
4. Remove shutdown logic

**Testing:**
- ✅ ASG still works alone
- ✅ Test Scope + ASG simultaneously with `pyrpl_IPC_test` preset
- ✅ Verify OUT1 signal generation visible on IN1 scope trace

---

### Phase 3: Migrate PID Plugin ⏳

**File:** `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_PID_IPC.py`

**Changes:** Same migration pattern

**Testing:**
- ✅ PID works alone
- ✅ Test Scope + PID
- ✅ Test Scope + ASG + PID

---

### Phase 4: Migrate IQ Plugin ⏳

**File:** `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/daq_0Dviewer_PyRPL_IQ_IPC.py`

**Changes:** Same migration pattern

**Testing:**
- ✅ IQ works alone
- ✅ Test all 4 modules together

---

## Verification Tests

### Test 1: Scope + ASG (Loopback)
**Setup:**
- Physical BNC cable: OUT1 → IN1
- Dashboard preset: `pyrpl_IPC_test`

**Procedure:**
1. Configure ASG: 1 kHz sine, 0.5V amplitude, output to OUT1
2. Configure Scope: IN1 input, decimation 64, trigger immediately
3. Start ASG output
4. Grab scope data

**Success Criteria:**
- ✅ Scope displays 1 kHz sine wave
- ✅ Vpp ≈ 1.0V (peak-to-peak)
- ✅ No "wrong control sequence" errors
- ✅ Both plugins respond to settings changes

### Test 2: Scope + ASG + PID (Feedback Loop)
**Setup:**
- IN1 monitors process variable
- PID controls output
- ASG provides test signal

**Success Criteria:**
- ✅ All three modules active simultaneously
- ✅ No hardware conflicts
- ✅ Settings changes propagate correctly

### Test 3: All Modules (Scope + ASG + PID + IQ)
**Success Criteria:**
- ✅ All 4 plugins initialize without errors
- ✅ Each plugin can send commands
- ✅ No deadlocks or race conditions
- ✅ Clean shutdown of all plugins

---

## Risk Mitigation

### Issue: Worker Initialization Race
**Risk:** Multiple plugins call `start_worker()` simultaneously during dashboard startup.

**Mitigation:** SharedPyRPLManager uses a lock and checks if worker already running.

**Test:** Load preset with all 4 plugins at once.

### Issue: Response Confusion
**Risk:** Plugin A sends command, gets Plugin B's response.

**Mitigation:** `command_lock` serializes command/response pairs.

**Test:** Rapidly send commands from multiple plugins in parallel.

### Issue: Worker Crash
**Risk:** Worker process crashes, all plugins fail.

**Mitigation:** 
- Worker logging shows detailed errors
- Plugins detect dead worker via `is_worker_running()`
- Could add auto-restart logic in manager

**Test:** Kill worker process manually, verify plugins handle gracefully.

---

## Timeline Estimate

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Migrate Scope plugin | 30 min | ⏳ Not started |
| 1 | Test Scope alone | 10 min | ⏳ |
| 2 | Migrate ASG plugin | 30 min | ⏳ |
| 2 | Test Scope + ASG | 20 min | ⏳ |
| 3 | Migrate PID plugin | 30 min | ⏳ |
| 3 | Test Scope + ASG + PID | 20 min | ⏳ |
| 4 | Migrate IQ plugin | 30 min | ⏳ |
| 4 | Test all 4 modules | 30 min | ⏳ |
| | **Total** | **3-4 hours** | |

---

## Success Metrics

✅ **Primary Goal:** Scope + ASG working simultaneously  
✅ **Secondary Goal:** Scope + ASG + PID working together  
✅ **Stretch Goal:** All 4 modules (Scope + ASG + PID + IQ) functional  

Once this is working, the original objective of accessing multiple PyRPL modules from PyMoDAQ will be **COMPLETE**.

---

## Next Action

**Start Phase 1:** Migrate the Scope plugin to use SharedPyRPLManager.

See: `SHARED_WORKER_ARCHITECTURE.md` for detailed migration guide.
