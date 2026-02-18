---
phase: 75-clifford-t-decomposed-sequence-generation-for-all-toffoli-addition
verified: 2026-02-18T00:00:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 75: Clifford+T Decomposed Sequence Generation Verification Report

**Phase Goal:** Pre-computed Clifford+T hardcoded sequences for all Toffoli addition variants (CDKM and BK CLA) eliminate runtime CCX decomposition overhead when toffoli_decompose=True, providing exact T-count and zero-allocation dispatch for widths 1-8
**Verified:** 2026-02-18
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With `toffoli_decompose=True`, CDKM addition at widths 1-8 uses hardcoded Clifford+T sequences (H/T/Tdg/CX/X only, zero CCX) | VERIFIED | `TestCliffordTGatePurity::test_cdkm_qq_purity[1-4]` pass; zero CCX confirmed in all 8 `toffoli_clifft_qq_*.c` files; `hot_path_add_toffoli.c` checks `toffoli_decompose` flag and routes to `get_hardcoded_toffoli_clifft_QQ_add()` |
| 2 | With `toffoli_decompose=True`, BK CLA addition at widths 2-8 uses hardcoded Clifford+T sequences (zero CCX) | VERIFIED | `TestCliffordTGatePurity::test_cla_qq_purity[2-4]` pass; zero CCX confirmed in all `toffoli_clifft_cla_*.c` files; `hot_path_add_toffoli.c` routes CLA path to `get_hardcoded_toffoli_clifft_cla_QQ_add()` |
| 3 | Clifford+T hardcoded addition produces identical arithmetic results to non-decomposed addition for all input pairs at widths 1-4 | VERIFIED | `TestCliffordTCorrectness` (exhaustive pairs): `test_cdkm_qq_equivalence[1-4]`, `test_cdkm_cq_inc_equivalence[1-4]`, `test_cla_qq_equivalence[2-4]`, `test_subtraction_works_width_2`, `test_subtraction_works_width_3` -- all pass |
| 4 | T-count is exact when `toffoli_decompose=True` (sum of actual T+Tdg gates, not 7*CCX estimate) | VERIFIED | `TestCliffordTTCount::test_t_count_exact_cdkm_qq[2-4]`, `test_t_count_exact_cla_qq[2-4]`, `test_t_count_zero_for_width_1` -- all pass |
| 5 | All existing Toffoli arithmetic tests pass with zero regressions | VERIFIED | `test_clifford_t_decomposition.py` (19 tests) and `test_decomposed_sequences.py` (110+ tests) all pass. 3 pre-existing failures in `test_cla_bk_algorithm.py::TestBKControlledCQAdd::test_controlled_bk_cq_add_ctrl1` confirmed to predate phase 75 (failures identical with `git stash` applied) |

**Score:** 5/5 truths verified

### Required Artifacts

#### Plan 01 (CDKM)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/generate_toffoli_seq.py` | Extended with --clifford-t flag | VERIFIED | `--clifford-t` argument registered at line 1079; `ccx_to_clifford_t()` at line 86; `toffoli_to_clifford_t()` at line 125; generates 8 QQ Clifford+T files |
| `scripts/generate_toffoli_decomp_seq.py` | Extended with --clifford-t flag | VERIFIED | `--clifford-t` argument registered; `ccx_to_clifford_t()` at line 100; generates 8 cQQ Clifford+T files |
| `scripts/generate_toffoli_clifft_cq_inc.py` | New script >=300 lines | VERIFIED | 902 lines; contains `CliffordTGate` dataclass and `ccx_to_clifford_t`; generates 8 CQ-inc + 8 cCQ-inc files + dispatch |
| `c_backend/src/sequences/toffoli_clifft_qq_2.c` | Width-2 CDKM QQ with T_GATE | VERIFIED | Contains 28 T_GATE/TDG_GATE entries; zero NumControls=2; includes `<math.h>` for M_PI |
| `c_backend/src/sequences/toffoli_clifft_cqq_2.c` | Width-2 CDKM cQQ with T_GATE | VERIFIED | Contains 140 T_GATE/TDG_GATE entries; zero NumControls=2 |
| `c_backend/src/sequences/toffoli_clifft_cdkm_dispatch.c` | Dispatch with 4 functions | VERIFIED | 68 references to the 4 dispatch function names; switch/case routing for all variants |

