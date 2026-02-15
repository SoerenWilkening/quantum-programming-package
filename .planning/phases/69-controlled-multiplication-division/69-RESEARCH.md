# Phase 69: Controlled Multiplication & Division - Research

**Researched:** 2026-02-15
**Domain:** Controlled Toffoli multiplication, restoring division with Toffoli add/sub
**Confidence:** HIGH

## Summary

Phase 69 completes the Toffoli arithmetic surface with two orthogonal work streams: (1) controlled multiplication (`cQQ_mul_toffoli`, `cCQ_mul_toffoli`) and (2) restoring division/modulo using Toffoli add/sub underneath. The controlled multiplication is an extension of the Phase 68 shift-and-add loop, and the division requires no new C code because the existing Python-level restoring division algorithm (`qint_division.pxi`) already composes `+=`, `-=`, `>=`, and `with` blocks, all of which already dispatch to Toffoli when `arithmetic_mode == ARITH_TOFFOLI`.

For controlled multiplication, the current `hot_path_mul.c` has explicit comments ("Controlled Toffoli multiplication deferred to Phase 69 -- falls through to QFT") at lines 23-24 and 84-85. The fix is straightforward: when `controlled && ARITH_TOFFOLI`, call a new `toffoli_cmul_qq` / `toffoli_cmul_cq` function that wraps each shift-and-add iteration with a doubly-controlled adder. Concretely, for cQQ multiplication, each iteration already uses `toffoli_cQQ_add` (controlled by multiplier bit `b[j]`). Making it doubly controlled requires adding the external control qubit, meaning each adder call uses an MCX(4 controls) instead of MCX(3 controls). However, the simpler approach is to use the SAME `toffoli_cQQ_add` sequence but build the qubit array so that the "control" slot maps to a fresh ancilla that is the AND of `b[j]` and the external control qubit. This avoids modifying the adder sequences entirely.

For division, the key insight is that division/modulo in `qint_division.pxi` is a Python-level algorithm composed from primitive operations (`>=`, `-=`, `+=`, `with`) that already flow through their respective hot paths. Since Toffoli is the default arithmetic mode, division already uses Toffoli add/sub for its internal arithmetic. The success criteria require *verifying* this works correctly, not implementing new C code. The known bug BUG-DIV-02 (MSB comparison leak) affects some edge cases and may need to be addressed or documented as xfail.

**Primary recommendation:** Implement controlled Toffoli multiplication by adding `toffoli_cmul_qq` and `toffoli_cmul_cq` functions that use a Toffoli AND ancilla pattern (CCX to compute `control AND b[j]`, use result as single control for existing `toffoli_cQQ_add`, then uncompute AND). Wire into `hot_path_mul.c` for the `controlled && ARITH_TOFFOLI` case. For division, verify the existing algorithm works with Toffoli dispatch and write exhaustive tests, acknowledging BUG-DIV-02 as xfail where applicable.

## Standard Stack

