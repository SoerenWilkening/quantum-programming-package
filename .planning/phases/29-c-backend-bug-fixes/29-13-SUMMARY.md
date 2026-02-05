---
phase: 29-c-backend-bug-fixes
plan: 13
status: completed
result: regression_detected
deviation: true
commits: ["6328d19"]
files_modified: ["src/quantum_language/qint.pyx", "src/quantum_language/qint_comparison.pxi", "c_backend/src/IntegerMultiplication.c"]
subsystem: comparison-multiplication-verification
tags: ["bug-fix", "comparison", "multiplication", "QFT", "verification", "BUG-02", "BUG-03"]
tech_stack:
  added: []
  patterns: ["PYTHONPATH-based testing", "build_ext --inplace workaround"]
dependencies:
  requires: ["29-12"]
  provides: ["verification-results-for-29-14", "BUG-02-fix-attempt", "BUG-03-fix-attempt"]
  affects: ["29-14"]
key_files:
  created: []
  modified: ["src/quantum_language/qint.pyx", "c_backend/src/IntegerMultiplication.c", "src/quantum_language/qint_comparison.pxi"]
decisions:
  - title: "Use PYTHONPATH=src instead of editable install"
    rationale: "pip install -e . fails with absolute path error; build_ext --inplace + PYTHONPATH works"
    alternative: "Fix setup.py to use relative paths"
  - title: "Apply BUG-02 fix: rewrite __le__ as ~(self > other)"
    rationale: "Old __le__ called QQ_add twice (causing BUG-05 cache pollution); new version only needs one QQ_add via __gt__"
    alternative: "Fix BUG-05 first, keep original __le__"
  - title: "Apply BUG-03 fix: reverse target qubit mappings in QQ_mul/cQQ_mul"
    rationale: "Target qubits were inverted (bits-i-1 → i) based on plan 29-14"
    alternative: "Deeper CCP decomposition redesign"
duration: "~15 min"
completed: 2026-01-31
---

# Phase 29 Plan 13: Rebuild and Verify BUG-02 & BUG-03 Fixes

**One-liner:** Rebuilt package with BUG-02 (__le__ rewrite) and BUG-03 (target qubit) fixes, but verification reveals REGRESSIONS in BUG-01/BUG-04 and NO improvement in BUG-02/BUG-03 due to BUG-05 memory explosion escalation.

## Objective

Rebuild and reinstall the quantum_language package with uncommitted BUG-02 and BUG-03 fixes from the previous session, then run the full verification suite (all 19 tests) to confirm which fixes work.

## What Was Done

### Task 1: Package Rebuild ✓

**Changes applied:**
- **BUG-02 (qint.pyx):**
  - Rewrote `__le__` from MSB-inspection approach to `return ~(self > other)`
  - Modified `__gt__` int path to create temp qint instead of `~(self <= other)` (breaks circular dependency)
- **BUG-03 (IntegerMultiplication.c):**
  - Fixed target qubit mapping in QQ_mul Block 2: `bits - i - 1` → `i`
  - Fixed target qubit mapping in cQQ_mul blocks: `bits - bit - 1` → `bit`
  - Fixed CP_sequence: `bits - i - 1 - rounds` → `rounds + i`

**Build process:**
1. Removed stale `qint.c` to force Cython regeneration
2. Attempted `pip install -e .` — failed with absolute path error (known issue)
3. Fell back to `python3 setup.py build_ext --inplace` — succeeded
4. Used `PYTHONPATH=src` for all test execution to bypass site-packages shadowing

**Commit:** `6328d19` - "fix(29-13): rebuild package with BUG-02 and BUG-03 fixes"

### Task 2: Full Verification Suite ✓

Ran all 4 bug test suites with `PYTHONPATH=src`:

## Test Results

### BUG-01: Subtraction — 2/5 PASS (REGRESSION from 5/5)

| Test | Expected | Actual | Status | Notes |
|------|----------|--------|--------|-------|
| 3 - 7 (4-bit) | 12 | 12 | **PASS** | ✓ Deterministic |
| 7 - 3 (4-bit) | 4 | 4 | **PASS** | ✓ Deterministic |
| 0 - 1 (4-bit) | 15 | - | **FAIL** | BUG-05: 1048576M memory |
| 5 - 5 (4-bit) | 0 | - | **FAIL** | BUG-05: 4294967296M memory |
| 15 - 0 (4-bit) | 15 | - | **FAIL** | BUG-05: 17592186044416M memory |

