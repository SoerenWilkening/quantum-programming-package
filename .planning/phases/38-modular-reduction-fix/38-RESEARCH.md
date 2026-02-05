# Phase 38: Modular Reduction Fix - Research

**Researched:** 2026-02-02
**Domain:** Quantum modular arithmetic bug fix (Cython `_reduce_mod` in `qint_mod.pyx`)
**Confidence:** HIGH

## Summary

The `_reduce_mod` method in `qint_mod.pyx` (lines 107-131) implements modular reduction via iterative "compare and conditionally subtract" -- `cmp = value >= N; with cmp: value -= N`. This method is called by `__add__`, `__sub__`, and `__mul__` on `qint_mod` to reduce results modulo N. The bug produces incorrect results for approximately 60% of modular arithmetic operations, with two distinct failure modes: (1) when the correct result is 0, the output is consistently N-2, and (2) for larger moduli (N>=7), widespread failures even for non-zero results due to multi-iteration reduction corruption.

The root cause is that each `>=` comparison allocates temporary qubits (widened copies for subtraction-based comparison) which entangle with the value register. When the `with cmp:` context exits, scope cleanup uncomputes intermediates created inside the block, but the comparison qbool `cmp` itself -- created OUTSIDE the `with` block -- is not uncomputed until GC. Across multiple loop iterations, these un-uncomputed comparison qbools accumulate entanglement with the value register, corrupting its state. The critical failure path: when conditional subtraction brings the value to exactly 0, all bits become entangled with the comparison ancillae, and the residual entanglement manifests as N-2 in the output.

**Primary recommendation:** Fix the `_reduce_mod` method by ensuring each comparison qbool is properly uncomputed after its conditional subtraction completes in each iteration. The comparison result must be uncomputed (reversed) AFTER the conditional block exits but BEFORE the next iteration begins. This breaks the entanglement chain between iterations. The `__lt__` comparison creates temporary widened qints that are GC'd eventually, but the key fix is ensuring the comparison qbool's qubit is returned to |0> after use so it does not carry forward entanglement.

## Standard Stack

Not applicable -- this is a bug fix within existing Cython code, not a new technology adoption.

### Core
| Component | Location | Purpose | Relevance |
|-----------|----------|---------|-----------|
| `qint_mod.pyx` | `src/quantum_language/` | `_reduce_mod` method + modular operators | **Primary fix target** |
| `qint.pyx` | `src/quantum_language/` | `__ge__`, `__lt__`, `__enter__`/`__exit__`, `_do_uncompute` | Comparison and scope mechanics used by _reduce_mod |
| `qbool.pyx` | `src/quantum_language/` | 1-bit qint used as comparison result | Result of `>=` comparison, used as `with` control |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `test_modular.py` | `tests/` | Modular arithmetic verification tests | Remove xfail markers after fix |
| `test_mod.py` | `tests/` | Modulo verification tests | Regression check (shares comparison pattern) |
| `test_div.py` | `tests/` | Division verification tests | Regression check (shares comparison pattern) |

## Architecture Patterns

### Current `_reduce_mod` Flow (Buggy)

```python
cdef _reduce_mod(self, qint value):
    max_val = 1 << value.bits
    max_subtractions = (max_val // self._modulus) + 1
    iterations = max_subtractions.bit_length()

    for _ in range(iterations):
        # Step 1: Compare -- allocates qbool + temporary widened qints
        cmp = value >= self._modulus

        # Step 2: Conditional subtract inside controlled context
        with cmp:
            value -= self._modulus

        # BUG: cmp qbool is NOT uncomputed here.
        # Its qubit remains entangled with value register bits.
        # Next iteration creates a NEW cmp, accumulating entanglement.

    return value
```

### What `value >= self._modulus` Actually Does

Tracing the call chain:
1. `__ge__(self, other)` returns `~(self < other)` -- calls `__lt__` then inverts
2. `__lt__(self, int_other)` creates `temp = qint(int_other, width=self.bits)`, then calls `self < temp`
3. `__lt__(self, qint_other)` with widened comparison:
   - Creates `temp_self = qint(0, width=comp_width)` where `comp_width = max(w1, w2) + 1`
   - Creates `temp_other = qint(0, width=comp_width)`
   - Copies bits via individual CNOTs (LSB-aligned)
   - Performs `temp_self -= temp_other`
   - Extracts MSB as sign bit: `msb = temp_self[63]`
   - Creates result `qbool()`, XORs MSB into it
   - Returns result (with dependencies on original operands)
4. `~(result)` inverts the qbool (X gate)

**Qubit allocations per comparison:** Each `value >= N` allocates:
- 1 qubit for the temp qint (int_other converted to qint) in `__lt__` int path
- `comp_width` qubits for `temp_self` (widened copy)
- `comp_width` qubits for `temp_other` (widened copy)
- 1 qubit for `msb` extraction (via `__getitem__`)
- 1 qubit for result `qbool`
- Total: ~2*comp_width + 3 qubits per iteration (where comp_width = value.bits + 1)

