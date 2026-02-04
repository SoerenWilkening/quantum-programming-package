# Requirements: Quantum Assembly v2.0

**Defined:** 2026-02-04
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v2.0 Requirements

Requirements for the function compilation milestone. Each maps to roadmap phases.

### Capture & Replay

- [x] **CAP-01**: `@ql.compile` decorator captures all gate sequences within a decorated function on first call
- [x] **CAP-02**: Captured gates are stored with virtual qubit references (not absolute indices)
- [x] **CAP-03**: Subsequent calls replay cached gates with virtual-to-real qubit remapping
- [x] **CAP-04**: Cache key includes function identity, argument widths, and classical argument values
- [x] **CAP-05**: Cache is cleared when a new `ql.circuit()` is created
- [x] **CAP-06**: Return values (qint/qbool) from compiled functions are usable in further quantum operations

### Optimization

- [x] **OPT-01**: Captured gate range is optimized via `_optimize_gate_list()` before caching
- [x] **OPT-02**: Optimized sequence replaces the individual operation sequences on replay

### Controlled Execution

- [x] **CTL-01**: Compiled functions work inside `with` blocks (controlled execution)
- [x] **CTL-02**: Controlled context triggers re-capture (not post-hoc control addition)
- [x] **CTL-03**: Cache key includes controlled state to avoid incorrect replay

### Inverse Generation

- [ ] **INV-01**: Compiled functions support `.inverse()` to generate adjoint of the compiled sequence
- [ ] **INV-02**: Inverse reverses gate order and applies adjoint transformation to each gate

### Debug Mode

- [ ] **DBG-01**: Debug mode shows original operations alongside optimized gate count
- [ ] **DBG-02**: Debug mode reports cache hits/misses

### Nested Compilation

- [ ] **NST-01**: A compiled function can call another compiled function
- [ ] **NST-02**: Inner compiled function's replayed gates become part of outer function's capture

### Infrastructure

- [x] **INF-01**: Two new Cython helper functions for gate extraction and remapped injection
- [x] **INF-02**: Global state snapshot/restore during tracing to prevent state pollution
- [ ] **INF-03**: Comprehensive test suite covering all compilation scenarios

## Future Requirements

Deferred to v2.1+. Tracked but not in current roadmap.

### Parametric Compilation

- **PAR-01**: True parametric compilation (compile once for all classical values) via C-level gate structure changes
- **PAR-02**: Symbolic classical parameters in compiled sequences

### Advanced Features

- **ADV-01**: Resource estimation for compiled functions (qubit count, gate count, depth)
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition (chain multiple compiled functions)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Abstract tracing (JAX-style) | Incompatible with Cython layer, would require rewriting ~50 operator methods |
| Bytecode manipulation (PyTorch Dynamo-style) | CPython-specific, fragile, massive complexity |
| Autodiff integration | Different product entirely, no quantum gradient infrastructure |
| Automatic parallelization | Optimizer already handles gate parallelization |
| JIT compilation to native code | Out of scope for circuit-building framework |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAP-01 | Phase 48 | Complete |
| CAP-02 | Phase 48 | Complete |
| CAP-03 | Phase 48 | Complete |
| CAP-04 | Phase 48 | Complete |
| CAP-05 | Phase 48 | Complete |
| CAP-06 | Phase 48 | Complete |
| OPT-01 | Phase 49 | Complete |
| OPT-02 | Phase 49 | Complete |
| CTL-01 | Phase 50 | Complete |
| CTL-02 | Phase 50 | Complete |
| CTL-03 | Phase 50 | Complete |
| INV-01 | Phase 51 | Pending |
| INV-02 | Phase 51 | Pending |
| DBG-01 | Phase 51 | Pending |
| DBG-02 | Phase 51 | Pending |
| NST-01 | Phase 51 | Pending |
| NST-02 | Phase 51 | Pending |
| INF-01 | Phase 48 | Complete |
| INF-02 | Phase 48 | Complete |
| INF-03 | Phase 51 | Pending |

**Coverage:**
- v2.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after roadmap creation*
