# Roadmap: Quantum Assembly

## Milestones

- v1.0 through v1.7: See milestone archives
- **v1.8 Quantum Copy, Array Mutability & Uncomputation Fix** - Phases 41-44 (in progress)

## Phases

### v1.8 Quantum Copy, Array Mutability & Uncomputation Fix

**Milestone Goal:** Enable quantum state copying for correct binary operations, make arrays mutable via augmented assignment, and fix the uncomputation regression.

**Phase Numbering:**
- Integer phases (41, 42, 43, 44): Planned milestone work
- Decimal phases (e.g., 42.1): Urgent insertions (marked with INSERTED)

- [x] **Phase 41: Uncomputation Fix** - Investigate and fix the uncomputation regression
- [x] **Phase 42: Quantum Copy Foundation** - CNOT-based quantum state copy for qint
- [ ] **Phase 43: Copy-Aware Binary Operations** - Binary ops use quantum copy instead of classical initialization
- [ ] **Phase 44: Array Mutability** - In-place augmented assignment for qarray elements

## Phase Details

### Phase 41: Uncomputation Fix
**Goal**: Automatic uncomputation works correctly -- expressions uncompute on scope exit without corrupting state
**Depends on**: Nothing (regression fix, highest priority)
**Requirements**: UNCOMP-01, UNCOMP-02
**Success Criteria** (what must be TRUE):
  1. The root cause of the uncomputation regression is identified and documented
  2. Expressions inside `with` blocks uncompute correctly when the scope exits
  3. Existing uncomputation tests pass (no new regressions introduced)
  4. Temporary qubits allocated during expressions are properly cleaned up
**Plans**: 2 plans

Plans:
- [x] 41-01-PLAN.md — Integrate .pxi files, add layer tracking, fix uncomputation regression
- [x] 41-02-PLAN.md — Gap closure: add layer tracking to __lt__/__gt__ widened-temp comparisons

### Phase 42: Quantum Copy Foundation
**Goal**: Users can create quantum copies of qint values using CNOT-based entanglement
**Depends on**: Phase 41 (uncomputation must work correctly before adding new qubit operations)
**Requirements**: COPY-01
**Success Criteria** (what must be TRUE):
  1. `qint.copy()` (or equivalent API) returns a new qint with fresh qubits CNOT-entangled to the source
  2. The copied qint has the same bit width as the source
  3. Measuring the copy produces the same value as measuring the source (for computational basis states)
  4. The copy's qubits are distinct from the source's qubits (no shared qubit references)
**Plans**: 1 plan

Plans:
- [x] 42-01-PLAN.md — Implement copy()/copy_onto() on qint, qbool.copy() override, and Qiskit-verified tests

### Phase 43: Copy-Aware Binary Operations
**Goal**: Binary operations on qint and qarray preserve quantum state by using quantum copy instead of classical value initialization
**Depends on**: Phase 42 (quantum copy must exist)
**Requirements**: COPY-02, COPY-03
**Success Criteria** (what must be TRUE):
  1. `qint + int` and `qint + qint` produce a result where the source operand is quantum-copied before the operation is applied
  2. `qarray + qarray` (and `-`, `*`, etc.) returns a new array whose elements are quantum-copied from the source before the operation
  3. The original qint/qarray operands are unmodified after the binary operation
  4. Generated circuits contain CNOT gates for the copy step, not classical reinitialization
**Plans**: 2 plans

Plans:
- [ ] 43-01-PLAN.md — Fix __add__, __radd__, __sub__ to use XOR-copy instead of classical init + tests
- [ ] 43-02-PLAN.md — Add missing qint ops (neg, rsub, lshift, rshift) + missing qarray ops + tests

### Phase 44: Array Mutability
**Goal**: Users can modify qarray elements in-place using augmented assignment operators
**Depends on**: Phase 41 (uncomputation correctness needed for in-place ops)
**Requirements**: AMUT-01, AMUT-02, AMUT-03
**Success Criteria** (what must be TRUE):
  1. `qarray[i] += x` modifies the element's existing qubits in-place (works for x as int, qint, or qbool)
  2. `qarray[i] -= x`, `qarray[i] *= x`, and other augmented assignments work in-place without allocating new qubits for the element
  3. Multi-dimensional indexing supports in-place ops (`qarray[i, j] += x`)
  4. Reading the element after in-place modification reflects the updated value
  5. The qarray's structure (length, element bit widths) is unchanged after in-place modification
**Plans**: TBD

Plans:
- [ ] 44-01: Implement qarray __setitem__ for augmented assignment
- [ ] 44-02: Multi-dimensional in-place operations

## Progress

**Execution Order:**
Phases execute in numeric order: 41 -> 42 -> 43 -> 44

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 41. Uncomputation Fix | 2/2 | ✓ Complete | 2026-02-02 |
| 42. Quantum Copy Foundation | 1/1 | ✓ Complete | 2026-02-02 |
| 43. Copy-Aware Binary Ops | 0/TBD | Not started | - |
| 44. Array Mutability | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-02*
*Milestone: v1.8*
