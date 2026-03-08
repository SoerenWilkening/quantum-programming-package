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

### v8.0 Quantum Chess Walk Rewrite (In Progress)

**Milestone Goal:** Rewrite the chess quantum walk to evaluate move legality in superposition using quantum predicates built from standard ql constructs, replace classical pre-filtering with all-moves enumeration and quantum validity checking, redesign diffusion for large branching factors, and optimize compile infrastructure with numpy-based qubit set operations.

- [x] **Phase 112: Compile Infrastructure Optimization** - Numpy-based qubit set operations in compile.py and call_graph.py with profiled before/after validation (completed 2026-03-08)
- [x] **Phase 113: Diffusion Redesign & Move Enumeration** - Arithmetic counting circuit replacing combinatorial diffusion explosion, plus all-moves enumeration table (completed 2026-03-08)
- [x] **Phase 114: Core Quantum Predicates** - Piece-exists and no-friendly-capture predicates using standard ql constructs with @ql.compile(inverse=True) (completed 2026-03-08)
- [ ] **Phase 115: Check Detection & Combined Predicate** - King-safety predicate via attack tables and combined move legality predicate composing all conditions
- [ ] **Phase 116: Walk Integration & Demo** - Full walk rewrite replacing classical pre-filtering with quantum predicates, end-to-end demo as framework showcase

## Phase Details

### Phase 112: Compile Infrastructure Optimization
**Goal**: Compile infrastructure uses numpy for qubit set operations, reducing Python loop overhead in compile.py and call_graph.py
**Depends on**: Nothing (independent of chess features)
**Requirements**: COMP-01, COMP-02, COMP-03
**Success Criteria** (what must be TRUE):
  1. compile.py qubit_set construction uses numpy operations (np.unique/np.concatenate) instead of Python set.update() loops
  2. call_graph.py DAGNode overlap computation uses numpy arrays (np.intersect1d) for pairwise qubit overlap detection
  3. All existing compile tests (186+ invocations) pass with zero regressions after numpy migration
  4. Profiling data shows measurable improvement (or documents that overhead is negligible for current workload sizes)
**Plans:** 2/2 plans complete

Plans:
- [ ] 112-01-PLAN.md — Profiling baseline and call_graph.py numpy overlap migration
- [ ] 112-02-PLAN.md — compile.py numpy qubit_set construction and post-migration profiling

### Phase 113: Diffusion Redesign & Move Enumeration
**Goal**: Walk circuits can handle large branching factors (100+ children) without combinatorial explosion, and all geometrically possible moves are enumerated for quantum evaluation
**Depends on**: Nothing (independent of Phase 112)
**Requirements**: WALK-01, WALK-03
**Success Criteria** (what must be TRUE):
  1. All-moves enumeration table contains every geometrically possible (piece_type, src, dst) triple for knights (up to 8 per square) and kings (up to 8 per square) without legality filtering
  2. Diffusion operator uses an arithmetic counting circuit (summing validity bits into a count register) instead of O(2^d_max) itertools.combinations pattern enumeration
  3. Diffusion circuit generation is O(d_max) in gate count — no exponential or superlinear blowup
  4. Existing walk tests continue to pass (diffusion redesign does not break SAT demo or small-board cases)
**Plans:** 3/3 plans complete

Plans:
- [ ] 113-01-PLAN.md — All-moves enumeration table builder (build_move_table in chess_encoding.py)
- [ ] 113-02-PLAN.md — Counting-based diffusion replacing combinatorial enumeration in walk.py
- [ ] 113-03-PLAN.md — Wire chess_walk.py to shared counting diffusion and cleanup

### Phase 114: Core Quantum Predicates
**Goal**: Users can evaluate piece-exists and no-friendly-capture conditions in superposition using standard ql constructs
**Depends on**: Nothing (uses existing framework primitives)
**Requirements**: PRED-01, PRED-02, PRED-05
**Success Criteria** (what must be TRUE):
  1. Quantum piece-exists predicate checks whether a specific piece type occupies a source square via `with` conditional on board qarray elements, returning a qbool result
  2. Quantum no-friendly-capture predicate rejects moves where target square is occupied by same-color piece, using `with` conditional on board qarray elements
  3. Both predicates use `@ql.compile(inverse=True)` for automatic ancilla uncomputation and compiled replay
  4. Predicates produce correct results verified against classical equivalents on small boards (2x2 or 3x3) within 17-qubit simulation limit
  5. All predicate logic uses standard ql constructs (with qbool:, operator overloading, @ql.compile) -- no raw gate emission for application logic
