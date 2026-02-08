# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (shipped 2026-02-04) -- See `milestones/v2.0-ROADMAP.md`
- v2.1 Compile Enhancements -- Phases 52-54 (shipped 2026-02-05) -- See `milestones/v2.1-ROADMAP.md`
- v2.2 Performance Optimization -- Phases 55-61 (shipped 2026-02-08) -- See `milestones/v2.2-ROADMAP.md`

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

### v2.3 Hardcoding Right-Sizing (In Progress)

**Milestone Goal:** Benchmark hardcoded vs dynamic gate sequence generation, right-size or eliminate hardcoded sequences based on data, and evaluate whether other operations warrant hardcoding.

- [x] **Phase 62: Measurement** - Benchmark all generation paths and evaluate other operations for hardcoding viability -- completed 2026-02-08
- [x] **Phase 63: Right-Sizing Implementation** - Apply data-driven decisions to right-size addition sequences -- completed 2026-02-08
- [ ] **Phase 64: Regression Verification** - Confirm no performance regression after changes

## Phase Details

### Phase 62: Measurement
**Goal**: Comprehensive benchmarks quantify the cost/benefit of hardcoded sequences for all operation types, producing a data-driven recommendation
**Depends on**: Nothing (first phase of v2.3)
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04, EVAL-01, EVAL-02, EVAL-03
**Success Criteria** (what must be TRUE):
  1. Running a benchmark script produces import time measurements with and without hardcoded sequences loaded, showing the cost in milliseconds
  2. Running a benchmark script produces per-operation first-call generation cost for all 9 operation types (QQ_add, CQ_add, cQQ_add, cCQ_add, QQ_mul, CQ_mul, Q_xor, Q_and, Q_or) at widths 1-16
  3. Running a benchmark script produces per-call dispatch overhead comparing hardcoded lookup vs dynamic cache hit, showing whether the difference is measurable
  4. A comparison report exists showing hardcoded vs dynamic cost per operation/width, with import time amortization analysis (break-even point in calls)
  5. Multiplication, bitwise, and division generation costs are each measured and documented with a clear keep/hardcode/skip recommendation
**Plans:** 2 plans
Plans:
- [x] 62-01-PLAN.md -- Benchmark measurement engine (BENCH-01, BENCH-02, BENCH-03)
- [x] 62-02-PLAN.md -- Evaluation and comparison report (EVAL-01/02/03, BENCH-04)

### Phase 63: Right-Sizing Implementation
**Goal**: Addition hardcoded sequences are right-sized (kept, factored, or removed) based on Phase 62 measurements
**Depends on**: Phase 62
**Requirements**: ADD-01, ADD-02, ADD-03
**Success Criteria** (what must be TRUE):
  1. A documented decision exists stating which addition widths (if any) remain hardcoded, with data justification from Phase 62 benchmarks
  2. If hardcoded sequences are kept: shared QFT/IQFT sub-sequences are factored out, reducing total generated C file size measurably
  3. If hardcoded sequences are removed: all hardcoded sequence files are deleted, the build system no longer references them, and dynamic generation handles all widths
  4. The existing test suite (`pytest tests/python/ -v`) passes after implementation changes
**Plans:** 1 plan
Plans:
- [x] 63-01-PLAN.md -- Decision document + shared QFT/IQFT factoring (ADD-01, ADD-02)

### Phase 64: Regression Verification
**Goal**: End-to-end circuit generation performance is verified to have no regression after right-sizing changes
**Depends on**: Phase 63
**Requirements**: ADD-04
**Success Criteria** (what must be TRUE):
  1. A benchmark comparing circuit generation throughput before and after changes shows no regression (or documents acceptable trade-offs with justification)
  2. The full test suite passes with zero new failures compared to the v2.2 baseline
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 62 -> 63 -> 64

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
| 64. Regression Verification | v2.3 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 shipped: 2026-02-05*
*Milestone v2.2 shipped: 2026-02-08*
*Milestone v2.3 roadmap added: 2026-02-08*
