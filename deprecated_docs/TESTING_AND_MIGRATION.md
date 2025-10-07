# Testing & Migration Protocol

## 5.1. Testing Protocol

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

## 5.2. User Migration Guide (Phase 1 to Phase 2)

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

## 5.3. Troubleshooting

*   **"Connection Refused" Error:** This is the most common issue. It means the `PyrplBridgeServer` is not running, or the IP/port in the plugin settings is incorrect. Check that the server script is running in its terminal and that the settings match.
*   **Firewall Issues:** If the server and client are on different computers, a firewall may be blocking the connection. Ensure that your system's firewall allows incoming TCP traffic on port `6341` on the server machine.
*   **Hardware Not Found by Server:** If the server terminal shows an error like "Could not connect to Red Pitaya," the issue is between the server and the hardware. Check that the Red Pitaya is powered on, connected to the network, and that the `hostname` in your `pyrpl` configuration is correct.

## 5.4. User Documentation Template (`README.md`)

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