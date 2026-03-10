# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (shipped 2026-02-04) -- See `milestones/v2.0-ROADMAP.md`
- v2.1 Compile Enhancements -- Phases 52-54 (shipped 2026-02-05) -- See `milestones/v2.1-ROADMAP.md`
- v2.2 Performance Optimization -- Phases 55-61 (shipped 2026-02-08) -- See `milestones/v2.2-ROADMAP.md`
- v2.3 Hardcoding Right-Sizing -- Phases 62-64 (shipped 2026-02-08) -- See `milestones/v2.3-ROADMAP.md`
- v3.0 Fault-Tolerant Arithmetic -- Phases 65-75 (shipped 2026-02-18) -- See `milestones/v3.0-ROADMAP.md`
- v4.0 Grover's Algorithm -- Phases 76-81 (shipped 2026-02-22) -- See `milestones/v4.0-ROADMAP.md`
- v4.1 Quality & Efficiency -- Phases 82-89 (shipped 2026-02-24) -- See `milestones/v4.1-ROADMAP.md`
- v5.0 Advanced Arithmetic & Compilation -- Phases 90-96 (shipped 2026-02-26) -- See `milestones/v5.0-ROADMAP.md`
- v6.0 Quantum Walk Primitives -- Phases 97-102 (shipped 2026-03-03) -- See `milestones/v6.0-ROADMAP.md`
- v6.1 Quantum Chess Demo -- Phases 103-106 (shipped 2026-03-05) -- See `milestones/v6.1-ROADMAP.md`
- v7.0 Compile Infrastructure -- Phases 107-111 (shipped 2026-03-08) -- See `milestones/v7.0-ROADMAP.md`
- v8.0 Quantum Chess Walk Rewrite -- Phases 112-116 (shipped 2026-03-09) -- See `milestones/v8.0-ROADMAP.md`

## Phases

<details>
<summary>v1.8 Quantum Copy, Array Mutability & Uncomputation Fix (Phases 41-44) -- SHIPPED 2026-02-03</summary>

- [x] Phase 41: Uncomputation Fix (2/2 plans) -- completed 2026-02-02
- [x] Phase 42: Quantum Copy Foundation (1/1 plan) -- completed 2026-02-02
- [x] Phase 43: Copy-Aware Binary Ops (2/2 plans) -- completed 2026-02-02
- [x] Phase 44: Array Mutability (2/2 plans) -- completed 2026-02-03

</details>

<details>
<summary>v1.9 Pixel-Art Circuit Visualization (Phases 45-47) -- SHIPPED 2026-02-03</summary>

- [x] Phase 45: Data Extraction Bridge (2/2 plans) -- completed 2026-02-03
- [x] Phase 46: Core Renderer (3/3 plans) -- completed 2026-02-03
- [x] Phase 47: Detail Mode & Public API (2/2 plans) -- completed 2026-02-03

</details>

<details>
<summary>v2.0 Function Compilation (Phases 48-51) -- SHIPPED 2026-02-04</summary>

- [x] Phase 48: Core Capture-Replay (2/2 plans) -- completed 2026-02-04
- [x] Phase 49: Optimization & Uncomputation (2/2 plans) -- completed 2026-02-04
- [x] Phase 50: Controlled Context (2/2 plans) -- completed 2026-02-04
- [x] Phase 51: Differentiators & Polish (2/2 plans) -- completed 2026-02-04

</details>

<details>
<summary>v2.1 Compile Enhancements (Phases 52-54) -- SHIPPED 2026-02-05</summary>

- [x] Phase 52: Ancilla Tracking & Inverse Qubit Reuse (2/2 plans) -- completed 2026-02-04
- [x] Phase 53: Qubit-Saving Auto-Uncompute (2/2 plans) -- completed 2026-02-04
- [x] Phase 54: qarray Support in @ql.compile (2/2 plans) -- completed 2026-02-05

</details>

<details>
<summary>v2.2 Performance Optimization (Phases 55-61) -- SHIPPED 2026-02-08</summary>

- [x] Phase 55: Profiling Infrastructure (3/3 plans) -- completed 2026-02-05
- [x] Phase 56: Forward/Inverse Depth Fix (2/2 plans) -- completed 2026-02-05
- [x] Phase 57: Cython Optimization (3/3 plans) -- completed 2026-02-05
- [x] Phase 58: Hardcoded Sequences (1-8 bit) (3/3 plans) -- completed 2026-02-05
- [x] Phase 59: Hardcoded Sequences (9-16 bit) (4/4 plans) -- completed 2026-02-06
- [x] Phase 60: C Hot Path Migration (4/4 plans) -- completed 2026-02-06
- [x] Phase 61: Memory Optimization (3/3 plans) -- completed 2026-02-08

</details>