### Core (Existing -- No New Dependencies)

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ToffoliMultiplication.c` | `c_backend/src/ToffoliMultiplication.c` | QQ/CQ Toffoli mul (Phase 68) | Extend with controlled variants |
| `ToffoliAddition.c` | `c_backend/src/ToffoliAddition.c` | CDKM adder (all 4 variants) | Used as subroutine in controlled mul |
| `hot_path_mul.c` | `c_backend/src/hot_path_mul.c` | Multiplication dispatch | Add controlled Toffoli branch |
| `toffoli_arithmetic_ops.h` | `c_backend/include/toffoli_arithmetic_ops.h` | Public API for Toffoli ops | Add controlled mul declarations |
| `qint_division.pxi` | `src/quantum_language/qint_division.pxi` | Division algorithm (Python) | Already uses Toffoli add/sub via dispatch |
| `qint_comparison.pxi` | `src/quantum_language/qint_comparison.pxi` | Comparison operators | Used by division; already works with Toffoli |
| `qubit_allocator.c` | `c_backend/src/qubit_allocator.c` | Ancilla allocation/free | For AND ancilla in controlled mul |
| `gate.h` | `c_backend/include/gate.h` | Gate primitives (ccx, cx, x, mcx) | For AND computation |

### Files to Modify

| File | Change | Estimated Lines |
|------|--------|-----------------|
| `c_backend/src/ToffoliMultiplication.c` | Add `toffoli_cmul_qq` and `toffoli_cmul_cq` functions | ~120 |
| `c_backend/include/toffoli_arithmetic_ops.h` | Declare new controlled mul functions | ~30 |
| `c_backend/src/hot_path_mul.c` | Wire controlled Toffoli dispatch (remove QFT fallback for controlled) | ~20 |
| `tests/test_toffoli_multiplication.py` | Add controlled multiplication tests | ~100 |
| `tests/test_div.py` or new `tests/test_toffoli_division.py` | Verify division uses Toffoli add/sub | ~150 |

### Files NOT Changed

| File | Why No Change |
|------|---------------|
| `qint_division.pxi` | Division algorithm already correct; it composes `+=`, `-=`, `>=` which dispatch to Toffoli |
| `IntegerMultiplication.c` | QFT multiplication stays as-is |
| `qint_arithmetic.pxi` | `multiplication_inplace` already passes `controlled` flag to C |
| `setup.py` | No new C files needed |

## Architecture Patterns

### Pattern 1: Controlled QQ Toffoli Multiplication (AND-Ancilla Approach)

**What:** For each multiplier bit `b[j]`, compute `and_ancilla = b[j] AND ext_control` using a CCX, use `and_ancilla` as the single control for the existing `toffoli_cQQ_add`, then uncompute the AND.

**When to use:** For `toffoli_cmul_qq` -- controlled multiplication of two quantum registers.

**Algorithm (n-bit controlled QQ mul: ret = self * other, controlled by ext_ctrl):**

```
// For j = 0 to n-1:
//   width = n - j
//   1. Compute AND: CCX(and_ancilla, other[j], ext_ctrl)  -- and_ancilla = b[j] AND ctrl
//   2. Build tqa with and_ancilla as control for toffoli_cQQ_add(width)
//   3. Run toffoli_cQQ_add(width) with tqa
//   4. Uncompute AND: CCX(and_ancilla, other[j], ext_ctrl)  -- restore and_ancilla to |0>
```

**Qubit array for each iteration (width >= 2):**
```
tqa[0..width-1]       = self_qubits[0..width-1]  (a-register, preserved)
tqa[width..2*width-1]  = ret_qubits[j..j+width-1]  (b-register, accumulator)
tqa[2*width]           = carry_ancilla
tqa[2*width+1]         = and_ancilla  (acts as "control" for cQQ_add)
```

**Key insight:** The existing `toffoli_cQQ_add` expects a single control qubit at position `2*bits+1`. By computing `AND(b[j], ext_ctrl)` into a fresh ancilla and using that ancilla as the control, we reuse the proven controlled adder without any modifications. The AND ancilla is uncomputed after each adder call (CCX is self-inverse).

**Ancilla budget per iteration:** 1 carry ancilla (reused) + 1 AND ancilla (reused). Total: 2 extra qubits allocated before the loop, freed after.

**For width == 1:** The 1-bit cQQ_add is a single CCX. For controlled 1-bit multiplication, we need `result[n-1] ^= self[0] AND other[j] AND ext_ctrl`, which is an MCX with 3 controls: `MCX(target=ret[n-1], controls=[self[0], other[j], ext_ctrl])`. This can be emitted directly as a single MCX gate.

### Pattern 2: Controlled CQ Toffoli Multiplication (Controlled Shift-and-Add)

**What:** For `cCQ_mul_toffoli`, the classical value's bits determine which additions to perform. In the uncontrolled case, only set bits trigger uncontrolled additions (`toffoli_QQ_add`). In the controlled case, each addition must be conditioned on the external control qubit, so we use `toffoli_cQQ_add` with the external control qubit (instead of uncontrolled `toffoli_QQ_add`).

**When to use:** For `toffoli_cmul_cq` -- controlled multiplication by a classical value.

**Algorithm (n-bit controlled CQ mul: ret = self * val, controlled by ext_ctrl):**

```
// For each set bit j of classical_value:
//   width = n - j
//   Build tqa with ext_ctrl as control for toffoli_cQQ_add(width)
//   Run toffoli_cQQ_add(width) -- adds self slice to ret slice, controlled by ext_ctrl
```

**Key difference from uncontrolled CQ:** The uncontrolled CQ path uses `toffoli_QQ_add` (no control). The controlled CQ path uses `toffoli_cQQ_add` with `ext_ctrl`, because the classical bit selection (compile-time) is already handled by the loop over set bits, but the *runtime* control from the external qubit must gate each addition.

**For width == 1:** Use CCX(target=ret[n-1], ctrl1=self[0], ctrl2=ext_ctrl) instead of CNOT.

### Pattern 3: Division Uses Toffoli Transparently (No New C Code)

**What:** The restoring division algorithm in `qint_division.pxi` is implemented purely in Python/Cython, composing these operations:
- `remainder ^= self` -- uses XOR (hot_path_bitwise), not arithmetic mode-dependent
- `can_subtract = remainder >= trial_value` -- uses comparison operators (widened subtraction)
- `with can_subtract:` -- sets `_controlled` flag in context
- `remainder -= trial_value` -- dispatches to `hot_path_add_cq` (controlled Toffoli CQ subtraction)
- `quotient += (1 << bit_pos)` -- dispatches to `hot_path_add_cq` (controlled Toffoli CQ addition)

Since ARITH_TOFFOLI is the default, ALL these internal operations already use Toffoli gates. The division algorithm needs no modifications. The comparison operators (`>=`, `<`) use widened subtraction which also dispatches to the Toffoli adder.

**When to use:** Always -- this is the current behavior.

**What needs verification:** That the end-to-end result is arithmetically correct. The individual Toffoli addition/subtraction operations are proven correct (Phase 66-67), but the composition in the division loop (with comparison ancilla, controlled contexts, layer floors) may have integration issues.

**Known issue: BUG-DIV-02 (MSB comparison leak):** The existing division tests (`test_div.py`) document 9 known-failing cases where `a >= 2^(w-1)` with small divisors. These are xfailed in the QFT tests and will likely also fail in Toffoli mode since the root cause is in the comparison operator, not the adder backend. Phase 69 should carry these xfails forward.

### Pattern 4: Division Inside `with` Blocks (Controlled Context)

**What:** Success criterion 5 requires division operations to work inside `with` blocks (controlled context) with Toffoli dispatch. This means:

```python
ctrl = ql.qint(1, width=1)
with ctrl:
    q = a // 3  # Controlled division
