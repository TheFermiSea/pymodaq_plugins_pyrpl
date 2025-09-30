# Archive

This directory contains historical documentation, test scripts, and obsolete files kept for reference.

## Contents

### old_docs/

Superseded documentation files:

- `HARDWARE_TEST_REPORT.md` - Initial hardware test findings (superseded by docs/HARDWARE_TESTING.md)
- `HARDWARE_TEST_FINAL_STATUS.md` - Hardware validation status (consolidated into docs/HARDWARE_TESTING.md)
- `HARDWARE_VALIDATION.md` - Old validation doc (merged into docs/HARDWARE_TESTING.md)

**Note:** These files contain useful historical context but have been superseded by the consolidated documentation in the `docs/` directory.

### test_scripts/

Experimental and development test scripts:

- `test_hardware_connection.py` - Early hardware connection tests
- `test_pyrpl_simple.py` - Minimal PyRPL connection test
- `test_pyrpl_no_na.py` - Network analyzer bypass attempt
- `test_with_fixes.py` - Bug fix validation script
- `test_patch_debug.py` - Patch debugging utilities
- `test_pid_only.py` - PID-specific testing script
- `pymodaq_dashboard_fixed.py` - Experimental dashboard modifications
- `pymodaq_qasync_monkey_patch.py` - Qt/asyncio integration experiments
- `inspect_pyqtgraph.py` - PyQtGraph compatibility investigation

**Note:** These scripts were used during development to identify and fix bugs. The official test suite is in `tests/` directory. These are preserved for reference but not actively maintained.

## Why Archive?

Files are archived (rather than deleted) when they:
- Contain useful historical information
- Document problem-solving approaches
- May be useful for future troubleshooting
- Are superseded by better implementations
- Were experimental or one-time use

## Current Documentation

For up-to-date documentation, see:
- **Main docs:** `../docs/`
- **Test suite:** `../tests/`
- **README:** `../README.rst`

## Restoration

If you need to reference or restore archived files:

```bash
# View archived documentation
cat archive/old_docs/HARDWARE_TEST_REPORT.md

# Run archived test script
python archive/test_scripts/test_hardware_connection.py

# Restore a file (if needed)
cp archive/old_docs/some_file.md docs/
```

## Archive Policy

Files may be moved to archive when:
1. New consolidated documentation replaces multiple old docs
2. Experimental scripts are superseded by official implementations
3. Development artifacts are no longer needed for active development
4. Files provide historical context but aren't part of current workflow

Files are **never** archived if:
- They are actively used by CI/CD
- They are referenced by current documentation
- They contain unique information not preserved elsewhere
- They are part of the public API or user-facing features
