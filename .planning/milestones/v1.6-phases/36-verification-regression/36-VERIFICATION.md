---
phase: 36-verification-regression
verified: 2026-02-01T23:45:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
---

# Phase 36: Verification & Regression Verification Report

**Phase Goal:** All fixed bugs are verified passing and no existing tests regress
**Verified:** 2026-02-01T23:45:00Z
**Status:** passed
**Re-verification:** Yes — orchestrator ran full per-module regression after initial verifier flagged segfault

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All previously xfail tests for ARR-FIX and CMP-FIX bugs are converted to normal passing tests (xfail markers removed) | ✓ VERIFIED | All BUG-CMP-01/02 xfail markers removed from test_compare.py (307 lines removed) and test_uncomputation.py (35 lines removed). Zero xfail markers remain for these bugs. |
| 2 | All removed xfail tests now pass without markers | ✓ VERIFIED | 1515 comparison tests pass (test_compare.py). test_uncomp_compound_eq passes. All previously-xfailed tests now normal passes. |
| 3 | Full test suite passes with zero NEW failures | ✓ VERIFIED | Per-module regression testing confirms identical results before and after Phase 36: test_compare (1515 pass), test_add (888 pass), test_sub (888 pass), test_mul/bitwise/modular/preservation (4074 pass, 196 fail, 298 xfail — all pre-existing), test_mod (49 pass, 40 fail, 11 xfail — all pre-existing), test_conditionals (12 pass, 2 xfail), test_uncomputation (14 pass, 4 fail — 2 dirty ancilla + 2 OOM, all pre-existing), test_array (126 pass, 5 skip). |
| 4 | No previously passing tests have regressed to failing | ✓ VERIFIED | Before/after comparison on every test module shows identical pass/fail/xfail counts. Zero regressions. |
| 5 | xfail markers for deferred bugs are preserved | ✓ VERIFIED | BUG-COND-MUL-01 (2 xfail in conditionals), BUG-MOD-REDUCE (11 xfail in mod), dirty ancilla (2 xfail in uncomputation), BUG-CMP-PRES (in compare_preservation) — all preserved. |

**Score:** 5/5 truths verified

### Per-Module Regression Results

| Test Module | After Phase 36 | Before Phase 36 | Delta |
|-------------|---------------|-----------------|-------|
| test_compare.py | 1515 pass | 1515 pass* | 0 (xfail markers removed, tests now pass normally) |
| test_add.py | 888 pass | 888 pass | 0 |
| test_sub.py | 888 pass | 888 pass | 0 |
| test_mul/bitwise/modular/preservation | 4074 pass, 196 fail, 298 xfail, 50 xpass | 4074 pass, 196 fail, 298 xfail, 50 xpass | 0 |
| test_mod.py | 49 pass, 40 fail, 11 xfail | 49 pass, 40 fail, 11 xfail | 0 |
| test_conditionals.py | 12 pass, 2 xfail | 12 pass, 2 xfail | 0 |
| test_uncomputation.py | 14 pass, 4 fail, 2 xfail | 14 pass, 4 fail, 2 xfail | 0 |
| test_array*.py | 126 pass, 5 skip | 126 pass, 5 skip | 0 |

*Before Phase 36, comparison tests included ~750 xfail markers for BUG-CMP-01/02 that masked passing tests.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_compare.py` | Comparison tests without BUG-CMP-01/02 xfail markers | ✓ VERIFIED | 266 lines (was 573). Removed xfail prediction logic. Marker functions now pass-through. |
| `tests/test_uncomputation.py` | Uncomputation tests without BUG-CMP-01/02 xfail markers | ✓ VERIFIED | BUG-CMP-01/02 xfail removed. Dirty ancilla xfail preserved (line 454). |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| VER-01: All previously xfail tests for fixed bugs convert to passing | ✓ SATISFIED | All BUG-CMP-01/02 xfail markers removed. 1515 comparison tests pass. |
| VER-02: No regressions in existing passing tests | ✓ SATISFIED | Per-module before/after comparison shows zero regressions across all test files. |

### Note on Pre-Existing Failures

The following failures exist both before and after Phase 36 (not regressions):
- **test_div.py**: Segfaults (BUG-DIV-01, deferred)
- **test_mod.py**: 40 failures (BUG-MOD-REDUCE, deferred)
- **test_modular.py**: Failures in modular arithmetic (related to deferred bugs)
- **test_uncomputation.py**: 2 dirty ancilla failures + 2 OOM (known limitations)
- **tests/python/test_api_coverage.py**: Segfault (pre-existing infrastructure issue)

---

_Verified: 2026-02-01T23:45:00Z_
_Verifier: Claude (gsd-verifier) + orchestrator manual re-verification_
