---
phase: 21-package-restructuring
plan: 04
subsystem: build
tags: [cython, setuptools, build-system, glob, multi-extension]

# Dependency graph
requires:
  - phase: 21-01
    provides: Core module structure in src/quantum_language/
  - phase: 21-02
    provides: Type module .pyx files (qint, qbool, qfixed, qint_mod)
  - phase: 21-03
    provides: State subpackage modules
provides:
  - Auto-discovery build system for multiple Cython extensions
  - Modern pyproject.toml build configuration
  - Future-proof setup.py with legacy fallback
affects: [21-05-test-migration, package-deployment, ci-cd]

# Tech tracking
tech-stack:
  added: [glob, pathlib, find_packages]
  patterns: [auto-discovery, multi-extension-build, legacy-fallback]

key-files:
  created: []
  modified: [python-backend/setup.py, pyproject.toml]

key-decisions:
  - "Include '.' in include_dirs for cimport resolution across modules"
  - "Use glob.glob with recursive=True for .pyx auto-discovery"
  - "Legacy fallback for smooth transition during Wave 2 completion"
  - "Package data includes .pxd files for external cimport capability"

patterns-established:
  - "Path to module name conversion: src/quantum_language/qint.pyx -> quantum_language.qint"
  - "Each .pyx file becomes separate Extension with shared C sources"
  - "find_packages(where='src') for proper package discovery"

# Metrics
duration: 2min
completed: 2026-01-29
---

# Phase 21 Plan 04: Package Restructuring Summary

**Multi-extension build system with auto-discovery and legacy fallback for smooth Wave 2 transition**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T11:10:30Z
- **Completed:** 2026-01-29T11:12:20Z
- **Tasks:** 2 (autonomous execution, checkpoint not run)
- **Files modified:** 2

## Accomplishments
- Updated setup.py with glob-based auto-discovery of all .pyx files
- Added modern [build-system] section to pyproject.toml with Cython dependency
- Implemented legacy fallback to support both old and new directory structures
- Configured include_dirs with "." for cross-module cimport resolution

## Task Commits

Each task was committed atomically:

1. **Task 1: Update setup.py for multi-extension build** - `b0baca1` (feat)
2. **Task 2: Update pyproject.toml build configuration** - `fab8d9f` (feat)

_Note: Plan marked autonomous=true, so checkpoint Task 3 (human-verify) will be handled by orchestrator_

## Files Created/Modified
- `python-backend/setup.py` - Multi-extension build with auto-discovery via glob.glob("src/quantum_language/**/*.pyx")
- `pyproject.toml` - Added [build-system] section with setuptools, wheel, and cython>=3.0.11

## Decisions Made

**1. Include "." in include_dirs for cimport resolution**
- Rationale: Allows `cimport quantum_language._core` to find .pxd files in the package structure
- Critical for cross-module Cython imports

**2. Use glob.glob with recursive=True pattern**
- Rationale: Auto-discovers all .pyx files in src/quantum_language/ and subpackages
- Converts paths to proper module names (e.g., src/quantum_language/state/qpu.pyx -> quantum_language.state.qpu)

**3. Legacy fallback mechanism**
- Rationale: Wave 2 plans (21-01, 21-02, 21-03) are running in parallel
- Setup.py checks if src/quantum_language/ exists; falls back to quantum_language_preprocessed.pyx if not
- Enables smooth transition without breaking existing builds

**4. Package data includes .pxd files**
- Rationale: External projects can cimport from quantum_language modules
- Future-proofs for potential extensions or advanced usage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Note on dependency timing:** Plan has `depends_on: ["21-01", "21-02", "21-03"]` but those plans are running in Wave 2 parallel execution. The src/quantum_language/ directory doesn't exist yet. The legacy fallback mechanism handles this gracefully - current builds use quantum_language_preprocessed.pyx, and future builds will automatically switch to multi-extension mode once Wave 2 completes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Task 3 checkpoint: Human verification of build system (handled by orchestrator)
- Plan 21-05: Test migration to new package structure

**Blockers:**
- Build verification (Task 3 checkpoint) needs Wave 2 (21-01, 21-02, 21-03) to complete first
- Until src/quantum_language/ exists, setup.py uses legacy fallback

**Technical notes:**
- The build configuration is future-proof and will automatically discover modules once they exist
- No changes needed to setup.py after Wave 2 completes
- Multiple .so files will be generated: _core.*.so, qint.*.so, qbool.*.so, qint_mod.*.so, qfixed.*.so, etc.

---
*Phase: 21-package-restructuring*
*Completed: 2026-01-29*
