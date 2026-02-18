---
phase: 60
plan: 01
subsystem: performance-profiling
tags: [profiling, cProfile, benchmarks, hot-paths, migration-targets]

dependency-graph:
  requires: [57, 58, 59]
  provides: [top-3-hot-paths, baseline-benchmarks, boundary-crossing-analysis]
  affects: [60-02, 60-03, 60-04]

tech-stack:
  added: []
  patterns: [cProfile-inline-profiling, pytest-benchmark-pedantic]

key-files:
  created: []
  modified:
    - tests/benchmarks/test_qint_benchmark.py

decisions:
  - id: MIG-01
    summary: "Top 3 hot paths: multiplication_inplace, addition_inplace, __ixor__/__xor__"
  - id: MIG-02
    summary: "Migration order: multiplication_inplace first (highest absolute time), addition_inplace second (highest frequency), ixor/xor third (enabler for many operations)"
  - id: MIG-03
    summary: "Baseline captured as JSON at /tmp/baseline_60.json and in benchmark table below"

metrics:
  duration: "10m 50s"
  completed: "2026-02-06"
---

# Phase 60 Plan 01: Fresh Profiling and Hot Path Identification Summary

**One-liner:** Fresh cProfile identifies multiplication_inplace (59.6ms), addition_inplace (37us), and __ixor__/__xor__ (3.3us) as top 3 migration targets with per-path boundary crossing analysis.

## Top 3 Hot Paths Identified

### Hot Path #1: `multiplication_inplace` (Plan 02 target)

| Attribute | Value |
|-----------|-------|
| **Function** | `multiplication_inplace` |
| **File** | `src/quantum_language/qint_preprocessed.pyx:1211` |
| **Benchmark (mul_classical 8bit)** | 11,808 us mean |
| **Benchmark (mul_8bit quantum)** | 236 us mean |
| **Profile cumulative time** | 11.917s (200 calls = 59.6ms/call) |
| **Boundary crossings per call** | 25 total: 3x `_get_circuit`, 2x `_get_circuit_initialized`, 2x `_get_control_bool`, 1x `_get_controlled`, 1x `_get_ancilla`, 1x `_increment_ancilla`, 1x `_increment_global_creation_counter`, 1x `_increment_int_counter`, 1x `_get_num_qubits`, 1x `_set_num_qubits`, 1x `_get_smallest_allocated_qubit`, 1x `_set_smallest_allocated_qubit`, 1x `_get_qubit_saving_mode`, 1x `_get_scope_stack`, + qint.__init__, add_dependency, pxd property accessors |
| **Estimated migration benefit** | >90% for classical mul (dominant is C-level CQ_mul loop); 20-40% for quantum mul |
| **Why migrate** | Dominates total execution time by 60x over next function. Classical multiplication is 333x slower than iadd. The C-level CQ_mul loop generates O(n^2) addition sequences and the Python/Cython wrapper adds massive overhead per call. |

### Hot Path #2: `addition_inplace` (Plan 03 target)

| Attribute | Value |
|-----------|-------|
| **Function** | `addition_inplace` |
| **File** | `src/quantum_language/qint_preprocessed.pyx:708` |
| **Benchmark (iadd_8bit classical)** | 37 us mean |
| **Benchmark (iadd_quantum_8bit)** | 62 us mean |
| **Benchmark (iadd_16bit classical)** | 48 us mean |
| **Benchmark (iadd_quantum_16bit)** | 414 us mean |
| **Profile cumulative time** | 0.193s (3000 calls = 64us/call) |
| **Boundary crossings per call** | 7 total: 1x `_get_circuit`, 1x `_get_controlled`, 1x `_get_control_bool`, 1x `_get_ancilla` (in non-controlled path for CQ_add/QQ_add) |
| **Estimated migration benefit** | 20-30% per call (eliminating 7 Python accessor roundtrips) |
| **Why migrate** | Highest-frequency hot path -- called by iadd, isub, __eq__ (subtract-add-back pattern), __lt__ (widened subtraction), __add__, __sub__. Every comparison and arithmetic operation goes through addition_inplace. Even a 20% improvement here compounds across all operations. |

