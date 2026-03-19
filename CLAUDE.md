## Required Reading

Before starting any implementation work, **scan these files** for context:

- `docs/PRD.md` — Product requirements for the call-graph-only execution model
- `docs/IMPLEMENTATION_PLAN.md` — 8-module implementation plan with dependencies, file changes, and tests
- `AGENTS.md` — Workflow rules, issue tracking with bd (beads), and session completion checklist

Use **bd (beads)** for all task tracking. Run `bd ready --json` to see available work. See `AGENTS.md` for full bd workflow.

---

# Claude Code Project Instructions

## Quantum Assembly Programming Guide

This is a quantum programming framework. You write quantum algorithms using **normal Python constructs** — arithmetic operators, comparisons, `with` blocks — and the framework compiles them to quantum circuits automatically. **You never touch gates directly.**

### Core Principle

Think of `qint` like a regular integer that happens to be in superposition. Use `+`, `-`, `*`, `==`, `<`, `with`, etc. The framework handles all gate generation, qubit allocation, and uncomputation internally.

### What NOT To Do

**NEVER do any of these:**

```python
# WRONG: Do not import or use gates directly
from quantum_language import X, H, CNOT, CX, Toffoli  # These don't exist as public API
ql.circuit().add_gate(...)        # Never manipulate gates manually
ql.circuit().add_qubits(...)      # Never allocate qubits manually

# WRONG: Do not use Qiskit/Cirq/other framework patterns
from qiskit import QuantumCircuit  # Not how this framework works
qc.h(0)                           # No manual gate application
qc.cx(0, 1)                       # No manual entanglement

# WRONG: Do not try to access quantum state directly
value = my_qint.get_state()       # Violates no-cloning theorem
bits = my_qint.read_bits()        # Not possible

# WRONG: Do not manually manage qubit indices
qubit_0 = 0                       # Framework manages qubit allocation
ql.circuit().apply_x(qubit_0)     # No direct qubit manipulation
```

**The framework is a DSL, not a gate library.** If you find yourself thinking about individual gates, you're using it wrong.

### Types

```python
import quantum_language as ql

# Quantum integer (1-64 bits, auto-width from value)
x = ql.qint(0, width=4)       # 4-bit quantum integer, initialized to 0
y = ql.qint(5)                 # auto-width: 3 bits (minimum for value 5)
z = ql.qint(5, width=8)        # 8-bit, initialized to 5

# Quantum boolean (1-bit)
b = ql.qbool()                 # quantum boolean

# Quantum array
arr = ql.qarray([1, 2, 3], width=4)          # array of 4-bit qints
flags = ql.qarray([0, 0, 0], dtype=ql.qbool) # array of qbools
board = ql.qarray(dim=(8, 8), dtype=ql.qbool) # 2D array (e.g., chess board)
```

### Arithmetic (works like normal Python)

```python
a = ql.qint(5, width=8)
b = ql.qint(3, width=8)

c = a + b          # addition
d = a - b          # subtraction (two's complement)
e = a * b          # multiplication
q = a // 3         # integer division (classical divisor only)
r = a % 3          # modulo (classical divisor only)

a += 1             # in-place augmented assignment
a -= b
a *= 2

# Bitwise
f = a & b          # AND
g = a | b          # OR
h = a ^ b          # XOR
i = ~a             # NOT
a <<= 2            # left shift
```

### Comparisons (return qbool)

```python
eq = (a == b)      # equality -> qbool
ne = (a != b)      # not equal
lt = (a < b)       # less than
gt = (a > b)       # greater than
le = (a <= b)      # less or equal
ge = (a >= b)      # greater or equal

# Use comparisons with classical values too
is_five = (a == 5)
```

### Quantum Conditionals (`with` blocks)

```python
# "with qbool:" means: execute the body controlled on that qbool being True
cond = (a > 3)
with cond:
    b += 1         # only happens when a > 3 (in superposition)
```

### Function Compilation (`@ql.compile`)

```python
@ql.compile
def add_values(x, y):
    x += y
    return x

# First call: captures gates. Subsequent calls: replays cached gates.
a = ql.qint(3, width=4)
b = ql.qint(2, width=4)
result = add_values(a, b)

# With inverse support (for oracles, uncomputation):
@ql.compile(inverse=True)
def prepare(x):
    x += 5
    return x

# prepare.inverse(x) undoes the operation
```

### Grover's Search (Complete Example)

This is the typical workflow for finding a value satisfying some condition:

```python
import quantum_language as ql

# Simple: find x where x == 5 in a 3-bit search space
value, iterations = ql.grover(lambda x: x == 5, width=3, m=1)
# Returns: (5, 1)

# Compound predicate: find x where 2 < x < 6
value, iterations = ql.grover(lambda x: (x > 2) & (x < 6), width=3)

# Unknown number of solutions (adaptive BBHT search):
result = ql.grover(lambda x: x > 5, width=4)
# Returns (value, iterations) or None

# Multi-register search:
result = ql.grover(lambda x, y: x + y == 10, widths=[4, 4])
```

### Amplitude Estimation & Counting

```python
# Estimate probability that a random x satisfies predicate
result = ql.amplitude_estimate(lambda x: x == 5, width=3, epsilon=0.05)
print(result.estimate)  # ~0.125 (1/8 for 3-bit space)

# Count number of solutions
count = ql.count_solutions(lambda x: x > 5, width=3, epsilon=0.05)
print(count.count)  # 2 (values 6 and 7)
```

### Circuit Output

```python
# Get circuit statistics
stats = ql.circuit_stats()

# Export to OpenQASM 3.0
qasm_str = ql.to_openqasm()

# Pixel-art visualization (requires Pillow)
img = ql.draw_circuit()
img.save("circuit.png")
```

### Configuration Options

```python
ql.option('fault_tolerant', True)      # Toffoli-based arithmetic (default)
ql.option('fault_tolerant', False)     # QFT-based arithmetic
ql.option('qubit_saving', True)        # Eager uncomputation of intermediates
ql.option('toffoli_decompose', True)   # Decompose CCX to Clifford+T gates
ql.option('tradeoff', 'min_depth')     # Use carry look-ahead adder
ql.option('tradeoff', 'min_qubits')   # Use ripple-carry (fewer qubits)
```

### Important Rules for Writing Algorithms

1. **Do not call `ql.circuit()`** -- it resets all state including options; the framework initializes automatically
2. **Never import gates** -- use arithmetic operators and comparisons only
3. **`with qbool:` is your conditional** -- it controls operations in superposition
4. **Use `@ql.compile`** for any function you call more than once (caches gate sequences)
5. **Use `@ql.compile(inverse=True)`** when you need to undo an operation (oracles, uncomputation)
6. **Comparisons return qbool**, not classical bool -- use them in `with` blocks
7. **`&` between qbools is Toffoli AND**, not classical and -- use it for compound conditions
8. **Division/modulo only works with classical divisors** (`a // 3` works, `a // b` doesn't for general b)
9. **Max simulation size: 21 qubits** -- keep test circuits small

---

## Development Notes

- Always read relevant files before making changes
- Run tests after making modifications: `pytest tests/python/ -v`
- Follow existing code style (C: LLVM style, Python: PEP 8)
- The C backend is in `Backend/src/`, Python frontend in `src/quantum_language/`
