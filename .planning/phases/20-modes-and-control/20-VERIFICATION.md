---
phase: 20-modes-and-control
verified: 2026-01-28T19:30:00Z
status: passed
score: 11/11 must-haves verified
---

# Phase 20: Modes and Control Verification Report

**Phase Goal:** Provide user control over uncomputation strategy and explicit override methods
**Verified:** 2026-01-28T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ql.option('qubit_saving') returns current mode value (False by default) | ✓ VERIFIED | option() function exists at line 49, returns _qubit_saving_mode (line 82), default is False (line 46). Test passes. |
| 2 | ql.option('qubit_saving', True) enables eager mode for subsequent qbools | ✓ VERIFIED | option() sets _qubit_saving_mode = value (line 85). Test confirms mode switching works. |
| 3 | Existing qbools keep their creation-time mode when global mode changes | ✓ VERIFIED | _uncompute_mode captured at creation in both __init__ branches (lines 317, 372). Test confirms mode immutability. |
| 4 | Qbool created in eager mode uncomputes immediately on garbage collection | ✓ VERIFIED | __del__ checks _uncompute_mode (line 233), calls _do_uncompute immediately if True (line 236). |
| 5 | Qbool created in lazy mode only uncomputes at scope boundaries | ✓ VERIFIED | __del__ checks scope depth when _uncompute_mode is False (lines 241-242), only uncomputes if current <= creation_scope. |
| 6 | Calling .keep() on qbool prevents automatic uncomputation in __del__ | ✓ VERIFIED | keep() sets _keep_flag = True (line 176), __del__ checks and returns early if flag set (lines 229-230). Test passes. |
| 7 | Calling .keep() on already-uncomputed qbool prints warning to stderr | ✓ VERIFIED | keep() checks _is_uncomputed and prints warning to stderr (lines 170-174). Test confirms warning printed. |
| 8 | Qbool with .keep() called can still be explicitly uncomputed with .uncompute() | ✓ VERIFIED | uncompute() has comment "NOT checking _keep_flag" (line 133), design documented. Test passes. |
| 9 | Error messages start with 'Cannot [action]:' pattern | ✓ VERIFIED | _check_not_uncomputed: "Cannot use qbool:" (line 190), uncompute(): "Cannot uncompute:" (line 141). |
| 10 | Use-after-uncompute error message suggests creating new qbool or calling .keep() | ✓ VERIFIED | Error includes "Create a new qbool or call .keep()" (line 191). Test confirms suggestion present. |
| 11 | Refcount error message explains how many references exist and what to do | ✓ VERIFIED | Error includes f-string with refcount-1 (line 141) and actionable suggestion (line 142). Test confirms count present. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python-backend/quantum_language.pyx` | option() function and mode-aware attributes | ✓ VERIFIED | option() at line 49 (39 lines), _qubit_saving_mode at line 46, _uncompute_mode cdef public at line 158, _keep_flag cdef at line 159 |
| `python-backend/qint_operations.pxi` | keep() method and mode-aware __del__ | ✓ VERIFIED | keep() at line 147 (30 lines), __del__ at line 204 (50+ lines with mode logic) |
| `python-backend/test.py` | Comprehensive Phase 20 test suite | ✓ VERIFIED | 12 tests starting at line 733, all pass (100% pass rate in test output) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|------|-----|--------|---------|
| option() function | _qubit_saving_mode global | global statement | ✓ WIRED | Line 78: `global _qubit_saving_mode`, lines 82-85 read/write |
| qint.__init__() | _qubit_saving_mode | capture at creation | ✓ WIRED | Lines 316-317, 371-372: `self._uncompute_mode = _qubit_saving_mode` |
| __del__() | _uncompute_mode | mode check before uncompute | ✓ WIRED | Line 233: `if self._uncompute_mode:` branches to different behavior |
| keep() method | _keep_flag attribute | flag setting | ✓ WIRED | Line 176: `self._keep_flag = True` |
| __del__() | _keep_flag | check before uncompute | ✓ WIRED | Lines 229-230: `if hasattr(self, '_keep_flag') and self._keep_flag: return` |
| _check_not_uncomputed() | ValueError | raise statement | ✓ WIRED | Lines 189-192: raises ValueError with "Cannot" pattern |
| uncompute() | ValueError | raise statement | ✓ WIRED | Lines 140-143: raises ValueError with "Cannot" pattern and refcount |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| MODE-01: Default lazy mode keeps intermediates until final qbool is uncomputed | ✓ SATISFIED | _qubit_saving_mode defaults to False (line 46), lazy mode checks scope depth (lines 238-242) |
| MODE-02: Qubit-saving eager mode (`ql.option("qubit_saving")`) uncomputes intermediates immediately | ✓ SATISFIED | option() sets mode (line 85), eager mode uncomputes immediately (line 236) |
| MODE-03: Per-circuit mode switching allows different strategies in same program | ✓ SATISFIED | Mode captured at creation (lines 317, 372), not retroactive. Test confirms different modes coexist. |
| CTRL-01: Clear error messages when uncomputation fails or is invalid | ✓ SATISFIED | "Cannot [action]:" pattern (lines 141, 190), actionable suggestions (lines 142, 191) |
| CTRL-02: Explicit `uncompute()` method available for manual control | ✓ SATISFIED | uncompute() method at line 100 in qint_operations.pxi, works independent of mode/keep flag |
| SCOPE-03: Explicit `.keep()` method allows opt-out of automatic uncomputation | ✓ SATISFIED | keep() method at line 147, sets flag checked by __del__ (lines 229-230) |

### Anti-Patterns Found

None detected. Code is substantive, well-documented, and properly wired.

### Human Verification Required

None. All requirements are programmatically verifiable and have been verified through:
1. Code inspection (all artifacts exist and are substantive)
2. Wiring analysis (all key links connected)
3. Automated tests (12 tests, 100% pass rate)

---

## Detailed Analysis

### Level 1: Existence ✓

All required artifacts exist:
- `python-backend/quantum_language.pyx` (modified, 389+ lines)
- `python-backend/qint_operations.pxi` (modified, contains all required methods)
- `python-backend/test.py` (modified, contains 12 Phase 20 tests)

### Level 2: Substantive ✓

**option() function (39 lines):**
- Has parameter validation (lines 83-84, 86-87)
- Returns current value when value=None (line 82)
- Sets mode when value provided (line 85)
- Comprehensive docstring with examples (lines 50-77)
- NOT a stub

**keep() method (30 lines):**
- Checks for already-uncomputed state (line 170)
- Prints warning to stderr appropriately (lines 172-173)
- Sets _keep_flag = True (line 176)
- Comprehensive docstring (lines 148-169)
- NOT a stub

**__del__() mode-aware implementation (50+ lines):**
- Checks _keep_flag (lines 229-230)
- Branches on _uncompute_mode (line 233)
- DISTINCT behavior for eager (line 236) vs lazy (lines 241-244)
- Comprehensive docstring explaining both modes (lines 204-222)
- NOT a stub

**Error messages:**
- _check_not_uncomputed: "Cannot use qbool: already uncomputed. Create a new qbool or call .keep() to prevent automatic cleanup." (lines 189-192)
- uncompute(): "Cannot uncompute: qbool still in use ({refcount - 1} references exist). Delete other references first or let automatic cleanup handle it." (lines 140-143)
- Both follow "Cannot [action]:" pattern with actionable suggestions
- NOT generic error messages

**Test suite (12 tests, 240+ lines):**
- Tests for option() get/set, validation
- Tests for mode capture at creation
- Tests for .keep() behavior
- Tests for error message content
- All tests pass (verified by test run output)
- NOT placeholder tests

### Level 3: Wired ✓

**option() → _qubit_saving_mode:**
- Global declaration (line 78)
- Read on line 82 (return path)
- Write on line 85 (set path)
- WIRED

**__init__() → mode capture:**
- Global _qubit_saving_mode accessed (lines 316, 371)
- Assigned to self._uncompute_mode (lines 317, 372)
- Happens in BOTH create_new branches
- WIRED

**__del__() → mode-aware behavior:**
- Checks _keep_flag first (lines 229-230)
- Branches on _uncompute_mode (line 233)
- Eager: calls _do_uncompute unconditionally (line 236)
- Lazy: checks scope depth before calling _do_uncompute (lines 241-244)
- WIRED with DISTINCT behaviors

**keep() → _keep_flag → __del__():**
- keep() sets flag (line 176)
- __del__() checks flag (line 229) and returns early if True (line 230)
- WIRED

**uncompute() → ValueError:**
- Line 140: `raise ValueError(...)`
- Error message includes refcount (line 141) and suggestions (line 142)
- WIRED

**_check_not_uncomputed() → ValueError:**
- Line 189: `raise ValueError(...)`
- Error message includes "Cannot" pattern and suggestions (lines 190-191)
- WIRED

### Test Coverage ✓

All 12 Phase 20 tests pass:
1. test_phase20_option_default - MODE-01
2. test_phase20_option_set_get - MODE-02
3. test_phase20_option_invalid_key - MODE API validation
4. test_phase20_option_invalid_value - MODE API validation
5. test_phase20_mode_capture_at_creation - MODE-03
6. test_phase20_keep_returns_none - SCOPE-03
7. test_phase20_keep_prevents_auto_uncompute - SCOPE-03
8. test_phase20_keep_on_uncomputed_warns - SCOPE-03
9. test_phase20_keep_allows_explicit_uncompute - SCOPE-03 + CTRL-02
10. test_phase20_error_use_after_uncompute - CTRL-01
11. test_phase20_error_refcount - CTRL-01
12. test_phase20_error_uses_valueerror - CTRL-01

Test run output shows: "Phase 20 Results: 12 passed, 0 failed"

---

## Success Criteria from ROADMAP.md

1. **Default behavior (lazy mode) keeps intermediates alive until the final result is uncomputed, minimizing gate count** ✓
   - Evidence: _qubit_saving_mode defaults to False (line 46), __del__ checks scope depth in lazy mode (lines 241-242)

2. **Eager mode (`ql.option("qubit_saving")`) uncomputes intermediates immediately after use, minimizing peak qubit count** ✓
   - Evidence: option() sets mode (line 85), __del__ calls _do_uncompute immediately when _uncompute_mode is True (line 236)

3. **Users can call `.uncompute()` explicitly on qbool variables to trigger early cleanup** ✓
   - Evidence: uncompute() method exists (line 100), works independently of mode/keep (line 133 comment)

4. **Users can call `.keep()` on qbool variables to prevent automatic uncomputation** ✓
   - Evidence: keep() method exists (line 147), sets _keep_flag (line 176), __del__ respects flag (lines 229-230)

5. **Error messages clearly indicate when uncomputation cannot be performed (e.g., value still in use)** ✓
   - Evidence: "Cannot [action]:" pattern (lines 141, 190), includes refcount and actionable suggestions (lines 142, 191)

---

_Verified: 2026-01-28T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
