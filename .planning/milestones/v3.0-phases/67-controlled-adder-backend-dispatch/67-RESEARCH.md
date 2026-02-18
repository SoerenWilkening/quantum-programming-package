# Phase 67: Controlled Adder & Backend Dispatch - Research

**Researched:** 2026-02-14
**Domain:** Controlled Toffoli-based quantum arithmetic, arithmetic mode dispatch
**Confidence:** HIGH

## Summary

Phase 67 extends the CDKM ripple-carry adder (Phase 66) with controlled variants and completes the backend dispatch system. The phase has three orthogonal work streams: (1) implementing `toffoli_cQQ_add` and `toffoli_cCQ_add` in C, (2) wiring controlled Toffoli dispatch into `hot_path_add.c` to remove the QFT fallback for controlled operations, and (3) changing the default arithmetic mode from ARITH_QFT to ARITH_TOFFOLI.

The controlled CDKM adder is constructed by adding an extra control qubit to every gate in the uncontrolled circuit. Concretely, every CX(target, control) in the CDKM sequence becomes CCX(target, control, ext_control), and every CCX(target, ctrl1, ctrl2) becomes a 3-controlled X gate (`mcx` with 3 controls). The codebase already has full infrastructure for this: the `mcx()` gate primitive supports arbitrary control counts via `large_control`, `run_instruction()` maps multi-controlled gates correctly, and the OpenQASM export emits `ctrl(n) @ x` syntax for gates with 3+ controls. The CQ controlled variant follows the same temp-register pattern from Phase 66, but with controlled X-init/cleanup and controlled QQ CDKM.

The most significant design decision is the qubit layout contract for controlled Toffoli addition. The existing QFT controlled addition (cQQ_add) places the control qubit at virtual index `2*bits`. The Toffoli cQQ variant needs `2*bits+1` virtual qubits for the two registers plus 1 ancilla, with the external control at a separate index. The recommended layout is: `[0..bits-1]` = a-register, `[bits..2*bits-1]` = b-register, `[2*bits]` = ancilla carry, `[2*bits+1]` = external control qubit. This avoids collision with the ancilla at `2*bits`.

**Primary recommendation:** Implement controlled CDKM variants by adding the external control qubit to every gate, wire into hot_path_add.c with correct ancilla + control qubit layout, change default arithmetic mode to ARITH_TOFFOLI, and verify exhaustively for widths 1-4.

## Standard Stack

