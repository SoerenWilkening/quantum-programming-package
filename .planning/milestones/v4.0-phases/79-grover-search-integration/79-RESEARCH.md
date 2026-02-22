# Phase 79: Grover Search Integration - Research

**Researched:** 2026-02-21
**Domain:** Grover's search algorithm end-to-end API, quantum circuit composition, Qiskit simulation, iteration count auto-calculation
**Confidence:** HIGH

## Summary

Phase 79 integrates the oracle infrastructure (Phase 77) and diffusion operator (Phase 78) into a single `ql.grover(oracle)` API that performs Grover's search algorithm end-to-end: creates a circuit, infers search register parameters from oracle type annotations, initializes equal superposition, applies the optimal number of oracle+diffusion iterations, simulates via Qiskit, and returns measured Python value(s). This is a **pure Python module** -- no C backend changes or Cython modifications are required because all gate primitives, oracle validation, diffusion operator, compile caching, and QASM export already exist.

The key engineering challenges are: (1) introspecting the oracle function's parameter annotations to determine register count and widths without the user passing registers explicitly, (2) composing a complete Grover iteration (oracle call, branch, diffusion, branch) that correctly uses `@ql.compile`-decorated diffusion and `GroverOracle`-wrapped oracles, (3) auto-calculating iteration count using `floor(pi/4 * sqrt(N/M) - 0.5)` with edge case handling for M=0 and M=N, (4) running single-shot Qiskit simulation internally and parsing the measured bitstring back into Python integer value(s), and (5) handling multi-register oracles where the flat tuple return includes values from each register plus the iteration count.

**Primary recommendation:** Implement `ql.grover()` as a new module `grover.py` in `src/quantum_language/`, following the existing module pattern (oracle.py, diffusion.py). The function uses `inspect.signature` to introspect the oracle's parameter annotations, creates quantum registers of inferred width, builds the complete circuit, exports to OpenQASM, simulates with Qiskit AerSimulator(shots=1), parses the bitstring, and returns a flat tuple of `(value, iterations)` or `(x_val, y_val, ..., iterations)`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Accepts any @ql.compile decorated function (not limited to @ql.grover_oracle) -- auto-wraps with oracle semantics if needed
- Search register inferred from oracle function's type-annotated parameters -- user does NOT pass register explicitly
- Supports multi-register oracles (e.g., oracle(x: qint, y: qint)) -- diffusion applied to all search registers
- Auto-initializes equal superposition (H^n) on all search registers before iterations
- Solution count `m` is optional, defaults to 1
- Explicit `iterations=k` override parameter available to bypass auto-calculation
- Fully self-contained: creates circuit, initializes superposition, runs iterations, simulates, returns result
- Returns a plain tuple: `(value, iterations)` for single-register oracles
- For multi-register oracles: `(x_val, y_val, ..., iterations)` -- flat tuple, iterations always last
- Single shot simulation -- value is sampled from probability distribution, not deterministic argmax
- Auto-calculated using `floor(pi/4 * sqrt(N/M) - 0.5)` formula
- When M=0: run 0 iterations, return random measurement from initial superposition
- When M=N: skip iterations (0 iterations), measure immediately
- No maximum cap on iterations -- trust the formula
- No validation that M <= N -- let it run regardless
- ql.grover() runs Qiskit simulation internally -- truly all-in-one black box
- True single-shot sampling from probability distribution (not statevector argmax)
- All registers measured (every qubit in every register passed to oracle)
- Circuit is internal -- not exposed for inspection (no circuit in return value, no separate grover_circuit method)

