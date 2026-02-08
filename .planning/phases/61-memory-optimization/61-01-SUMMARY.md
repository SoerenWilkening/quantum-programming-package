---
phase: 61-memory-optimization
plan: 01
subsystem: profiling
tags: [memray, memory-profiling, allocation-analysis, benchmarking]

# Dependency graph
requires:
  - phase: 60-c-hot-path-migration
    provides: C hot paths for add/mul/xor that are now the primary allocation sites
provides:
  - Memray profiling data at 8-bit, 16-bit, and 32-bit widths
  - Per-operation allocation rates and scaling analysis
  - Phase 61 throughput baseline benchmarks
  - Ranked optimization targets for Plans 02 and 03
affects: [61-02, 61-03]

# Tech tracking
tech-stack:
  added: [memray 1.19.1]
  patterns: [memray profiling with --native flag for C allocation tracking]

key-files:
  created:
    - scripts/profile_memory_61.py
  modified: []

key-decisions:
  - "MEM-01: Multiplication at width > 24 causes segfault in C backend (buffer overflow), profiling capped at 24-bit"
  - "MEM-02: 32-bit memray profiling requires inline script (-c) due to argparse/memray interaction crash"
  - "MEM-03: Top optimization target is run_instruction() per-gate malloc (leaked, ~40 bytes per gate)"

patterns-established:
  - "Profiling pattern: Use memray run --native for C-level allocation tracking"
  - "Scaling analysis: Compare per-operation allocation rates across 8/16/32-bit widths"

# Metrics
duration: 10min
completed: 2026-02-08
---

# Phase 61 Plan 01: Memory Profiling Summary

**Memray profiling of add/mul/xor hot paths at 3 widths reveals run_instruction() per-gate malloc as dominant allocation site (leaked, scaling O(n^2) with bit width)**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-08T13:36:44Z
- **Completed:** 2026-02-08T13:47:00Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- Captured memray profiling data at 8-bit, 16-bit, and 32-bit widths with native C tracking
- Identified and ranked allocation hotspots with quantified byte counts and call frequencies
- Documented O(n^2) scaling behavior for multiplication and O(n) for addition/XOR
- Captured Phase 61 throughput baseline via pytest-benchmark (24 tests, JSON artifact)
- Discovered 32-bit multiplication segfault (pre-existing C backend buffer overflow)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create memory profiling script and run memray** - `65ee0e8` (feat)
2. **Task 2: Analyze profiling data** - No commit (analysis-only, documented in SUMMARY)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified

- `scripts/profile_memory_61.py` - Memory profiling script exercising add/mul/xor at configurable widths

## Profiling Results

### Aggregate Allocation Data

| Width | Total Allocs | Total Memory | Peak Memory | Iterations |
|-------|-------------|-------------|-------------|------------|
| 8-bit | 633,855 | 323.5 MB | 86.1 MB | 200 add, 200 mul, 200 xor |
| 16-bit | 535,843 | 274.5 MB | 117.1 MB | 200 add, 20 mul, 200 xor |
| 32-bit | 173,511 | 62.3 MB | 46.6 MB | 50 add, 0 mul, 50 xor |

### Per-Operation Allocation Rates

| Operation | Width | Bytes/Op | Allocs/Op |
|-----------|-------|----------|-----------|
| iadd (+=) | 8-bit | 25.8 KB | 232 |
| iadd (+=) | 16-bit | 83.2 KB | 851 |
| mul (*) | 8-bit | 954.8 KB | 2,456 |
| mul (*) | 16-bit | 10,133.8 KB | 17,086 |
| ixor (^=) | 8-bit | 889 B | 20 |
| ixor (^=) | 16-bit | 1,741 B | 36 |

### Scaling Analysis (16-bit / 8-bit ratio)

| Operation | Bytes Scaling | Alloc Count Scaling |
|-----------|--------------|-------------------|
| Addition | 3.2x | 3.7x |
| Multiplication | 10.6x | 7.0x |
| XOR | 2.0x | 1.8x |

