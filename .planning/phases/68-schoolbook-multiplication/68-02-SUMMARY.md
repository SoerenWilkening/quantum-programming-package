---
phase: 68-schoolbook-multiplication
plan: 02
subsystem: testing
tags: [toffoli, multiplication, verification, exhaustive, qiskit, statevector]

# Dependency graph
requires:
  - phase: 68-schoolbook-multiplication
    plan: 01
    provides: "ToffoliMultiplication.c with toffoli_mul_qq and toffoli_mul_cq functions"
  - phase: 66-toffoli-addition
    provides: "test_toffoli_addition.py verification patterns (_simulate_and_extract, _verify_toffoli_qq)"
provides:
  - "Exhaustive correctness proof for Toffoli QQ multiplication at widths 1-3"
  - "Exhaustive correctness proof for Toffoli CQ multiplication at widths 1-3"
  - "Gate purity verification: Toffoli mul uses only CCX/CX/X (no QFT gates)"
  - "Operator dispatch verification: default mode routes to Toffoli path"
affects: [69-controlled-toffoli-multiplication]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Custom result extraction for Toffoli mul (QQ at 2*w, CQ at w) vs verify_circuit fixture"]

key-files:
  created:
    - "tests/test_toffoli_multiplication.py"
  modified: []

key-decisions:
  - "Custom verification helpers instead of conftest verify_circuit fixture -- Toffoli path allocates ancilla at different positions"
  - "QQ result extraction from [2*width..3*width-1] (third register allocated after self and other)"
  - "CQ result extraction from [width..2*width-1] (result register allocated after original self)"
  - "Width 1-3 only (not 4+) to keep simulation tractable with 3*width + ancilla qubits"

patterns-established:
  - "Toffoli multiplication test pattern: same _simulate_and_extract helper, different result_start per operation type"

# Metrics
duration: 9min
completed: 2026-02-15
---

# Phase 68 Plan 02: Toffoli Multiplication Verification Tests Summary

**Exhaustive QQ/CQ Toffoli multiplication verification at widths 1-3 with gate purity and operator dispatch checks via Qiskit statevector simulation**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-15T09:53:12Z
- **Completed:** 2026-02-15T10:03:10Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Exhaustive QQ multiplication verification: all 84 input pairs at widths 1-3 produce correct (a*b) mod 2^w
- Exhaustive CQ multiplication verification: all 84 input pairs at widths 1-3 produce correct (a*b) mod 2^w
- Gate purity confirmed: QQ and CQ Toffoli multiplication circuits contain only CCX/CX/X gates (no H/P from QFT)
- Operator dispatch verified: `a * b` and `a *= b` use Toffoli path in default mode without explicit opt-in

## Task Commits

Each task was committed atomically:

1. **Task 1: Create exhaustive Toffoli multiplication verification tests** - `7c1368f` (test)

## Files Created/Modified
- `tests/test_toffoli_multiplication.py` - Exhaustive QQ/CQ Toffoli multiplication tests with gate purity and dispatch verification (9 test functions, ~507 implicit test cases)

## Decisions Made
- **Custom verification helpers:** Used `_verify_toffoli_mul_qq` and `_verify_toffoli_mul_cq` with explicit qubit position extraction rather than the `verify_circuit` conftest fixture. The Toffoli path allocates ancilla at different qubit positions than QFT, making the fixture's "first width bits of bitstring" extraction incorrect.
- **QQ result at position 2*width:** For `c = a * b`, allocation order is a[0..w-1], b[w..2w-1], c[2w..3w-1]. Result extracted from physical qubits [2*width..3*width-1].
- **CQ result at position width:** For `a *= val`, `__imul__` internally calls `__mul__` creating result at [w..2w-1], then swaps Python refs. Result extracted from physical qubits [width..2*width-1].
- **Widths 1-3 only:** Width 4 QQ mul requires 3*4 + ancilla = 13+ qubits for statevector simulation. Widths 1-3 keep test runtime under 10 seconds while providing exhaustive coverage.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 68 (Schoolbook Multiplication) is now fully complete
- All success criteria met: exhaustive verification at widths 1-3, gate purity, operator dispatch
- Ready for Phase 69 (Controlled Toffoli Multiplication) which will add cQQ and cCQ multiplication
- Existing test suites verified: 72 Toffoli addition tests pass, 165 hardcoded sequence tests pass

## Self-Check: PASSED

All files verified present:
- tests/test_toffoli_multiplication.py (contains TestToffoliQQMultiplication, TestToffoliCQMultiplication, TestToffoliMultiplicationGatePurity)

All commits verified:
- 7c1368f: test(68-02): add exhaustive Toffoli multiplication verification tests

---
*Phase: 68-schoolbook-multiplication*
*Completed: 2026-02-15*