```

Inside the `with ctrl:` block, `_get_controlled()` returns True and `_get_control_bool()` returns `ctrl`. The division's internal operations (`remainder >= trial_value`, `remainder -= trial_value`, `quotient += (1 << bit_pos)`) are ALREADY inside a `with can_subtract:` block. When the outer `with ctrl:` is active, these operations become doubly controlled.

**Key concern:** The `with` context manager stacks. Inside `with ctrl: with can_subtract:`, the operations see TWO control qubits. The current `_get_controlled()` mechanism only tracks a single control qubit (the most recent `with` block). Looking at the codebase, the `qint.__enter__` sets `_controlled` and `_control_bool` to itself, and `__exit__` restores the previous values. The `with can_subtract:` inside `with ctrl:` means `can_subtract` becomes the active control, and the outer `ctrl` is NOT active during the inner block.

**This means:** Division inside `with ctrl:` does NOT produce doubly-controlled operations. The `with can_subtract:` overrides the outer `with ctrl:`. This is actually correct behavior for the division algorithm -- the comparison result `can_subtract` correctly encodes "should I subtract?", and the outer control's effect was already captured when computing `can_subtract` (since `remainder >= trial_value` was computed with `ctrl` active).

**Wait -- re-examining:** Actually, the comparison `can_subtract = remainder >= trial_value` is computed OUTSIDE the `with can_subtract:` block but INSIDE the `with ctrl:` block. Does the comparison itself see the outer control? Looking at `__ge__` -> `~(self < other)` -> `__lt__`: the comparison allocates widened temps, does subtraction (`temp_self -= temp_other`), and extracts the MSB. The subtraction inside `__lt__` calls `__isub__` -> `addition_inplace(other, invert=True)` which checks `_get_controlled()`. If `ctrl` is active (from `with ctrl:`), the subtraction is controlled.

**Conclusion:** The comparison IS controlled by the outer `ctrl`, which means `can_subtract` correctly reflects "should I subtract, given that ctrl is |1>?". Then `with can_subtract:` uses that result as the control for the subtraction/addition inside the loop. This should be semantically correct but needs verification.

### Anti-Patterns to Avoid

- **Anti-pattern: Modifying the adder to support 2 external controls.** Instead of creating a doubly-controlled CDKM adder (which would require 4-controlled X gates), use the AND-ancilla pattern: compute `AND(ctrl1, ctrl2)` into a fresh ancilla, use it as a single control for the existing cQQ adder, then uncompute the AND. This reuses proven infrastructure.

- **Anti-pattern: Implementing division in C.** The division algorithm is a Python-level loop that composes primitive operations. Moving it to C would require reimplementing comparison, conditional subtraction, and quotient accumulation logic. The overhead of the Python loop is negligible compared to the circuit generation per iteration. Keep division in Python.

- **Anti-pattern: Ignoring BUG-DIV-02 in tests.** The MSB comparison leak affects both QFT and Toffoli backends. Tests must xfail the known cases rather than silently ignoring them or expecting them to magically work.

- **Anti-pattern: Using different register layout for controlled mul.** The controlled multiplication must use the SAME qubit array layout as uncontrolled (ret, self, other passed separately). The external control qubit is obtained from `control_qubit` parameter. The AND ancilla is allocated internally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Doubly-controlled adder | MCX(4 controls) CDKM variant | AND-ancilla + existing cQQ adder | Avoids new sequence generator; AND is 2 CCX gates |
| Division algorithm | C-level division | Existing Python qint_division.pxi | Already works, already dispatches to Toffoli |
| Quantum comparator for division | Toffoli-native comparator | Existing widened-subtraction comparator | Already works, already uses Toffoli add/sub |
| Controlled subtraction for division | New controlled sub path | Existing cCQ_add with invert flag | `run_instruction(seq, qa, invert=1, circ)` works for Toffoli |

**Key insight:** The entire division functionality is already Toffoli-compatible because it composes from primitives (add/sub/compare) that already dispatch to Toffoli. Phase 69 division work is verification, not implementation.

## Common Pitfalls

### Pitfall 1: AND Ancilla Not Uncomputed

**What goes wrong:** If the AND ancilla (`and_ancilla = b[j] AND ext_ctrl`) is not uncomputed after each adder call, it remains entangled with the multiplier and control registers. Over n iterations, this creates n dirty ancilla.

**Why it happens:** CCX is self-inverse. Applying the same CCX after the adder call uncomputes the AND. But if the adder modifies any of the CCX's input qubits (b[j] or ext_ctrl), the second CCX does NOT properly uncompute.

**How to avoid:** The CDKM adder preserves the source register (b/other) and the external control is never modified. So `b[j]` and `ext_ctrl` are unchanged after the adder call. The second CCX correctly uncomputes the AND. Document this reasoning in a comment.

**Warning signs:** Ancilla qubits are not returned to |0> after multiplication. Allocator reports leaked ancilla.

### Pitfall 2: 1-bit Controlled Multiplication Edge Case

**What goes wrong:** For width 1, controlled QQ multiplication is `ret[0] = self[0] AND other[0] AND ext_ctrl` -- a 3-controlled X (MCX with 3 controls). The AND-ancilla pattern works but is overkill for 1 bit. Emitting a direct MCX(3 controls) is simpler.

**Why it happens:** The general loop calls `toffoli_cQQ_add(1)` which is a CCX. With the AND-ancilla pattern, the total gate count for 1-bit is: CCX(compute AND) + CCX(1-bit adder) + CCX(uncompute AND) = 3 CCX gates. A direct MCX(3 controls) is 1 gate.

**How to avoid:** Special-case width 1 in the controlled QQ mul to emit a single MCX(target=ret[0], controls=[self[0], other[j], ext_ctrl]).

### Pitfall 3: BUG-COND-MUL-01 May Affect QFT Fallback

**What goes wrong:** The existing bug BUG-COND-MUL-01 ("Controlled multiplication corrupts result register") refers to the QFT-based controlled multiplication (`cQQ_mul`, `cCQ_mul`). Phase 69 introduces Toffoli-based controlled multiplication, which may be free of this bug. But the QFT fallback path remains for non-Toffoli mode.

**Why it happens:** Unknown -- the bug was documented as "not yet investigated." It may be in the QFT `cQQ_mul` sequence generation (IntegerMultiplication.c) or in the hot_path qubit array layout.

**How to avoid:** Phase 69 implements Toffoli controlled multiplication as a NEW path. It does not fix the QFT controlled multiplication. The Toffoli path is independently verified. The QFT path's bug (BUG-COND-MUL-01) remains a carry-forward issue.

### Pitfall 4: Division Qubit Count Exceeds Statevector Simulator Capacity

**What goes wrong:** Division at width w allocates: input(w) + quotient(w) + remainder(w) + comparison ancilla per iteration. For width 3, this can reach 33-44 qubits, exceeding statevector simulation capacity on typical hardware.

**Why it happens:** Each comparison `remainder >= trial_value` allocates widened temporaries (w+1 bits each), and the `with can_subtract:` block adds a control qubit. The total qubit count grows as O(w^2) per division.

**How to avoid:** Use `matrix_product_state` (MPS) simulator for division tests, matching the existing `test_div.py` pattern. MPS handles 40+ qubit circuits efficiently for circuits with limited entanglement (which restoring division has, since operations are sequential).

**Warning signs:** Statevector simulation runs out of memory for width >= 3. Tests hang or crash.

### Pitfall 5: Controlled CQ Mul Ancilla for Temp Register

**What goes wrong:** In controlled CQ multiplication, each iteration uses `toffoli_cQQ_add` (not `toffoli_QQ_add`). The cQQ adder expects a control qubit at position `2*width+1`. The external control qubit must be mapped to this position. But the CQ path also needs a carry ancilla at `2*width`. If both ancilla allocation calls return the same qubit (allocator reuse), the carry and control collide.

**Why it happens:** The allocator reuses freed qubits. If carry is allocated, freed, then control is allocated, it may get the same physical qubit.

**How to avoid:** For controlled CQ mul, allocate the carry ancilla BEFORE the loop and keep it allocated throughout (since it is guaranteed |0> after each CDKM call). The external control qubit is passed from the hot path, not allocated. No collision risk.

### Pitfall 6: Division with `with` Block Nesting Semantics

**What goes wrong:** When division runs inside a `with ctrl:` block, the comparison `can_subtract = remainder >= trial_value` is computed with `ctrl` active. Then `with can_subtract:` overrides `ctrl` as the active control. The operations inside `with can_subtract:` only see `can_subtract` as the control, not `ctrl`.

**Why it happens:** The `with` context manager replaces (not stacks) the controlled state.

**How to avoid:** This is actually correct for the algorithm. The comparison result `can_subtract` already incorporates the effect of `ctrl` (because the comparison's internal subtraction was controlled by `ctrl`). If `ctrl = |0>`, the comparison produces `can_subtract = |0>` (since the subtraction doesn't happen, the MSB check shows no borrow), which means the `with can_subtract:` block does nothing. The division is effectively a no-op when `ctrl = |0>`.

**Verification needed:** Test with `ctrl = |1>` (division happens normally) and `ctrl = |0>` (dividend unchanged, quotient = 0).

**WAIT -- re-examining more carefully:** If `ctrl = |0>`, then inside `with ctrl:`:
- `remainder ^= self` -- this is NOT inside a `with can_subtract:` block. It IS inside `with ctrl:`. So `remainder ^= self` is controlled by `ctrl`. If `ctrl = |0>`, remainder stays at 0.
- `can_subtract = remainder >= trial_value` -- comparison is controlled by `ctrl`. If `ctrl = |0>`, the comparison's internal subtraction does nothing, so `can_subtract` should be `|0>` (or possibly incorrect if the comparison short-circuits for known-zero input).
- `with can_subtract: remainder -= trial_value; quotient += (1 << bit_pos)` -- controlled by `can_subtract` which is `|0>`, so these are no-ops.

Actually, looking more closely at `__floordiv__`, the operations happen AT THE PYTHON LEVEL, not inside an explicit `with ctrl:`. The user writes:
```python
with ctrl:
    q = a // 3
