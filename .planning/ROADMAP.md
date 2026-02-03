# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- v1.8 Quantum Copy, Array Mutability & Uncomputation Fix -- Phases 41-44 (shipped 2026-02-03) -- See `milestones/v1.8-ROADMAP.md`
- **v1.9 Pixel-Art Circuit Visualization** -- Phases 45-47 (in progress)

## Phases

<details>
<summary>v1.8 Quantum Copy, Array Mutability & Uncomputation Fix (Phases 41-44) -- SHIPPED 2026-02-03</summary>

- [x] Phase 41: Uncomputation Fix (2/2 plans) -- completed 2026-02-02
- [x] Phase 42: Quantum Copy Foundation (1/1 plan) -- completed 2026-02-02
- [x] Phase 43: Copy-Aware Binary Ops (2/2 plans) -- completed 2026-02-02
- [x] Phase 44: Array Mutability (2/2 plans) -- completed 2026-02-03

</details>

### v1.9 Pixel-Art Circuit Visualization (In Progress)

**Milestone Goal:** Add compact pixel-art circuit visualization that scales to 200+ qubits where existing tools fail.

- [x] **Phase 45: Data Extraction Bridge** - Cython binding exposing per-gate circuit data to Python -- completed 2026-02-03
- [x] **Phase 46: Core Renderer** - NumPy-based pixel-art rendering of complete circuits at overview scale -- completed 2026-02-03
- [ ] **Phase 47: Detail Mode & Public API** - Detail zoom, auto-selection, and ql.draw_circuit() API

## Phase Details

### Phase 45: Data Extraction Bridge
**Goal**: Python code can access structured per-gate circuit data with compact qubit indexing
**Depends on**: Nothing (first phase of v1.9)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. Calling `circuit.draw_data()` on a built circuit returns a Python dict containing gate type, target qubit, control qubits, angle, and layer index for every gate
  2. Unused qubit rows are eliminated and sparse C-backend indices are remapped to dense sequential rows (e.g., C indices [0,1,62,63] become rows [0,1,2,3])
  3. The extraction handles circuits with 200+ qubits and 10,000+ gates without errors or excessive memory use
**Plans**: 2 plans

Plans:
- [x] 45-01-PLAN.md -- C extraction function (draw_data_t) and Cython bridge (draw_data() method)
- [x] 45-02-PLAN.md -- Integration tests: compaction, controls, scale, gate types

### Phase 46: Core Renderer
**Goal**: Users can render any quantum circuit as a compact pixel-art PNG showing all gates, wires, and control connections at overview scale
**Depends on**: Phase 45
**Requirements**: REND-01, REND-02, REND-03, REND-04, REND-05, REND-06, ZOOM-01
**Success Criteria** (what must be TRUE):
  1. Every active qubit has a visible horizontal wire line spanning the full circuit width
  2. All 10 gate types (X, Y, Z, R, H, Rx, Ry, Rz, P, M) render as distinct 2-3px colored icons at their correct (layer, qubit) position
  3. Multi-qubit gates (CNOT, CCX, MCX) show vertical connection lines between control and target qubits, with control dots at control positions
  4. Rendering uses NumPy array bulk operations (not per-pixel ImageDraw calls) and produces a valid PIL Image
  5. A circuit with 200+ qubits and 10,000+ gates renders successfully as a PNG without crashing or exceeding memory limits
**Plans**: 3 plans

Plans:
- [x] 46-01-PLAN.md -- draw.py renderer with layout engine, wires, single-qubit gate rendering, Pillow dep, and basic tests
- [x] 46-02-PLAN.md -- Multi-qubit control lines, control dots, rendering order, and multi-qubit gate tests
- [x] 46-03-PLAN.md -- Scale testing at 200+ qubits / 10K+ gates and real circuit integration test

### Phase 47: Detail Mode & Public API
**Goal**: Users can visualize circuits at two zoom levels with automatic selection and a clean public API
**Depends on**: Phase 46
**Requirements**: ZOOM-02, ZOOM-03, ZOOM-04, OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Detail mode renders gates at 8-12px with readable gate type labels, usable for circuits up to ~30 qubits
  2. Auto-zoom selects detail mode for small circuits (<=30 qubits and <=200 layers) and overview mode otherwise
  3. User can override auto-zoom by passing `mode="overview"` or `mode="detail"`
  4. `ql.draw_circuit()` returns a PIL Image that can be saved to PNG via `.save("file.png")`
  5. Importing the visualization module when Pillow is not installed raises a helpful error message
**Plans**: 2 plans

Plans:
- [ ] 47-01-PLAN.md -- Detail mode rendering with gate labels (render_detail function + tests)
- [ ] 47-02-PLAN.md -- Auto-zoom selection and public API (ql.draw_circuit, lazy Pillow import)

## Progress

**Execution Order:** 45 -> 46 -> 47

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 41. Uncomputation Fix | v1.8 | 2/2 | Complete | 2026-02-02 |
| 42. Quantum Copy Foundation | v1.8 | 1/1 | Complete | 2026-02-02 |
| 43. Copy-Aware Binary Ops | v1.8 | 2/2 | Complete | 2026-02-02 |
| 44. Array Mutability | v1.8 | 2/2 | Complete | 2026-02-03 |
| 45. Data Extraction Bridge | v1.9 | 2/2 | Complete | 2026-02-03 |
| 46. Core Renderer | v1.9 | 3/3 | Complete | 2026-02-03 |
| 47. Detail Mode & Public API | v1.9 | 0/2 | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone v1.8 shipped: 2026-02-03*
*Milestone v1.9 roadmap: 2026-02-03*
