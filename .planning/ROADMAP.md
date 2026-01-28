# Roadmap: Quantum Assembly v1.2

**Milestone:** Automatic Uncomputation
**Phases:** 5
**Requirements:** 17

## Overview

This milestone delivers automatic uncomputation of intermediate qubits in boolean expressions. Phase 16 establishes dependency tracking infrastructure to record which intermediates were created. Phase 17 implements C-level reverse gate generation for creating adjoint circuits. Phase 18 integrates uncomputation with Python object lifetimes, enabling automatic cleanup when qbool variables go out of scope. Phase 19 extends this to quantum conditionals (the `with` statement). Phase 20 adds mode control (lazy vs eager uncomputation) and explicit user control methods.

## Milestones

- v1.0 MVP - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State Removal - Phases 11-15 (shipped 2026-01-28)
- v1.2 Automatic Uncomputation - Phases 16-20 (shipped 2026-01-28)

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 16 | Dependency Tracking | Infrastructure for recording qbool creation dependencies | TRACK-01, TRACK-02, TRACK-03, TRACK-04 | 4 |
| 17 | Reverse Gate Generation | C backend generates adjoint circuits for uncomputation | UNCOMP-01, UNCOMP-04 | 3 |
| 18 | Basic Uncomputation | Automatic cleanup when qbool lifetime ends | UNCOMP-02, UNCOMP-03, SCOPE-02 | 4 |
| 19 | Context Manager Integration | Uncomputation works correctly with `with` statements | SCOPE-01, SCOPE-04 | 3 |
| 20 | Modes and Control | User control over uncomputation strategy and timing | MODE-01, MODE-02, MODE-03, CTRL-01, CTRL-02, SCOPE-03 | 5 |

## Phase Details

<details>
<summary>v1.0 MVP (Phases 1-10) - SHIPPED 2026-01-27</summary>

Delivered production-ready quantum programming framework with variable-width integers, complete arithmetic, bitwise operations, circuit optimization, and comprehensive documentation. 41 plans completed across 10 phases.

</details>

<details>
<summary>v1.1 QPU State Removal (Phases 11-15) - SHIPPED 2026-01-28</summary>

Eliminated global state dependency and implemented efficient comparison operators with classical qint initialization. 13 plans completed across 5 phases.

</details>

### v1.2 Automatic Uncomputation (Complete)

**Milestone Goal:** Automatically uncompute intermediate qubits when their lifetime ends

---

### Phase 16: Dependency Tracking Infrastructure

**Goal:** Record parent-child dependencies when qbool operations create intermediate results

**Requirements:**
- TRACK-01: Track parent-child dependencies when qbool operations create intermediate results
- TRACK-02: Track dependencies from qint comparison results (>, <, ==, etc.)
- TRACK-03: Single ownership model prevents circular reference memory leaks
- TRACK-04: Layer-aware dependency tracking respects existing circuit structure

**Success Criteria:**
1. When qbool operations create intermediates (`~a & b`), the system records which qbool values were used to create the result
2. Comparison operations (`qint > qint`) return qbool with tracked dependencies on the compared qint values
3. Dependency graph uses single ownership (each intermediate has one parent), preventing circular references
4. Dependencies respect circuit layer structure, enabling correct uncomputation ordering

**Dependencies:** None (foundation phase)

**Plans:** 2 plans

Plans:
- [x] 16-01-PLAN.md - Dependency tracking infrastructure and operator modifications
- [x] 16-02-PLAN.md - Tests and verification

---

### Phase 17: C Reverse Gate Generation

**Goal:** Generate adjoint gate sequences for all supported quantum operations

**Requirements:**
- UNCOMP-01: Generate reverse gates (adjoints) for all supported gate types
- UNCOMP-04: Gate-type-specific inversion handles multi-controlled gates and phase gates correctly

**Success Criteria:**
1. C backend can generate reverse gate sequences for basic gates (X->X, H->H)
2. Phase gates invert correctly (P(t)->P(-t), T->Tdagger)
3. Multi-controlled gates reverse correctly (maintaining control structure and gate order)

**Dependencies:** Phase 16 (needs dependency graph to know what to reverse)

**Plans:** 1 plan

Plans:
- [x] 17-01-PLAN.md - C reverse gate function, Python binding, and tests

---

### Phase 18: Basic Uncomputation Integration

**Goal:** Automatically uncompute intermediates when final qbool goes out of scope

**Requirements:**
- UNCOMP-02: Cascade uncomputation through dependency graph when final qbool is uncomputed
- UNCOMP-03: Reverse order (LIFO) cleanup ensures correct uncomputation sequence
- SCOPE-02: Uncompute when qbool is destroyed or goes out of scope

**Success Criteria:**
1. When a qbool variable goes out of scope, its allocated qubits are automatically uncomputed before being freed
2. Uncomputation cascades through dependencies (if A depends on B and C, uncomputing A also uncomputes B and C)
3. Intermediates uncompute in reverse creation order (LIFO), preserving quantum state correctness
4. Both qbool operations (`a & b`) and qint comparisons (`x > y`) trigger uncomputation correctly

**Dependencies:** Phase 17 (needs reverse gate generation to perform uncomputation)

**Plans:** 2 plans

Plans:
- [x] 18-01-PLAN.md - Core uncomputation infrastructure (layer tracking, _do_uncompute method)
- [x] 18-02-PLAN.md - Integration and tests (__del__, .uncompute(), use-after guards)