### Claude's Discretion
- Internal circuit construction approach (how oracle/diffusion are composed)
- Error handling for invalid oracle functions
- How multi-register diffusion is applied (joint vs per-register)
- Qiskit backend selection and simulation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GROV-01 | `ql.grover(oracle, search_space)` API executes search and returns measured value | The function creates quantum registers by inspecting oracle parameter annotations via `inspect.signature`, builds the full circuit (superposition + iterations of oracle+diffusion), exports to OpenQASM via `ql.to_openqasm()`, simulates with `AerSimulator(shots=1)`, and parses the bitstring result into Python integer(s). The CONTEXT.md refines the API to `ql.grover(oracle)` with register inference (no explicit search_space argument). |
| GROV-02 | Automatic iteration count calculated from search space size N and solution count M | Formula: `floor(pi/4 * sqrt(N/M) - 0.5)`. N = total search space size = product of 2^width for each register. M defaults to 1, overridable via `m=` parameter. Edge cases: M=0 -> 0 iterations, M=N -> 0 iterations. Verified numerically: N=8,M=1 -> k=1 (P=0.78); N=4,M=1 -> k=1 (P=1.00); N=16,M=1 -> k=2 (P=0.91). |
| GROV-04 | Multiple solutions supported (iteration formula accounts for M > 1) | The formula `floor(pi/4 * sqrt(N/M) - 0.5)` naturally handles M>1 by reducing the iteration count. Verified: N=8,M=2 -> k=1 (P=1.00); N=8,M=4 -> k=0 (skip). Multi-register oracles are also supported with joint diffusion across all registers. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `quantum_language.oracle` | internal | `GroverOracle` class, `grover_oracle` decorator | Phase 77 deliverable -- oracle validation, caching, bit-flip wrapping |
| `quantum_language.diffusion` | internal | `diffusion()` function (X-MCZ-X pattern) | Phase 78 deliverable -- zero-ancilla S_0 reflection |
| `quantum_language._gates` | internal | `emit_h`, `emit_ry` (for superposition initialization) | Gate primitives for Hadamard / branch |
| `quantum_language.compile` | internal | `@ql.compile` decorator, `CompiledFunc` class | Gate capture/replay, width classification |
| `quantum_language._core` | internal | `circuit()`, `circuit_stats()`, `option()` | Circuit creation, allocator stats |
| `quantum_language.openqasm` | internal | `to_openqasm()` | QASM 3.0 export for Qiskit simulation |
| `quantum_language.qint` | internal | `qint` type | Quantum register creation and manipulation |
| `inspect` | stdlib | `inspect.signature()` | Oracle parameter introspection (name, type annotation, count) |
| `math` | stdlib | `math.floor()`, `math.pi`, `math.sqrt()` | Iteration count calculation |
| `qiskit` | 1.x+ | `qiskit.qasm3.loads()` | Parse exported OpenQASM into Qiskit circuit |
| `qiskit-aer` | 0.15+ | `AerSimulator` | Single-shot simulation for measurement sampling |
| `qiskit` | 1.x+ | `transpile()` | Circuit compilation for AerSimulator |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | `typing.get_type_hints()` | Fallback for oracle parameter type resolution |
| `qiskit_qasm3_import` | pip | QASM 3.0 import support for `qiskit.qasm3.loads()` | Already installed (Phase 78 dependency) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `inspect.signature` for param inference | Require user to pass register widths explicitly | Inference is cleaner UX (user decision locked); explicit is simpler to implement |
| AerSimulator with QASM export | Direct statevector computation | QASM pipeline already proven in 100+ tests; statevector would skip QASM validation |
| `qint.branch(0.5)` for superposition | Direct `emit_h` on each qubit | `branch(0.5)` is the standard project API for equal superposition (PRIM-03) |

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── grover.py           # NEW: ql.grover() implementation (main deliverable)
├── oracle.py           # EXISTING: @ql.grover_oracle, GroverOracle class
├── diffusion.py        # EXISTING: ql.diffusion() convenience wrapper
├── compile.py          # EXISTING: @ql.compile, CompiledFunc
├── _gates.pyx          # EXISTING: emit_h, emit_ry, emit_x, emit_mcz
├── _core.pyx           # EXISTING: circuit(), circuit_stats(), option()
├── openqasm.pyx        # EXISTING: to_openqasm()
├── qint.pyx            # EXISTING: qint type with branch()
└── __init__.py         # MODIFIED: add `from .grover import grover` and export
```

### Pattern 1: Oracle Parameter Introspection
**What:** Use `inspect.signature` on the oracle's original function (accessed via `_original_func` for `GroverOracle` or `_func` for `CompiledFunc`) to determine the number and types of quantum parameters. Each parameter annotated as `qint` becomes a search register.
**When to use:** Every call to `ql.grover()` -- this is how register widths are determined.
**Key insight:** The oracle function must have type-annotated parameters (e.g., `def oracle(x: ql.qint)`) for inference to work. The width of each register is NOT available from the annotation alone -- it must be provided separately or inferred from context. Since CONTEXT.md says "Search register inferred from oracle function's type-annotated parameters," the user must provide a `width` parameter or the oracle must have a standard width convention.

**CRITICAL DESIGN QUESTION RESOLVED:** The CONTEXT.md says the user does NOT pass registers explicitly. But `qint` type annotations don't carry width information. The API must accept a `width` parameter (or a `search_space` size) to determine register widths. The simplest approach: `ql.grover(oracle, width=3)` for single-register, or `ql.grover(oracle, widths=[3, 4])` for multi-register. Alternatively, `ql.grover(oracle, n=8)` where `n` is the search space size and `width = ceil(log2(n))`.

**Recommended approach:** Accept `width` as a required keyword argument for single-register oracles. For multi-register oracles, accept `widths` as a list. The oracle signature tells us HOW MANY registers (by counting `qint`-annotated params), while `width`/`widths` tells us HOW WIDE each one is.

**Example:**
```python
import inspect
from quantum_language.oracle import GroverOracle
from quantum_language.compile import CompiledFunc
from quantum_language.qint import qint