### Core (Existing - No New Dependencies)

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ccx()` | `c_backend/src/gate.c:200` | Toffoli gate primitive | Used in CDKM, becomes controlled CX |
| `mcx()` | `c_backend/src/gate.c:208` | Multi-controlled X gate | Handles 3+ controls for controlled CCX |
| `cx()` | `c_backend/src/gate.c:193` | CNOT gate primitive | Becomes CCX in controlled variant |
| `x()` | `c_backend/src/gate.c:187` | NOT gate primitive | Becomes CX in controlled CQ variant |
| `sequence_t` | `c_backend/include/types.h:77` | Gate sequence container | Standard for all arithmetic |
| `run_instruction()` | `c_backend/src/execution.c:14` | Execute with qubit mapping + inversion | Already handles multi-controlled gates |
| `allocator_alloc/free` | `c_backend/src/qubit_allocator.c` | Ancilla lifecycle | Phase 65 infrastructure |
| `hot_path_add_qq/cq` | `c_backend/src/hot_path_add.c` | C hot path dispatch | Phase 60 pattern, Phase 66 extended |
| `toffoli_QQ_add` | `c_backend/src/ToffoliAddition.c:140` | Uncontrolled QQ CDKM adder | Phase 66, reused by cCQ |
| `toffoli_CQ_add` | `c_backend/src/ToffoliAddition.c:210` | Uncontrolled CQ CDKM adder | Phase 66 |
| `toffoli_sequence_free` | `c_backend/src/ToffoliAddition.c:329` | Free CQ sequences | Phase 66 |

### Files to Modify

| File | Change | Estimated Lines |
|------|--------|-----------------|
| `c_backend/src/ToffoliAddition.c` | Add `toffoli_cQQ_add(bits)` and `toffoli_cCQ_add(bits, val)` | ~200 |
| `c_backend/include/toffoli_arithmetic_ops.h` | Declare new controlled functions | ~30 |
| `c_backend/src/hot_path_add.c` | Wire controlled Toffoli dispatch (remove QFT fallback for controlled) | ~80 |
| `c_backend/src/circuit_allocations.c` | Change default `arithmetic_mode = ARITH_TOFFOLI` | ~1 |
| `src/quantum_language/_core.pxd` | Declare `toffoli_cQQ_add`, `toffoli_cCQ_add` C functions | ~5 |

### Files NOT Changed

| File | Why No Change |
|------|---------------|
| `IntegerAddition.c` | QFT code stays as-is |
| `qint_arithmetic.pxi` | Hot path dispatch is in C; Cython layer transparent |
| `execution.c` | Already handles multi-controlled gates correctly |
| `gate.c` | `mcx()` already supports arbitrary control counts |
| `circuit_output.c` | Already exports 3+ control gates as `ctrl(n) @ x` |
| `setup.py` | `ToffoliAddition.c` already in build |

## Architecture Patterns

### Pattern 1: Controlled CDKM Adder (cQQ) via Gate Promotion

**What:** Convert every gate in the uncontrolled CDKM circuit to its controlled version by adding an extra control qubit.

**When to use:** For `toffoli_cQQ_add(bits)`.

**Algorithm:**
The uncontrolled CDKM adder uses CX and CCX gates in MAJ/UMA chains. The controlled version replaces:
- CX(target, ctrl) --> CCX(target, ctrl, ext_control)
- CCX(target, ctrl1, ctrl2) --> MCX(target, [ctrl1, ctrl2, ext_control])

This is the standard technique from quantum computing: to make any unitary U controlled by qubit c, make every gate in U's circuit controlled by c.

**Qubit layout for toffoli_cQQ_add(bits):**
```
[0..bits-1]       = register a (target, modified: a += b)
[bits..2*bits-1]  = register b (source, unchanged)
[2*bits]          = ancilla carry (bits >= 2 only, returned to |0>)
[2*bits+1]        = external control qubit
```

For bits == 1: single CCX(target=0, ctrl=1, ctrl=ext_control), no ancilla needed.

**Gate counts for n-bit controlled addition (n >= 2):**
- 3-controlled X (MCX) gates: 2n (from promoted CCX gates)
- CCX (Toffoli) gates: 4n (from promoted CX gates)
- Total gates: 6n
- Ancilla: 1 qubit + 1 control qubit
- Depth: 6n (sequential)

**Implementation approach:**
```c
// Controlled MAJ: same logic as MAJ but with external control
static void emit_cMAJ(sequence_t *seq, int *layer,
                      int a, int b, int c, int ext_ctrl) {
    // Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl) -- controlled b ^= c
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c, ext_ctrl);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl) -- controlled a ^= c
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: MCX(target=c, [a, b, ext_ctrl]) -- controlled c ^= (a AND b)
    qubit_t ctrls[3] = {a, b, ext_ctrl};
    mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    (*layer)++;
}