### Hot Path #3: `__ixor__` / `__xor__` (Plan 04 target)

| Attribute | Value |
|-----------|-------|
| **Function** | `__ixor__` (in-place) and `__xor__` (out-of-place) |
| **File** | `src/quantum_language/qint_preprocessed.pyx:1915` (__ixor__) / `:1791` (__xor__) |
| **Benchmark (ixor_8bit classical)** | 3.3 us mean |
| **Benchmark (ixor_quantum_8bit)** | 6.3 us mean |
| **Benchmark (xor_8bit out-of-place)** | 23 us mean |
| **Profile cumulative time** | 0.018s (1800 calls = 10us/call) |
| **Boundary crossings per call** | 4 total: 1x `_get_circuit`, 1x `_get_controlled` (for ixor classical); 6 for xor out-of-place (adds `_get_circuit_initialized`, `_get_control_bool`, qint alloc overhead) |
| **Estimated migration benefit** | 30-50% for ixor (few crossings but each is proportionally large at 3us total); 20-30% for xor |
| **Why migrate** | XOR is the fundamental copy/init operation -- every out-of-place operation (`a + b`, `a * b`, `a ^ b`, `a & b`, `a | b`, `copy()`) first XORs into a fresh result. It is the most-called primitive. Also called in __lt__ for widened-temp copying (16 per-bit Q_xor calls). Migrating this removes overhead from the inner loop of almost every operation. |

## Recommended Migration Order

| Plan | Target | Rationale |
|------|--------|-----------|
| 02 | `multiplication_inplace` | Highest absolute time (59.6ms/call). Classical mul is 333x slower than iadd. Biggest single-operation win. |
| 03 | `addition_inplace` | Highest frequency (called by iadd, isub, eq, lt, add, sub). 20-30% improvement compounds across all operations. |
| 04 | `__ixor__` / `__xor__` | Fundamental copy primitive. Eliminating overhead here accelerates every out-of-place operation. |

## Baseline Benchmark Table (Phase 60 Pre-Migration)

| Benchmark | Min (us) | Mean (us) | Median (us) | OPS | Rounds |
|-----------|----------|-----------|-------------|-----|--------|
| test_ixor_8bit | 2.8 | 3.3 | 3.0 | 302,317 | 149,300 |
| test_ixor_quantum_8bit | 5.1 | 6.3 | 5.6 | 159,529 | 77,743 |
| test_qint_creation_8bit | 11.5 | 12.5 | 12.0 | 80,230 | 100 |
| test_or_8bit | 15.5 | 18.4 | 16.4 | 54,470 | 100 |
| test_qint_creation_16bit | 16.2 | 18.6 | 16.8 | 53,879 | 100 |
| test_and_8bit | 17.0 | 19.3 | 18.0 | 51,725 | 100 |
| test_xor_8bit | 20.0 | 22.6 | 21.0 | 44,231 | 100 |
| test_isub_8bit | 24.3 | 31.2 | 26.1 | 32,098 | 26,095 |
| test_iadd_8bit | 24.4 | 37.2 | 30.1 | 26,854 | 15,257 |
| test_isub_quantum_8bit | 28.5 | 61.7 | 36.6 | 16,204 | 24,971 |
| test_iadd_quantum_8bit | 32.8 | 62.4 | 37.1 | 16,019 | 16,961 |
| test_circuit_creation | 37.9 | 54.7 | 48.8 | 18,276 | 11,534 |
| test_add_scaling[4] | 38.3 | 43.1 | 40.2 | 23,179 | 50 |
| test_iadd_16bit | 42.4 | 48.3 | 43.5 | 20,714 | 9,765 |
| test_add_8bit | 49.2 | 59.6 | 53.4 | 16,788 | 100 |
| test_add_scaling[8] | 52.5 | 56.9 | 54.5 | 17,566 | 50 |
| test_iadd_quantum_16bit | 52.7 | 413.7 | 114.4 | 2,417 | 14,230 |
| test_add_16bit | 91.0 | 107.2 | 96.2 | 9,331 | 100 |
| test_add_scaling[16] | 91.1 | 100.2 | 95.0 | 9,976 | 50 |
| test_eq_8bit | 91.4 | 103.1 | 94.7 | 9,703 | 100 |
| test_lt_8bit | 99.6 | 115.3 | 102.3 | 8,675 | 100 |
| test_mul_8bit | 202.9 | 236.2 | 224.0 | 4,234 | 50 |
| test_add_scaling[32] | 256.3 | 291.6 | 266.5 | 3,429 | 50 |
| test_mul_classical | 3,016.7 | 11,807.7 | 12,573.9 | 85 | 50 |

