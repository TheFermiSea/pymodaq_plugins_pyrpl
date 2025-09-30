# Shared PyRPL Worker Architecture

## Problem
PyRPL can only have **ONE instance** connected to a Red Pitaya at a time. The original IPC architecture had each plugin (Scope, ASG, PID, IQ) creating its own worker process with its own PyRPL instance, causing conflicts.

## Solution
**ONE shared worker process** that all plugins connect to.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PyMoDAQ Dashboard                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Scope   │  │   ASG    │  │   PID    │  │   IQ     │  │
│  │  Plugin  │  │  Plugin  │  │  Plugin  │  │  Plugin  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │              │             │         │
│       └─────────────┴──────────────┴─────────────┘         │
│                          │                                  │
│                 ┌────────▼────────┐                        │
│                 │ SharedPyRPLManager │                     │
│                 │   (Singleton)    │                       │
│                 │  - command_lock  │                       │
│                 └────────┬─────────┘                       │
└──────────────────────────┼──────────────────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │  Command Queue   │
                  └────────┬─────────┘
                           │
                  ┌────────▼──────────┐
                  │  PyRPL Worker     │
                  │  (ONE Process)    │
                  │  - Pyrpl Instance │
                  │  - Red Pitaya @   │
                  │    100.107.106.75 │
                  └────────┬──────────┘
                           │
                  ┌────────▼─────────┐
                  │  Response Queue  │
                  └──────────────────┘
```

## Key Components

###  1. SharedPyRPLManager (Singleton)
- **Location:** `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`
- **Purpose:** Ensures only ONE worker process exists
- **Key Features:**
  - Singleton pattern - only one instance across all plugins
  - `start_worker()` - starts worker if not running, returns shared queues
  - `send_command()` - thread-safe command sending with response
  - `command_lock` - prevents race conditions between plugins

### 2. PyRPL Worker Process
- **Location:** `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`
- **Purpose:** Hosts the single PyRPL instance
- **Handles:**
  - Scope commands: `scope_acquire`, `scope_set_decimation`, etc.
  - ASG commands: `asg_setup`, `asg_set_frequency`, etc.
  - PID commands: `pid_configure`, `pid_set_setpoint`, etc.
  - IQ commands: `iq_setup`, `iq_get_measurement`, etc.

### 3. Plugin Modifications
All IPC plugins (Scope, ASG, PID, IQ) must:
1. Import `get_shared_worker_manager()`
2. In `ini_detector()`/`ini_stage()`: Call `manager.start_worker(config)`
3. Replace direct queue usage with `manager.send_command()`

## Thread Safety

**The Problem:**
Multiple plugins in different threads calling:
```python
command_queue.put({'command': 'scope_acquire', ...})
response = response_queue.get()  # ❌ WRONG! Might get ASG's response!
```

**The Solution:**
Use the manager's `send_command()` which locks around the pair:
```python
response = manager.send_command('scope_acquire', {...})  # ✓ SAFE!
```

## Usage Example

```python
from ...utils.shared_pyrpl_manager import get_shared_worker_manager

class DAQ_1DViewer_PyRPL_Scope_IPC(DAQ_Viewer_base):
    def ini_detector(self, controller=None):
        # Get the shared manager (singleton)
        manager = get_shared_worker_manager()

        # Start worker (or get existing one)
        config = {
            'hostname': '100.107.106.75',
            'config_name': 'pymodaq',
            'mock_mode': False
        }
        cmd_q, resp_q = manager.start_worker(config)

        # Store manager for later use
        self.pyrpl_manager = manager

        # ... initialization logic ...

    def grab_data(self, **kwargs):
        # Use thread-safe command sending
        response = self.pyrpl_manager.send_command(
            'scope_acquire',
            {
                'decimation': 64,
                'trigger_source': 'immediately',
                'input_channel': 'in1'
            }
        )

        if response['status'] == 'ok':
            data = response['data']
            # ... process data ...
