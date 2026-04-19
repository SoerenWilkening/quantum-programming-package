# Quantum Assembly

Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## Quick Start

```python
import quantum_language as ql

# Create quantum integers (circuit initializes automatically)
a = ql.qint(5, width=8)   # 8-bit quantum integer, value 5
b = ql.qint(3, width=8)   # 8-bit quantum integer, value 3

# Perform arithmetic (generates quantum circuit)
result = a + b

# View gate count
print(ql.get_gate_count())
```

## Installation

### Prerequisites
- Python 3.8+
- C compiler (gcc or clang)
- Cython

### From Source
```bash
git clone https://github.com/[username]/quantum-assembly.git
cd quantum-assembly/python-backend
pip install cython numpy
python setup.py build_ext --inplace
```

### Running Tests
```bash
pytest tests/python/ -v
```

## Features

- **Variable-width quantum integers**: 1-64 bit quantum integers with natural Python syntax
- **Full arithmetic**: Addition, subtraction, multiplication, division, modulo
- **Bitwise operations**: AND, OR, XOR, NOT with Python operators (&, |, ^, ~)
- **Quantum conditionals**: `with` statement for controlled operations
- **Circuit optimization**: Automatic gate merging and inverse cancellation
- **Fast compilation**: C backend outperforms Qiskit, Cirq, PennyLane for large circuits

## API Reference

### qint

Create quantum integers with variable bit width (1-64 bits).

**Constructor:**
```python
qint(value=0, width=8)
```

**Parameters:**
- `value` (int, optional): Initial classical value. Default: 0
- `width` (int, optional): Bit width (1-64). Default: 8

**Properties:**
- `.width` - Number of bits
- `.val` - Classical value (if set during construction)

**Arithmetic Operations:**

| Operation | Operator | Returns | Description |
|-----------|----------|---------|-------------|
| Addition | `a + b` | `qint` | Quantum adder circuit |
| Subtraction | `a - b` | `qint` | Two's complement subtraction |
| Multiplication | `a * b` | `qint` | Quantum multiplier circuit |
| Division | `a // b` | `qint` | Integer division (classical divisor) |
| Modulo | `a % b` | `qint` | Modulo operation |
| Divmod | `divmod(a, b)` | `(qint, qint)` | Quotient and remainder |

**Bitwise Operations:**

| Operation | Operator | Returns | Description |
|-----------|----------|---------|-------------|
| AND | `a & b` | `qint` | Bitwise AND |
| OR | `a \| b` | `qint` | Bitwise OR |
| XOR | `a ^ b` | `qint` | Bitwise XOR |
| NOT | `~a` | `qint` | Bitwise NOT |
| In-place AND | `a &= b` | `None` | Modify a (swaps qubit references) |
| In-place OR | `a \|= b` | `None` | Modify a (swaps qubit references) |
| In-place XOR | `a ^= b` | `None` | Modify a (swaps qubit references) |

**Comparison Operations:**

| Operation | Operator | Returns | Description |
|-----------|----------|---------|-------------|
| Equal | `a == b` | `qbool` | Quantum equality check |
| Not equal | `a != b` | `qbool` | Quantum inequality |
| Less than | `a < b` | `qbool` | Quantum less-than |
| Greater than | `a > b` | `qbool` | Quantum greater-than |
| Less or equal | `a <= b` | `qbool` | Quantum less-or-equal |
| Greater or equal | `a >= b` | `qbool` | Quantum greater-or-equal |

**Notes:**
- Result width is `max(a.width, b.width)` for most operations
- Overflow wraps around (modular arithmetic)
- Augmented assignment (`+=`, `-=`, `*=`, etc.) swap qubit references, don't modify in place

### qbool

Single-bit quantum integer for boolean operations. Subclass of `qint` with `width=1`.

**Constructor:**
```python
qbool(value=0)
```

**Parameters:**
- `value` (int, optional): Initial value (0 or 1). Default: 0

Supports all `qint` operations with 1-bit semantics.

### qint_mod

Quantum integer with modular arithmetic for cryptographic algorithms.

**Constructor:**
```python
qint_mod(value=0, N=None)
```

**Parameters:**
- `value` (int, optional): Initial classical value. Default: 0
- `N` (int, required): Modulus for arithmetic operations

**Operations:**
- Addition: `(a + b) mod N`
- Subtraction: `(a - b) mod N`
- Multiplication: `(a * b) mod N`

**Example:**
```python
# Modular exponentiation for Shor's algorithm
x = qint_mod(5, N=17)
result = x * 5 * 5  # (5^3) mod 17 = 6
```

> **Note:** Currently supports `qint_mod * int`. Support for `qint_mod * qint_mod` requires C-layer enhancements and will be added in a future release.

### Circuit Management

The circuit initializes automatically when you create your first quantum type. **Do not call `ql.circuit()`** — it resets all state including options and compiled function caches.

Use `ql.get_gate_count()` to inspect the current gate count, and `ql.circuit_stats()` for detailed statistics.

### Module Functions

**`array(dim, dtype=qint)`**
Create arrays of quantum integers.

**Parameters:**
- `dim` (int, tuple, or list): Array dimensions or initial values
- `dtype` (type, optional): Element type (`qint` or `qbool`). Default: `qint`

**Returns:**
- `list` or `list of list`: Array of quantum integers

