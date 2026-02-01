# Roadmap: Quantum Assembly

## Milestones

- v1.0 MVP - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State Removal - Phases 11-15 (shipped 2026-01-28)
- v1.2 Automatic Uncomputation - Phases 16-20 (shipped 2026-01-28)
- v1.3 Package & Array - Phases 21-24 (shipped 2026-01-29)
- v1.4 OpenQASM Export - Phases 25-27 (shipped 2026-01-30)
- v1.5 Bug Fixes & Verification - Phases 28-33 (shipped 2026-02-01)
- v1.6 Array & Comparison Fixes - Phases 34-36 (in progress)

## Overview

v1.6 fixes three categories of bugs discovered during v1.5 exhaustive verification: array constructor and element-wise operation bugs, comparison operator inversion and boundary errors, and circuit size explosion for ordering comparisons. Phases proceed from array fixes (independent of comparison code) through comparison fixes (independent of array code) to a final verification phase that converts xfail tests to passing and confirms no regressions.

## Phases

- [x] **Phase 34: Array Fixes** - Fix constructor value initialization and element-wise operations
- [ ] **Phase 35: Comparison Bug Fixes** - Fix eq/ne inversion, MSB boundary errors, and circuit explosion
- [ ] **Phase 36: Verification & Regression** - Convert xfail tests to passing and confirm no regressions

## Phase Details

### Phase 34: Array Fixes
**Goal**: Users can create quantum arrays with correct initial values and perform element-wise operations that produce correct circuits
**Depends on**: Nothing (first phase in v1.6; array and comparison fixes are independent)
**Requirements**: ARR-FIX-01, ARR-FIX-02, ARR-FIX-03, ARR-FIX-04, ARR-FIX-05
**Success Criteria** (what must be TRUE):
  1. `ql.array([3, 5, 7], width=4)` creates elements with values 3, 5, 7 (not value=4 for all)
  2. Each array element allocates exactly `width` qubits (e.g., width=3 gives 3 qubits per element)
  3. `A + B` and `A - B` between two arrays produce circuits that simulate to correct results via Qiskit
  4. `A += B` and `A -= B` produce correct circuits when both arrays have matching element widths
  5. All previously xfail array verification tests from v1.5 pass
**Plans**: 1 plan

Plans:
- [x] 34-01: Fix array constructor and verify all array operations

### Phase 35: Comparison Bug Fixes
**Goal**: All six comparison operators produce correct results for all value pairs and reasonable circuit sizes
**Depends on**: Nothing (independent of Phase 34; comparison code is separate from array code)
**Requirements**: CMP-FIX-01, CMP-FIX-02, CMP-FIX-03
**Success Criteria** (what must be TRUE):
  1. `qint(3) == qint(3)` returns true and `qint(3) == qint(5)` returns false (eq/ne no longer inverted)
  2. Ordering comparisons at MSB boundary values (e.g., 3 < 4 where 4 is MSB for 3-bit) return correct results
  3. `gt` and `le` operations at width=6 produce circuits with gate count proportional to width (not exponential)
  4. All 488 previously xfail eq/ne tests pass after the inversion fix
**Plans**: 2 plans

Plans:
- [ ] 35-01: Fix eq/ne comparison inversion (remove GC-triggering layer tracking from __eq__)
- [ ] 35-02: Fix ordering comparison MSB boundary errors (widen __lt__) and investigate circuit explosion

### Phase 36: Verification & Regression
**Goal**: All fixed bugs are verified passing and no existing tests regress
**Depends on**: Phase 34, Phase 35
**Requirements**: VER-01, VER-02
**Success Criteria** (what must be TRUE):
  1. All previously xfail tests for ARR-FIX and CMP-FIX bugs are converted to normal passing tests (xfail markers removed)
  2. Full test suite (`pytest`) passes with zero failures and zero unexpected failures
  3. No previously passing tests have regressed to failing
**Plans**: TBD

Plans:
- [ ] 36-01: Convert xfail tests to passing and run full regression suite

## Progress

**Execution Order:** 34 -> 35 -> 36 (34 and 35 are independent; 36 depends on both)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 34. Array Fixes | v1.6 | 1/1 | Complete | 2026-02-01 |
| 35. Comparison Bug Fixes | v1.6 | 0/2 | Not started | - |
| 36. Verification & Regression | v1.6 | 0/1 | Not started | - |

---
*Roadmap created: 2026-02-01 for v1.6 Array & Comparison Fixes*