// Controlled UMA: same logic as UMA but with external control
static void emit_cUMA(sequence_t *seq, int *layer,
                      int a, int b, int c, int ext_ctrl) {
    // Step 1: MCX(target=c, [a, b, ext_ctrl])
    qubit_t ctrls[3] = {a, b, ext_ctrl};
    mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a, ext_ctrl);
    (*layer)++;
}
```

### Pattern 2: Controlled CQ Addition (cCQ) via Temp-Register Approach

**What:** Extend the Phase 66 temp-register CQ approach to be controlled.

**When to use:** For `toffoli_cCQ_add(bits, value)`.

**Algorithm:**
The uncontrolled CQ path (Phase 66) uses:
1. X-init temp register to classical value
2. Run QQ CDKM adder (temp acts as b-register)
3. X-cleanup temp register

The controlled version:
1. **Controlled** X-init: CX(target=temp[i], ctrl=ext_control) for each bit=1
2. **Controlled** QQ CDKM adder: Use cQQ variant with the external control
3. **Controlled** X-cleanup: CX(target=temp[i], ctrl=ext_control) for each bit=1

**Qubit layout for toffoli_cCQ_add(bits, value):**
```
[0..bits-1]       = temp register (controlled init to classical value, controlled cleanup)
[bits..2*bits-1]  = self register (target, modified: self += value)
[2*bits]          = carry ancilla (bits >= 2 only)
[2*bits+1]        = external control qubit
```

For bits == 1: single CX(target=0, ctrl=ext_control) if value's LSB is 1, identity if 0.

**Key insight:** The X-init and X-cleanup must also be controlled. If the control qubit is |0>, no temp register bits should be flipped (otherwise they'd be left in a non-zero state after the UMA sweep, since the controlled CDKM would not execute but the unconditional X-init would).

### Pattern 3: Hot Path Dispatch (Removing QFT Fallback)

**What:** The current `hot_path_add.c` has a comment "Toffoli mode with controlled: fall back to QFT path below" at lines 105 and 204. Phase 67 removes this fallback by routing controlled+Toffoli to the new `toffoli_cQQ_add` / `toffoli_cCQ_add`.

**Implementation for hot_path_add_qq controlled Toffoli path:**
```c
if (circ->arithmetic_mode == ARITH_TOFFOLI) {
    if (controlled) {
        // Controlled Toffoli path
        unsigned int tqa[256];
        // a-register [0..bits-1] = other (source, preserved)
        for (i = 0; i < other_bits; i++) tqa[i] = other_qubits[i];
        // b-register [bits..2*bits-1] = self (target, gets sum)
        for (i = 0; i < self_bits; i++) tqa[result_bits + i] = self_qubits[i];

        if (result_bits == 1) {
            // 1-bit: CCX(target=0, ctrl=1, ctrl=ext_control)
            tqa[2] = control_qubit;  // ext_control at index 2*1+1 = but wait, for 1-bit cQQ it's just CCX
            // ... handle 1-bit case
        } else {
            // Allocate 1 ancilla for carry
            qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
            tqa[2 * result_bits] = ancilla_qubit;
            tqa[2 * result_bits + 1] = control_qubit;

            sequence_t *toff_seq = toffoli_cQQ_add(result_bits);
            run_instruction(toff_seq, tqa, invert, circ);

            allocator_free(circ->allocator, ancilla_qubit, 1);
        }
    } else {
        // Uncontrolled Toffoli path (existing Phase 66 code)
        // ...
    }
    return;
}
// QFT path (for ARITH_QFT mode)
```

### Pattern 4: Default Mode Change (DSP-03)

**What:** Change `init_circuit()` to set `arithmetic_mode = ARITH_TOFFOLI` instead of `ARITH_QFT`.

**Impact analysis:**
- In `circuit_allocations.c` line 18: change `ARITH_QFT` to `ARITH_TOFFOLI`
- All existing tests that do NOT call `ql.option("fault_tolerant", True)` will now use Toffoli mode
- Tests that explicitly test QFT behavior must call `ql.option("fault_tolerant", False)` first
- The `option()` function in `_core.pyx` already supports setting `False` to restore QFT mode

**Risk:** This is a high-impact change that affects all arithmetic operations. Must be done LAST, after controlled variants are verified. The Phase 66 QFT fallback tests (TestToffoliQFTFallback) already demonstrate the switch works both ways.

**Backward compatibility:** The `ql.option('fault_tolerant', False)` call explicitly restores QFT behavior. Any test or user code that needs QFT can opt in.

### Anti-Patterns to Avoid

- **Anti-Pattern 1: Separate controlled MAJ/UMA chains that duplicate logic.** Instead, create `emit_cMAJ` / `emit_cUMA` helpers that mirror the uncontrolled versions but add the external control to every gate. This keeps the code DRY and makes the correspondence obvious.

- **Anti-Pattern 2: Controlled CQ with unconditional X-init.** The temp register X-init and X-cleanup MUST be controlled. If they are unconditional, the temp register will be left dirty when the control qubit is |0> because the controlled CDKM does nothing but the X gates already flipped the temp bits.

- **Anti-Pattern 3: Putting control qubit at index 2*bits for Toffoli cQQ.** This collides with the ancilla carry qubit, which is already at `2*bits` in the uncontrolled layout. The control qubit must go at `2*bits+1` (after the ancilla).

- **Anti-Pattern 4: Changing the default mode before controlled variants work.** The default mode change (DSP-03) must be the LAST task, after cQQ and cCQ Toffoli variants are verified. Otherwise, all controlled operations silently break.

- **Anti-Pattern 5: Caching controlled CQ sequences.** Like uncontrolled CQ, controlled CQ sequences are value-dependent and must be generated fresh per call, freed by the caller via `toffoli_sequence_free()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-controlled X gate | Custom 3-control implementation | `mcx()` from `gate.c` | Already handles arbitrary controls, maps correctly in `run_instruction()` |
| Ancilla allocation | Manual qubit tracking | `allocator_alloc()` + `allocator_free()` | Phase 65 infrastructure with block reuse |
| Controlled CQ classical init | Separate init logic | CX gates (controlled X) for X-init/cleanup | Same pattern as uncontrolled but with extra control |
| OpenQASM export of 3-ctrl gates | Custom export code | Existing `ctrl(n) @ x` path in `circuit_output.c` | Already handles NumControls > 2 |
| Gate inversion for subtraction | Separate controlled subtraction | `run_instruction(seq, qa, invert=1, circ)` | Phase 65 self-inverse handling works for CCX, MCX |

