---
phase: 81-amplitude-estimation-iqae
plan: 01
subsystem: quantum-algorithms
tags: [iqae, amplitude-estimation, grover, scipy, confidence-interval, clopper-pearson]

# Dependency graph
requires:
  - phase: 79-grover-search
    provides: "Grover iterate infrastructure (_run_grover_attempt, oracle, diffusion)"
  - phase: 80-oracle-auto-synthesis-adaptive-search
    provides: "Predicate-to-oracle synthesis, _verify_classically, BBHT adaptive search"
provides:
  - "IQAE algorithm module (amplitude_estimation.py)"
  - "AmplitudeEstimationResult float-like result class"
  - "ql.amplitude_estimate() public API"
  - "Multi-shot Qiskit simulation helper"
  - "Clopper-Pearson confidence interval computation"
  - "FindNextK and theta interval refinement helpers"
affects: [81-02-PLAN, amplitude-estimation-tests]

# Tech tracking
tech-stack:
  added: [scipy.stats.beta (Clopper-Pearson CI)]
  patterns: [IQAE theta interval refinement, multi-shot simulation, float-like result objects]

key-files:
  created:
    - src/quantum_language/amplitude_estimation.py
  modified:
    - src/quantum_language/__init__.py

key-decisions:
  - "Default epsilon=0.01 (common IQAE default from literature and Qiskit examples)"
  - "Clopper-Pearson CI via scipy.stats.beta.ppf (tighter than Chernoff-Hoeffding)"
  - "Classical predicate required for good-state classification (no ancilla-based approach)"
  - "Multi-shot simulation extends _simulate_single_shot pattern with configurable shots"
  - "Decorated oracles require explicit predicate kwarg for IQAE (raises ValueError otherwise)"

patterns-established:
  - "Multi-shot simulation: _simulate_multi_shot(qasm_str, shots) returns Qiskit counts dict"
  - "Float-like result class: AmplitudeEstimationResult with full numeric dunder methods"
  - "IQAE loop pattern: FindNextK -> build_and_simulate -> count_good_states -> Clopper-Pearson -> update_theta"

requirements-completed: [AMP-01, AMP-02, AMP-03]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 81 Plan 01: IQAE Algorithm & Result Class Summary

**QFT-free iterative amplitude estimation (IQAE) with Clopper-Pearson confidence intervals, multi-shot simulation, and float-like AmplitudeEstimationResult class**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T16:04:01Z
- **Completed:** 2026-02-22T16:08:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Complete IQAE algorithm implementation following Grinko et al. (2021) with theta interval refinement
- AmplitudeEstimationResult class with full float-like arithmetic (19 dunder methods)
- Public `ql.amplitude_estimate()` API mirroring `ql.grover()` signature pattern
- Multi-shot simulation, Clopper-Pearson confidence intervals, FindNextK algorithm
- Lambda predicate auto-synthesis via existing `_predicate_to_oracle` infrastructure

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement amplitude_estimation.py module with IQAE algorithm** - `023df06` (feat)
2. **Task 2: Export amplitude_estimate from __init__.py** - `720c76a` (feat)

## Files Created/Modified
- `src/quantum_language/amplitude_estimation.py` - IQAE algorithm module: AmplitudeEstimationResult class, _simulate_multi_shot, _count_good_states, _clopper_pearson_confint, _find_next_k, _update_theta_interval, _build_and_simulate, _iqae_loop, amplitude_estimate()
- `src/quantum_language/__init__.py` - Added amplitude_estimate import and __all__ export

## Decisions Made
- Default epsilon=0.01 per research recommendation (common IQAE default in literature)
- Clopper-Pearson CI via scipy.stats.beta.ppf for tighter confidence intervals than Chernoff
- Classical predicate required for good-state classification -- decorated oracles must pass predicate= kwarg
- Shots per round computed from IQAE paper formula: ceil(32 / (1-2*sin(pi/14))^2 * ln(2*T/alpha))
- max_iterations caps num_oracle_queries (shots * k per round), not IQAE round count
- Bonferroni correction: alpha / max_rounds per confidence interval computation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- IQAE module complete and exported, ready for Plan 02 (tests)
- All internal helpers are importable for unit testing
- Integration tests can use lambda predicates with known solution counts

## Self-Check: PASSED

- [x] `src/quantum_language/amplitude_estimation.py` exists
- [x] `src/quantum_language/__init__.py` modified with export
- [x] Commit `023df06` found (Task 1)
- [x] Commit `720c76a` found (Task 2)

---
*Phase: 81-amplitude-estimation-iqae*
*Completed: 2026-02-22*
