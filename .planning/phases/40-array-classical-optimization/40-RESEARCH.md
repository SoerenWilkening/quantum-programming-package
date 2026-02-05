# Phase 40: Array Classical Optimization - Research

**Researched:** 2026-02-02
**Domain:** Cython/quantum circuit optimization for array element-wise operations with classical values
**Confidence:** HIGH

## Summary

This phase optimizes array element-wise operations with classical (int/list) operands to use direct `CQ_*` C backend calls instead of creating temporary `qint` objects. The current implementation in `qarray.pyx` delegates all operations through Python-level lambdas (e.g., `lambda a, b: a + b`) which invoke `qint.__add__`, `qint.__and__`, etc. For classical operands, these qint methods already internally call the correct `CQ_*` functions -- but they first allocate temporary qint objects that are unnecessary overhead.

The optimization is purely internal to `qarray.pyx`. It bypasses the qint operator dispatch for classical operands and calls the C backend `CQ_*` functions directly on each element's qubits, eliminating temporary qint allocations per element per operation.

**Primary recommendation:** Add specialized code paths in `qarray.pyx` for classical operands (int and list-of-int) that call `CQ_add`, `CQ_and`, `CQ_or`, `CQ_mul` directly, following the exact same qubit layout and calling conventions already used in `qint.pyx`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | (project version) | Compile qarray.pyx to C extension | Already used for all quantum_language modules |
| C backend (`_core.pxd`) | N/A | Provides `CQ_add`, `CQ_and`, `CQ_or`, `CQ_mul`, `run_instruction` | Already declared and used by qint.pyx |

### Available CQ_* Functions

| Function | Declared In | Signature | Purpose |
|----------|-------------|-----------|---------|
| `CQ_add` | `_core.pxd` (arithmetic_ops.h) | `CQ_add(int bits, long long value)` | Classical-quantum addition |
| `CQ_mul` | `_core.pxd` (arithmetic_ops.h) | `CQ_mul(int bits, long long value)` | Classical-quantum multiplication |
| `CQ_and` | `_core.pxd` (bitwise_ops.h) | `CQ_and(int bits, int64_t value)` | Classical-quantum AND |
| `CQ_or` | `_core.pxd` (bitwise_ops.h) | `CQ_or(int bits, int64_t value)` | Classical-quantum OR |
| **NO** `CQ_xor` | N/A | N/A | Does not exist in C backend |
| **NO** `CQ_sub` | N/A | N/A | Subtraction uses `CQ_add` with `invert=True` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct CQ_* calls in qarray | Keep current lambda dispatch | Current approach works correctly, just slower (temp qint per element) |
| Batch all elements into single C call | Per-element CQ_* calls | Batch not feasible -- each qint has different qubit indices |

## Architecture Patterns

### Current Code Flow (Unoptimized)

```
qarray.__add__(self, int_value)
  -> _elementwise_binary_op(int_value, lambda a, b: a + b)
    -> for each element:
         lambda(qint_elem, int_value)
           -> qint.__add__(self, int_value)
             -> temp = qint(value=self.value, width=result_width)  # TEMP ALLOCATION
             -> temp += int_value
               -> addition_inplace(int_value)
                 -> CQ_add(self.bits, int_value)  # actual work
             -> return temp
```

### Optimized Code Flow

```
qarray.__add__(self, int_value)
  -> _elementwise_classical_add(int_value)
    -> for each element:
         result_qint = qint(width=self._width)  # allocate result only
         # Copy element qubits to result via Q_xor (or CNOT pattern)
         # Call CQ_add(bits, int_value) directly on result qubits
         # No temporary qint created for the classical value
```

### Pattern 1: Direct CQ_* Call for In-Place Operations

**What:** For `qarray += int_value`, call `CQ_add` directly on each element's qubits without creating a temp qint.
**When to use:** In-place arithmetic/bitwise with int scalar or int list.

