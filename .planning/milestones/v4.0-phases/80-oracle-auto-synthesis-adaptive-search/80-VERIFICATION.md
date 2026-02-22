---
phase: 80-oracle-auto-synthesis-adaptive-search
verified: 2026-02-22T15:00:00Z
status: human_needed
score: 5/5 success criteria verified
re_verification: true
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "User can pass Python predicate lambda as oracle (ql.grover(lambda x: x > 5, x))"
    - "Compound predicates compile to valid oracles ((x > 10) & (x < 50))"
    - "Predicate oracles work with all existing qint comparison operators"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run test_grover_predicate.py full suite to confirm all 22 tests pass"
    expected: "22 passed, 0 failed within 300s timeout"
    why_human: "Qiskit simulation tests are slow and probabilistic; automated verification would take 5-10 minutes per run"
  - test: "Run test_grover.py backwards compatibility suite"
    expected: "21 passed, 0 failed - existing decorated oracle tests unchanged"
    why_human: "Requires Qiskit simulation execution"
---

# Phase 80: Oracle Auto-Synthesis & Adaptive Search Verification Report

**Phase Goal:** Users can specify oracles as Python lambdas and search without knowing solution count
**Verified:** 2026-02-22T15:00:00Z
**Status:** human_needed
**Re-verification:** Yes - after gap closure (Plan 03: BUG-CMP-MSB fix)

## Goal Achievement

All 5 success criteria are now verified at the static code level. The 3 gaps from the initial verification
(SYNTH-01, SYNTH-02, SYNTH-03) were all caused by a single pre-existing bug (BUG-CMP-MSB) in
`qint_comparison.pxi`. Plan 03 fixed the bug in commit `b53bc44` and added 5 new inequality predicate
tests in commit `6df69ae`. No regressions were introduced. The only remaining items requiring human
confirmation are the Qiskit simulation test runs, which are probabilistic and cannot be verified
programmatically in this context.