---

### Phase 19: Context Manager Integration for `with`

**Goal:** Uncompute temporaries automatically when quantum conditional blocks exit

**Requirements:**
- SCOPE-01: Uncompute temporaries automatically when `with` block exits
- SCOPE-04: Scope-aware tracking handles nested `with` statements correctly

**Success Criteria:**
1. Qbool variables created inside a `with` block are automatically uncomputed when the block exits
2. Nested `with` statements uncompute correctly (inner scope before outer scope)
3. Uncomputation respects conditional control structure (gates generated inside controlled context)

**Dependencies:** Phase 18 (extends basic uncomputation to conditional scopes)

**Plans:** 1 plan

Plans:
- [x] 19-01-PLAN.md - Scope stack infrastructure, __enter__/__exit__ integration, and tests

---

### Phase 20: Uncomputation Modes and User Control

**Goal:** Provide user control over uncomputation strategy and explicit override methods

**Requirements:**
- MODE-01: Default lazy mode keeps intermediates until final qbool is uncomputed
- MODE-02: Qubit-saving eager mode (`ql.option("qubit_saving")`) uncomputes intermediates immediately
- MODE-03: Per-circuit mode switching allows different strategies in same program
- CTRL-01: Clear error messages when uncomputation fails or is invalid
- CTRL-02: Explicit `uncompute()` method available for manual control
- SCOPE-03: Explicit `.keep()` method allows opt-out of automatic uncomputation

**Success Criteria:**
1. Default behavior (lazy mode) keeps intermediates alive until the final result is uncomputed, minimizing gate count
2. Eager mode (`ql.option("qubit_saving")`) uncomputes intermediates immediately after use, minimizing peak qubit count
3. Users can call `.uncompute()` explicitly on qbool variables to trigger early cleanup
4. Users can call `.keep()` on qbool variables to prevent automatic uncomputation
5. Error messages clearly indicate when uncomputation cannot be performed (e.g., value still in use)

**Dependencies:** Phase 19 (all basic and scope-aware features complete)

**Plans:** 4 plans

Plans:
- [x] 20-01-PLAN.md - Option API and mode-aware automatic uncomputation
- [x] 20-02-PLAN.md - .keep() method for opt-out of automatic uncomputation
- [x] 20-03-PLAN.md - Enhanced error messages for uncomputation failures
- [x] 20-04-PLAN.md - Comprehensive Phase 20 test suite

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRACK-01 | Phase 16 | Complete |
| TRACK-02 | Phase 16 | Complete |
| TRACK-03 | Phase 16 | Complete |
| TRACK-04 | Phase 16 | Complete |
| UNCOMP-01 | Phase 17 | Complete |
| UNCOMP-04 | Phase 17 | Complete |
| UNCOMP-02 | Phase 18 | Complete |
| UNCOMP-03 | Phase 18 | Complete |
| SCOPE-02 | Phase 18 | Complete |
| SCOPE-01 | Phase 19 | Complete |
| SCOPE-04 | Phase 19 | Complete |
| MODE-01 | Phase 20 | Complete |
| MODE-02 | Phase 20 | Complete |
| MODE-03 | Phase 20 | Complete |
| CTRL-01 | Phase 20 | Complete |
| CTRL-02 | Phase 20 | Complete |
| SCOPE-03 | Phase 20 | Complete |

**Coverage:** 17/17 (100%)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | Complete | 2026-01-27 |
| 2. Clean C Backend | v1.0 | 4/4 | Complete | 2026-01-27 |
| 3. Variable-Width qint | v1.0 | 4/4 | Complete | 2026-01-27 |
| 4. Arithmetic Operations | v1.0 | 5/5 | Complete | 2026-01-27 |
| 5. Comparison Operations | v1.0 | 4/4 | Complete | 2026-01-27 |
| 6. Bitwise Operations | v1.0 | 4/4 | Complete | 2026-01-27 |
| 7. Python Integration | v1.0 | 4/4 | Complete | 2026-01-27 |
| 8. Circuit Optimization | v1.0 | 4/4 | Complete | 2026-01-27 |
| 9. Documentation | v1.0 | 4/4 | Complete | 2026-01-27 |
| 10. Testing & Validation | v1.0 | 4/4 | Complete | 2026-01-27 |
| 11. QPU State Analysis | v1.1 | 2/2 | Complete | 2026-01-28 |
| 12. Multi-Controlled Gates | v1.1 | 3/3 | Complete | 2026-01-28 |
| 13. Equality Refactoring | v1.1 | 3/3 | Complete | 2026-01-28 |
| 14. Ordering Operators | v1.1 | 3/3 | Complete | 2026-01-28 |
| 15. Classical Initialization | v1.1 | 2/2 | Complete | 2026-01-28 |
| 16. Dependency Tracking | v1.2 | 2/2 | Complete | 2026-01-28 |
| 17. Reverse Gate Generation | v1.2 | 1/1 | Complete | 2026-01-28 |
| 18. Basic Uncomputation | v1.2 | 2/2 | Complete | 2026-01-28 |
| 19. Context Manager Integration | v1.2 | 1/1 | Complete | 2026-01-28 |
| 20. Modes and Control | v1.2 | 4/4 | Complete | 2026-01-28 |

---
*Roadmap created: 2026-01-28*
