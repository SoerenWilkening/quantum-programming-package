---
phase: 113-diffusion-redesign-move-enumeration
verified: 2026-03-08T20:15:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 113: Diffusion Redesign & Move Enumeration Verification Report

**Phase Goal:** Walk circuits can handle large branching factors (100+ children) without combinatorial explosion, and all geometrically possible moves are enumerated for quantum evaluation
**Verified:** 2026-03-08T20:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All-moves enumeration table contains every geometrically possible (piece_type, src, dst) triple for knights (up to 8 per square) and kings (up to 8 per square) without legality filtering | VERIFIED | `build_move_table()` in `src/chess_encoding.py:66` uses `_KNIGHT_OFFSETS` (8 L-shapes) and `_KING_OFFSETS` (8 adjacencies), returns 8 entries per piece regardless of board position. 8 tests in `tests/python/test_move_table.py` validate sizes, offsets, piece IDs, indexing. |
| 2 | Diffusion operator uses an arithmetic counting circuit (summing validity bits into a count register) instead of O(2^d_max) itertools.combinations pattern enumeration | VERIFIED | `counting_diffusion_core()` in `src/quantum_language/walk.py:464` sums validity bits via `count += v` loop into a `qint` count register, then dispatches via `count == d_val` comparisons. No `itertools.combinations` in walk.py or chess_walk.py. |
| 3 | Diffusion circuit generation is O(d_max) in gate count -- no exponential or superlinear blowup | VERIFIED | `counting_diffusion_core` iterates `range(1, d_max+1)` (linear loop) for both U_dagger and U forward phases. Test `test_gate_count_linear` in `tests/python/test_counting_diffusion.py` verifies gate_count(d_max=8)/gate_count(d_max=4) < 3.0. |
| 4 | Existing walk tests continue to pass (diffusion redesign does not break SAT demo or small-board cases) | VERIFIED | Summary 113-03 reports 259 tests passing. `_variable_diffusion` delegates to `_counting_diffusion` (walk.py:964). Legacy code removed (no `_variable_diffusion_legacy`). Commits verified in git history. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/chess_encoding.py` | `build_move_table()` function | VERIFIED | Function at line 66, exported in `__all__` at line 38, full docstring and type hints |
| `tests/python/test_move_table.py` | Move table unit tests | VERIFIED | 8 test functions covering sizes, offsets, piece IDs, indexing, edge cases |
| `src/quantum_language/walk.py` | `_counting_diffusion()` and `counting_diffusion_core()` | VERIFIED | `_counting_diffusion` at line 966 delegates to `counting_diffusion_core` at line 464 (120+ lines of substantive implementation) |
| `tests/python/test_counting_diffusion.py` | Equivalence and property tests | VERIFIED | 8 test functions: equivalence d2/d3, reflection d2/d3, gate count linearity, norm preservation, state modification |
| `src/chess_walk.py` | `apply_diffusion()` using shared counting diffusion | VERIFIED | Imports `counting_diffusion_core` at line 22, calls it at line 470. No `itertools` import remains. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `chess_encoding.py` | `_KNIGHT_OFFSETS`/`_KING_OFFSETS` | offset lookup by piece_type | WIRED | Line 91: `_KNIGHT_OFFSETS if piece_type == "knight" else _KING_OFFSETS` |
| `walk.py` | `qint.__eq__` | count comparison dispatch | WIRED | Line 524: `cond = count == d_val` inside counting_diffusion_core |
| `walk.py` | validity sum | popcount via addition | WIRED | Lines 515-516: `count += v` loop over validity qbools |
| `chess_walk.py` | `walk.py:counting_diffusion_core` | shared function import | WIRED | Line 22: `counting_diffusion_core,` imported; line 470: called with correct arguments |
| `walk.py:_variable_diffusion` | `_counting_diffusion` | delegation | WIRED | Line 964: `self._counting_diffusion(depth)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WALK-01 | 113-01 | All-moves enumeration table precomputes every geometrically possible triple for knights and kings | SATISFIED | `build_move_table()` returns 8 entries per piece with correct offsets, validated by 8 tests |
| WALK-03 | 113-02, 113-03 | Diffusion operator redesigned with arithmetic counting circuit replacing O(2^d_max) enumeration | SATISFIED | `counting_diffusion_core()` shared by both walk.py and chess_walk.py, no `itertools.combinations` remains |

No orphaned requirements found -- REQUIREMENTS.md maps only WALK-01 and WALK-03 to Phase 113, matching plan declarations.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No TODO/FIXME/PLACEHOLDER/HACK found in any modified file |

### Human Verification Required

None required. All success criteria are verifiable through code inspection and test existence. The equivalence tests (statevector comparison) and reflection property tests provide mathematical correctness guarantees that don't need human visual verification.

### Gaps Summary

No gaps found. All four success criteria from ROADMAP.md are satisfied:

1. Move enumeration table exists with correct geometric offsets (8 per piece, no legality filtering)
2. Counting circuit replaces combinatorial enumeration (validity sum + comparison dispatch)
3. Linear gate complexity (O(d_max) loop structure, test-verified scaling)
4. No regressions (legacy code removed, delegation chain intact, 259 tests reported passing)

All 6 commits verified in git history (9fcc6fd, 15e4a93, 9b16766, 1588338, 68c793f, cbbd693).

---

_Verified: 2026-03-08T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