**Analysis:** BUG-05 memory explosion NOW affects 3 tests that previously passed. This is a REGRESSION.

### BUG-02: Comparison — 1/6 PASS (NO improvement from 0/2 baseline)

| Test | Expected | Actual | Status | Notes |
|------|----------|--------|--------|-------|
| 5 <= 5 (4-bit) | 1 | 0 | **FAIL** | Logic failure (still returns 0) |
| 3 <= 7 (4-bit) | 1 | 0 | **FAIL** | Logic failure (still returns 0) |
| 7 <= 3 (4-bit) | 0 | 0 | **PASS** | ✓ (but may be coincidence) |
| 0 <= 0 (4-bit) | 1 | - | **FAIL** | BUG-05: 131072M memory |
| 0 <= 15 (4-bit) | 1 | - | **FAIL** | BUG-05: 33554432M memory |
| 15 <= 0 (4-bit) | 0 | - | **FAIL** | BUG-05: 8589934592M memory |

**Analysis:** The `__le__ = ~(self > other)` rewrite did NOT fix the bug. Still returns 0 for true comparisons. BUG-05 now blocks 3 tests that could run before.

### BUG-03: Multiplication — 0/5 PASS (REGRESSION from 2/5)

| Test | Expected | Actual | Status | Notes |
|------|----------|--------|--------|-------|
| 0 * 5 (4-bit) | 0 | - | **FAIL** | BUG-05: 67108864M memory (was PASS) |
| 1 * 1 (2-bit) | 1 | 2 | **FAIL** | Logic failure: 1*1=2 (was PASS) |
| 2 * 3 (4-bit) | 6 | 8 | **FAIL** | Logic failure: 2*3=8 (was 13/15) |
| 2 * 2 (3-bit) | 4 | - | **FAIL** | BUG-05: 34359738368M memory |
| 3 * 3 (4-bit) | 9 | - | **FAIL** | BUG-05: 16384M memory |

**Analysis:** Target qubit fix MADE THINGS WORSE. Even trivial cases (0*5, 1*1) now fail or memory-explode. The qubit reversal was INCORRECT.

### BUG-04: QFT Addition — 7/7 PASS (NO regression)

| Test | Expected | Actual | Status | Notes |
|------|----------|--------|--------|-------|
| 0 + 0 (4-bit) | 0 | 0 | **PASS** | ✓ |
| 0 + 1 (4-bit) | 1 | 1 | **PASS** | ✓ |
| 1 + 0 (4-bit) | 1 | 1 | **PASS** | ✓ |
| 1 + 1 (4-bit) | 2 | 2 | **PASS** | ✓ |
| 3 + 5 (4-bit) | 8 | 8 | **PASS** | ✓ |
| 7 + 8 (5-bit) | 15 | 15 | **PASS** | ✓ |
| 8 + 8 (4-bit) | 0 | 0 | **PASS** | ✓ Overflow wrap |

**Analysis:** Only bright spot — BUG-04 tests still all pass.

## Phase 29 Success Criteria Evaluation

| # | Criterion | 29-12 Status | 29-13 Status | Change |
|---|-----------|--------------|--------------|--------|
| 1 | qint(3) - qint(7) = 12 | **PASS** | **PASS** | No change |
| 2 | qint(5) <= qint(5) = 1 | **FAIL** | **FAIL** | No improvement |
| 3 | 2 * 3 = 6 | **FAIL** (13/15) | **FAIL** (8) | Different wrong value |
| 4 | 3 + 5 = 8 | **PASS** | **PASS** | No change |
| 5 | >= 14/19 tests pass | **PASS** (14/19) | **FAIL** (10/19) | **REGRESSION** |

**Score: 3/5 → 3/5** (no improvement, but composition changed)

**Overall pass rate: 14/19 (73.7%) → 10/19 (52.6%)** — BELOW threshold

## Critical Findings

### 1. BUG-05 Memory Explosion ESCALATED

BUG-05 now affects **9 additional test cases** that previously ran (slow but successful):
- BUG-01: 3 new failures (0-1, 5-5, 15-0)
- BUG-02: 3 new memory explosions (0≤0, 0≤15, 15≤0)
- BUG-03: 3 new memory explosions (0*5, 2*2, 3*3)

**Memory requirements grew exponentially:**
- Before: Circuits completed (even if slow/wrong)
- After: Requires 16384M to 17592186044416M (17 PB!) for 4-bit arithmetic

