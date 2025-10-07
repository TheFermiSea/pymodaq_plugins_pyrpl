# PyRPL-PyMoDAQ Integration Strategy

## Section 1: Project Overview & Task Matrix

### 1.1. Executive Summary

This document outlines a comprehensive, two-phase strategy for integrating the `pyrpl` library with PyMoDAQ. The primary objective is to deliver a stable, high-performance, and user-friendly solution for controlling PyRPL-powered hardware directly from the PyMoDAQ environment.

*   **Phase 1** is focused on **rapid development** via a direct, **in-process plugin**. This approach prioritizes speed and simplicity to quickly deliver a functional prototype for validation and immediate use, with the understanding that it carries stability risks.
*   **Phase 2** transitions the project to a robust, production-ready **bridge server architecture**. This isolates the `pyrpl` hardware control into a separate, stable process, ensuring that any hardware-related failures do not impact the main PyMoDAQ application. This is the definitive, long-term architecture.

The "Contract First" principle is the strategic foundation of this plan, guaranteeing a seamless and low-effort migration from Phase 1 to Phase 2 by enforcing a consistent API.

### 1.2. Project & Version Control

*   **Project Tracking:** All tasks, progress, and milestones will be logged and tracked on the **Zen MPC Server** under the project "PyRPL-PyMoDAQ Integration."
*   **Version Control:** All source code will be managed in Git on the **Octocode MCP Server**. The following branching strategy is mandated:
    *   `main`: Contains stable, production-ready releases (the final result of Phase 2).
    *   `develop`: The primary integration branch for completed features. All feature branches are merged into `develop` before being promoted to `main`.
    *   `feature/phase1-plugin`: All development work for the initial in-process plugin.
    *   `feature/phase2-bridge`: All development work for the bridge server and the updated client plugin.

### 1.3. Task Matrix

| Task ID | Task Description | Dependencies | Definition of Done |
| :--- | :--- | :--- | :--- |
| T01 | Define `PyrplInstrumentContract` | None | The abstract base class is fully defined with all methods, type hints, and docstrings, and is committed to the `develop` branch. |
| T02 | Implement Phase 1 `PyrplWorker` & Plugin | T01 | The in-process plugin and its `QThread` worker are created, implements the contract, and pass all unit tests against a mock object. |
| T03 | Create Test Suite for Phase 1 | T02 | A comprehensive `pytest` suite is written, validating all contract methods, UI integration, and thread safety. |
| T04 | Build Phase 2 Bridge Server | T01 | The standalone server application is created, reuses the `PyrplWorker` logic, and is confirmed to expose all contract methods over TCP. |
| T05 | Update Plugin for Phase 2 (Client) | T04 | The Phase 1 plugin is refactored into a TCP client that connects to the bridge server. Core logic remains unchanged. |
| T06 | Develop Migration & Testing Protocol | T04, T05 | A complete test plan and a step-by-step user migration guide are documented and validated. |
| T07 | Final Documentation & Release | T06 | All user and developer documentation is consolidated, and a final release candidate is tagged on the `main` branch. |

---

## Section 2: The PyRPL Device Contract

### 2.1. "Contract First" Principle

The "Contract First" principle is the most critical element for ensuring the success of our two-phase strategy. By defining a formal, stable interface—the `PyrplInstrumentContract`—at the outset, we create a powerful abstraction layer.

This approach provides two key benefits:
1.  **Seamless Migration:** The core logic of the PyMoDAQ plugin will be written against the contract, not the implementation. This means the code for `grab_data`, `setup_scope`, etc., will be nearly identical between Phase 1 and Phase 2. The only change will be the object that fulfills the contract (a local worker vs. a remote TCP client).
2.  **Parallel Development & Testability:** Once the contract is defined, the bridge server (Phase 2) can be developed and tested in parallel with the in-process plugin (Phase 1). Furthermore, our test suite can be written to run against any class that implements the contract, allowing us to reuse tests for both phases.

### 2.2. `PyrplInstrumentContract` Definition

The following abstract base class is the formal contract for all PyRPL instrument interactions.

