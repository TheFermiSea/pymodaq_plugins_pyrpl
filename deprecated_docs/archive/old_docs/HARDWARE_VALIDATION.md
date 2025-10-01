# Hardware Validation Overview

This document consolidates the historical hardware validation notes. It
captures the compatibility fixes that allow PyRPL to run inside PyMoDAQ and the
current status of Red Pitaya testing.

## Test Environment

- **Date of validation:** September 2025
- **Red Pitaya host:** `rp-f08d6c.local`
- **PyRPL version:** 0.9.3.6
- **Python:** 3.12.x
- **Qt:** PySide6 6.9.0
- **OS:** Linux (Ubuntu-based images on Red Pitaya)

## Compatibility Fixes

To run PyRPL alongside modern Qt/NumPy stacks the following shims are applied
inside `utils/pyrpl_wrapper.py`:

- Map deprecated `collections.Mapping` symbols to `collections.abc` (Python
  3.10+).
- Alias `np.complex` to the built‑in `complex` (NumPy 1.20+).
- Restore `pyqtgraph.GraphicsWindow` by pointing it to
  `GraphicsLayoutWidget` (pyqtgraph 0.13+).
- Patch `QTimer.setInterval` to coerce float values to integers before reaching
  Qt (fixes `TypeError: argument 1 has unexpected type 'float'`).

For deterministic operation, the Red Pitaya dashboard is launched via the
qasync-enabled `pymodaq_dashboard_fixed.py`. This ensures PyMoDAQ owns the Qt
event loop while PyRPL joins through the monkey patch shim.

## Validation Results

- All five plugin families (PID move, ASG move, 0D voltage viewer, 0D IQ
  viewer, 1D scope) load successfully under PyMoDAQ with the monkey patch in
  place.
- Mock-mode coverage is comprehensive: 46+ automated tests exercise PID gains,
  signal generation, IQ measurements, and scope acquisitions without hardware.
- Real hardware validation confirms that network connectivity, module access
  (`pid0/1/2`, `asg0/1`, `scope`), and basic voltage or ASG operations succeed
  once the Red Pitaya OS is reachable. Authentication issues that surface in
  some test logs are due to device configuration rather than library defects.

## Mock vs Hardware Modes

- **Mock mode** provides first-order-plus-dead-time simulations, noise models,
  and coordinated state sharing across all plugins. It is suitable for training
  exercises and automated CI.
- **Hardware mode** now runs inside the patched event loop. Use environment
  variables such as `PYRPL_TEST_HOST` when executing pytest with hardware
  markers (`pytest -m hardware`). Ensure the device’s SSH/SCPI services are
  configured and reachable.

## Deployment Notes

- Maintain the monkey patch launcher for production dashboards to guarantee
  unified Qt/asyncio control.
- If accessing devices over the internet, configure Tailscale in
  `--tun=userspace-networking` mode (see the developer guide for steps).
- Keep compatibility patches in sync with upstream PyRPL updates. When the
  library provides native Qt6 support these shims can be revisited.

---

This summary replaces the former hardware validation markdown files
(`COMPLETE_HARDWARE_VALIDATION.md`, `HARDWARE_TEST_RESULTS.md`,
`FINAL_HARDWARE_TEST_RESULTS.md`, `HARDWARE_VALIDATION_SUMMARY.md`, and
`PYRPL_FIX_SUMMARY.md`).
