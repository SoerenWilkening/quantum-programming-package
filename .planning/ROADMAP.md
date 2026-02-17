# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (shipped 2026-02-04) -- See `milestones/v2.0-ROADMAP.md`
- v2.1 Compile Enhancements -- Phases 52-54 (shipped 2026-02-05) -- See `milestones/v2.1-ROADMAP.md`
- v2.2 Performance Optimization -- Phases 55-61 (shipped 2026-02-08) -- See `milestones/v2.2-ROADMAP.md`
- v2.3 Hardcoding Right-Sizing -- Phases 62-64 (shipped 2026-02-08) -- See `milestones/v2.3-ROADMAP.md`
- v3.0 Fault-Tolerant Arithmetic -- Phases 65-74 (in progress)

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

### v3.0 Fault-Tolerant Arithmetic (In Progress)

**Milestone Goal:** Implement Toffoli-based arithmetic (no phase/rotation gates) as an alternative backend, enabling fault-tolerant circuit generation. CDKM ripple-carry adder as foundation, schoolbook multiplication, restoring division, CLA depth optimization, all wired through `ql.option('fault_tolerant')` dispatch.

- [x] **Phase 65: Infrastructure Prerequisites** - Fix reverse_circuit_range, allocator block reuse, and ancilla lifecycle contracts -- completed 2026-02-14
- [x] **Phase 66: CDKM Ripple-Carry Adder** - QQ/CQ addition and subtraction via MAJ/UMA chain with 1 ancilla -- completed 2026-02-14
- [x] **Phase 67: Controlled Adder & Backend Dispatch** - cQQ/cCQ controlled addition and fault_tolerant mode switching -- completed 2026-02-14
- [x] **Phase 68: Schoolbook Multiplication** - QQ/CQ Toffoli-based multiplication using shift-and-add -- completed 2026-02-15
- [x] **Phase 69: Controlled Multiplication & Division** - cQQ/cCQ multiplication and restoring division via Toffoli add/sub -- completed 2026-02-15
- [x] **Phase 70: Cross-Backend Verification** - Exhaustive equivalence testing between Toffoli and QFT backends -- completed 2026-02-15
- [x] **Phase 71: Carry Look-Ahead Adder** - O(log n) depth addition with Brent-Kung and Kogge-Stone prefix trees -- completed 2026-02-17
- [x] **Phase 72: Performance Polish** - Hardcoded sequences, T-count reporting, controlled add-subtract optimization -- completed 2026-02-18
- [x] **Phase 73: Toffoli CQ/cCQ Classical-Bit Gate Reduction** - Inline CQ/cCQ generators exploiting classical bit values, hardcoded increment sequences -- completed 2026-02-17
- [x] **Phase 74: MCX/CCX Gate Decomposition & Sequence Refactoring** - Decompose CCCX gates mandatory, opt-in CCX decomposition, fast decomposed sequence functions, file refactoring -- completed 2026-02-17

## Phase Details

### Phase 65: Infrastructure Prerequisites
**Goal**: All infrastructure bugs that would silently corrupt Toffoli circuits are fixed before algorithm work begins
**Depends on**: Nothing (first phase of v3.0)
**Requirements**: INF-01
**Success Criteria** (what must be TRUE):
  1. `reverse_circuit_range()` correctly inverts circuits containing CCX, CX, and X gates (self-inverse gates retain GateValue=1, not -1)
  2. `allocator_alloc()` can allocate and reuse contiguous blocks of ancilla qubits (count > 1), not just single-qubit allocations
  3. Ancilla qubits allocated with `is_ancilla=true` are verified to be in |0> state after uncomputation via debug assertion
  4. Existing QFT arithmetic tests still pass with zero regressions after infrastructure changes
**Plans**: 3 plans

Plans:
- [x] 65-01-PLAN.md -- Fix GateValue negation for self-inverse gates in reverse_circuit_range and run_instruction
- [x] 65-02-PLAN.md -- Replace freed stack with block-based free-list for contiguous ancilla allocation
- [x] 65-03-PLAN.md -- Add debug-mode ancilla lifecycle assertions and integration tests

