---
phase: 67-controlled-adder-backend-dispatch
plan: 02
subsystem: arithmetic
tags: [toffoli, cdkm, controlled-adder, hot-path, dispatch, mcx, use-after-free]

# Dependency graph
requires:
  - phase: 67-controlled-adder-backend-dispatch
    plan: 01
    provides: "toffoli_cQQ_add and toffoli_cCQ_add C functions with CCX + MCX gates"
  - phase: 66-cdkm-ripple-carry-adder
    provides: "hot_path_add.c dispatch pattern, ARITH_TOFFOLI mode enum"
provides:
  - "Controlled Toffoli dispatch in hot_path_add_qq (toffoli_cQQ_add) and hot_path_add_cq (toffoli_cCQ_add)"
  - "No QFT fallback for controlled operations in Toffoli mode"
  - "Cython declarations for toffoli_cQQ_add and toffoli_cCQ_add"
  - "Exhaustive controlled Toffoli addition tests for widths 1-4"
  - "MCX use-after-free fix in run_instruction and free_circuit"
affects: [67-03 default arithmetic mode switch]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Controlled Toffoli hot-path dispatch with register swap", "Circuit ownership of MCX large_control arrays"]

key-files:
  created: []
  modified:
    - c_backend/src/hot_path_add.c
    - c_backend/src/execution.c
    - c_backend/src/circuit_allocations.c
    - src/quantum_language/_core.pxd
    - tests/test_toffoli_addition.py

key-decisions:
  - "Circuit takes ownership of remapped large_control arrays (no free after add_gate)"
  - "free_circuit iterates gates to clean up large_control pointers for MCX gates"
  - "Controlled QQ 1-bit uses tqa[0]=self, tqa[1]=other, tqa[2]=control (no swap needed for XOR)"
  - "Controlled CQ 1-bit uses tqa[0]=self, tqa[1]=control (CX or identity)"

patterns-established:
  - "MCX ownership transfer: run_instruction allocates remapped large_control, circuit owns it after add_gate, free_circuit cleans up"
  - "Controlled in-place test pattern: _verify_controlled_inplace extracts result from qubits [0..w-1]"

# Metrics
duration: 39min
completed: 2026-02-14
---

# Phase 67 Plan 02: Controlled Toffoli Hot-Path Dispatch Summary

**Controlled Toffoli dispatch wired into hot_path_add.c with MCX use-after-free fix and exhaustive verification for widths 1-4**

## Performance

- **Duration:** 39 min
- **Started:** 2026-02-14T22:12:22Z
- **Completed:** 2026-02-14T22:51:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Wired controlled Toffoli dispatch into hot_path_add_qq (cQQ) and hot_path_add_cq (cCQ), eliminating QFT fallback
- Fixed pre-existing MCX use-after-free bug in run_instruction that caused garbage qubit indices in circuits with 3+ control gates
- Added 28 exhaustive controlled Toffoli tests: cQQ add/sub (widths 1-4), cCQ add/sub (widths 1-4), gate purity checks
- All 70 Toffoli tests pass (42 existing + 28 new), 165 hardcoded sequence tests pass, zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire controlled Toffoli dispatch in hot_path_add.c and add Cython declarations** - `a1fdc7c` (feat)
2. **Task 2: Exhaustive verification tests for controlled Toffoli addition + MCX fix** - `cf5b6b6` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `c_backend/src/hot_path_add.c` - Added controlled Toffoli paths in both QQ and CQ dispatch, removed QFT fallback comments
- `c_backend/src/execution.c` - Fixed MCX use-after-free: circuit takes ownership of remapped large_control arrays
- `c_backend/src/circuit_allocations.c` - Added large_control cleanup in free_circuit for MCX gates with 3+ controls
- `src/quantum_language/_core.pxd` - Added Cython declarations for toffoli_cQQ_add and toffoli_cCQ_add
- `tests/test_toffoli_addition.py` - Added TestControlledToffoliQQAddition and TestControlledToffoliCQAddition classes

## Decisions Made
- Circuit takes ownership of remapped large_control arrays allocated by run_instruction (no free after add_gate). This fixes a use-after-free where the circuit gate's large_control pointer pointed to freed memory.
- free_circuit now iterates through all gates in used layers to free large_control arrays for MCX gates with 3+ controls, preventing memory leaks.
- Controlled QQ 1-bit special case: tqa layout [self, other, control] with no register swap needed (XOR is symmetric).
- Controlled CQ 1-bit special case: tqa layout [self, control] using CX or identity based on classical value LSB.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MCX use-after-free in run_instruction**
- **Found during:** Task 2 (test verification revealed garbage qubit indices in QASM output)
- **Issue:** run_instruction allocated new large_control arrays for MCX gate qubit remapping, then freed them after add_gate. But add_gate stores the gate via memcpy (shallow copy), so the circuit's gate pointed to freed memory. This caused garbage qubit indices like q[470061322] in QASM output.
- **Fix:** Removed free of large_control after add_gate in both run_instruction and reverse_circuit_range. Added large_control cleanup in free_circuit to prevent memory leaks.
- **Files modified:** c_backend/src/execution.c, c_backend/src/circuit_allocations.c
- **Verification:** All controlled Toffoli tests pass with correct QASM output. No garbage qubit indices.
- **Committed in:** cf5b6b6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Bug fix was essential for controlled Toffoli MCX gates to work. Without it, any circuit using MCX gates (3+ controls) through run_instruction would produce corrupted output. No scope creep.

## Issues Encountered
- Pre-commit clang-format hook reformatted hot_path_add.c on first commit attempt. Re-staged and committed on second attempt.
- The tests/python/ suite has a pre-existing segfault (32-bit multiplication buffer overflow, already tracked in STATE.md). Used tests/test_toffoli_addition.py and tests/test_hardcoded_sequences.py for regression verification instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Controlled Toffoli dispatch fully operational: hot_path_add.c routes both QQ and CQ controlled operations to Toffoli path when fault_tolerant=True
- 70 Toffoli tests pass (uncontrolled + controlled), 165 hardcoded sequence tests pass
- Ready for Plan 03: default arithmetic mode switch and final integration
- MCX use-after-free fix benefits any future code path using MCX gates through run_instruction

## Self-Check: PASSED

- FOUND: c_backend/src/hot_path_add.c
- FOUND: c_backend/src/execution.c
- FOUND: c_backend/src/circuit_allocations.c
- FOUND: src/quantum_language/_core.pxd
- FOUND: tests/test_toffoli_addition.py
- FOUND: commit a1fdc7c
- FOUND: commit cf5b6b6
- ZERO "fall back to QFT" in hot_path_add.c

---
*Phase: 67-controlled-adder-backend-dispatch*
*Completed: 2026-02-14*