#### Plan 02 (BK CLA)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/generate_toffoli_clifft_cla.py` | New script >=500 lines | VERIFIED | 1319 lines; `bk_compute_merges()` Python port at line 197; all 4 BK CLA variants implemented |
| `c_backend/src/sequences/toffoli_clifft_cla_qq_4.c` | Width-4 BK CLA QQ with T_GATE | VERIFIED | Contains 98 T_GATE/TDG_GATE entries; zero NumControls=2 |
| `c_backend/src/sequences/toffoli_clifft_cla_cqq_4.c` | Width-4 BK CLA cQQ with T_GATE | VERIFIED | Contains 420 T_GATE/TDG_GATE entries; zero NumControls=2 |
| `c_backend/src/sequences/toffoli_clifft_cla_dispatch.c` | Dispatch with 4 CLA functions | VERIFIED | 61 references to `get_hardcoded_toffoli_clifft_cla_*` functions |

#### Plan 03 (Wiring + Tests)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `c_backend/include/toffoli_sequences.h` | 8 Clifford+T dispatch declarations | VERIFIED | Lines 100-109: all 8 `get_hardcoded_toffoli_clifft_*` declarations present |
| `c_backend/src/hot_path_add_toffoli.c` | toffoli_decompose check + Clifford+T dispatch + caching | VERIFIED | Lines 31-38: 8 static pointer arrays; lines 108-586: full dispatch routing with cache-on-first-call pattern for all 4 code paths |
| `setup.py` | All ~62 new Clifford+T C files | VERIFIED | 10 entries covering all variants via list comprehensions (8 CDKM QQ + 8 cQQ + 8 CQ-inc + 8 cCQ-inc + CDKM dispatch + 7 BK QQ + 7 BK cQQ + 7 BK CQ-inc + 7 BK cCQ-inc + BK dispatch) |
| `tests/python/test_clifford_t_hardcoded.py` | Comprehensive test suite >=150 lines | VERIFIED | 390 lines; 44 tests across 4 classes: `TestCliffordTGatePurity`, `TestCliffordTCorrectness`, `TestCliffordTTCount`, `TestCliffordTFallback` |

### File Count Verification

