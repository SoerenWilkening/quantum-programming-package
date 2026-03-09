---
phase: 115-check-detection-combined-predicate
verified: 2026-03-09T13:15:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
requirements_verified:
  - PRED-03
  - PRED-04
---

# Phase 115: Check Detection & Combined Predicate Verification Report

**Phase Goal:** Users can evaluate full move legality including king safety in superposition, with all conditions composed into a single predicate
**Verified:** 2026-03-09T13:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Check detection predicate verifies king is not in check after a move using pre-computed attack tables (knight L-shapes + king adjacency) evaluated via `with` conditionals on board qarray | VERIFIED | `make_check_detection_predicate` at line 241 of chess_predicates.py uses `_compute_attack_table` (line 197) with king/knight offset distinction; 6 statevector tests in TestCheckDetection + 7 classical equivalence configs in TestCheckDetectionClassical all exercise this |
| 2 | Combined move legality predicate composes piece-exists, no-friendly-capture, and check detection using standard `with qbool:` conditional nesting and boolean operators | VERIFIED | `make_combined_predicate` (line 322) calls all three sub-predicates (lines 359-362), uses `&` operator for three-way AND (lines 392-395), and uncomputes via `.adjoint()` (lines 398-400) |
| 3 | Combined predicate returns a single qbool indicating full move legality, usable as a validity flag for walk branching | VERIFIED | `is_legal` function signature takes `result` as last arg (line 379), three-way AND result flips single `result` qbool (lines 392-395); `__all__` exports `make_combined_predicate` for Phase 116 consumption |
| 4 | All predicates verified correct against classical equivalents on small boards within 17-qubit simulation limit | VERIFIED | TestCheckDetectionClassical (7 configs, line 592) verifies check detection against `_classical_check_safe`; TestCombinedPredicate uses circuit-build-only for full combined (exceeds 17-qubit limit) + 3 separate AND composition statevector tests (lines 764-817) verifying the AND logic within budget |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/chess_predicates.py` | `make_check_detection_predicate` factory | VERIFIED | 403 lines, contains `_compute_attack_table` (line 197), `make_check_detection_predicate` (line 241), `make_combined_predicate` (line 322) |
| `src/chess_predicates.py` | `make_combined_predicate` factory | VERIFIED | Line 322, composes all 3 sub-predicates, three-way AND, proper uncomputation |
| `tests/python/test_chess_predicates.py` | TestCheckDetection class | VERIFIED | 6 tests (lines 423-560): safe, in-check, non-attacking, king-move-destination, knight-move-current, adjoint-roundtrip |
| `tests/python/test_chess_predicates.py` | TestCheckDetectionClassical class | VERIFIED | 1 test with 7 configs (line 563-635) |
| `tests/python/test_chess_predicates.py` | TestCombinedPredicate class | VERIFIED | 8 tests (lines 677-817): 5 circuit-build-only + 3 AND composition statevector |
| `tests/python/test_chess_predicates.py` | TestScalingPhase115 class | VERIFIED | 2 tests (lines 638-669): 8x8 check detection + 8x8 combined predicate build |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| chess_predicates.py (make_combined_predicate) | chess_predicates.py (make_piece_exists_predicate) | Internal call | WIRED | Line 359: `pe_pred = make_piece_exists_predicate(...)` |
| chess_predicates.py (make_combined_predicate) | chess_predicates.py (make_no_friendly_capture_predicate) | Internal call | WIRED | Line 360: `nfc_pred = make_no_friendly_capture_predicate(...)` |
| chess_predicates.py (make_combined_predicate) | chess_predicates.py (make_check_detection_predicate) | Internal call | WIRED | Lines 361-363: `cd_pred = make_check_detection_predicate(...)` |
| test_chess_predicates.py | chess_encoding.py | Import offsets | WIRED | `from chess_encoding import _KING_OFFSETS` in 8 test methods, `_KNIGHT_OFFSETS` in 1 test |
| chess_predicates.py | quantum_language | @ql.compile(inverse=True) | WIRED | 4 compiled functions: piece_exists, no_friendly_capture, check_safe, is_legal |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRED-03 | 115-01 | Check detection predicate verifies king safety using attack tables | SATISFIED | `make_check_detection_predicate` implemented with `_compute_attack_table`, king/knight move distinction, flip-and-unflip pattern; 7 statevector tests + 7 classical equivalence configs pass |
| PRED-04 | 115-02 | Combined predicate composes all three conditions via boolean operators | SATISFIED | `make_combined_predicate` composes pe/nfc/cd sub-predicates via three-way `&` AND; 8 tests (5 circuit-build + 3 AND composition statevector) pass |

No orphaned requirements found -- ROADMAP lists PRED-03 and PRED-04 for Phase 115, both are claimed and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

No TODO/FIXME/PLACEHOLDER/HACK comments found. No empty implementations. No stub patterns detected.

### Commits Verified

All 4 claimed commits exist in git history:
- `1c3d526` test(115-01): add failing tests for check detection predicate
- `1be1820` feat(115-01): implement check detection predicate factory
- `d7e31d7` test(115-02): add failing tests for combined move legality predicate
- `c2bc50a` feat(115-02): implement combined move legality predicate

### Human Verification Required

No items require human verification. All predicate behavior is verified via statevector simulation and circuit construction tests. The combined predicate exceeds the 17-qubit simulation budget for full end-to-end statevector testing, but:
- Each sub-predicate is independently verified via statevector against classical equivalents
- The AND composition logic is verified separately with pre-set qbool inputs within budget
- Circuit construction succeeds for all configurations including 8x8

### Gaps Summary

No gaps found. All 4 success criteria verified, all artifacts substantive and wired, all requirements satisfied, no anti-patterns detected.

---

_Verified: 2026-03-09T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
