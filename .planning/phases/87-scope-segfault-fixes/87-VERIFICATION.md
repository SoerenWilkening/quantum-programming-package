---
phase: 87-scope-segfault-fixes
verification-date: 2026-02-24
result: PASSED
---

# Phase 87: Scope & Segfault Fixes - Verification

## Success Criteria Check

### Criterion 1: 32-bit multiplication completes without segfault (BUG-01)
**Status: PASSED**
- MAXLAYERINSEQUENCE increased from 10,000 to 300,000 in `c_backend/include/types.h`
- 32-bit multiplication generates circuit without segfault (13/13 tests pass)
- 16-bit and 8-bit multiplication also verified
- 4-bit simulation correctness verified (3 * 2 = 6)
- All widths 1-8 tested parametrically
- Test file: `tests/python/test_bug01_32bit_mul.py` (13 tests)
- Commit: `dca9d98`

### Criterion 2: qarray *= scalar executes without crashing for widths 1-8 (BUG-02)
**Status: PASSED**
- Root cause: MAXLAYERINSEQUENCE overflow (resolved by BUG-01 fix)
- Defensive guard added in `__imul__`: sets `_is_uncomputed=True` and `allocated_qubits=False` on swapped-out result_qint
- Single-element qarray *= 2 tested at widths 1-8
- Multi-element qarray *= 2 tested at widths 1-4
- Simulation correctness verified at widths 3-4
- 6 skip markers removed from test_qarray_elementwise.py, test_qarray_mutability.py, test_api_coverage.py
- Test file: `tests/python/test_bug02_qarray_imul.py` (25 tests)
- Commit: `83ba3f2`

### Criterion 3: Controlled multiplication produces correct results (BUG-07)
**Status: PASSED**
- Scope depth bypass in `__mul__`/`__rmul__`: temporarily sets `current_scope_depth` to 0 during result qint creation
- Prevents result register from being registered in scope frame, avoiding uncomputation by `__exit__`
- Controlled in-place multiplication (cond=True): result *= 2 produces correct value 2
- Controlled in-place multiplication (cond=False): result stays 0 (fresh register, no gates fire)
- Controlled out-of-place multiplication: a * b inside with block produces correct result
- 13 test workarounds removed (6 from test_toffoli_multiplication.py, 7 from test_cross_backend.py)
- xfail markers removed from test_conditionals.py conditional mul tests
- All 21 Toffoli multiplication tests pass without workarounds
- Test file: `tests/python/test_bug07_cond_mul.py` (7 tests)
- Commit: `1e7f971`

### Criterion 4: BUG-MOD-REDUCE (BUG-09) explicitly deferred with rationale
**Status: PASSED**
- BUG-09 marked as `[-]` (explicitly deferred) in REQUIREMENTS.md
- Traceability table updated: BUG-09 -> "Future (Beauregard redesign)" / "Explicitly deferred"
- Detailed rationale added to Future Requirements section explaining why Beauregard-style algorithm redesign is needed
- Commit: `74525ed`

## Test Results Summary

| Test Suite | Result |
|-----------|--------|
| test_bug01_32bit_mul.py | 13/13 passed |
| test_bug02_qarray_imul.py | 25/25 passed |
| test_bug07_cond_mul.py | 7/7 passed |
| test_toffoli_multiplication.py | 21/21 passed |
| test_conditionals.py (TestCondMul) | 2/2 passed |

## Pre-existing Failures (NOT regressions)

- test_conditionals.py: 7 non-multiplication tests fail due to pre-existing `verify_circuit` fixture extraction issue (bitstring[:width] doesn't account for qubit allocation offsets). These are unrelated to Phase 87 changes.

## Plan Completion

| Plan | Description | Commit | Status |
|------|------------|--------|--------|
| 87-01 | MAXLAYERINSEQUENCE increase | `dca9d98` | Complete |
| 87-02 | BUG-09 deferral docs | `74525ed` | Complete |
| 87-03 | qarray *= fix | `83ba3f2` | Complete |
| 87-04 | Controlled mul scope fix | `1e7f971` | Complete |

## Verdict

**PASSED** - All 4 success criteria met. No crashes at valid operation widths and controlled multiplication produces correct results.

---
*Phase: 87-scope-segfault-fixes*
*Verified: 2026-02-24*