```
This calls `__floordiv__` which internally runs the loop. During this loop, `_get_controlled()` returns True (because of outer `with ctrl:`). So:
- `remainder ^= self` -- `__ixor__` checks `_get_controlled()`. Yes, XOR is controlled by `ctrl`.
- `can_subtract = remainder >= trial_value` -- `__ge__` -> `__lt__` checks `_get_controlled()`. Comparison is controlled by `ctrl`.

ACTUALLY wait -- `__ixor__` in `qint_bitwise.pxi` does check `_get_controlled()`. Let me check:

The XOR operation `remainder ^= self` goes through `__ixor__` -> `_xor_inplace` which is a bitwise operation. Looking at the code flow, it uses `qubit_array` and `run_instruction`. Whether it checks `_get_controlled()` depends on the implementation.

This is a subtle area. The safest approach for success criterion 5 is to test it empirically: run division inside `with ctrl:` with both `ctrl = |1>` (should produce correct quotient) and `ctrl = |0>` (should leave everything unchanged).

## Code Examples

### Controlled QQ Toffoli Multiplication (AND-Ancilla Pattern)

```c
void toffoli_cmul_qq(circuit_t *circ,
                     const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits,
                     unsigned int ext_ctrl) {
    int n = ret_bits;

    // Allocate 1 carry ancilla (reused per iteration)
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) return;

    // Allocate 1 AND ancilla (reused per iteration)
    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, carry, 1);
        return;
    }

    for (int j = 0; j < n; j++) {
        int width = n - j;
        if (width < 1) break;

        if (width == 1) {
            // 1-bit: MCX(target=ret[n-1], controls=[self[0], other[j], ext_ctrl])
            unsigned int tqa[4];
            tqa[0] = ret_qubits[n - 1];  // target
            // Emit MCX with 3 controls directly
            gate_t g;
            memset(&g, 0, sizeof(gate_t));
            qubit_t ctrls[3] = {self_qubits[0], other_qubits[j], ext_ctrl};
            // Use add_gate pattern or build inline...
            // Actually, use the qubit_array + run_instruction pattern
            // with a custom 1-gate sequence or direct gate emission
            // ... (simplified for illustration)
        } else {
            // Compute AND: and_anc = other[j] AND ext_ctrl
            // CCX(target=and_anc, ctrl1=other[j], ctrl2=ext_ctrl)
            // (emit directly via add_gate or build a 1-layer sequence)

            unsigned int tqa[256];
            // a-register [0..width-1] = self (source, preserved)
            for (int i = 0; i < width; i++)
                tqa[i] = self_qubits[i];
            // b-register [width..2*width-1] = ret[j..j+width-1] (target, accumulator)
            for (int i = 0; i < width; i++)
                tqa[width + i] = ret_qubits[j + i];
            // carry ancilla
            tqa[2 * width] = carry;
            // control = and_anc (holds b[j] AND ext_ctrl)
            tqa[2 * width + 1] = and_anc;

            sequence_t *toff_seq = toffoli_cQQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, and_anc, 1);
                allocator_free(circ->allocator, carry, 1);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);

            // Uncompute AND: CCX(target=and_anc, ctrl1=other[j], ctrl2=ext_ctrl)
            // (emit directly)
        }
    }

    allocator_free(circ->allocator, and_anc, 1);
    allocator_free(circ->allocator, carry, 1);
}
```

**Note on gate emission:** The AND compute/uncompute (CCX gates) and the 1-bit MCX gates need to be emitted directly. The codebase has `add_gate()` or can build a single-layer sequence. Look at how `hot_path_add.c` handles 1-bit cases for the pattern.

### Controlled CQ Toffoli Multiplication

```c
void toffoli_cmul_cq(circuit_t *circ,
                     const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     int64_t classical_value,
                     unsigned int ext_ctrl) {
    int n = ret_bits;
    int *bin = two_complement(classical_value, n);
    if (bin == NULL) return;

    // Allocate 1 carry ancilla (reused per iteration)
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) { free(bin); return; }

    for (int j = 0; j < n; j++) {
        if (bin[n - 1 - j] == 0) continue;  // Skip zero bits

        int width = n - j;
        if (width < 1) break;

        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (width == 1) {
            // 1-bit controlled: CCX(target=ret[n-1], ctrl1=self[0], ctrl2=ext_ctrl)
            tqa[0] = ret_qubits[n - 1];
            tqa[1] = self_qubits[0];
            tqa[2] = ext_ctrl;

            toff_seq = toffoli_cQQ_add(1);
            if (toff_seq == NULL) { free(bin); allocator_free(circ->allocator, carry, 1); return; }
            run_instruction(toff_seq, tqa, 0, circ);
        } else {
            // a-register = self[0..width-1] (source, preserved)
            for (int i = 0; i < width; i++)
                tqa[i] = self_qubits[i];
            // b-register = ret[j..j+width-1] (target, accumulator)
            for (int i = 0; i < width; i++)
                tqa[width + i] = ret_qubits[j + i];
            // carry ancilla
            tqa[2 * width] = carry;
            // control = ext_ctrl
            tqa[2 * width + 1] = ext_ctrl;

            toff_seq = toffoli_cQQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, carry, 1);
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
        }
    }

    allocator_free(circ->allocator, carry, 1);
    free(bin);
}
```

### Division Verification Test Pattern

```python
# Verify Toffoli-mode division produces correct results
def _run_toffoli_div(width, a_val, divisor):
    """Run division through Toffoli pipeline."""
    ql.circuit()
    ql.option("fault_tolerant", True)  # Ensure Toffoli mode
    a = ql.qint(a_val, width=width)
    q = a // divisor
    qasm_str = ql.to_openqasm()

    # Verify no QFT gates in output
    assert 'h ' not in qasm_str.lower() or 'p(' not in qasm_str.lower(), \
        "QFT gates found in Toffoli-mode division"

    # Simulate
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(method="matrix_product_state")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    n = len(bitstring)
    quotient_bits = bitstring[n - 2 * width : n - width]
    actual = int(quotient_bits, 2)
    return actual

