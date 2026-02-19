# Architecture Research: Grover's Algorithm Integration

**Domain:** Quantum search algorithms (Grover's algorithm, amplitude amplification, amplitude estimation)
**Researched:** 2026-02-19
**Confidence:** HIGH (based on thorough codebase analysis + algorithm literature)

## Executive Summary

The existing three-layer architecture (C backend -> Cython bindings -> Python frontend) is well-suited for Grover's algorithm integration. The key insight is that Grover's algorithm is a **meta-algorithm** that composes existing primitives: oracle functions (user-defined comparisons), diffusion operator (Hadamard + conditional phase flip), and iteration control. The existing `@ql.compile` decorator, `with` statement for controlled gates, and automatic uncomputation provide the building blocks -- new components primarily orchestrate these existing features rather than implementing low-level gate sequences.

Oracle compilation leverages the existing capture-replay mechanism: a user-defined function `f(*args) -> qbool` is traced once to capture its gate sequence, then replayed with phase kickback (controlled-Z) to mark solutions. The diffusion operator uses the existing `with a == 0` controlled gate pattern plus Hadamard gates. Amplitude estimation extends Grover iteration with quantum phase estimation, reusing QFT sequences already implemented for QFT-based arithmetic.

## Recommended Architecture

### High-Level Component Overview

```
Python Layer (Orchestration)
+------------------------------------------------------------------+
|  grover(oracle, *args, iterations=auto)                          |
|    |                                                             |
|    +-- OracleWrapper (oracle_func -> phase-marking circuit)      |
|    |     |                                                       |
|    |     +-- @ql.compile (capture gate sequence)                 |
|    |     +-- phase_kickback (Z gate controlled by oracle output) |
|    |                                                             |
|    +-- DiffusionOperator (reflect about mean)                    |
|    |     |                                                       |
|    |     +-- H on all search qubits                              |
|    |     +-- S0 reflection (with x == 0: phase flip)             |
|    |     +-- H on all search qubits                              |
|    |                                                             |
|    +-- IterationController                                       |
|          +-- optimal_iterations(N, M) calculation                |
|          +-- early termination support                           |
+------------------------------------------------------------------+
                          |
                          v
Cython Layer (Bindings + qint/qbool)
+------------------------------------------------------------------+
|  qint, qbool, qarray (existing)                                  |
|    |                                                             |
|    +-- __eq__, __lt__, etc. -> comparison circuits               |
|    +-- with statement -> controlled gate context                 |
|    +-- automatic uncomputation -> dependency tracking            |
|                                                                  |
|  NEW: grover_primitives.pxi (thin wrappers)                     |
|    +-- hadamard_all(qarray) -> batch H gates                     |
|    +-- phase_flip(qbool) -> Z gate                               |
+------------------------------------------------------------------+
                          |
                          v
C Backend (Gate Sequences)
+------------------------------------------------------------------+
|  EXISTING: All gate primitives needed                            |
|    +-- H gate: h(gate_t*, qubit_t)                               |
|    +-- Z gate: z(gate_t*, qubit_t)                               |
|    +-- CZ gate: cz(gate_t*, qubit_t, qubit_t)                    |
|    +-- Multi-controlled Z: mcx + phase decomposition             |
|                                                                  |
|  OPTIONAL NEW: grover_sequences.c                               |
|    +-- diffusion_sequence(n) -> precompiled H-S0-H sequence     |
+------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Layer | Status |
|-----------|---------------|-------|--------|
| `grover()` | Main entry point, orchestrates search | Python | NEW |
| `OracleWrapper` | Wraps user function for phase marking | Python | NEW |
| `DiffusionOperator` | Implements reflection about mean | Python | NEW |
| `IterationController` | Calculates optimal iterations | Python | NEW |
| `@ql.compile` | Captures oracle gate sequence | Python | EXISTS |
| `qint.__eq__`, `__lt__` | Comparison circuits for oracles | Cython | EXISTS |
| `with qbool:` | Controlled gate context | Cython | EXISTS |
| `h()`, `z()`, `cz()` | Gate primitives | C | EXISTS |
| `mcx()` | Multi-controlled X | C | EXISTS |
| `emit_ccx_clifford_t()` | Toffoli decomposition | C | EXISTS |

## Detailed Integration Design

### 1. Oracle Compilation Architecture

**Goal:** Allow users to write `f(*args) -> qbool` and auto-compile to phase-marking oracle.

**The existing `@ql.compile` infrastructure handles 90% of this:**

```python
# User writes natural comparisons:
def find_solution(x):
    return x == 42  # Returns qbool

# OracleWrapper transforms this for Grover:
class OracleWrapper:
    def __init__(self, func):
        self._compiled = ql.compile(func)

    def mark_phase(self, *args):
        """Execute oracle and apply phase kickback."""
        # 1. Evaluate oracle (produces qbool result)
        result = self._compiled(*args)

        # 2. Apply phase kickback: Z on result qubit
        #    This marks |1> states with -1 phase
        self._apply_z(result)

        # 3. Uncompute oracle (reverse gates to free ancillas)
        self._compiled.inverse(*args)
```

**Key insight:** The compiled function's `.inverse()` method already exists and handles uncomputation correctly. The oracle evaluation is reversible by design.

**Phase kickback implementation options:**

Option A: **Add Z gate to gate.h primitives (minimal)**
```c
// Already exists in gate.h:
void z(gate_t *g, qubit_t target);
```

Option B: **Use controlled-Z for explicit marking**
```c
// Already exists:
void cz(gate_t *g, qubit_t target, qubit_t control);
```

**Oracle types supported by existing infrastructure:**

| Oracle Type | Example | Existing Support |
|-------------|---------|------------------|
| Equality | `x == 42` | `CQ_equal_width` circuit |
| Inequality | `x != 42` | `~(x == 42)` via inversion |
| Range | `x < 100` | Subtraction + sign bit check |
| Compound | `(x > 10) & (x < 50)` | Bitwise AND of qbools |
| Custom | User-defined logic | `@ql.compile` captures any logic |

### 2. Diffusion Operator Architecture

**The diffusion operator reflects amplitudes about the mean using the formula:**
```
D = 2|s><s| - I
```
where |s> is the uniform superposition state.

**Circuit implementation uses existing primitives:**

```
D = H^n * (2|0><0| - I) * H^n
  = H^n * S_0 * H^n
```

Where S_0 is the "reflection about zero" operator.

**S_0 implementation via existing `with` statement:**

The existing `with qint:` context manager makes controlled gates. Combined with MCX decomposition already in the codebase:

```python
def diffusion(search_register):
    """Apply diffusion operator to search register."""
    n = len(search_register)

    # H^n
    for qubit in search_register:
        H(qubit)

    # S_0: flip phase of |0...0> state
    # Implemented as: X on all, multi-controlled Z, X on all
    for qubit in search_register:
        X(qubit)

    # Multi-controlled Z on last qubit, controlled by all others
    # This is equivalent to a phase flip on |1...1> (which was |0...0>)
    with search_register[:-1].all():  # All qubits except last as controls
        Z(search_register[-1])

    for qubit in search_register:
        X(qubit)

    # H^n
    for qubit in search_register:
        H(qubit)
```

**Alternative S_0 via `with x == 0`:**

The existing comparison operators make this even cleaner:

```python
def diffusion(x):
    """Apply diffusion operator using existing comparison."""
    # H on all qubits
    hadamard_all(x)

    # S_0 via comparison (already supported!)
    with x == 0:
        # Phase flip - need to add phase gate application
        apply_global_phase_flip()  # NEW: Simple Z gate

    # H on all qubits
    hadamard_all(x)
```

**Decision: Use explicit MCX pattern, not `x == 0`**

Rationale: The `x == 0` comparison allocates ancilla qubits and generates a multi-bit equality check circuit. The MCX pattern is more efficient for diffusion because:
1. No ancilla allocation needed
2. Direct phase flip without intermediate qbool
3. Gate count is O(n) vs O(n^2) for comparison

### 3. Grover Iteration Controller

**Optimal iteration count formula:**
```python
def optimal_iterations(N: int, M: int = 1) -> int:
    """Calculate optimal Grover iterations.

    Args:
        N: Search space size (2^n for n qubits)
        M: Number of solutions

    Returns:
        Optimal number of iterations (floor(pi/4 * sqrt(N/M)))
    """
    import math
    return int(math.floor(math.pi / 4 * math.sqrt(N / M)))
```

**Integration with circuit layer tracking:**

The existing `_start_layer` and `_end_layer` tracking on qint/qbool enables:
1. Measuring circuit depth per iteration
2. Supporting variable iteration counts
3. Potential early termination optimization

### 4. Amplitude Estimation Architecture

**Amplitude estimation uses Grover iteration as a subroutine:**

```
             +---------+
|0>^t ---H---| QFT^-1  |--- measure theta
             |         |
             +----|----+
                  |
|psi> -------[Q^(2^j)]--- (j = 0 to t-1)
```

Where Q = Grover iterate = oracle * diffusion.

**QFT reuse:** The existing QFT infrastructure from arithmetic operations can be reused:

```c
// Already exists in gate.h:
sequence_t *QFT(sequence_t *seq, int num_qubits);
sequence_t *QFT_inverse(sequence_t *seq, int num_qubits);
```

**Controlled Grover iteration:**

The `@ql.compile` decorator already supports controlled variants via cache derivation:

```python
# From compile.py line 183-195:
def _derive_controlled_gates(gates, control_virtual_idx):
    """Add one control qubit to every gate in the list."""
    controlled = []
    for g in gates:
        cg = dict(g)
        cg["num_controls"] = g["num_controls"] + 1
        cg["controls"] = [control_virtual_idx] + list(g["controls"])
        controlled.append(cg)
    return controlled
```

**Amplitude estimation component structure:**

```python
class AmplitudeEstimator:
    def __init__(self, oracle, precision_bits: int):
        self.oracle = OracleWrapper(oracle)
        self.precision = precision_bits
        self.grover_iterate = GroverIterate(self.oracle)

    def estimate(self, *search_args):
        """Estimate amplitude of marked states."""
        # 1. Allocate precision register (t qubits)
        precision_reg = qarray(dim=self.precision, dtype=qbool)

        # 2. Initialize precision register in superposition
        hadamard_all(precision_reg)

        # 3. Apply controlled powers of Grover iterate
        for j in range(self.precision):
            power = 2 ** j
            with precision_reg[j]:
                for _ in range(power):
                    self.grover_iterate(*search_args)

        # 4. Apply inverse QFT on precision register
        qft_inverse(precision_reg)

        # 5. Measure precision register
        return measure(precision_reg)
```

### 5. New Components Specification

#### 5.1 grover.py (Python module)

```python
# Location: src/quantum_language/grover.py
# ~400 lines estimated

class OracleWrapper:
    """Wraps user function for phase-marking oracle."""

class DiffusionOperator:
    """Implements reflection about mean."""

class GroverSearch:
    """Main Grover search implementation."""

def grover(oracle, *args, iterations=None):
    """Run Grover's algorithm on oracle with given arguments."""

def optimal_iterations(n_qubits, n_solutions=1):
    """Calculate optimal iteration count."""
```

#### 5.2 amplitude_estimation.py (Python module)

```python
# Location: src/quantum_language/amplitude_estimation.py
# ~300 lines estimated

class AmplitudeEstimator:
    """Quantum amplitude estimation using phase estimation."""

def estimate_amplitude(oracle, *args, precision=8):
    """Estimate amplitude of oracle-marked states."""
```

#### 5.3 grover_primitives.pxi (Cython include)

```cython
# Location: src/quantum_language/grover_primitives.pxi
# ~150 lines estimated

def hadamard_all(qarray arr):
    """Apply Hadamard to all qubits in array."""

def apply_z(qbool target):
    """Apply Z gate to single qubit."""

def multi_controlled_z(qarray controls, qbool target):
    """Apply multi-controlled Z gate."""
```

#### 5.4 Cython Bindings Updates

**_core.pyx additions (~30 lines):**

```cython
# Export Z gate sequence function
def _apply_z_gate(qubit_idx):
    """Apply Z gate to qubit at given index."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    z(&g, qubit_idx)
    add_gate(circ, &g)

# Export H gate sequence function
def _apply_h_gate(qubit_idx):
    """Apply H gate to qubit at given index."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    h(&g, qubit_idx)
    add_gate(circ, &g)
```

### 6. Data Flow Changes

#### 6.1 Oracle Compilation Flow

```
User Function: f(x: qint) -> qbool
    |
    v
@ql.compile captures gate sequence
    |
    v
OracleWrapper.mark_phase():
    |
    +-- Execute compiled function -> gate sequence emitted
    |
    +-- Extract result qbool qubit index
    |
    +-- Apply Z gate to result qubit (phase marking)
    |
    +-- Call compiled.inverse() -> adjoint gates emitted
```

#### 6.2 Grover Iteration Flow

```
GroverSearch.__call__(x):
    |
    +-- Initialize: H on all qubits of x
    |
    for i in range(iterations):
        |
        +-- Oracle: OracleWrapper.mark_phase(x)
        |
        +-- Diffusion: DiffusionOperator(x)
    |
    v
Result: x in superposition biased toward solutions
```

#### 6.3 Amplitude Estimation Flow

```
AmplitudeEstimator.estimate(x):
    |
    +-- Allocate precision register (t qubits)
    |
    +-- H on precision register
    |
    for j in 0..t-1:
        |
        +-- with precision[j]:
        |       for _ in range(2^j):
        |           GroverIterate(x)
    |
    +-- QFT_inverse(precision)
    |
    v
Result: precision register encodes amplitude theta
```

## Patterns to Follow

### Pattern 1: Compile-Based Oracle Wrapping

**What:** Use `@ql.compile` to capture oracle function and derive controlled/adjoint variants.
**When:** For all oracle functions in Grover/amplitude estimation.
**Trade-offs:**
- Pro: Reuses existing optimized infrastructure
- Pro: Automatic gate optimization (inverse cancellation, rotation merge)
- Con: First call has capture overhead

**Example:**
```python
@ql.compile
def is_solution(x):
    return x == 42

# OracleWrapper automatically derives:
# - is_solution(x)           -> forward evaluation
# - is_solution.inverse(x)   -> adjoint for uncomputation
# - is_solution (controlled) -> phase marking with control qubit
```

### Pattern 2: Diffusion via MCX Decomposition

**What:** Use X-MCZ-X pattern for diffusion, leveraging existing MCX decomposition.
**When:** For diffusion operator in Grover/amplitude amplification.
**Trade-offs:**
- Pro: No ancilla qubits needed for S_0
- Pro: Uses optimized MCX decomposition path
- Con: More verbose than comparison-based approach

**Example:**
```python
def diffusion(x):
    """Reflect about mean state."""
    n = x.width

    # H^n
    for i in range(n):
        H(x[i])

    # S_0 = X^n * MCZ * X^n
    for i in range(n):
        X(x[i])
    # MCZ: multi-controlled Z
    with x[:-1].all():  # n-1 controls
        Z(x[-1])
    for i in range(n):
        X(x[i])

    # H^n
    for i in range(n):
        H(x[i])
```

### Pattern 3: Controlled Grover Iterate for Amplitude Estimation

**What:** Use `with` statement to create controlled Grover iterates for QPE.
**When:** In amplitude estimation's controlled-U^k applications.
**Trade-offs:**
- Pro: Reuses existing controlled gate infrastructure
- Pro: Automatic control qubit tracking
- Con: Each controlled gate adds depth

**Example:**
```python
def amplitude_estimation_core(precision_reg, grover_iterate, x):
    for j in range(len(precision_reg)):
        power = 2 ** j
        with precision_reg[j]:  # Control on precision qubit
            for _ in range(power):
                grover_iterate(x)  # Automatically controlled
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Manual Gate-by-Gate Oracle Construction

**What people do:** Build oracle circuit gate-by-gate instead of using `@ql.compile`.
**Why it's wrong:**
- Loses optimization opportunities
- No automatic adjoint derivation
- Harder to maintain and debug
**Do this instead:** Use `@ql.compile` on natural Python comparisons.

### Anti-Pattern 2: Using Comparison for Diffusion S_0

**What people do:** `with x == 0: phase_flip()` for S_0 in diffusion.
**Why it's wrong:**
- Allocates ancilla qubits unnecessarily
- Generates multi-bit equality check circuit
- O(n^2) gate count vs O(n) for direct MCZ
**Do this instead:** Use X-MCZ-X pattern directly.

### Anti-Pattern 3: Hardcoding Iteration Count

**What people do:** Fixed `for i in range(10):` in Grover loop.
**Why it's wrong:**
- Over-iteration destroys solution amplitude
- Under-iteration gives low success probability
- Ignores problem-specific optimal count
**Do this instead:** Calculate `optimal_iterations(N, M)` from search space size.

### Anti-Pattern 4: Not Uncomputing Oracle Ancillas

**What people do:** Evaluate oracle, mark phase, forget about cleanup.
**Why it's wrong:**
- Ancilla qubits remain allocated
- Entanglement with ancillas corrupts amplitude amplification
- Circuit grows unboundedly with iterations
**Do this instead:** Always call `oracle.inverse()` after phase marking.

## Integration Points

### Existing Infrastructure Reuse

| Feature | Existing Code | How Grover Uses It |
|---------|---------------|-------------------|
| Gate capture | `compile.py:_capture()` | Oracle function compilation |
| Gate replay | `compile.py:_replay()` | Oracle re-execution |
| Adjoint derivation | `compile.py:_InverseCompiledFunc` | Oracle uncomputation |
| Controlled derivation | `compile.py:_derive_controlled_gates()` | Controlled Grover iterate |
| Multi-qubit conditions | `with qbool:` context | Controlled gates in diffusion |
| Qubit allocation | `qubit_allocator.c` | Ancilla for complex oracles |
| Automatic uncompute | `qint._do_uncompute()` | Oracle cleanup |
| QFT sequences | `IntegerAddition.c:QFT()` | Amplitude estimation |
| MCX decomposition | `gate.c:emit_ccx_clifford_t()` | Multi-controlled Z in diffusion |

### New <-> Existing Boundaries

| New Component | Calls | Returns |
|---------------|-------|---------|
| `OracleWrapper.__init__` | `ql.compile(func)` | `CompiledFunc` |
| `OracleWrapper.mark_phase` | `compiled_func(args)`, `_apply_z()`, `compiled_func.inverse(args)` | None (side effect) |
| `DiffusionOperator.__call__` | `_apply_h_gate()`, `_apply_z_gate()`, `with` context | None (side effect) |
| `GroverSearch.__call__` | `OracleWrapper`, `DiffusionOperator` | Input qint (modified) |
| `AmplitudeEstimator.estimate` | `GroverSearch`, `QFT_inverse` | Measurement result |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-4 qubits | Direct implementation, full simulation possible |
| 5-10 qubits | Need efficient MCX decomposition (already exists) |
| 10-20 qubits | Consider T-gate optimization for fault tolerance |
| 20+ qubits | Requires hardware execution, depth optimization critical |

### Depth vs Width Trade-offs

| Choice | Depth Impact | Width Impact | When to Use |
|--------|--------------|--------------|-------------|
| Linear MCX | O(n) | O(1) ancilla | NISQ, depth-limited |
| Log-depth MCX | O(log n) | O(n) ancilla | Fault-tolerant |
| CQ comparison oracle | Low | 0 ancilla | Known solution pattern |
| QQ comparison oracle | Higher | 1+ ancilla | Unknown search criteria |

## Suggested Build Order

**Phase ordering follows dependency chain:**

### Phase 1: Gate Primitives (1-2 days)

1. Add `_apply_h_gate()` to `_core.pyx`
2. Add `_apply_z_gate()` to `_core.pyx`
3. Add `_apply_cz_gate()` to `_core.pyx`
4. Create `grover_primitives.pxi` with `hadamard_all(qarray)`
5. Write unit tests for new gate functions

**Dependencies:** None (uses existing `gate.h` functions)

### Phase 2: Oracle Wrapper (2-3 days)

1. Create `grover.py` module skeleton
2. Implement `OracleWrapper.__init__()` wrapping `@ql.compile`
3. Implement `OracleWrapper.mark_phase()` with Z gate application
4. Add support for multi-qubit oracle outputs
5. Write tests with simple equality oracles (`x == 42`)
6. Write tests with compound oracles (`(x > 10) & (x < 50)`)

**Dependencies:** Phase 1 (Z gate), existing `@ql.compile`

### Phase 3: Diffusion Operator (1-2 days)

1. Implement `DiffusionOperator.__init__()`
2. Implement `DiffusionOperator.__call__()` with H-S0-H pattern
3. Optimize S_0 using MCX decomposition path
4. Write tests verifying phase flip on |0> state
5. Benchmark against naive implementation

**Dependencies:** Phase 1 (H gate), existing MCX infrastructure

### Phase 4: Grover Search Integration (2-3 days)

1. Implement `GroverSearch.__init__(oracle, iterations=None)`
2. Implement `optimal_iterations(N, M)` calculation
3. Implement `GroverSearch.__call__(x)` main loop
4. Add auto-iteration detection from qubit count
5. Write end-to-end tests with known solutions
6. Verify amplitude amplification behavior

**Dependencies:** Phase 2 (oracle), Phase 3 (diffusion)

### Phase 5: Amplitude Estimation (3-4 days)

1. Create `amplitude_estimation.py` module
2. Implement controlled Grover iterate using `with` context
3. Implement QFT inverse integration
4. Implement `AmplitudeEstimator.estimate()`
5. Write tests comparing estimated vs known amplitudes
6. Add precision parameter support

**Dependencies:** Phase 4 (Grover iterate), existing QFT infrastructure

### Phase 6: API Polish and Documentation (1-2 days)

1. Add `ql.grover()` convenience function
2. Add `ql.estimate_amplitude()` convenience function
3. Write docstrings with examples
4. Add type hints
5. Create usage examples in docs/

**Dependencies:** All previous phases

**Total estimated time: 10-16 days**

## File Inventory: New vs Modified

### New Files (4)

| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/quantum_language/grover.py` | Grover search implementation | ~400 |
| `src/quantum_language/amplitude_estimation.py` | Amplitude estimation | ~300 |
| `src/quantum_language/grover_primitives.pxi` | Cython gate helpers | ~150 |
| `tests/python/test_grover.py` | Grover algorithm tests | ~500 |

### Modified Files (4)

| File | Change | Lines Added |
|------|--------|-------------|
| `src/quantum_language/_core.pyx` | Add `_apply_h_gate`, `_apply_z_gate` | ~20 |
| `src/quantum_language/__init__.py` | Export `grover`, `estimate_amplitude` | ~5 |
| `src/quantum_language/qint.pyx` | Include `grover_primitives.pxi` | ~1 |
| `setup.py` | Add new Python modules to package | ~5 |

### Files That Do NOT Need Changes

| File | Why No Change |
|------|---------------|
| `compile.py` | Oracle wrapping uses existing compile infrastructure |
| `qarray.pyx` | All qarray operations already support Grover needs |
| `qint_comparison.pxi` | Comparison circuits work unchanged for oracles |
| `c_backend/*` | All needed gates already exist (H, Z, CZ, MCX) |
| `qubit_allocator.c` | Ancilla management unchanged |
| `circuit_optimizer.c` | Gate optimization applies to Grover circuits |

## Sources

- [Grover's algorithm - Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm) - Algorithm overview
- [Automatic generation of efficient oracles - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0164121224002474) - Oracle compilation patterns
- [PennyLane Grover's Algorithm Tutorial](https://pennylane.ai/qml/demos/tutorial_grovers_algorithm) - Implementation reference
- [Qiskit Finance Amplitude Estimation](https://qiskit-community.github.io/qiskit-finance/tutorials/00_amplitude_estimation.html) - AE implementation patterns
- [Modular Quantum Amplitude Estimation](https://arxiv.org/html/2508.05805v1) - Modern AE architecture (2025)
- [Iterative QAE - npj Quantum Information](https://www.nature.com/articles/s41534-021-00379-1) - QPE-free amplitude estimation variant
- [Quantum Amplitude Amplification and Estimation](https://arxiv.org/abs/quant-ph/0005055) - Original Brassard et al. paper

---
*Architecture research for: Grover's Algorithm Integration*
*Researched: 2026-02-19*