The pattern from `qint.addition_inplace` (lines 685-745 of `qint.pyx`):
```python
# Extract qubits for this element
self_offset = 64 - self.bits
qubit_array[:self.bits] = self.qubits[self_offset:64]
start = self.bits

# Ancilla setup
qubit_array[start: start + NUMANCILLY] = _get_ancilla()

# Call CQ_add directly
seq = CQ_add(self.bits, classical_value)
arr = qubit_array
run_instruction(seq, &arr[0], False, _circuit)
```

### Pattern 2: Direct CQ_* Call for Out-of-Place Operations

**What:** For `qarray + int_value`, allocate result qint, copy source qubits, then apply CQ_* on result.
**When to use:** Out-of-place ops that produce new qarray.

For addition: The current `qint.__add__` does `temp = qint(value=self.value, width=w); temp += other`. The optimization can do the same but skip the lambda overhead. However, the real savings are in the in-place path where temp qint creation for the classical value itself is eliminated.

### Pattern 3: Bitwise CQ_* Calls (AND, OR)

**What:** For `qarray & int_value`, use `CQ_and` directly. Same for OR.
**When to use:** Bitwise ops with classical scalar.

The pattern from `qint.__and__` (lines 1067-1178 of `qint.pyx`):
```python
# CQ_and expects: [0:bits] = output, [bits:2*bits] = quantum operand
result = qint(width=result_bits)
result_offset = 64 - result_bits
self_offset = 64 - self.bits

qubit_array[:result_bits] = result.qubits[result_offset:64]
qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
# Zero-extend if needed

seq = CQ_and(result_bits, classical_value)
arr = qubit_array
run_instruction(seq, &arr[0], False, _circuit)
```

### Pattern 4: XOR with Classical Value (No CQ_xor)

**What:** XOR with classical value uses X gates (Q_not) per bit, not a single CQ call.
**When to use:** `qarray ^ int_value`.

From `qint.__xor__` (lines 1433-1453):
```python
# No CQ_xor exists. Apply X gate for each 1-bit in classical value
for i in range(result_bits):
    if (other >> i) & 1:
        qubit_array[0] = result.qubits[64 - result_bits + i]
        arr = qubit_array
        seq = Q_not(1)
        run_instruction(seq, &arr[0], False, _circuit)
```

### Anti-Patterns to Avoid

- **Don't create CQ_xor or CQ_sub**: These don't exist in the C backend. XOR uses X gates; subtraction uses `CQ_add` with `invert=True`.
- **Don't change qint operator methods**: This optimization is entirely in `qarray.pyx`. The qint class methods must remain unchanged.
- **Don't skip qubit layout correctness**: Each CQ_* function has specific qubit array layout requirements (output region, operand region, ancilla region). These must be followed exactly.
- **Don't forget the `invert` parameter for subtraction**: `CQ_add` with `invert=True` performs subtraction. The `run_instruction` call takes `invert` as 3rd parameter.
- **Don't forget ancilla qubits**: `CQ_add` and `CQ_mul` need `NUMANCILLY` ancilla qubits appended to the qubit array. `CQ_and` and `CQ_or` do not.
- **Don't forget padding qints for AND/OR**: When `self.bits < result_bits`, padding ancilla must be allocated before the result (see qint.__and__ for the pattern).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Classical-quantum addition | Custom gate sequences | `CQ_add(bits, value)` | C backend handles QFT-based addition correctly |
| Classical-quantum multiplication | Custom gate sequences | `CQ_mul(bits, value)` | Complex shift-add circuit in C backend |
| Classical-quantum AND | Custom Toffoli patterns | `CQ_and(bits, value)` | Correct ancilla management in C backend |
| Classical-quantum OR | Custom gate patterns | `CQ_or(bits, value)` | Handles De Morgan's correctly in C backend |
| Classical XOR | New CQ_xor function | X gate loop (existing pattern) | Simple bit-flip pattern, no new C code needed |
| Subtraction | New CQ_sub function | `CQ_add` with `invert=True` | Inverse QFT addition is subtraction |

**Key insight:** All the C backend infrastructure already exists. The optimization is purely about eliminating Python-level overhead (temporary qint allocations and lambda dispatch) in the array loop.

## Common Pitfalls