```python
# src/pymodaq_plugins_pyrpl/contract.py
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
import numpy as np

class PyrplInstrumentContract(ABC):
    """
    Abstract Base Class defining the contract for PyRPL instrument control.

    This contract ensures that both the in-process (Phase 1) and bridge-server
    (Phase 2) implementations provide an identical interface to the PyMoDAQ plugin.
    """

    @abstractmethod
    def connect(self, config: Dict) -> bool:
        """
        Establishes a connection to the PyRPL hardware (Red Pitaya).

        Args:
            config (Dict): A dictionary containing connection parameters,
                           e.g., {'hostname': '192.168.1.100', 'user': 'root', ...}.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """
        Closes the connection to the PyRPL hardware.
        """
        raise NotImplementedError

    @abstractmethod
    def get_idn(self) -> Optional[str]:
        """
        Retrieves an identification string from the instrument.

        Returns:
            Optional[str]: A string identifying the hardware, or None if not connected.
        """
        raise NotImplementedError

    @abstractmethod
    def setup_scope(
        self,
        channel: str,
        decimation: int,
        trigger_source: str,
        trigger_level: float,
        duration: float
    ) -> None:
        """
        Configures the oscilloscope module.

        Args:
            channel (str): The input channel to use (e.g., 'in1', 'in2').
            decimation (int): The decimation factor for the sampling rate (e.g., 64).
            trigger_source (str): The source for the acquisition trigger (e.g., 'ch1_positive_edge').
            trigger_level (float): The trigger level in volts.
            duration (float): The acquisition duration in seconds.
        """
        raise NotImplementedError

    @abstractmethod
    def acquire_trace(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Acquires a single trace from the configured oscilloscope channel.
        This is expected to be a blocking call.

        Returns:
            Tuple[np.ndarray, np.ndarray]: A tuple containing two NumPy arrays:
                                           (time_axis, voltage_data).
        """
        raise NotImplementedError

    @abstractmethod
    def set_output_voltage(self, channel: str, voltage: float) -> None:
        """
        Sets the DC voltage of an analog output channel.

        Args:
            channel (str): The output channel to set (e.g., 'out1', 'out2').
            voltage (float): The voltage to set, in volts.
        """
        raise NotImplementedError
```

---

## Section 3: Phase 1 Implementation Plan (In-Process)

### 3.1. Implementation Strategy

For Phase 1, we will create a `DAQ_1DViewer` plugin that directly controls `pyrpl`. To ensure the PyMoDAQ GUI remains responsive, all blocking hardware calls will be offloaded to a separate `QThread`. A `PyrplWorker` class, inheriting from `QObject` and our `PyrplInstrumentContract`, will manage the `pyrpl` object and execute all hardware operations.

### 3.2. Code - `PyrplWorker`

This `QObject` worker will live in the `QThread` and handle all direct interactions with the `pyrpl` library.

```python
# src/pymodaq_plugins_pyrpl/phase1_worker.py
from qtpy.QtCore import QObject, Signal, Slot
from typing import Dict, Tuple, Optional
import numpy as np
from pyrpl import Pyrpl

from .contract import PyrplInstrumentContract

class PyrplWorker(QObject, PyrplInstrumentContract):
    """
    Worker object that lives in a separate thread to handle blocking
    hardware calls to the pyrpl library. Implements the device contract.
    """
    # Signal to emit acquired data back to the main thread
    trace_ready = Signal(tuple)
    # Signal to emit status updates
    status_update = Signal(str)

    def __init__(self):
        super().__init__()
        self.pyrpl: Optional[Pyrpl] = None

    @Slot(dict)
    def connect(self, config: Dict) -> bool:
        try:
            self.pyrpl = Pyrpl(**config)
            self.status_update.emit(f"Successfully connected to {self.get_idn()}")
            return True
        except Exception as e:
            self.status_update.emit(f"Connection to PyRPL failed: {e}")
            return False

    @Slot()
    def disconnect(self):
        if self.pyrpl and self.pyrpl.rp:
            self.pyrpl.rp.end()
            self.status_update.emit("Disconnected from PyRPL.")
        self.pyrpl = None

    def get_idn(self) -> Optional[str]:
        return f"PyRPL on {self.pyrpl.rp.hostname}" if self.pyrpl and self.pyrpl.rp else "Not Connected"

    @Slot(str, int, str, float, float)
    def setup_scope(self, channel, decimation, trigger_source, trigger_level, duration):
        if not self.pyrpl: return
        scope = self.pyrpl.rp.scope
        scope.input1 = channel
        scope.decimation = decimation
        scope.trigger_source = trigger_source
        scope.trigger_level = trigger_level
        # Duration is used to calculate the number of points, not set directly
        # This logic will be handled in acquire_trace or by the plugin
        self.status_update.emit("Scope configured.")

    @Slot()
    def acquire_trace(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs the blocking hardware call and emits the result via a signal.
        """
        if not self.pyrpl: return (np.array([]), np.array([]))
        try:
            # This is the blocking call that necessitates the thread
            data = self.pyrpl.rp.scope.single() 
            times = self.pyrpl.rp.scope.times
            self.trace_ready.emit((times, data))
            return (times, data)
        except Exception as e:
            self.status_update.emit(f"Acquisition failed: {e}")
            return (np.array([]), np.array([]))

    @Slot(str, float)
    def set_output_voltage(self, channel: str, voltage: float):
        if not self.pyrpl: return
        if channel == 'out1':
            self.pyrpl.rp.asg1.setup(amplitude=voltage, waveform='dc')
        elif channel == 'out2':
            self.pyrpl.rp.asg2.setup(amplitude=voltage, waveform='dc')
        self.status_update.emit(f"Set {channel} to {voltage:.3f} V.")

```

