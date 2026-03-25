# Active Bug Specifications

## BUG-1: Division never dispatches to controlled C functions

**Status:** Open
**Severity:** High — produces silently incorrect gate counts in controlled contexts
**File:** `src/quantum_language/qint_division.pxi` (and `qint_preprocessed.pyx`)

### Problem

`_divmod_c` always calls `toffoli_divmod_cq` / `toffoli_divmod_qq` regardless of whether `_controlled` is True. The controlled C variants (`toffoli_cdivmod_cq`, `toffoli_cdivmod_qq`) exist in the backend but are never called.

### Symptom

In `examples/test.py`, the DAG report shows identical gate counts for `divmod_cq` in both the "Uncontrolled" and "Controlled" sections. Controlled division should produce more gates (CCX-based operations instead of CX).

### Root Cause

In `qint_division.pxi`, lines 67 and 95:
```python
toffoli_divmod_cq(_circ, dividend_qa, n, <int64_t>divisor, quotient_qa, remainder_qa)
```
No `if _controlled:` dispatch. Compare with the correct pattern in `qint_arithmetic.pxi` for multiplication:
```python
if _controlled:
    toffoli_cmul_cq(...)
else:
    toffoli_mul_cq(...)
```

### Fix

Add controlled dispatch in `_divmod_c`:
1. When `_controlled` is True, call `toffoli_cdivmod_cq` / `toffoli_cdivmod_qq` with `control_qubit` as the extra parameter.
2. When `_controlled` is False, call the existing uncontrolled versions.
3. Pass appropriate gate counts to `_record_operation`.
4. Apply identical changes to `qint_preprocessed.pyx`.

### C function signatures (from `c_backend/include/toffoli_arithmetic_ops.h`)

```c
// Uncontrolled (existing calls)
void toffoli_divmod_cq(circuit_t *circ, const unsigned int *dividend_qubits, int dividend_bits,
                       int64_t divisor, const unsigned int *quotient_qubits,
                       const unsigned int *remainder_qubits);

// Controlled (need to call these)
void toffoli_cdivmod_cq(circuit_t *circ, const unsigned int *dividend_qubits, int dividend_bits,
                        int64_t divisor, const unsigned int *quotient_qubits,
                        const unsigned int *remainder_qubits, unsigned int ext_ctrl);
```

Same pattern for `_qq` variants.

### Verification

After fix, `examples/test.py` should show different (higher) gate counts for `divmod_cq` in the "Controlled" section vs "Uncontrolled".

---

## BUG-2: Bitwise and equality ops skip gate emission in Toffoli compile-mode

**Status:** Open
**Severity:** High — compiled functions produce incorrect (lower) gate counts
**File:** `src/quantum_language/qint_bitwise.pxi`, `src/quantum_language/qint_comparison.pxi` (and `qint_preprocessed.pyx`)

### Problem

Bitwise operations (NOT, AND, XOR, IXOR, OR) and the `eq_cq` comparison check `if _is_compile_mode():` without the `and _circ.arithmetic_mode != 1` guard. In Toffoli mode, they incorrectly record IR entries and return early without emitting gates. Since `_execute_ir` is (correctly) skipped in Toffoli mode (commit 6e914ab), these IR entries are never replayed.

### Symptom

In `examples/3sat/sat_walk_assembly.py`, compiled `main()` reports 37411 gates but uncompiled `walk_step()` reports 61111 gates. The difference (23700 gates) comes from bitwise and equality operations that silently produce 0 gates during compiled capture.

Reproducer:
```python
ql.option('simulate', False)

@ql.compile(inverse=True)
def test(x):
    eq = (x == 2)  # Records IR, never emits gates
    ...

test(x)
# block.original_gate_count == 0  (should be ~7)
```

### Root Cause

Five locations in `qint_bitwise.pxi` and one in `qint_comparison.pxi` use:
```python
if _is_compile_mode():  # BUG: missing arithmetic_mode check
```

Compare with the correct pattern in `qint_arithmetic.pxi` and `qint_comparison.pxi` (lt/gt):
```python
if _is_compile_mode() and _circ.arithmetic_mode != 1:  # Correct: Toffoli falls through
```

### Affected locations

| File | Line | Operation |
|------|------|-----------|
| `qint_bitwise.pxi` | 61 | NOT (qq) |
| `qint_bitwise.pxi` | 329 | AND (qq) |
| `qint_bitwise.pxi` | 635 | XOR (qq/cq) |
| `qint_bitwise.pxi` | 831 | IXOR (qq/cq) |
| `qint_bitwise.pxi` | 1026 | OR (qq/cq) |
| `qint_comparison.pxi` | 112 | EQ (cq) |

### Fix

Add `and _circ.arithmetic_mode != 1` to all six guards so Toffoli mode falls through to direct dispatch (emitting gates normally), matching the pattern used by arithmetic and lt/gt comparison operations. Apply identical changes to `qint_preprocessed.pyx`.

### Verification

After fix:
1. `examples/3sat/sat_walk_assembly.py` should report the same gate count for compiled and uncompiled `walk_step`.
2. `@ql.compile` functions using equality/bitwise ops should have non-zero `block.original_gate_count`.
