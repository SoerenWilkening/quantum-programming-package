---
phase: 78-diffusion-operator
plan: 03
subsystem: quantum-gates
tags: [phase-gate, emit_p_raw, phase-kickback, S_0-reflection, grover, diffusion]

# Dependency graph
requires:
  - phase: 78-diffusion-operator
    provides: "_PhaseProxy class, emit_p gate primitive, diffusion operator"
provides:
  - "emit_p_raw() function for P gate emission without auto-control context"
  - "Fixed _PhaseProxy.__iadd__ using emit_p_raw to avoid double-control bug"
  - "Layer floor helpers for circuit optimizer interaction"
  - "Direct statevector tests for manual S_0 path"
affects: [79-grover-iteration, 80-grover-search]

# Tech tracking
tech-stack:
  added: []
  patterns: ["emit_p_raw for manual phase kickback (bypass auto-control context)"]

key-files:
  created: []
  modified:
    - src/quantum_language/_gates.pyx
    - src/quantum_language/qint.pyx
    - tests/python/test_diffusion.py

key-decisions:
  - "emit_p_raw bypasses _get_controlled() to prevent double-control (P not CP on control qubit)"
  - "Layer floor manipulation in __iadd__ keeps P gate outside comparison layer range during compute-P-uncompute"
  - "Phase tests updated to expect P gate (not CP) after emit_p_raw fix -- P on control qubit is quantum-equivalent via phase kickback"

patterns-established:
  - "emit_p_raw for direct phase application in controlled context: used when caller already handles control logic"
  - "Layer floor save/restore pattern: _get_layer_floor() -> _set_layer_floor_to_used() -> emit -> _restore_layer_floor()"

requirements-completed: [GROV-05]

# Metrics
duration: 10min
completed: 2026-02-20
---

# Phase 78 Plan 03: Gap Closure -- Manual S_0 Path Fix Summary

**Fixed emit_p double-control bug with emit_p_raw + layer floor protection, enabling `with x == 0: x.phase += pi` to produce observable S_0 reflection verified by Qiskit statevector**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-20T23:25:12Z
- **Completed:** 2026-02-20T23:35:51Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed the double-control bug where `_PhaseProxy.__iadd__` called `emit_p` inside a controlled context, producing a no-op self-controlled `cp(q[n], q[n])` gate
- Added `emit_p_raw()` to `_gates.pyx` that emits P(angle) without checking `_get_controlled()`, preventing the double-wrap
- Added layer floor helpers and save/restore in `__iadd__` to keep the P gate outside the comparison's layer range, preventing the optimizer from cancelling it during uncomputation
- Manual S_0 path (`with x == 0: x.phase += pi`) now produces observable phase flip: |00> amplitude = -0.5, others = +0.5 in Qiskit statevector
- Added 2 new tests and updated 6 existing tests: direct statevector verification for width=2 and width=3, QASM-level P gate check

## Task Commits

Each task was committed atomically:

1. **Task 1: Add emit_p_raw and fix _PhaseProxy.__iadd__** - `dda58e1` (feat)
2. **Task 2: Update tests for emit_p_raw and add direct manual S_0 tests** - `d5c798c` (test)

**Plan metadata:** (pending)

## Files Created/Modified
- `src/quantum_language/_gates.pyx` - Added `emit_p_raw()` function after `emit_mcz`
- `src/quantum_language/qint.pyx` - Import `emit_p_raw`, added `_set_layer_floor_to_used`/`_restore_layer_floor`/`_get_layer_floor` helpers, fixed `_PhaseProxy.__iadd__`
- `tests/python/test_diffusion.py` - Updated 5 tests to expect P (not CP), replaced misleading `test_manual_s0_reflection_statevector` with direct test, added `test_manual_s0_direct_statevector` and `test_manual_s0_qasm_shows_p_gate`

## Decisions Made
- **emit_p_raw instead of fixing emit_p**: Adding a separate function is safer than modifying emit_p's behavior, which is used elsewhere. The "_raw" suffix clearly signals "no auto-control."
- **Layer floor manipulation in __iadd__**: The circuit optimizer shares layers across different qubits. Without forcing the P gate into a new layer, it ends up inside the comparison's [start_layer, end_layer) range and gets reversed during uncomputation. Setting layer_floor = used_layer before emitting P forces it into a dedicated layer.
- **P gate on control qubit (not CP)**: Quantum-mechanically, P(theta) on a qubit in |1> state implements a controlled global phase via phase kickback -- exactly what's needed for S_0. Using P instead of CP avoids the double-control bug entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Layer floor protection for P gate survival**
- **Found during:** Task 1 (emit_p_raw integration)
- **Issue:** After switching to emit_p_raw, the P gate was emitted correctly but disappeared from QASM output. The circuit optimizer placed P in the same layer as comparison gates, causing it to fall within the comparison's [start_layer, end_layer) range and get incorrectly reversed during uncomputation.
- **Fix:** Added layer floor helper functions (`_set_layer_floor_to_used`, `_restore_layer_floor`, `_get_layer_floor`) and save/restore logic in `_PhaseProxy.__iadd__` to force the P gate into a new layer after the comparison gates.
- **Files modified:** `src/quantum_language/qint.pyx`
- **Verification:** P gate visible in QASM, Qiskit statevector confirms S_0 reflection
- **Committed in:** `dda58e1` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Layer floor fix was essential for correctness -- without it the P gate was invisible and had no quantum effect. No scope creep.

## Issues Encountered
- C-level `reverse_circuit_range` layer_floor modification was explored and rejected: caused segfaults in broader test suite. The Cython-level fix (in `__iadd__`) is correct because it targets the specific P gate placement, not all reversed gates.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GROV-05 (manual S_0 path) is now fully functional and verified
- Both `ql.diffusion()` (X-MCZ-X) and manual `with x == 0: x.phase += pi` paths work correctly
- Ready for Phase 79 (Grover iteration) which combines oracle + diffusion

## Self-Check: PASSED

- All 4 files verified present
- Both task commits verified (dda58e1, d5c798c)
- Key content verified in all modified files (emit_p_raw, test_manual_s0_direct_statevector, test_manual_s0_qasm_shows_p_gate)
- 22/22 diffusion tests passing

---
*Phase: 78-diffusion-operator*
*Completed: 2026-02-20*
