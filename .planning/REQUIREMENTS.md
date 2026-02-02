# Requirements: Quantum Assembly v1.6

**Defined:** 2026-02-01
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.6 Requirements

Requirements for Array & Comparison Fixes milestone. Each maps to roadmap phases.

### Array Fixes

- [x] **ARR-FIX-01**: Array constructor initializes elements with correct value AND width (`qint(value, width=self._width)` instead of `qint(self._width)`)
- [x] **ARR-FIX-02**: Array elements have correct qubit count matching specified width (e.g., `width=3` allocates 3 qubits per element)
- [x] **ARR-FIX-03**: In-place element-wise operations (`+=`, `-=`) produce correct circuits when element widths match `self._width`
- [x] **ARR-FIX-04**: Non-in-place element-wise operations (`+`, `-`) produce correct circuits
- [x] **ARR-FIX-05**: All previously xfail array verification tests pass after fixes

### Comparison Fixes

- [x] **CMP-FIX-01**: eq/ne comparisons return correct (non-inverted) results for all value pairs (BUG-CMP-01, 488 xfail tests)
- [x] **CMP-FIX-02**: Ordering comparisons produce correct results at MSB boundary values (BUG-CMP-02)
- [x] **CMP-FIX-03**: gt/le operations produce reasonable circuit sizes at widths >= 6 (BUG-CMP-03)

### Verification

- [x] **VER-01**: All previously xfail tests for fixed bugs convert to passing
- [x] **VER-02**: No regressions in existing passing tests

## Future Requirements

Deferred to later milestones.

### Division & Modular Fixes

- **DIV-FIX-01**: Division comparison overflow fixed for divisor >= 2^(w-1) (BUG-DIV-01)
- **MOD-FIX-01**: _reduce_mod result corruption fixed (BUG-MOD-REDUCE)

### Conditional Operation Fixes

- **COND-FIX-01**: Controlled multiplication no longer corrupts result register (BUG-COND-MUL-01)

## Out of Scope

| Feature | Reason |
|---------|--------|
| New array features | Bug fixes only; new features deferred |
| Division/modular fixes | Separate milestone — different C backend area |
| Controlled multiplication fix | Separate milestone — different C backend area |
| Performance optimization | Focus on correctness first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARR-FIX-01 | Phase 34 | Complete |
| ARR-FIX-02 | Phase 34 | Complete |
| ARR-FIX-03 | Phase 34 | Complete |
| ARR-FIX-04 | Phase 34 | Complete |
| ARR-FIX-05 | Phase 34 | Complete |
| CMP-FIX-01 | Phase 35 | Complete |
| CMP-FIX-02 | Phase 35 | Complete |
| CMP-FIX-03 | Phase 35 | Complete |
| VER-01 | Phase 36 | Complete |
| VER-02 | Phase 36 | Complete |

**Coverage:**
- v1.6 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after Phase 36 completion*
