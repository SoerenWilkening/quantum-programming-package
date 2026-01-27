# Roadmap: Quantum Assembly

## Milestones

- v1.0 Initial Release - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State Removal & Comparison Refactoring - Phases 11-15 (in progress)

## Phases

<details>
<summary>v1.0 Initial Release (Phases 1-10) - SHIPPED 2026-01-27</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for full milestone details.

**Phases:**
1. Testing Foundation - Characterization tests and infrastructure
2. C Layer Cleanup - Eliminate global state and fix memory bugs
3. Memory Architecture - Centralized qubit allocator
4. Module Separation - Split QPU.c into focused modules
5. Variable-Width Integers - 1-64 bit quantum integers
6. Bit Operations - Bitwise operations with operator overloading
7. Extended Arithmetic - Multiplication, division, modulo, modular arithmetic
8. Circuit Optimization - Statistics, visualization, optimization passes
9. Code Organization - Category-based module headers
10. Documentation and API Polish - Comprehensive docs and tests

**Summary:** 41 plans, 3.14 hours total execution time, all 37 v1.0 requirements shipped.

</details>

### v1.1 QPU State Removal & Comparison Refactoring (Complete)

**Milestone Goal:** Remove global state dependency (QPU_state R0-R3 registers) and refactor comparison operations for cleaner architecture and efficient implementation.

- [x] **Phase 11: Global State Removal** - Remove QPU_state global dependency
- [x] **Phase 12: Comparison Function Refactoring** - Implement comparison functions with explicit parameters
- [x] **Phase 13: Equality Comparison** - Implement qint == int and qint == qint
- [x] **Phase 14: Ordering Comparisons** - Refactor <= and >= for efficiency
- [x] **Phase 15: Classical Initialization** - Initialize qint with classical values

## Phase Details

### Phase 11: Global State Removal
**Goal:** Remove QPU_state global dependency from C backend, eliminating the last remnant of global state
**Depends on:** Nothing (first phase of v1.1)
**Requirements:** GLOB-01, GLOB-04 (CC_equal removal completed here)
**Success Criteria** (what must be TRUE):
  1. QPU_state global variable and R0-R3 registers are completely removed from C backend
  2. All C functions that previously used QPU_state now use local variables or parameters
  3. All tests pass without any global state dependencies
  4. Memory leak checks confirm no leaked register qubits
**Plans:** 5 plans in 4 waves

Plans:
- [x] 11-01-PLAN.md - Remove purely classical functions (CC_add, CC_mul, CC_equal, etc.)
- [x] 11-02-PLAN.md - Refactor P_add/cP_add to take explicit phase parameter
- [x] 11-03-PLAN.md - Refactor legacy logic functions to take explicit width/value parameters
- [x] 11-04-PLAN.md - Remove QPU_state global, instruction_t type, and infrastructure
- [x] 11-05-PLAN.md - Update Python bindings and verify full test suite

### Phase 12: Comparison Function Refactoring
**Goal:** Implement CQ_equal_width and cCQ_equal_width to generate quantum gate sequences for classical-quantum comparison
**Depends on:** Phase 11
**Requirements:** GLOB-02, GLOB-03
**Success Criteria** (what must be TRUE):
  1. CQ_equal_width(bits, value) generates quantum gates comparing quantum register to classical value
  2. cCQ_equal_width(bits, value) generates controlled comparison gates
  3. Functions return empty sequence for overflow (value >= 2^bits), NULL for invalid width
  4. C-level tests verify function behavior directly (no Python dependency)
**Plans:** 2 plans in 2 waves

Plans:
- [x] 12-01-PLAN.md - Implement CQ_equal_width, cCQ_equal_width, and add C-level unit tests
- [x] 12-02-PLAN.md - Close gap: implement proper n-bit AND for 3+ bit comparisons (gap closure)

### Phase 13: Equality Comparison
**Goal:** Implement efficient equality comparison for qint == int and qint == qint using refactored functions
**Depends on:** Phase 12
**Requirements:** COMP-01, COMP-02
**Success Criteria** (what must be TRUE):
  1. User can compare qint == int and get correct quantum boolean result
  2. User can compare qint == qint and get correct result using (qint - qint) == 0 pattern
  3. Equality comparisons use CQ_equal_width with explicit parameters
  4. Python operator overloading (__eq__) works correctly for both cases
  5. Tests verify equality comparisons for various bit widths and values
**Plans:** 2 plans in 2 waves

Plans:
- [x] 13-01-PLAN.md - Refactor __eq__ to use C-level CQ_equal_width and subtract-add-back pattern
- [x] 13-02-PLAN.md - Add comprehensive equality comparison tests

### Phase 14: Ordering Comparisons
**Goal:** Refactor <= and >= operators to use in-place subtraction/addition without temporary qint allocation
**Depends on:** Phase 13
**Requirements:** COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. User can compare qint <= value without allocating temporary qint
  2. User can compare qint >= value without allocating temporary qint
  3. Ordering comparisons use in-place arithmetic operations for efficiency
  4. Python operator overloading (__le__, __ge__) works correctly
  5. Tests verify memory efficiency (no temp qint allocation during comparison)
**Plans:** 2 plans in 2 waves

Plans:
- [x] 14-01-PLAN.md - Refactor __lt__, __gt__, __le__, __ge__ to use in-place subtract-add-back pattern
- [x] 14-02-PLAN.md - Add comprehensive ordering comparison tests

### Phase 15: Classical Initialization
**Goal:** Initialize qint with classical value by setting qubits to |1> based on binary representation
**Depends on:** Phase 11 (independent of comparison refactoring)
**Requirements:** INIT-01
**Success Criteria** (what must be TRUE):
  1. User can create qint with classical initial value (e.g., qint(5, width=8) creates 8-bit qint initialized to 5)
  2. Initialization sets qubits to |1> via Q_not based on binary representation
  3. Auto-width mode: qint(5) creates minimum-width qint initialized to 5
  4. Initialized qint can be used in arithmetic and comparison operations
  5. Tests verify correct initialization for various bit widths and values
**Plans:** 2 plans in 2 waves

Plans:
- [x] 15-01-PLAN.md - Implement auto-width calculation and X gate initialization in qint.__init__()
- [x] 15-02-PLAN.md - Add comprehensive initialization tests

## Progress

**Execution Order:**
Phases execute in numeric order: 11 -> 12 -> 13 -> 14 -> 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Global State Removal | v1.1 | 5/5 | Complete | 2026-01-27 |
| 12. Comparison Function Refactoring | v1.1 | 2/2 | Complete | 2026-01-27 |
| 13. Equality Comparison | v1.1 | 2/2 | Complete | 2026-01-27 |
| 14. Ordering Comparisons | v1.1 | 2/2 | Complete | 2026-01-27 |
| 15. Classical Initialization | v1.1 | 2/2 | Complete | 2026-01-27 |

---
*Last updated: 2026-01-27 — Phase 15 complete, v1.1 milestone complete*