### 3.3. Code - PyMoDAQ Plugin

This plugin manages the `QThread` and communicates with the `PyrplWorker` via signals and slots.

```python
# src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_Pyrpl_InProcess.py
from qtpy.QtCore import QThread, Signal
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand

from ..phase1_worker import PyrplWorker

class DAQ_1DViewer_Pyrpl_InProcess(DAQ_Viewer_base):
    # Signal to trigger a connection in the worker thread
    do_connect = Signal(dict)
    # Signal to trigger acquisition
    do_acquire = Signal()

    params = comon_parameters + [
        {'title': 'PyRPL Config:', 'name': 'pyrpl_config', 'type': 'group', 'children': [
            {'title': 'Hostname:', 'name': 'hostname', 'type': 'str', 'value': '192.168.1.100'},
            # Add other pyrpl config params here...
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.worker: Optional[PyrplWorker] = None
        self.thread: Optional[QThread] = None

    def ini_detector(self, controller=None):
        self.status.update_sig.emit(ThreadCommand("Update_Status", ["Initializing In-Process PyRPL..."]))
        
        # 1. Create and manage the worker and thread
        self.thread = QThread()
        self.worker = PyrplWorker()
        self.worker.moveToThread(self.thread)

        # 2. Connect signals and slots
        self.do_connect.connect(self.worker.connect)
        self.do_acquire.connect(self.worker.acquire_trace)
        self.worker.trace_ready.connect(self.emit_data)
        self.worker.status_update.connect(lambda msg: self.status.update_sig.emit(ThreadCommand("Update_Status", [msg])))

        # 3. Start the thread
        self.thread.start()

        # 4. Trigger the connection
        config = {'hostname': self.settings.child('pyrpl_config', 'hostname').value()}
        self.do_connect.emit(config)
        
        self.status.update_sig.emit(ThreadCommand("Update_Status", ["PyRPL Worker Initialized."]))
        return self.status

    def close(self):
        if self.worker:
            self.worker.disconnect()
        if self.thread:
            self.thread.quit()
            self.thread.wait(5000) # Wait 5s for the thread to finish

    def grab_data(self, Naverage=1, **kwargs):
        """
        Non-blocking call to start data acquisition. Emits a signal
        that the worker thread will pick up.
        """
        self.do_acquire.emit()

    @Slot(tuple)
    def emit_data(self, data: tuple):
        """
        Slot that receives the data from the worker thread and emits it
        to the PyMoDAQ data pipeline.
        """
        times, voltages = data
        x_axis = Axis(data=times, label='Time', units='s')
        self.dte_signal.emit(DataFromPlugins(name='PyRPL Scope', data=[voltages], dim='Data1D', axes=[x_axis]))
```

---

## Section 4: Phase 2 Implementation Plan (Bridge Server)

### 4.1. Implementation Strategy

We will now refactor to a client-server model. A standalone Python script will run the `PyrplBridgeServer`, which instantiates our `PyrplWorker` and exposes its methods over TCP using PyMoDAQ's `TCPServer`. The PyMoDAQ plugin will be simplified to a `TCPClient` that makes network calls to the server. Because we used the "Contract First" approach, the `PyrplWorker` can be reused with almost no changes.

### 4.2. Code - `PyrplBridgeServer`

This script is the standalone server application.