<details>
<summary>v2.3 Hardcoding Right-Sizing (Phases 62-64) -- SHIPPED 2026-02-08</summary>

- [x] Phase 62: Measurement (2/2 plans) -- completed 2026-02-08
- [x] Phase 63: Right-Sizing Implementation (1/1 plan) -- completed 2026-02-08
- [x] Phase 64: Regression Verification (1/1 plan) -- completed 2026-02-08

</details>

<details>
<summary>v3.0 Fault-Tolerant Arithmetic (Phases 65-75) -- SHIPPED 2026-02-18</summary>

- [x] Phase 65: Infrastructure Prerequisites (3/3 plans) -- completed 2026-02-14
- [x] Phase 66: CDKM Ripple-Carry Adder (3/3 plans) -- completed 2026-02-14
- [x] Phase 67: Controlled Adder & Backend Dispatch (3/3 plans) -- completed 2026-02-14
- [x] Phase 68: Schoolbook Multiplication (2/2 plans) -- completed 2026-02-15
- [x] Phase 69: Controlled Multiplication & Division (3/3 plans) -- completed 2026-02-15
- [x] Phase 70: Cross-Backend Verification (2/2 plans) -- completed 2026-02-15
- [x] Phase 71: Carry Look-Ahead Adder (6/6 plans) -- completed 2026-02-17
- [x] Phase 72: Performance Polish (3/3 plans) -- completed 2026-02-18
- [x] Phase 73: Toffoli CQ/cCQ Classical-Bit Gate Reduction (2/2 plans) -- completed 2026-02-17
- [x] Phase 74: MCX/CCX Gate Decomposition & Sequence Refactoring (5/5 plans) -- completed 2026-02-17
- [x] Phase 75: Clifford+T Decomposed Sequence Generation (3/3 plans) -- completed 2026-02-18

</details>

<details>
<summary>v4.0 Grover's Algorithm (Phases 76-81) -- SHIPPED 2026-02-22</summary>

- [x] Phase 76: Gate Primitive Exposure (6/6 plans) -- completed 2026-02-20
- [x] Phase 77: Oracle Infrastructure (2/2 plans) -- completed 2026-02-20
- [x] Phase 78: Diffusion Operator (3/3 plans) -- completed 2026-02-20
- [x] Phase 79: Grover Search Integration (2/2 plans) -- completed 2026-02-22
- [x] Phase 80: Oracle Auto-Synthesis & Adaptive Search (3/3 plans) -- completed 2026-02-22
- [x] Phase 81: Amplitude Estimation - IQAE (2/2 plans) -- completed 2026-02-22

</details>

<details>
<summary>v4.1 Quality & Efficiency (Phases 82-89) -- SHIPPED 2026-02-24</summary>

- [x] Phase 82: Infrastructure & Dependency Fixes (2/2 plans) -- completed 2026-02-23
- [x] Phase 83: Tech Debt Cleanup (2/2 plans) -- completed 2026-02-23
- [x] Phase 84: Security Hardening (2/2 plans) -- completed 2026-02-23
- [x] Phase 85: Optimizer Fix & Improvement (3/3 plans) -- completed 2026-02-23
- [x] Phase 86: QFT Bug Fixes (3/3 plans) -- completed 2026-02-24
- [x] Phase 87: Scope & Segfault Fixes (4/4 plans) -- completed 2026-02-24
- [x] Phase 88: Binary Size Reduction (2/2 plans) -- completed 2026-02-24
- [x] Phase 89: Test Coverage (3/3 plans) -- completed 2026-02-24

</details>

<details>
<summary>v5.0 Advanced Arithmetic & Compilation (Phases 90-96) -- SHIPPED 2026-02-26</summary>

- [x] Phase 90: Quantum Counting (2/2 plans) -- completed 2026-02-24
- [x] Phase 91: Arithmetic Bug Fixes (3/3 plans) -- completed 2026-02-24
- [x] Phase 92: Modular Toffoli Arithmetic (3/3 plans) -- completed 2026-02-25
- [x] Phase 93: Depth/Ancilla Tradeoff (2/2 plans) -- completed 2026-02-25
- [x] Phase 94: Parametric Compilation (3/3 plans) -- completed 2026-02-25
- [x] Phase 95: Verification & Requirements Closure (3/3 plans) -- completed 2026-02-26
- [x] Phase 96: v5.0 Tech Debt Cleanup (3/3 plans) -- completed 2026-02-26

</details>

<details>
<summary>v6.0 Quantum Walk Primitives (Phases 97-102) -- SHIPPED 2026-03-03</summary>

