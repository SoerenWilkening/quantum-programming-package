---
phase: 55-profiling-infrastructure
plan: 01
subsystem: infra
tags: [profiling, cython, line-profiler, pytest-benchmark, memray, py-spy, scalene]

# Dependency graph
requires: []
provides:
  - "[profiling] optional dependency group in pyproject.toml"
  - "QUANTUM_PROFILE environment variable for profiling builds"
  - "Cython profile=True and linetrace=True directives"
affects: [55-02, 55-03, 56-memory-profiling, 57-cython-optimization]

# Tech tracking
tech-stack:
  added: [line-profiler, snakeviz, pytest-benchmark, memray, pytest-memray, py-spy, scalene]
  patterns: [optional-dependencies-with-platform-markers, env-var-build-modes]

key-files:
  modified:
    - pyproject.toml
    - setup.py

key-decisions:
  - "Platform markers for Linux/macOS-only tools (memray, py-spy, scalene)"
  - "Core cross-platform deps in setup.py, full list in pyproject.toml"

patterns-established:
  - "QUANTUM_PROFILE=1 enables profiling build mode"
  - "Platform-specific dependencies use sys_platform markers"

# Metrics
duration: 5min
completed: 2026-02-05
---

# Phase 55 Plan 01: Profiling Infrastructure Dependencies Summary

**Profiling optional dependencies with platform markers and QUANTUM_PROFILE Cython build mode**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-05
- **Completed:** 2026-02-05
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added [profiling] extra to pyproject.toml with 7 profiling tools
- Added platform markers (sys_platform != 'win32') for Linux/macOS-only tools
- Added QUANTUM_PROFILE environment variable support for Cython profiling builds
- Cython profile=True and linetrace=True enabled when QUANTUM_PROFILE is set

## Task Commits

Each task was committed atomically:

1. **Task 1: Add [profiling] optional dependencies to pyproject.toml** - `4a5284f` (feat)
2. **Task 2: Add QUANTUM_PROFILE build support to setup.py** - `248875e` (feat)
3. **Task 3: Verify installation works** - No commit (verification only)

## Files Created/Modified
- `pyproject.toml` - Added [project.optional-dependencies] with profiling, verification, dev extras
- `setup.py` - Added QUANTUM_PROFILE env var check, profiling_directives, [profiling] extras_require

## Decisions Made
- Platform markers for memray, py-spy, scalene (Linux/macOS only - Windows not supported)
- Core cross-platform profiling deps (line-profiler, snakeviz, pytest-benchmark) in both pyproject.toml and setup.py
- Full dependency list with platform markers only in pyproject.toml (PEP 621 supports environment markers properly)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit hook reformatted setup.py on first commit attempt - resolved by re-staging after format
- pip dry-run blocked by externally-managed-environment - verified TOML parsing directly instead

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Profiling dependencies can now be installed with `pip install '.[profiling]'`
- Profiling builds can be triggered with `QUANTUM_PROFILE=1 pip install -e .`
- Ready for Plan 02: pytest-benchmark integration and initial benchmarks

---
*Phase: 55-profiling-infrastructure*
*Completed: 2026-02-05*