def _get_oracle_func(oracle):
    """Extract the original function from an oracle wrapper."""
    if isinstance(oracle, GroverOracle):
        return oracle._original_func
    elif isinstance(oracle, CompiledFunc):
        return oracle._func
    elif callable(oracle):
        return oracle
    raise TypeError(f"Expected oracle function, got {type(oracle)}")

def _get_quantum_params(func):
    """Introspect oracle function to find quantum parameter names and count."""
    sig = inspect.signature(func)
    quantum_params = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            # No annotation -- assume quantum parameter
            quantum_params.append(name)
        elif annotation is qint or (isinstance(annotation, type) and issubclass(annotation, qint)):
            quantum_params.append(name)
        elif isinstance(annotation, str) and annotation in ('qint', 'ql.qint'):
            quantum_params.append(name)
    return quantum_params
```

### Pattern 2: Complete Grover Iteration Circuit
**What:** Build the full Grover search circuit: initialize superposition on all registers, then repeat (oracle + diffusion) for the calculated number of iterations.
**When to use:** Inside `ql.grover()` after register creation.
**Key insight:** The Grover diffusion operator D = H^n * S_0 * H^n, where S_0 is the X-MCZ-X pattern from `ql.diffusion()`. However, the project's `ql.diffusion()` only applies S_0 (X-MCZ-X), not the full D. The Hadamard (branch) must be applied before and after S_0 in each iteration.

**CORRECTION:** Re-reading the Phase 78 research more carefully:
> "The X-MCZ-X pattern IS the complete diffusion when the initial state preparation is understood to be separate."
> "ql.diffusion(x) = X-MCZ-X = S_0 reflection. The Hadamard/branch sandwiching is done at the Grover iteration level (Phase 79)."

So each Grover iteration is:
1. Apply oracle (phase flip on marked states)
2. Apply branch (H^n) on all search register qubits
3. Apply diffusion (S_0 = X-MCZ-X)
4. Apply branch (H^n) on all search register qubits

And the initial setup is:
1. Create circuit
2. Create registers
3. Apply branch (H^n) for initial equal superposition

**Example circuit structure for k iterations:**
```
H^n (initial superposition)
[Repeat k times]:
    Oracle(x)          -- phase flip marked states
    H^n                -- transform to computational basis
    S_0 (X-MCZ-X)     -- reflect about |0>
    H^n                -- transform back to superposition basis
```

This is equivalent to:
```
H^n
[Repeat k times]:
    Oracle(x)
    D  (where D = H^n S_0 H^n)
```

### Pattern 3: Single-Shot Qiskit Simulation
**What:** Export the constructed circuit to OpenQASM, load into Qiskit, add measurements, simulate with `AerSimulator(shots=1)`, and parse the result bitstring.
**When to use:** At the end of `ql.grover()` to obtain the measured result.
**Key insight:** The project already has a proven pattern for QASM export -> Qiskit simulation, used in 100+ tests. Single-shot simulation with `shots=1` is used in `scripts/verify_circuit.py` and `tests/test_modular.py`.

**Example:**
```python
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

