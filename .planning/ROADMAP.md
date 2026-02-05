# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- v1.9 Pixel-Art Circuit Visualization -- Phases 45-47 (shipped 2026-02-03) -- See `milestones/v1.9-ROADMAP.md`
- v2.0 Function Compilation -- Phases 48-51 (shipped 2026-02-04) -- See `milestones/v2.0-ROADMAP.md`
- v2.1 Compile Enhancements -- Phases 52-54 (shipped 2026-02-05) -- See `milestones/v2.1-ROADMAP.md`
- **v2.2 Performance Optimization** -- Phases 55-61 (active)

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

<details open>
<summary>v2.2 Performance Optimization (Phases 55-61) -- ACTIVE</summary>

### Phase 55: Profiling Infrastructure

**Goal:** Establish cross-layer profiling infrastructure enabling measurement-driven optimization decisions

**Dependencies:** None (foundation for all subsequent phases)

**Requirements:** PROF-01, PROF-02, PROF-03, PROF-04, PROF-05, PROF-06, PROF-07

**Plans:** 3 plans

Plans:
- [x] 55-01-PLAN.md — Add [profiling] extra and QUANTUM_PROFILE build support
- [x] 55-02-PLAN.md — Create ql.profile() context manager and benchmark suite
- [x] 55-03-PLAN.md — Add Makefile profiling targets and verify tool integration

**Success Criteria:**
1. User can run `python -m cProfile` on circuit generation and see function-level timing
2. User can run `memray` to see C extension memory allocation patterns
3. User can run `cython -a` to generate HTML showing Python/C boundary crossings (yellow lines)
4. User can use `ql.profile()` context manager for inline profiling
5. Benchmark suite with pytest-benchmark produces reproducible timing comparisons

---

### Phase 56: Forward/Inverse Depth Fix

**Goal:** Forward compilation path produces same optimized depth as inverse compilation

**Dependencies:** Phase 55 (profiling identifies exact cause)

**Requirements:** FIX-01, FIX-02

**Plans:** 2 plans

Plans:
- [x] 56-01-PLAN.md — Diagnose depth discrepancy between forward/adjoint paths
- [x] 56-02-PLAN.md — Implement fix and add regression tests

**Success Criteria:**
1. Profiling data shows where forward path diverges from inverse optimization
2. `f(x)` produces circuit depth equal to `f.inverse(x)` for same operations
3. Existing compilation tests continue to pass (no regression)

---

### Phase 57: Cython Optimization

**Goal:** Cython hot paths have complete static typing and compiler directives for C-speed execution

**Dependencies:** Phase 55 (profiling identifies hot paths), Phase 56 (optimizer understood)

**Requirements:** CYT-01, CYT-02, CYT-03, CYT-04

**Success Criteria:**
1. `cython -a` shows reduced yellow lines in identified hot path functions
2. Benchmarks show measurable improvement (target: 2-10x in typed sections)
3. Array parameters use memory views where applicable (no Python list overhead)
4. Hot path functions have `boundscheck=False, wraparound=False` where safe

---

### Phase 58: Hardcoded Sequences (1-8 bit)

**Goal:** Pre-computed addition sequences for 1-8 bit widths eliminate runtime QFT generation

**Dependencies:** Phase 55 (profiling confirms addition is hot path)

**Requirements:** HCS-01, HCS-02, HCS-05, HCS-06

**Success Criteria:**
1. Addition operations for 1-4 bit widths use pre-computed gate sequences
2. Addition operations for 5-8 bit widths use pre-computed gate sequences
3. Validation tests confirm hardcoded output matches dynamic generation exactly
4. Width > 8 automatically falls back to dynamic generation

---

### Phase 59: Hardcoded Sequences (9-16 bit)

**Goal:** Extend pre-computed addition sequences to cover 9-16 bit widths

**Dependencies:** Phase 58 (1-8 bit infrastructure validated)

**Requirements:** HCS-03, HCS-04

**Success Criteria:**
1. Addition operations for 9-12 bit widths use pre-computed gate sequences
2. Addition operations for 13-16 bit widths use pre-computed gate sequences
3. Default 8-bit and common 16-bit operations benefit from hardcoded sequences
4. Validation tests confirm all widths 1-16 match dynamic generation

---

### Phase 60: C Hot Path Migration

**Goal:** Top hot paths identified by profiling execute entirely in C without boundary crossing overhead

**Dependencies:** Phase 55 (profiling identifies top 3 hot paths), Phase 57 (Cython optimized first)

**Requirements:** MIG-01, MIG-02, MIG-03

**Success Criteria:**
1. Profiling data identifies top 3 hot paths with >20% potential improvement
2. Identified hot paths migrated to C (hot_paths.h/c) if profiling confirms benefit
3. run_instruction() overhead eliminated for migrated operations
4. Benchmark shows >20% improvement for migrated paths (or documented reason for skipping)

---

### Phase 61: Memory Optimization

**Goal:** Memory allocation overhead in gate creation paths reduced based on profiling data

**Dependencies:** Phase 55 (profiling identifies malloc bottlenecks), Phase 60 (hot paths may eliminate need)

**Requirements:** MEM-01, MEM-02, MEM-03

**Success Criteria:**
1. Memory profiling shows malloc patterns in gate creation paths
2. inject_remapped_gates malloc overhead reduced if profiled as bottleneck
3. gate_t object pooling implemented if profiling shows >10% benefit
4. Memory profiling confirms reduced allocation count in circuit generation

</details>

## Progress

**Execution Order:** 55 -> 56 -> 57 -> 58 -> 59 -> 60 -> 61

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
| 57. Cython Optimization | v2.2 | 0/? | Pending | - |
| 58. Hardcoded Sequences (1-8 bit) | v2.2 | 0/? | Pending | - |
| 59. Hardcoded Sequences (9-16 bit) | v2.2 | 0/? | Pending | - |
| 60. C Hot Path Migration | v2.2 | 0/? | Pending | - |
| 61. Memory Optimization | v2.2 | 0/? | Pending | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 shipped: 2026-02-03*
*Milestone v2.0 shipped: 2026-02-04*
*Milestone v2.1 shipped: 2026-02-05*
*Milestone v2.2 started: 2026-02-05*