**Plans**: 2 plans

Plans:
- [ ] 114-01-PLAN.md — Piece-exists predicate factory with test suite and statevector verification
- [ ] 114-02-PLAN.md — No-friendly-capture predicate factory with classical equivalence tests

### Phase 115: Check Detection & Combined Predicate
**Goal**: Users can evaluate full move legality including king safety in superposition, with all conditions composed into a single predicate
**Depends on**: Phase 114
**Requirements**: PRED-03, PRED-04
**Success Criteria** (what must be TRUE):
  1. Check detection predicate verifies king is not in check after a move using pre-computed attack tables (knight L-shapes + king adjacency) evaluated via `with` conditionals on board qarray
  2. Combined move legality predicate composes piece-exists, no-friendly-capture, and check detection using standard `with qbool:` conditional nesting and boolean operators
  3. Combined predicate returns a single qbool indicating full move legality, usable as a validity flag for walk branching
  4. All predicates verified correct against classical equivalents on small boards within 17-qubit simulation limit
**Plans**: TBD

Plans:
- [ ] 115-01: TBD
- [ ] 115-02: TBD

### Phase 116: Walk Integration & Demo
**Goal**: Chess quantum walk evaluates move legality in superposition using quantum predicates instead of classical pre-filtering, serving as a showcase of the framework's expressiveness
**Depends on**: Phase 113, Phase 115
**Requirements**: WALK-02, WALK-04, WALK-05
**Success Criteria** (what must be TRUE):
  1. evaluate_children calls the quantum legality predicate per move candidate instead of the trivial always-valid check from v6.1
  2. Rewritten chess_walk.py integrates quantum predicates, all-moves enumeration, and redesigned diffusion into a complete walk step U = R_B * R_A
  3. End-to-end demo generates a valid quantum circuit for the chess walk on a KNK (king-knight-king) position with quantum legality evaluation
  4. All quantum logic in the demo uses standard ql constructs (with qbool:, operator overloading, @ql.compile, ql.array) -- no raw gate emission for application logic
  5. Demo produces circuit statistics (qubit count, gate count, depth) demonstrating the walk circuit is constructible
**Plans**: TBD

Plans:
- [ ] 116-01: TBD
- [ ] 116-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 112 -> 113 -> 114 -> 115 -> 116

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 41-44 | v1.8 | 7/7 | Complete | 2026-02-03 |
| 45-47 | v1.9 | 7/7 | Complete | 2026-02-03 |
| 48-51 | v2.0 | 8/8 | Complete | 2026-02-04 |
| 52-54 | v2.1 | 6/6 | Complete | 2026-02-05 |
| 55-61 | v2.2 | 22/22 | Complete | 2026-02-08 |
| 62-64 | v2.3 | 4/4 | Complete | 2026-02-08 |
| 65-75 | v3.0 | 35/35 | Complete | 2026-02-18 |
| 76-81 | v4.0 | 18/18 | Complete | 2026-02-22 |
| 82-89 | v4.1 | 21/21 | Complete | 2026-02-24 |
| 90-96 | v5.0 | 19/19 | Complete | 2026-02-26 |
| 97-102 | v6.0 | 11/11 | Complete | 2026-03-03 |
| 103-106 | v6.1 | 8/8 | Complete | 2026-03-05 |
| 107-111 | v7.0 | 10/10 | Complete | 2026-03-08 |
| 112. Compile Infra Opt | 2/2 | Complete    | 2026-03-08 | - |
| 113. Diffusion & Enum | 3/3 | Complete    | 2026-03-08 | - |
| 114. Core Predicates | 2/2 | Complete    | 2026-03-08 | - |
| 115. Check & Combined | v8.0 | 0/TBD | Not started | - |
| 116. Walk Integration | v8.0 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 shipped: 2026-02-05*
*Milestone v2.2 shipped: 2026-02-08*
*Milestone v2.3 shipped: 2026-02-08*
*Milestone v3.0 shipped: 2026-02-18*
*Milestone v4.0 shipped: 2026-02-22*
*Milestone v4.1 shipped: 2026-02-24*
*Milestone v5.0 shipped: 2026-02-26*
*Milestone v6.0 shipped: 2026-03-03*
*Milestone v6.1 shipped: 2026-03-05*
*Milestone v7.0 shipped: 2026-03-08*
*Milestone v8.0 roadmap created: 2026-03-08*