### Phase 66: CDKM Ripple-Carry Adder
**Goal**: Users can perform Toffoli-based addition and subtraction on quantum registers of any width using the CDKM ripple-carry algorithm
**Depends on**: Phase 65
**Requirements**: ADD-01, ADD-02, ADD-05, ADD-07
**Success Criteria** (what must be TRUE):
  1. `QQ_add_toffoli(bits)` generates a correct sequence using only CCX/CX/X gates with exactly 1 ancilla qubit, verified for all input pairs at widths 1-4
  2. `CQ_add_toffoli(bits, val)` adds a classical constant to a quantum register using only CCX/CX/X gates, verified for all input pairs at widths 1-4
  3. Subtraction works via inverted adder sequence (reversed gate order) for both QQ and CQ variants, verified for all input pairs at widths 1-4
  4. Mixed-width addition handles operands of different bit widths via zero-extension, verified for width combinations (2,3), (3,4), (4,6)
  5. Ancilla qubit is allocated before computation, uncomputed to |0>, and freed after each operation
**Plans**: 3 plans

Plans:
- [x] 66-01-PLAN.md -- Implement CDKM adder in C (ToffoliAddition.c, types/circuit changes, hot path dispatch)
- [x] 66-02-PLAN.md -- Python wiring (Cython declarations, fault_tolerant option, build) and exhaustive verification tests
- [x] 66-03-PLAN.md -- Gap closure: fix CQ Toffoli addition via temp-register QQ approach

### Phase 67: Controlled Adder & Backend Dispatch
**Goal**: Users can switch all addition/subtraction to Toffoli-based circuits via `ql.option('fault_tolerant', True)` with controlled variants for quantum conditionals
**Depends on**: Phase 66
**Requirements**: ADD-03, ADD-04, DSP-01, DSP-02, DSP-03
**Success Criteria** (what must be TRUE):
  1. `cQQ_add_toffoli(bits)` performs addition conditioned on a control qubit using only CCX/CX/X gates, verified for widths 1-4
  2. `cCQ_add_toffoli(bits, val)` performs classical-quantum addition conditioned on a control qubit, verified for widths 1-4
  3. `ql.option('fault_tolerant', True)` causes `a += b` to emit CCX/CX/X gates instead of CP/H gates, and `ql.option('fault_tolerant', False)` restores QFT behavior
  4. Hot-path C dispatch functions check the fault_tolerant flag and route to the correct sequence generator without qubit layout collisions
  5. Toffoli-based arithmetic is the default mode; QFT arithmetic is available via explicit `ql.option('fault_tolerant', False)`
**Plans**: 3 plans

Plans:
- [x] 67-01-PLAN.md -- Implement controlled CDKM adder (cQQ/cCQ) in ToffoliAddition.c with MCX memory fix
- [x] 67-02-PLAN.md -- Wire controlled Toffoli dispatch in hot_path_add.c, Cython declarations, exhaustive tests
- [x] 67-03-PLAN.md -- Change default arithmetic mode to ARITH_TOFFOLI and adapt test suite

### Phase 68: Schoolbook Multiplication
**Goal**: Users can multiply quantum integers using Toffoli-based circuits with quadratic gate count
**Depends on**: Phase 67
**Requirements**: MUL-01, MUL-02
**Success Criteria** (what must be TRUE):
  1. `QQ_mul_toffoli(bits)` computes the product of two quantum registers using shift-and-add with Toffoli adders, verified for all input pairs at widths 1-3
  2. `CQ_mul_toffoli(bits, val)` computes the product of a quantum register and a classical value, verified for all input pairs at widths 1-3
  3. Multiplication circuits contain only CCX/CX/X gates (no CP/H gates) when fault_tolerant mode is active
  4. `a * b` and `a *= b` operators dispatch to Toffoli multiplication when fault_tolerant mode is active
**Plans**: 2 plans

Plans:
- [x] 68-01-PLAN.md -- Implement ToffoliMultiplication.c (QQ/CQ shift-and-add) and wire Toffoli dispatch into hot_path_mul.c
- [x] 68-02-PLAN.md -- Exhaustive verification tests for Toffoli multiplication (widths 1-3), gate purity, operator dispatch