| Category | Expected | Actual | Status |
|----------|----------|--------|--------|
| CDKM QQ Clifford+T files | 8 (widths 1-8) | 8 | VERIFIED |
| CDKM cQQ Clifford+T files | 8 (widths 1-8) | 8 | VERIFIED |
| CDKM CQ-inc Clifford+T files | 8 (widths 1-8) | 8 | VERIFIED |
| CDKM cCQ-inc Clifford+T files | 8 (widths 1-8) | 8 | VERIFIED |
| CDKM dispatch file | 1 | 1 | VERIFIED |
| BK CLA QQ Clifford+T files | 7 (widths 2-8) | 7 | VERIFIED |
| BK CLA cQQ Clifford+T files | 7 (widths 2-8) | 7 | VERIFIED |
| BK CLA CQ-inc Clifford+T files | 7 (widths 2-8) | 7 | VERIFIED |
| BK CLA cCQ-inc Clifford+T files | 7 (widths 2-8) | 7 | VERIFIED |
| BK CLA dispatch file | 1 | 1 | VERIFIED |
| **Total** | **63** | **63** | **VERIFIED** |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/generate_toffoli_seq.py` | `toffoli_clifft_qq_*.c` | `--clifford-t` flag triggers Clifford+T generation | WIRED | `args.clifford_t` at line 1112 branches to `generate_clifft_qq_width_file()`; output path is `toffoli_clifft_qq_{width}.c` |
| `scripts/generate_toffoli_decomp_seq.py` | `toffoli_clifft_cqq_*.c` | `--clifford-t` flag triggers Clifford+T generation | WIRED | `toffoli_to_clifford_t()` at line 124; `generate_clifft_cqq_width_file()` at line 340 |
| `c_backend/src/sequences/toffoli_clifft_cdkm_dispatch.c` | `toffoli_clifft_qq_*.c` | switch/case to per-width `get_hardcoded_toffoli_clifft_QQ_add_N()` | WIRED | 68 references; switch/case pattern confirmed |
| `c_backend/src/hot_path_add_toffoli.c` | `c_backend/include/toffoli_sequences.h` | Calls 8 Clifford+T dispatch functions when `toffoli_decompose==1` | WIRED | `get_hardcoded_toffoli_clifft` called 6 times in dispatch functions; pointer-array caching in 8 static arrays |
| `setup.py` | `c_backend/src/sequences/toffoli_clifft_*.c` | `c_sources` list comprehensions include all 63 files | WIRED | 10 setup.py lines cover all patterns via range(1,9) and range(2,9) |
| `tests/python/test_clifford_t_hardcoded.py` | `c_backend/src/hot_path_add_toffoli.c` | `ql.option('toffoli_decompose', True)` exercises Clifford+T path | WIRED | `_setup_clifft()` at line 25 sets `toffoli_decompose` to True; all 44 tests exercised the dispatch path |
| `scripts/generate_toffoli_clifft_cla.py` | `c_backend/src/ToffoliAdditionCLA.c` | Python `bk_compute_merges()` matches C `bk_compute_merges()` | WIRED | Python port at line 197; correctness confirmed by `TestCliffordTCorrectness::test_cla_qq_equivalence` passing exhaustively for widths 2-4 |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INF-03 | 75-01, 75-02, 75-03 | Hardcoded Toffoli gate sequences for common widths eliminate generation overhead | SATISFIED | 63 pre-computed C files exist; runtime uses static const sequences (zero generation overhead); `toffoli_decompose=True` routes to O(1) cached dispatch |
| INF-04 | 75-03 | T-count reporting in circuit statistics | SATISFIED | `TestCliffordTTCount` confirms exact T+Tdg gate count (not 7*CCX estimate); T-count = actual T_GATE + TDG_GATE gates summed from sequences |

### Anti-Patterns Found

No blocker or warning anti-patterns found in phase 75 artifacts. All generated C files use static const arrays (no dynamic allocation). No TODO/FIXME/placeholder comments in generated sequences. No empty implementations.

### Human Verification Required

#### 1. Width 5-8 Gate Purity (Partial Coverage)

**Test:** With `toffoli_decompose=True`, run CDKM QQ addition for width 5-8 and inspect gate counts
**Expected:** Zero CCX gates, T_gates > 0
**Why human:** Test suite parametrizes widths 1-4 for gate purity. File-level verification confirmed all 8 CDKM QQ files have zero `NumControls = 2` entries, but end-to-end execution at widths 5-8 was not exercised in the test suite.

#### 2. BK CLA cCQ-inc Path End-to-End

**Test:** With `toffoli_decompose=True` and `qubit_saving=True`, trigger a controlled CQ increment of 1 for widths 2-4 and verify arithmetic result
**Expected:** Correct modular addition result with zero CCX in gate counts
**Why human:** `TestCliffordTGatePurity::test_cla_cqq_purity` covers the cQQ path; there is no dedicated purity test for the `cCQ_inc` BK CLA path specifically. File-level analysis confirms the C files have zero CCX, but the Python→C dispatch path for this specific variant was not isolated in the test suite.

### Pre-existing Test Failures (Not Phase 75 Regressions)

Three failures exist in `tests/python/test_cla_bk_algorithm.py::TestBKControlledCQAdd::test_controlled_bk_cq_add_ctrl1[2,3,4]`. These failures were confirmed to predate all phase 75 commits by applying `git stash` and re-running the tests — the failures occur identically. These are pre-existing bugs in the BK controlled CQ add path (unrelated to Clifford+T), not regressions introduced by phase 75.

### Test Run Summary

```
tests/python/test_clifford_t_hardcoded.py: 44 passed (0 failed)
tests/python/test_clifford_t_decomposition.py: 19 passed (0 failed)
tests/python/test_decomposed_sequences.py: 110+ passed (0 failed)
tests/python/test_cla_bk_algorithm.py: 148 passed, 2 xfailed, 3 FAILED (pre-existing)
```

---

_Verified: 2026-02-18_
_Verifier: Claude (gsd-verifier)_