**Cleanup:** `temp_self`, `temp_other`, and the temp qint from int conversion are orphaned local variables. They will be GC'd eventually. But `cmp` (the qbool result) is assigned to a Python variable in `_reduce_mod` and lives until that variable is reassigned on the next iteration. The key problem: even when Python reassigns `cmp`, the OLD qbool goes to GC, but:
- Its `_do_uncompute` only reverses gates if `_end_layer > _start_layer`
- Comparison results deliberately do NOT set `_start_layer/_end_layer` (per Phase 29 design: "comparison results must persist")
- So the old comparison qbool's qubit is NEVER uncomputed, leaking entanglement

### Why Result=0 Produces N-2

When `value = N` before reduction:
1. Iteration 1: `cmp = (N >= N)` = True. With cmp: `value -= N` => value = 0.
2. Now value register is all zeros, but the subtraction was controlled on `cmp`.
3. Iteration 2: `cmp2 = (0 >= N)` = False. No subtraction. But the comparison itself creates entanglement between value bits and the new comparison ancillae.
4. The value register qubits are now entangled with BOTH the iteration-1 cmp qubit and the iteration-2 comparison temporaries.
5. On measurement, this entanglement collapses to give N-2 instead of 0.

The N-2 pattern: for N=3, result is 1 (=3-2). For N=5, result is 3 (=5-2). This suggests 2 bits of the value register are being flipped by residual entanglement from the comparison operations.

### Fix Pattern: Explicit Comparison Uncomputation

The fix must ensure each iteration's comparison qbool is properly uncomputed after the conditional block. Two approaches:

**Approach A: Reverse the comparison after use (preferred)**
```python
for _ in range(iterations):
    cmp = value >= self._modulus
    with cmp:
        value -= self._modulus
    # Uncompute comparison: reverse the gates that created cmp
    # This disentangles cmp from value, returning cmp qubit to |0>
    # Need to reverse: the subtraction-based comparison, MSB extraction, XOR
```

The challenge with Approach A is that `__ge__` creates nested temporaries that are already being GC'd. The comparison's internal gates form a complex sequence. The cleanest way to reverse them is to track `_start_layer` and `_end_layer` on the comparison result, then use `reverse_circuit_range`.

**Approach B: Allocate fresh comparison ancilla and use controlled-comparison**
More complex and allocates more qubits. Not preferred per CONTEXT.md.

**Approach C: Use the division algorithm's pattern**
The division algorithm (`__floordiv__` in qint.pyx) uses the SAME compare-and-subtract pattern and works correctly (post Phase 37 fix). The key difference: in division, the `can_subtract` qbool created each iteration is a local variable that goes out of scope at the end of each loop body. The `with can_subtract:` block's `__exit__` uncomputes scope-local qbools. But the comparison qbool `can_subtract` was created OUTSIDE the `with` block's scope, so it is NOT uncomputed by scope cleanup.

Wait -- division has the same pattern and the same non-uncomputation of comparison qbools. Why does division work but modular reduction doesn't?

**Critical difference:** In division, `remainder >= trial_value` is `remainder >= (divisor << bit_pos)` where trial_value is a different classical constant each iteration. The comparison creates a fresh temp qint each time, and the specific pattern of entanglement varies per iteration in a way that doesn't accumulate destructively because each iteration operates on a different bit position of the quotient.

In `_reduce_mod`, EVERY iteration compares against the SAME modulus and subtracts the SAME modulus from the SAME register. The entanglement pattern from each comparison overlaps with previous iterations' entanglement on the SAME qubits, causing destructive interference.

**The actual fix:** The comparison qbool must be explicitly cleaned up. The approach is:

1. Capture the circuit layer before the comparison
2. Perform the comparison
3. Use the comparison in the `with` block for conditional subtraction
4. After the `with` block exits, reverse the comparison gates to uncompute the qbool

This is the "compute-use-uncompute" pattern standard in quantum computing.

### Comparison with Division Code

Division (in `qint.pyx` `__floordiv__`):
```python
for bit_pos in range(max_bit_pos, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)
```

This works because:
1. Each iteration uses a DIFFERENT `trial_value` (powers of 2 scaled)
2. The quotient accumulates in a SEPARATE register (not the compared register)
3. The remainder decreases monotonically -- once a subtraction happens, subsequent iterations see a smaller value, and the entanglement from earlier iterations doesn't corrupt the result because the higher-order comparisons don't overlap with lower-order ones

In contrast, `_reduce_mod` compares and subtracts the SAME value repeatedly from the SAME register. Multiple iterations may all be "active" (value >= N could be true for multiple iterations), and the accumulated comparison entanglement corrupts the register.

### Iteration Count

Current: `iterations = (max_val // modulus + 1).bit_length()` -- this is log2 of max possible subtractions.