### Phase 69: Controlled Multiplication & Division
**Goal**: Users can perform controlled multiplication and division/modulo using Toffoli-based circuits, completing the full arithmetic surface
**Depends on**: Phase 68
**Requirements**: MUL-03, MUL-04, DIV-01, DIV-02
**Success Criteria** (what must be TRUE):
  1. `cQQ_mul_toffoli(bits)` performs multiplication conditioned on a control qubit, verified for widths 1-3
  2. `cCQ_mul_toffoli(bits, val)` performs classical-quantum multiplication conditioned on a control qubit, verified for widths 1-3
  3. `a // b` and `a % b` produce correct quotient and remainder using Toffoli add/sub underneath when fault_tolerant is active, verified for widths 2-4 with classical divisors
  4. `a // b` and `a % b` work with quantum divisors using Toffoli add/sub, verified for widths 2-3
  5. Division operations inside `with` blocks (controlled context) work correctly with Toffoli dispatch
**Plans**: 3 plans

Plans:
- [x] 69-01-PLAN.md -- Implement controlled Toffoli multiplication (cQQ/cCQ) in C and wire hot_path dispatch
- [x] 69-02-PLAN.md -- Exhaustive verification tests for controlled Toffoli multiplication (widths 1-3)
- [x] 69-03-PLAN.md -- Division/modulo Toffoli verification tests (classical + quantum divisors, controlled context)

### Phase 70: Cross-Backend Verification
**Goal**: Toffoli and QFT backends are proven to produce identical computational results for all arithmetic operations across practical widths
**Depends on**: Phase 69
**Requirements**: INF-02
**Success Criteria** (what must be TRUE):
  1. For widths 1-8, every addition input pair produces identical results between Toffoli and QFT backends (QQ, CQ, cQQ, cCQ variants)
  2. For widths 1-6, every multiplication input pair produces identical results between Toffoli and QFT backends (QQ, CQ, cQQ, cCQ variants)
  3. For widths 2-6, division/modulo results match between Toffoli and QFT backends for classical and quantum divisors
  4. A regression test suite runs both backends and compares results, integrated into `pytest tests/python/ -v`
**Plans**: 2 plans

Plans:
- [x] 70-01-PLAN.md -- Cross-backend test infrastructure + addition/subtraction equivalence tests (widths 1-8)
- [x] 70-02-PLAN.md -- Multiplication and division/modulo cross-backend equivalence tests (widths 1-6 mul, 2-6 div)

### Phase 71: Carry Look-Ahead Adder
**Goal**: Users can perform O(log n) depth addition for large register widths using the Draper CLA algorithm
**Depends on**: Phase 70
**Requirements**: ADD-06
**Success Criteria** (what must be TRUE):
  1. `QQ_add_cla(bits)` computes addition using a generate/propagate prefix tree with O(log n) depth and 2n-2 ancilla qubits
  2. CLA adder produces identical results to RCA adder for all input pairs at widths 1-6
  3. CLA circuit depth is measurably less than RCA circuit depth for widths >= 8
  4. All 2n-2 ancilla qubits are correctly uncomputed to |0> and freed after each CLA operation
**Plans**: 6 plans

Plans:
- [x] 71-01-PLAN.md -- Infrastructure (cla_override, option plumbing) + Brent-Kung QQ adder stub + QQ dispatch + smoke tests
- [x] 71-02-PLAN.md -- Kogge-Stone QQ adder stub + BK/KS CQ stubs + CQ dispatch + variant selection tests
- [x] 71-03-PLAN.md -- Controlled CLA stubs (cQQ/cCQ for BK+KS) + controlled dispatch + controlled tests
- [x] 71-04-PLAN.md -- Comprehensive verification: CLA vs RCA equivalence, depth comparison (xfail), ancilla cleanup, gate purity
- [x] 71-05-PLAN.md -- Gap closure: Implement working BK QQ CLA adder with prefix tree + update dispatch ancilla count
- [x] 71-06-PLAN.md -- Gap closure: Wire BK CQ/cQQ/cCQ variants + remove depth comparison xfail markers

