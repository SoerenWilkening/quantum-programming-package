# Requirements: Quantum Assembly

**Defined:** 2026-01-30
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.4 Requirements

Requirements for OpenQASM Export & Verification milestone. Each maps to roadmap phases.

### C Backend Export (EXP)

- [x] **EXP-01**: New `circuit_to_qasm_string()` C function returning malloc'd OpenQASM 3.0 string buffer
- [x] **EXP-02**: Export all single-qubit gates: X, Y, Z, H (lowercase OpenQASM syntax)
- [x] **EXP-03**: Export all rotation gates: P(θ), Rx(θ), Ry(θ), Rz(θ) with `%.17g` angle precision
- [x] **EXP-04**: Multi-controlled gate export: `cx` (1 ctrl), `ccx` (2 ctrl), `ctrl(n) @ gate` (>2 ctrl)
- [x] **EXP-05**: `large_control` array support for gates with >2 control qubits
- [x] **EXP-06**: Measurement export with classical register: `bit[n] c;` + `c[i] = measure q[i];`
- [x] **EXP-07**: Error handling: NULL circuit check, malloc failure returns NULL
- [x] **EXP-08**: Fix existing `circuit_to_opanqasm()`: add fclose, fix gate no-ops, fix measurement syntax

### Python API (API)

- [x] **API-01**: Cython `to_openqasm()` method with memory-safe C buffer cleanup (try/finally + free)
- [x] **API-02**: Module-level `ql.to_openqasm()` convenience function returning QASM string
- [x] **API-03**: Add `extras_require` for optional Qiskit verification dependencies

### Verification Script (VER)

- [x] **VER-01**: Standalone `scripts/verify_circuit.py` with Qiskit integration (qasm3.loads + AerSimulator)
- [x] **VER-02**: Built-in arithmetic test cases: addition, subtraction, multiplication with overflow
- [x] **VER-03**: Built-in comparison test cases: <, <=, ==, >=, >, !=
- [x] **VER-04**: Deterministic verification using 1 shot exact match for classical-init circuits
- [x] **VER-05**: Pass/fail reporting with summary output and non-zero exit code on failure
- [x] **VER-06**: Built-in bitwise test cases: AND, OR, XOR, NOT
- [x] **VER-07**: Detailed failure diagnostics: expected vs actual values, QASM snippet for failing test

## v1.3 Requirements (Complete)

Requirements for Package Structure & ql.array milestone. All complete.

### Package Structure (PKG)

- [x] **PKG-01**: Create proper Python package with `__init__.py` files
- [x] **PKG-02**: Split large Cython files to ~200-300 lines each
- [x] **PKG-03**: Maintain all existing functionality after restructuring
- [x] **PKG-04**: Update imports across codebase to use new package structure

### Array Class Core (ARR)

- [x] **ARR-01**: Create `ql.array` class for homogeneous quantum arrays
- [x] **ARR-02**: Support qint arrays (array of quantum integers)
- [x] **ARR-03**: Support qbool arrays (array of quantum booleans)
- [x] **ARR-04**: Initialize array from Python list or NumPy array with auto-width inference
- [x] **ARR-05**: Initialize array with explicit width parameter
- [x] **ARR-06**: Initialize array from dimensions with dtype
- [x] **ARR-07**: Support multi-dimensional arrays with arbitrary shapes
- [x] **ARR-08**: Validate homogeneity (reject mixed qint/qbool)

### Array Reductions (RED)

- [x] **RED-01**: AND reduction with pairwise tree for O(log n) depth
- [x] **RED-02**: OR reduction with pairwise tree for O(log n) depth
- [x] **RED-03**: XOR reduction with pairwise tree for O(log n) depth
- [x] **RED-04**: Sum reduction with pairwise tree for O(log n) depth

### Element-wise Operations (ELM)

- [x] **ELM-01**: Element-wise arithmetic between arrays
- [x] **ELM-02**: Element-wise bitwise between arrays
- [x] **ELM-03**: Element-wise comparison between arrays
- [x] **ELM-04**: Array shape validation for element-wise operations
- [x] **ELM-05**: In-place element-wise operations

### Python Integration (PYI)

- [x] **PYI-01**: `len(A)` returns total element count
- [x] **PYI-02**: Iteration support
- [x] **PYI-03**: NumPy-style indexing
- [x] **PYI-04**: NumPy-style slicing

## Future Requirements

Deferred to later milestones.

### Visualization & Debugging

- **VIS-01**: Debug visualization for uncomputation
- **VIS-02**: Qubit statistics tracking
- **VIS-03**: OpenQASM comment markers for uncomputation blocks

### Advanced Operations

- **ADV-01**: Bit shift operations for qint (<<, >>)

## Out of Scope

Explicitly excluded from v1.4.

| Feature | Reason |
|---------|--------|
| OpenQASM 2.0 export | Deprecated format, industry moved to 3.0 |
| Noise model simulation | Out of scope, use Qiskit Aer separately |
| Hardware backend execution | QASM export enables this separately |
| Statistical verification | Deterministic circuits don't need shots |
| Dynamic circuits (mid-circuit measurement, reset) | Not supported by framework |
| Custom gate definitions in QASM | Decompose to standard gates |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXP-01 | Phase 25 | Complete |
| EXP-02 | Phase 25 | Complete |
| EXP-03 | Phase 25 | Complete |
| EXP-04 | Phase 25 | Complete |
| EXP-05 | Phase 25 | Complete |
| EXP-06 | Phase 25 | Complete |
| EXP-07 | Phase 25 | Complete |
| EXP-08 | Phase 25 | Complete |
| API-01 | Phase 26 | Complete |
| API-02 | Phase 26 | Complete |
| API-03 | Phase 26 | Complete |
| VER-01 | Phase 27 | Complete |
| VER-02 | Phase 27 | Complete |
| VER-03 | Phase 27 | Complete |
| VER-04 | Phase 27 | Complete |
| VER-05 | Phase 27 | Complete |
| VER-06 | Phase 27 | Complete |
| VER-07 | Phase 27 | Complete |

**Coverage:**
- v1.4 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30*
