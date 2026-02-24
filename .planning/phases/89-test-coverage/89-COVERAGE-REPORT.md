# Phase 89: Test Coverage Report

**Date:** 2026-02-24
**Phase:** 89 - Test Coverage

## Coverage Summary

| Metric | Baseline (Phase 82) | Current (Phase 89) | Delta |
|--------|--------------------|--------------------|-------|
| Overall (Python) | 48.2% | 56% | +7.8% |

**Methodology:** Python-level coverage only (no Cython linetrace). Cython `.pyx` modules compiled without tracing; only pure Python `.py` files under `quantum_language/` measured. Consistent with Phase 82 methodology.

**Note:** Measurement excludes tests that cause segfaults (array/qarray tests, known Phase 87 issue). Coverage collected in batches to avoid segfault-induced data loss, then combined via `--cov-append`.

## Per-Module Coverage

| Module | Stmts | Miss | Cover | Change |
|--------|-------|------|-------|--------|
| `__init__.py` | 30 | 8 | 73% | -- |
| `_qarray_utils.py` | 47 | 23 | 51% | -- |
| `amplitude_estimation.py` | 187 | 139 | 26% | -- |
| `compile.py` | 621 | 228 | **63%** | improved |
| `diffusion.py` | 37 | 0 | **100%** | improved |
| `draw.py` | 200 | 200 | 0% | unchanged |
| `grover.py` | 140 | 14 | **90%** | improved |
| `oracle.py` | 203 | 35 | **83%** | improved |
| `profiler.py` | 28 | 16 | 43% | -- |
| `sim_backend.py` | 39 | 6 | **85%** | improved |
| `state/__init__.py` | 2 | 2 | 0% | unchanged |
| **TOTAL** | **1534** | **671** | **56%** | **+7.8%** |

## New Tests Added

| File | Tests | Covers |
|------|-------|--------|
| `test_nested_with_blocks.py` | 9 (3 pass, 6 xfail) | Nested quantum conditionals (TEST-03) |
| `test_circuit_reset.py` | 5 (5 pass) | Circuit state isolation (TEST-04) |
| `test_c_backend.py` | 6 (4 pass, 2 xfail) | C backend subprocess wrappers (TEST-05) |
| `test_cross_backend.py` | (modified) | xfail conversions for fixed bugs (TEST-06) |

## xfail Conversions

| Bug ID | Tests Converted | Status |
|--------|----------------|--------|
| BUG-CQQ-QFT (cqq_add) | 7 tests | Converted -- all widths 2-8 now pass |
| BUG-CQQ-QFT (cqq_mul) | 0 | Still xfail -- multiplication not fixed by Phase 86-02 |
| BUG-CQQ-QFT (ccq_mul) | 0 | Still xfail -- multiplication not fixed by Phase 86-02 |
| BUG-COND-MUL-01 | 0 | Already converted before Phase 89 |
| BUG-01 | 0 | Already had regression tests |
| BUG-02 | 0 | Already had regression tests |

## Key Findings

1. **Nested with-blocks unsupported:** `__enter__` performs `_control_bool &= self` which calls `__and__`, and controlled QQ AND is not implemented. Tests document this as xfail.
2. **C test compilation fixed:** The `tests/c/Makefile` had stale source dependencies from code changes in Phases 65-75. Fixed by expanding wildcards and adding missing source files.
3. **Pre-existing C test failures:** `test_comparison` and `test_hot_path_mul` have assertion failures unrelated to our changes.

## Top Uncovered Modules

1. `draw.py` -- 200 lines, 0% coverage (visualization module, no tests)
2. `amplitude_estimation.py` -- 139 missing lines, 26% coverage
3. `compile.py` -- 228 missing lines, 63% coverage (improved from ~18%)
4. `profiler.py` -- 16 missing lines, 43% coverage
5. `state/__init__.py` -- 2 lines, 0% coverage

## Measurement Command

```bash
# Batch 1: Core tests
pytest tests/python/test_nested_with_blocks.py tests/python/test_circuit_reset.py \
    tests/python/test_bug07_cond_mul.py tests/python/test_api_coverage.py \
    tests/python/test_ancilla_lifecycle.py \
    --cov=quantum_language --cov-report=term --tb=no -q \
    -k "not (test_array_creates_list_of_qint or test_qint_default_width or test_qarray or test_array_2d)" \
    -p no:Cython.Coverage

# Batch 2+: Additional tests with --cov-append
pytest tests/python/test_branch_superposition.py tests/python/test_bug01_32bit_mul.py \
    tests/python/test_bug02_qarray_imul.py \
    --cov=quantum_language --cov-append --cov-report= --tb=no -q -p no:Cython.Coverage

pytest tests/python/test_clifford_t_decomposition.py tests/python/test_clifford_t_hardcoded.py \
    tests/python/test_cython_optimization.py tests/python/test_decomposed_sequences.py \
    tests/python/test_diffusion.py tests/python/test_grover.py \
    tests/python/test_grover_predicate.py tests/python/test_mcx_decomposition.py \
    tests/python/test_openqasm_export.py tests/python/test_oracle.py \
    --cov=quantum_language --cov-append --cov-report= --tb=no -q -p no:Cython.Coverage

# Final report
python3 -m coverage report --show-missing
```
