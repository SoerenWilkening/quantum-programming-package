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
- v4.0 Grover's Algorithm -- Phases 76-81 (in progress)

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

### v4.0 Grover's Algorithm (In Progress)

**Milestone Goal:** Enable users to implement Grover's search and amplitude amplification using both manual building blocks and high-level convenience APIs.

- [x] **Phase 76: Gate Primitive Exposure** - Expose H, Z, Ry gates at Python level via Cython bindings (3/3 plans complete)
- [ ] **Phase 77: Oracle Infrastructure** - @ql.grover_oracle decorator with compute-phase-uncompute enforcement
- [ ] **Phase 78: Diffusion Operator** - X-MCZ-X pattern with zero ancilla and O(n) gates
- [ ] **Phase 79: Grover Search Integration** - ql.grover() API combining oracle + diffusion with auto iteration count
- [ ] **Phase 80: Oracle Auto-Synthesis & Adaptive Search** - Lambda predicate oracles and exponential backoff for unknown M
- [ ] **Phase 81: Amplitude Estimation (IQAE)** - ql.amplitude_estimate() with configurable precision and confidence

## Phase Details

### Phase 76: Gate Primitive Exposure
**Goal**: Users can apply Hadamard-equivalent and rotation gates to qint/qbool via branch(theta) method
**Depends on**: Nothing (first phase in milestone)
**Requirements**: PRIM-01, PRIM-02, PRIM-03
**Success Criteria** (what must be TRUE):
  1. User can call `x.branch(theta)` on a qint to apply Ry(theta) rotation to all qubits
  2. User can call `b.branch(theta)` on a qbool to apply Ry(theta) rotation
  3. `branch(pi/2)` creates equal superposition verifiable via Qiskit simulation
  4. H and Z gates are accessible internally for diffusion operator construction
**Plans**: 3 plans
- [x] 76-01-PLAN.md - C backend Ry gates + _gates.pyx module
- [x] 76-02-PLAN.md - branch() method on qint/qbool
- [x] 76-03-PLAN.md - Qiskit verification tests

### Phase 77: Oracle Infrastructure
**Goal**: Users can create quantum oracles with correct phase-marking semantics that integrate with @ql.compile
**Depends on**: Phase 76
**Requirements**: ORCL-01, ORCL-02, ORCL-03, ORCL-04, ORCL-05
**Success Criteria** (what must be TRUE):
  1. User can pass any @ql.compile decorated function as oracle to Grover
  2. @ql.grover_oracle decorator enforces compute-then-phase-then-uncompute ordering
  3. Oracle exits with zero ancilla delta (validated, hard error on violation)
  4. Bit-flip oracles are auto-wrapped with X-H-oracle-H-X phase kickback pattern
  5. Oracle cached correctly under different arithmetic_mode settings (QFT vs Toffoli)
**Plans**: TBD

### Phase 78: Diffusion Operator
**Goal**: Users can apply the Grover diffusion operator as a reusable building block
**Depends on**: Phase 76
**Requirements**: GROV-03, GROV-05
**Success Criteria** (what must be TRUE):
  1. Diffusion operator uses X-MCZ-X pattern with zero ancilla allocation
  2. User can manually construct S_0 reflection via `with a == 0` for custom amplitude amplification
  3. Diffusion operator accepts explicit qubit list (validated against search register width)
  4. Phase flip on |0...0> state verifiable via Qiskit simulation for widths 1-8
**Plans**: TBD

### Phase 79: Grover Search Integration
**Goal**: Users can execute Grover search with a single API call and get measured results
**Depends on**: Phase 77, Phase 78
**Requirements**: GROV-01, GROV-02, GROV-04
**Success Criteria** (what must be TRUE):
  1. `ql.grover(oracle, search_space)` executes search and returns measured Python value
  2. Iteration count auto-calculated from N and M using floor(pi/4 * sqrt(N/M) - 0.5)
  3. Multiple solutions (M > 1) produce correct iteration count and find any valid solution
  4. End-to-end test with known-solution oracle achieves peak probability at calculated iteration count
**Plans**: TBD

### Phase 80: Oracle Auto-Synthesis & Adaptive Search
**Goal**: Users can specify oracles as Python lambdas and search without knowing solution count
**Depends on**: Phase 79
**Requirements**: SYNTH-01, SYNTH-02, SYNTH-03, ADAPT-01, ADAPT-02
**Success Criteria** (what must be TRUE):
  1. User can pass Python predicate lambda as oracle (`ql.grover(lambda x: x > 5, x)`)
  2. Compound predicates compile to valid oracles (`(x > 10) & (x < 50)`)
  3. Predicate oracles work with all existing qint comparison operators
  4. When M is unknown, Grover uses exponential backoff strategy
  5. Adaptive search terminates when solution found or search space exhausted
**Plans**: TBD

### Phase 81: Amplitude Estimation (IQAE)
**Goal**: Users can estimate success probability of an oracle using iterative quantum amplitude estimation
**Depends on**: Phase 79
**Requirements**: AMP-01, AMP-02, AMP-03
**Success Criteria** (what must be TRUE):
  1. `ql.amplitude_estimate(oracle, register)` returns estimated probability
  2. Implementation uses IQAE variant (no QFT circuit required)
  3. User can specify precision (epsilon) and confidence level as parameters
  4. Estimated amplitude matches known oracle probability within specified epsilon
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 41-44 | v1.8 | 7/7 | Complete | 2026-02-03 |
| 45-47 | v1.9 | 7/7 | Complete | 2026-02-03 |
| 48-51 | v2.0 | 8/8 | Complete | 2026-02-04 |
| 52-54 | v2.1 | 6/6 | Complete | 2026-02-05 |
| 55-61 | v2.2 | 22/22 | Complete | 2026-02-08 |
| 62-64 | v2.3 | 4/4 | Complete | 2026-02-08 |
| 65-75 | v3.0 | 35/35 | Complete | 2026-02-18 |
| 76 | v4.0 | 3/3 | Complete | 2026-02-19 |
| 77 | v4.0 | 0/TBD | Not started | - |
| 78 | v4.0 | 0/TBD | Not started | - |
| 79 | v4.0 | 0/TBD | Not started | - |
| 80 | v4.0 | 0/TBD | Not started | - |
| 81 | v4.0 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 shipped: 2026-02-05*
*Milestone v2.2 shipped: 2026-02-08*
*Milestone v2.3 shipped: 2026-02-08*
*Milestone v3.0 shipped: 2026-02-18*
*Milestone v4.0 started: 2026-02-19*