### Phase 72: Performance Polish
**Goal**: Toffoli arithmetic is optimized for production use with hardcoded sequences, resource reporting, and gate count reduction
**Depends on**: Phase 71
**Requirements**: INF-03, INF-04, MUL-05
**Success Criteria** (what must be TRUE):
  1. Hardcoded Toffoli gate sequences for widths 1-8 eliminate runtime sequence generation, with measurable dispatch speedup
  2. `ql.stats()` reports T-count alongside existing gate counts, computed as 7 * Toffoli_count for fault-tolerant circuits
  3. Controlled add-subtract optimization in multiplication reduces Toffoli count by approximately 50% compared to naive controlled addition approach, verified by gate count comparison
**Plans**: 3 plans

Plans:
- [x] 72-01-PLAN.md -- Generate hardcoded Toffoli sequence C files (QQ/cQQ for widths 1-8) via Python script
- [x] 72-02-PLAN.md -- Wire hardcoded sequences into ToffoliAddition.c + T-count exposure in Python API + tests
- [x] 72-03-PLAN.md -- AND-ancilla MCX decomposition in QQ multiplication to eliminate 3-control gates

### Phase 73: Toffoli CQ/cCQ Classical-Bit Gate Reduction
**Goal**: CQ and cCQ Toffoli arithmetic uses inline generators that exploit known classical bit values to eliminate unnecessary gates, reducing T-count for fault-tolerant circuits
**Depends on**: Phase 72
**Requirements**: ADD-02, ADD-04, ADD-05, INF-03, INF-04
**Success Criteria** (what must be TRUE):
  1. Inline CQ CDKM generator eliminates CX gates at zero-bit positions and folds X-init into MAJ chain, verified correct at widths 1-4
  2. Inline cCQ CDKM generator eliminates CCX gates at zero-bit positions (14T per position), verified correct at widths 1-4
  3. BK CLA CQ/cCQ generators apply classical-bit simplification to Phase A/E, verified correct at widths 2-4
  4. Subtraction works via inverted inline sequences for all CQ/cCQ variants
  5. Hardcoded CQ/cCQ increment (value=1) sequences for widths 1-8 match inline generator output
  6. T-count reporting reflects reduced gate counts for CQ/cCQ operations
**Plans**: 2 plans

Plans:
- [x] 73-01-PLAN.md -- Inline CQ/cCQ CDKM and BK CLA generators with classical-bit gate simplification + exhaustive tests
- [x] 73-02-PLAN.md -- Hardcoded CQ/cCQ increment sequences (widths 1-8) + dispatch + propagation tests

## Progress

