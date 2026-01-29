# Roadmap: Quantum Assembly v1.3

## Overview

This milestone transforms Quantum Assembly's package structure for maintainability and introduces `ql.array` — a homogeneous quantum array class supporting qint and qbool elements. The roadmap progresses from package restructuring (foundation) through array class creation, reduction operations with optimal O(log n) depth, and element-wise operations between arrays.

## Milestones

- v1.0 MVP - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State - Phases 11-15 (shipped 2026-01-28)
- v1.2 Uncomputation - Phases 16-20 (shipped 2026-01-28)
- **v1.3 Package Structure & ql.array** - Phases 21-24 (in progress)

## Phases

- [x] **Phase 21: Package Restructuring** - Split large Cython files, create proper package structure
- [x] **Phase 22: Array Class Foundation** - Create ql.array with qint/qbool support and Python integration
- [ ] **Phase 23: Array Reductions** - Implement AND/OR/XOR/sum reductions with pairwise tree structure
- [ ] **Phase 24: Element-wise Operations** - Implement arithmetic, bitwise, and comparison operators between arrays

## Phase Details

### Phase 21: Package Restructuring
**Goal**: Maintainable package structure with proper Python packaging and manageable file sizes
**Depends on**: v1.2 completion (Phase 20)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):
  1. Package can be imported with `import quantum_language` and all submodules are accessible
  2. No single Cython file exceeds ~300 lines (excluding generated code)
  3. All existing tests pass without modification
  4. Import statements throughout codebase use new package structure
**Plans**: 7 plans in 4 waves

Plans:
- [x] 21-01-PLAN.md — Create src layout, .pxd declaration files, and _core.pyx with accessor functions
- [x] 21-02-PLAN.md — Extract qint.pyx, qbool.pyx, qint_mod.pyx type modules
- [x] 21-03-PLAN.md — Create state/ subpackage and __init__.py public API
- [x] 21-04-PLAN.md — Update setup.py for multi-extension build
- [x] 21-05-PLAN.md — Migrate test imports to use installed package
- [x] 21-06-PLAN.md — (Gap closure) Extract arithmetic and bitwise operations to include files
- [x] 21-07-PLAN.md — (Gap closure) Extract comparison and division operations (Cython limitation blocked refactor)

### Phase 22: Array Class Foundation
**Goal**: Users can create and manipulate multi-dimensional quantum arrays with natural Python syntax
**Depends on**: Phase 21
**Requirements**: ARR-01, ARR-02, ARR-03, ARR-04, ARR-05, ARR-06, ARR-07, ARR-08, PYI-01, PYI-02, PYI-03, PYI-04
**Success Criteria** (what must be TRUE):
  1. User can create array from Python list or NumPy array: `arr = ql.array([1, 2, 3])` or `arr = ql.array(np_array)` (auto-width)
  2. User can create array with explicit width: `arr = ql.array([1, 2, 3], width=8)`
  3. User can create array from dimensions: `arr = ql.array(dim=(3,3), dtype=ql.qint)`
  4. User can access elements with NumPy-style indexing: `A[i,j]`, `A[:, j]`, `A[1:3, 0:2]`
  5. User can iterate over flattened array: `for x in arr: ...`
  6. Mixed-type arrays (qint + qbool) raise clear error at construction time
**Plans**: 5 plans in 4 waves

Plans:
- [x] 22-01-PLAN.md — Create qarray.pyx/pxd with core data structure and flat list construction
- [x] 22-02-PLAN.md — Multi-dimensional construction and NumPy-style indexing with view semantics
- [x] 22-03-PLAN.md — Extended construction API: width, dtype, dim, NumPy array support
- [x] 22-04-PLAN.md — Python integration: iteration, immutability, compact repr
- [x] 22-05-PLAN.md — Public API integration and comprehensive test suite

### Phase 23: Array Reductions
**Goal**: Users can reduce arrays to single values with optimal circuit depth
**Depends on**: Phase 22
**Requirements**: RED-01, RED-02, RED-03, RED-04
**Success Criteria** (what must be TRUE):
  1. User can AND-reduce: `result = &arr` returns qbool (all elements)
  2. User can OR-reduce: `result = |arr` returns qbool (any element)
  3. User can XOR-reduce: `result = ^arr` returns qbool (parity)
  4. User can sum: `result = sum(arr)` returns qint with appropriate width
  5. All reductions use pairwise tree structure achieving O(log n) circuit depth
  6. Multi-dimensional arrays are flattened before reduction
**Plans**: 2 plans in 2 waves

Plans:
- [ ] 23-01-PLAN.md — AND/OR/XOR reduction methods with pairwise tree and linear chain algorithms
- [ ] 23-02-PLAN.md — Sum reduction, module-level functions, and comprehensive test suite

### Phase 24: Element-wise Operations
**Goal**: Users can perform element-wise operations between arrays of equal shape
**Depends on**: Phase 23
**Requirements**: ELM-01, ELM-02, ELM-03, ELM-04, ELM-05
**Success Criteria** (what must be TRUE):
  1. User can perform element-wise arithmetic: `C = A + B`, `C = A - B`, `C = A * B`
  2. User can perform element-wise bitwise: `C = A & B`, `C = A | B`, `C = A ^ B`
  3. User can perform element-wise comparison: `C = A < B` returns array of qbool
  4. User can perform in-place operations: `A += B`, `A -= B`, `A *= B`, `A &= B`, `A |= B`, `A ^= B`
  5. Mismatched array shapes raise clear error with shapes shown
  6. Result arrays preserve input shape
**Plans**: TBD

Plans:
- [ ] 24-01: TBD

## Progress

**Execution Order:** 21 -> 22 -> 23 -> 24

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 21. Package Restructuring | v1.3 | 7/7 | Complete | 2026-01-29 |
| 22. Array Class Foundation | v1.3 | 5/5 | Complete | 2026-01-29 |
| 23. Array Reductions | v1.3 | 0/2 | Not started | - |
| 24. Element-wise Operations | v1.3 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-29*
*Last updated: 2026-01-29*