@pytest.mark.parametrize("width,a,divisor", exhaustive_cases)
def test_toffoli_div(width, a, divisor):
    expected = a // divisor
    actual = _run_toffoli_div(width, a, divisor)
    assert actual == expected
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Controlled mul falls through to QFT | Controlled mul dispatches to Toffoli (AND-ancilla pattern) | Phase 69 (new) | Full Toffoli coverage for all multiplication variants |
| Division not verified with Toffoli | Division verified to use Toffoli add/sub transparently | Phase 69 (new) | Proves restoring division algorithm is backend-agnostic |
| BUG-COND-MUL-01 blocks controlled mul | Toffoli controlled mul is independent implementation | Phase 69 (new) | New path may be free of QFT controlled mul bugs |

## Open Questions

1. **Gate emission for AND compute/uncompute in controlled mul**
   - What we know: The CDKM adder uses `sequence_t` + `run_instruction`. Direct gate emission (for the CCX that computes the AND ancilla) needs either a 1-layer sequence or a different emission mechanism.
   - What's unclear: Does the circuit have an `add_gate` function that can emit a single CCX without building a sequence? Or should we build a 1-layer sequence for the CCX?
   - Recommendation: Build a helper function `emit_ccx_gate(circ, target, ctrl1, ctrl2)` that creates a 1-layer sequence with one CCX and calls `run_instruction`. Or look for an existing pattern in the codebase for emitting individual gates.