```python
# scripts/pyrpl_bridge_server.py
import sys
from pymodaq.utils.tcp_ip.tcp_server import TCPServer
# We can reuse the exact same worker from Phase 1!
from src.pymodaq_plugins_pyrpl.phase1_worker import PyrplWorker 

# Add the source directory to the path to find our modules
# In a real package, this would be handled by installation.
sys.path.append('../')

class PyrplBridgeServer:
    def __init__(self, ip_address="localhost", port=6341):
        """
        Initializes the bridge server.
        
        It creates an instance of the PyrplWorker, which holds the pyrpl object
        and all the control logic. This worker object is then passed to PyMoDAQ's
        TCPServer, which automatically exposes its public methods over the network.
        """
        # 1. The instrument logic is the same as Phase 1
        self.instrument_controller = PyrplWorker() 
        
        # 2. Setup the PyMoDAQ TCP Server with the controller
        self.server = TCPServer(ip_address, port, controller=self.instrument_controller)
        print(f"PyRPL Bridge Server listening on {ip_address}:{port}")
        print("Press Ctrl+C to quit.")

    def run(self):
        """Starts the server's command loop."""
        self.server.run()

if __name__ == '__main__':
    # In a real application, you might parse command-line args for IP/port
    server = PyrplBridgeServer()
    server.run()
```

### 4.3. Code - PyMoDAQ Client Plugin

The plugin is now much simpler. It no longer manages threads and directly uses a `TCPClient` as its controller.

```python
# src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_Pyrpl_BridgeClient.py
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.tcp_ip.tcp_client import TCPClient

class DAQ_1DViewer_Pyrpl_BridgeClient(DAQ_Viewer_base):
    params = comon_parameters + [
        {'title': 'Server Config:', 'name': 'server_config', 'type': 'group', 'children': [
            {'title': 'IP Address:', 'name': 'ip_address', 'type': 'str', 'value': 'localhost'},
            {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': 6341},
        ]},
        # ... other scope params ...
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        # The controller is now a TCPClient, which will be our remote proxy
        self.controller: Optional[TCPClient] = None

    def ini_detector(self, controller=None):
        self.status.update_sig.emit(ThreadCommand("Update_Status", ["Initializing Bridge Client..."]))
        
        # 1. Instantiate the TCPClient
        ip = self.settings.child('server_config', 'ip_address').value()
        port = self.settings.child('server_config', 'port').value()
        self.controller = TCPClient(ip, port)
        
        # 2. Call the 'connect' method defined in our contract
        # The TCPClient forwards this call to the remote PyrplWorker
        config = {'hostname': '192.168.1.100'} # This should come from settings
        is_connected = self.controller.connect(config=config) 
        if not is_connected:
            raise ConnectionError("Failed to connect to the PyRPL Bridge Server.")

        # 3. Get remote instrument ID
        idn = self.controller.get_idn()
        self.status.update_sig.emit(ThreadCommand("Update_Status", [f"Connected to: {idn}"]))
        return self.status

    def close(self):
        if self.controller:
            self.controller.disconnect()

    def grab_data(self, Naverage=1, **kwargs):
        """
        The core logic is identical to Phase 1. The `acquire_trace` call
        is now a network request, but the plugin doesn't know or care.
        """
        if self.controller:
            # This call is transparently sent over TCP to the server
            times, voltages = self.controller.acquire_trace() 
            
            x_axis = Axis(data=times, label='Time', units='s')
            self.dte_signal.emit(DataFromPlugins(name='PyRPL Scope', data=[voltages], dim='Data1D', axes=[x_axis]))
```

---

## Section 5: Testing & Migration Protocol

### 5.1. Testing Protocol

A rigorous testing protocol is essential to validate both phases and ensure a smooth transition.

**Unit Tests:**
*   [ ] Create a mock `Pyrpl` class that simulates hardware behavior without needing a real Red Pitaya.
*   [ ] Write `pytest` tests for the `PyrplWorker` class, using the mock object to verify that all contract methods (`connect`, `acquire_trace`, etc.) behave as expected.
*   [ ] Ensure all unit tests pass before proceeding to integration testing.

**Integration Tests (Phase 1):**
*   [ ] Launch the `DAQ_1DViewer_Pyrpl_InProcess` plugin within the PyMoDAQ dashboard.
*   [ ] **Connection:** Verify the plugin initializes and connects to the hardware (or mock) without errors.
*   **UI Responsiveness:** Confirm the PyMoDAQ GUI remains fully responsive while the plugin is acquiring data, proving the `QThread` is working correctly.
*   **Data Acquisition:** Perform single and continuous acquisitions. Verify that data is displayed correctly and matches the expected output from the hardware.
*   **Disconnection:** Test the `close` method, ensuring the thread is properly terminated and resources are released.