### Pitfall 1: Qubit Array Layout Mismatch
**What goes wrong:** CQ_* functions expect specific qubit layouts. Getting the order wrong produces incorrect circuits.
**Why it happens:** Different operations have different layouts:
  - `CQ_add`: `[target_qubits, ancilla]`
  - `CQ_and`/`CQ_or`: `[output_qubits, source_qubits, (padding)]`
  - `CQ_mul`: `[result_qubits, source_qubits, ancilla]`
**How to avoid:** Copy the exact qubit setup from the corresponding `qint.__iadd__`, `qint.__and__`, etc. methods. Do not innovate on layout.
**Warning signs:** Wrong computation results; segfaults in C backend.

### Pitfall 2: Missing Ancilla Qubits
**What goes wrong:** `CQ_add` and `CQ_mul` need ancilla qubits appended after operand qubits.
**Why it happens:** Easy to forget that `_get_ancilla()` returns indices to shared ancilla qubits that must be in the qubit_array.
**How to avoid:** Always include `qubit_array[start: start + NUMANCILLY] = _get_ancilla()` for add/mul.
**Warning signs:** Segfault or memory corruption.

### Pitfall 3: Forgetting cimport for C Functions
**What goes wrong:** `qarray.pyx` currently does not cimport `CQ_add`, `CQ_and`, etc. from `_core`.
**Why it happens:** These are only cimported in `qint.pyx` currently.
**How to avoid:** Add necessary cimports to `qarray.pyx`:
```python
from ._core cimport (
    CQ_add, CQ_mul, CQ_and, CQ_or,
    sequence_t, circuit_t, circuit_s,
    run_instruction, Q_not, Q_xor,
    NUMANCILLY, INTEGERSIZE,
    qubit_allocator_t,
)
from ._core import (
    _get_circuit, _get_circuit_initialized,
    _get_controlled, _get_ancilla,
    qubit_array,
)
```
**Warning signs:** Cython compilation errors about undefined names.

### Pitfall 4: Controlled Operations Not Supported
**What goes wrong:** Attempting to optimize controlled (conditional) classical operations.
**Why it happens:** The `_get_controlled()` flag indicates operations inside a `with control(qbool):` block.
**How to avoid:** When `_get_controlled()` is True, fall back to the existing unoptimized path (delegate to qint operators). The controlled variants (`cCQ_add`, etc.) have different qubit layouts.
**Warning signs:** Wrong results inside control blocks.

### Pitfall 5: Breaking Out-of-Place Semantics
**What goes wrong:** For `C = A + 5`, if optimization modifies A's qubits instead of creating new result qubits.
**Why it happens:** Confusion between in-place and out-of-place code paths.
**How to avoid:** Out-of-place ops MUST allocate a new qint for each result element, copy source qubits to it, then apply the CQ_* operation on the copy.
**Warning signs:** Source array elements are modified after the operation.

### Pitfall 6: List-of-int Operands
**What goes wrong:** Forgetting that list operands contain per-element classical values, not a single broadcast scalar.
**Why it happens:** Scalar path uses one classical value for all elements; list path uses different values per element.
**How to avoid:** For list operands, extract `flat_values[i]` and pass to `CQ_add(bits, flat_values[i])` per element.
**Warning signs:** All elements get the same classical value applied.

### Pitfall 7: Multiplication Result Width
**What goes wrong:** `CQ_mul` expects result qubits at position 0, source qubits at position `result_bits`.
**Why it happens:** Multiplication has a different layout than addition (which is in-place on the target).
**How to avoid:** Follow `qint.multiplication_inplace` layout exactly: `[ret_qubits, self_qubits, ancilla]`.
**Warning signs:** Wrong products, potential overflow or truncation.

## Code Examples

### Example 1: Optimized In-Place Addition (qarray += int)

Source: `qint.pyx` lines 685-745 (pattern for addition_inplace with int)

```python
# In qarray._inplace_binary_op, for __iadd__ with int:
cdef sequence_t *seq
cdef unsigned int[:] arr
cdef int self_offset
cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()

for i in range(len(self._elements)):
    elem = <qint>self._elements[i]
    self_offset = 64 - elem.bits
    qubit_array[:elem.bits] = elem.qubits[self_offset:64]
    start = elem.bits
    qubit_array[start: start + NUMANCILLY] = _get_ancilla()
    seq = CQ_add(elem.bits, classical_value)
    arr = qubit_array
    run_instruction(seq, &arr[0], False, _circuit)
    # elem is modified in-place (its qubits now reflect the addition)
```