**Root cause hypothesis:** The __le__ rewrite and/or target qubit changes interact with BUG-05 cache pollution in a way that exponentially compounds circuit size.

### 2. BUG-03 Target Qubit Fix Was WRONG

The plan 29-14 premise (reverse `bits-i-1` → `i`) made multiplication WORSE:
- Lost both trivial cases that previously passed (0*5, 1*1)
- Changed wrong values (2*3: 13/15 → 8)

**Conclusion:** The target qubit mapping reversal is INCORRECT. Need to revert this change.

### 3. BUG-02 __le__ Rewrite Had NO Effect

Despite the theoretical soundness of `__le__ = ~(self > other)` to avoid double QQ_add, the tests show:
- Still returns 0 for true comparisons (5≤5, 3≤7)
- No improvement over baseline

**Hypothesis:** The comparison bug is NOT in the QQ_add invocation pattern, but in how the qbool result is extracted/returned. The __gt__ implementation may also be broken.

## Deviations from Plan

### Auto-Applied (Deviation Rule 3 - Blocking Issue)

**1. Fallback to build_ext --inplace + PYTHONPATH approach**
- **Found during:** Task 1 rebuild
- **Issue:** `pip install -e .` fails with "Error: setup script specifies an absolute path"
- **Fix:** Used `python3 setup.py build_ext --inplace` + `PYTHONPATH=src` for testing
- **Files modified:** None (build system workaround)
- **Commit:** Part of 6328d19

## Next Phase Readiness

### Blockers for Plan 14

❌ **ABORT Plan 14** — The BUG-03 target qubit fix from plan 29-14 made things WORSE. Should not proceed with verification; need to REVERT the IntegerMultiplication.c changes.

### Immediate Actions Needed

1. **REVERT IntegerMultiplication.c to baseline** (undo all `bits-i-1` → `i` changes)
2. **Investigate BUG-05 escalation** — Why did these changes trigger exponential memory growth?
3. **Re-examine BUG-02 comparison logic** — The __le__ rewrite alone is insufficient

### Open Questions

1. **Why does target qubit reversal break trivial multiplication?** Even 1*1 now returns 2.
2. **Why does BUG-05 memory explosion affect tests that previously worked?** Is there circuit construction change that compounds qubit allocation?
3. **Is the __gt__ implementation also broken?** If `__le__ = ~(__gt__)` still fails, maybe __gt__ returns inverted values.

## Recommendations

### For Phase 29 Continuation

1. **REVERT plan 29-13 changes** (create plan 29-15 to undo commit 6328d19)
2. **Isolate BUG-05 root cause** before attempting further BUG-02/BUG-03 fixes
3. **Create minimal reproduction test** for BUG-05 to understand why memory explodes
4. **Test __gt__ independently** to verify it returns correct boolean values
5. **Analytical verification of multiplication algorithm** before further qubit mapping changes

### For Plan 14

**DO NOT PROCEED** with plan 29-14 as written. The BUG-03 fix made things worse. Plan 14 should be revised to revert changes and re-investigate the multiplication algorithm from first principles.

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `src/quantum_language/qint.pyx` | __le__ rewrite, __gt__ int path change | No improvement, BUG-02 still broken |
| `c_backend/src/IntegerMultiplication.c` | Target qubit reversals (5 locations) | REGRESSION: BUG-03 worse than baseline |
| `src/quantum_language/qint_comparison.pxi` | Same as qint.pyx (reference copy) | Not used (no include directive) |

## Success Criteria Status

- [x] Package rebuilt with uncommitted fixes
- [x] Full test results for all 4 bug suites documented
- [x] BUG-01 and BUG-04 regression status assessed
- [x] 29-13-SUMMARY.md created for Plan 14 consumption
- [ ] ❌ BUG-02 or BUG-03 improvements (both regressed or unchanged)
- [ ] ❌ >= 4/5 phase 29 success criteria met (still 3/5, but overall pass rate dropped)

## Conclusion

**Plan 13 execution: Complete**
**Plan 13 outcome: FAILURE (regressions detected)**

The BUG-02 __le__ rewrite and BUG-03 target qubit fix both failed to improve their respective bugs and triggered a BUG-05 memory explosion escalation that broke 9 previously-working tests. **Recommend reverting commit 6328d19 and re-investigating BUG-05 before attempting further fixes.**
