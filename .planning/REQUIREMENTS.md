# Requirements: Quantum Assembly v2.0

**Defined:** 2026-02-04
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v2.0 Requirements

Requirements for the function compilation milestone. Each maps to roadmap phases.

### Capture & Replay

- [ ] **CAP-01**: `@ql.compile` decorator captures all gate sequences within a decorated function on first call
- [ ] **CAP-02**: Captured gates are stored with virtual qubit references (not absolute indices)
- [ ] **CAP-03**: Subsequent calls replay cached gates with virtual-to-real qubit remapping
- [ ] **CAP-04**: Cache key includes function identity, argument widths, and classical argument values
- [ ] **CAP-05**: Cache is cleared when a new `ql.circuit()` is created
- [ ] **CAP-06**: Return values (qint/qbool) from compiled functions are usable in further quantum operations

### Optimization

- [ ] **OPT-01**: Captured gate range is optimized via `circuit_optimize()` before caching
- [ ] **OPT-02**: Optimized sequence replaces the individual operation sequences on replay

### Controlled Execution

- [ ] **CTL-01**: Compiled functions work inside `with` blocks (controlled execution)
- [ ] **CTL-02**: Controlled context triggers re-capture (not post-hoc control addition)
- [ ] **CTL-03**: Cache key includes controlled state to avoid incorrect replay

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

- [ ] **INF-01**: Two new Cython helper functions for gate extraction and remapped injection
- [ ] **INF-02**: Global state snapshot/restore during tracing to prevent state pollution
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
| CAP-01 | TBD | Pending |
| CAP-02 | TBD | Pending |
| CAP-03 | TBD | Pending |
| CAP-04 | TBD | Pending |
| CAP-05 | TBD | Pending |
| CAP-06 | TBD | Pending |
| OPT-01 | TBD | Pending |
| OPT-02 | TBD | Pending |
| CTL-01 | TBD | Pending |
| CTL-02 | TBD | Pending |
| CTL-03 | TBD | Pending |
| INV-01 | TBD | Pending |
| INV-02 | TBD | Pending |
| DBG-01 | TBD | Pending |
| DBG-02 | TBD | Pending |
| NST-01 | TBD | Pending |
| NST-02 | TBD | Pending |
| INF-01 | TBD | Pending |
| INF-02 | TBD | Pending |
| INF-03 | TBD | Pending |

**Coverage:**
- v2.0 requirements: 20 total
- Mapped to phases: 0
- Unmapped: 20 ⚠️

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after initial definition*
