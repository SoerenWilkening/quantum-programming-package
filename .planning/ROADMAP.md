# Milestone v1.7: Bug Fixes & Array Optimization

**Status:** 🚧 IN PROGRESS
**Phases:** 37-41
**Total Plans:** TBD

## Overview

v1.7 addresses three deferred bugs from v1.5/v1.6 verification (division overflow, modular reduction corruption, controlled multiplication corruption) and optimizes array element-wise operations with classical values to use direct CQ_* calls instead of allocating temporary qint objects. Each bug gets focused investigation and fixing, followed by array optimization, and final comprehensive verification to ensure all xfail markers are removed and no regressions occur.

## Phases

### Phase 37: Division Overflow Fix

**Goal**: Division produces correct results for all operand combinations including when divisor >= 2^(w-1)
**Depends on**: Nothing (first phase in v1.7)
**Requirements**: FIX-01
**Success Criteria** (what must be TRUE):
  1. User can divide qint(15, width=4) / qint(9, width=4) and get correct result (1)
  2. User can divide qint(7, width=4) / qint(8, width=4) and get correct result (0)
  3. Division operations with divisor >= 2^(w-1) produce mathematically correct quotients
  4. All previously-xfail division tests pass without xfail markers
**Plans**: 1 plan

Plans:
- [x] 37-01-PLAN.md — Fix division loop bounds and remove xfail markers

### Phase 38: Modular Reduction Fix

**Goal**: _reduce_mod produces correct reduced values without corrupting result register
**Depends on**: Nothing (independent of division bug; modular reduction code is separate)
**Requirements**: FIX-02
**Success Criteria** (what must be TRUE):
  1. User can compute (a * b) mod N and get correct reduced result
  2. _reduce_mod preserves result register integrity across all test cases
  3. Modular arithmetic operations produce correct values for all reasonable inputs
  4. All previously-xfail modular reduction tests pass without xfail markers
**Plans**: 1 plan

Plans:
- [ ] 38-01-PLAN.md — Fix _reduce_mod with Beauregard-style subtract-check-sign, remove xfail markers

### Phase 39: Controlled Multiplication Fix

**Goal**: Controlled multiplication preserves result register integrity and produces correct conditional products
**Depends on**: Nothing (independent of division and modular reduction)
**Requirements**: FIX-03
**Success Criteria** (what must be TRUE):
  1. User can execute conditional multiplication in quantum if-block without result corruption
  2. Result register contains correct product when condition is True
  3. Result register is unchanged when condition is False
  4. All previously-xfail controlled multiplication tests pass without xfail markers
**Plans**: TBD

Plans:
- [ ] 39-01: TBD

### Phase 40: Array Classical Optimization

**Goal**: Array element-wise operations with classical values use direct CQ_* calls instead of creating temporary qint objects
**Depends on**: Nothing (independent optimization; does not depend on bug fixes)
**Requirements**: OPT-01, OPT-02
**Success Criteria** (what must be TRUE):
  1. Array + int uses CQ_add directly without allocating temporary qint
  2. Array & int uses CQ_and directly without allocating temporary qint
  3. All element-wise arithmetic ops (add, sub, mul) with classical values optimized
  4. All element-wise bitwise ops (and, or, xor) with classical values optimized
  5. Existing array tests pass with no behavioral changes (optimization only)
**Plans**: 1 plan

Plans:
- [ ] 40-01-PLAN.md — Remove temporary qint allocation for classical operands in array in-place operations

### Phase 41: Verification & Regression

**Goal**: All v1.7 bug fixes verified passing and no existing tests regress
**Depends on**: Phase 37, Phase 38, Phase 39, Phase 40
**Requirements**: None (verification phase)
**Success Criteria** (what must be TRUE):
  1. All BUG-DIV-01 xfail markers removed from test suite
  2. All BUG-MOD-REDUCE xfail markers removed from test suite
  3. All BUG-COND-MUL-01 xfail markers removed from test suite
  4. Full regression suite passes with zero unexpected failures
  5. xpass count = 0 (no unexpected passes)
**Plans**: TBD

Plans:
- [ ] 41-01: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 37. Division Overflow Fix | 1/1 | ✓ Complete | 2026-02-02 |
| 38. Modular Reduction Fix | 0/TBD | Not started | - |
| 39. Controlled Multiplication Fix | 0/TBD | Not started | - |
| 40. Array Classical Optimization | 0/TBD | Not started | - |
| 41. Verification & Regression | 0/TBD | Not started | - |

---

_For current project status, see .planning/STATE.md_
