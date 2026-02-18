---
phase: 31
plan: 02
subsystem: verification
tags: [comparison, preservation, operand-integrity, calibration, qiskit]
dependency-graph:
  requires: []
  provides: ["operand preservation verification for all 6 comparison operators"]
  affects: ["33-final-verification"]
tech-stack:
  added: []
  patterns: ["calibration-based extraction", "per-operator bitstring layout detection"]
key-files:
  created: ["tests/test_compare_preservation.py"]
  modified: []
decisions:
  - id: "31-02-D1"
    decision: "Module-level calibration with empirical position detection"
    rationale: "Different operators have different qubit layouts (gt uses widened temporaries); positions must be empirically determined per operator"
  - id: "31-02-D2"
    decision: "No xfails needed -- all operators preserve operands"
    rationale: "All 6 operators in both QQ and CQ variants preserve input operands correctly across all test pairs"
metrics:
  duration: "3m 28s"
  completed: "2026-01-31"
  tests-added: 108
  tests-passed: 108
  tests-xfailed: 0
---

# Phase 31 Plan 02: Operand Preservation Verification Summary

**One-liner:** Calibration-based operand preservation tests confirm all 6 comparison operators (eq, ne, lt, gt, le, ge) in both QQ and CQ variants preserve input qint values after comparison.

## What Was Done

### Task 1: Create operand preservation tests with per-operator calibration

Created `tests/test_compare_preservation.py` with:

1. **Pipeline helper** (`_run_comparison_pipeline`): Runs a comparison through the full pipeline (quantum_language -> OpenQASM -> Qiskit simulate) and returns the complete bitstring for analysis.

2. **Calibration system** (`_calibrate_extraction`): Empirically determines where operand values sit in the measurement bitstring by running a known case (width=3, a=3, b=5) and searching for the values. Handles both standard positions (rightmost for first-allocated) and non-standard layouts (gt with widened temporaries).

3. **96 preservation tests**: 6 operators x 2 variants x 8 test pairs covering boundaries (0,7), (7,0), (7,7) and interior values (3,5), (5,3), (4,4), (1,6), (2,3).

4. **12 calibration sanity tests**: Verify the calibration itself produces correct extraction positions.

**Key finding:** All comparison operators preserve operands correctly. The `__gt__` operator, despite creating widened (w+1) temporaries, does not modify the original operands. The subtract-add-back patterns in `__eq__`, `__lt__`, and their derivatives correctly restore values.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 31-02-D1 | Module-level calibration with empirical position detection | gt uses widened temporaries with different layout; empirical detection handles all variants uniformly |
| 31-02-D2 | No xfails needed | All operators preserve operands correctly -- no bugs found |

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Hash | Description |
|------|-------------|
| 768c1dd | test(31-02): add operand preservation verification for comparison operators |

## Test Results

```
108 passed, 0 xfailed, 0 failed
```

Breakdown:
- 48 QQ preservation tests (6 ops x 8 pairs): all pass
- 48 CQ preservation tests (6 ops x 8 pairs): all pass
- 6 QQ calibration sanity tests: all pass
- 6 CQ calibration sanity tests: all pass

## Next Phase Readiness

No blockers. Operand preservation is verified for all comparison operators. This satisfies VCMP-03 edge case coverage requirements.
