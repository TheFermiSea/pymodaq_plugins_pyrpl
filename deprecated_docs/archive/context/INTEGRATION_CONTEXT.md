 # Integration Context
 
 Canonical configuration for Factory Droids working on this repository. Use this to keep Knowledge Droid and Code Droid in sync through the repo filesystem via Bridge.
 
 ## Environment
 - Machine: Local Machine via Factory Bridge (not a remote workspace)
 - Working directory: `/Users/briansquires/serena_projects/pymodaq_plugins_pyrpl`
 - Tooling: Python + `uv`, `pytest`
 - Test entry points:
   - `uv run pytest -vv tests/test_command_multiplexing.py`
   - `uv run pytest -vv tests/test_scope_asg_concurrent.py`
 
 ## Droids and Roles
 - Knowledge Droid (model: Gemini 2.5 Pro)
   - Responsibilities: architecture analysis, upstream docs synthesis (PyRPL, PyMoDAQ), design decisions, reviews, documentation
   - Write outputs to repo files (do not leave conclusions only in chat):
     - `ARCHITECTURE_REVIEW.md`
     - `CODE_REVIEW.md`
     - `INTEGRATION_REPORT.md`
     - May update: `IMPLEMENTATION_FLEET_PLAN.md`
 - Code Droid
   - Responsibilities: implement code/tests, run commands locally, fix failing tests
   - Primary files touched:
     - `src/pymodaq_plugins_pyrpl/utils/shared_pyrpl_manager.py`
     - `src/pymodaq_plugins_pyrpl/utils/pyrpl_ipc_worker.py`
     - `tests/test_command_multiplexing.py`
     - `tests/test_scope_asg_concurrent.py`
   - Persist run outputs to repo (for cross-agent visibility):
     - Test logs: `logs/pytest_latest.txt`
     - Any diagnostics: `logs/*.log`
 
 ## Conventions
 - Always read/write within the working directory above.
 - Prefer small, atomic diffs; include docstrings where added.
 - Backward compatibility: worker responses may lack `id`; manager must not crash on such responses.
 - Artifacts directory: `logs/` (create if missing).
 
 ## Prompt Snippets
 - Knowledge Droid (Gemini 2.5 Pro):
   """
   Use the Integration Context:
   - Machine: Local via Bridge
   - Working dir: /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
   Tasks:
   - Review SHARED_WORKER_ARCHITECTURE.md (Command ID Multiplexing)
   - Include upstream constraints from PyRPL and PyMoDAQ
   Output: overwrite ARCHITECTURE_REVIEW.md with findings, constraints, design impacts, and test plan.
   """
 
 - Code Droid:
   """
   Use the Integration Context:
   - Machine: Local via Bridge
   - Working dir: /Users/briansquires/serena_projects/pymodaq_plugins_pyrpl
   Tasks:
   - Implement command‑ID multiplexing; update worker to echo id; harden listener
   - Unskip/implement tests and run pytest; save output to logs/pytest_latest.txt
   """
 
 ## Success Criteria
 - All tests pass locally.
 - Review documents updated and stored in repo.
 - Logs available in `logs/` for traceability.