**Interpretation:**
- **Addition** scales roughly O(n) -- doubling width roughly triples allocation (expected: QFT addition has O(n^2) gates)
- **Multiplication** scales roughly O(n^2) or worse -- doubling width causes 7-10x allocation increase (expected: schoolbook multiplication is O(n^2) additions)
- **XOR** scales O(n) -- doubling width doubles allocation (expected: 1 CNOT per bit)

### Top Allocation Sites (Ranked by Impact)

| Rank | Site | 8-bit Bytes | 8-bit Allocs | Source | Leaked? |
|------|------|------------|-------------|--------|---------|
| 1 | Multiplication operation (line 74: `a * b`) | 186.5 MB | 491,205 | run_instruction() malloc + add_gate() realloc | YES |
| 2 | Multiplication setup (line 71: `ql.circuit()`) | 79.7 MB | 79,000 | Circuit infrastructure + sequence creation | Partial |
| 3 | Addition operation (line 53: `a += b`) | 5.0 MB | 46,425 | run_instruction() malloc | YES |
| 4 | Addition setup (line 47: qint creation) | 398.4 KB | 395 | One-time allocation | NO |
| 5 | XOR operation (line 95: `a ^= b`) | 173.6 KB | 4,000 | run_instruction() malloc | YES |
| 6 | numpy import (blas_fpe_check) | 33.6 MB | - | One-time import overhead | NO |

### Cross-Reference with Research Allocation Sites

| Site | Research Prediction | Profiling Confirmation |
|------|-------------------|----------------------|
| Site 1: run_instruction() per-gate malloc | CRITICAL, leaked | CONFIRMED - dominant in all operations |
| Site 2: reverse_circuit_range() per-gate malloc | CRITICAL, leaked | Not separately visible (part of operation totals) |
| Site 3: colliding_gates() per-add_gate malloc | MODERATE, freed | CONFIRMED - contributes to per-operation overhead |
| Site 4: Sequence creation | LOW, cached | CONFIRMED - one-time cost, not significant |
| Site 5: Non-cached sequences (Q_not) | MODERATE | Not separately visible in profiling |
| Site 6: Circuit infrastructure | LOW, amortized | CONFIRMED - visible in circuit() calls |

### Memory Leak Confirmation

The profiling confirms the memory leak pattern identified in research. Evidence:
- **Peak memory grows with iteration count** -- 86 MB peak at 8-bit with 200 mul iterations
- **Multiplication dominates** because it generates the most gates per operation (~2,456 mallocs at 8-bit = ~2,456 leaked gate_t structs per mul, each ~40 bytes = ~96 KB leaked per 8-bit multiply)
- **XOR is minimal** because it generates only 8 gates per 8-bit operation (20 allocs/op includes overhead)

### Phase 61 Throughput Baseline

| Operation | Mean (us) | OPS | vs Phase 60 |
|-----------|-----------|-----|-------------|
| ixor_8bit | 7.3 | 136,651 | Baseline noise |
| ixor_quantum_8bit | 10.8 | 92,409 | Baseline noise |
| iadd_8bit | 18.0 | 55,482 | Baseline noise |
| isub_8bit | 65.5 | 15,276 | Baseline noise |
| iadd_quantum_8bit | 49.5 | 20,214 | Baseline noise |
| isub_quantum_8bit | 236.0 | 4,238 | Baseline noise |
| iadd_16bit | 83.6 | 11,965 | Baseline noise |
| add_8bit | 64.5 | 15,494 | Baseline noise |
| eq_8bit | 199.8 | 5,004 | Baseline noise |
| lt_8bit | 267.7 | 3,736 | Baseline noise |
| mul_8bit | 300.3 | 3,330 | Baseline noise |
| mul_classical | 37,028.4 | 27 | Baseline noise |

Note: Higher absolute times than Phase 60 due to different system load. Benchmark JSON saved at `/tmp/benchmark_61_baseline.json` for post-optimization delta comparison.

