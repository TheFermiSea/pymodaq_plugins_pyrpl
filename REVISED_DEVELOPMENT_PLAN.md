# REVISED PyRPL-PyMoDAQ Integration Strategy (using StemLab)

## Section 1: Project Overview & Task Matrix

### 1.1. Executive Summary

This document outlines the revised, official two-phase strategy for integrating the `StemLab` library (a headless fork of `pyrpl`) with PyMoDAQ. The primary objective is to deliver a stable, maintainable, and user-friendly plugin for controlling Red Pitaya-based hardware from within the PyMoDAQ ecosystem. The decision to use `StemLab` is a direct result of insurmountable dependency conflicts with the original `pyrpl` library.

*   **Phase 1** focuses on rapid development via a direct, **in-process plugin** using `StemLab`. This provides the fastest path to a functional prototype.
*   **Phase 2** transitions to a robust, **bridge server architecture** for production use, ensuring maximum stability and process isolation.

The "Contract First" principle remains the strategic foundation of this plan.

### 1.2. Project & Version Control

*   **Project Tracking:** All tasks will continue to be tracked on the **Zen MPC Server** under the project "PyRPL-PyMoDAQ Integration."
*   **Version Control:** All code will be managed on the **Octocode MCP Server** using the established Git branching strategy (`main`, `develop`, `feature/*`).

### 1.3. Task Matrix

| Task ID | Task Description | Dependencies | Definition of Done |
| :--- | :--- | :--- | :--- |
| T01 | Update `pyproject.toml` with `StemLab` | None | The `pyrpl` dependency is replaced with a Git dependency for `ograsdijk/StemLab`. |
| T02 | Refactor `PyrplWorker` to use `StemLab` | T01 | The worker class in `hardware/pyrpl_worker.py` is updated to import and instantiate `StemLab` instead of `Pyrpl`. |
| T03 | Run Unit & Integration Test Suite | T02 | All tests in `tests/unit` and `tests/integration` pass successfully using the `StemLab`-based worker. |
| T04 | Run End-to-End Hardware Tests | T03 | All tests in `tests/e2e`, marked with `@pytest.mark.hardware`, pass against the real hardware at `100.107.106.75`. |
| T05 | Finalize Documentation | T04 | The `README.md` and `TESTING.md` files are updated to reflect the use of `StemLab` and the successful test runs. |
| T06 | Prepare for Release | T05 | The `develop` branch is merged into `main`, and a release candidate is tagged. |

---

## Section 2: The PyRPL Device Contract

*(This section remains unchanged. The `PyrplInstrumentContract` defined in `src/pymodaq_plugins_pyrpl/hardware/pyrpl_contract.py` is compatible with the `StemLab` API and will continue to be the guiding interface for the project.)*

---

## Section 3: Phase 1 Implementation Plan (In-Process)

### 3.1. Implementation Strategy

The strategy remains the same, but the implementation will now use the `stemlab` library. The `PyrplWorker` will instantiate `StemLab`, and because `StemLab` is headless, we anticipate none of the previous GUI-related errors.

### 3.2. Code - `PyrplWorker` (Refactored for `StemLab`)

**Target File:** `src/pymodaq_plugins_pyrpl/hardware/pyrpl_worker.py`

**Instructions:** The only required change is to the import and instantiation logic.

```python
# src/pymodaq_plugins_pyrpl/hardware/pyrpl_worker.py
from qtpy.QtCore import QObject, Signal, Slot
from typing import Dict, Tuple, Optional
import numpy as np
# MODIFICATION: Import StemLab instead of Pyrpl
from stemlab import StemLab

from .pyrpl_contract import PyrplInstrumentContract

class PyrplWorker(QObject, PyrplInstrumentContract):
    # ... (signals remain the same) ...

    def __init__(self):
        super().__init__()
        # MODIFICATION: The type hint is now StemLab
        self.pyrpl: Optional[StemLab] = None

    def connect(self, config: Dict) -> bool:
        try:
            # MODIFICATION: Instantiate StemLab
            self.pyrpl = StemLab(**config)
            self.status_update.emit(f"Successfully connected to {self.get_idn()}")
            return True
        except Exception as e:
            self.status_update.emit(f"Connection to StemLab failed: {e}")
            return False

    # ... (all other methods remain identical, as the API is the same) ...
```

---

## Section 4: Phase 2 Implementation Plan (Bridge Server)

*(This section remains conceptually unchanged. The `PyrplBridgeServer` will still instantiate the `PyrplWorker`. Since the worker is now based on `StemLab`, the server will automatically use the headless library, resolving all previous instability issues.)*

---

## Section 5: Testing & Migration Protocol

### 5.1. Testing Protocol

The existing test suite (`unit`, `integration`, `e2e`) is still valid. The goal is now to run this suite against the `StemLab`-based implementation and achieve a passing result.

*   **Unit & Integration Tests:** These should now pass without any modifications to third-party libraries, as the root cause of the errors (GUI dependencies) has been eliminated.
*   **End-to-End Tests:** These will be the ultimate validation. We will execute the `test_hardware.py` suite against the live Red Pitaya to confirm that `StemLab` provides the same level of control and data integrity as the original `pyrpl` library.

### 5.2. User Migration Guide

*(This section remains unchanged for now. The end-user experience is identical, as the architectural change is internal. The user will still run the `pyrpl_bridge_server` command and use the `BridgeClient` plugin.)*