2. **AND-ancilla vs doubly-controlled adder**
   - What we know: The AND-ancilla approach reuses the proven cQQ adder and adds only 2 CCX per iteration. A doubly-controlled adder would need MCX(4 controls) per gate, significantly increasing gate count.
   - What's unclear: Whether the MCX(4 controls) overhead is acceptable. For fault-tolerant T-count optimization, the AND-ancilla approach has known T-count: 2 * 7T (for the two AND CCXs) + controlled adder T-count. The MCX(4 controls) approach has higher T-count per gate.
   - Recommendation: Use AND-ancilla. It is the standard approach in the literature (Beauregard 2003, Haner et al. 2018) and matches the existing codebase patterns.

3. **BUG-DIV-02 interaction with Toffoli mode**
   - What we know: BUG-DIV-02 manifests as MSB comparison leak in division for values >= 2^(w-1). The root cause is in the comparison operator (`>=`), which uses widened subtraction. The comparison already dispatches to Toffoli add/sub.
   - What's unclear: Whether the Toffoli backend produces the same failures as the QFT backend for BUG-DIV-02 cases. It likely does since the comparison algorithm is identical regardless of backend.
   - Recommendation: Copy the xfail set from `test_div.py` (`KNOWN_DIV_MSB_LEAK`) into the Toffoli division tests. Verify the same cases fail and the non-xfail cases pass.

