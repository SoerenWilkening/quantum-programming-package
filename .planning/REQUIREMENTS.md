# Requirements: Quantum Assembly v2.1

**Defined:** 2026-02-04
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v2.1 Requirements

### Inverse Qubit Reuse

- [ ] **INV-01**: Compiled function tracks all qubits allocated during execution as ancillas (including `ql.qint()`)
- [ ] **INV-02**: `f(x).inverse()` uncomputes ancillas from that specific forward call (return value carries compiled-origin metadata)
- [ ] **INV-03**: `f.inverse(x)` targets ancillas from a prior `f(x)` call with matching inputs
- [ ] **INV-04**: Inverse runs adjoint gates on original ancillas, uncomputing them to |0⟩
- [ ] **INV-05**: Ancilla qubits are deallocated after inverse completes (returned to allocator)
- [ ] **INV-06**: Inverse works when called at any point after forward call (not just immediately after)
- [ ] **INV-07**: When qubit-saving is active and function returns a qint, auto-uncompute all ancillas except the return value's qubits after forward call

### qarray Support in @ql.compile

- [ ] **ARR-01**: `ql.qarray` can be passed as argument to `@ql.compile`-decorated functions
- [ ] **ARR-02**: Capture phase correctly extracts qubit indices from qarray elements
- [ ] **ARR-03**: Replay phase correctly remaps qarray element qubits to virtual namespace
- [ ] **ARR-04**: Cache key incorporates qarray shape and element widths

## Future Requirements

### Deferred Compilation Features

- **PAR-01**: Parametric compilation (compile once for all classical values)
- **PAR-02**: Parametric replay with classical value substitution
- **ADV-01**: Resource estimation for compiled functions
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition

## Out of Scope

| Feature | Reason |
|---------|--------|
| Parametric compilation | Separate milestone, different mechanism |
| qarray return from compiled functions | Not requested, adds complexity |
| Nested inverse qubit reuse | Single-level inverse sufficient for now |
| Automatic qubit-saving without `ql.option` | Explicit opt-in preserves backward compatibility |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INV-01 | Phase 52 | Pending |
| INV-02 | Phase 52 | Pending |
| INV-03 | Phase 52 | Pending |
| INV-04 | Phase 52 | Pending |
| INV-05 | Phase 52 | Pending |
| INV-06 | Phase 52 | Pending |
| INV-07 | Phase 53 | Pending |
| ARR-01 | Phase 54 | Pending |
| ARR-02 | Phase 54 | Pending |
| ARR-03 | Phase 54 | Pending |
| ARR-04 | Phase 54 | Pending |

**Coverage:**
- v2.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after roadmap creation*