### Example 2: Optimized Out-of-Place AND (qarray & int)

Source: `qint.pyx` lines 1067-1178 (pattern for __and__ with int)

```python
# For each element:
result_elem = qint(width=result_bits)  # Allocate result
result_offset = 64 - result_bits
self_offset = 64 - elem.bits

# CQ_and layout: [output:N, source:N]
qubit_array[:result_bits] = result_elem.qubits[result_offset:64]
qubit_array[result_bits:result_bits + elem.bits] = elem.qubits[self_offset:64]
# Zero-extend if elem.bits < result_bits (need padding qint)

seq = CQ_and(result_bits, classical_value)
arr = qubit_array
run_instruction(seq, &arr[0], False, _circuit)
result_elements.append(result_elem)
```

### Example 3: Subtraction via Inverted CQ_add

Source: `qint.pyx` line 882 (subtraction calls addition_inplace with invert=True)

```python
# Same as addition, but pass invert=True to run_instruction
seq = CQ_add(elem.bits, classical_value)
arr = qubit_array
run_instruction(seq, &arr[0], True, _circuit)  # invert=True for subtraction
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Lambda dispatch through qint operators | Direct CQ_* calls in qarray | Phase 40 (this phase) | Eliminates N temporary qint allocations per array op |

**Current state:** Array ops with classical values create O(N) temporary qint objects. Each temp qint allocates qubit indices, sets up qubit_array, and calls CQ_*. The optimization keeps the CQ_* calls but removes the Python-level qint allocation overhead.

## Open Questions

1. **XOR optimization scope**
   - What we know: `CQ_xor` does not exist. XOR with classical uses X gate loop.
   - What's unclear: Whether the X-gate loop pattern is worth optimizing at the array level (it's already fairly direct in qint.__xor__).
   - Recommendation: Still optimize by inlining the X-gate loop directly in qarray, avoiding the temporary qint copy + lambda overhead. The per-bit X-gate pattern from qint.__xor__ can be replicated directly.

2. **Controlled operation handling**
   - What we know: Controlled variants (cCQ_add, etc.) exist but have different qubit layouts.
   - What's unclear: Whether controlled array ops are commonly used.
   - Recommendation: Fall back to unoptimized path when `_get_controlled()` is True. This is the safest approach and matches how qint handles this edge case.

3. **Build/test cycle**
   - What we know: Changes to .pyx require Cython recompilation (`pip install -e .` or `python setup.py build_ext --inplace`).
   - What's unclear: Whether the CI/CD pipeline handles incremental builds.
   - Recommendation: After each code change, rebuild with `pip install -e .` and run `pytest tests/test_qarray_elementwise.py tests/test_qarray.py tests/test_qarray_reductions.py`.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/qarray.pyx` - Full source of array operations (lines 804-891 for _elementwise_binary_op and _inplace_binary_op)
- `src/quantum_language/qint.pyx` - CQ_* usage patterns (lines 685-745 for addition_inplace, 885-955 for multiplication_inplace, 1067-1178 for __and__, 1212-1322 for __or__, 1356-1474 for __xor__)
- `src/quantum_language/_core.pxd` - C function declarations (lines 5-41 for all CQ_* function signatures)
- `tests/test_qarray_elementwise.py` - Existing test suite (706 lines, covers all operation types)

### Secondary (MEDIUM confidence)
- `src/quantum_language/qarray.pxd` - qarray cdef class declaration
- `src/quantum_language/qint.pxd` - qint cdef class declaration
- `setup.py` - Build configuration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All CQ_* functions and calling patterns are directly observable in the codebase
- Architecture: HIGH - The optimization pattern is clear from comparing qarray dispatch to qint implementation
- Pitfalls: HIGH - All pitfalls derive from actual code patterns observed in qint.pyx

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (stable internal codebase, 30 days)
