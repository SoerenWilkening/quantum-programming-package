---
phase: 21-package-restructuring
plan: 01
subsystem: architecture
tags: [cython, package-structure, modularity, cimport]

# Dependency graph
requires:
  - phase: 20-uncomputation-modes
    provides: Uncomputation mode flag (_qubit_saving_mode) in global state
provides:
  - src/quantum_language/ package structure with modular .pxd/.pyx files
  - _core module with circuit class, global state, and accessor functions
  - .pxd declaration files for cross-module cimport (qint, qbool, qint_mod)
  - Accessor function pattern for global state sharing across modules
affects: [22-module-splitting, 23-array-implementation, 24-package-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Accessor functions for global state (bypasses cimport limitations)"
    - "Inheritance chain: qint->circuit, qbool->qint, qint_mod->qint"
    - "Package-level .pxd files for C-level cimport declarations"

key-files:
  created:
    - src/quantum_language/__init__.pxd
    - src/quantum_language/_core.pxd
    - src/quantum_language/_core.pyx
    - src/quantum_language/qint.pxd
    - src/quantum_language/qbool.pxd
    - src/quantum_language/qint_mod.pxd
  modified: []

key-decisions:
  - "Accessor functions for global state (Cython module-level cdef variables cannot be cimported)"
  - "array() function requires explicit dtype parameter in _core (patched later in __init__.py)"
  - "Empty __init__.pxd enables package-level cimport"

patterns-established:
  - "Pattern 1: .pxd files declare C-level interfaces for cimport"
  - "Pattern 2: accessor functions (_get_*, _set_*) provide cross-module state access"
  - "Pattern 3: cimport chains follow inheritance: qint->_core, qbool->qint, qint_mod->qint"

# Metrics
duration: 3min
completed: 2026-01-29
---

# Phase 21 Plan 01: Package Restructuring - Foundation Summary

**Established src/quantum_language/ package with _core module (circuit, global state, utilities) and .pxd files defining C-level interfaces for cross-module cimport**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-29T10:54:05Z
- **Completed:** 2026-01-29T10:57:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created src/quantum_language/ package structure with proper src layout
- Extracted shared _core module (585 lines) with circuit class, global state, and utilities
- Established .pxd declaration files for all type modules (qint, qbool, qint_mod)
- Implemented 21 accessor functions for cross-module global state access
- Defined cimport inheritance chains: qint->_core, qbool->qint, qint_mod->qint

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src layout and .pxd declaration files** - `cca913a` (feat)
2. **Task 2: Create _core.pyx with shared utilities and accessor functions** - `c285dc7` (feat)

## Files Created/Modified
- `src/quantum_language/__init__.pxd` - Empty file enabling package-level cimport
- `src/quantum_language/_core.pxd` - C-level declarations: extern blocks, circuit class, constants
- `src/quantum_language/_core.pyx` - Shared core: circuit class, global state, utilities, 21 accessor functions
- `src/quantum_language/qint.pxd` - qint C-level interface (inherits from circuit)
- `src/quantum_language/qbool.pxd` - qbool C-level interface (inherits from qint)
- `src/quantum_language/qint_mod.pxd` - qint_mod C-level interface (inherits from qint)

## Decisions Made

**1. Accessor functions for global state sharing**
- **Rationale:** Cython module-level `cdef` variables cannot be directly cimported across modules
- **Solution:** Python-level functions (_get_circuit, _set_int_counter, etc.) provide access
- **Impact:** Other modules will import these functions instead of using cimport for state

**2. array() dtype parameter required in _core module**
- **Rationale:** array() references qint/qbool which won't exist until full package imports
- **Solution:** Require explicit dtype parameter; __init__.py will wrap with default
- **Impact:** Direct _core.array() calls fail unless dtype provided (as intended)

**3. Empty __init__.pxd for package-level cimport**
- **Rationale:** Enables `from quantum_language cimport ...` syntax
- **Solution:** Single comment explaining purpose
- **Impact:** Package can be used as cimport target

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 21-02 (Module Splitting):**
- _core module provides shared foundation
- .pxd files define C-level interfaces
- Accessor functions enable state access
- Inheritance chains established

**Components to extract in 21-02:**
- qint implementation (from quantum_language.pyx)
- qbool implementation (from quantum_language.pyx)
- qint_mod implementation (from quantum_language.pyx)
- Each will cimport from _core and use accessor functions

**No blockers or concerns.**

---
*Phase: 21-package-restructuring*
*Completed: 2026-01-29*