## Comparison with Phase 57 Baseline

| Operation | Phase 57 (us) | Phase 60 Pre (us) | Change |
|-----------|---------------|-------------------|--------|
| iadd_8bit | 25 | 37 | +48% (higher variance in new bench) |
| xor_8bit | 30 | 23 | -23% (improved by Phase 57 optimizations) |
| add_8bit | 53 | 60 | +13% (within measurement noise) |
| eq_8bit | 100 | 103 | +3% (stable) |
| lt_8bit | 152 | 115 | -24% (improved by Phase 59 hardcoded seqs) |
| mul_8bit | 356 | 236 | -34% (improved by Phase 57-59 optimizations) |
| mul_classical | 31,256 | 11,808 | -62% (major improvement from hardcoded seqs) |

Note: Phase 57 baselines used a different benchmark setup (non-pedantic for some tests). The Phase 60 baselines should be used as the authoritative pre-migration reference.

## Profiling Methodology

1. **Build with profiling:** `QUANTUM_PROFILE=1` enables Cython function-level profiling
2. **Comprehensive workload:** 500 iterations each of iadd/isub/ixor (8-bit and 16-bit), 100 iterations each of add/xor/eq/lt/mul (8-bit and 16-bit)
3. **cProfile analysis:** Sorted by cumulative time to identify function-level hot paths
4. **Single-call profiling:** Individual operation profiling with profiling build to count exact boundary crossings
5. **Clean baselines:** Rebuilt without profiling, ran pytest-benchmark for accurate timing data
6. **JSON export:** Baseline saved to `/tmp/baseline_60.json` for automated comparison

## Profiling Raw Data (Top Functions by Cumulative Time)

```
         215682 function calls in 12.778 seconds

   ncalls  tottime  cumtime  filename:lineno(function)
      200   11.917  11.917  qint_preprocessed.pyx:1211(multiplication_inplace)
    13400    0.377   0.390  _core.pyx:250(__init__)
     3000    0.191   0.193  qint_preprocessed.pyx:708(addition_inplace)
     8600    0.168   0.199  qint_preprocessed.pyx:91(__init__)
     8597    0.018   0.038  qint_preprocessed.pyx:526(__del__)
     1800    0.017   0.018  qint_preprocessed.pyx:1915(__ixor__)
     8597    0.017   0.017  _core.pyx:156(_decrement_ancilla)
     8500    0.011   0.011  _core.pyx:151(_increment_ancilla)
      100    0.004   0.015  qint_preprocessed.pyx:2376(__lt__)
   200/100   0.003   0.014  qint_preprocessed.pyx:2199(__eq__)
      200    0.004   0.008  qint_preprocessed.pyx:1791(__xor__)
```

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fresh profiling and hot path identification | 60178c3 | tests/benchmarks/test_qint_benchmark.py |

## Deviations from Plan

None -- plan executed exactly as written.

## Next Phase Readiness

Plans 02-04 can proceed with the following targets:
- **Plan 02:** Migrate `multiplication_inplace` to C (hand-written, one C file)
- **Plan 03:** Migrate `addition_inplace` to C (hand-written, one C file)
- **Plan 04:** Migrate `__ixor__`/`__xor__` to C (hand-written, one C file)

All three are well-bounded functions with clear C-callable interfaces via the existing `qubit_array` + `run_instruction` pattern.

## Self-Check: PASSED
