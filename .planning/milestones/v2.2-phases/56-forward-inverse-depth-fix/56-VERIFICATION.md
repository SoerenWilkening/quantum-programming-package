---
phase: 56-forward-inverse-depth-fix
verified: 2026-02-05T14:30:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 56: Forward/Inverse Depth Fix Verification Report

**Phase Goal:** Forward compilation path produces same optimized depth as inverse compilation

**Verified:** 2026-02-05T14:30:00Z

**Status:** PASSED

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Diagnostic test measures depth of f(x) capture vs f(x) replay vs f.adjoint(x) replay | ✓ VERIFIED | test_depth_capture_vs_replay exists and measures all three paths |
| 2 | Test output shows exact depth values for each path | ✓ VERIFIED | Tests use get_current_layer() to measure depth, assertions show exact values on failure |
| 3 | Root cause of depth discrepancy is identified and documented | ✓ VERIFIED | DEPTH-PARITY section documents layer_floor constraint (lines 2980-2997) |
| 4 | f(x) replay produces same circuit depth as f.adjoint(x) replay for equivalent operations | ✓ VERIFIED | test_forward_adjoint_depth_equal passes, asserts equality |
| 5 | Existing compilation tests pass without regression | ✓ VERIFIED | All 110 tests pass (100% success rate) |
| 6 | Depth comparison tests assert equality (not just measure) | ✓ VERIFIED | All 4 depth tests use hard assertions (assert forward_depth == adjoint_depth) |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| tests/test_compile.py (56-01) | Diagnostic test functions for depth analysis containing test_depth_capture_vs_replay | ✓ VERIFIED | Lines 2978-3180: DEPTH-PARITY section with 4 tests including test_depth_capture_vs_replay (line 3150) |
| src/quantum_language/compile.py (56-02) | Fixed replay path with consistent depth containing _replay | ✓ VERIFIED | Lines 952-1010: _replay() function with layer_floor documentation (lines 984-990) |
| tests/test_compile.py (56-02) | Permanent depth regression tests containing test_forward_adjoint_depth_equal | ✓ VERIFIED | Line 3000: test_forward_adjoint_depth_equal with hard assertions |

**All artifacts verified at 3 levels:**
- Level 1 (Existence): All files exist
- Level 2 (Substantive): test_compile.py depth section is 202 lines with 4 complete tests, compile.py _replay has comprehensive documentation
- Level 3 (Wired): Tests import get_current_layer and use it throughout, _replay is called by CompiledFunc.__call__

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| tests/test_compile.py | quantum_language._core | import statement | ✓ WIRED | Line 24: imports get_current_layer, used in all depth tests |
| tests/test_compile.py | src/quantum_language/compile.py | test imports | ✓ WIRED | Line 23: imports quantum_language as ql, tests call @ql.compile |
| test_forward_adjoint_depth_equal | get_current_layer | depth measurement | ✓ WIRED | Lines 3026-3036: calls get_current_layer() before/after operations |
| test_depth_capture_vs_replay | get_current_layer | depth measurement | ✓ WIRED | Lines 3165-3176: measures capture and replay depths |

### Requirements Coverage

| Requirement | Status | Supporting Evidence |
|-------------|--------|---------------------|
| FIX-01: Investigate f() vs f.inverse() depth discrepancy | ✓ SATISFIED | Diagnostic tests measure all paths, root cause documented in lines 2980-2997 |
| FIX-02: Fix forward compilation path to match inverse optimization | ✓ SATISFIED | Tests prove forward_depth == adjoint_depth, documentation added to compile.py:984-990 |

### Anti-Patterns Found

**None detected.** Scanned lines 2978-3180 (depth test section) and lines 950-1010 (_replay function):
- No TODO/FIXME/HACK comments
- No empty returns or stub implementations
- No console.log debugging artifacts
- One "placeholder" comment on line 976 is legitimate (describes control qubit mapping, not a stub)

### Test Results

```bash
$ pytest tests/test_compile.py::test_forward_adjoint_depth_equal -v
PASSED [100%]

$ pytest tests/test_compile.py::test_forward_adjoint_depth_equal_multiwidth -v
PASSED [100%]

$ pytest tests/test_compile.py::test_controlled_depth_parity -v
PASSED [100%]

$ pytest tests/test_compile.py::test_depth_capture_vs_replay -v
PASSED [100%]

$ pytest tests/test_compile.py -v
============================= 110 passed in 0.42s ==============================
```

**All tests pass. No regressions.**

### Phase Discovery: Interesting Finding

The SUMMARY documents reveal an important finding: **The original hypothesis was incorrect.**

**Original assumption (ROADMAP.md):** Forward compilation `f(x)` produces different depth than inverse `f.adjoint(x)`.

**Actual finding (56-01-SUMMARY.md):** Forward replay and adjoint replay produce **equal depths** already. The real discrepancy is between capture and replay when capture can parallelize gates into earlier layers.

**Resolution:** 
- Phase 56 success criterion from ROADMAP: "f(x) produces circuit depth equal to f.inverse(x)" is **already met** by the existing layer_floor constraint in _replay()
- Plan 02 added comprehensive documentation explaining why depth equality is guaranteed
- Regression tests ensure this invariant holds permanently
- No code fix was needed, only verification and documentation

This is a perfect example of goal-backward verification: The GOAL was depth parity (achieved), even though the HYPOTHESIS about the root cause was incorrect.

---

## Verification Summary

**Phase 56 goal is ACHIEVED.**

All must-haves verified:
1. ✓ Diagnostic tests measure all depth paths
2. ✓ Test output shows exact depth values
3. ✓ Root cause documented (layer_floor constraint ensures equality)
4. ✓ Forward/adjoint replays produce equal depth (verified by tests)
5. ✓ No regression in existing tests (110/110 pass)
6. ✓ Tests assert equality with hard assertions

**Requirements status:**
- FIX-01 (Investigate depth discrepancy): ✓ Complete — investigation proved forward/adjoint already equal
- FIX-02 (Fix forward path): ✓ Complete — no fix needed, documented guarantee, regression tests added

**Technical quality:**
- 4 comprehensive depth parity tests
- Documentation explains mechanism (layer_floor constraint)
- All tests use hard assertions (not just measurements)
- 100% test pass rate, zero regressions
- No anti-patterns detected

**Deliverables:**
- DEPTH-PARITY test suite (202 lines)
- Documentation in compile.py explaining depth behavior
- Root cause analysis in test docstrings

---

_Verified: 2026-02-05T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
