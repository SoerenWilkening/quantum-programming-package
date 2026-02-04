# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (in progress)

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

### v2.0 Function Compilation (In Progress)

**Milestone Goal:** `@ql.compile` decorator that captures gate sequences on first call, optimizes them, and replays with qubit remapping on subsequent calls -- enabling compiled quantum functions that work inside controlled contexts and support inverse generation, nesting, and debug introspection.

- [x] **Phase 48: Core Capture-Replay** - Cython infrastructure, decorator, gate capture/replay with qubit remapping and caching -- completed 2026-02-04
- [x] **Phase 49: Optimization & Uncomputation** - Optimize captured sequences and integrate with uncomputation tracking -- completed 2026-02-04
- [x] **Phase 50: Controlled Context** - Compiled functions work inside `with` blocks via re-capture with controlled cache keys -- completed 2026-02-04
- [ ] **Phase 51: Differentiators & Polish** - Inverse generation, debug mode, nested compilation, and comprehensive test suite

## Phase Details

### Phase 48: Core Capture-Replay
**Goal**: Users can decorate a quantum function with `@ql.compile` and call it multiple times with different quantum arguments, getting correct results from cached gate replay with qubit remapping
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, INF-01, INF-02
**Success Criteria** (what must be TRUE):
  1. A function decorated with `@ql.compile` produces the same circuit output as the undecorated version on first call
  2. Calling the compiled function a second time with different qint arguments replays gates onto the new qubits (no re-execution of the function body)
  3. The returned qint/qbool from a compiled function is usable in subsequent quantum operations (arithmetic, comparisons, conditionals)
  4. Calling with different classical parameter values or different qint widths triggers re-capture (separate cache entries)
  5. Creating a new circuit via `ql.circuit()` invalidates the compilation cache
**Plans**: 2 plans
Plans:
- [x] 48-01-PLAN.md -- Cython infrastructure (extract_gate_range, inject_remapped_gates, helpers)
- [x] 48-02-PLAN.md -- Python compile decorator, __init__.py wiring, and test suite

### Phase 49: Optimization & Uncomputation
**Goal**: Captured gate sequences are optimized before caching, and compiled function outputs integrate correctly with the automatic uncomputation system
**Depends on**: Phase 48
**Requirements**: OPT-01, OPT-02
**Success Criteria** (what must be TRUE):
  1. A compiled function produces fewer gates than the undecorated version (optimization applied to captured sequence)
  2. Replayed gates come from the optimized sequence, not the original unoptimized capture
  3. A qint returned from a compiled function is correctly uncomputed when it goes out of scope inside a `with` block
**Plans**: 2 plans
Plans:
- [x] 49-01-PLAN.md -- Gate list optimizer, optimize parameter, and stats exposure
- [x] 49-02-PLAN.md -- Uncomputation integration and comprehensive tests

### Phase 50: Controlled Context
**Goal**: Compiled functions work correctly inside `with` blocks, producing controlled gate variants
**Depends on**: Phase 49
**Requirements**: CTL-01, CTL-02, CTL-03
**Success Criteria** (what must be TRUE):
  1. Calling a compiled function inside a `with qbool:` block produces controlled gates (verified via OpenQASM export or circuit inspection)
  2. The same compiled function called outside and inside a `with` block uses separate cache entries (controlled vs uncontrolled)
  3. Nested `with` blocks around compiled function calls produce the correct multi-controlled gates
**Plans**: 2 plans
Plans:
- [x] 50-01-PLAN.md -- Core controlled context implementation (derivation, cache key, replay remapping)
- [x] 50-02-PLAN.md -- Controlled context tests (basic, cache separation, nested with, custom key)

### Phase 51: Differentiators & Polish
**Goal**: Compiled functions support inverse generation, debug introspection, nesting, and the feature has comprehensive test coverage
**Depends on**: Phase 50
**Requirements**: INV-01, INV-02, DBG-01, DBG-02, NST-01, NST-02, INF-03
**Success Criteria** (what must be TRUE):
  1. Calling `.inverse()` on a compiled function produces the adjoint of the compiled sequence (reversed gate order, adjoint transformations)
  2. Debug mode (`@ql.compile(debug=True)`) prints original operation count alongside optimized gate count and reports cache hits/misses
  3. A compiled function calling another compiled function produces correct results (inner function's replayed gates become part of outer capture)
  4. Comprehensive test suite covers all compilation scenarios: basic capture/replay, different widths, cache invalidation, controlled context, inverse, debug, and nesting
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 48 -> 49 -> 50 -> 51

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
| 51. Differentiators & Polish | v2.0 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 roadmap created: 2026-02-04*