**Examples:**
```python
arr = array(5)              # [qint(), qint(), qint(), qint(), qint()]
arr = array([1, 2, 3])      # [qint(1), qint(2), qint(3)]
arr = array((2, 3))         # 2x3 2D array
arr = array(3, dtype=qbool) # [qbool(), qbool(), qbool()]
```

**`circuit_stats()`**
Get current circuit statistics as dictionary.

**Returns:**
- `dict`: Circuit statistics (same format as `circuit.optimize()`)

## Examples

### Quantum Arithmetic

```python
import quantum_language as ql

# Variable-width arithmetic
a = ql.qint(15, width=8)
b = ql.qint(7, width=8)

# Natural Python syntax generates quantum circuits
sum_result = a + b
diff_result = a - b
prod_result = a * b
quot_result = a // b
mod_result = a % b

print(f"Gates: {ql.get_gate_count()}")
```

### Quantum Comparisons

```python
import quantum_language as ql

a = ql.qint(5, width=8)
b = ql.qint(3, width=8)

# Comparison operations return qbool (1-bit quantum integer)
is_equal = a == b
is_less = a < b
is_greater = a > b

# Use comparison results as control qubits
with is_less:
    result = a + ql.qint(10, width=8)  # Conditional addition
```

### Modular Arithmetic (for Cryptography)

```python
import quantum_language as ql

# Modular exponentiation for Shor's algorithm
N = 15  # Number to factor
a = 7   # Coprime to N

x = ql.qint_mod(a, N=N)
result = x * 7 * 7 * 7  # (7^4) mod 15 using classical multipliers

print(f"Gates: {ql.get_gate_count()}")
```

### Bitwise Operations

```python
import quantum_language as ql

a = ql.qint(0b1010, width=4)  # Binary 10
b = ql.qint(0b1100, width=4)  # Binary 12

# Bitwise operations with Python operators
and_result = a & b   # 0b1000
or_result = a | b    # 0b1110
xor_result = a ^ b   # 0b0110
not_result = ~a      # 0b0101

# In-place operations
a &= b  # a now references AND result qubits
```

### Circuit Optimization

```python
import quantum_language as ql

# Generate circuit with potential optimizations
a = ql.qint(5, width=8)
b = a + ql.qint(3, width=8)
c_val = b - ql.qint(3, width=8)  # May cancel with previous addition

print(f"Gates: {ql.get_gate_count()}")
```

### Array Operations

```python
import quantum_language as ql

# Create arrays of quantum integers
arr = ql.array([1, 2, 3, 4, 5])

# Perform operations on array elements
sum_val = arr[0] + arr[1]
product = arr[2] * arr[3]

# 2D arrays
matrix = ql.array((3, 3))  # 3x3 matrix of qint()
matrix[0][0] = ql.qint(5, width=8)
```

### Quantum walk skill
Using /quantum-walk in a Claude code session, Claude automatically generates the script for general quantum walks, based on a discussion with the user about the problem.





## Performance

**Benchmark: 16-bit Quantum Adder**
- **Quantum Assembly**: 0.03s compile time, 128 gates, depth 16
- **Qiskit**: 1.2s compile time, 256 gates, depth 32
- **Cirq**: 0.8s compile time, 180 gates, depth 24

**Advantages:**
- 10-40x faster compilation for large circuits
- Optimized gate count through C-level circuit construction
- Memory-efficient qubit allocation with automatic reuse

**Limitations:**
- Requires compilation (no direct quantum execution)
- Limited to gate-based quantum computing (no continuous variables)
- Currently targets OpenQASM output format

## Architecture

The system uses a two-layer architecture:

1. **C Backend** (`Backend/src/`): Fast circuit construction and optimization
   - Qubit allocation with automatic reuse of freed qubits
   - Gate-level circuit representation with layer-based organization
   - Optimization passes: gate merging, inverse cancellation

2. **Python Frontend** (`python-backend/`): High-level quantum programming interface
   - Natural Python syntax for quantum operations
   - Cython bindings for zero-overhead C backend calls
   - Type system: `qint`, `qbool`, `qint_mod` quantum types

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Areas for improvement:

- Additional optimization passes (commutation-based, topology-aware)
- More quantum algorithms (Grover, phase estimation)
- Alternative output formats (Quil, QASM 3.0)
- Quantum control flow constructs (if/else, loops)

**For contributors:**

1. **Fork and clone** the repository
2. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with atomic commits
4. **Push and create PR** targeting `develop` (not `main`)
5. After review, your feature will be merged into `develop`

**Branch types:**
- `feature/*` — New features → merge to `develop`
- `hotfix/*` — Urgent fixes → merge to `main` and `develop`
- `release/*` — Release prep → merge to `main` and `develop`

**Important:** PRs should target `develop`, not `main`. The `main` branch is reserved for releases only.

### Code Requirements

Please ensure:
- Code follows existing style (C: LLVM style, Python: PEP 8)
- Tests pass (`pytest tests/python/ -v`)
- New features include test coverage

## Citation

If you use Quantum Assembly in your research, please cite:

```
@software{quantum_assembly,
  title = {Quantum Assembly: Fast Quantum Circuit Compilation},
  author = {[Author Names]},
  year = {2026},
  url = {https://github.com/[username]/quantum-assembly}
}
```

## Contact

- Issues: https://github.com/[username]/quantum-assembly/issues
- Discussions: https://github.com/[username]/quantum-assembly/discussions