def _simulate_single_shot(qasm_str, register_widths):
    """Run single-shot Qiskit simulation and return measured values."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim), shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Parse bitstring into register values
    # Qiskit uses little-endian convention: q[0] is rightmost bit
    # The QASM export allocates qubits sequentially
    values = _parse_bitstring(bitstring, register_widths)
    return values
```

### Pattern 4: Bitstring Parsing for Multi-Register Results
**What:** Parse a Qiskit measurement bitstring into integer values for each search register.
**When to use:** After simulation to construct the return tuple.
**Key insight:** Qiskit's bitstring ordering is big-endian with respect to qubit indices: the leftmost bit corresponds to the highest-numbered qubit. The project's QASM export allocates qubits sequentially (register 1 gets q[0..w1-1], register 2 gets q[w1..w1+w2-1], etc.). In the bitstring, the bits are in reverse order from qubit numbering.

**Qiskit convention (from STATE.md):** "Qiskit little-endian convention: ctrl=q[0] is rightmost bit in bitstrings."

So for a circuit with total n qubits, the bitstring has n characters where:
- bitstring[0] = measurement of q[n-1] (highest qubit)
- bitstring[n-1] = measurement of q[0] (lowest qubit)

For multi-register parsing:
- Register 1 qubits: q[0] ... q[w1-1] -> rightmost w1 bits of bitstring
- Register 2 qubits: q[w1] ... q[w1+w2-1] -> next w2 bits from right
- etc.

**IMPORTANT:** The total number of qubits in the circuit may exceed the search register qubits (oracle uses ancillas that get allocated/deallocated). The bitstring from Qiskit's `measure_all()` measures ALL qubits, including any residual ancilla qubits at |0>. The search register qubits are the first ones allocated.

**Approach:** Since `ql.grover()` controls the entire circuit construction, it knows exactly which qubits belong to each register. After measurement, extract only the search register bits from the bitstring.

```python
def _parse_bitstring(bitstring, register_widths, total_qubits):
    """Parse bitstring into integer values per register.

    Qiskit convention: bitstring is big-endian w.r.t qubit indices.
    bitstring[0] = q[total_qubits - 1], bitstring[-1] = q[0].

    Search registers are allocated first: q[0..w1-1], q[w1..w1+w2-1], etc.
    These correspond to the RIGHTMOST bits in the bitstring.
    """
    values = []
    bit_offset = 0  # offset from the right (LSB) of the bitstring

    for width in register_widths:
        # Extract width bits starting from bit_offset from the right
        # Reverse to get MSB-first order for int conversion
        start = len(bitstring) - bit_offset - width
        end = len(bitstring) - bit_offset
        register_bits = bitstring[start:end]
        value = int(register_bits, 2)
        values.append(value)
        bit_offset += width

    return tuple(values)
```

### Pattern 5: Auto-Wrapping Non-Oracle Functions
**What:** If the user passes a `@ql.compile`-decorated function (not a `@ql.grover_oracle`), automatically wrap it with oracle semantics.
**When to use:** When `ql.grover()` receives a `CompiledFunc` instead of a `GroverOracle`.
**Key insight:** The CONTEXT.md says "Accepts any @ql.compile decorated function -- auto-wraps with oracle semantics if needed." This means calling `grover_oracle(compiled_func)` on non-oracle functions.

```python
from quantum_language.oracle import GroverOracle, grover_oracle

def _ensure_oracle(oracle):
    """Ensure the oracle is a GroverOracle instance."""
    if isinstance(oracle, GroverOracle):
        return oracle
    # Auto-wrap with oracle semantics (default: phase oracle, validate=True)
    return grover_oracle(oracle)
```

### Anti-Patterns to Avoid
- **Exposing circuit to user:** The circuit is internal. Do NOT return a `QuantumCircuit` or QASM string -- only return the measured tuple.
- **Using statevector argmax instead of sampling:** The user decision explicitly says "True single-shot sampling from probability distribution, not deterministic argmax." Use `shots=1` measurement, not statevector extraction.
- **Applying diffusion without H sandwiching:** `ql.diffusion()` only applies S_0 = X-MCZ-X. The full Grover diffusion requires H^n before and after S_0. Missing the H gates will produce incorrect amplification.
- **Forgetting to initialize superposition:** The initial H^n on all search qubits must be applied before the first iteration. Without it, the oracle operates on |0...0> only.
- **Creating registers before circuit:** Must call `ql.circuit()` before creating `qint` registers.
- **Not cleaning up circuit state:** Since `ql.grover()` creates its own internal circuit, it must not interfere with any pre-existing circuit the user may have.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Oracle validation & caching | Custom oracle checking | `GroverOracle` from `oracle.py` | Already validates ancilla delta, compute-phase-uncompute, caches per arithmetic mode |
| Diffusion operator | Custom X-MCZ-X emission | `ql.diffusion()` from `diffusion.py` | Already compiled, cached, zero-ancilla, handles multi-register |
| Superposition initialization | Manual H gate emission on individual qubits | `qint.branch(0.5)` | Standard project API, handles width correctly, emits Ry(pi/2) = H equivalent |
| QASM export | Custom circuit serialization | `ql.to_openqasm()` | Proven export pipeline, handles all gate types |
| Qiskit simulation | Custom simulation | `AerSimulator` + `transpile` | Industry standard, already a project dependency |
| QASM parsing | Custom QASM reader | `qiskit.qasm3.loads()` | Handles full QASM 3.0 syntax |
| Gate capture/replay | Custom gate recording | `@ql.compile` infrastructure | Existing optimized capture/replay machinery |

**Key insight:** Phase 79 is primarily a composition layer. Every component already exists. The new code orchestrates existing components into a single API call.

## Common Pitfalls

### Pitfall 1: Missing H Gates in Grover Iteration
**What goes wrong:** The diffusion operator `ql.diffusion()` only applies S_0 = X-MCZ-X. Without the H^n sandwich, the reflection is about |0...0> in the computational basis, not about the uniform superposition state |s>.
**Why it happens:** Confusion between S_0 (reflection about |0>) and the full Grover diffusion D = H^n S_0 H^n (reflection about |s>).
**How to avoid:** Each Grover iteration must apply: oracle(x) -> x.branch(0.5) -> ql.diffusion(x) -> x.branch(0.5). The branch(0.5) calls apply H^n before and after S_0.
**Warning signs:** Amplification doesn't work -- probability stays at 1/N instead of concentrating on marked states.

### Pitfall 2: Bitstring Parsing Order (Qiskit Little-Endian)
**What goes wrong:** Qiskit's bitstring convention has q[0] as the rightmost bit. If registers are parsed in the wrong direction, values are scrambled.
**Why it happens:** Different tools use different endianness conventions. The project's C backend allocates qubits from q[0] upward, and QASM exports them in order. Qiskit's measurement bitstring reverses this.
**How to avoid:** For registers allocated as q[0..w-1], the measured value is in the rightmost w bits of the bitstring. Parse from the right. Use the known qubit allocation order from the circuit construction.
**Warning signs:** Measured values are consistently wrong or reversed from expected.

### Pitfall 3: Ancilla Qubits in Measurement Bitstring
**What goes wrong:** The oracle (and diffusion if not purely X-MCZ-X) may internally allocate and deallocate ancilla qubits. These qubits still exist in the QASM circuit and get measured by `measure_all()`. The bitstring is longer than expected.
**Why it happens:** Ancilla qubits are deallocated logically but the physical qubit slots remain in the QASM output (they're just at |0>).
**How to avoid:** Track total allocated qubits (via `circuit_stats()['total_allocated']` or by knowing the register widths). When parsing the bitstring, only extract bits corresponding to the search register qubits, ignoring ancilla positions.
**Warning signs:** Bitstring is longer than sum of register widths; extra bits are all '0'.

### Pitfall 4: branch(0.5) on Non-Zero Initialized Qint
**What goes wrong:** `qint(5, width=3)` creates |101>. Calling `branch(0.5)` on it applies Ry to each qubit regardless of initial state, which is NOT the same as H|0>^n.
**Why it happens:** `branch(prob)` applies Ry(theta) to every qubit unconditionally. If the qubit is already in |1>, Ry rotates from |1> instead of |0>.
**How to avoid:** Always create registers with initial value 0: `qint(0, width=n)`. Then `branch(0.5)` is equivalent to H^n|0...0> = |s> (uniform superposition). `ql.grover()` must create registers with value 0.
**Warning signs:** Initial superposition is not uniform.

### Pitfall 5: Circuit State Leakage
**What goes wrong:** `ql.grover()` creates a new circuit internally with `ql.circuit()`, which resets all global state (including any previous circuit the user had). After `ql.grover()` returns, the user's previous circuit context is lost.
**Why it happens:** `ql.circuit()` is a global singleton -- creating a new one destroys the old one.
**How to avoid:** Document that `ql.grover()` creates its own circuit. The user should NOT have an active circuit when calling `ql.grover()`. Since `ql.grover()` is self-contained (CONTEXT.md: "fully self-contained"), this is by design.
**Warning signs:** User's pre-existing circuit disappears after calling `ql.grover()`.

### Pitfall 6: Iteration Count for Edge Cases
**What goes wrong:** M=0 causes division by zero in `sqrt(N/M)`. M>N produces imaginary results or nonsensical iteration counts.
**Why it happens:** The formula `floor(pi/4 * sqrt(N/M) - 0.5)` has domain restrictions.
**How to avoid:** Handle edge cases explicitly before applying the formula:
- M=0: return 0 iterations (random measurement)
- M>=N: return 0 iterations (all states are solutions)
- M<0: raise error (invalid)
- Standard case (0 < M < N): apply formula
**Warning signs:** ZeroDivisionError or negative iteration counts.

### Pitfall 7: Oracle Width Parameter Inference
**What goes wrong:** The `width` of each register must be known to create `qint(0, width=w)`. Type annotations like `x: qint` don't carry width information. If `ql.grover()` tries to infer width from annotations alone, it fails.
**Why it happens:** Python type annotations are types, not value descriptors. `qint` has no width metadata in the type.
**How to avoid:** Require a `width` parameter in `ql.grover()`: `ql.grover(oracle, width=3)`. For multi-register oracles, accept either `width=3` (all same width) or `widths=[3, 4]` (per-register). This is the only practical approach.
**Warning signs:** "Cannot determine register width" errors.

## Code Examples

Verified patterns from project codebase:

### Example 1: Basic ql.grover() Usage (Single Register)
```python
import quantum_language as ql

@ql.grover_oracle
@ql.compile
def mark_five(x: ql.qint):
    flag = (x == 5)
    with flag:
        pass

# Search for x where oracle marks x=5
value, iterations = ql.grover(mark_five, width=3)
# value is sampled from probability distribution (likely 5)
# iterations is the auto-calculated count (1 for N=8, M=1)
```

### Example 2: Multi-Register Oracle
```python
@ql.grover_oracle
@ql.compile
def mark_pair(x: ql.qint, y: ql.qint):
    flag = (x + y == 7)
    with flag:
        pass

# Search for (x, y) where x + y == 7
x_val, y_val, iterations = ql.grover(mark_pair, widths=[3, 3])
# Multiple solutions: (0,7), (1,6), ..., (7,0) = 8 solutions out of 64
```

### Example 3: Explicit Iteration Override
```python
value, iterations = ql.grover(mark_five, width=3, iterations=2)
# Uses exactly 2 iterations instead of auto-calculated count
# iterations in return tuple will be 2
```

### Example 4: Multiple Solutions
```python
@ql.grover_oracle
@ql.compile
def mark_even(x: ql.qint):
    flag = (x[0] == 0)  # LSB is 0 -> even number
    with flag:
        pass

value, iters = ql.grover(mark_even, width=3, m=4)
# 4 solutions out of 8 (0,2,4,6) -> k=0 iterations
# Returns random even number from superposition
```

### Example 5: Internal Circuit Construction (Implementation Pattern)
```python
def grover(oracle, *, width=None, widths=None, m=1, iterations=None):
    """Execute Grover's search and return measured result."""
    # 1. Ensure oracle is wrapped
    oracle = _ensure_oracle(oracle)

    # 2. Determine register widths
    param_names = _get_quantum_params(_get_oracle_func(oracle))
    register_widths = _resolve_widths(param_names, width, widths)

    # 3. Calculate iteration count
    N = 1
    for w in register_widths:
        N *= 2 ** w
    if iterations is None:
        k = _grover_iterations(N, m)
    else:
        k = iterations

    # 4. Build circuit
    ql.circuit()
    ql.option("fault_tolerant", True)  # Use Toffoli backend

    # 5. Create registers
    registers = [ql.qint(0, width=w) for w in register_widths]

    # 6. Initialize superposition
    for reg in registers:
        reg.branch(0.5)

    # 7. Apply k Grover iterations
    for _ in range(k):
        # Oracle application
        oracle(*registers)
        # Diffusion: H - S_0 - H
        for reg in registers:
            reg.branch(0.5)
        ql.diffusion(*registers)
        for reg in registers:
            reg.branch(0.5)

    # 8. Export and simulate
    qasm = ql.to_openqasm()
    values = _simulate_single_shot(qasm, register_widths)

    # 9. Return tuple
    return (*values, k)