**Key insight:** The entire infrastructure for multi-controlled gates already exists. The `gate_t` struct supports `large_control` for 3+ controls, `run_instruction()` remaps multi-controlled gates, and the QASM export handles `ctrl(n) @ x`. This phase's main work is generating the right gate sequences and wiring the dispatch.

## Common Pitfalls

### Pitfall 1: Control Qubit Position Collision with Ancilla

**What goes wrong:** Placing the external control qubit at virtual index `2*bits` collides with the ancilla carry qubit (already at `2*bits` in the CDKM layout).

**Why it happens:** The uncontrolled QQ CDKM uses `[0..bits-1, bits..2*bits-1, 2*bits]` for a, b, ancilla. The QFT cQQ_add places control at `2*bits` because it has no ancilla. Copying the QFT control position to the Toffoli path causes a collision.

**How to avoid:** For Toffoli cQQ: ancilla at `2*bits`, control at `2*bits+1`. Document the layout clearly in both the sequence generator and the hot path dispatch. Test with `assert(ancilla_qubit != control_qubit)` or equivalent.

**Warning signs:** All controlled additions produce garbage. The ancilla qubit gets entangled with the control qubit.

### Pitfall 2: Unconditional X-init in Controlled CQ

**What goes wrong:** If the temp register is initialized with unconditional X gates (as in uncontrolled CQ), the control qubit does not gate the initialization. When control=|0>, the CDKM does nothing, but the temp bits are already flipped. The X-cleanup then un-flips them, but the intermediate state had dirty temp qubits operating through the CDKM chain -- which does nothing, so the temp register is left in the classical state after cleanup. But the CDKM's carry qubit may have been affected by the non-zero temp register through the controlled MAJ chain... actually, since the controlled CDKM does nothing when control=|0>, the final state is correct. BUT: this creates unnecessary entanglement and wasted gate operations.

