# AGENT PLAYBOOK

## Repository Orientation
- Source lives under `src/pymodaq_plugins_pyrpl/` with actuator (`daq_move_plugins`), detector (`daq_viewer_plugins`), models, and utility modules (`utils/pyrpl_wrapper.py`, threading helpers, mock fixtures).
- Tests reside in `tests/`, including hardware suites such as `tests/test_real_hardware_rp_f08d6c.py` and simulation-focused coverage.
- Packaging metadata is in `pyproject.toml` and `plugin_info.toml`; avoid editing unless explicitly instructed.

## Working Guidelines
- Always inspect files with the provided Factory tools (`Read`, `LS`, `Grep`, etc.) using absolute paths; avoid shell shortcuts and parallel edits on the same file.
- Maintain concise changes, matching existing code style and limiting comments to those strictly necessary.
- Do not modify `README.rst` or other documentation unless the user explicitly requests it.
- Track multi-step work by updating the shared todo list (`TodoWrite`) as tasks progress.
- Before committing on behalf of the user, run `git status`, review diffs, and include the mandated co-author line.

## Testing Expectations
- Favor project-provided scripts; hardware validation uses pytest, e.g.:
  - `python -m pytest tests/test_real_hardware_rp_f08d6c.py -v -s`
- Execute all relevant linters/tests before handing work back unless instructed otherwise.

## Hardware Context
- Primary Red Pitaya target: `100.107.106.75` (output1→input1 loopback; input2 fed by external function generator).
- Real hardware tests rely on PyRPL connectivity; ensure the host is reachable and that the environment variable `PYRPL_TEST_HOST` is set if using an alternate address.
