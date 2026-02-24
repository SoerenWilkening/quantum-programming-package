# Requirements: Quantum Assembly v5.0

**Defined:** 2026-02-24
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v5.0 Requirements

Requirements for v5.0 Advanced Arithmetic & Compilation. Each maps to roadmap phases.

### Bug Fixes

- [ ] **FIX-01**: Division correctly uncomputes MSB comparison temporaries (BUG-DIV-02)
- [ ] **FIX-02**: QFT division/modulo produces correct results for all tested widths (BUG-QFT-DIV)
- [ ] **FIX-03**: Modular reduction produces correct (a+b) mod N without orphan qubits (BUG-MOD-REDUCE)
- [ ] **FIX-04**: Compile cache key includes arithmetic_mode, cla_override, and tradeoff_policy

### Modular Toffoli Arithmetic

- [ ] **MOD-01**: User can compute (a + b) mod N using Toffoli gates via qint_mod addition
- [ ] **MOD-02**: User can compute (a - b) mod N using Toffoli gates via qint_mod subtraction
- [ ] **MOD-03**: User can compute controlled (a + b) mod N inside a with block
- [ ] **MOD-04**: User can compute (a * c) mod N (c classical) using Toffoli gates via qint_mod multiplication
- [ ] **MOD-05**: Modular operations verified exhaustively for widths 2-4 (statevector) and 5-8 (MPS)

### Quantum Counting

- [ ] **CNT-01**: User can call ql.count_solutions(oracle, width=n) to get integer solution count M
- [ ] **CNT-02**: CountResult includes .count, .estimate, .count_interval, .search_space, .num_oracle_calls
- [ ] **CNT-03**: Quantum counting verified against known-M oracles (M=1,2,3)

### Depth/Ancilla Tradeoff

- [ ] **TRD-01**: User can set ql.option('tradeoff', 'auto'|'min_depth'|'min_qubits') to control adder selection
- [ ] **TRD-02**: Auto mode selects CLA for width >= threshold, CDKM otherwise
- [ ] **TRD-03**: Modular arithmetic primitives force RCA regardless of tradeoff policy
- [ ] **TRD-04**: CLA subtraction limitation documented clearly

### Parametric Compilation

- [ ] **PAR-01**: User can decorate with @ql.compile(parametric=True) to enable parametric mode
- [ ] **PAR-02**: Parametric functions replay with different classical values without re-capture
- [ ] **PAR-03**: Toffoli CQ operations fall back to per-value caching with documentation
- [ ] **PAR-04**: Oracle decorator forces per-value caching for structural parameters

## Future Requirements

Deferred to v6+. Tracked but not in current roadmap.

### Modular Arithmetic Extensions

- **MEXT-01**: Modular exponentiation via repeated squaring with controlled modular multiply
- **MEXT-02**: Full Shor's algorithm API (`ql.factor(N)`) with QPE and classical post-processing
- **MEXT-03**: QFT-based modular arithmetic (Beauregard coset representation)

### Grover Extensions

- **GADV-02**: Fixed-point amplitude amplification
- **GADV-03**: Custom state preparation (non-uniform initial superposition)
- **GSPEC-01**: SAT/3-SAT oracle auto-generation from CNF formulas
- **GSPEC-02**: Database search oracle from classical data structure

### Compilation Extensions

- **ADV-01**: Resource estimation for compiled functions
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition

### Performance Extensions

- **ADV-OPT-01**: Hardcoded sequences for multiplication
- **ADV-OPT-03**: SIMD vectorization for bulk gate operations
- **ADV-OPT-04**: Multi-threaded circuit building

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Modular exponentiation | Circuit sizes exceed 17-qubit simulator limit; provide building blocks instead |
| Full Shor's API (`ql.factor(N)`) | Untestable on simulator; QPE wrapper and continued fractions out of scope |
| QFT-based modular arithmetic | Defeats fault-tolerant purpose; BUG-QFT-DIV makes QFT path unreliable |
| Auto Clifford+T inside mod-add | 15x gate explosion; decomposition already available as post-processing |
| Dynamic parametric recompilation | Violates compile-then-execute model; parameters must be classical |
| Per-operation adder selection | Minimal benefit over global selection; adds unnecessary complexity |
| Kogge-Stone CLA implementation | BK CLA sufficient; KS stubs remain placeholder |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | — | Pending |
| FIX-02 | — | Pending |
| FIX-03 | — | Pending |
| FIX-04 | — | Pending |
| MOD-01 | — | Pending |
| MOD-02 | — | Pending |
| MOD-03 | — | Pending |
| MOD-04 | — | Pending |
| MOD-05 | — | Pending |
| CNT-01 | — | Pending |
| CNT-02 | — | Pending |
| CNT-03 | — | Pending |
| TRD-01 | — | Pending |
| TRD-02 | — | Pending |
| TRD-03 | — | Pending |
| TRD-04 | — | Pending |
| PAR-01 | — | Pending |
| PAR-02 | — | Pending |
| PAR-03 | — | Pending |
| PAR-04 | — | Pending |

**Coverage:**
- v5.0 requirements: 20 total
- Mapped to phases: 0
- Unmapped: 20

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after initial definition*