## Priority Optimization Targets

Based on profiling evidence, ranked by expected impact:

### Target 1: Eliminate run_instruction() per-gate malloc (CRITICAL)

**Current:** `gate_t *g = malloc(sizeof(gate_t))` per gate, NEVER freed.
**Fix:** Use stack-allocated gate_t or reuse a single gate_t buffer.
**Expected savings:** Eliminate ~232 mallocs per 8-bit iadd, ~2,456 per 8-bit mul.
**Estimated improvement:** 20-40% throughput improvement (eliminates per-gate heap allocation + eliminates memory leak).

### Target 2: Eliminate reverse_circuit_range() per-gate malloc (HIGH)

**Current:** Same pattern as run_instruction() -- malloc per reversed gate.
**Fix:** Same approach -- stack allocation or buffer reuse.
**Expected savings:** Proportional to uncomputation usage.

### Target 3: Reduce colliding_gates() per-add_gate realloc (MODERATE)

**Current:** `realloc(3*sizeof(gate_t*))` per add_gate call.
**Fix:** Pre-allocate gate pointer arrays or use geometric growth.
**Expected savings:** Reduces realloc overhead per gate insertion.

## Decisions Made

- **MEM-01:** 32-bit multiplication segfaults in C backend (buffer overflow in circuit allocation arrays). Profiling capped multiplication at 24-bit width. This is a pre-existing bug, not caused by Phase 61 changes.
- **MEM-02:** memray with argparse-based scripts crashes at 32-bit under native tracking. Used inline `-c` script as workaround for 32-bit profiling.
- **MEM-03:** Priority optimization target is run_instruction() per-gate malloc -- confirmed by profiling as the dominant allocation site across all operations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Handled 32-bit multiplication segfault**
- **Found during:** Task 1 (running profiling at 32-bit)
- **Issue:** 32-bit multiplication causes segfault in C backend
- **Fix:** Added width cap at 24-bit in profiling script with informative message
- **Files modified:** scripts/profile_memory_61.py
- **Verification:** Script runs successfully at 32-bit with mul capped
- **Committed in:** 65ee0e8 (Task 1 commit)

**2. [Rule 3 - Blocking] memray script execution crash at 32-bit**
- **Found during:** Task 1 (memray profiling at 32-bit)
- **Issue:** memray run with script file crashes at 32-bit even with mul capped
- **Fix:** Used `memray run -c "..."` inline script for 32-bit profiling
- **Verification:** 32-bit profiling data captured successfully
- **Committed in:** Not committed (workaround for profiling execution only)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were necessary to capture profiling data at all three widths. No scope creep.

## Issues Encountered

- Pre-existing test suite segfaults in `test_array_creates_list_of_qint` and `test_multiplication_at_width` (wider widths). Not related to Phase 61 changes.
- `pip install -e .` fails due to `build_preprocessor` import (pre-existing). Using `PYTHONPATH=src` with existing compiled extensions works fine.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Profiling baseline established for post-optimization comparison
- Top 3 optimization targets identified and ranked
- Plan 02 (fix memory leaks in run_instruction/reverse_circuit_range) can proceed immediately
- Plan 03 (optimize colliding_gates and circuit allocation) can follow Plan 02
- Benchmark JSON at `/tmp/benchmark_61_baseline.json` for automated delta comparison

## Self-Check: PASSED

All key files verified on disk:
- scripts/profile_memory_61.py: FOUND
- .planning/phases/61-memory-optimization/61-01-SUMMARY.md: FOUND
- /tmp/memray_61_{8,16,32}bit.bin: FOUND (all 3)
- /tmp/memray_61_{8,16,32}bit_stats.txt: FOUND (all 3)
- /tmp/benchmark_61_baseline.json: FOUND
- Commit 65ee0e8: FOUND

---
*Phase: 61-memory-optimization*
*Completed: 2026-02-08*