**Actually, the real problem is:** If we use the SAME CDKM core for the controlled case (i.e., run the controlled QQ CDKM on the temp+self registers), the X-init and X-cleanup MUST be controlled. Otherwise, when control=|0>:
- X-init flips temp bits unconditionally
- Controlled CDKM does nothing (all gates gated by control)
- X-cleanup flips temp bits back
- Result: correct (self unchanged, temp cleaned), but uses unnecessary gates

Actually, this is technically correct but wasteful. The more serious concern: if there are intermediate operations between init and the CDKM, unconditional X-init could create entanglement issues. Since there are NO intermediate operations in our implementation, unconditional X-init/cleanup is actually safe but wasteful.

**Recommendation:** Use controlled X-init/cleanup (CX gates instead of X gates) for correctness purity. This matches the fault-tolerant philosophy of minimizing unnecessary operations.

**How to avoid:** Use `cx(target=temp[i], control=ext_control)` instead of `x(target=temp[i])` for init and cleanup.

### Pitfall 3: 1-bit Controlled Addition Edge Case

**What goes wrong:** For 1-bit cQQ, the operation is "controlled a[0] ^= b[0]", which is a CCX gate. For 1-bit cCQ, it's "controlled a[0] ^= value", which is a CX if value=1 or identity if value=0. No ancilla needed.

**Why it happens:** The general CDKM path allocates ancilla for carry, but 1-bit has no carry.

**How to avoid:** Handle 1-bit as explicit special case in both controlled functions. Skip ancilla allocation in the hot path for 1-bit controlled addition.

### Pitfall 4: MCX Gate Memory Management in Sequences

**What goes wrong:** The `mcx()` function allocates `large_control` dynamically for 3+ controls. The sequence's gate_t stores this pointer. If the sequence is freed via `toffoli_sequence_free()`, the `large_control` arrays inside gates are NOT freed (only `seq->seq[i]` arrays are freed, not individual gate internals).

**Why it happens:** The existing `toffoli_sequence_free()` (and the general `free` pattern for sequences) only frees the layer arrays, not gate-internal allocations like `large_control`.

**How to avoid:** Two approaches:
1. Extend `toffoli_sequence_free()` to iterate gates and free `large_control` for any gate with NumControls > 2.
2. For cached sequences (cQQ), this is a minor leak since they persist for program lifetime. For per-call sequences (cCQ), this is a real leak that must be fixed.

**Recommendation:** Option 1 is cleaner. Add a gate-level cleanup loop in `toffoli_sequence_free()`.

### Pitfall 5: Register Swap in Hot Path for Controlled QQ

**What goes wrong:** The uncontrolled Toffoli QQ path in `hot_path_add.c` swaps the register positions (other at a-register, self at b-register) because CDKM stores the sum in the b-register. The controlled path must do the SAME swap, plus add the control qubit.

**Why it happens:** Copy-paste from the QFT controlled path, which does NOT swap registers (QFT stores result in the first register).

**How to avoid:** The controlled Toffoli QQ dispatch must mirror the uncontrolled Toffoli QQ dispatch's register swap. Test by verifying that `a + b == b + a` for controlled addition.

### Pitfall 6: Default Mode Change Breaking Existing Tests

**What goes wrong:** Changing default from ARITH_QFT to ARITH_TOFFOLI means ALL existing arithmetic tests now use Toffoli mode. Tests that rely on QFT-specific behavior (e.g., checking for H/P gates, counting specific gate types) will fail.

**Why it happens:** The test suite was developed with QFT as default.

**How to avoid:** After the default change, run the full test suite. Fix any QFT-specific tests by explicitly setting `ql.option('fault_tolerant', False)` before the test. The Phase 66 test `TestToffoliQFTFallback` already demonstrates this pattern.

**Warning signs:** Tests that check `gate_counts['H'] > 0` or `gate_counts['P'] > 0` will fail because Toffoli mode produces zero H/P gates.

## Code Examples

### Complete toffoli_cQQ_add Implementation

