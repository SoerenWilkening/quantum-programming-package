# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (shipped 2026-02-04) -- See `milestones/v2.0-ROADMAP.md`
- **v2.1 Compile Enhancements** -- Phases 52-54 (in progress)

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

### v2.1 Compile Enhancements (In Progress)

**Milestone Goal:** Make `@ql.compile` inverse reuse physical ancilla qubits from forward call (uncompute + deallocate), and support `ql.qarray` as compiled function arguments.

- [ ] **Phase 52: Ancilla Tracking & Inverse Qubit Reuse** - Compiled functions track ancillas and inverse targets same physical qubits
- [ ] **Phase 53: Qubit-Saving Auto-Uncompute** - Compiled functions auto-uncompute ancillas in qubit-saving mode
- [ ] **Phase 54: qarray Support in @ql.compile** - Pass ql.qarray as arguments to compiled functions

## Phase Details

### Phase 52: Ancilla Tracking & Inverse Qubit Reuse
**Goal**: Users can call `f(x).inverse()` or `f.inverse(x)` to target the same physical ancilla qubits allocated during `f(x)`, uncomputing them to |0⟩ and deallocating them
**Depends on**: v2.0 compilation infrastructure (Phase 51)
**Requirements**: INV-01, INV-02, INV-03, INV-04, INV-05, INV-06
**Success Criteria** (what must be TRUE):
  1. When a compiled function allocates qubits internally (e.g., `ql.qint()` inside the function), those qubits appear in a trackable ancilla list
  2. `f(x).inverse()` — return value carries compiled-origin metadata; calling `.inverse()` on it runs adjoint on that call's exact physical ancillas
  3. `f.inverse(x)` — looks up ancillas from a prior `f(x)` with matching inputs and runs adjoint on them
  4. After inverse completes, ancilla qubits are in |0⟩ state (Qiskit-verified)
  5. After inverse completes, ancilla qubits are deallocated (returned to allocator for reuse)
  6. Inverse works when called at any later point in the program (not just immediately after forward call)
**Plans**: TBD

### Phase 53: Qubit-Saving Auto-Uncompute
**Goal**: When qubit-saving mode is active, compiled functions that return a qint automatically uncompute all ancillas except the return value's qubits after the forward call
**Depends on**: Phase 52 (ancilla tracking infrastructure)
**Requirements**: INV-07
**Success Criteria** (what must be TRUE):
  1. With `ql.option("qubit_saving")` active, calling a compiled function that returns a qint automatically uncomputes internal ancillas after the forward call completes
  2. The return value's qubits are preserved (not uncomputed) and remain usable in subsequent operations
  3. The auto-uncomputed ancilla qubits are deallocated and available for reuse by later allocations
**Plans**: TBD

### Phase 54: qarray Support in @ql.compile
**Goal**: Users can pass `ql.qarray` objects as arguments to `@ql.compile`-decorated functions with correct capture, caching, and replay
**Depends on**: v2.0 compilation infrastructure (Phase 51); independent of Phases 52-53
**Requirements**: ARR-01, ARR-02, ARR-03, ARR-04
**Success Criteria** (what must be TRUE):
  1. A `@ql.compile`-decorated function accepting a `ql.qarray` argument captures gates correctly on first call (no errors, correct circuit)
  2. Replay of a compiled function with a different qarray of the same shape and element widths produces the correct remapped circuit
  3. Calling the same compiled function with qarrays of different shapes or element widths triggers separate cache entries (not incorrect replay)
  4. Compiled qarray functions produce identical circuits to their non-compiled equivalents (verified by gate-level comparison or Qiskit simulation)
**Plans**: TBD

## Progress

**Execution Order:** 52 -> 53 -> 54

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
| 52. Ancilla Tracking & Inverse Qubit Reuse | v2.1 | 0/TBD | Not started | - |
| 53. Qubit-Saving Auto-Uncompute | v2.1 | 0/TBD | Not started | - |
| 54. qarray Support in @ql.compile | v2.1 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 roadmap added: 2026-02-04*
