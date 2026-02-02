# Requirements: Quantum Assembly v1.7

**Defined:** 2026-02-02
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.7 Requirements

### Bug Fixes

- [x] **FIX-01**: Division produces correct results when divisor >= 2^(w-1) (BUG-DIV-01)
- [ ] **FIX-02**: _reduce_mod produces correct reduced values without result corruption (BUG-MOD-REDUCE)
- [ ] **FIX-03**: Controlled multiplication preserves result register integrity (BUG-COND-MUL-01)

### Array Classical Optimization

- [x] **OPT-01**: Array element-wise arithmetic with classical values (int/list) uses CQ_add/CQ_sub/CQ_mul directly instead of creating temporary qint objects
- [x] **OPT-02**: Array element-wise bitwise ops with classical values (int/list) uses CQ_and/CQ_or/CQ_xor directly instead of creating temporary qint objects

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
| FIX-01 | Phase 37 | Complete |
| FIX-02 | Phase 38 | Pending |
| FIX-03 | Phase 39 | Pending |
| OPT-01 | Phase 40 | Complete |
| OPT-02 | Phase 40 | Complete |

**Coverage:**
- v1.7 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-02*
*Last updated: 2026-02-02 after roadmap creation*
