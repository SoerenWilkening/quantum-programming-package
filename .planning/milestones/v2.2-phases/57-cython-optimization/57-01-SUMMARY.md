---
phase: 57-cython-optimization
plan: 01
subsystem: performance
tags: [cython, profiling, benchmarks, pytest-benchmark, debug-builds]

# Dependency graph
requires:
  - phase: 55-profiling-infrastructure
    provides: profiling Makefile targets (profile-cprofile, benchmark)
provides:
  - CYTHON_DEBUG build mode for debugging optimized code
  - Extended benchmark suite covering all operations (18 tests)
  - Baseline performance metrics for optimization tracking
affects: [57-02, 57-03, 57-04, 57-05, MIG, MEM phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "benchmark.pedantic with setup for qubit-allocating operations"
    - "Fresh circuit per benchmark iteration to prevent qubit exhaustion"

key-files:
  created: []
  modified:
    - setup.py
    - tests/benchmarks/test_qint_benchmark.py

key-decisions:
  - "Use benchmark.pedantic with setup for ops that allocate new qubits"
  - "In-place operations can use simple benchmark mode (no new qubits)"
  - "CYTHON_DEBUG enables boundscheck, wraparound, initializedcheck"

patterns-established:
  - "Debug build: CYTHON_DEBUG=1 pip install -e . for safety checks"
  - "Benchmark pattern: setup creates circuit+qints, operation measured separately"

# Metrics
duration: 8min
completed: 2026-02-05
---

# Phase 57 Plan 01: CYTHON_DEBUG and Baseline Benchmarks Summary

**CYTHON_DEBUG build mode and expanded benchmark suite (18 tests) capturing baseline performance: iadd 25us, xor 30us, add 53us, mul 356us, mul_classical 31ms**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-05T14:55:24Z
- **Completed:** 2026-02-05T15:03:XX
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added CYTHON_DEBUG=1 build mode enabling all safety checks (boundscheck, wraparound, initializedcheck)
- Expanded benchmark suite from 9 to 18 tests covering add, mul, bitwise (xor, and, or), comparison (eq, lt), and in-place operations
- Captured baseline metrics for all operations to track optimization progress
- Fixed benchmark qubit exhaustion issue using pedantic mode with setup functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CYTHON_DEBUG build mode to setup.py** - `dede885` (feat)
2. **Task 2: Expand benchmark suite** - `df7b6cd` (feat)
3. **Task 2 fix: Use pedantic mode for benchmarks** - `7077ca0` (fix)

Task 3 was diagnostic-only (no code changes to commit).

## Files Created/Modified
- `setup.py` - Added CYTHON_DEBUG environment variable support with debug_directives
- `tests/benchmarks/test_qint_benchmark.py` - Expanded from 9 to 18 tests, using pedantic mode for qubit-allocating ops

## Baseline Benchmark Results

| Operation | Mean (us) | Min (us) | OPS | Notes |
|-----------|-----------|----------|-----|-------|
| iadd_8bit | 24.98 | 14.48 | 40,040 | In-place, no alloc |
| iadd_quantum_8bit | 68.55 | 17.70 | 14,588 | In-place, no alloc |
| xor_8bit | 29.81 | 23.11 | 33,546 | Fast bitwise |
| and_8bit | 30.22 | 20.03 | 33,096 | Fast bitwise |
| or_8bit | 32.97 | 22.48 | 30,335 | Fast bitwise |
| add_8bit | 53.38 | 38.32 | 18,733 | |
| eq_8bit | 99.99 | 74.14 | 10,001 | |
| lt_8bit | 152.16 | 122.73 | 6,572 | |
| mul_8bit | 356.29 | 245.74 | 2,807 | Multiplication |
| mul_classical | 31,256 | 4,486 | 32 | Very slow - optimize |

**Key observations:**
- Classical multiplication is 100x slower than quantum multiplication
- Comparisons (eq, lt) are 2-5x slower than bitwise ops
- In-place operations are fastest (no qubit allocation overhead)

## Cython Annotation File Sizes

Larger files have more yellow lines (Python interaction overhead):

| File | Size | Priority |
|------|------|----------|
| qint_preprocessed.html | 1.95 MB | Primary target |
| qarray.html | 1.21 MB | Secondary target |
| _core.html | 595 KB | |
| qint_mod.html | 169 KB | |
| qbool.html | 57 KB | |
| openqasm.html | 44 KB | |

## Recommended Optimization Order

Based on benchmark and annotation data:

1. **mul_classical** - 31ms mean, likely Python loop overhead
2. **qint_preprocessed** - Largest annotation file, covers most operations
3. **qarray** - Second largest, affects array operations
4. **Comparison operations** - Moderate timing, room for improvement

## Decisions Made
- benchmark.pedantic with setup functions for operations that allocate new qubits (prevents qubit exhaustion)
- Simple benchmark mode for in-place operations (no allocation)
- CYTHON_DEBUG enables all three safety directives: boundscheck, wraparound, initializedcheck

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed benchmark qubit exhaustion**
- **Found during:** Task 3 (running benchmarks)
- **Issue:** Operations like `a + b` allocate new qubits; repeated iterations exhaust qubit pool
- **Fix:** Converted allocating operations to use benchmark.pedantic with setup functions that create fresh circuits
- **Files modified:** tests/benchmarks/test_qint_benchmark.py
- **Verification:** All 18 benchmarks pass, no MemoryError
- **Committed in:** 7077ca0

---

**Total deviations:** 1 auto-fixed (blocking issue)
**Impact on plan:** Essential fix for benchmark reliability. No scope creep.

## Issues Encountered
- cProfile cannot trace into Cython functions without QUANTUM_PROFILE build - profiling shows import time, not operation time. This is expected; use benchmarks for timing data.

## Next Phase Readiness
- Baseline metrics captured for optimization tracking
- CYTHON_DEBUG mode ready for debugging optimizations
- Primary optimization targets identified: mul_classical, qint_preprocessed.pyx
- Ready for Plan 02: Apply Cython optimizations to hot paths

---
*Phase: 57-cython-optimization*
*Completed: 2026-02-05*