4. **Does XOR (`^=`) inside `with ctrl:` work correctly for division?**
   - What we know: Division starts with `remainder ^= self` to copy the dividend. Inside `with ctrl:`, this XOR should be controlled.
   - What's unclear: Whether `__ixor__` checks `_get_controlled()`. If it does not, `remainder ^= self` happens unconditionally even when `ctrl = |0>`, corrupting the circuit.
   - Recommendation: Verify by inspecting `qint_bitwise.pxi` for the `__ixor__` implementation. If it does not check `_get_controlled()`, this is a bug that needs fixing for success criterion 5.

5. **Division gate purity: will division in Toffoli mode contain only Toffoli gates?**
   - What we know: Division's internal operations (add, sub) dispatch to Toffoli. But comparisons use `Q_xor(1)` for bit-by-bit copy in widened temporaries (see `qint_comparison.pxi` lines 253-258).
   - What's unclear: Whether `Q_xor(1)` generates QFT-style gates or Toffoli-style gates. If `Q_xor` is from the QFT path, the division circuit will contain non-Toffoli gates.
   - Recommendation: Check `Q_xor` implementation. It should just be a CNOT, which is Toffoli-compatible.

## Detailed Implementation Plan Guidance

### Plan 1: Controlled Toffoli Multiplication (MUL-03, MUL-04)

**Files:** `ToffoliMultiplication.c`, `toffoli_arithmetic_ops.h`, `hot_path_mul.c`

1. Add `toffoli_cmul_qq` function to `ToffoliMultiplication.c`:
   - AND-ancilla pattern for controlled QQ mul
   - Special case for width 1 (single MCX with 3 controls)
   - Allocate carry + AND ancilla before loop, free after
   - Gate emission for CCX: use a static 1-layer sequence helper or find existing pattern

2. Add `toffoli_cmul_cq` function to `ToffoliMultiplication.c`:
   - Use `toffoli_cQQ_add` with ext_ctrl for each set classical bit
   - Special case for width 1 (CCX)
   - Allocate carry before loop, free after

3. Update `hot_path_mul.c`:
   - Change `if (circ->arithmetic_mode == ARITH_TOFFOLI && !controlled)` to also handle `controlled`
   - Route controlled+Toffoli to `toffoli_cmul_qq` / `toffoli_cmul_cq`

