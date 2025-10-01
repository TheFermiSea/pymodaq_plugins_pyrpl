# Documentation Consolidation Plan

## Current State Analysis

**Root directory has 28 markdown files** - this is creating significant clutter.

We have existing archive directories:
- `archive/old_docs/` - Contains 3 old hardware test reports
- `development_history/` - Contains development scripts and reports

## Proposed Organization

### KEEP in Root (Essential User-Facing Documentation)

1. **README.md** (if exists - need to create/update)
   - Primary entry point for users
   - Links to all other docs
   
2. **QUICK_START.md** ✅ KEEP
   - Essential for new users
   - Shows how to use the plugins
   
3. **COMMAND_MULTIPLEXING_SUMMARY.md** ✅ KEEP
   - Current feature documentation
   - Production-ready reference
   
4. **PR_DESCRIPTION.md** ✅ KEEP (for now, delete after PR merged)
   - Active PR documentation
   - Should be deleted once PR is merged

### KEEP in docs/ (Technical Documentation)

Move these to `docs/` directory where they belong:

5. **ARCHITECTURE_REVIEW.md** → `docs/ARCHITECTURE_REVIEW.md`
   - Technical architecture documentation
   - Developer reference
   
6. **SHARED_WORKER_ARCHITECTURE.md** → `docs/SHARED_WORKER_ARCHITECTURE.md`
   - Technical deep-dive
   - Developer reference

7. **PYMODAQ_SETUP_GUIDE.md** → `docs/PYMODAQ_SETUP_GUIDE.md`
   - Setup instructions belong in docs/

### ARCHIVE - Historical Implementation Documentation

Move to `archive/implementation_docs/`:

8. **COMMAND_MULTIPLEXING_IMPLEMENTATION.md** → archive (superseded by SUMMARY)
9. **IMPLEMENTATION_COMPLETE.md** → archive
10. **IMPLEMENTATION_ROADMAP.md** → archive
11. **IMPLEMENTATION_FLEET_PLAN.md** → archive
12. **IPC_IMPLEMENTATION_SUMMARY.md** → archive
13. **COMPLETE_IPC_PLUGIN_SUITE.md** → archive
14. **PLUGIN_WORKING_CONFIRMATION.md** → archive

### ARCHIVE - Historical Test/Fix Reports

Move to `archive/test_reports/`:

15. **HARDWARE_TEST_RESULTS.md** → archive
16. **TEST_FIX_SUMMARY.md** → archive
17. **THREADING_FIX_SUMMARY.md** → archive
18. **SSH_CONNECTION_FIX.md** → archive
19. **HARDWARE_MODE_FIX.md** → archive
20. **CLEANUP_SUMMARY.md** → archive
21. **RECOVERY_SUMMARY.md** → archive

### ARCHIVE - Research/Planning Documents

Move to `archive/research/`:

22. **GEMINI_QUERY.md** → archive
23. **GEMINI_RESPONSE.md** → archive
24. **CODE_REVIEW.md** → archive
25. **PYRPL_REFACTORING_ROADMAP.md** → archive (outdated planning doc)

### ARCHIVE - Historical Context

Move to `archive/context/`:

26. **INTEGRATION_CONTEXT.md** → archive
27. **INTEGRATION_REPORT.md** → archive
28. **REPOSITORY_STRUCTURE.md** → archive

### ARCHIVE - Agent/Planning Documents

Move to `archive/agents/` or delete (redundant with .claude/agents/):

29. **AGENTS.md** → archive or delete

## Proposed Final Structure

```
/
├── README.md (create - main entry point)
├── QUICK_START.md (keep)
├── COMMAND_MULTIPLEXING_SUMMARY.md (keep - current feature)
├── PR_DESCRIPTION.md (temporary - delete after PR merge)
│
├── docs/
│   ├── README.md (index of all docs)
│   ├── ARCHITECTURE_REVIEW.md (moved from root)
│   ├── SHARED_WORKER_ARCHITECTURE.md (moved from root)
│   ├── PYMODAQ_SETUP_GUIDE.md (moved from root)
│   ├── DEVELOPER_GUIDE.md (existing)
│   ├── INSTALLATION.md (existing)
│   ├── IPC_ARCHITECTURE.md (existing)
│   ├── THREADING_ARCHITECTURE.md (existing)
│   ├── HARDWARE_TESTING.md (existing)
│   ├── MOCK_TUTORIAL.md (existing)
│   ├── TROUBLESHOOTING_SSH_CONNECTION.md (existing)
│   └── CONTROL_THEORY_FOUNDATIONS.md (existing)
│
├── archive/
│   ├── README.md (create - explains archive structure)
│   ├── implementation_docs/
│   │   ├── COMMAND_MULTIPLEXING_IMPLEMENTATION.md
│   │   ├── IMPLEMENTATION_COMPLETE.md
│   │   ├── IMPLEMENTATION_ROADMAP.md
│   │   ├── IMPLEMENTATION_FLEET_PLAN.md
│   │   ├── IPC_IMPLEMENTATION_SUMMARY.md
│   │   ├── COMPLETE_IPC_PLUGIN_SUITE.md
│   │   └── PLUGIN_WORKING_CONFIRMATION.md
│   │
│   ├── test_reports/
│   │   ├── HARDWARE_TEST_RESULTS.md
│   │   ├── HARDWARE_TEST_FINAL_STATUS.md (existing)
│   │   ├── HARDWARE_TEST_REPORT.md (existing)
│   │   ├── HARDWARE_VALIDATION.md (existing)
│   │   ├── TEST_FIX_SUMMARY.md
│   │   ├── THREADING_FIX_SUMMARY.md
│   │   ├── SSH_CONNECTION_FIX.md
│   │   ├── HARDWARE_MODE_FIX.md
│   │   ├── CLEANUP_SUMMARY.md
│   │   └── RECOVERY_SUMMARY.md
│   │
│   ├── research/
│   │   ├── GEMINI_QUERY.md
│   │   ├── GEMINI_RESPONSE.md
│   │   ├── CODE_REVIEW.md
│   │   └── PYRPL_REFACTORING_ROADMAP.md
│   │
│   ├── context/
│   │   ├── INTEGRATION_CONTEXT.md
│   │   ├── INTEGRATION_REPORT.md
│   │   └── REPOSITORY_STRUCTURE.md
│   │
│   └── old_docs/ (existing)
│       └── ... (keep as is)
│
└── development_history/
    └── ... (keep as is)
```

## Benefits

1. **Root directory clean** - Only 3-4 essential files
2. **Logical organization** - Easy to find what you need
3. **History preserved** - Nothing deleted, all in archive
4. **Better discoverability** - Clear separation of current vs historical docs
5. **Professional appearance** - Repository looks well-maintained

## Execution Plan

1. Create `archive/implementation_docs/`
2. Create `archive/test_reports/`
3. Create `archive/research/`
4. Create `archive/context/`
5. Move files according to plan above
6. Update `archive/README.md` with directory structure
7. Create/update root `README.md` with links to key docs
8. Update `docs/README.md` as index
9. Commit with clear message

## Notes

- `.claude/agents/` and `.serena/memories/` left untouched (tool-specific)
- `pyrpl/` subdirectory left untouched (submodule)
- All historical context preserved for future reference
- Can easily retrieve archived docs if needed
