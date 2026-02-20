---
phase: 77-oracle-infrastructure
plan: 02
subsystem: testing
tags: [grover, oracle, pytest, qiskit, simulation, integration-tests, phase-marking, caching]

# Dependency graph
requires:
  - phase: 77-oracle-infrastructure
    provides: oracle.py module with GroverOracle class, grover_oracle decorator, emit_x
provides:
  - 37 integration tests for oracle infrastructure (ORCL-01 through ORCL-05)
  - Qiskit simulation verification of oracle circuit validity
  - Direct (non-compiled) phase oracle tests showing CZ gate phase marking
  - Allocator consistency tests for oracle ancilla lifecycle
affects: [79-grover-search-api, 80-oracle-auto-synthesis]

# Tech tracking
tech-stack:
  added: []
  patterns: [oracle-test-pattern, direct-vs-compiled-oracle-testing, allocator-stats-verification]

key-files:
  created:
    - tests/python/test_oracle.py
  modified: []

key-decisions:
  - "Direct (non-compiled) oracle tests used for QASM-visible phase marking verification"
  - "Compiled oracle tests focus on allocator stats and API behavior since compile replay packs gates into existing layers"
  - "bit_flip=True mismatch detection tested as expected error behavior (standard comparison oracle cannot interact with kickback ancilla)"
  - "Cache key testing at _oracle_cache_key level verifies arithmetic_mode/width/source differentiation without circuit-level side effects"

patterns-established:
  - "Oracle test pattern: fresh ql.circuit() + option('fault_tolerant', True) per test for isolation"
  - "Factory function pattern for parameterized oracles in loops to avoid closure variable capture (B023)"
  - "Allocator stats verification: pre/post circuit_stats() comparison for zero ancilla delta"

requirements-completed: [ORCL-01, ORCL-02, ORCL-03, ORCL-04, ORCL-05]

# Metrics
duration: 14min
completed: 2026-02-20
---

# Phase 77 Plan 02: Oracle Tests Summary

**37 integration tests covering all 5 ORCL requirements: decorator API, compute-phase-uncompute validation, ancilla delta enforcement, bit-flip mismatch detection, and arithmetic-mode-aware caching -- verified via Qiskit simulation and allocator stats**

## Performance

- **Duration:** 14 min
- **Started:** 2026-02-20T16:18:37Z
- **Completed:** 2026-02-20T16:32:58Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created test_oracle.py (946 lines) with 37 tests across 7 test classes
- All 5 ORCL requirements verified: decorator API (ORCL-01), compute-phase-uncompute (ORCL-02), ancilla delta (ORCL-03), bit-flip wrapping (ORCL-04), caching (ORCL-05)
- Qiskit simulation tests verify valid OpenQASM generation, circuit simulation, and phase-marking gate visibility
- Direct oracle tests demonstrate CZ gate phase marking in QASM output
- Full test suite (31 existing branch + 37 new oracle) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create oracle unit and validation tests** - `eaf9afe` (test)
2. **Task 2: Qiskit simulation verification of oracle phase semantics** - `08ae165` (test)

## Files Created/Modified
- `tests/python/test_oracle.py` - 37 integration tests for oracle infrastructure (946 lines)

## Test Coverage by Requirement

| Requirement | Tests | Coverage |
|-------------|-------|----------|
| ORCL-01 (Decorator API) | 7 | bare, parens, params, validate=False, auto-compile, callable, repr |
| ORCL-02 (CPU Ordering) | 2 | valid pattern passes, multiple comparison targets pass |
| ORCL-03 (Ancilla Delta) | 4 | zero passes, nonzero raises, validate=False bypass, runtime stats |
| ORCL-04 (Bit-Flip) | 4 | callable, mismatch raises, validate=False still raises, flag preserved |
| ORCL-05 (Caching) | 6 | cache hit, miss on width, arithmetic_mode key, width key, source hash key, mode switch |
| Simulation | 14 | OpenQASM validity, Qiskit simulation, superposition, direct CZ, interference, multi-target, qubit count, phase marking, Grover iteration, allocator consistency, multiple calls |

## Decisions Made
- Direct (non-compiled) oracle tests used for QASM-level verification because @ql.compile replay packs gates into existing layers, making them invisible in QASM export -- this is expected behavior of the compile optimization (adjacent inverse cancellation)
- bit_flip=True tested as expected error behavior: standard comparison oracle (flag = x == 5; with flag: pass) cannot interact with the system-allocated kickback ancilla because the comparison creates its own independent ancilla qubits
- Cache key differentiation tested at the _oracle_cache_key function level for precise arithmetic_mode/width/source verification without circuit-level interference
- Factory function pattern used for parameterized oracles in loops to satisfy B023 linting (closure variable binding)

## Deviations from Plan

None - plan executed exactly as written. The plan's fallback guidance for complex Qiskit tests was followed: direct (non-compiled) oracle tests demonstrate phase marking gate visibility, while compiled oracle tests verify allocator behavior and API correctness.

## Issues Encountered
- Compiled oracle (@ql.compile + @ql.grover_oracle) produces empty QASM because the compile optimization cancels adjacent inverse gate pairs (compute + uncompute with empty phase block = identity). This is correct mathematical behavior, not a bug. Direct (non-compiled) oracle tests used as complement to show gate-level behavior.
- Pre-existing qarray segfault in test_api_coverage.py (BUG in STATE.md) -- not caused by oracle changes, not in scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Oracle infrastructure fully tested and ready for Phase 79 (Grover search API)
- 37 tests provide regression safety net for future oracle modifications
- Direct oracle test pattern established for Phase 78 (diffusion operator) testing

## Self-Check: PASSED

- FOUND: tests/python/test_oracle.py (946 lines, 37 tests)
- FOUND: eaf9afe (Task 1 commit)
- FOUND: 08ae165 (Task 2 commit)
- FOUND: 77-02-SUMMARY.md

---
*Phase: 77-oracle-infrastructure*
*Completed: 2026-02-20*