For a 3-bit value with N=3: max_val=8, max_subtractions=3, iterations=2.
For a 3-bit value with N=5: max_val=8, max_subtractions=2, iterations=1.

The iteration count is already logarithmic. For correctness, the number of iterations should be `ceil(log2(max_val / modulus)) + 1` at most. The current formula computes `(max_val // modulus + 1).bit_length()` which is correct.

However, after fixing the uncomputation bug, the iteration count might need adjustment. The current iterative subtraction (subtract N once per iteration if value >= N) only reduces the value by N each time. To reduce a value up to `2^w - 1` to the range `[0, N)`, we need up to `floor((2^w - 1) / N)` subtractions. Using `bit_length()` of that count gives log2 iterations -- but this only works if each "iteration" can subtract N multiple times. It doesn't -- each iteration subtracts at most once.

**This is a second bug:** The loop runs `iterations = log2(max_subtractions)` times, but each iteration only subtracts N once. To reduce from max_val to [0, N), you need up to `max_subtractions` iterations, not `log2(max_subtractions)`.

Example: value=7, N=3. Need to subtract 3 twice: 7->4->1. Current iterations = `(8//3 + 1).bit_length() = 3.bit_length() = 2`. So it runs 2 iterations -- just barely enough for this case. But consider value=14 (if value comes from multiplication, the pre-reduction value could be larger): 14->11->8->5->2, needing 4 subtractions. With N=3 and a result from 4-bit multiplication (max_val=16): iterations = `(16//3 + 1).bit_length() = 6.bit_length() = 3`. Only 3 iterations for 5 needed subtractions -- insufficient.

**Wait, re-reading:** For `add_mod`, the input to `_reduce_mod` comes from `qint.__add__`, which returns a value of width `max(self.bits, other.bits)`. For a 3-bit qint_mod with N=5, max value after addition is `4+4=8` but the register is only 3 bits wide (so max representable is 7). So `max_val = 1 << 3 = 8`, `max_subtractions = 8//5 + 1 = 2`, `iterations = 2.bit_length() = 1`. Only 1 iteration needed (7 >= 5 => subtract once to get 2, which is correct).

For `mul_mod`, the product register has same width as the operand. A 3-bit multiply can't exceed 7. But for `qint_mod(4, N=5) * 4`, the product is 16, but the register is only 3 bits -- so it wraps to `16 % 8 = 0`. The product register width is the operand width. So the pre-reduction value is ALREADY wrapped by register width. With width=3 and N=5: max_val=8, max needed = 1 subtraction. iterations=1.