```c
// Source: Derived from ToffoliAddition.c toffoli_QQ_add + controlled gate promotion
static sequence_t *precompiled_toffoli_cQQ_add[65] = {NULL};

sequence_t *toffoli_cQQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence - DO NOT FREE
    //
    // Qubit layout:
    //   [0..bits-1]       = register a (target, modified: a += b)
    //   [bits..2*bits-1]  = register b (source, unchanged)
    //   [2*bits]          = ancilla carry (bits >= 2 only)
    //   [2*bits+1]        = external control qubit

    if (bits < 1 || bits > 64) return NULL;
    if (precompiled_toffoli_cQQ_add[bits] != NULL)
        return precompiled_toffoli_cQQ_add[bits];

    if (bits == 1) {
        // Controlled 1-bit: CCX(target=0, ctrl1=1, ctrl2=ext_control=2)
        sequence_t *seq = alloc_sequence(1);
        if (seq == NULL) return NULL;
        // For 1-bit cQQ, ext_control is at index 2 (=2*1+1-1? No: 2*1=2 -> 2*bits+1=3)
        // Wait: for 1-bit, no ancilla, so control at 2*bits = 2
        // Actually, must decide: for 1-bit, no ancilla needed.
        // Layout: [0]=a, [1]=b, [2]=ext_control
        ccx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1, 2);
        seq->used_layer = 1;
        precompiled_toffoli_cQQ_add[bits] = seq;
        return seq;
    }

    // General case: 6*bits layers
    int num_layers = 6 * bits;
    int ext_ctrl = 2 * bits + 1;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) return NULL;

    int layer = 0;
    int ancilla = 2 * bits;

    // Forward cMAJ sweep
    emit_cMAJ(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);
    for (int i = 1; i < bits; i++) {
        emit_cMAJ(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Reverse cUMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }
    emit_cUMA(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);

    seq->used_layer = layer;
    precompiled_toffoli_cQQ_add[bits] = seq;
    return seq;
}
```

### Hot Path Controlled QQ Dispatch

```c
// In hot_path_add_qq, inside ARITH_TOFFOLI block:
if (controlled) {
    unsigned int tqa[256];
    sequence_t *toff_seq;

    if (result_bits == 1) {
        // 1-bit controlled: CCX(target=a[0], ctrl1=b[0], ctrl2=control_qubit)
        // Layout: [0]=self(target), [1]=other(source), [2]=control
        tqa[0] = self_qubits[0];   // Not swapped for 1-bit (XOR is symmetric)
        tqa[1] = other_qubits[0];
        tqa[2] = control_qubit;

        toff_seq = toffoli_cQQ_add(result_bits);
        if (toff_seq == NULL) return;
        run_instruction(toff_seq, tqa, invert, circ);
    } else {
        // Swap registers: a-register = other (source), b-register = self (target)
        for (i = 0; i < other_bits; i++) tqa[i] = other_qubits[i];
        for (i = 0; i < self_bits; i++) tqa[result_bits + i] = self_qubits[i];

        // Allocate 1 ancilla for carry
        qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
        if (ancilla_qubit == (qubit_t)-1) return;

        tqa[2 * result_bits] = ancilla_qubit;
        tqa[2 * result_bits + 1] = control_qubit;

        toff_seq = toffoli_cQQ_add(result_bits);
        if (toff_seq == NULL) {
            allocator_free(circ->allocator, ancilla_qubit, 1);
            return;
        }
        run_instruction(toff_seq, tqa, invert, circ);
        allocator_free(circ->allocator, ancilla_qubit, 1);
    }
    return;
}
```

### Controlled CQ Toffoli Dispatch