```

## Benefits

1. ✅ **No hardware conflicts** - Only one PyRPL instance, eliminates "wrong control sequence" errors
2. ✅ **All plugins can work** - Scope + ASG + PID + IQ all access same hardware
3. ✅ **Thread-safe** - No race conditions or response confusion
4. ✅ **Resource efficient** - One worker process, not four
5. ✅ **Clean shutdown** - Automatic cleanup on exit

**Note:** With the recommended Command ID Multiplexing (see below), plugins achieve TRUE concurrent operation. Without it, commands are serialized (one at a time).

## Migration Guide

To migrate existing plugins to use shared worker:

1. **Import the manager:**
   ```python
   from ...utils.shared_pyrpl_manager import get_shared_worker_manager
   ```

2. **In `ini_detector()`/`ini_stage()`, replace:**
   ```python
   # OLD:
   self.command_queue = Queue()
   self.response_queue = Queue()
   self.worker_process = Process(target=pyrpl_worker_main, ...)
   self.worker_process.start()

   # NEW:
   self.pyrpl_manager = get_shared_worker_manager()
   cmd_q, resp_q = self.pyrpl_manager.start_worker(config)
   ```

3. **Replace all `_send_command()` calls:**
   ```python
   # OLD:
   self.command_queue.put({'command': cmd, 'params': params})
   response = self.response_queue.get(timeout=5)

   # NEW:
   response = self.pyrpl_manager.send_command(cmd, params, timeout=5)
   ```

4. **In `close()`, remove worker shutdown** (manager handles it):
   ```python
   # OLD:
   if self.worker_process:
       self.command_queue.put({'command': 'shutdown'})
       self.worker_process.join(timeout=5)

   # NEW:
   # Manager handles cleanup automatically
   pass
   ```

## Testing

Run the `pyrpl_IPC_test` preset which loads:
- Scope viewer (IN1)
- ASG actuator (OUT1)

Connect OUT1 → IN1 with BNC cable, configure ASG for 1kHz sine wave, and verify scope shows the signal.

## ⚠️ Critical Decision: Command Execution Architecture

### Option 1: Naive Synchronous (NOT RECOMMENDED)

A simple lock-based approach serializes all commands:

```python
def send_command(self, command, params):
    with self.command_lock:  # ONLY ONE PLUGIN AT A TIME
        self.command_queue.put({'command': command, 'params': params})
        return self.response_queue.get(timeout=5)
```

**Problem:**
- ❌ Scope acquiring data (50ms) **blocks** ASG from updating frequency
- ❌ Only ONE command in-flight at a time
- ❌ No true concurrency between plugins
- ❌ Slow commands block everything

**Timeline Example:**
```
t=0ms:   Scope sends 'scope_acquire' → acquires lock
t=0-50ms: Scope waits for response (HOLDS LOCK)
t=10ms:  ASG tries 'asg_setup' → **BLOCKED waiting for lock**
t=50ms:  Scope done, releases lock
t=50ms:  ASG finally sends command
```

### Option 2: Command ID Multiplexing (RECOMMENDED) ✅

Add command IDs and response demultiplexer for **true concurrent operation**:

```python
def send_command(self, command, params, timeout=5.0):
    cmd_id = str(uuid.uuid4())
    event = threading.Event()
    result_container = {}
    
    # Register response handler
    with self._response_lock:
        self._pending_responses[cmd_id] = (event, result_container)
    
    # Send command (no global lock!)
    self.command_queue.put({
        'command': command,
        'params': params,
        'id': cmd_id
    })
    
    # Wait for this specific response
    if event.wait(timeout):
        return result_container['response']
    else:
        raise TimeoutError(...)
