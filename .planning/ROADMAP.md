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
- v7.0 Compile Infrastructure -- Phases 107-110 (in progress)

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

### v7.0 Compile Infrastructure (In Progress)

**Milestone Goal:** Restructure `@ql.compile` from monolithic circuit generation to a multi-level compilation model with call graph DAG, selective sequence merging, and DOT visualization.

- [x] **Phase 107: Call Graph DAG Foundation** - opt_flag API, DAG construction with qubit overlap edges, backward compat (completed 2026-03-05)
- [x] **Phase 108: Call Graph Analysis & Visualization** - Per-node stats extraction, aggregate metrics, DOT export, compilation report (completed 2026-03-06)
- [ ] **Phase 109: Selective Sequence Merging** - opt_flag=2 with merge candidate detection, correct merging, cross-boundary optimization
- [ ] **Phase 110: Merge Verification & Regression** - Qiskit simulation equivalence, full test suite regression

## Phase Details

### Phase 107: Call Graph DAG Foundation
**Goal**: Users can compile functions at multiple optimization levels with a call graph DAG capturing program structure
**Depends on**: Nothing (first phase of v7.0)
**Requirements**: CAPI-01, CAPI-03, CAPI-04, CGRAPH-01, CGRAPH-02, CGRAPH-03
**Success Criteria** (what must be TRUE):
  1. User can write `@ql.compile(opt=1)` and get a CallGraphDAG object alongside the compiled function
  2. User can write `@ql.compile(opt=3)` and get identical behavior to existing `@ql.compile()` (full expansion)
  3. All 106+ existing compile tests pass unchanged when opt=3 is the default
  4. Call graph DAG contains nodes with qubit sets, and edges weighted by shared qubit count between dependent sequences
  5. Parallel sequences (disjoint qubit sets) are identified as concurrent groups in the DAG
**Plans**: 2 plans

Plans:
- [ ] 107-01-PLAN.md -- CallGraphDAG module with DAGNode, overlap edges, parallel groups, builder stack
- [ ] 107-02-PLAN.md -- Wire opt parameter into compile.py, DAG building in __call__, backward compat + integration tests

### Phase 108: Call Graph Analysis & Visualization
**Goal**: Users can extract actionable metrics from the call graph and visualize program structure as DOT
**Depends on**: Phase 107
**Requirements**: CGRAPH-04, CGRAPH-05, VIS-01, VIS-02
**Success Criteria** (what must be TRUE):
  1. User can extract gate count, depth, qubit count, and T-count per node from the call graph without building a full circuit
  2. User can compute aggregate totals (gates, depth, T-count) across the full call graph
  3. User can call an API (e.g., `compiled_func.call_graph.to_dot()`) and receive a valid DOT string with labeled nodes and edges
  4. User can view a compilation report showing per-node stats including parallel group membership
**Plans**: 2 plans

Plans:
- [ ] 108-01-PLAN.md -- Per-node stats (depth, T-count) on DAGNode + aggregate() method
- [ ] 108-02-PLAN.md -- DOT export (to_dot) + compilation report (report) methods

### Phase 109: Selective Sequence Merging
**Goal**: Users can merge overlapping-qubit sequences for cross-boundary gate optimization
**Depends on**: Phase 108
**Requirements**: CAPI-02, MERGE-01, MERGE-02, MERGE-03
**Success Criteria** (what must be TRUE):
  1. User can write `@ql.compile(opt=2)` and overlapping-qubit sequences are automatically identified and merged
  2. Merged sequences produce correct quantum states (per-qubit gate ordering preserved)
  3. Cross-boundary optimizations fire (e.g., QFT at end of sequence A cancels IQFT at start of sequence B)
  4. Non-overlapping sequences remain independent (no unnecessary merging)
**Plans**: 2 plans

Plans:
- [ ] 109-01-PLAN.md -- merge_groups() on CallGraphDAG, _merge_and_optimize helper, merge_threshold param
- [ ] 109-02-PLAN.md -- opt=2 wiring in __call__, _apply_merge, merged replay, cross-boundary integration tests

### Phase 110: Merge Verification & Regression
**Goal**: Merged circuits are proven correct via simulation and the full test suite passes at all opt levels
**Depends on**: Phase 109
**Requirements**: MERGE-04
**Success Criteria** (what must be TRUE):
  1. Merged circuit output verified equivalent to sequential execution via Qiskit statevector simulation for arithmetic workloads (add, mul, grover oracle)
  2. All 106+ existing compile tests pass at opt=1, opt=2, and opt=3
  3. Parametric compilation works correctly at each opt level (no topology corruption from merge)
**Plans**: 2 plans

Plans:
- [ ] 110-01: TBD
- [ ] 110-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 107 -> 108 -> 109 -> 110

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
| 107. Call Graph DAG Foundation | 2/2 | Complete   | 2026-03-05 | - |
| 108. Call Graph Analysis & Visualization | 2/2 | Complete    | 2026-03-06 | - |
| 109. Selective Sequence Merging | v7.0 | 0/2 | Planning complete | - |
| 110. Merge Verification & Regression | v7.0 | 0/TBD | Not started | - |

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
*v7.0 roadmap created: 2026-03-05*