4. Update `toffoli_arithmetic_ops.h` with new function declarations

### Plan 2: Controlled Multiplication Tests

**Files:** `tests/test_toffoli_multiplication.py`

1. Add `TestToffoliControlledQQMultiplication`:
   - Exhaustive for widths 1-3 with control=|1> (multiplication happens)
   - Exhaustive for widths 1-2 with control=|0> (no-op, ret stays 0)
   - Result extraction: ret at [2*width..3*width-1] + ctrl at [3*width]

2. Add `TestToffoliControlledCQMultiplication`:
   - Exhaustive for widths 1-3 with control=|1>
   - Exhaustive for widths 1-2 with control=|0>

3. Gate purity checks for controlled multiplication

### Plan 3: Division/Modulo Toffoli Verification (DIV-01, DIV-02)

**Files:** `tests/test_toffoli_division.py` (new)

1. Verify `a // divisor` produces correct quotient with Toffoli dispatch for classical divisors at widths 2-4
2. Verify `a % divisor` produces correct remainder with Toffoli dispatch for classical divisors at widths 2-4
3. Verify `a // b` and `a % b` work with quantum divisors at widths 2-3
4. Verify division inside `with ctrl:` block works with Toffoli dispatch
5. Copy BUG-DIV-02 xfails from test_div.py
6. Use MPS simulator for width 3+ (matching existing test_div.py)

### Qubit Budget

**Controlled QQ multiplication (n bits):**
- Input: n (self) + n (other) + n (ret) + 1 (ctrl) = 3n + 1
- Ancilla: 1 carry + 1 AND = 2
- Total: 3n + 3

**Controlled CQ multiplication (n bits):**
- Input: n (self) + n (ret) + 1 (ctrl) = 2n + 1
- Ancilla: 1 carry
- Total: 2n + 2

**Division (n bits, classical divisor):**
- Input: n (dividend)
- Allocates: n (quotient) + n (remainder) + per-iteration comparison ancilla
- Per iteration: comparison allocates widened temps (n+1 bits each, 2 copies) + control qbool
- Total: approximately 7n-10n qubits (depends on implementation details)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `c_backend/src/ToffoliMultiplication.c` -- Phase 68 QQ/CQ mul implementation with qubit layouts
- Codebase inspection: `c_backend/src/ToffoliAddition.c` -- all 4 CDKM adder variants with controlled gates
- Codebase inspection: `c_backend/src/hot_path_mul.c` -- current controlled fallback comments at lines 23-24, 84-85
- Codebase inspection: `src/quantum_language/qint_division.pxi` -- full division/modulo algorithm using +=, -=, >=, with
- Codebase inspection: `src/quantum_language/qint_comparison.pxi` -- comparison operators used by division
- Codebase inspection: `src/quantum_language/qint_arithmetic.pxi` -- `multiplication_inplace` passing controlled flag
- Codebase inspection: `tests/test_div.py` -- existing division tests with BUG-DIV-02 xfails
- Codebase inspection: `tests/test_toffoli_multiplication.py` -- Phase 68 test patterns for result extraction
- Phase 68 RESEARCH.md, 68-01-SUMMARY.md, 68-02-SUMMARY.md -- multiplication architecture and test patterns
- Phase 67 RESEARCH.md -- controlled CDKM adder architecture and hot path dispatch patterns
- Phase 37 37-01-SUMMARY.md -- BUG-DIV-02 documentation and MPS simulator decision

### Secondary (MEDIUM confidence)
- AND-ancilla pattern for controlled operations: standard technique in quantum computing (Beauregard 2003, Haner et al. 2018)
- Restoring division algorithm: standard textbook algorithm composed from add/sub/compare primitives

### Tertiary (LOW confidence)
- BUG-COND-MUL-01 interaction: unknown whether QFT controlled mul bug shares root cause with any Toffoli path issue

## Metadata

**Confidence breakdown:**
- Controlled multiplication architecture (AND-ancilla): HIGH -- standard pattern, all infrastructure exists
- Hot path wiring: HIGH -- same pattern as Phase 67 (controlled addition dispatch)
- Division Toffoli verification: HIGH -- division already uses Toffoli add/sub, just needs testing
- Division inside `with` blocks: MEDIUM -- needs empirical verification of `with` nesting semantics
- BUG-DIV-02 interaction: MEDIUM -- expected to manifest identically, but not verified
- XOR controlled behavior for division: MEDIUM -- needs code inspection of `__ixor__`

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (stable domain, no external dependencies changing)
