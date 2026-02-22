# Requirements: Quantum Assembly v4.0 Grover's Algorithm

**Defined:** 2026-02-19
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v4.0 Requirements

Requirements for Grover's Algorithm milestone. Each maps to roadmap phases.

### Quantum Primitives

- [x] **PRIM-01**: User can apply Ry rotation via `qint.branch(theta)` method on all qubits
- [x] **PRIM-02**: User can apply Ry rotation via `qbool.branch(theta)` method
- [x] **PRIM-03**: `branch(pi/2)` creates equal superposition (Hadamard-equivalent)

### Oracle Infrastructure

- [x] **ORCL-01**: User can pass `@ql.compile` decorated function as oracle to Grover
- [x] **ORCL-02**: `@ql.grover_oracle` decorator enforces compute-phase-uncompute ordering
- [x] **ORCL-03**: Oracle decorator validates ancilla allocation delta is zero on exit
- [x] **ORCL-04**: Bit-flip oracles auto-wrapped with phase kickback pattern
- [x] **ORCL-05**: Oracle cache key includes `arithmetic_mode` (QFT vs Toffoli)

### Grover Search

- [x] **GROV-01**: `ql.grover(oracle, search_space)` API executes search and returns measured value
- [x] **GROV-02**: Automatic iteration count calculated from search space size N and solution count M
- [x] **GROV-03**: Diffusion operator uses X-MCZ-X pattern (zero ancilla, O(n) gates)
- [x] **GROV-04**: Multiple solutions supported (iteration formula accounts for M > 1)
- [x] **GROV-05**: User can manually construct S_0 reflection via `with a == 0` for custom amplitude amplification

### Oracle Auto-Synthesis

- [x] **SYNTH-01**: User can pass Python predicate lambda as oracle (`ql.grover(lambda x: x > 5, x)`)
- [x] **SYNTH-02**: Compound predicates compile to valid oracles (`(x > 10) & (x < 50)`)
- [x] **SYNTH-03**: Predicate oracles work with existing qint comparison operators

### Adaptive Search

- [ ] **ADAPT-01**: When M is unknown, Grover uses exponential backoff strategy
- [ ] **ADAPT-02**: Adaptive search terminates when solution found or search space exhausted

### Amplitude Estimation

- [ ] **AMP-01**: `ql.amplitude_estimate(oracle, register)` returns estimated probability
- [ ] **AMP-02**: Uses Iterative QAE (IQAE) variant -- no QFT circuit required
- [ ] **AMP-03**: User can specify precision (epsilon) and confidence level

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Search

- **ADV-01**: Quantum counting (`ql.count_solutions`) for exact M estimation
- **ADV-02**: Fixed-point amplitude amplification for non-standard amplification profiles
- **ADV-03**: Custom state preparation (non-uniform initial superposition)

### Specialized Oracles

- **SPEC-01**: SAT/3-SAT oracle auto-generation from CNF formulas
- **SPEC-02**: Database search oracle from classical data structure

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Full QPE-based amplitude estimation | IQAE provides same capability with lower depth |
| Grover with error correction | Requires QEC milestone first |
| Variational quantum search | Different algorithm family, separate milestone |
| Interactive oracle debugging | Complex infrastructure, defer to tooling milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRIM-01 | Phase 76 | Complete |
| PRIM-02 | Phase 76 | Complete |
| PRIM-03 | Phase 76 | Complete |
| ORCL-01 | Phase 77 | Complete |
| ORCL-02 | Phase 77 | Complete |
| ORCL-03 | Phase 77 | Complete |
| ORCL-04 | Phase 77 | Complete |
| ORCL-05 | Phase 77 | Complete |
| GROV-01 | Phase 79 | Complete |
| GROV-02 | Phase 79 | Complete |
| GROV-03 | Phase 78 | Complete |
| GROV-04 | Phase 79 | Complete |
| GROV-05 | Phase 78 | Complete |
| SYNTH-01 | Phase 80 | Complete |
| SYNTH-02 | Phase 80 | Complete |
| SYNTH-03 | Phase 80 | Complete |
| ADAPT-01 | Phase 80 | Pending |
| ADAPT-02 | Phase 80 | Pending |
| AMP-01 | Phase 81 | Pending |
| AMP-02 | Phase 81 | Pending |
| AMP-03 | Phase 81 | Pending |

**Coverage:**
- v4.0 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after roadmap creation*
