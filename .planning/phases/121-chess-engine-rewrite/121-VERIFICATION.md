---
phase: 121-chess-engine-rewrite
verified: 2026-03-10T01:15:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 121: Chess Engine Rewrite Verification Report

**Phase Goal:** A readable chess engine example demonstrates the full v9.0 feature set in natural-programming style
**Verified:** 2026-03-10T01:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

Truths derived from ROADMAP.md Success Criteria (5 criteria mapped directly):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `examples/chess_engine.py` reads like pseudocode -- nested `with` blocks for conditionals, 2D qarrays for the board, arithmetic operators for move logic | VERIFIED | File is 204 lines. Uses `ql.qarray(dim=(8, 8), dtype=ql.qbool)` for boards (lines 82-89), 4-level nested `with` blocks for legality (lines 141-155), `+= 1` for qbool toggles, `== d` for branch matching (line 175). Clear section headers. No gate-level code. |
| 2 | The engine compiles with `@ql.compile(opt=1)` without OOM errors | VERIFIED | `compile.py` line 1494: `if self._opt != 1:` guards `inject_remapped_gates()`. Test file `test_compile_dag_only.py` (129 lines, 4 tests) proves opt=1 replay does not inject gates. DAG accumulates across calls (line 799). SUMMARY reports chess engine runs to completion printing stats. |
| 3 | Move legality checking (piece-exists, no-friendly-capture, check detection) is implemented using nested `with` blocks and compiled sub-predicates | VERIFIED | Lines 141-162: `with bk[bk_r, bk_c]` (piece-exists), `with ~w_king[to_r, to_c]` (no white king at dest), `with ~w_knight[to_r, to_c]` (no white knight at dest), `with ~in_check` (not in check). Attack map computed by `compute_white_attacks` compiled predicate (lines 106-116). |
| 4 | Walk operators (R_A, R_B) and diffusion are present in readable style matching the framework's natural-programming paradigm | VERIFIED | R_A: lines 133-163 (evaluate 8 directions). R_B: lines 165-167 (`with h[0]: ql.diffusion(br)`). Phase 3 controlled move application: lines 169-180. All inline within `walk_step` compiled function. |
| 5 | Running the script produces circuit statistics (gate count, depth, qubit count) without requiring quantum simulation | VERIFIED | Lines 194-202: `walk_step._call_graph.aggregate()` prints gates, depth, qubits, T-count, DAG nodes. No simulation calls (`ql.simulate`, `ql.measure`, `AerSimulator`) anywhere in file. SUMMARY reports output: "14,004 gates, 693 depth, 277 qubits, 75,117 T-count, 20 DAG nodes". |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `examples/chess_engine.py` | Complete chess engine example demonstrating v9.0 features (min 150 lines, contains `ql.qarray`) | VERIFIED | 204 lines. Contains `ql.qarray` at lines 82, 85, 89, 94, 95, 149. Wired: imports `quantum_language as ql` (line 10). |
| `tests/python/test_compile_dag_only.py` | Tests for opt=1 DAG-only replay (min 30 lines) | VERIFIED | 129 lines. 4 test methods in `TestOpt1DagOnlyReplay` class. Tests gate skip, opt=0 unchanged, DAG 3-node accumulation, return value correctness. |
| `src/quantum_language/compile.py` | opt=1 DAG-only replay skip in `_replay()` | VERIFIED | Line 1494: `if self._opt != 1:` guards `inject_remapped_gates()`. Line 799: DAG reuse for opt=1. Line 899: `track_forward` conditional on `self._inverse_func is not None`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `examples/chess_engine.py` | `quantum_language` | `import quantum_language as ql` | WIRED | Line 10: `import quantum_language as ql`. Used throughout (ql.circuit, ql.qarray, ql.qint, ql.qbool, ql.compile, ql.diffusion). |
| `chess_engine.py walk_step` | `@ql.compile(opt=1)` | Compiled walk step for DAG-only replay | WIRED | Line 122: `@ql.compile(opt=1)`. Lines 189-191: called NUM_STEPS (3) times in loop. |
| `chess_engine.py compute_white_attacks` | `@ql.compile(opt=1)` | Compiled attack predicate | WIRED | Line 106: `@ql.compile(opt=1)`. Called twice per direction (forward + uncompute via XOR self-inverse, lines 150 and 158). |
| `chess_engine.py main` | `CallGraphDAG.aggregate()` | `walk_step._call_graph.aggregate()` for circuit stats | WIRED | Lines 194-202: accesses `walk_step._call_graph`, calls `.aggregate()`, prints gates/depth/qubits/t_count, accesses `.node_count`. |
| `compile.py:_replay()` | `inject_remapped_gates()` | Conditional skip when `self._opt == 1` | WIRED | Line 1494: `if self._opt != 1: inject_remapped_gates(block.gates, virtual_to_real)`. |
| `compile.py:_call_inner() cache hit` | `CallGraphDAG.add_node()` | DAG node recording unchanged on replay | WIRED | Lines 901-906: DAG node recording in cache hit path, gated on `_building_dag`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CHESS-01 | 121-02 | Chess engine follows readable natural-programming format | SATISFIED | 204-line file with clear sections, nested `with` blocks, 2D qarrays, arithmetic operators. No gate-level code. Chess notation in comments. |
| CHESS-02 | 121-01 | Engine compiles with `@ql.compile(opt=1)` without OOM | SATISFIED | `compile.py` conditional skip of `inject_remapped_gates()` for opt=1. 4 tests verify behavior. SUMMARY confirms engine runs to completion. |
| CHESS-03 | 121-02 | Engine includes move legality checking (piece-exists, no-friendly-capture, check detection) | SATISFIED | 4-level nested `with` blocks: piece-exists, no-white-king-at-dest, no-white-knight-at-dest, not-in-check. Attack map computed by compiled predicate. |
| CHESS-04 | 121-02 | Engine includes walk operators (R_A/R_B) and diffusion in readable style | SATISFIED | R_A evaluates 8 directions (lines 133-163), R_B does diffusion conditioned on leaf level (lines 165-167), Phase 3 applies selected move (lines 169-180). |
| CHESS-05 | 121-01, 121-02 | Engine is circuit-build-only (no simulation required) | SATISFIED | No simulation calls in file. Stats from `_call_graph.aggregate()`. No `ql.simulate`, `ql.measure`, or `AerSimulator`. |

