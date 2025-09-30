# Factory Droids Plan: Command ID Multiplexing

This document maps the original “fleet” roles onto Factory Droids so you can drive the whole effort with AI, end‑to‑end, on your local machine.

Quick start:
- Start a session with Knowledge Droid (use model: Gemini 2.5 Pro): https://app.factory.ai/sessions/new?droidId=knowledge-droid
- Start a session with Code Droid: https://app.factory.ai/sessions/new?droidId=code-droid

Ensure Bridge is connected to your local machine and set the working directory to:
`/Users/briansquires/serena_projects/pymodaq_plugins_pyrpl`

---

## Roles → Droids

```
┌─────────────────────────────────────────────────────────────────┐
│                         Integration Lead                         │
│                   (You + Knowledge Droid + Code Droid)          │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────▼────────┐
    │ Knowledge Droid │  ← Gate 1: Architecture & test plan approval
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │   Code Droid    │  ← Gate 2: Implementation + tests + fixes
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Knowledge Droid │  ← Gate 3: Code review + integration checklist
    └──────────────────┘
```

---

## Phase 1: Architecture Validation (Knowledge Droid)

Mission: Validate architecture before coding.

Prompt to paste into Knowledge Droid:
```
Context: Repository at /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
Task: Review SHARED_WORKER_ARCHITECTURE.md (lines 188–287) for the Command ID Multiplexing proposal.
Validate:
- UUID per command
- threading.Event per command
- _pending_responses dict guarded by a lock
- response listener thread demultiplexing
Identify risks: race conditions, deadlocks, memory leaks (event cleanup), worker crash/timeout/duplicate IDs.
Deliver: ARCHITECTURE_REVIEW.md with findings, edge cases, and test scenarios.
Gate: If issues found, propose concrete fixes.
```

Success: No critical issues; edge cases + tests defined; review document produced.

---

## Phase 2: Implementation (Code Droid)

Prereq: Knowledge Droid approved Phase 1.

### A. Core: SharedPyRPLManager

File: `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`

Implement:
- Response tracking map: `{cmd_id: (Event, result_container)}` with lock
- Background response listener thread
- `send_command(command, params, timeout)` that attaches a UUID, waits on its own Event, and cleans up in finally
- Graceful shutdown of listener + worker

Prompt to paste into Code Droid:
```
Open src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py.
Add command‑ID multiplexing with uuid4, threading.Event per command, a protected _pending_responses dict, a listener thread that demuxes responses by id, and cleanup in finally. Include docstrings.
```

### B. Worker: pyrpl_ipc_worker

File: `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`

Implement:
- Echo incoming `id` on every response path: init, success, error, shutdown, timeout

Prompt:
```
Open src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py.
In the command loop, extract cmd_id from the request and include it in every response (including exceptions). Keep backward compatibility when id is missing.
```

---

## Phase 2C: Tests (Code Droid)

Add tests under `tests/`.

1) `tests/test_command_multiplexing.py`
- single command returns `pong` with status ok
- 10 concurrent `ping` commands complete without errors
- timeout path surfaces TimeoutError and cleans `_pending_responses`
- resource cleanup after many commands (no leaks)
- backward compatibility when id is absent

2) `tests/test_scope_asg_concurrent.py`
- scope acquires continuously (≈50 ms)
- ASG updates frequency (≈100 ms)
- run ~5 s; verify neither blocks the other

Prompt:
```
Create tests as above. Make them deterministic and fast. Use any available mock/sim mode if hardware is not attached.
```

---

## Phase 3: Review & Quality Gates (Knowledge Droid)

Checklist:
- Manager: lock coverage, finally cleanup, listener lifecycle, timeouts, worker‑death handling, malformed response safety
- Worker: id echoed on all paths; compatibility with/without id
- Tests: concurrency, edge cases, determinism, performance assertions

Prompt:
```
Review the diffs for the two files and the tests. Produce CODE_REVIEW.md with pass/fail per checklist and any fixes required. Block merge if critical issues found.
```

---

## Phase 4: Integration & Testing (Code Droid → run locally)

Commands:
```
cd /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
uv run pytest tests/test_command_multiplexing.py -v
uv run pytest tests/test_scope_asg_concurrent.py -v
```

Hardware checklist:
- Load `scope_test_IPC` preset; verify single scope
- Logs show command IDs

Performance:
- latency < 100 ms
- 100+ concurrent commands OK
- memory stable

Deliverable: `INTEGRATION_REPORT.md` with results and regressions (if any).

---

## Success Criteria

- All tests pass; review approved
- No regressions on hardware
- Performance targets met
- Docs produced: ARCHITECTURE_REVIEW.md, CODE_REVIEW.md, INTEGRATION_REPORT.md

---

## Using Factory Droids Effectively

- Keep Knowledge Droid focused on analysis, architecture, review, and documentation. Feed it file paths and exact questions.
- Keep Code Droid focused on edits, tests, and running commands in your bridged local repo. Provide precise file paths and acceptance criteria.
- Use short, iterative prompts; paste errors back into the same session for quick fixes.

Quick links:
- Knowledge Droid: https://app.factory.ai/sessions/new?droidId=knowledge-droid
- Code Droid: https://app.factory.ai/sessions/new?droidId=code-droid