```

**Benefits:**
- ✅ Multiple plugins send commands **concurrently**
- ✅ Each plugin blocks only for **its own** response
- ✅ PyRPL hardware modules (scope, ASG, PID) run in **parallel**
- ✅ Fast AND slow commands coexist without blocking

**Timeline Example:**
```
t=0ms:   Scope sends 'scope_acquire' (ID=A)
t=5ms:   ASG sends 'asg_setup' (ID=B) ← NOT BLOCKED!
t=10ms:  PID sends 'pid_get_setpoint' (ID=C) ← NOT BLOCKED!
t=15ms:  Worker receives A, processes, sends response (ID=A)
t=20ms:  Worker receives B, processes, sends response (ID=B)
t=25ms:  Worker receives C, processes, sends response (ID=C)
t=15ms:  Scope gets its response and continues
t=20ms:  ASG gets its response and continues
t=25ms:  PID gets its response and continues
```

### Implementation Requirements

1. **Manager Changes:**
   - Add `_pending_responses = {}` dict
   - Add `_response_listener_thread` to demultiplex responses
   - Remove global `command_lock` (not needed!)

2. **Worker Changes:**
   - Echo back `id` field in all responses
   - No other changes needed

3. **Plugin Changes:**
   - None! Use same `send_command()` API

### Decision Criteria

| Use Case | Option 1 (Naive) | Option 2 (Multiplexed) |
|----------|------------------|----------------------|
| Single plugin only | ✅ Fine | ✅ Fine |
| Multiple plugins, infrequent commands | ⚠️ Acceptable | ✅ Better |
| Scope + ASG together | ❌ Will serialize | ✅ **Required** |
| Fast continuous acquisition | ❌ Blocks everything | ✅ **Required** |
| Long-running commands | ❌ Catastrophic | ✅ **Required** |

**Recommendation: Implement Option 2 (Command ID Multiplexing) immediately.** It's only slightly more complex but enables the ACTUAL goal of "multiple PyRPL modules working together."

## Status

### Current Implementation
- ✅ SharedPyRPLManager architecture designed
- ✅ Singleton pattern ensures one worker process  
- ✅ Documentation complete
- ✅ Single Scope plugin working with hardware
- ⏳ **Command ID Multiplexing needs implementation** (REQUIRED for multi-plugin)
- ⏳ Plugins need migration to use shared manager
- ⏳ Testing with multiple plugins needed

### Required Work (For Multi-Plugin Support)
1. ⏳ **Implement Command ID Multiplexing in SharedPyRPLManager**
   - Add `_pending_responses` dict with threading.Event per command
   - Add `_response_listener_thread` to demultiplex responses
   - Update `send_command()` to use command IDs
   - Remove global `command_lock` (replaced by per-response events)

2. ⏳ **Update pyrpl_ipc_worker.py**
   - Echo back `id` field in all responses

3. ⏳ **Migrate all plugins**
   - Update to use SharedPyRPLManager
   - No API changes needed (same `send_command()` interface)

### Optional Future Work
- 💡 Full async with callbacks (for network analyzer, etc.)
- 💡 Progress updates for long-running commands  
- 💡 Cancellation support for slow operations

## Next Steps

### Phase 1: Implement Command ID Multiplexing (REQUIRED) 🎯
1. **Update SharedPyRPLManager:**
   - Implement response listener thread
   - Add command ID generation and tracking
   - Replace `command_lock` with per-response events

2. **Update pyrpl_ipc_worker.py:**
   - Echo `id` field in responses

3. **Test with single plugin:**
   - Verify no regression
   - Confirm IDs work correctly

### Phase 2: Migrate Plugins
1. Update Scope_IPC plugin to use SharedPyRPLManager
2. Update ASG_IPC plugin to use SharedPyRPLManager
3. **Test Scope + ASG together** ← THE ORIGINAL GOAL!
4. Update PID_IPC plugin to use SharedPyRPLManager
5. Update IQ_IPC plugin to use SharedPyRPLManager
6. Test all 4 plugins simultaneously

### Phase 3: Optional Enhancements (Future)
- Full async command execution with callbacks
- Progress notifications for slow commands
- Cancellation support

---

## Future Enhancement: Asynchronous Command Execution

**Note:** This section documents Gemini's suggested enhancement for handling long-running commands. Implementation is **optional** and should only be done if synchronous blocking becomes a problem in practice.

### Current Limitation

The current `send_command` method is **synchronous**: the plugin thread sends a command and blocks (waits) until a response is received. For the majority of PyRPL commands that execute quickly (< 100ms), this is the simplest and most robust approach.

### Rationale for Asynchronicity

A problem arises if a command triggers a long-running task in the PyRPL worker (e.g., a slow hardware sweep, waiting for a PID loop to stabilize). During this time, the PyMoDAQ plugin thread that called `send_command` will be completely blocked. While this won't freeze the main PyMoDAQ GUI, it will make that specific plugin unresponsive to other commands (e.g., `stop`, `get_status`).

An asynchronous, callback-based approach solves this by allowing the plugin to send a command and immediately continue its work. The result is delivered later via a callback function.

### Proposed Asynchronous Architecture

This requires several additions to the `SharedPyRPLManager`:

1.  **Unique Command IDs**: Every command sent must have a unique identifier. The worker will include this ID in its response.
2.  **Callback Registry**: A thread-safe dictionary within the manager to store a mapping of `command_id` to the `callback_function` that should be executed when the response arrives.
3.  **Response Listener Thread**: The manager will spawn a single, dedicated background thread whose only job is to listen on the `response_queue` for incoming results.
4.  **Callback Execution**: When the listener thread receives a response, it looks up the `command_id`, finds the corresponding callback in the registry, and executes it with the response data.

### Implementation Details

#### 1. `SharedPyRPLManager` Modifications

The manager would be extended as follows:

```python
# In: src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py
import uuid
from threading import Thread, Lock