**Execution Order:**
Phases execute in numeric order: 65 -> 66 -> 67 -> 68 -> 69 -> 70 -> 71 -> 72 -> 73 -> 74

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 41. Uncomputation Fix | v1.8 | 2/2 | Complete | 2026-02-02 |
| 42. Quantum Copy Foundation | v1.8 | 1/1 | Complete | 2026-02-02 |
| 43. Copy-Aware Binary Ops | v1.8 | 2/2 | Complete | 2026-02-02 |
| 44. Array Mutability | v1.8 | 2/2 | Complete | 2026-02-03 |
| 45. Data Extraction Bridge | v1.9 | 2/2 | Complete | 2026-02-03 |
| 46. Core Renderer | v1.9 | 3/3 | Complete | 2026-02-03 |
| 47. Detail Mode & Public API | v1.9 | 2/2 | Complete | 2026-02-03 |
| 48. Core Capture-Replay | v2.0 | 2/2 | Complete | 2026-02-04 |
| 49. Optimization & Uncomputation | v2.0 | 2/2 | Complete | 2026-02-04 |
| 50. Controlled Context | v2.0 | 2/2 | Complete | 2026-02-04 |
| 51. Differentiators & Polish | v2.0 | 2/2 | Complete | 2026-02-04 |
| 52. Ancilla Tracking & Inverse Qubit Reuse | v2.1 | 2/2 | Complete | 2026-02-04 |
| 53. Qubit-Saving Auto-Uncompute | v2.1 | 2/2 | Complete | 2026-02-04 |
| 54. qarray Support in @ql.compile | v2.1 | 2/2 | Complete | 2026-02-05 |
| 55. Profiling Infrastructure | v2.2 | 3/3 | Complete | 2026-02-05 |
| 56. Forward/Inverse Depth Fix | v2.2 | 2/2 | Complete | 2026-02-05 |
| 57. Cython Optimization | v2.2 | 3/3 | Complete | 2026-02-05 |
| 58. Hardcoded Sequences (1-8 bit) | v2.2 | 3/3 | Complete | 2026-02-05 |
| 59. Hardcoded Sequences (9-16 bit) | v2.2 | 4/4 | Complete | 2026-02-06 |
| 60. C Hot Path Migration | v2.2 | 4/4 | Complete | 2026-02-06 |
| 61. Memory Optimization | v2.2 | 3/3 | Complete | 2026-02-08 |
| 62. Measurement | v2.3 | 2/2 | Complete | 2026-02-08 |
| 63. Right-Sizing Implementation | v2.3 | 1/1 | Complete | 2026-02-08 |
| 64. Regression Verification | v2.3 | 1/1 | Complete | 2026-02-08 |
| 65. Infrastructure Prerequisites | v3.0 | 3/3 | Complete | 2026-02-14 |
| 66. CDKM Ripple-Carry Adder | v3.0 | 3/3 | Complete | 2026-02-14 |
| 67. Controlled Adder & Backend Dispatch | v3.0 | 3/3 | Complete | 2026-02-14 |
| 68. Schoolbook Multiplication | v3.0 | 2/2 | Complete | 2026-02-15 |
| 69. Controlled Multiplication & Division | v3.0 | 3/3 | Complete | 2026-02-15 |
| 70. Cross-Backend Verification | v3.0 | 2/2 | Complete | 2026-02-15 |
| 71. Carry Look-Ahead Adder | v3.0 | 6/6 | Complete | 2026-02-17 |
| 72. Performance Polish | v3.0 | 3/3 | Complete | 2026-02-18 |
| 73. Toffoli CQ/cCQ Classical-Bit Gate Reduction | v3.0 | 2/2 | Complete | 2026-02-17 |
| 74. MCX/CCX Gate Decomposition & Sequence Refactoring | v3.0 | 5/5 | Complete | 2026-02-17 |

### Phase 74: MCX/CCX Gate Decomposition & Sequence Refactoring
**Goal**: All MCX gates (3+ controls) are automatically decomposed into CCX/CX/X gates, with an opt-in `toffoli_decompose` option to further decompose CCX into Clifford+T. Sequences containing CCX gates get dedicated fast-path functions. Large C files are refactored for maintainability.
**Depends on**: Phase 73
**Requirements**: INF-03, INF-04
**Success Criteria** (what must be TRUE):
  1. CCCX (3-control) gates produced by controlled addition are automatically decomposed into CCX/CX/X gates using AND-ancilla pattern, verified by gate purity checks (no MCX in output)
  2. `ql.option('toffoli_decompose', True)` decomposes all CCX gates into Clifford+T (H, T, T†, CNOT) basis gates, verified by gate purity checks
  3. All sequence-generating functions that produce CCX gates have dedicated decomposed variants for fast dispatch
  4. Overly long C source files are refactored into logical sub-modules without changing behavior
  5. All existing Toffoli arithmetic tests pass with zero regressions
**Plans**: 5 plans

Plans:
- [x] 74-01-PLAN.md -- Pure refactoring: split ToffoliAddition.c into CDKM/CLA/Helpers + extract Toffoli dispatch from hot_path_add.c
- [x] 74-02-PLAN.md -- Gate infrastructure: T_GATE/TDG_GATE enum, toffoli_decompose option, updated gate counts + QASM export
- [x] 74-03-PLAN.md -- MCX auto-decomposition: AND-ancilla decomposition at all 9 MCX emission points + gate purity tests
- [x] 74-04-PLAN.md -- CCX->Clifford+T: decomposition helper, inline integration, Clifford+T test suite
- [x] 74-05-PLAN.md -- Hardcoded decomposed cQQ sequences (widths 1-8) + dispatch + comprehensive verification

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 shipped: 2026-02-05*
*Milestone v2.2 shipped: 2026-02-08*
*Milestone v2.3 shipped: 2026-02-08*
*Milestone v3.0 roadmap created: 2026-02-14*
