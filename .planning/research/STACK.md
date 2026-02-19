# Stack Research: Grover's Algorithm & Amplitude Estimation

**Domain:** Quantum search algorithms (Grover's algorithm, oracle compilation, amplitude estimation)
**Researched:** 2026-02-19
**Confidence:** HIGH

## Executive Summary

Grover's Algorithm implementation in Quantum Assembly requires **zero new external dependencies**. The existing framework provides all necessary building blocks:

1. **H gate** (Hadamard): Already implemented in `gate.h` as `h(gate_t*, qubit_t)`
2. **MCX gate** (Multi-controlled X): Already implemented as `mcx()` with arbitrary controls
3. **Conditional operations** (`with` statement): Working for single control via `qint.__enter__`/`__exit__`
4. **`@ql.compile` decorator**: Gate capture/replay with automatic controlled variant derivation
5. **Toffoli arithmetic**: Full suite working in fault-tolerant mode (`ql.option('fault_tolerant', True)`)

The implementation is fundamentally an **API/pattern layer** on top of existing capabilities, not a new technology stack. The main work is:
- Exposing H gates at Python level (currently C-only)
- Building diffusion operator pattern (H-X-MCZ-X-H)
- Creating oracle compilation utilities that transform classical functions to phase oracles
- Adding iteration count helpers (mathematical formulas)

For amplitude estimation, the framework supports both **circuit-based QAE** (Grover operator powers + phase estimation) and **iterative variants** (multiple independent circuit runs), with no additional dependencies beyond existing Qiskit verification infrastructure.

## New Dependencies: NONE

The existing stack is sufficient:

| Category | Current Stack | Used For Grover |
|----------|---------------|-----------------|
| Core | C backend + Cython + Python | All algorithm components |
| Gates | `h()`, `x()`, `z()`, `cx()`, `ccx()`, `mcx()` | Diffusion operator, oracles |
| Arithmetic | Toffoli-based `+=`, `-=`, `*`, etc. | Oracle predicates |
| Conditionals | `with flag:` controlled context | S_0 reflection via `with a == 0:` |
| Compilation | `@ql.compile` decorator | Oracle compilation |
| Verification | Qiskit (optional dependency) | Correctness verification |
| Export | OpenQASM 3.0 | Interoperability |

**No new pip packages, no new C libraries, no new build dependencies.**

## Recommended Stack: Leverage Existing Infrastructure

### Core Framework (Already Available)

| Component | Location | Purpose for Grover | Status |
|-----------|----------|-------------------|--------|
| `h()` gate function | `c_backend/src/gate.c` | Hadamard in diffusion operator | **EXISTS** - needs Python exposure |
| `mcx()` gate function | `c_backend/include/gate.h` | Multi-controlled Z in diffusion | **EXISTS** |
| `z()` gate function | `c_backend/src/gate.c` | Phase flip for marked states | **EXISTS** - needs Python exposure |
| `qint.__enter__/__exit__` | `src/quantum_language/qint.pyx` | S_0 via `with a == 0:` | **EXISTS** |
| `@ql.compile` | `src/quantum_language/compile.py` | Oracle capture/replay | **EXISTS** |
| `qarray` | `src/quantum_language/qarray.pyx` | Register manipulation | **EXISTS** |

### Gate Exposure (Minimal New Code)

The following gates need Python-level API exposure:

```python
# Proposed additions to quantum_language module
def hadamard(qbit):
    """Apply Hadamard gate to a qubit."""
    # Calls h() via Cython binding

def hadamard_all(register):
    """Apply Hadamard to all qubits in a qint/qarray."""
    # H^(otimes n) for uniform superposition

def phase_flip(qbit):
    """Apply Z gate (phase flip) to a qubit."""
    # Calls z() via Cython binding
```

### Algorithm Components (New Pure Python)

| Component | Implementation Approach | Dependencies |
|-----------|------------------------|--------------|
| `grover_iterate(oracle, n_qubits)` | Python function calling existing gates | h(), mcx(), oracle |
| `diffusion_operator(register)` | H-X-MCZ-X-H pattern using existing gates | h(), x(), z(), mcx() |
| `optimal_iterations(n_qubits, n_marked)` | Pure math: `floor(pi/4 * sqrt(N/M))` | math module only |
| `grover_search(oracle, n_qubits, n_iter)` | Composition of above | iterate + diffusion |
| `amplitude_estimate(problem, precision)` | Grover powers + measurement | grover_iterate |

## Technology Decisions

### Decision 1: Use Existing `with` Statement for S_0 Reflection

**What:** The S_0 (reflection about zero) component of the diffusion operator can be implemented using the existing quantum conditional pattern.

**Why:** The `with a == 0:` construct already generates controlled operations conditioned on all qubits being zero. Combined with a phase flip on an ancilla, this produces the required 2|0><0| - I reflection.

**Alternative considered:** Dedicated `reflection_zero()` C function.
**Why rejected:** Unnecessary duplication. The `with` conditional infrastructure is proven and handles controlled context stacking correctly.

**Implementation pattern:**
```python
def reflection_zero(register, ancilla):
    """S_0 = 2|0><0| - I reflection."""
    with register == 0:  # Generates multi-controlled gate
        ancilla.z()      # Phase flip only when all zero
```

### Decision 2: Oracle Compilation via @ql.compile

**What:** User-defined oracle functions decorated with `@ql.compile` are automatically converted to controlled circuit blocks.

**Why:** The `@ql.compile` decorator already:
- Captures gate sequences on first call
- Virtualizes qubit indices
- Derives controlled variants automatically
- Handles adjoint generation for uncomputation

**How oracles work:**
```python
@ql.compile
def oracle(x, target):
    """Mark states where f(x) = 1."""
    # User writes classical-style predicate
    with x == search_value:
        target.z()  # Phase flip marked states

# Oracle automatically becomes phase oracle O_f
```

### Decision 3: MCX Decomposition Strategy Selection

**What:** Multi-controlled X gates in the diffusion operator should use the existing MCX decomposition infrastructure.

**Why:** The framework already has:
- `emit_ccx_clifford_t()` for Toffoli decomposition
- MCX -> Toffoli cascade for arbitrary controls
- AND-ancilla decomposition for fault-tolerant mode

**Configuration:** Use `ql.option('fault_tolerant', True)` to select Clifford+T decomposition, or leave default for native CCX/MCX.

### Decision 4: No External Quantum Libraries for Core Algorithm

**What:** Implement Grover's algorithm natively without importing Qiskit's `GroverOperator` or similar.

**Why:**
- Quantum Assembly's value proposition is native implementation, not a Qiskit wrapper
- External library calls break the gate capture/replay model
- Users already have Qiskit if they want that approach
- Native implementation enables framework-specific optimizations

**Qiskit role:** Verification only (via `ql.option('verification')` or test infrastructure).

### Decision 5: Iterative Amplitude Estimation (Not Phase Estimation)

**What:** For amplitude estimation, use Iterative QAE (IQAE) rather than canonical phase-estimation-based QAE.

**Why:**
- IQAE uses only Grover operators, no QFT required
- Lower circuit depth (critical for NISQ devices)
- Modular: runs multiple independent circuits
- Same quadratic speedup, fewer qubits
- [Research shows IQAE is "best candidate to demonstrate advantage"](https://www.nature.com/articles/s41534-021-00379-1)

**What this means:** No new circuit components beyond Grover operator powers.

## Supporting Libraries (Already Dependencies)

| Library | Current Version | Purpose for Grover | Rationale |
|---------|-----------------|-------------------|-----------|
| NumPy | >=1.24 | Qubit array manipulation | Already in pyproject.toml |
| Qiskit | >=1.0 (optional) | Verification | Already in [verification] extra |

No version changes or additions required.

## Installation

**No changes to pyproject.toml needed.**

The existing installation covers all requirements:
```bash
pip install -e .                    # Core framework
pip install -e ".[verification]"    # With Qiskit for testing
```

## What NOT to Add

### 1. Do NOT add Cirq, PennyLane, or other quantum frameworks

**Why not:**
- Creates framework fragmentation
- Different gate naming conventions
- Quantum Assembly's goal is self-contained implementation
- Users can export to OpenQASM for interoperability

### 2. Do NOT add specialized Grover libraries (e.g., `grove`, `groveropt`)

**Why not:**
- Niche packages with uncertain maintenance
- Likely incompatible with Quantum Assembly's circuit model
- The algorithm is simple enough to implement directly

### 3. Do NOT add symbolic math libraries (SymPy) for oracle analysis

**Why not:**
- Over-engineering for this use case
- Oracle compilation doesn't need symbolic analysis
- Classical Python evaluation + gate capture is sufficient

### 4. Do NOT add SAT solvers for automatic oracle synthesis

**Why not:**
- Scope creep - SAT-based synthesis is a research topic
- Users provide oracles as Python functions, not logic formulas
- Phase 1 should be manual oracle construction
- Automatic synthesis is a potential future milestone (v5.0+)

### 5. Do NOT add mid-circuit measurement infrastructure

**Why not:**
- Measurement-based uncomputation (Gidney's trick) is deferred
- Current framework uses coherent uncomputation
- Mid-circuit measurement requires significant infrastructure changes
- Grover works fine with standard measurement at end

### 6. Do NOT add QFT-based arithmetic for Grover oracles

**Why not:**
- Toffoli arithmetic is already implemented and fault-tolerant
- QFT-based oracles would break fault-tolerant compilation goal
- Existing bugs in QFT division (BUG-QFT-DIV) would propagate

## Integration Points

### Existing API Extensions

| Extension | Description | Implementation |
|-----------|-------------|----------------|
| `ql.hadamard(qbit)` | Single-qubit Hadamard | Cython wrapper to `h()` |
| `ql.hadamard_all(register)` | H^n on register | Loop over qubits |
| `ql.phase(qbit)` | Z gate | Cython wrapper to `z()` |
| `ql.grover_iterate(oracle, reg)` | One Grover iteration | Oracle + diffusion |
| `ql.optimal_iter(n, m=1)` | Iteration count formula | Pure Python math |
| `ql.grover(oracle, n_qubits, iter=None)` | Full search | Compose above |

### Oracle Interface

```python
# User-defined oracle pattern
@ql.compile
def my_oracle(x: qint, ancilla: qbool):
    """Phase oracle: flip phase when x satisfies predicate."""
    # Classical-style predicate using existing operations
    with x == target_value:  # Or any comparison
        ancilla.z()
    # OR for arithmetic predicate:
    with (x * x) == 4:  # Uses Toffoli multiplication
        ancilla.z()
```

### Amplitude Estimation Interface

```python
# Iterative amplitude estimation
result = ql.amplitude_estimate(
    oracle=my_oracle,
    state_prep=default_hadamard,  # Optional custom
    precision=0.01,               # Target accuracy
    confidence=0.95               # Confidence level
)
# Returns: estimated amplitude, confidence interval
```

## Patterns by Use Case

### Pattern A: Simple Search (Known Target)

```python
@ql.compile
def search_oracle(x, target):
    with x == target:
        target.z()

circuit = ql.circuit()
x = ql.qint(0, width=4)  # 4-qubit search space (N=16)
target = ql.qbool(True)  # Ancilla for phase flip

ql.hadamard_all(x)       # Uniform superposition
for _ in range(3):       # ~pi/4 * sqrt(16) = 3 iterations
    ql.grover_iterate(search_oracle, x, target)
```

### Pattern B: Arithmetic Oracle

```python
@ql.compile
def factor_oracle(x, y, n_target, ancilla):
    """Mark (x,y) pairs where x*y == n_target."""
    product = x * y
    with product == n_target:
        ancilla.z()
    # product auto-uncomputed by @ql.compile

# Used identically to simple search
```

### Pattern C: Amplitude Estimation

```python
# Count satisfying assignments
problem = ql.EstimationProblem(
    oracle=my_oracle,
    n_qubits=8,
    objective_qubits=[7]  # Ancilla qubit
)

result = ql.iterative_amplitude_estimate(problem, precision=0.01)
n_solutions = result.amplitude * (2 ** 8)  # Estimated count
```

## Version Compatibility

No new dependencies means no compatibility concerns beyond existing:

| Current Constraint | Rationale |
|--------------------|-----------|
| Python >=3.11 | Type hints, async features |
| NumPy >=1.24 | Stable API for qubit arrays |
| Cython >=3.0.11,<4.0 | C extension compilation |
| Qiskit >=1.0 (optional) | Verification only |

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|------------|--------|-------|
| Gate primitives | HIGH | Codebase analysis | `h()`, `z()`, `mcx()` all exist in gate.h/gate.c |
| Conditional context | HIGH | Test suite | `with flag:` working for comparisons |
| `@ql.compile` | HIGH | Extensive testing | Controlled variants, adjoint derivation proven |
| Iteration formula | HIGH | [Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm), [IBM](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) | Standard result: floor(pi/4 * sqrt(N/M)) |
| Amplitude estimation | MEDIUM | [Qiskit Finance tutorial](https://qiskit-community.github.io/qiskit-finance/tutorials/00_amplitude_estimation.html) | IQAE approach verified, implementation details need planning |
| Oracle compilation | HIGH | `@ql.compile` analysis | Existing gate capture handles user functions |

## Sources

### Primary (HIGH confidence)
- [Grover's Algorithm - IBM Quantum Documentation](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) - Standard implementation pattern
- [Grover's Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm) - Iteration formula: r = floor(pi/4 * sqrt(N/M))
- [Azure Quantum - Grover Theory](https://learn.microsoft.com/en-us/azure/quantum/concepts-grovers) - Mathematical foundations
- [Iterative QAE - npj Quantum Information](https://www.nature.com/articles/s41534-021-00379-1) - IQAE as preferred variant
- [Qiskit Amplitude Estimation Tutorial](https://qiskit-community.github.io/qiskit-finance/tutorials/00_amplitude_estimation.html) - EstimationProblem interface

### Secondary (MEDIUM confidence)
- [grover_operator - IBM Quantum](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.grover_operator) - Reference implementation (deprecated class, function preferred)
- [Automated Oracle Synthesis - arXiv:2304.03829](https://arxiv.org/abs/2304.03829) - Future direction for automatic oracle generation
- [PennyLane Amplitude Amplification](https://pennylane.ai/qml/demos/tutorial_intro_amplitude_amplification) - Alternative framework reference

### Codebase Analysis
- `c_backend/include/gate.h` - Gate function declarations (h, z, mcx exist)
- `src/quantum_language/qint.pyx` lines 584-679 - Conditional context implementation
- `src/quantum_language/compile.py` - Gate capture and controlled variant derivation

---
*Stack research for: Grover's Algorithm & Amplitude Estimation*
*Researched: 2026-02-19*
*Conclusion: Zero new dependencies. Build on existing infrastructure.*
