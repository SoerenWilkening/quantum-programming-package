# Requirements: Quantum Assembly

**Defined:** 2026-02-08
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v2.3 Requirements

Requirements for v2.3 Hardcoding Right-Sizing. Each maps to roadmap phases.

### Benchmarking

- [ ] **BENCH-01**: Benchmark measures package import time (`import quantum_language`) with and without hardcoded sequences
- [ ] **BENCH-02**: Benchmark measures first-call generation cost for each operation type (QQ_add, CQ_add, cQQ_add, cCQ_add, QQ_mul, CQ_mul, Q_xor, Q_and, Q_or) at widths 1-16
- [ ] **BENCH-03**: Benchmark measures per-call dispatch overhead for cached sequences (hardcoded lookup vs dynamic cache hit)
- [ ] **BENCH-04**: Benchmark produces comparison report: hardcoded vs dynamic per operation/width with import time amortization analysis

### Addition Right-Sizing

- [ ] **ADD-01**: Data-driven decision on which addition widths to keep hardcoded (may be all, some, or none)
- [ ] **ADD-02**: If keeping hardcoded sequences, factor out shared QFT/IQFT sub-sequences to reduce file size
- [ ] **ADD-03**: If reverting to dynamic, remove hardcoded sequence files and update build system
- [ ] **ADD-04**: Verify no performance regression in end-to-end circuit generation after changes

### Other Operations Evaluation

- [ ] **EVAL-01**: Multiplication generation cost measured and documented with hardcoding recommendation
- [ ] **EVAL-02**: Bitwise operation generation cost measured and documented with hardcoding recommendation
- [ ] **EVAL-03**: Division generation cost measured and documented with hardcoding recommendation

## Future Requirements

### Hardcoding Implementation (pending v2.3 evaluation)

- **HC-MUL-01**: Implement multiplication hardcoding if EVAL-01 recommends it
- **HC-BIT-01**: Implement bitwise hardcoding if EVAL-02 recommends it

## Out of Scope

| Feature | Reason |
|---------|--------|
| Actually hardcoding mul/bitwise/div | This milestone only evaluates; implementation deferred to future based on data |
| Widths > 16 hardcoding | Diminishing returns, file sizes too large |
| SIMD vectorization | Separate optimization concern (ADV-OPT-03) |
| Multi-threaded circuit building | Separate optimization concern (ADV-OPT-04) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BENCH-01 | — | Pending |
| BENCH-02 | — | Pending |
| BENCH-03 | — | Pending |
| BENCH-04 | — | Pending |
| ADD-01 | — | Pending |
| ADD-02 | — | Pending |
| ADD-03 | — | Pending |
| ADD-04 | — | Pending |
| EVAL-01 | — | Pending |
| EVAL-02 | — | Pending |
| EVAL-03 | — | Pending |

**Coverage:**
- v2.3 requirements: 11 total
- Mapped to phases: 0
- Unmapped: 11 ⚠️

---
*Requirements defined: 2026-02-08*
*Last updated: 2026-02-08 after initial definition*