class SharedPyRPLManager:
    def __init__(self):
        # ... existing attributes ...
        self._callbacks = {}
        self._callback_lock = Lock()
        self._response_thread = None

    def start_worker(self, config):
        # ... existing start_worker logic ...
        if self.worker_process and not self._response_thread:
            self._response_thread = Thread(target=self._response_listener, daemon=True)
            self._response_thread.start()
        return self.command_queue, self.response_queue

    def _response_listener(self):
        """
        Runs in a background thread. Listens for all responses from the worker
        and dispatches them to the appropriate callback.
        """
        while True:
            response = self.response_queue.get()
            if response is None: # Sentinel for shutdown
                break

            cmd_id = response.get('id')
            if cmd_id:
                with self._callback_lock:
                    callback = self._callbacks.pop(cmd_id, None)
                if callback:
                    callback(response)
                # else: handle response with no callback (e.g. from sync command)

    def send_command_async(self, command, params, callback):
        """Sends a command and returns immediately. The response will be passed to the callback function."""
        if not self.worker_process or not self.worker_process.is_alive():
            raise RuntimeError("PyRPL worker process is not running.")

        cmd_id = str(uuid.uuid4())
        with self._callback_lock:
            self._callbacks[cmd_id] = callback

        self.command_queue.put({
            'command': command,
            'params': params,
            'id': cmd_id
        })

    # ... existing send_command and shutdown logic ...
    # The shutdown logic would need to be updated to also signal
    # the _response_listener thread to exit by putting None on the queue.
```

#### 2. Worker Process Modifications

The worker must be updated to echo back the `id` in its response.

```python
# In: src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py

# ... inside the main while loop ...
command_request = command_queue.get()
cmd_id = command_request.get('id') # Get the command ID

# ... after processing a command ...
response_data = {'status': 'ok', 'data': result}
if cmd_id:
    response_data['id'] = cmd_id # Echo the ID back

response_queue.put(response_data)
```

#### 3. Plugin Usage Example

The plugin would define a callback method to handle the result.

```python
class DAQ_1DViewer_PyRPL_Scope_IPC(DAQ_Viewer_base):
    # ... ini_detector as before ...

    def grab_data(self, **kwargs):
        # For a long acquisition, use the async method
        self.pyrpl_manager.send_command_async(
            'start_long_sweep',
            {'duration': 60},
            self._on_long_sweep_done
        )
        # The grab_data method can return immediately

    def _on_long_sweep_done(self, response):
        """
        This method is the callback. It will be executed by the manager's
        listener thread when the data is ready.
        """
        if response['status'] == 'ok':
            data = response['data']
            # IMPORTANT: To update the GUI, this callback must emit a Qt signal
            # that the main plugin object is connected to.
            self.data_ready_signal.emit(data)
```

### Recommendations

1. **Implement Command ID Multiplexing first** (as described in "Option 2" above)
   - This enables true concurrent operation
   - Required for Scope + ASG + PID to work together
   - Not much more complex than naive synchronous

2. **Full async with callbacks is optional**
   - Only implement if network analyzer or other slow commands are needed
   - Most commands (< 100ms) work fine with multiplexed synchronous approach
   - Adds complexity that's unnecessary for 90% of use cases

3. **Thorough testing with multiple plugins**
   - Test all combinations: Scope+ASG, Scope+ASG+PID, all 4 plugins
   - Verify no race conditions or deadlocks
   - Confirm hardware modules operate concurrently
---

## Summary

### What Works Now ✅
✅ **Single Scope plugin** acquiring real data from Red Pitaya (100.107.106.75)  
✅ **Hardware loopback verified** (OUT1 → IN1 with ~40mV test signal visible)  
✅ **Proper channel selection** (IN1/IN2) with signal statistics logging  
✅ **SharedPyRPLManager architecture** designed and documented  
✅ **No more "wrong control sequence" errors** from multiple PyRPL instances  

### What Must Be Done (REQUIRED for Multi-Plugin) 🎯
1. ⏳ **Implement Command ID Multiplexing in SharedPyRPLManager**
   - This enables TRUE concurrent operation of Scope + ASG + PID + IQ
   - Without it, commands are serialized (defeating the whole purpose!)
   
2. ⏳ **Update worker to echo command IDs in responses**

3. ⏳ **Migrate all 4 plugins to use SharedPyRPLManager**

4. ⏳ **Test Scope + ASG simultaneously** ← **THE ORIGINAL GOAL!**

### What Can Be Done Later (Optional Enhancement) 💡
- Full async callbacks (for network analyzer sweeps, etc.)
- Progress updates during long operations  
- Command cancellation support  

### Key Insight 💡
**Command ID Multiplexing is NOT optional** - it's the difference between:
- ❌ Plugins taking turns (serialized, slow, defeats the purpose)
- ✅ Plugins working together (concurrent, fast, achieves the goal)

The "naive synchronous" approach with a global lock **does not enable the use case** of "Scope + ASG running together". It only prevents crashes, but forces everything to wait in line.

### Path Forward
Implement Command ID Multiplexing (Phase 1) **first**, then migrate plugins (Phase 2). This delivers the actual goal of multiple PyRPL modules accessible from PyMoDAQ simultaneously.
