---
phase: 77-oracle-infrastructure
plan: 01
subsystem: api
tags: [grover, oracle, decorator, compile, cython, phase-kickback, caching]

# Dependency graph
requires:
  - phase: 76-gate-primitive-exposure
    provides: emit_h, emit_z, emit_ry, emit_mcz gate primitives in _gates.pyx
provides:
  - GroverOracle class with decorator, validation, bit-flip wrapping, and caching
  - grover_oracle decorator function (ql.grover_oracle)
  - emit_x gate primitive in _gates.pyx
affects: [79-grover-search-api, 80-oracle-auto-synthesis]

# Tech tracking
tech-stack:
  added: []
  patterns: [oracle-decorator-layering, compute-phase-uncompute-validation, phase-kickback-wrapping]

key-files:
  created:
    - src/quantum_language/oracle.py
  modified:
    - src/quantum_language/_gates.pyx
    - src/quantum_language/__init__.py

key-decisions:
  - "Validation at circuit generation time (first call), not decoration time"
  - "validate=False bypasses ALL checks (ancilla delta + compute-phase-uncompute)"
  - "Bit-flip detection checks ancilla interaction count > 4 (wrapping gates)"
  - "Phase gate detection limited to Z-type gates targeting param qubits only"

patterns-established:
  - "Oracle decorator pattern: grover_oracle wraps CompiledFunc, adds validation/wrapping layer"
  - "Controlled context save/restore for unconditional gate emission inside controlled blocks"

requirements-completed: [ORCL-01, ORCL-02, ORCL-03, ORCL-04, ORCL-05]

# Metrics
duration: 34min
completed: 2026-02-20
---

# Phase 77 Plan 01: Oracle Infrastructure Summary

**@ql.grover_oracle decorator with compute-phase-uncompute validation, ancilla delta enforcement, X-H-oracle-H-X phase kickback auto-wrapping, and source-hash + arithmetic-mode-aware caching**

## Performance

- **Duration:** 34 min
- **Started:** 2026-02-20T15:40:34Z
- **Completed:** 2026-02-20T16:14:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created oracle.py module (462 lines) with GroverOracle class implementing all 5 ORCL requirements
- Added emit_x gate primitive to _gates.pyx following the established emit_h pattern
- Exported grover_oracle as ql.grover_oracle with full decorator API (bare, empty parens, kwargs)
- Package builds and existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add emit_x to _gates.pyx and create oracle.py module** - `3cde879` (feat)
2. **Task 2: Export grover_oracle from __init__.py and verify build** - `bf360c1` (feat)

## Files Created/Modified
- `src/quantum_language/oracle.py` - GroverOracle class with decorator, validation, bit-flip wrapping, and caching (462 lines)
- `src/quantum_language/_gates.pyx` - Added emit_x function and x()/cx() C declarations
- `src/quantum_language/__init__.py` - Added grover_oracle import and __all__ export

## Decisions Made
- Validation happens at circuit generation time (first call), not decoration time -- per CONTEXT.md Claude's discretion
- `validate=False` bypasses ALL checks (both ordering and ancilla delta) -- per research recommendation
- Phase gate detection limited to Z-type gates (type == _Z) targeting param qubits (virtual indices 0..width-1) only -- ancilla Z gates are part of compute/uncompute, not phase marking
- Bit-flip oracle interaction detection counts gates targeting the ancilla qubit; if count <= 4 (the wrapping X-H-H-X gates), oracle didn't interact with ancilla
- Controlled context is saved/restored around kickback wrapping gates so X and H on ancilla are always unconditional

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Build required `--break-system-packages` flag due to externally-managed Python environment (Linux container with system Python 3.13, project venv from macOS pyenv not usable)
- Pre-existing test failures in comparison operators (qubit index 63 out of range) and qarray segfault -- not caused by oracle changes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- oracle.py module ready for Phase 77-02 (oracle tests)
- GroverOracle class ready for Phase 79 (Grover search API) integration
- emit_x gate primitive available for Phase 78 (diffusion operator)

## Self-Check: PASSED

- FOUND: src/quantum_language/oracle.py
- FOUND: src/quantum_language/_gates.pyx
- FOUND: src/quantum_language/__init__.py
- FOUND: 3cde879 (Task 1 commit)
- FOUND: bf360c1 (Task 2 commit)

---
*Phase: 77-oracle-infrastructure*
*Completed: 2026-02-20*
