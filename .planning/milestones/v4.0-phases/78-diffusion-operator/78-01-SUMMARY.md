---
phase: 78-diffusion-operator
plan: 01
subsystem: quantum-primitives
tags: [grover, diffusion, phase-gate, mcz, cython, compile-decorator]

# Dependency graph
requires:
  - phase: 77-oracle-infrastructure
    provides: "@ql.compile decorator, emit_x/emit_z/emit_mcz gate primitives, controlled context system"
provides:
  - "ql.diffusion() function with X-MCZ-X pattern (zero ancilla, O(n) gates)"
  - "emit_p() gate primitive with auto-control context handling"
  - "_PhaseProxy class enabling x.phase += theta syntax on quantum registers"
  - "phase property on qint (inherited by qbool) and qarray"
affects: [79-grover-iteration, 80-grover-search, diffusion-operator-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: ["_PhaseProxy pattern for augmented assignment on cdef class properties", "X-MCZ-X zero-ancilla diffusion", "width-based compile cache key for variable-arity functions"]

key-files:
  created:
    - "src/quantum_language/diffusion.py"
  modified:
    - "src/quantum_language/_gates.pxd"
    - "src/quantum_language/_gates.pyx"
    - "src/quantum_language/qint.pyx"
    - "src/quantum_language/qarray.pyx"
    - "src/quantum_language/__init__.py"

key-decisions:
  - "_PhaseProxy defined as plain Python class at module level in qint.pyx (before cdef class qint)"
  - "No-op setter on phase property absorbs Python += desugaring re-assignment"
  - "emit_p targets control qubit in controlled context (register-agnostic global phase)"
  - "qarray imports _PhaseProxy from qint (no circular import issues)"
  - "Unused qbool import removed from diffusion.py by ruff linter"

patterns-established:
  - "_PhaseProxy pattern: proxy object with __iadd__/__imul__ + no-op setter for augmented assignment on Cython cdef class properties"
  - "Width-based compile cache key: _total_width(*args) for variable-arity compiled quantum functions"

requirements-completed: [GROV-03, GROV-05]

# Metrics
duration: 17min
completed: 2026-02-20
---

# Phase 78 Plan 01: Diffusion Operator Summary

**X-MCZ-X diffusion operator with zero ancilla via emit_p/emit_mcz, plus x.phase += theta property using _PhaseProxy on qint/qbool/qarray**

## Performance

- **Duration:** 17 min
- **Started:** 2026-02-20T18:49:11Z
- **Completed:** 2026-02-20T19:06:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented `ql.diffusion()` function using X-MCZ-X pattern with zero ancilla allocation (GROV-03)
- Added `emit_p()` gate primitive to `_gates.pyx` with automatic controlled-context handling (CP when inside `with` block)
- Implemented `_PhaseProxy` class enabling `x.phase += theta` syntax on qint, qbool (inherited), and qarray (GROV-05 foundation)
- Exported `diffusion` at top-level `ql` namespace with `@ql.compile(key=_total_width)` caching
- Verified all patterns: single qubit (X-Z-X), multi-qubit (X-MCZ-X), multi-register, qarray flattening

## Task Commits

Each task was committed atomically:

1. **Task 1: Add emit_p gate primitive and implement phase property on qint/qarray** - `5efc4a9` (feat)
2. **Task 2: Implement ql.diffusion() module and export** - `b63852a` (feat)

## Files Created/Modified
- `src/quantum_language/_gates.pxd` - Added P/CP C gate declarations
- `src/quantum_language/_gates.pyx` - Added P/CP extern declarations and `emit_p()` function with auto-control
- `src/quantum_language/qint.pyx` - Added `_PhaseProxy` class and `phase` property with no-op setter
- `src/quantum_language/qarray.pyx` - Added `phase` property importing `_PhaseProxy` from qint
- `src/quantum_language/diffusion.py` - New module: `ql.diffusion()` with X-MCZ-X pattern, `_collect_qubits`, `_total_width`
- `src/quantum_language/__init__.py` - Added `diffusion` import and `__all__` entry

## Decisions Made
- `_PhaseProxy` defined as plain Python class in qint.pyx (before `cdef class qint`), not in separate module -- avoids circular imports and keeps it close to the property
- No-op `phase.setter` absorbs `x.phase = x.phase.__iadd__(theta)` re-assignment from Python's `+=` desugaring
- `emit_p` in controlled context targets `ctrl.qubits[63]` (the control qubit itself) since global phase is register-agnostic
- `qarray` imports `_PhaseProxy` from `qint` directly -- no circular import issues since qarray already imports from qint
- `diffusion.py` uses `@ql_compile(key=_total_width)` where `_total_width` sums qubit count across all args, enabling cache sharing for same total width regardless of register structure
- Single-qubit diffusion uses `emit_z` instead of `emit_mcz` (degenerate case)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Recreated venv with system Python 3.13**
- **Found during:** Task 1 verification (pip install -e .)
- **Issue:** Project venv had broken symlink to non-existent pyenv Python 3.11.9; pip install failed
- **Fix:** Installed python3.13-venv package, recreated venv with system Python 3.13, installed numpy/cython/qiskit dependencies
- **Files modified:** venv/ (gitignored)
- **Verification:** `pip install -e .` succeeded, Cython compiled cleanly
- **Committed in:** N/A (venv is gitignored)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Infrastructure fix only -- no code changes, no scope creep.

## Issues Encountered
- Pre-commit ruff linter auto-removed unused `qbool` import from diffusion.py and reformatted string quotes -- re-staged and committed cleanly on second attempt

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `ql.diffusion()` ready for Grover iteration integration in Phase 79
- `x.phase += theta` property ready for manual S_0 reflection via `with x == 0: x.phase += pi`
- `emit_p` primitive available for any future phase-gate needs
- All existing tests pass (53 fast tests verified, pre-existing failures in CLA/oracle simulation unrelated)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 78-diffusion-operator*
*Completed: 2026-02-20*