```c
// In hot_path_add_cq, inside ARITH_TOFFOLI block:
if (controlled) {
    sequence_t *toff_seq;
    if (self_bits == 1) {
        // 1-bit controlled CQ: CX(target=self[0], ctrl=control_qubit) if value&1
        // Layout: [0]=self, [1]=ext_control
        unsigned int tqa[2];
        tqa[0] = self_qubits[0];
        tqa[1] = control_qubit;
        toff_seq = toffoli_cCQ_add(self_bits, classical_value);
        if (toff_seq == NULL) return;
        run_instruction(toff_seq, tqa, invert, circ);
        toffoli_sequence_free(toff_seq);
    } else {
        // Allocate temp + carry ancilla: self_bits + 1 qubits
        qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 1, true);
        if (temp_start == (qubit_t)-1) return;

        unsigned int tqa[256];
        // [0..self_bits-1] = temp
        for (i = 0; i < self_bits; i++) tqa[i] = temp_start + i;
        // [self_bits..2*self_bits-1] = self
        for (i = 0; i < self_bits; i++) tqa[self_bits + i] = self_qubits[i];
        // [2*self_bits] = carry
        tqa[2 * self_bits] = temp_start + self_bits;
        // [2*self_bits+1] = ext_control
        tqa[2 * self_bits + 1] = control_qubit;

        toff_seq = toffoli_cCQ_add(self_bits, classical_value);
        if (toff_seq == NULL) {
            allocator_free(circ->allocator, temp_start, self_bits + 1);
            return;
        }
        run_instruction(toff_seq, tqa, invert, circ);
        toffoli_sequence_free(toff_seq);
        allocator_free(circ->allocator, temp_start, self_bits + 1);
    }
    return;
}
```

### Test Pattern for Controlled Toffoli Addition

