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
- v6.0 Quantum Walk Primitives -- Phases 97-101 (in progress)

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

### v6.0 Quantum Walk Primitives (In Progress)

**Milestone Goal:** Predicate-aware quantum walk operators based on Montanaro 2015 backtracking speedup, with variable branching, correct amplitude calculation, and Qiskit-verified demos on small SAT instances.

- [x] **Phase 97: Tree Encoding & Predicate Interface** - Foundational data structures, register allocation, predicate API, and resource estimation -- completed 2026-03-02
- [x] **Phase 98: Local Diffusion Operator** - D_x with correct amplitude angles for uniform branching, root special case, and statevector verification (completed 2026-03-02)
- [ ] **Phase 99: Walk Operators** - R_A, R_B via parity-controlled diffusion, composed walk step, @ql.compile wrapping, disjointness validation
- [ ] **Phase 100: Variable Branching** - Dynamic child counting via predicate evaluation and controlled Ry rotation based on d(x)
- [ ] **Phase 101: Detection & Demo** - Iterative power-method detection, SAT demo within 17-qubit budget, Qiskit statevector verification

## Phase Details

### Phase 97: Tree Encoding & Predicate Interface
**Goal**: Users can create a QuantumBacktrackingTree with correct register layout and define accept/reject predicates that are validated before circuit construction
**Depends on**: Nothing (first phase of v6.0)
**Requirements**: TREE-01, TREE-02, TREE-03, PRED-01, PRED-02, PRED-03
**Success Criteria** (what must be TRUE):
  1. User can instantiate QuantumBacktrackingTree(max_depth, branching_degree) and it allocates one-hot height register (max_depth+1 qubits) plus QuantumArray branch registers (one per depth level)
  2. User can call the resource estimator with tree parameters and receive exact qubit count; estimator raises an error before circuit construction if budget exceeds 17 qubits
  3. User can prepare the root state (height qubit set, branch registers initialized) and verify via statevector that the root is correctly encoded
  4. User can pass a predicate callable returning (is_accept, is_reject) qbools and the framework validates mutual exclusion (both cannot be true simultaneously)
  5. Predicate uncomputation works correctly via raw allocation or @ql.compile inverse pattern without conflicting with LIFO scope tracking
**Plans**: 2 plans

Plans:
- [x] 97-01-PLAN.md — QWalkTree class + TreeNode + root state prep + tree encoding tests (TREE-01, TREE-02, TREE-03)
- [x] 97-02-PLAN.md — Predicate interface + mutual exclusion validation + predicate tests (PRED-01, PRED-02, PRED-03)

### Phase 98: Local Diffusion Operator
**Goal**: Users can apply verified-correct local diffusion D_x to any tree node with proper amplitude coefficients
**Depends on**: Phase 97
**Requirements**: DIFF-01, DIFF-02, DIFF-03
**Success Criteria** (what must be TRUE):
  1. Local diffusion D_x for uniform branching uses phi = 2*arctan(sqrt(d)) and produces amplitudes matching 1/sqrt(d(x)+1) for parent and each child (the "+1" includes the parent node)
  2. Root node diffusion uses a separate phi_root formula (different amplitude weighting per Montanaro section 2) and is controlled on the root height qubit h[max_depth]
  3. Statevector tests confirm |psi_x> amplitudes match the 1/sqrt(d(x)+1) tolerance for non-root nodes and the correct root formula for the root node
**Plans**: 2 plans

Plans:
- [ ] 98-01-PLAN.md — Angle precomputation + local_diffusion() implementation with height-controlled dispatch (DIFF-01, DIFF-02)
- [ ] 98-02-PLAN.md — Statevector tests for non-root, root, and amplitude verification (DIFF-03)

### Phase 99: Walk Operators
**Goal**: Users can apply the complete walk step U = R_B * R_A as a compiled, cacheable operation with verified qubit disjointness between R_A and R_B
**Depends on**: Phase 98
**Requirements**: WALK-01, WALK-02, WALK-03, WALK-04, WALK-05
**Success Criteria** (what must be TRUE):
  1. R_A applies local diffusions at even-depth nodes via height-parity control, and R_B applies local diffusions at odd-depth nodes plus root reflection via height-parity control
  2. Qubit disjointness test confirms R_A and R_B operate on zero overlapping qubit indices (structural correctness of the product-of-reflections)
  3. Walk step U = R_B * R_A is wrapped in @ql.compile and the controlled variant is accessible for phase estimation
  4. Applying the walk step to a known tree state produces the expected statevector transformation (verified via Qiskit simulation)
**Plans**: TBD

Plans:
- [ ] 99-01: TBD
- [ ] 99-02: TBD

### Phase 100: Variable Branching
**Goal**: Walk operators support trees where different nodes have different numbers of valid children, with amplitude angles computed dynamically from predicate evaluation
**Depends on**: Phase 99
**Requirements**: DIFF-04
**Success Criteria** (what must be TRUE):
  1. Variable branching counts valid children per node by evaluating the predicate on each potential child and produces the correct d(x) count
  2. Controlled Ry rotation applies the angle phi = 2*arctan(sqrt(d(x))) conditioned on the child count d(x), so nodes with fewer valid children get different diffusion amplitudes
  3. Statevector tests confirm correct amplitudes for a tree where different nodes have different branching factors (at least one node pruned vs. one node fully branching)
**Plans**: TBD

Plans:
- [ ] 100-01: TBD
- [ ] 100-02: TBD

### Phase 101: Detection & Demo
**Goal**: Users can detect whether a solution exists in a backtracking tree, verified end-to-end on a small SAT instance within the 17-qubit simulator ceiling
**Depends on**: Phase 100
**Requirements**: DET-01, DET-02, DET-03
**Success Criteria** (what must be TRUE):
  1. Iterative power-method detection algorithm applies walk step powers, measures, and correctly identifies solution existence when threshold probability exceeds 3/8
  2. Demo runs on a small SAT instance (binary tree depth 2-3, within 17-qubit budget) and correctly detects the known solution
  3. Qiskit statevector verification confirms detection probability is above threshold on a known-solution instance and below threshold on a no-solution instance
  4. Detection returns false (no false positive) on a tree with no satisfying assignment
**Plans**: TBD

Plans:
- [ ] 101-01: TBD
- [ ] 101-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 97 -> 98 -> 99 -> 100 -> 101

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
| 97. Tree Encoding & Predicate Interface | v6.0 | 2/2 | Complete | 2026-03-02 |
| 98. Local Diffusion Operator | v6.0 | 2/2 | Complete | 2026-03-02 |
| 99. Walk Operators | v6.0 | 0/? | Not started | - |
| 100. Variable Branching | v6.0 | 0/? | Not started | - |
| 101. Detection & Demo | v6.0 | 0/? | Not started | - |

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
*Milestone v6.0 roadmap created: 2026-02-26*
