---
phase: 74-mcx-ccx-gate-decomposition-sequence-refactoring
plan: 02
subsystem: gate-infrastructure
tags: [t-gate, tdg-gate, toffoli-decompose, gate-counting, qasm-export, clifford-t]

# Dependency graph
requires:
  - phase: 72-toffoli-hardcoded-sequences
    provides: "gate_counts_t with mcx_gates field, T-count estimation"
provides:
  - "T_GATE and TDG_GATE enum values in Standardgate_t"
  - "t_gate() and tdg_gate() gate primitives"
  - "T/Tdg inverse recognition in gates_are_inverse()"
  - "toffoli_decompose field in circuit_t with Python API"
  - "T/Tdg counting in gate_counts_t (replaces mcx_gates)"
  - "QASM export for T and Tdg gates"
  - "Updated Python gate_counts dict with T_gates/Tdg_gates keys"
affects: [74-03-mcx-decomposition, 74-04-ccx-clifford-t, 74-05-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "T_GATE/TDG_GATE naming to avoid C macro conflicts"
    - "Derived T-count field: actual when T gates present, estimate from CCX otherwise"

key-files:
  created: []
  modified:
    - "c_backend/include/types.h"
    - "c_backend/include/gate.h"
    - "c_backend/src/gate.c"
    - "c_backend/include/circuit.h"
    - "c_backend/src/circuit_allocations.c"
    - "c_backend/include/circuit_stats.h"
    - "c_backend/src/circuit_stats.c"
    - "c_backend/src/circuit_output.c"
    - "src/quantum_language/_core.pxd"
    - "src/quantum_language/_core.pyx"
    - "tests/python/test_phase8_circuit.py"
    - "tests/test_toffoli_hardcoded.py"
    - "tests/test_mul_addsub.py"
    - "tests/test_toffoli_cq_reduction.py"

key-decisions:
  - "Used T_GATE/TDG_GATE naming (not T/Tdg) to avoid C macro conflicts per RESEARCH.md"
  - "Removed MCX from gate_counts entirely (3+ control X counted as 'other')"
  - "T-count dual formula: actual T/Tdg count when present, 7*CCX estimate when not"
  - "T/Tdg recognized as inverses via special case in gates_are_inverse() (not self-inverse)"

patterns-established:
  - "T_GATE/TDG_GATE enum values always at end of Standardgate_t"
  - "gate_counts dict excludes MCX; uses T_gates/Tdg_gates/T keys"
  - "toffoli_decompose option pattern matches fault_tolerant/cla option style"

requirements-completed: [INF-04]

# Metrics
duration: 26min
completed: 2026-02-17
---

# Phase 74 Plan 02: Gate Infrastructure Foundation Summary

**T_GATE/TDG_GATE enum values, gate primitives, inverse recognition, toffoli_decompose circuit option, updated gate counting (T_gates/Tdg_gates replacing MCX), and QASM export for T/Tdg gates**

## Performance

- **Duration:** 26 min
- **Started:** 2026-02-17T14:21:47Z
- **Completed:** 2026-02-17T14:47:49Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Added T_GATE and TDG_GATE to the Standardgate_t enum with full infrastructure (creation, counting, export, inverse detection, visualization)
- Added toffoli_decompose field to circuit_t with Python ql.option() API for future CCX-to-Clifford+T decomposition
- Replaced mcx_gates with t_gates/tdg_gates in gate_counts_t, with dual T-count formula (actual when decomposed, estimate from CCX otherwise)
- Updated all switch statements across gate.c, circuit_output.c, and circuit_stats.c for T_GATE/TDG_GATE
- Updated 4 test files to remove MCX key references and use new gate_counts schema

## Task Commits

Each task was committed atomically:

1. **Task 1: Add T_GATE/TDG_GATE enum, gate primitives, inverse recognition, toffoli_decompose field** - `3ff9dfa` (feat)
2. **Task 2: Update gate counting, QASM export, and Python option/stats API** - `51871b8` (feat)

## Files Created/Modified
- `c_backend/include/types.h` - Added T_GATE, TDG_GATE to Standardgate_t enum
- `c_backend/include/gate.h` - Added t_gate(), tdg_gate() declarations
- `c_backend/src/gate.c` - Implemented t_gate()/tdg_gate(), T/Tdg inverse detection, switch updates
- `c_backend/include/circuit.h` - Added toffoli_decompose field to circuit_t
- `c_backend/src/circuit_allocations.c` - Initialize toffoli_decompose to 0 in init_circuit()
- `c_backend/include/circuit_stats.h` - Replaced mcx_gates with t_gates/tdg_gates, updated t_count comment
- `c_backend/src/circuit_stats.c` - T_GATE/TDG_GATE counting, MCX->other routing, dual t_count formula
- `c_backend/src/circuit_output.c` - T/Tdg in print_circuit, circuit_visualize, QASM export ("t"/"tdg")
- `src/quantum_language/_core.pxd` - T_GATE/TDG_GATE enum, t_gates/tdg_gates in gate_counts_t, toffoli_decompose in circuit_s
- `src/quantum_language/_core.pyx` - toffoli_decompose option API, gate_counts dict (T_gates/Tdg_gates replacing MCX)
- `tests/python/test_phase8_circuit.py` - Updated expected_keys and gate_counts sum (excludes T derived field)
- `tests/test_toffoli_hardcoded.py` - Updated T-count formula: 7*CCX (removed MCX references)
- `tests/test_mul_addsub.py` - Updated MCX assertions to use 'other', T-count formula simplified
- `tests/test_toffoli_cq_reduction.py` - Removed MCX from gate total sum

## Decisions Made
- Used T_GATE/TDG_GATE naming instead of T/Tdg to avoid C macro conflicts (T is a common macro name in C)
- Removed MCX field entirely from gate_counts rather than keeping it alongside T_gates/Tdg_gates -- MCX (3+ control) gates are now counted under 'other' since they should not appear after decomposition
- T-count uses dual formula: when actual T/Tdg gates are present, sum them directly; otherwise estimate as 7*CCX. This handles both decomposed and non-decomposed circuits correctly.
- T and Tdg are recognized as inverses via a special case before the Gate equality check in gates_are_inverse(), since they have different enum values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_phase8_circuit.py gate_counts assertions**
- **Found during:** Task 2 (verification)
- **Issue:** test_gate_counts_property_exists expected old key set (without T_gates/Tdg_gates/T), and test_gate_counts_breakdown summed all values including derived 'T' field
- **Fix:** Updated expected_keys set, excluded 'T' from gate count sum
- **Files modified:** tests/python/test_phase8_circuit.py
- **Verification:** All 18 phase8 tests pass
- **Committed in:** 51871b8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test update was necessary to match the new gate_counts schema. No scope creep.

## Issues Encountered
None - plan executed cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- T_GATE/TDG_GATE infrastructure complete -- Plan 03 (MCX decomposition) and Plan 04/05 (CCX Clifford+T decomposition) can now emit T and Tdg gates
- toffoli_decompose option plumbed from Python to C -- Plan 04 can check this flag to route CCX gates through decomposition
- gate_counts correctly tracks T_gates/Tdg_gates -- Plan 05 verification can validate actual T-counts after decomposition

## Self-Check: PASSED

All 14 modified files verified present. Both task commits (3ff9dfa, 51871b8) verified in git log.

---
*Phase: 74-mcx-ccx-gate-decomposition-sequence-refactoring*
*Completed: 2026-02-17*
