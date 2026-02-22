---
phase: 80-oracle-auto-synthesis-adaptive-search
plan: 01
subsystem: quantum-algorithm
tags: [grover, oracle, predicate, lambda, synthesis, tracing, cache, closure]

# Dependency graph
requires:
  - phase: 79-grover-search-integration
    provides: "ql.grover() API, GroverOracle class, oracle caching, Qiskit simulation"
  - phase: 77-oracle-infrastructure
    provides: "GroverOracle class, grover_oracle decorator, oracle validation, CompiledFunc"
provides:
  - "_predicate_to_oracle: converts Python callable predicates into GroverOracle via tracing"
  - "_lambda_cache_key: cache key with closure variable values, arithmetic mode, register widths"
  - "grover() *registers support for explicit register passing"
  - "grover() predicate detection: callable oracles auto-synthesized"
  - "_verify_classically: post-measurement classical predicate verification helper"
  - "grover() m=None placeholder for Plan 02 BBHT adaptive search"
affects: [80-02-adaptive-search, 81-amplitude-estimation]

# Tech tracking
tech-stack:
  added: []
  patterns: [predicate-tracing-synthesis, closure-aware-cache-key, variadic-register-passing]

key-files:
  created: []
  modified: [src/quantum_language/oracle.py, src/quantum_language/grover.py]

key-decisions:
  - "Tracing approach for predicate synthesis (not AST parsing) -- call predicate with real qint objects"
  - "validate=False on synthesized oracles (P gate targets comparison ancilla, not search register)"
  - "m=None defaults to m=1 in Plan 01 as backwards-compatible placeholder for Plan 02 BBHT"
  - "Closure variable values included in cache key to distinguish predicates with different captured values"
  - "noqa on predicate variable assignment (will be used by Plan 02 BBHT adaptive search)"

patterns-established:
  - "Predicate detection: not isinstance(oracle, GroverOracle | CompiledFunc) and callable(oracle)"
  - "Lambda cache key: (source_hash, closure_values, arithmetic_mode, register_widths_tuple)"
  - "Variadic register width extraction: [r.width for r in registers] from *registers positional args"

requirements-completed: [SYNTH-01, SYNTH-02, SYNTH-03]

# Metrics
duration: 31min
completed: 2026-02-22
---

# Phase 80 Plan 01: Predicate-to-Oracle Synthesis Summary

**Predicate-to-oracle auto-synthesis via tracing with closure-aware caching, *registers support, and _verify_classically helper for grover()**

## Performance

- **Duration:** 31 min
- **Started:** 2026-02-22T12:50:08Z
- **Completed:** 2026-02-22T13:21:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added _predicate_to_oracle and _lambda_cache_key to oracle.py (114 new lines) enabling `ql.grover(lambda x: x > 5, width=3)` syntax
- Updated grover() signature to support *registers positional args, predicate detection, and m=None for future adaptive search
- Added _verify_classically helper for post-measurement classical verification (BBHT Plan 02)
- All 21 existing test_grover.py tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add predicate-to-oracle synthesis to oracle.py** - `951cdc0` (feat)
2. **Task 2: Update grover() with predicate detection and *registers support** - `aaedf64` (feat)

## Files Created/Modified
- `src/quantum_language/oracle.py` - Added _lambda_cache_key (closure-aware cache key), _predicate_to_oracle (tracing-based synthesis), _predicate_oracle_cache dict
- `src/quantum_language/grover.py` - Updated grover() signature (*registers, m=None, max_attempts), predicate detection, _verify_classically helper, updated docstring and module docstring

## Decisions Made
- Used tracing approach for predicate synthesis: predicate called with real qint objects, existing comparison/arithmetic operators capture gates automatically. No AST parsing needed.
- validate=False on synthesized oracles because phase marking via `with result: x.phase += math.pi` targets the comparison ancilla qubit, not search register qubits (same pattern as Phase 79-02).
- m=None defaults to m=1 in Plan 01 as backwards-compatible placeholder. Plan 02 will add BBHT adaptive search.
- Closure variable values (int, float, str, bool only) included in lambda cache key to distinguish closures with different captured values but identical source text.
- predicate variable saved with noqa comment for future Plan 02 use (BBHT needs the original predicate for classical verification).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed duplicate register creation in grover()**
- **Found during:** Task 2
- **Issue:** Two unconditional `registers = [qint_type(0, width=w)...]` lines created double registers on the circuit, consuming double qubits and causing oracle to target wrong register
- **Fix:** Removed duplicate, kept single register creation after circuit() call
- **Files modified:** src/quantum_language/grover.py
- **Verification:** All 21 tests pass, 2-qubit Grover returns correct value=3
- **Committed in:** aaedf64 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug was in newly written code, caught during verification. No scope creep.

## Issues Encountered
- Ruff lint: `isinstance(x, (int, float, str, bool))` requires `int | float | str | bool` syntax (UP038 rule). Fixed.
- Ruff lint: unused `predicate` variable flagged (F841). Added noqa comment since it will be used by Plan 02 BBHT.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Predicate-to-oracle synthesis infrastructure complete, ready for end-to-end testing and BBHT adaptive search in Plan 02
- _verify_classically ready for BBHT loop integration
- grover() m=None and max_attempts= parameters stubbed for Plan 02
- All helpers importable for testing and extension

## Self-Check: PASSED

- FOUND: src/quantum_language/oracle.py
- FOUND: src/quantum_language/grover.py
- FOUND: 80-01-SUMMARY.md
- FOUND: commit 951cdc0
- FOUND: commit aaedf64

---
*Phase: 80-oracle-auto-synthesis-adaptive-search*
*Completed: 2026-02-22*