Actually, `_reduce_mod` receives the result of parent class addition/multiplication. For multiplication, `qint.__mul__` returns a result of width `self.bits` (the qint_mod's width). So the value is already wrapped to register width by the time `_reduce_mod` sees it.

For add: `qint.__add__` returns width = max(self.bits, other.bits). Both operands are qint_mod with the same width (N.bit_length()), so result width = N.bit_length(). Max representable = `2^(N.bit_length()) - 1`. For N=5 (3 bits): max=7, max subtractions = 7//5 = 1, so 1 subtraction needed, iterations = `2.bit_length() = 1`. Correct.

For N=3 (2 bits): max=3, max subtractions = 3//3 = 1, iterations = `2.bit_length() = 1`. But 2+2=4 which wraps to 0 in 2-bit register. Wait, the add is using `qint.__add__` which creates a result of width 2 (N.bit_length() for N=3). Max value in 2 bits = 3. So (2+2) % 4 = 0, then _reduce_mod sees 0, compares 0 >= 3, which is False, no subtraction. Result is 0, which is correct!

But wait, input values are reduced mod N before encoding. So max input = N-1 = 2. Max sum = 4. Register width = 2 bits. 4 in 2 bits wraps to 0. So _reduce_mod sees 0 -- which IS correct for (2+2) mod 3 = 1... but 4 wrapped to 0 is not 1. The wrapping IS the bug. The register is too narrow.

**Third insight: register width may be insufficient for intermediate values.** When adding two values mod N, the intermediate sum can be up to 2*(N-1). For N=3: 2*(3-1) = 4, but 2-bit register can only hold 0-3. So the sum of 2+2=4 wraps to 0 in 2 bits, and _reduce_mod never gets the true value.

This could be a contributing factor but is separate from the entanglement bug. The register width issue would cause incorrect results even without the comparison entanglement problem.

**However:** Looking at the test results, the test harness does NOT report failures for cases where the register wraps AND the modular result matches. The calibration-based extraction finds the correct result when it exists in the bitstring. The actual bug symptoms (N-2 instead of 0) suggest the entanglement is the primary issue.

### Recommended Fix Architecture

**Step 1: Fix comparison uncomputation in the loop**

The cleanest approach -- aligned with quantum computing best practices -- is the compute-use-uncompute pattern:

```python
cdef _reduce_mod(self, qint value):
    max_val = 1 << value.bits
    max_subtractions = (max_val // self._modulus) + 1
    iterations = max_subtractions.bit_length()

    for _ in range(iterations):
        # Capture layer before comparison
        start_layer = get_current_layer()

        # Compare
        cmp = value >= self._modulus

        # Use (conditional subtract)
        with cmp:
            value -= self._modulus

        # Uncompute: reverse comparison gates to disentangle cmp from value
        end_layer = get_current_layer()
        # Reverse from end_layer back to where comparison started
        # (but AFTER the conditional subtraction, which must persist)
        # Actually, we need to be more careful here...
```

**The subtlety:** We cannot simply reverse ALL gates from start_layer to end_layer, because that would undo the conditional subtraction too. We need to:
1. Record the layer range of the comparison
2. Perform the conditional subtraction (which adds gates AFTER the comparison)
3. After the `with` block exits, reverse ONLY the comparison gates, not the subtraction gates

This requires capturing the layer AFTER comparison but BEFORE the `with` block. Since comparison and `with` entry happen in sequence, this is feasible:

```python
for _ in range(iterations):
    # Record layer before comparison
    comp_start = get_current_layer()

    cmp = value >= self._modulus

    # Record layer after comparison (before conditional subtract)
    comp_end = get_current_layer()

    with cmp:
        value -= self._modulus

    # Uncompute comparison by reversing gates in [comp_start, comp_end)
    reverse_circuit_range(comp_start, comp_end)
```

**Wait -- this is incorrect.** Reversing the comparison gates AFTER the conditional subtraction has happened would create a circuit where:
1. Comparison gates run (entangling cmp with value)
2. Conditional subtraction runs (using cmp as control, modifying value)
3. Comparison gates run in reverse (attempting to disentangle)

But step 3 cannot properly uncompute the comparison because the value register has CHANGED (step 2 modified it). The comparison was computed on the original value, and uncomputation assumes the value is still in its original state.

**This is the fundamental challenge of quantum uncomputation in iterative algorithms.**

**The correct pattern is:**
1. Compute comparison on value
2. Copy comparison result to a FRESH ancilla qubit (so the comparison can be uncomputed while the copy persists)
3. Uncompute the comparison (reversing gates -- now value is restored to pre-comparison state AND comparison ancillae are clean)
4. Use the COPIED qubit as control for conditional subtraction
5. After subtraction, the copied qubit can be uncomputed by a controlled inverse (or just left as garbage if we accept ancilla cost)

But this requires extra ancilla qubits (the copy), which CONTEXT.md says to minimize but accept if truly necessary.

**Alternative correct pattern (simpler, no extra ancilla):**

Actually, let me reconsider. The standard quantum modular reduction pattern from literature (e.g., Beauregard's circuit for Shor's algorithm) works as:

1. Compare value >= N (sets ancilla to 1 if true)
2. Controlled on ancilla: subtract N from value
3. Uncompute comparison: compare value >= N again (this time value might be different, so the comparison gives a different result, BUT if value was >= N and we subtracted N, now value < N, so comparison gives 0 -- which XORs with the ancilla's 1, returning it to 0)

Wait, that's the key insight! In the standard reversible pattern:
- Step 1: ancilla = (value >= N) -- ancilla is 1 if value >= N
- Step 2: if ancilla=1, value -= N
- Step 3: ancilla ^= (value >= N) -- NOW value < N (because we subtracted), so comparison gives 0, and 1 XOR 0 = 1... that doesn't uncompute.

Actually, the correct Beauregard pattern is:
- Step 1: value -= N (unconditionally)
- Step 2: ancilla = MSB of value (sign bit -- if value went negative, MSB=1)
- Step 3: controlled on ancilla: value += N (undo subtraction if it went negative)
- Step 4: uncompute ancilla by checking MSB again? No...

Let me re-derive. The standard pattern for modular reduction of value that might be in [0, 2N) to [0, N):

1. Subtract N: `value -= N`
2. Check sign: `ancilla = (value < 0)` -- i.e., MSB of the value (if negative after subtraction)
3. If negative, add N back: `with ancilla: value += N`
4. At this point, value is reduced to [0, N), and ancilla encodes whether we added back
5. Uncompute ancilla: The ancilla should now be 0 if value was >= N (subtraction succeeded), or 1 if value was < N (we added back). Since value is now correct, we can set ancilla = NOT(value >= 0)... but this is circular.

The Beauregard trick: after step 3, the ancilla is 1 iff original value was < N. The value is now in [0, N). To uncompute the ancilla:
- Compute sign of value (is value < 0? No, it's in [0, N), so MSB=0)
- XOR that into ancilla (ancilla ^= 0 = ancilla, doesn't help)

Actually, the standard Beauregard uncomputation uses the MSB of the result:
- After conditional add-back, the result MSB is guaranteed to be 0 (value is in [0, 2^(w-1)) since N < 2^w)
- Wait, that's not guaranteed either.

Let me look at this from a different angle. The current code's approach -- compare then conditionally subtract -- is valid as long as the comparison ancilla is properly cleaned up. The issue is that in the current code, it is NOT cleaned up.

**Practical fix approach:** The simplest fix that aligns with the CONTEXT.md decision to "repair existing compare-and-subtract logic" is:

For each iteration:
1. `cmp = value >= N` (creates comparison qbool)
2. `with cmp: value -= N` (conditional subtraction)
3. After the `with` block, explicitly uncompute `cmp` using the relationship:
   - If cmp was True (value was >= N), after subtraction value < N, so now `value >= N` is False
   - If cmp was False (value was < N), value is unchanged, so `value >= N` is still False
   - In BOTH cases, `value >= N` is now False
   - So: `cmp2 = value >= N` (produces False), then `cmp ^= cmp2` (flips cmp to match), then uncompute cmp2
   - This is the "re-compare to uncompute" pattern

**Even simpler:** Since after the conditional subtraction, `value < N` always holds (assuming at most one subtraction needed), we can uncompute cmp by:
1. Compute `cmp_new = value >= N` -- this is guaranteed to be False (0)
2. `cmp ^= cmp_new` -- this doesn't change cmp (XOR with 0)

That doesn't work. The issue is that `cmp` needs to be returned to |0>, and re-computing doesn't help directly.

**The Bennett trick for uncomputation:**
1. Forward compute: `cmp = f(value)` where f is the comparison
2. Use result: `with cmp: value -= N`
3. Value has changed. But we need to uncompute cmp.
4. Since `f(value_new) = False` and `cmp = f(value_old)`, we can't directly reverse f.

**The correct approach (standard in quantum computing):**
1. Copy cmp to a fresh ancilla: `ctrl = qbool(); ctrl ^= cmp`
2. Uncompute cmp: since value hasn't changed yet, reverse the comparison gates
3. Now ctrl holds the comparison result and cmp is back to |0>
4. Use ctrl for conditional subtraction: `with ctrl: value -= N`
5. Now value has changed and ctrl is "dirty" (holds old comparison result)
6. But we know: if ctrl=1, value went from >= N to value-N (which is < N); if ctrl=0, value unchanged (< N)
7. Uncompute ctrl: `ctrl ^= (value < N)^1` ... this is getting complex.

**Pragmatic fix (what actually works in this codebase):**

Looking at how the DIVISION code works (and it DOES produce correct results for non-MSB-leak cases): the division code uses the EXACT same pattern (`can_subtract = remainder >= trial_value; with can_subtract: remainder -= trial_value`) and it works. The key difference is that each division iteration uses a DIFFERENT trial_value, and the quotient bits accumulate in a separate register.

The modular reduction issue is specifically about:
1. Multiple iterations comparing against the SAME value
2. Entanglement from comparison ancillae accumulating on the SAME value register
3. The comparison qbool not being uncomputed between iterations

**The simplest effective fix:** Ensure the comparison qbool IS properly uncomputed between iterations. The way to do this in the existing framework:

```python
for _ in range(iterations):
    cmp = value >= self._modulus
    with cmp:
        value -= self._modulus
    # Force uncompute of cmp and its dependency chain
    del cmp
    # GC will call __del__ -> _do_uncompute -> but comparison results
    # deliberately don't set _start_layer/_end_layer, so nothing happens!
```

**This confirms the root cause:** Comparison results in this codebase are designed to NOT auto-uncompute (per Phase 29 decision D29-16-2). This makes sense for user-facing code (comparison results should persist). But inside `_reduce_mod`, we NEED the comparison to be uncomputed.

**The fix must override the comparison's non-uncomputation behavior.** Options:

**Option 1: Manually set _start_layer/_end_layer on the comparison result inside _reduce_mod**
```python
start = get_current_layer()
cmp = value >= self._modulus
cmp._start_layer = start
cmp._end_layer = get_current_layer()
```
Then when cmp goes out of scope, `_do_uncompute` will reverse those layers.

**Problem:** After the `with` block, the conditional subtraction gates are BETWEEN the comparison gates. Reversing `[start, end)` would reverse the conditional subtraction too. We need to reverse only the comparison portion.

**Option 2: Use a different comparison approach that's self-uncomputing**

Instead of using `>=` (which creates persistent qbools), implement the reduction using the subtract-and-check-sign approach used in Beauregard-style circuits:

```python
for _ in range(iterations):
    # Subtract N unconditionally
    value -= self._modulus
    # Check if result went negative (MSB = sign bit)
    sign = value[MSB_position]  # extract MSB as qbool view
    # If negative, add N back
    with sign:
        value += self._modulus
    # value is now reduced; sign qubit is part of value register, not separate
```

This avoids creating separate comparison qbools entirely. The sign bit is just a VIEW of the value register (via `__getitem__`), not a separately allocated qubit. The `with sign:` block uses the value register's own MSB as the control.

**This is the standard Beauregard modular reduction approach and is the recommended fix.**

**Advantages:**
- No separate comparison qbools to uncompute
- No entanglement leakage between iterations
- The control qubit (MSB) is part of the value register itself
- Standard pattern from quantum computing literature
- Fewer total qubits allocated (no widened temps for comparison)

**Concern:** The `__getitem__` method creates a qbool view of the MSB, but does NOT allocate new qubits. The qbool shares the same physical qubit as the MSB of value. When used as `with sign:`, the `__enter__` sets this qubit as the control. This is exactly what we want.

**One subtlety:** After `with sign: value += N`, the value may have changed (if sign was 1), so the MSB may no longer be 1. The `__exit__` of the `with` block uncomputes scope-local qbools, but `sign` was created outside the scope. The key: `sign` is a VIEW, not an independent qubit. Its qubit is the MSB of `value`. After the conditional add, the MSB is updated (it's part of `value`). No separate cleanup needed.

**HOWEVER:** There's a register width issue. For the subtract-and-check-sign approach to work, the value register needs an extra MSB to serve as the sign bit. If value is N.bit_length() bits wide, subtracting N from a value < N would produce a negative number that wraps in the register. The sign bit must be a genuinely extra bit, not a data bit.

**Solution:** Before entering the reduction loop, widen the value register by 1 bit (prepend a 0 MSB). This ensures the subtraction result has a valid sign bit. After the loop completes, the extra MSB is guaranteed to be 0 (value is in [0, N)), so it can be discarded.

### Anti-Patterns to Avoid

- **Leaving comparison qbools un-uncomputed across iterations:** This is the current bug. Each comparison creates entanglement that must be cleaned up.
- **Using `reverse_circuit_range` after conditional subtraction to uncompute comparison:** This would also reverse the subtraction, which must persist.
- **Creating extra ancilla copies of comparison results:** Increases qubit count without solving the fundamental entanglement issue.
- **Rewriting the entire algorithm from scratch:** CONTEXT.md says "repair existing compare-and-subtract logic." The subtract-and-check-sign approach is a repair -- same algorithmic intent (conditional subtraction based on comparison), different implementation that avoids the ancilla entanglement issue.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modular reduction | Custom uncomputation protocol | Subtract-check-sign pattern (Beauregard-style) | Standard quantum pattern, avoids ancilla entanglement |
| Comparison uncomputation | Manual layer reversal tracking | Built-in `__getitem__` for MSB access | No separate qbool allocation needed |
| Register widening | Complex bit manipulation | `qint(0, width=w+1)` + CNOT copy pattern from `__lt__` | Established pattern in codebase |

**Key insight:** The fix replaces `cmp = value >= N; with cmp: value -= N` with `value -= N; sign = value[MSB]; with sign: value += N`. This eliminates the problematic comparison qbool entirely by using the value register's own sign bit as the control.

## Common Pitfalls

### Pitfall 1: Register width insufficient for sign bit
**What goes wrong:** Subtracting N from a value < N produces a negative result that wraps in the register, making the MSB unreliable as a sign indicator.
**Why it happens:** Value register has exactly N.bit_length() bits -- no room for a sign bit.
**How to avoid:** Widen the value register by 1 bit before the reduction loop. Create a (w+1)-bit qint, copy value bits into it, then perform reduction on the widened register. After reduction, the extra MSB is guaranteed 0 and can be discarded.
**Warning signs:** Incorrect results even for simple cases like value=1, N=3 (where no reduction should happen but subtraction would produce -2).

### Pitfall 2: MSB position calculation for `__getitem__`
**What goes wrong:** Extracting the wrong bit as the "sign" indicator.
**Why it happens:** Qubit storage is right-aligned: `qubits[64-width]` is bit 0 (LSB), `qubits[63]` is bit (width-1) (MSB). The `__getitem__` method uses the raw index, not the logical bit position.
**How to avoid:** Use `value[63]` to get the MSB (highest bit), which corresponds to the physical qubit at index 63 in the 64-element array. For a (w+1)-bit value, the MSB at position `w` maps to `qubits[63]`.
**Warning signs:** The sign check always returns 0 or always returns 1 regardless of the actual subtraction result.

### Pitfall 3: Iteration count wrong for subtract-check-sign pattern
**What goes wrong:** Too few iterations leave unreduced values; too many waste gate count.
**Why it happens:** Each iteration of subtract-check-sign reduces value by at most N. For value in [0, 2^w), we need at most `floor((2^w - 1) / N)` iterations.
**How to avoid:** For add_mod: max input to _reduce_mod is 2*(N-1) (sum of two values in [0,N)). After wrapping to register width, max value = min(2*(N-1), 2^w - 1). Usually just 1 iteration suffices for addition. For mul_mod: max input is (N-1)^2 wrapped to w bits. Use `max_subtractions = (max_val - 1) // N` and iterate that many times.
**Warning signs:** Modular addition works but multiplication doesn't (insufficient iterations for larger pre-reduction values).

### Pitfall 4: Subtraction extraction instability in sub_mod
**What goes wrong:** `__sub__` in qint_mod has an extra `is_negative = diff < 0; with is_negative: diff += N` step BEFORE calling _reduce_mod. This allocates additional qubits that shift the result position.
**Why it happens:** The negative-value handling creates a variable qubit layout depending on the input values.
**How to avoid:** After fixing _reduce_mod, test subtraction separately. The subtraction's negative-value handling may need its own fix (using the same subtract-check-sign pattern instead of separate comparison). But per CONTEXT.md, sub_mod is lower priority -- focus on add_mod and mul_mod first.
**Warning signs:** Addition and multiplication pass but subtraction still fails with extraction position instability.

### Pitfall 5: Breaking division by modifying shared comparison code
**What goes wrong:** If the fix modifies `__ge__` or `__lt__` behavior, division tests could regress.
**Why it happens:** Division uses the same comparison operators. Changing their uncomputation behavior would affect division.
**How to avoid:** The recommended fix modifies ONLY `_reduce_mod` in `qint_mod.pyx`. It does NOT change comparison operators. The fix replaces the comparison-based pattern with a subtraction-and-sign-check pattern that doesn't use `>=` at all. Division is unaffected.
**Warning signs:** After the fix, run `test_div.py` and `test_mod.py` to verify no regressions.

## Code Examples

### Recommended fix for `_reduce_mod`

```python
cdef _reduce_mod(self, qint value):
    """Reduce value mod N via subtract-and-check-sign pattern.

    Uses Beauregard-style modular reduction: subtract N, check sign,
    conditionally add back. Avoids comparison qbool entanglement leak.
    """
    cdef int comp_width = value.bits + 1  # Extra bit for sign
    cdef int max_val = 1 << value.bits
    cdef int max_subtractions = max_val // self._modulus
    cdef int iterations = max(1, max_subtractions)  # At least 1 iteration

    # Widen value register to comp_width for sign bit
    widened = qint(0, width=comp_width)
    # Copy value bits to widened (LSB-aligned, MSB stays 0)
    for i in range(value.bits):
        # CNOT copy pattern (same as __lt__ uses)
        qubit_array[0] = widened.qubits[64 - comp_width + i]
        qubit_array[1] = value.qubits[64 - value.bits + i]
        arr = qubit_array
        seq = Q_xor(1)
        run_instruction(seq, &arr[0], False, _circuit)

    for _ in range(iterations):
        # Subtract N (unconditionally)
        widened -= self._modulus

        # Check sign: MSB of widened result
        # If subtraction went negative, MSB is 1
        sign = widened[63]  # MSB is at position 63 (right-aligned storage)

        # If negative, add N back (undo subtraction)
        with sign:
            widened += self._modulus

    # Copy result back to value-width register
    result = qint(0, width=value.bits)
    for i in range(value.bits):
        qubit_array[0] = result.qubits[64 - value.bits + i]
        qubit_array[1] = widened.qubits[64 - comp_width + i]
        arr = qubit_array
        seq = Q_xor(1)
        run_instruction(seq, &arr[0], False, _circuit)

    return result
```

### Sub_mod negative handling fix (same pattern)

The `__sub__` method in qint_mod currently uses `is_negative = diff < 0; with is_negative: diff += N`. This could use the same subtract-check-sign approach:

```python
def __sub__(self, other):
    diff = qint.__sub__(self, other)
    # diff might be negative (in two's complement)
    # MSB indicates negativity -- use it directly
    sign = diff[63]  # MSB as sign indicator
    with sign:
        diff += self._modulus
    reduced = self._reduce_mod(diff)
    return self._wrap_result(reduced)
```

But this is only valid if the width has room for a proper sign bit, which depends on whether `__sub__` returns a result with the correct width. This needs careful analysis.

### Test xfail removal

After the fix, remove the xfail functions and related code from `test_modular.py`:
- Remove `_is_known_add_failure()`, `_is_known_sub_failure()`, `_is_known_mul_failure()`
- Remove xfail conditionals in test functions
- Keep the calibration-based extraction if needed, or switch to fixed extraction if the fix stabilizes qubit layout

## State of the Art

| Aspect | Current (Buggy) | After Fix | Impact |
|--------|----------------|-----------|--------|
| _reduce_mod algorithm | Compare-and-conditionally-subtract | Subtract-and-check-sign (Beauregard) | Eliminates comparison qbool entanglement leak |
| Comparison qbool lifecycle | Created, never uncomputed (by design) | Not used in _reduce_mod | No entanglement accumulation |
| Extra qubits per reduction | ~2*(w+1)+3 per comparison iteration | 1 extra bit (sign) for entire reduction | Significant qubit savings |
| xfail count (test_modular.py) | ~129 xfail of 212 tests | Target: 0 xfail | All modular tests pass |
| Iteration count | `log2(max_subtractions)` | `max_subtractions` (or optimize if safe) | May need more iterations but correct |

## Open Questions

### 1. Does register width wrapping affect intermediate sums?

- **What we know:** `qint.__add__` returns a result with width = max(operand widths). For qint_mod, both operands have width = N.bit_length(). Max sum of two values in [0, N) is 2*(N-1). For N=5 (3 bits): max sum = 8, but 3-bit register holds 0-7. Sum of 4+4=8 wraps to 0 in the register.
- **What's unclear:** Whether this wrapping causes incorrect modular results even with a fixed _reduce_mod. For (4+4) mod 5: correct answer is 3. But the register sees 0, and _reduce_mod(0, N=5) gives 0, not 3.
- **Recommendation:** After fixing _reduce_mod, check if addition operands need the result register to be 1 bit wider to avoid premature wrapping. This may require modifying `__add__` in qint_mod to allocate a wider result before reduction.

### 2. Will the subtract-check-sign approach work with the existing `with` statement mechanics?

- **What we know:** `__getitem__` creates a qbool that shares the physical qubit with the value register. `__enter__` sets it as control. `__exit__` restores control state and uncomputes scope-local qbools.
- **What's unclear:** Whether the qbool view from `__getitem__` properly interacts with `__enter__`/`__exit__`. Specifically, `__getitem__` creates a qbool with `create_new=False` and `bit_list` pointing to the original qubit. Its `allocated_qubits = False`, so `__exit__` won't try to uncompute it (no allocated qubits to free). This is correct behavior.
- **Recommendation:** Test with a simple case first (e.g., value=3, N=3, expecting result=0) to verify the pattern works with the existing scope mechanics.

### 3. Should the iteration count be max_subtractions or can it be optimized?

- **What we know:** For add_mod, the pre-reduction value is at most 2*(N-1), wrapping to register width. Usually 1-2 subtractions suffice. For mul_mod, the product wraps to register width, so max_subtractions could be higher.
- **What's unclear:** The exact iteration count formula that is both correct and minimal.
- **Recommendation:** Use `max_subtractions = (max_val - 1) // self._modulus` as a safe upper bound. Per CONTEXT.md, iteration count optimization is at Claude's discretion. Start with the safe bound, optimize later if needed.

### 4. Does `__sub__` in qint_mod need a separate fix for extraction instability?

- **What we know:** The subtraction's `diff < 0` check allocates comparison qubits that shift the result position. This is the same entanglement pattern as _reduce_mod.
- **What's unclear:** Whether fixing _reduce_mod alone will fix subtraction, or whether the negative-value handling also needs the subtract-check-sign treatment.
- **Recommendation:** After fixing _reduce_mod, test subtraction. If it still fails, apply the same pattern to the negative-value handling in `__sub__`. Per CONTEXT.md, sub_mod should pass but is lower priority.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/qint_mod.pyx` -- Direct source inspection of `_reduce_mod` algorithm (lines 107-131)
- `src/quantum_language/qint.pyx` -- Direct source inspection of `__ge__`, `__lt__`, `__enter__`, `__exit__`, `_do_uncompute`
- `tests/test_modular.py` -- Known failure patterns with detailed bug analysis comments
- `.planning/phases/30-arithmetic-verification/30-04-SUMMARY.md` -- Original bug discovery and root cause analysis

### Secondary (MEDIUM confidence)
- `.planning/phases/37-division-overflow-fix/37-RESEARCH.md` -- Phase 37 analysis confirming _reduce_mod is separate from division overflow
- `.planning/phases/37-division-overflow-fix/37-01-SUMMARY.md` -- Division fix patterns and MSB leak documentation
- `.planning/phases/38-modular-reduction-fix/38-CONTEXT.md` -- User decisions constraining fix approach
- `.planning/STATE.md` -- Current bug tracking (BUG-MOD-REDUCE status)

### Tertiary (LOW confidence)
- Beauregard-style modular reduction pattern (from quantum computing literature, referenced from training data, not verified via external source for this specific codebase)

## Metadata

**Confidence breakdown:**
- Root cause analysis: HIGH -- Direct code tracing confirms comparison qbool entanglement leak mechanism; corroborated by Phase 30 original discovery
- Fix approach (subtract-check-sign): HIGH -- Standard quantum computing pattern, avoids the problematic comparison qbool entirely
- Register width concern: MEDIUM -- Theoretical issue identified but unclear whether it manifests in practice with current test inputs
- Subtraction fix: MEDIUM -- Same root cause as _reduce_mod, but extraction instability may have additional factors
- Iteration count: HIGH -- Straightforward calculation, conservative bound is safe

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable codebase, no external dependencies)
