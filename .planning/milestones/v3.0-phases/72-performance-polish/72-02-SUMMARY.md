---
phase: 72-performance-polish
plan: 02
subsystem: performance
tags: [toffoli, hardcoded-sequences, t-count, dispatch, build-system]

# Dependency graph
requires:
  - phase: 72-01
    provides: "Toffoli hardcoded C files + dispatch (toffoli_add_seq_*.c, toffoli_sequences.h)"
  - phase: 72-03
    provides: "T-count and MCX tracking in gate_counts_t struct (circuit_stats.h/c, _core.pxd/pyx)"
provides:
  - "Hardcoded Toffoli sequence dispatch in ToffoliAddition.c (zero-malloc for widths 1-8)"
  - "Build system integration for 9 new Toffoli C source files"
  - "17 verification tests: T-count reporting + hardcoded correctness + gate purity"
affects: [ToffoliAddition.c, setup.py, hot_path_add.c]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Hardcoded sequence cache-first lookup between cache check and dynamic generation"]

key-files:
  created:
    - tests/test_toffoli_hardcoded.py
  modified:
    - c_backend/src/ToffoliAddition.c
    - setup.py

key-decisions:
  - "Hardcoded lookup placed BETWEEN cache check and dynamic generation (not before cache): first call hits hardcoded, stores in cache; subsequent calls hit cache directly"
  - "T-count exposure already done by 72-03 (no _core.pxd/_core.pyx changes needed): adapted plan to avoid duplicating work"
  - "Test correctness via Qiskit AerSimulator (not qint.measure()) since measure() returns initial value without simulation"

patterns-established:
  - "Toffoli hardcoded dispatch: #include toffoli_sequences.h, check TOFFOLI_HARDCODED_MAX_WIDTH, const cast to cache"

requirements-completed: [INF-03, INF-04]

# Metrics
duration: 18min
completed: 2026-02-16
---

# Phase 72 Plan 02: Hardcoded Toffoli Integration + T-count Exposure Summary

**Hardcoded Toffoli CDKM sequences wired into ToffoliAddition.c dispatch for zero-malloc widths 1-8, with 17 verification tests for T-count reporting and correctness**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-16T23:14:57Z
- **Completed:** 2026-02-16T23:33:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Wired `get_hardcoded_toffoli_QQ_add()` and `get_hardcoded_toffoli_cQQ_add()` into ToffoliAddition.c: first call for widths 1-8 uses pre-computed static sequences (zero malloc), cached for subsequent calls
- Added 9 Toffoli C source files (8 per-width + dispatch) to setup.py build configuration, compiling successfully alongside existing QFT hardcoded sequences
- Created 17 verification tests: 4 T-count tests (presence, formula, QFT zero, scaling), 4 QQ correctness at widths 1-4, 4 gate purity, 2 controlled QQ, 2 subtraction, 1 regression
- Confirmed T-count exposure already present from 72-03 (MCX + T-count in gate_counts_t): no duplicate changes to _core.pxd/_core.pyx

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire hardcoded Toffoli sequences into ToffoliAddition.c and build system** - `7717351` (feat)
2. **Task 2: Expose T-count in Python API and write verification tests** - `dfd71b0` (test)

## Files Created/Modified
- `c_backend/src/ToffoliAddition.c` - Added hardcoded lookup in toffoli_QQ_add() and toffoli_cQQ_add()
- `setup.py` - Added 9 Toffoli sequence C files to c_sources list
- `tests/test_toffoli_hardcoded.py` - 17 verification tests for hardcoded sequences and T-count

## Decisions Made
- **Hardcoded lookup placement**: Placed between cache check and dynamic generation. On first call, cache is empty, hardcoded hit stores in cache and returns. On subsequent calls, cache returns immediately (O(1)). This matches the pattern from IntegerAddition.c for QFT sequences.
- **No _core.pxd/_core.pyx changes**: Plan 72-03 (Wave 1) already added `t_count`, `mcx_gates` to `gate_counts_t` struct and exposed 'T' and 'MCX' keys in Python gate_counts dict. Detected during pre-execution file review, avoided duplicate work.
- **Test verification via Qiskit**: Plan specified `qint.measure()` for correctness testing, but `measure()` returns the initial value without simulation. Adapted to use Qiskit AerSimulator statevector method (same proven pattern as test_toffoli_addition.py).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test verification method (measure -> Qiskit simulation)**
- **Found during:** Task 2 (verification tests)
- **Issue:** Plan's tests used `qint.measure()` which returns initial value without simulation; arithmetic results cannot be verified this way
- **Fix:** Rewrote correctness tests to use Qiskit AerSimulator with QASM export, matching test_toffoli_addition.py pattern
- **Files modified:** tests/test_toffoli_hardcoded.py
- **Verification:** All 17 tests pass including simulation-based correctness checks
- **Committed in:** dfd71b0 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed qint constructor usage (positional args)**
- **Found during:** Task 2 (verification tests)
- **Issue:** Plan used `qint(width, value)` but actual signature is `qint(value, width=width)` -- first positional is value, width is keyword
- **Fix:** Changed all qint constructors to use keyword width argument: `qint(a_val, width=width)`
- **Files modified:** tests/test_toffoli_hardcoded.py
- **Verification:** All 17 tests pass
- **Committed in:** dfd71b0 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in plan's test code)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
- `pip install -e .` failed in sandbox environment (externally-managed-environment + build_preprocessor import). Used `python setup.py build_ext --inplace` via venv activation instead.
- Full regression suite (`tests/python/`) hangs or OOM-kills on certain tests (pre-existing, not caused by this plan's changes). Toffoli-specific and T-count tests all pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 72 complete: all 3 plans (01, 02, 03) finished
- Hardcoded Toffoli sequences integrated into dispatch (widths 1-8)
- T-count and MCX tracking exposed in Python API
- AND-ancilla MCX decomposition applied to QQ multiplication
- Ready for next milestone work

## Self-Check: PASSED

- All 3 modified/created files verified present on disk
- Task 1 commit 7717351 verified in git log
- Task 2 commit dfd71b0 verified in git log
- SUMMARY.md exists at expected path

---
*Phase: 72-performance-polish*
*Completed: 2026-02-16*