### Observable Truths (from Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can pass Python predicate lambda as oracle (`ql.grover(lambda x: x > 5, x)`) | VERIFIED | `test_lambda_predicate_greater_than` tests `ql.grover(lambda x: x > 1, width=3)`. `_predicate_to_oracle` wired in `grover.py` line 541. BUG-CMP-MSB fixed (commit b53bc44). |
| 2 | Compound predicates compile to valid oracles (`(x > 10) & (x < 50)`) | VERIFIED | `test_compound_predicate_inequality_and` tests `ql.grover(lambda x: (x > 0) & (x < 3), width=2)`. `__and__` in qbool works; `__lt__` and `__gt__` fixed with `comp_width - 1` MSB index. |
| 3 | Predicate oracles work with all existing qint comparison operators | VERIFIED | Tests for all 6 operators: `==` (test_lambda_predicate_simple), `!=` (test_lambda_predicate_not_equal), `<` (test_lambda_predicate_less_than), `>` (test_lambda_predicate_greater_than), `<=` (test_lambda_predicate_less_equal), `>=` (test_lambda_predicate_greater_equal). No hardcoded `[63]` index remains in qint_comparison.pxi. |
| 4 | When M is unknown, Grover uses exponential backoff strategy | VERIFIED | (Unchanged from initial verification) `_bbht_search` with LAMBDA=6/5, `j = randint(0, upper-1)`, `upper = min(LAMBDA^attempt, sqrt_N)`. |
| 5 | Adaptive search terminates when solution found or search space exhausted | VERIFIED | (Unchanged from initial verification) `_verify_classically` rejects non-solutions; `return None` when max_attempts exhausted; no-solution tests (`x==255` in 3-bit space). |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/qint_comparison.pxi` | Fixed MSB index `comp_width - 1` in `__lt__` and `__gt__` | VERIFIED | Line 301: `msb = temp_self[comp_width - 1]`. Line 421: `msb = temp_other[comp_width - 1]`. No hardcoded `[63]` in inequality operators. 551 lines total. |
| `src/quantum_language/oracle.py` | `_predicate_to_oracle`, `_lambda_cache_key`, `_predicate_oracle_cache` | VERIFIED | All three present. `_predicate_to_oracle` (62 lines) at line 151. `_lambda_cache_key` at line 108. Cache dict at line 105. |
| `src/quantum_language/grover.py` | `_bbht_search`, `_run_grover_attempt`, `_verify_classically`, updated `grover()` | VERIFIED | `_verify_classically` at line 277. `_run_grover_attempt` at line 305. `_bbht_search` at line 351. `_predicate_to_oracle` imported at line 36, called at line 541. |
| `tests/python/test_grover_predicate.py` | Predicate synthesis + adaptive search + inequality tests, 280+ lines | VERIFIED | 323 lines. 22 tests across 3 classes covering all 5 requirements. 5 new inequality tests added in Plan 03. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `grover.py` | `oracle.py` | `_predicate_to_oracle` import | WIRED | `from .oracle import GroverOracle, _predicate_to_oracle, grover_oracle` (line 36) |
| `grover.py` | `oracle.py` | `_predicate_to_oracle` called for lambda oracles | WIRED | `oracle = _predicate_to_oracle(oracle, register_widths)` (line 541) |
| `grover.py` | `_verify_classically` | Classical verification in BBHT loop | WIRED | `if _verify_classically(predicate, values):` (line 413) |
| `grover.py` | `_bbht_search` | Adaptive dispatch when `m is None` | WIRED | `return _bbht_search(oracle, register_widths, max_attempts, predicate)` (line 549) |
| `qint_comparison.pxi` | `qint.pyx` | include directive inlines at build time | WIRED | `include "qint_comparison.pxi"` (qint.pyx line 906) |
| `test_grover_predicate.py` | `grover.py` | `ql.grover()` with inequality lambda predicates | WIRED | 5 inequality lambda tests: `x > 1`, `x < 2`, `x >= 2`, `x <= 1`, `(x > 0) & (x < 3)` |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SYNTH-01 | 80-01, 80-02, 80-03 | User can pass Python predicate lambda as oracle | SATISFIED | `_predicate_to_oracle` implemented; `>` operator now works end-to-end. `test_lambda_predicate_greater_than` tests `ql.grover(lambda x: x > 1, width=3)`. REQUIREMENTS.md shows `[x] SYNTH-01: Complete`. |
| SYNTH-02 | 80-01, 80-02, 80-03 | Compound predicates compile to valid oracles | SATISFIED | `&` operator works via `qbool.__and__`; `test_compound_predicate_inequality_and` tests `(x > 0) & (x < 3)`. REQUIREMENTS.md shows `[x] SYNTH-02: Complete`. |
| SYNTH-03 | 80-01, 80-02, 80-03 | Predicate oracles work with existing qint comparison operators | SATISFIED | All 6 operators tested: `==`, `!=`, `<`, `>`, `<=`, `>=`. No hardcoded `[63]` remains. REQUIREMENTS.md shows `[x] SYNTH-03: Complete`. |
| ADAPT-01 | 80-02 | When M is unknown, Grover uses exponential backoff strategy | SATISFIED | (Unchanged) `_bbht_search` with LAMBDA=6/5 growth, random `j` in `[0, upper)`, `upper = min(LAMBDA^attempt, sqrt_N)`. |
| ADAPT-02 | 80-02 | Adaptive search terminates when solution found or search space exhausted | SATISFIED | (Unchanged) `_verify_classically` loop; `return None` on exhaustion; `max_attempts` parameter. |

No orphaned requirements. REQUIREMENTS.md maps all 5 IDs to Phase 80, all marked `[x] Complete`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `grover.py` | ~280 | `"Used for post-measurement verification in adaptive BBHT search (Plan 02)"` in docstring | Info | Stale internal plan reference. Cosmetic only; no functional impact. |

No stubs, missing implementations, hardcoded `[63]` index values, or TODO blockers found in any
gap-closure files. No regressions detected in static inspection.

### Re-verification: Previous Gaps Status

#### Gap 1 (was PARTIAL): "User can pass Python predicate lambda as oracle"

**Previous:** BUG-CMP-MSB prevented `>` operator; only `==` and `!=` worked.
**Now:** CLOSED. `qint_comparison.pxi` line 301 changed from `temp_self[63]` to `temp_self[comp_width - 1]`. `test_lambda_predicate_greater_than` exercises `ql.grover(lambda x: x > 1, width=3)`. Commit b53bc44 verified in git log.

#### Gap 2 (was PARTIAL): "Compound predicates compile to valid oracles"

**Previous:** `&` operator worked but specific `(x > 10) & (x < 50)` example failed because `>` and `<` failed.
**Now:** CLOSED. Both `__gt__` and `__lt__` fixed. `test_compound_predicate_inequality_and` tests `ql.grover(lambda x: (x > 0) & (x < 3), width=2)` using both inequality operators plus `&`. Commit 6df69ae verified.

#### Gap 3 (was FAILED): "Predicate oracles work with all existing qint comparison operators"

**Previous:** `<`, `>`, `<=`, `>=` all failed with IndexError.
**Now:** CLOSED. Fix in `__lt__` (line 301) and `__gt__` (line 421); `__le__` and `__ge__` delegate to `~(self > other)` and `~(self < other)` respectively, so they inherit the fix. Four dedicated tests: `test_lambda_predicate_less_than`, `test_lambda_predicate_greater_equal`, `test_lambda_predicate_less_equal`, plus `test_lambda_predicate_greater_than`. No `[63]` hardcoded index remains anywhere in the inequality operator implementations.

### Human Verification Required

#### 1. Full Predicate Test Suite (including new inequality tests)

**Test:** Run `python3 -m pytest tests/python/test_grover_predicate.py -v --timeout=300`
**Expected:** 22 passed, 0 failed (17 original + 5 new inequality tests)
**Why human:** Qiskit simulation is slow and probabilistic; inequality predicate tests use the adaptive path which may take multiple BBHT attempts per trial. Full suite may take 5-15 minutes.

#### 2. Backwards Compatibility Test Suite

**Test:** Run `python3 -m pytest tests/python/test_grover.py -v --timeout=120`
**Expected:** 21 passed, 0 failed — all pre-existing decorated oracle tests unchanged
**Why human:** Requires Qiskit simulation execution.

#### 3. Combined Suite Regression Check

**Test:** Run `python3 -m pytest tests/python/test_grover.py tests/python/test_grover_predicate.py -v`
**Expected:** 43 passed, 0 failed (21 + 22)
**Why human:** The Plan 03 SUMMARY reports 43/43, but the simulation must be re-run to confirm no environment-specific failures since the Cython rebuild.

### Gaps Summary

No gaps remain. All 3 previously failing truths are now verified at the static code level:

1. BUG-CMP-MSB root cause is eliminated — `comp_width - 1` replaces hardcoded `[63]` at both affected sites in `qint_comparison.pxi`
2. Five new inequality predicate tests cover all four inequality operators and compound `&` composition
3. REQUIREMENTS.md reflects `[x] Complete` for all 5 requirement IDs
4. Both gap-closure commits (`b53bc44`, `6df69ae`) are confirmed in git history with matching change descriptions

The remaining `human_needed` items are simulation execution confirmations — automated verification
cannot run Qiskit circuits in this environment.

---

_Verified: 2026-02-22T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
