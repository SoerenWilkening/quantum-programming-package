# Requirements: Quantum Assembly v3.0 — Fault-Tolerant Arithmetic

**Defined:** 2026-02-14
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v3.0 Requirements

Requirements for Toffoli-based fault-tolerant arithmetic. Each maps to roadmap phases.

### Toffoli Addition

- [ ] **ADD-01**: Ripple-carry adder (QQ) adds two quantum registers using only Toffoli/CNOT/X gates with 1 ancilla qubit
- [ ] **ADD-02**: Ripple-carry adder (CQ) adds a classical value to a quantum register using only Toffoli/CNOT/X gates
- [ ] **ADD-03**: Controlled ripple-carry adder (cQQ) performs QQ addition conditioned on a control qubit
- [ ] **ADD-04**: Controlled ripple-carry adder (cCQ) performs CQ addition conditioned on a control qubit
- [ ] **ADD-05**: Subtraction works via inverse of Toffoli adder (reversed gate sequence) for all 4 variants
- [ ] **ADD-06**: Carry look-ahead adder (QQ) achieves O(log n) depth using 2n-2 ancilla qubits (Draper et al. 2004)
- [ ] **ADD-07**: Mixed-width Toffoli addition handles operands of different bit widths via zero-extension

### Toffoli Multiplication

- [ ] **MUL-01**: Schoolbook multiplication (QQ) computes quantum*quantum product using Toffoli-based adders (Litinski 2024)
- [ ] **MUL-02**: Classical-quantum multiplication (CQ) computes quantum*classical using shift-and-add with Toffoli adders
- [ ] **MUL-03**: Controlled multiplication (cQQ) performs QQ multiply conditioned on a control qubit
- [ ] **MUL-04**: Controlled multiplication (cCQ) performs CQ multiply conditioned on a control qubit
- [ ] **MUL-05**: Controlled add-subtract optimization reduces Toffoli count by ~50% in multiplication subroutine

### Toffoli Division

- [ ] **DIV-01**: Restoring division with classical divisor computes quotient and remainder using Toffoli add/sub
- [ ] **DIV-02**: Restoring division with quantum divisor computes quotient and remainder using Toffoli add/sub

### Backend Dispatch

- [ ] **DSP-01**: `ql.option('fault_tolerant', True)` switches all arithmetic operations to Toffoli-based implementations
- [ ] **DSP-02**: Hot-path C functions dispatch to Toffoli or QFT sequence generators based on fault_tolerant flag
- [ ] **DSP-03**: Toffoli-based arithmetic is the default; QFT arithmetic remains available via `ql.option('fault_tolerant', False)`

### Infrastructure

- [ ] **INF-01**: Ancilla qubits are allocated, used, and returned to |0> state (uncomputed) correctly for all Toffoli operations
- [ ] **INF-02**: Verification suite confirms Toffoli and QFT backends produce identical results for widths 1-8 across all operations
- [ ] **INF-03**: Hardcoded Toffoli gate sequences for common widths eliminate generation overhead
- [ ] **INF-04**: T-count reporting in circuit statistics (each Toffoli = 7 T gates)

## Future Requirements

Deferred beyond v3.0. Tracked but not in current roadmap.

### Advanced Toffoli Optimization

- **OPT-01**: Automatic depth/ancilla tradeoff selects ripple-carry vs CLA based on register width
- **OPT-02**: Karatsuba multiplication for widths > 64 (asymptotically better but worse for practical sizes)

### Fault-Tolerant Extensions

- **FTE-01**: Full error correction code integration (surface code, Steane code)
- **FTE-02**: Modular arithmetic via Toffoli gates (for Shor's algorithm)
- **FTE-03**: Non-restoring division (marginal T-count improvement, more complex)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Karatsuba/Toom-Cook multiplication | Worse for practical sizes n <= 64 (Litinski 2024 confirms schoolbook wins) |
| Non-restoring division | Marginal ~15% T-count improvement, significantly more complex circuit design |
| QFT-Toffoli hybrid circuits | Mixing backends adds complexity without clear benefit |
| Measurement-based uncomputation | Requires mid-circuit measurement support not in current framework |
| Floating-point Toffoli arithmetic | Out of scope for integer arithmetic framework |
| Full error correction integration | v3.0 provides fault-tolerant gate set; EC integration is a separate milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ADD-01 | Phase 66 | Pending |
| ADD-02 | Phase 66 | Pending |
| ADD-03 | Phase 67 | Pending |
| ADD-04 | Phase 67 | Pending |
| ADD-05 | Phase 66 | Pending |
| ADD-06 | Phase 71 | Pending |
| ADD-07 | Phase 66 | Pending |
| MUL-01 | Phase 68 | Pending |
| MUL-02 | Phase 68 | Pending |
| MUL-03 | Phase 69 | Pending |
| MUL-04 | Phase 69 | Pending |
| MUL-05 | Phase 72 | Pending |
| DIV-01 | Phase 69 | Pending |
| DIV-02 | Phase 69 | Pending |
| DSP-01 | Phase 67 | Pending |
| DSP-02 | Phase 67 | Pending |
| DSP-03 | Phase 67 | Pending |
| INF-01 | Phase 65 | Pending |
| INF-02 | Phase 70 | Pending |
| INF-03 | Phase 72 | Pending |
| INF-04 | Phase 72 | Pending |

**Coverage:**
- v3.0 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-02-14*
*Last updated: 2026-02-14 after roadmap creation (all 21 requirements mapped to phases 65-72)*