- [x] Phase 97: Tree Encoding & Predicate Interface (2/2 plans) -- completed 2026-03-02
- [x] Phase 98: Local Diffusion Operator (2/2 plans) -- completed 2026-03-02
- [x] Phase 99: Walk Operators (2/2 plans) -- completed 2026-03-02
- [x] Phase 100: Variable Branching (2/2 plans) -- completed 2026-03-02
- [x] Phase 101: Detection & Demo (2/2 plans) -- completed 2026-03-03
- [x] Phase 102: Verification & Cosmetic Cleanup (1/1 plan) -- completed 2026-03-03

</details>

<details>
<summary>v6.1 Quantum Chess Demo (Phases 103-106) -- SHIPPED 2026-03-05</summary>

- [x] Phase 103: Chess Board Encoding & Legal Moves (2/2 plans) -- completed 2026-03-03
- [x] Phase 104: Walk Register Scaffolding & Local Diffusion (2/2 plans) -- completed 2026-03-03
- [x] Phase 105: Full Walk Operators (2/2 plans) -- completed 2026-03-05
- [x] Phase 106: Demo Scripts (2/2 plans) -- completed 2026-03-05

</details>

<details>
<summary>v7.0 Compile Infrastructure (Phases 107-111) -- SHIPPED 2026-03-08</summary>

- [x] Phase 107: Call Graph DAG Foundation (2/2 plans) -- completed 2026-03-05
- [x] Phase 108: Call Graph Analysis & Visualization (2/2 plans) -- completed 2026-03-06
- [x] Phase 109: Selective Sequence Merging (2/2 plans) -- completed 2026-03-06
- [x] Phase 110: Merge Verification & Regression (3/3 plans) -- completed 2026-03-07
- [x] Phase 111: Phase 107 Verification Closure (1/1 plan) -- completed 2026-03-08

</details>

<details>
<summary>v8.0 Quantum Chess Walk Rewrite (Phases 112-116) -- SHIPPED 2026-03-09</summary>

- [x] Phase 112: Compile Infrastructure Optimization (2/2 plans) -- completed 2026-03-08
- [x] Phase 113: Diffusion Redesign & Move Enumeration (3/3 plans) -- completed 2026-03-08
- [x] Phase 114: Core Quantum Predicates (2/2 plans) -- completed 2026-03-08
- [x] Phase 115: Check Detection & Combined Predicate (2/2 plans) -- completed 2026-03-09
- [x] Phase 116: Walk Integration & Demo (2/2 plans) -- completed 2026-03-09

</details>

### v9.0 Nested Controls & Chess Engine (In Progress)

**Milestone Goal:** Enable arbitrary-depth nested `with qbool:` blocks via Toffoli AND control composition, fix 2D qarray support, and rewrite the chess engine in readable natural-programming style.

- [x] **Phase 117: Control Stack Infrastructure** - Replace flat control globals with stack and add Toffoli AND helpers (completed 2026-03-09)
- [x] **Phase 118: Nested With-Block Rewrite** - Rewrite `__enter__`/`__exit__` with push/pop semantics and AND-ancilla lifecycle (completed 2026-03-09)
- [x] **Phase 119: Compile Compatibility** - Verify and fix `@ql.compile` with nested control contexts (completed 2026-03-09)
- [x] **Phase 120: 2D Qarray Support** - Fix 2D qarray construction and indexing (completed 2026-03-09)
- [ ] **Phase 121: Chess Engine Rewrite** - Rewrite chess engine in readable natural-programming style with nested `with` blocks

## Phase Details

### Phase 117: Control Stack Infrastructure
**Goal**: Framework has a control stack data structure and Toffoli AND emission primitives that all downstream features depend on
**Depends on**: Nothing (first phase in v9.0)
**Requirements**: CTRL-02, CTRL-03
**Success Criteria** (what must be TRUE):
  1. `_control_stack` list replaces flat `_controlled`/`_control_bool` globals with backward-compatible accessor wrappers (`_get_controlled()` and `_get_control_bool()` work identically for single-level use)
  2. `emit_ccx` function emits a Toffoli gate directly without going through the heavyweight `&` operator
  3. `_toffoli_and` / `_uncompute_toffoli_and` helpers allocate an AND-ancilla qubit and clean it up via reverse Toffoli
  4. Existing single-level `with` blocks still produce correct circuits (stack depth 0 and 1 behave identically to old globals)
**Plans**: 2 plans

Plans:
- [x] 117-01-PLAN.md -- Control stack global + gate emission primitives (emit_ccx, _toffoli_and, _uncompute_toffoli_and)
- [x] 117-02-PLAN.md -- Wire stack into __enter__/__exit__, compile.py, oracle.py + regression verification

