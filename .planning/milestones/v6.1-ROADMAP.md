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
- v6.1 Quantum Chess Demo -- Phases 103-106 (in progress)

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

### v6.1 Quantum Chess Demo (In Progress)

**Milestone Goal:** Build a quantum minimax chess solver demo using raw quantum_language primitives -- manual quantum walk on a chess game tree with legal move generation, demonstrating the framework's expressiveness without using the QWalkTree API.

**Context:** Chess has at most 218 legal moves per turn. In our simplified endgame (2 kings + white knights): white has max ~32 moves (5-bit branch register), black has max 8 moves (3-bit branch register). Branch register width per level is fixed at the maximum for that player's turn.

- [x] **Phase 103: Chess Board Encoding & Legal Moves** - Board representation, piece encoding, move generation, and compiled move oracle (completed 2026-03-03)
- [x] **Phase 104: Walk Register Scaffolding & Local Diffusion** - One-hot height register, branch registers, board-state-from-branch-history derivation, and single D_x diffusion operator with position-aware branching factor (completed 2026-03-03)
- [x] **Phase 105: Full Walk Operators** - Height-controlled diffusion cascade, R_A, R_B, and compiled walk step U = R_B * R_A (completed 2026-03-05)
- [x] **Phase 106: Demo Scripts** - Manual walk demo.py with circuit statistics and QWalkTree comparison script (completed 2026-03-05)

## Phase Details

### Phase 103: Chess Board Encoding & Legal Moves
**Goal**: Users can encode a chess endgame position and generate legal moves for any piece using quantum primitives
**Depends on**: Nothing (first phase of v6.1; builds on existing v6.0 framework)
**Requirements**: CHESS-01, CHESS-02, CHESS-03, CHESS-04, CHESS-05
**Success Criteria** (what must be TRUE):
  1. A chess position with 2 kings and white knights is encoded as a qarray with correct square-to-qubit mapping
  2. Knight attack patterns are generated correctly from any occupied square, respecting board boundaries
  3. King moves are generated for all 8 directions with edge-awareness (no wrapping off board edges)
  4. Legal move filtering excludes destinations attacked by opponent or occupied by friendly pieces
  5. The move oracle is wrapped as a `@ql.compile` function that produces a legal move set for a given position
**Plans**: 2 plans

Plans:
- [x] 103-01-PLAN.md -- Classical chess module: board encoding, move generation, filtering, enumeration (CHESS-01 through CHESS-04)
- [x] 103-02-PLAN.md -- Compiled move oracle with @ql.compile and subcircuit spot-checks (CHESS-05)

### Phase 104: Walk Register Scaffolding & Local Diffusion
**Goal**: Users can construct quantum walk registers and apply a local diffusion operator with correct Montanaro angles from raw primitives (not QWalkTree). Crucially, the diffusion operator must derive the board position at each node by applying the sequence of moves encoded in branch registers to the starting position — only then can it determine which child moves are legal and compute the correct branching factor d(x) for diffusion angles.
**Depends on**: Phase 103
**Requirements**: WALK-01, WALK-02, WALK-03
**Success Criteria** (what must be TRUE):
  1. A one-hot height register of (max_depth+1) qubits is created from raw qint with the root qubit initialized to |1>
  2. Per-level branch registers are created encoding the chosen move index from the legal move list at each depth
  3. The board position at any tree node is correctly derived by replaying the move sequence encoded in branch registers 0..d-1 from the starting position
  4. A single local diffusion D_x applies Ry rotations with correct Montanaro angles (phi = 2*arctan(sqrt(d))) where d is the number of legal moves at the derived board position, using raw gate primitives
**Plans**: 2 plans

Plans:
- [ ] 104-01-PLAN.md -- Register scaffolding: height register, branch registers, board state replay (WALK-01, WALK-02)
- [ ] 104-02-PLAN.md -- Local diffusion D_x with Montanaro angles and variable branching (WALK-03)

### Phase 105: Full Walk Operators
**Goal**: Users can compose a complete quantum walk step U = R_B * R_A from manual height-controlled diffusion operators
**Depends on**: Phase 104
**Requirements**: WALK-04, WALK-05, WALK-06, WALK-07
**Success Criteria** (what must be TRUE):
  1. Height-controlled diffusion cascade activates D_x only at the correct depth level via one-hot qubit control
  2. R_A composes diffusion at even depths (excluding root) with correct height-register conditioning
  3. R_B composes diffusion at odd depths plus root with correct height-register conditioning
  4. Walk step U = R_B * R_A is composed via `@ql.compile` and produces a valid quantum circuit
**Plans**: 2 plans

Plans:
- [ ] 105-01-PLAN.md -- R_A and R_B walk operators with height-controlled diffusion cascade (WALK-04, WALK-05, WALK-06)
- [ ] 105-02-PLAN.md -- Mega-register construction and compiled walk step U = R_B * R_A (WALK-07)

### Phase 106: Demo Scripts
**Goal**: Users can run demo scripts that showcase the manual quantum walk on a chess game tree and compare against the QWalkTree API
**Depends on**: Phase 103, Phase 104, Phase 105
**Requirements**: DEMO-01, DEMO-02
**Success Criteria** (what must be TRUE):
  1. demo.py runs end-to-end producing a quantum circuit for a chess endgame walk -- showing starting position, legal move tree structure, walk operators, and circuit statistics (depth, gate count, qubit count)
  2. A secondary comparison script applies the QWalkTree API to the same chess position and prints side-by-side circuit statistics against the manual approach
**Plans**: 2 plans

Plans:
- [ ] 106-01-PLAN.md -- Manual chess walk demo with progressive walkthrough and circuit stats (DEMO-01)
- [ ] 106-02-PLAN.md -- QWalkTree comparison script with side-by-side stats table (DEMO-02)

## Progress

**Execution Order:**
Phases execute in numeric order: 103 -> 104 -> 105 -> 106

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
| 103. Chess Board Encoding & Legal Moves | v6.1 | Complete    | 2026-03-03 | 2026-03-03 |
| 104. Walk Register Scaffolding & Local Diffusion | 2/2 | Complete    | 2026-03-03 | - |
| 105. Full Walk Operators | 2/2 | Complete    | 2026-03-05 | - |
| 106. Demo Scripts | 2/2 | Complete    | 2026-03-05 | - |

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
*Milestone v6.1 roadmap created: 2026-03-03*
