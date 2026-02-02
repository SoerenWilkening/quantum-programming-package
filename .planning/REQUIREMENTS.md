# Requirements: Quantum Assembly v1.7

**Defined:** 2026-02-02
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.7 Requirements

### Bug Fixes

- [ ] **FIX-01**: Division produces correct results when divisor >= 2^(w-1) (BUG-DIV-01)
- [ ] **FIX-02**: _reduce_mod produces correct reduced values without result corruption (BUG-MOD-REDUCE)
- [ ] **FIX-03**: Controlled multiplication preserves result register integrity (BUG-COND-MUL-01)

### Array Classical Optimization

- [ ] **OPT-01**: Array element-wise arithmetic with classical values (int/list) uses CQ_add/CQ_sub/CQ_mul directly instead of creating temporary qint objects
- [ ] **OPT-02**: Array element-wise bitwise ops with classical values (int/list) uses CQ_and/CQ_or/CQ_xor directly instead of creating temporary qint objects

## Future Requirements

None currently identified.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Classical optimization for single qint ops | qint arithmetic with int already uses CQ_ functions correctly |
| Array classical comparison optimization | Comparisons not included per user scope |
| qint(value) initialization change | X-gate init for single qint creation works correctly |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | — | Pending |
| FIX-02 | — | Pending |
| FIX-03 | — | Pending |
| OPT-01 | — | Pending |
| OPT-02 | — | Pending |

**Coverage:**
- v1.7 requirements: 5 total
- Mapped to phases: 0
- Unmapped: 5 ⚠️

---
*Requirements defined: 2026-02-02*
*Last updated: 2026-02-02 after initial definition*