### Phase 118: Nested With-Block Rewrite
**Goal**: Users can nest `with qbool:` blocks at arbitrary depth with correct multi-controlled gate emission and automatic ancilla cleanup
**Depends on**: Phase 117
**Requirements**: CTRL-01, CTRL-04, CTRL-05
**Success Criteria** (what must be TRUE):
  1. `with a: with b: x += 1` produces a doubly-controlled addition (two control qubits composed via Toffoli AND into a combined control ancilla)
  2. Controlled XOR (`~qbool`) works inside `with` blocks without raising NotImplementedError
  3. All existing single-level `with` block tests pass with zero regressions
  4. The 6 xfail tests in `test_nested_with_blocks.py` pass (xfail markers removed)
  5. 3+ level nesting produces correct multi-controlled circuits (each level adds one AND-ancilla)
**Plans**: 2 plans

Plans:
- [x] 118-01-PLAN.md -- AND-composition in __enter__/__exit__, width validation, rewrite xfail tests
- [x] 118-02-PLAN.md -- 3+ level nesting tests and full regression verification

### Phase 119: Compile Compatibility
**Goal**: `@ql.compile` captured functions work correctly inside nested `with` blocks
**Depends on**: Phase 118
**Requirements**: CTRL-06
**Success Criteria** (what must be TRUE):
  1. A compiled function called inside a 2-level nested `with` block emits all gates with the correct combined control qubit
  2. Controlled variant derivation handles the AND-ancilla as control qubit during both capture and replay
  3. Compile save/restore correctly preserves and restores the full control stack (not just top entry)
**Plans**: 1 plan

Plans:
- [x] 119-01-PLAN.md -- Compile + nested with tests (replay, inverse, adjoint, compiled-calling-compiled, regression)

### Phase 120: 2D Qarray Support
**Goal**: Users can create and index 2D quantum arrays for board-like data structures
**Depends on**: Nothing (independent of Phases 117-119, must complete before Phase 121)
**Requirements**: ARR-01, ARR-02
**Success Criteria** (what must be TRUE):
  1. `ql.qarray(dim=(8, 8), dtype=ql.qbool)` creates a 64-element qarray accessible as a 2D grid without TypeError
  2. `arr[r, c]` reads the correct element and `arr[r, c] |= flag` mutates it in place
  3. Existing 1D qarray tests pass with zero regressions
**Plans**: 1 plan

Plans:
- [ ] 120-01-PLAN.md -- Fix __setitem__ bug, add 2D tests, update CLAUDE.md to ql.qarray()

### Phase 121: Chess Engine Rewrite
**Goal**: A readable chess engine example demonstrates the full v9.0 feature set in natural-programming style
**Depends on**: Phase 118, Phase 119, Phase 120
**Requirements**: CHESS-01, CHESS-02, CHESS-03, CHESS-04, CHESS-05
**Success Criteria** (what must be TRUE):
  1. `examples/chess_engine.py` reads like pseudocode -- nested `with` blocks for conditionals, 2D qarrays for the board, arithmetic operators for move logic
  2. The engine compiles with `@ql.compile(opt=1)` without OOM errors
  3. Move legality checking (piece-exists, no-friendly-capture, check detection) is implemented using nested `with` blocks and compiled sub-predicates
  4. Walk operators (R_A, R_B) and diffusion are present in readable style matching the framework's natural-programming paradigm
  5. Running the script produces circuit statistics (gate count, depth, qubit count) without requiring quantum simulation
**Plans**: 2 plans

Plans:
- [ ] 121-01-PLAN.md -- opt=1 DAG-only replay fix in compile.py (OOM prevention + DAG stats)
- [ ] 121-02-PLAN.md -- Chess engine rewrite with nested with-blocks, 2D qarrays, walk operators

## Progress

**Execution Order:**
Phases execute in numeric order: 117 -> 118 -> 119 -> 120 -> 121
(Phase 120 is independent and can execute in parallel with 117-119 if desired)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-64 | v1.0-v2.3 | 166/166 | Complete | 2026-02-08 |
| 65-75 | v3.0 | 35/35 | Complete | 2026-02-18 |
| 76-81 | v4.0 | 18/18 | Complete | 2026-02-22 |
| 82-89 | v4.1 | 21/21 | Complete | 2026-02-24 |
| 90-96 | v5.0 | 19/19 | Complete | 2026-02-26 |
| 97-102 | v6.0 | 11/11 | Complete | 2026-03-03 |
| 103-106 | v6.1 | 8/8 | Complete | 2026-03-05 |
| 107-111 | v7.0 | 10/10 | Complete | 2026-03-08 |
| 112-116 | v8.0 | 11/11 | Complete | 2026-03-09 |
| 117. Control Stack Infrastructure | 2/2 | Complete    | 2026-03-09 | - |
| 118. Nested With-Block Rewrite | 2/2 | Complete    | 2026-03-09 | - |
| 119. Compile Compatibility | 1/1 | Complete    | 2026-03-09 | - |
| 120. 2D Qarray Support | 1/1 | Complete    | 2026-03-09 | - |
| 121. Chess Engine Rewrite | v9.0 | 0/2 | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v9.0 roadmap added: 2026-03-09*
