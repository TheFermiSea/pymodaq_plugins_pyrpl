# PyRPL Developer Guide

This guide consolidates the developer notes that were previously scattered
across multiple markdown files. It provides a single reference for building,
testing, and extending the PyMoDAQ–PyRPL integration.

## Project Overview

`pymodaq_plugins_pyrpl` delivers full Red Pitaya STEMlab support for PyMoDAQ.
The plugin suite covers hardware PID control, arbitrary waveform generation,
oscilloscope acquisition, lock-in detection, and voltage monitoring. The code
base is production ready for mock-mode development and validated for real
hardware operation.

## Repository Layout

- `src/pymodaq_plugins_pyrpl/`
  - `daq_move_plugins/` – actuator plugins (`DAQ_Move_PyRPL_PID`, `DAQ_Move_PyRPL_ASG`)
  - `daq_viewer_plugins/plugins_0D/` – voltage and IQ detectors
  - `daq_viewer_plugins/plugins_1D/` – scope acquisition
  - `extensions/` – dashboard integrations and manager widgets
  - `models/` – PID model (`PIDModelPyRPL`)
  - `utils/` – shared infrastructure (configuration, threading, wrapper, mocks)
- `docs/` – user and developer documentation (installation, mock tutorial, control theory, this guide)
- `tests/` – automated pytest suite (mock, integration, and hardware markers)

## Build & Test Commands

```bash
# Install in editable mode
pip install -e .[dev]

# Run full test suite (mock and optional hardware markers)
python -m pytest tests/

# Focused subsets
python -m pytest tests/test_pyrpl_functionality.py -k "test_pid"
python -m pytest tests/test_pyrpl_functionality.py -k "test_asg"
python -m pytest tests/test_pyrpl_functionality.py -k "test_scope"
python -m pytest tests/test_pyrpl_functionality.py -k "test_iq"

# Marker based
python -m pytest -m mock
python -m pytest -m hardware  # requires configured Red Pitaya

# Linting (ruff or flake8 depending on local preference)
ruff check src tests
```

## Coding Guidelines

- Follow PEP 8 with 4-space indentation and type hints on public APIs.
- Plugin classes follow PyMoDAQ naming: `DAQ_<dim>Viewer_PyRPL_*` and
  `DAQ_Move_PyRPL_*`.
- Emit `ThreadCommand('Update_Status', [...])` around hardware calls to keep the
  GUI responsive.
- Run `ruff check --select I` (or equivalent) to maintain deterministic import
  ordering before committing.

## Event Loop & Threading Architecture

PyRPL historically relied on Quamash to merge Qt and asyncio event loops. The
current integration adopts qasync monkey patching so PyMoDAQ owns the single
event loop and PyRPL attaches through a shim. Key points:

- `pymodaq_qasync_monkey_patch.py` installs a qasync-backed `mkQApp` and a
  Quamash compatibility shim. Import this **before** importing PyMoDAQ when
  launching outside the provided dashboard script.
- `pymodaq_dashboard_fixed.py` applies the patches automatically and should be
  used as the default dashboard entry point.
- Threaded hardware operations are executed via `ThreadedHardwareManager`,
  which now delegates to Qt-managed `QThread` workers to avoid competing with
  PyMoDAQ’s QThread infrastructure. Continuous acquisition is handled by
  `_AcquisitionWorker` (Qt timer driven) inside `utils/threading.py`.
- If a plugin needs to interact with the shared mock layer, obtain an adapter
  with `create_pyrpl_connection(..., mock_mode=True)` so the reference counting
  and signal dispatch remain consistent.

## Mock Demonstration Environment

The enhanced mock environment reproduces realistic plant dynamics for training
and development:

- Enable mock mode in plugin parameters (`Mock Mode: True`).
- Apply presets from `pymodaq_plugins_pyrpl.utils.demo_presets` for predefined
  scenarios such as `stable_basic`, `oscillatory_challenge`, or
  `noisy_derivative`.
- Viewer plugins (0D voltage, IQ lock-in, 1D scope) share the same simulation
  state so PID moves, scope captures, and IQ measurements remain synchronized.
- `EnhancedMockPyRPLConnection` exposes performance metrics through
  `get_performance_metrics()` enabling classroom-style demonstrations.

## Remote Access Notes (Tailscale)

Red Pitaya boards can be exposed securely through Tailscale when direct LAN
access is unavailable:

1. Install Tailscale on the device (Ubuntu 22.04 base OS).
2. Edit `tailscaled.service` and append `--tun=userspace-networking` to the
   `ExecStart` line because the vendor kernel lacks the `tun` module.
3. Reload systemd and restart Tailscale:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart tailscaled
   tailscale up --auth-key=YOUR_AUTH_KEY --ssh
   ```
4. Install `iptables` if routing errors appear in the logs.

## Recent Enhancements

- Custom exception hierarchy and frequency validation helpers were added to the
  ASG actuator plugin for clearer diagnostics.
- Scope mock mode gained selectable waveforms (`damped_sine`, `square`,
  `noise`) to support richer demos.
- The dashboard extension now emits live updates via `PyRPLManager.status_updated`
  signals and offers a placeholder **Configure** action for connected hosts.
- Centralized mock management in `pyrpl_wrapper.py` exposes
  `PyRPLMockConnectionAdapter`, shared instance helpers, and mock-aware test
  fixtures.
- Qt threading helpers were refactored to rely on QThreads and timers,
  preventing Python threads from competing with PyMoDAQ’s event loop.

---

Use this document as the canonical reference for development workflows. For
hardware validation details, consult `docs/HARDWARE_VALIDATION.md`.
