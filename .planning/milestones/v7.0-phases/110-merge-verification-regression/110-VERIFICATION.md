---
phase: 110-merge-verification-regression
verified: 2026-03-07T12:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 7/7
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 110: Merge Verification & Regression -- Verification Report

**Phase Goal:** Prove merge infrastructure produces correct results at all opt levels and causes no regressions.
**Verified:** 2026-03-07T12:00:00Z
**Status:** passed
**Re-verification:** Yes -- confirming previous passed status

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | opt=2 add circuit produces identical statevector to opt=3 for all input pairs at widths 1-4 | VERIFIED | test_add_equiv parametrized at widths [1,2,3,4] with exhaustive pairs; _statevectors_equivalent with global phase normalization (lines 103-127 of test_merge_equiv.py) |
| 2 | opt=2 mul circuit produces identical statevector to opt=3 for all input pairs at widths 1-4 | VERIFIED | test_mul_equiv parametrized at widths [1,2,3,4] with exhaustive pairs (lines 130-155) |
| 3 | opt=2 grover oracle circuit produces identical statevector to opt=3 | VERIFIED | test_grover_oracle_equiv uses x==5 predicate, width=4, 7 qubits (lines 158-177) |
| 4 | parametric=True works at opt=1 and opt=3, raises ValueError at opt=2 | VERIFIED | TestParametricOptInteraction: test_parametric_opt1_works (line 188), test_parametric_opt3_works (line 224), test_parametric_opt2_raises with pytest.raises(ValueError) (line 254) |
| 5 | Existing compile tests pass at all opt levels via selective opt_safe decorator | VERIFIED | test_compile.py defines opt_safe at line 48; @opt_safe applied to 29 behavioral tests; non-behavioral tests run at default only (plan 03 refinement to avoid OOM) |
| 6 | All 29 existing merge tests pass at opt=1, opt=2, and opt=3 | VERIFIED | test_merge.py line 23: pytestmark = pytest.mark.usefixtures("opt_level") -- all tests run at all 3 levels |
| 7 | Pre-existing xfail tests remain xfail at all opt levels with no new failures | VERIFIED | 15 pre-existing failures unchanged; selective opt_level application prevents false inflation |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/python/test_merge_equiv.py` | Statevector equivalence tests and parametric+opt interaction tests (min 120 lines) | VERIFIED | 265 lines. Contains _statevectors_equivalent helper (line 32), _get_statevector helper (line 53), test_add_equiv (line 104), test_mul_equiv (line 131), test_grover_oracle_equiv (line 158), TestParametricOptInteraction with 3 tests (line 185). No TODOs or placeholders. |
| `tests/conftest.py` | opt_level fixture that monkeypatches ql.compile default opt | VERIFIED | opt_level fixture at line 167, parametrized over [1,2,3], patches _compile_mod.compile and ql.compile (lines 194-195), skips opt=2 for parametric=True (line 190). _gc_between_tests autouse fixture at line 154. |
| `tests/test_compile.py` | Wired to opt_level fixture via selective @opt_safe | VERIFIED | opt_safe = pytest.mark.usefixtures("opt_level") at line 48; @opt_safe applied to behavioral test functions. |
| `tests/python/test_merge.py` | Wired to opt_level fixture | VERIFIED | pytestmark = pytest.mark.usefixtures("opt_level") at line 23. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| test_merge_equiv.py | quantum_language.compile | @ql.compile(opt=N) decorator | WIRED | Pattern `ql.compile(opt=opt_level)` at lines 114, 142, 166 |
| test_merge_equiv.py | qiskit.quantum_info.Statevector | Statevector.from_instruction | WIRED | Used at lines 72, 213, 248 for statevector extraction |
| conftest.py opt_level | quantum_language.compile | monkeypatch ql.compile | WIRED | Patches both _compile_mod.compile and ql.compile at lines 194-195 |
| test_compile.py | conftest.py opt_level | opt_safe usefixtures | WIRED | Line 48 defines opt_safe; applied to behavioral test functions |
| test_merge.py | conftest.py opt_level | pytestmark usefixtures | WIRED | Line 23: pytestmark = pytest.mark.usefixtures("opt_level") |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MERGE-04 | 110-01, 110-02, 110-03 | Merged result verified equivalent to sequential execution via Qiskit simulation | SATISFIED | Statevector equivalence proven for add/mul/grover (plan 01); full regression at all opt levels (plan 02); OOM fix and selective opt_level (plan 03). Marked complete in REQUIREMENTS.md line 81. |

No orphaned requirements. MERGE-04 is the only requirement mapped to Phase 110 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected in any phase artifact |

### Human Verification Required

No items require human verification. All phase behaviors are fully automated via pytest with statevector comparison and regression counting. No visual, real-time, or external service dependencies.

### Gaps Summary

No gaps found. All 7 observable truths verified against the actual codebase. All 4 artifacts exist, are substantive (no stubs), and are properly wired. MERGE-04 is fully satisfied. No regressions from previous verification.

---

_Verified: 2026-03-07T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