**Integration Tests (Phase 2):**
*   [ ] Run the `pyrpl_bridge_server.py` script as a separate process.
*   [ ] Launch the `DAQ_1DViewer_Pyrpl_BridgeClient` plugin and verify it connects to the server.
*   [ ] Repeat all Phase 1 integration tests, ensuring the behavior is identical from the user's perspective.
*   **Failure Mode Test 1 (Server Crash):** While the client is connected, manually terminate the server process. Verify that the plugin detects the disconnection gracefully and reports an error without crashing PyMoDAQ.
*   **Failure Mode Test 2 (Reconnect):** After the server has been terminated, restart it. Verify that the client plugin can successfully re-initialize and connect to the newly started server.

### 5.2. User Migration Guide (Phase 1 to Phase 2)

Migrating from the prototype plugin to the production bridge server is a simple, three-step process.

1.  **Launch the Bridge Server:**
    *   Open a new terminal or command prompt.
    *   Navigate to the `scripts` directory of the project.
    *   Run the server with the command: `python pyrpl_bridge_server.py`
    *   A confirmation message will appear: `PyRPL Bridge Server listening on localhost:6341`. **Keep this terminal window open.** The server must be running for the plugin to work.

2.  **Switch Plugins in PyMoDAQ:**
    *   Start the PyMoDAQ application.
    *   In the DAQ Manager, if you have the "PyRPL In-Process" plugin loaded, remove it.
    *   Add a new `DAQ_Viewer` and select the **"PyRPL Bridge Client"** plugin from the list.

3.  **Configure and Initialize:**
    *   In the new plugin's settings, ensure the "Server IP" is `localhost` (if running on the same machine) and the "Server Port" is `6341`.
    *   Click the "Init" button. The plugin will connect to the server, and the status log will show a successful connection message. The plugin is now ready to use.

### 5.3. Troubleshooting

*   **"Connection Refused" Error:** This is the most common issue. It means the `PyrplBridgeServer` is not running, or the IP/port in the plugin settings is incorrect. Check that the server script is running in its terminal and that the settings match.
*   **Firewall Issues:** If the server and client are on different computers, a firewall may be blocking the connection. Ensure that your system's firewall allows incoming TCP traffic on port `6341` on the server machine.
*   **Hardware Not Found by Server:** If the server terminal shows an error like "Could not connect to Red Pitaya," the issue is between the server and the hardware. Check that the Red Pitaya is powered on, connected to the network, and that the `hostname` in your `pyrpl` configuration is correct.

### 5.4. User Documentation Template (`README.md`)

```markdown
# PyMoDAQ Plugin for PyRPL

This package provides PyMoDAQ plugins for controlling and acquiring data from hardware running the PyRPL library, such as the Red Pitaya.

## Architecture

This integration uses a client-server architecture for stability. A standalone "Bridge Server" runs on the computer connected to the PyRPL hardware, and the PyMoDAQ plugin acts as a network client. This ensures that any hardware issues do not crash the main PyMoDAQ application.

## Installation

[... Installation instructions via pip ...]

## Quick Start Guide

1.  **Start the Server:** Open a terminal and run the following command:
    ```bash
    python -m pymodaq_plugins_pyrpl.server
    ```
    Keep this terminal open.

2.  **Launch PyMoDAQ:** Start the PyMoDAQ dashboard.

3.  **Load the Plugin:** In the DAQ Manager, add a new viewer/actuator and select the "PyRPL Bridge Client" plugin.

4.  **Configure:** In the plugin settings, enter the IP address and port of the server (default is `localhost:6341`).

5.  **Initialize:** Click the "Init" button to connect. You are now ready to acquire data.

## Plugin Settings

| Setting | Description | Default Value |
| :--- | :--- | :--- |
| **Server IP** | The IP address of the machine running the Bridge Server. | `localhost` |
| **Server Port** | The port the Bridge Server is listening on. | `6341` |
| **Hostname** | The hostname or IP of the Red Pitaya device. | `192.168.1.100` |
| ... | ... | ... |

## Troubleshooting

*   **Connection Refused:** Ensure the Bridge Server is running and that the IP/port settings are correct.
*   **Firewall:** Check that your firewall is not blocking the connection to the server port.
```