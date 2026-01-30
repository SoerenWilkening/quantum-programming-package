# Roadmap: Quantum Assembly

## Milestones

- v1.0 MVP - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State - Phases 11-15 (shipped 2026-01-28)
- v1.2 Uncomputation - Phases 16-20 (shipped 2026-01-28)
- v1.3 Package & Array - Phases 21-24 (shipped 2026-01-29)
- v1.4 OpenQASM Export - Phases 25-27 (shipped 2026-01-30)
- **v1.5 Bug Fixes & Exhaustive Verification** - Phases 28-33 (in progress)

## v1.5 Bug Fixes & Exhaustive Verification

**Milestone Goal:** Fix all known C backend bugs and exhaustively verify every operation category through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check).

### Phase Overview

- [x] **Phase 28: Verification Framework & Init** - Reusable test framework with parameterized generation and init verification
- [ ] **Phase 29: C Backend Bug Fixes** - Fix subtraction, comparison, multiplication, and QFT addition bugs
- [ ] **Phase 30: Arithmetic Verification** - Exhaustive verification of all arithmetic operations
- [ ] **Phase 31: Comparison Verification** - Exhaustive verification of all comparison operators and variants
- [ ] **Phase 32: Bitwise Verification** - Verification of all bitwise operations across widths
- [ ] **Phase 33: Advanced Feature Verification** - Verify uncomputation, conditionals, and array operations

## Phase Details

### Phase 28: Verification Framework & Init
**Goal**: A reusable, parameterized test framework exists that can build any operation circuit, export to OpenQASM, simulate via Qiskit, and report clear pass/fail diagnostics -- proven working with qint initialization tests.
**Depends on**: Nothing (builds on v1.4 verification script as starting point)
**Requirements**: VFWK-01, VFWK-02, VFWK-03, VINIT-01
**Success Criteria** (what must be TRUE):
  1. A test function can be called with operation type, operands, and bit width to automatically build circuit, export OpenQASM, simulate, and check result
  2. Tests can be parameterized to generate exhaustive combinations for small widths (1-4 bits) and representative samples for larger widths
  3. Test failures display expected value, actual value, operation name, operand values, and bit width
  4. Classical qint initialization is verified correct for all bit widths 1 through 8 (exhaustive value coverage for 1-4 bits)
**Plans**: 2 plans

Plans:
- [x] 28-01-PLAN.md -- Reusable verification framework (conftest fixture + helpers)
- [x] 28-02-PLAN.md -- Exhaustive qint initialization verification

### Phase 29: C Backend Bug Fixes
**Goal**: All four known C backend bugs are fixed -- subtraction underflow, less-or-equal comparison, multiplication segfault, and QFT addition with nonzero operands all produce correct results.
**Depends on**: Phase 28 (framework used to verify fixes)
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04
**Success Criteria** (what must be TRUE):
  1. `qint(3) - qint(7)` on 4-bit integers returns the correct unsigned wrap result (12), not 7
  2. `qint(5) <= qint(5)` returns 1 (true), not 0
  3. Multiplication operations complete without segfault across all tested bit widths (1-4 bits exhaustive)
  4. QFT-based addition of two nonzero operands (e.g., `qint(3) + qint(5)`) returns the correct sum
  5. All four fixes pass through the full verification pipeline (OpenQASM export -> Qiskit simulate -> result check)
**Plans**: 2 plans

Plans:
- [ ] 29-01-PLAN.md -- Fix BUG-01 (subtraction underflow) and BUG-02 (less-or-equal comparison) in Python operator logic
- [ ] 29-02-PLAN.md -- Fix BUG-03 (multiplication segfault) and BUG-04 (QFT addition) in C backend

### Phase 30: Arithmetic Verification
**Goal**: Every arithmetic operation (add, subtract, multiply, divide, modulo, modular arithmetic) is exhaustively verified at small bit widths and representatively tested at larger widths.
**Depends on**: Phase 29 (bug fixes must land first so tests pass)
**Requirements**: VARITH-01, VARITH-02, VARITH-03, VARITH-04, VARITH-05
**Success Criteria** (what must be TRUE):
  1. Addition is verified for all input pairs at 1-4 bit widths and representative pairs at 5-8 bits
  2. Subtraction is verified for all input pairs at 1-4 bit widths (including underflow wrapping cases)
  3. Multiplication is verified for all input pairs at 1-3 bit widths and representative pairs at 4-5 bits
  4. Division and modulo operations produce correct quotient and remainder for tested input pairs
  5. Modular arithmetic (add mod N, sub mod N, mul mod N) produces correct results for representative inputs
**Plans**: TBD

Plans:
- [ ] 30-01: TBD
- [ ] 30-02: TBD

### Phase 31: Comparison Verification
**Goal**: All six comparison operators are verified across qint-vs-int and qint-vs-qint variants, including edge cases.
**Depends on**: Phase 29 (comparison bug fix must be in place)
**Requirements**: VCMP-01, VCMP-02, VCMP-03
**Success Criteria** (what must be TRUE):
  1. All six operators (==, !=, <, >, <=, >=) return correct boolean results for exhaustive input pairs at 1-4 bit widths
  2. Both qint-vs-int and qint-vs-qint comparison variants produce identical correct results
  3. Edge cases verified: equal values, zero compared to nonzero, maximum value boundaries, minimum (0) boundaries
**Plans**: TBD

Plans:
- [ ] 31-01: TBD

### Phase 32: Bitwise Verification
**Goal**: All bitwise operations (AND, OR, XOR, NOT) are verified including variable-width operand combinations.
**Depends on**: Phase 28 (framework only; no bug fixes needed for bitwise)
**Requirements**: VBIT-01, VBIT-02
**Success Criteria** (what must be TRUE):
  1. AND, OR, XOR, NOT operations return correct results for exhaustive input pairs at 1-4 bit widths
  2. Bitwise operations between operands of different widths produce correct results (e.g., 3-bit AND 4-bit)
**Plans**: TBD

Plans:
- [ ] 32-01: TBD

### Phase 33: Advanced Feature Verification
**Goal**: Automatic uncomputation, quantum conditionals, and array operations are verified through the full pipeline.
**Depends on**: Phase 30 (arithmetic verification confirms operations work; advanced features build on them)
**Requirements**: VADV-01, VADV-02, VADV-03
**Success Criteria** (what must be TRUE):
  1. After operations with uncomputation enabled, ancilla qubits are measured in |0> state (verified via Qiskit simulation)
  2. Quantum conditional blocks (`with qbool:`) correctly gate operations on the condition qubit's value
  3. ql.array reductions (sum, AND-reduce, OR-reduce) and element-wise operations produce correct results
**Plans**: TBD

Plans:
- [ ] 33-01: TBD
- [ ] 33-02: TBD

## Progress

**Execution Order:** 28 -> 29 -> 30 -> 31 -> 32 -> 33
(Note: Phase 32 can execute in parallel with 30-31 since it only depends on Phase 28)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 28. Verification Framework & Init | v1.5 | 2/2 | ✓ Complete | 2026-01-30 |
| 29. C Backend Bug Fixes | v1.5 | 0/TBD | Not started | - |
| 30. Arithmetic Verification | v1.5 | 0/TBD | Not started | - |
| 31. Comparison Verification | v1.5 | 0/TBD | Not started | - |
| 32. Bitwise Verification | v1.5 | 0/TBD | Not started | - |
| 33. Advanced Feature Verification | v1.5 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-30*
*Last updated: 2026-01-30*