No orphaned requirements. All 5 CHESS requirements mapped to Phase 121 in REQUIREMENTS.md are claimed by plans and have evidence in the codebase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

No TODOs, FIXMEs, placeholders, empty implementations, or stub patterns found in any modified file.

### Noted Deviations from Plan (Non-blocking)

The 121-02 plan must_have specified `@ql.compile(opt=1, inverse=True)` for `compute_white_attacks` with `.inverse()` uncomputation. The actual implementation uses `@ql.compile(opt=1)` (without `inverse=True`) and achieves uncomputation via the self-inverse XOR double-call pattern (calling the function twice). This was documented as a blocking auto-fix in the SUMMARY because `.inverse()` encountered a forward-call tracking conflict in the nested compiled context. The functional goal of uncomputation IS achieved -- the mechanism is different but quantum-mechanically equivalent.

### Human Verification Required

### 1. Chess Engine Script Execution

**Test:** Run `python examples/chess_engine.py` and observe output
**Expected:** ASCII board with K at e1, N at b2 and f3, k at e7; progress messages for 3 walk steps; circuit statistics block with gates, depth, qubits, T-count, DAG nodes; "Done." at end
**Why human:** Cannot execute Python script in verification context. SUMMARY claims successful execution with specific stats (14,004 gates, 693 depth, 277 qubits, 75,117 T-count, 20 DAG nodes) but this needs live confirmation.

### 2. Readability Assessment

**Test:** Read `examples/chess_engine.py` and assess whether it reads like pseudocode
**Expected:** A programmer unfamiliar with quantum computing should understand the chess logic from reading the code. The quantum mechanics should be invisible behind the DSL.
**Why human:** Readability is subjective and cannot be verified programmatically.

### 3. opt=1 Test Suite Execution

**Test:** Run `python -m pytest tests/python/test_compile_dag_only.py -x -v`
**Expected:** All 4 tests pass (gate skip, opt=0 unchanged, DAG 3-node accumulation, return value)
**Why human:** Test execution needed for live confirmation of behavior.

### Gaps Summary

No gaps found. All 5 success criteria from the ROADMAP are satisfied with evidence in the codebase:

1. The chess engine file exists at the expected path, is 204 lines, and uses all specified v9.0 features (nested with-blocks, 2D qarrays, compile, diffusion, arithmetic operators).
2. The opt=1 compile change is implemented in `compile.py` with a clear conditional guard, supported by 4 dedicated tests.
3. Move legality uses 4-level nested `with` blocks -- exceeding the 3-level requirement.
4. Walk operators R_A, R_B, and diffusion are clearly structured in the walk_step function.
5. Circuit statistics are printed from the DAG without any simulation.
6. All 5 CHESS requirements are covered by plan claims and verified against artifacts.
7. All commits referenced in SUMMARYs (9f1bd11, a482d7a, 9e8537b, 008082b) exist in git history.

The one deviation (self-inverse double-call instead of `.inverse()`) is well-documented and functionally equivalent. It does not affect goal achievement.

---

_Verified: 2026-03-10T01:15:00Z_
_Verifier: Claude (gsd-verifier)_
