---
phase: 52-ancilla-tracking-inverse-reuse
plan: 01
subsystem: compile
tags: [ancilla, inverse, adjoint, qubit-reuse, compile-decorator]

# Dependency graph
requires:
  - phase: 48-51 (v2.0 Function Compilation)
    provides: CompiledFunc, _InverseCompiledFunc, CompiledBlock, _replay, _capture, inject_remapped_gates
provides:
  - _deallocate_qubits Python-callable function in _core.pyx
  - AncillaRecord data class for forward call tracking
  - _AncillaInverseProxy for f.inverse(x) uncomputation
  - Forward call registry (_forward_calls) on CompiledFunc
  - f.adjoint(x) standalone adjoint via _InverseCompiledFunc
affects: [52-02 (tests), 53 (nested compile), 54 (optimization)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Forward call registry pattern: per-CompiledFunc dict mapping qubit identity tuples to AncillaRecord"
    - "Property-based callable proxy: @property returning object with __call__ for f.inverse(x) syntax"
    - "Lazy import pattern: _deallocate_qubits imported inside __call__ to avoid circular import issues"

key-files:
  created: []
  modified:
    - src/quantum_language/_core.pyx
    - src/quantum_language/compile.py
    - tests/test_compile.py

key-decisions:
  - "Only track forward calls when ancilla qubits are allocated (in-place functions without ancillas skip tracking)"
  - "f.inverse is a @property returning _AncillaInverseProxy (not a method)"
  - "f.adjoint is a @property returning _InverseCompiledFunc (standalone, no tracking)"
  - "_replay accepts track_forward=True parameter to avoid adjoint path polluting forward call registry"
  - "Adjoint-triggered captures clean up side-effect forward call records"

patterns-established:
  - "AncillaRecord: lightweight __slots__ record for forward call ancilla tracking"
  - "_input_qubit_key: qubit identity matching via physical qubit index tuples"
  - "Non-contiguous deallocation: deallocate each ancilla qubit individually via _deallocate_qubits(idx, 1)"

# Metrics
duration: 9min
completed: 2026-02-04
---

# Phase 52 Plan 01: Ancilla Tracking & Inverse Reuse Summary

**Forward call registry with _AncillaInverseProxy for f.inverse(x) uncomputation and f.adjoint(x) standalone reverse, plus _deallocate_qubits Cython wrapper**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-04T21:42:13Z
- **Completed:** 2026-02-04T21:51:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- _deallocate_qubits exposed from _core.pyx wrapping allocator_free for Python-level qubit deallocation
- Forward call tracking in both capture path and replay path, with AncillaRecord storing ancilla qubits, virtual-to-real mapping, block, and return qint
- f.inverse(x) via _AncillaInverseProxy: replays adjoint gates on original ancilla qubits, deallocates them, invalidates return qint
- f.adjoint(x) via _InverseCompiledFunc (renamed from old .inverse()): standalone adjoint with fresh ancillas, no tracking
- Error handling for double-forward-without-inverse, inverse-without-forward, and double-inverse
- Circuit reset properly clears forward call registry

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _deallocate_qubits and data structures** - `de78a71` (feat)
2. **Task 2: Implement forward call tracking, f.inverse(x), f.adjoint(x)** - `2098d6f` (feat)

## Files Created/Modified
- `src/quantum_language/_core.pyx` - Added _deallocate_qubits() function wrapping allocator_free
- `src/quantum_language/compile.py` - Added AncillaRecord, _input_qubit_key, _AncillaInverseProxy, forward call tracking in _replay and _capture_inner, @property inverse/adjoint
- `tests/test_compile.py` - Updated existing tests from .inverse() method to .adjoint property

## Decisions Made
- Only track forward calls when ancilla qubits exist (functions that operate in-place without allocating ancillas don't need tracking and shouldn't block repeat calls)
- Changed inverse from a method returning _InverseCompiledFunc to a @property returning _AncillaInverseProxy, enabling f.inverse(x) call syntax
- Added track_forward parameter to _replay to prevent adjoint path from polluting forward call registry
- Adjoint-triggered capture (when cache is cold) cleans up side-effect forward call records immediately

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed double-forward detection for in-place functions**
- **Found during:** Task 2
- **Issue:** Functions without ancillas (e.g., `x += 1; return x`) triggered false double-forward errors when called twice with same qubits (e.g., in nested compilation)
- **Fix:** Only track forward calls when `ancilla_qubits` list is non-empty
- **Files modified:** src/quantum_language/compile.py
- **Verification:** test_nesting_inner_gates_in_outer_capture passes
- **Committed in:** 2098d6f

**2. [Rule 1 - Bug] Fixed adjoint-triggered capture polluting forward call registry**
- **Found during:** Task 2
- **Issue:** When adjoint (via _InverseCompiledFunc) triggers a cache-warming forward call, it created a side-effect forward call record that blocked subsequent forward calls
- **Fix:** After adjoint-triggered capture, pop the side-effect record from _forward_calls
- **Files modified:** src/quantum_language/compile.py
- **Verification:** Adjoint standalone test shows 0 forward calls after execution

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness with existing code patterns. No scope creep.

## Issues Encountered
- Cython build required `python setup.py build_ext --inplace` instead of `pip install -e .` (build_preprocessor module not found in isolated pip build environment)
- Linter removed unused `_deallocate_qubits` import from compile.py top-level; resolved by using lazy import inside _AncillaInverseProxy.__call__

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Core infrastructure complete: forward call tracking, inverse proxy, adjoint, deallocation
- Ready for Phase 52-02: comprehensive test suite for all INV-01 through INV-06 scenarios
- No blockers

---
*Phase: 52-ancilla-tracking-inverse-reuse*
*Completed: 2026-02-04*