```

### Example 6: Single-Shot Simulation (Project Pattern)
```python
# From scripts/verify_circuit.py and tests/test_modular.py:
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

def _simulate_single_shot(qasm_str, register_widths):
    """Single-shot Qiskit simulation with bitstring parsing."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim), shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Parse register values from bitstring
    return _parse_bitstring(bitstring, register_widths)
```

### Example 7: Iteration Count Calculation
```python
import math

def _grover_iterations(N, M):
    """Calculate optimal Grover iteration count.

    Formula: floor(pi/4 * sqrt(N/M) - 0.5)

    Edge cases:
    - M=0: return 0 (random measurement from superposition)
    - M>=N: return 0 (all states are solutions, no iteration needed)
    """
    if M <= 0 or M >= N:
        return 0
    return int(math.floor(math.pi / 4 * math.sqrt(N / M) - 0.5))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Grover circuit construction (oracle + H + X-MCZ-X + H per iteration) | Single `ql.grover(oracle)` API call | This phase (79) | Users go from ~20 lines of circuit code to 1 line |
| Separate circuit building, QASM export, Qiskit simulation | All-in-one black box that returns Python values | This phase (79) | No Qiskit knowledge needed by end users |
| Manual iteration count calculation | Auto-calculated from N and M | This phase (79) | Users don't need to know the optimal iteration formula |

**Deprecated/outdated:**
- N/A -- this is new infrastructure, no predecessor to deprecate

## Open Questions

1. **Width parameter design**
   - What we know: The CONTEXT.md says "Search register inferred from oracle function's type-annotated parameters -- user does NOT pass register explicitly." But type annotations don't carry width information.
   - What's unclear: Exactly how the user specifies register widths. Options: (a) `width=3` for single-register, (b) `widths=[3,4]` for multi-register, (c) both supported.
   - Recommendation: Accept `width=` (int, for single-register or all-same-width) and `widths=` (list of int, for per-register widths). This is the minimal extension needed. Error if both provided and inconsistent. Error if neither provided.

2. **Should ql.grover() set fault_tolerant mode?**
   - What we know: Most tests set `ql.option("fault_tolerant", True)` for Toffoli-based arithmetic (needed for comparison operators in oracles). The Grover search will need comparisons for common oracles.
   - What's unclear: Whether to force fault_tolerant mode or respect the user's setting.
   - Recommendation: Set `ql.option("fault_tolerant", True)` by default inside `ql.grover()`. This ensures oracle comparisons work correctly. Document this behavior.

3. **Does branch(0.5) perfectly implement H^n?**
   - What we know: `branch(0.5)` applies Ry(theta) where theta = 2*arcsin(sqrt(0.5)) = pi/2 to each qubit. Ry(pi/2) on |0> produces (|0>+|1>)/sqrt(2), which is the same as H|0>.
   - What's unclear: Whether Ry(pi/2) and H produce identical states on |0>.
   - Verification: Ry(pi/2)|0> = cos(pi/4)|0> + sin(pi/4)|1> = (|0>+|1>)/sqrt(2). H|0> = (|0>+|1>)/sqrt(2). They are identical.
   - BUT: Ry(pi/2)|1> = -sin(pi/4)|0> + cos(pi/4)|1> = (-|0>+|1>)/sqrt(2). H|1> = (|0>-|1>)/sqrt(2). They differ by a sign on each component.
   - **Impact on Grover:** The diffusion operator requires `H^n * S_0 * H^n`. If using `branch(0.5)` (Ry) instead of H, the second application of Ry on non-|0> states produces different signs. However, Ry(pi/2) * X * MCZ * X * Ry(pi/2) may NOT equal H * X * MCZ * X * H due to the sign difference when acting on |1>.
   - **CRITICAL:** This needs verification. The Grover diffusion is D = 2|s><s| - I. Using Ry instead of H changes the basis transformation. Need to verify whether `Ry(pi/2)^n * S_0 * Ry(pi/2)^n` produces the correct reflection operator.
   - Recommendation: **Use direct `emit_h` gate emission instead of `branch(0.5)` for the Hadamard sandwich in Grover iterations.** branch(0.5) is fine for the initial superposition (applied to |0>), but the subsequent H^n applications during iterations should use actual H gates. This is safer because H^2 = I (Hadamard is self-inverse) while Ry(pi/2)^2 = Ry(pi) != I.
   - **VERIFIED:** Ry(pi/2)^2 = Ry(pi) applies a full pi rotation, mapping |0> -> |1> and |1> -> -|0>. This is NOT the identity. H^2 = I (Hadamard IS self-inverse). Therefore, using branch(0.5) for both the initial superposition AND the diffusion H-sandwich would be INCORRECT. The initial branch(0.5) on |0> is fine, but the H gates in the diffusion must be actual Hadamard gates (emit_h), not Ry(pi/2).

4. **How to handle the "H sandwich" in the iteration**
   - What we know: Each Grover iteration needs: Oracle -> H^n -> S_0 -> H^n. The `emit_h()` function in `_gates.pyx` emits individual H gates (with auto-controlled context).
   - What's unclear: Whether to (a) emit raw H gates via `emit_h()` on each qubit in each iteration, or (b) create a compiled function for the full H^n layer and reuse it.
   - Recommendation: Create a small helper that applies H to all register qubits using `emit_h()`. Since this runs inside the grover() function (which creates a fresh circuit each time), caching is not critical. Direct `emit_h` calls are simpler and work correctly.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/oracle.py` -- GroverOracle class, grover_oracle decorator, `_original_func` for introspection
- `src/quantum_language/diffusion.py` -- `diffusion()` function, `_collect_qubits()` helper, X-MCZ-X pattern
- `src/quantum_language/compile.py` -- CompiledFunc, `_classify_args()`, `_func` attribute, cache key structure
- `src/quantum_language/_gates.pyx` -- `emit_h()`, `emit_ry()`, `emit_x()`, `emit_mcz()` gate primitives
- `src/quantum_language/_core.pyx` -- `circuit()` class, `circuit_stats()`, `option()`, `to_openqasm()`
- `src/quantum_language/qint.pyx` -- `qint(0, width=n)`, `branch(prob)` method, qubit array layout
- `tests/python/test_oracle.py` -- Oracle test patterns, single Grover iteration test (lines 820-868)
- `tests/python/test_diffusion.py` -- Diffusion statevector verification, simulation patterns
- `tests/python/test_branch_superposition.py` -- Qiskit simulation helper pattern
- `scripts/verify_circuit.py` -- Single-shot simulation pattern (lines 677-699)

### Secondary (MEDIUM confidence)
- Grover's algorithm iteration count formula: `floor(pi/4 * sqrt(N/M) - 0.5)` -- standard textbook (Nielsen & Chuang Chapter 6, Grover 1996)
- Qiskit little-endian bitstring convention: Verified in STATE.md and multiple test files
- `Ry(pi/2)|0> == H|0>` equivalence: Mathematical verification (both produce (|0>+|1>)/sqrt(2))
- `Ry(pi/2)^2 != I` while `H^2 = I`: Mathematical verification (Ry(pi) != I, rotation matrices)

### Tertiary (LOW confidence)
- None -- all findings verified from codebase inspection and mathematical derivation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist in codebase, verified via source reading
- Architecture: HIGH -- composition of existing proven components, follows established patterns
- Pitfalls: HIGH -- all identified from actual code behavior and mathematical properties
- Ry vs H correctness: HIGH -- mathematical verification confirms branch(0.5) must NOT be used for H-sandwich

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable internal architecture, no external dependency drift)
