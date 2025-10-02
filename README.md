# PyMoDAQ Plugin for PyRPL

This package provides PyMoDAQ plugins for controlling and acquiring data from hardware running the `stemlab` library (a headless fork of `pyrpl`), such as the Red Pitaya.

## Architecture

This integration uses a client-server architecture for stability. A standalone "Bridge Server" runs on the computer connected to the Red Pitaya hardware, and the PyMoDAQ plugin acts as a network client. This ensures that any hardware issues do not crash the main PyMoDAQ application.

## Installation

```bash
pip install .
```

## Quick Start Guide (Production Usage)

1.  **Start the Bridge Server:** Open a terminal and run the following command. This server must remain running while you use the plugin.
    ```bash
    pyrpl_bridge_server
    ```

2.  **Launch PyMoDAQ:** Start the PyMoDAQ dashboard application.

3.  **Load the Plugin:** In the DAQ Manager, add a new `DAQ_Viewer` and select the **"PyRPL Bridge Client"** plugin from the list.

4.  **Configure:** In the plugin settings, enter the IP address and port of the server (default is `localhost:6341`) and the hostname of your Red Pitaya device.

5.  **Initialize:** Click the "Init" button to connect. You are now ready to acquire data.

## Development & Prototyping (Phase 1 Plugin)

For rapid development, an in-process plugin is also provided. This plugin runs `stemlab` in the same process as PyMoDAQ and is ideal for quick tests, but it is **not recommended for production** as a crash in the hardware library will crash the entire application.

To use it, load the **"PyRPL In-Process"** plugin instead.

## Plugin Settings

| Setting | Description | Default Value |
| :--- | :--- | :--- |
| **Server IP** | (Phase 2 Only) The IP address of the machine running the Bridge Server. | `localhost` |
| **Server Port** | (Phase 2 Only) The port the Bridge Server is listening on. | `6341` |
| **Hostname** | The hostname or IP of the Red Pitaya device. | `192.168.1.100` |

## Troubleshooting

*   **Connection Refused:** This error means the `pyrpl_bridge_server` is not running, or the IP/port in the plugin settings is incorrect. Check that the server script is running in its terminal and that the settings match.
*   **Firewall Issues:** If the server and client are on different computers, a firewall may be blocking the connection. Ensure that your system's firewall allows incoming TCP traffic on the specified port on the server machine.
*   **Hardware Not Found by Server:** If the server terminal shows an error like "Could not connect to Red Pitaya," the issue is between the server and the hardware. Check that the Red Pitaya is powered on, connected to the network, and that the `hostname` in your `stemlab` configuration is correct.

## Testing

The unit and integration tests have been successfully run. The end-to-end hardware tests were skipped due to a connection issue with the hardware at `100.107.106.75`. Please refer to the `TESTING.md` file for instructions on how to run the tests.