```python
# Verification test for controlled QQ Toffoli addition
def test_cqq_toffoli_controlled_add(width):
    """Test controlled QQ Toffoli addition with control=|1>."""
    for a in range(1 << width):
        for b in range(1 << width):
            gc.collect()
            ql.circuit()
            ql.option("fault_tolerant", True)

            qa = ql.qint(a, width=width)
            qb = ql.qint(b, width=width)
            ctrl = ql.qint(1, width=1)  # control = |1>

            with ctrl:
                qa += qb  # Controlled addition

            expected = (a + b) % (1 << width)
            # ... simulate and verify ...

def test_cqq_toffoli_controlled_noop(width):
    """Test controlled QQ Toffoli addition with control=|0> (should be no-op)."""
    for a in range(1 << width):
        for b in range(1 << width):
            gc.collect()
            ql.circuit()
            ql.option("fault_tolerant", True)

            qa = ql.qint(a, width=width)
            qb = ql.qint(b, width=width)
            ctrl = ql.qint(0, width=1)  # control = |0>

            with ctrl:
                qa += qb  # Should NOT add

            expected = a  # Unchanged
            # ... simulate and verify ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Controlled addition falls back to QFT when ARITH_TOFFOLI | Controlled addition dispatches to Toffoli-native cQQ/cCQ | Phase 67 | Full Toffoli coverage for all addition variants |
| Default arithmetic mode is ARITH_QFT | Default arithmetic mode is ARITH_TOFFOLI | Phase 67 (DSP-03) | Toffoli arithmetic out-of-the-box |
| `hot_path_add.c` checks `!controlled` for Toffoli | `hot_path_add.c` handles both controlled and uncontrolled Toffoli | Phase 67 | No more QFT fallback for controlled ops |

**Phase 66 established the foundation:** Uncontrolled QQ and CQ Toffoli adders, hot path dispatch pattern, arithmetic mode enum. Phase 67 completes the story.

## Open Questions

1. **Should toffoli_cQQ_add be cached?**
   - What we know: The uncontrolled `toffoli_QQ_add` is cached per width. The controlled version has the same structure (width-dependent, not value-dependent).
   - Recommendation: YES, cache `toffoli_cQQ_add` per width, just like the uncontrolled version. Use a separate cache array `precompiled_toffoli_cQQ_add[65]`.

2. **1-bit controlled cQQ layout: control at index 2 or 3?**
   - What we know: For 1-bit uncontrolled QQ, the layout is `[0]=a, [1]=b`, no ancilla. For general controlled cQQ, the layout is `[0..bits-1]=a, [bits..2*bits-1]=b, [2*bits]=ancilla, [2*bits+1]=control`.
   - What's unclear: For 1-bit, there's no ancilla. Should control go at index 2 (matching `2*1+0`, which is the "ancilla slot" that doesn't exist) or index 2 (matching `2*bits`, the first free slot)?
   - Recommendation: For consistency, 1-bit controlled uses `[0]=a, [1]=b, [2]=control` (no ancilla slot). The hot path must handle this as a special case.

3. **large_control memory leak in sequence_free?**
   - What we know: `mcx()` allocates `large_control` for 3+ controls. Current `toffoli_sequence_free()` does not free gate-internal allocations.
   - Recommendation: Extend `toffoli_sequence_free()` to iterate all gates and free `large_control` where NumControls > 2. This is critical for cCQ (per-call sequences) and a good practice for cQQ (cached, but still should be clean).

4. **How to verify controlled Toffoli correctness?**
   - What we know: The Phase 66 test infrastructure uses Qiskit AerSimulator with statevector simulation.
   - Recommendation: Test both control=|1> (addition happens) and control=|0> (no-op) exhaustively for widths 1-4. The `with ctrl:` context manager in Python sets the `_controlled` flag which flows through to `hot_path_add_qq/cq`.

5. **Impact of ARITH_TOFFOLI default on multiplication?**
   - What we know: `hot_path_mul.c` does NOT check `arithmetic_mode`. It always uses QFT multiplication.
   - What's unclear: When default changes to ARITH_TOFFOLI, multiplication still uses QFT. This is fine because Toffoli multiplication is out of scope for Phase 67.
   - Recommendation: No change needed for multiplication. The `arithmetic_mode` flag only affects addition dispatch currently.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `ToffoliAddition.c` (Phase 66 CDKM implementation), `hot_path_add.c` (dispatch pattern with controlled fallback), `gate.c` (`mcx()` multi-controlled gate), `execution.c` (multi-control remapping in `run_instruction`), `circuit_output.c` (`ctrl(n) @ x` QASM export)
- Phase 66 RESEARCH.md: CDKM algorithm, MAJ/UMA decomposition, qubit layouts
- Phase 66 VERIFICATION.md: All 5 success criteria verified, CQ temp-register approach confirmed

### Secondary (MEDIUM confidence)
- [Cuccaro et al., "A new quantum ripple-carry addition circuit" (2004)](https://arxiv.org/abs/quant-ph/0410184) -- Original CDKM paper, gate decomposition
- [IBM Quantum CDKMRippleCarryAdder docs](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.CDKMRippleCarryAdder) -- Reference implementation
- [Qiskit CDKMRippleCarryAdder source](https://github.com/Qiskit/qiskit/blob/main/qiskit/circuit/library/arithmetic/adders/cdkm_ripple_carry_adder.py) -- Qiskit uses `circuit.control()` to create controlled versions

### Tertiary (LOW confidence)
- Controlled gate promotion technique (CX->CCX, CCX->C3X): standard quantum computing technique but not verified from a single authoritative reference; derived from first principles and consistent with Qiskit's `circuit.control()` approach

## Metadata

**Confidence breakdown:**
- Controlled CDKM algorithm (gate promotion): HIGH -- standard technique, infrastructure verified in codebase
- Qubit layout contracts: HIGH -- directly inspected all relevant hot path and sequence code
- Hot path dispatch wiring: HIGH -- Phase 66 established the pattern, controlled path is analogous
- Default mode change impact: MEDIUM -- full test suite run needed to identify QFT-specific test failures
- MCX/large_control memory management: HIGH -- directly inspected gate.c and execution.c
- 1-bit edge cases: MEDIUM -- needs implementation-time validation

**Research date:** 2026-02-14
**Valid until:** 2026-04-14 (stable algorithms, stable codebase -- 60-day validity)
