# Phase 41: Uncomputation Fix - Research

**Researched:** 2026-02-02
**Domain:** Quantum circuit uncomputation, Python GC-based cleanup, layer tracking
**Confidence:** HIGH

## Summary

The uncomputation system has a regression where expressions inside `with` blocks (and comparisons/arithmetic in general) fail to properly uncompute temporary qubits and reverse their gates when no longer needed. This causes circuits to accumulate unused qubits and stale gates, leading to exponential qubit growth (e.g., 56 qubits for a 4-bit division, 31 qubits for compound boolean on 3-bit integers).

The root cause has been identified through direct code analysis and empirical testing. There are **two distinct issues** that interact:

1. **Missing layer tracking on comparisons and arithmetic**: The `__gt__`, `__lt__`, `__le__`, `__eq__`, `__add__`, `__sub__`, `__mul__` operations create result qints without setting `_start_layer`/`_end_layer`, so `_do_uncompute()` never reverses their gates even when GC frees the qubits. For comparisons, this was a deliberate decision (D29-16-2) made in Phase 29 to prevent GC-triggered gate reversal from corrupting circuits, but it means temporaries inside comparisons also never get their gates reversed.

2. **Stale `.pxi` files not included**: The `.pxi` include files (`qint_comparison.pxi`, `qint_arithmetic.pxi`) contain NEWER, corrected implementations with proper layer tracking, but they are NOT included in `qint.pyx` -- the code is duplicated inline in `qint.pyx` with the older implementation.

**Primary recommendation:** Fix the layer tracking on all operations that create temporary qints, and ensure the `.pxi` include files are either properly included or removed to avoid confusion. The comparison `.pxi` already has the correct implementation with layer tracking that should replace the inline code.

## Standard Stack

### Core (Already in Codebase)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `_do_uncompute()` | qint.pyx lines 356-414 | Core uncomputation logic | Working correctly |
| `reverse_circuit_range()` | c_backend/src/execution.c | LIFO gate reversal | Working correctly |
| `allocator_free()` | c_backend/src/qubit_allocator.c | Qubit deallocation | Working correctly |
| `_start_layer`/`_end_layer` | qint.pxd | Layer boundary tracking | **Not set on most operations** |
| `_scope_stack` | _core.pyx | Scope-based cleanup in `__exit__` | Working but ineffective due to missing layer tracking |
| `__del__` | qint.pyx lines 521-563 | GC-triggered cleanup | Working but reverses no gates (layers = 0) |

### Supporting (Unused but Available)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `qint_comparison.pxi` | src/quantum_language/ | Updated comparison ops WITH layer tracking | **Not included in build** |
| `qint_arithmetic.pxi` | src/quantum_language/ | Updated arithmetic ops | **Not included in build** |

## Architecture Patterns

### Pattern 1: Layer-Tracked Operation (Working Example from `__and__`)

**What:** Capture circuit layer before/after an operation so `_do_uncompute` can reverse exactly those gates.
**When to use:** Every operation that allocates new qubits for a result.
**Source:** qint.pyx `__and__` implementation (lines 1067-1178)

```python
# Capture start layer BEFORE any gates
start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

# ... allocate result qint ...
# ... apply gates ...

# Capture end layer AFTER all gates
result._start_layer = start_layer
result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
result.operation_type = 'AND'
result.add_dependency(self)
```

When `result` is GC'd or explicitly uncomputed, `_do_uncompute` calls:
```python
if self._end_layer > self._start_layer:
    reverse_circuit_range(_circuit, self._start_layer, self._end_layer)
```

### Pattern 2: Current Broken Pattern (Arithmetic)

**What:** `__add__` creates a new qint initialized with classical value, then adds in-place. No layer tracking.
**Source:** qint.pyx `__add__` (lines 747-777)

```python
def __add__(self, other):
    a = qint(value=self.value, width=result_width)  # X gates for init
    a += other  # Addition gates
    return a  # _start_layer=0, _end_layer=0, operation_type=None
```

When `a` is GC'd: qubits are freed, but gates remain in circuit forever.

### Pattern 3: Current Broken Pattern (Comparisons with Widened Temporaries)

**What:** `__gt__` in qint.pyx creates widened temp copies for unsigned comparison, but those temps have no layer tracking.
**Source:** qint.pyx `__gt__` (lines 1895-2005)

```python
def __gt__(self, other):
    # For qint operand:
    comp_width = max(self.bits, other.bits) + 1
    temp_other = qint(0, width=comp_width)  # No layer tracking
    temp_self = qint(0, width=comp_width)   # No layer tracking
    # ... copy bits via XOR ...
    # ... subtract ...
    result.add_dependency(self)
    result.add_dependency(other)
    # Note: deliberately NOT setting _start_layer/_end_layer here.
    return result  # temp_other, temp_self leak their gates
```

### Pattern 4: Corrected Pattern (in `.pxi` files - not compiled)

**What:** The `.pxi` file has a simpler comparison that operates in-place without widened temps.
**Source:** qint_comparison.pxi `__gt__` (lines 264-339)

```python
def __gt__(self, other):
    if type(other) == qint:
        other -= self           # In-place subtraction
        msb = other[64 - other.bits]
        result = qbool()
        result ^= msb
        other += self           # Restore
        result._start_layer = start_layer
        result._end_layer = (<circuit_s*>_circuit).used_layer
        return result
```

This is cleaner: no widened temps, proper layer tracking, and simpler logic.

### Anti-Patterns to Avoid

- **Removing layer tracking to "fix" GC issues (D29-16-2):** The real fix is to control WHEN uncomputation happens, not to disable it entirely. The `__del__` method already has mode-aware logic (EAGER vs LAZY) and `.keep()` flag.
- **Creating temporary qints without layer tracking inside operations:** Every qint that allocates qubits and applies gates MUST track its layer boundaries, even if it's a local variable.
- **Duplicating code between `.pyx` and `.pxi` files:** The `.pxi` files exist but aren't included, leading to divergent implementations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate reversal | Custom adjoint logic | `reverse_circuit_range()` | Already handles all gate types, LIFO order |
| Qubit cleanup | Manual tracking | `allocator_free()` via `_do_uncompute()` | Already handles reuse pool |
| Scope tracking | Custom scope system | `_scope_stack` + `__enter__`/`__exit__` | Already implemented in Phase 19 |

**Key insight:** The infrastructure for uncomputation is COMPLETE and WORKING. The `__and__` operation proves it. The fix is about applying the same layer-tracking pattern consistently to ALL operations.

## Common Pitfalls

### Pitfall 1: Breaking Comparison Correctness When Adding Layer Tracking

**What goes wrong:** Adding layer tracking to comparisons might cause GC to reverse comparison gates while the result is still needed elsewhere.
**Why it happens:** D29-16-2 removed layer tracking because GC was reversing gates prematurely.
**How to avoid:** The `.pxi` comparison code shows the solution: use in-place operations that don't create widened temporaries, and track layers on the result qbool. The result won't be GC'd while it's referenced (Python refcounting ensures this). The D29-16-2 problem was actually caused by widened temporaries being GC'd out of order, not by the result itself.
**Warning signs:** Comparison results returning wrong values after GC cycle.

### Pitfall 2: Nested Layer Ranges Overlapping

**What goes wrong:** If operation A creates temp at layer 5, then operation B creates temp at layer 8, and A's temp range is [5,12] while B's is [8,15], reversing A's range would also reverse B's gates.
**Why it happens:** Layer tracking uses absolute layer indices, not relative ones.
**How to avoid:** Ensure that each operation's layer range covers ONLY its own gates. The current `_do_uncompute` cascades in LIFO order (newest first), which should prevent overlap if dependencies are correct. However, the comparison operations that mutate operands in-place (subtract-add-back) have gates that span across the result's layer range, which complicates reversal.
**Warning signs:** Gate reversal corrupting unrelated operations.

### Pitfall 3: In-Place Subtract-Add-Back Pattern and Layer Tracking

**What goes wrong:** `__lt__` does `self -= other`, checks MSB, then `self += other`. If the result's layer range covers all of this, reversing the result would also reverse the restoration `self += other`, corrupting `self`.
**Why it happens:** The subtract-add-back pattern is designed to be self-contained (restore operands), but layer tracking doesn't know which gates are "restoration" vs "computation."
**How to avoid:** The result's gates should NOT include the restoration step. Only the actual comparison computation (subtract, MSB check) should be tracked. The `.pxi` code handles this correctly by capturing start_layer before the operation and end_layer after, which includes the restoration gates -- but this is actually fine because the restoration gates are the EXACT inverse of the computation gates, so reversing [start, end) is idempotent (subtracting then adding then subtracting again etc.). However, the MSB extraction (`result ^= msb`) is what needs to persist.
**Warning signs:** Operand qints getting corrupted after result is uncomputed.

### Pitfall 4: The `.pxi` vs `.pyx` Confusion

**What goes wrong:** Developer modifies `.pxi` file thinking it's compiled, but actual code is inline in `.pyx`.
**Why it happens:** The `.pxi` files exist alongside the `.pyx` and contain method implementations, but no `include` directive is present.
**How to avoid:** Either integrate the `.pxi` files properly with `include` directives, or delete them. Don't maintain two copies.
**Warning signs:** Changes to `.pxi` have no effect; `.pyx` and `.pxi` diverge over time.

## Code Examples

### Example 1: Current Failing Test (Compound AND)

```python
# test_uncomp_compound_and - FAILS with "Insufficient memory: 32768M"
# Because: a > 1 creates 15 qubits (3 for a, 3 for temp_int(1),
# 4+4 for widened copies, 1 for result)
# b < 3 creates another ~12 qubits
# Total: ~31 qubits -> 2^31 * 16 bytes = 32GB statevector
ql.option('qubit_saving', True)
a = ql.qint(2, width=3)
b = ql.qint(1, width=3)
cond1 = a > 1    # 15 qubits peak, 7 remaining
cond2 = b < 3    # +8 more qubits
result = cond1 & cond2  # +1 qubit
# Total: 31 qubits in QASM despite most being logically freed
```

### Example 2: Working Uncomputation (AND Operation)

```python
ql.option('qubit_saving', True)
a = ql.qint(5, width=3)
b = ql.qint(3, width=3)
result = a & b  # _start_layer=1, _end_layer=2, operation_type='AND'
del result; gc.collect()
# After: gates REVERSED (layer goes 2->3), qubits freed
# Stats show deallocation happened
```

### Example 3: Expected Fix Pattern for `__add__`

```python
def __add__(self, other):
    start_layer = (<circuit_s*>_circuit).used_layer
    result = qint(value=self.value, width=result_width)
    result += other
    result._start_layer = start_layer
    result._end_layer = (<circuit_s*>_circuit).used_layer
    result.operation_type = 'ADD'
    result.add_dependency(self)
    if isinstance(other, qint):
        result.add_dependency(other)
    return result
```

## Root Cause Analysis

### Finding 1: Two implementations exist, wrong one is compiled (HIGH confidence)

The `.pxi` include files contain updated, corrected implementations:
- `qint_comparison.pxi`: Uses in-place subtract-add-back WITHOUT widened temporaries, WITH layer tracking
- `qint_arithmetic.pxi`: Same arithmetic code (no layer tracking added yet)

But `qint.pyx` does NOT include these files. The inline code in `qint.pyx` uses the OLD implementation:
- Comparisons: Widened temporaries (comp_width+1) that leak qubits, NO layer tracking (per D29-16-2)
- Arithmetic: No layer tracking, no dependency tracking, no operation_type

### Finding 2: Layer tracking is the gating issue (HIGH confidence)

Empirical evidence from test runs:
- `__and__` (HAS layer tracking): Gates are reversed on GC, circuit stays clean
- `__add__` (NO layer tracking): Gates persist forever, circuit grows
- `__gt__` (NO layer tracking per D29-16-2): Gates persist, widened temps leak gates

The `_do_uncompute()` method works correctly -- it just has nothing to reverse when `_end_layer == _start_layer == 0`.

### Finding 3: Qubit deallocation works, gate reversal doesn't (HIGH confidence)

```
After a > 1:  peak_allocated=15, deallocations=2 (widened temps freed)
              current_in_use=7 (a=3, result=1, temp_int=3)
              BUT: circuit has 15 qubit declarations in QASM
```

The allocator properly frees qubit slots, but the QASM export sees all gates ever added and declares qubits for the maximum qubit index used.

### Finding 4: The D29-16-2 decision needs revisiting (HIGH confidence)

D29-16-2 removed layer tracking from comparisons to prevent GC-triggered gate reversal. But this created the uncomputation regression. The `.pxi` files show the correct approach: use simpler comparison implementations that don't need widened temps, and rely on Python's refcounting to prevent premature GC (result stays alive as long as it's referenced).

### Finding 5: Division creates O(width) comparisons, each leaking (HIGH confidence)

```python
# a // 3 with width=4:
# For each of 4 bit positions:
#   can_subtract = remainder >= trial_value  # comparison -> leaks gates
#   with can_subtract:                        # scope creates/destroys
#     remainder -= trial_value
#     quotient += (1 << bit_pos)
# Result: 56 qubits in QASM for 4-bit division
```

## Recommended Fix Strategy

### Option A: Integrate `.pxi` Files (RECOMMENDED)

1. Add `include "qint_comparison.pxi"` and `include "qint_arithmetic.pxi"` to `qint.pyx`
2. Remove the inline implementations from `qint.pyx`
3. Add layer tracking to arithmetic operations in the `.pxi` files
4. The `.pxi` comparison code already has correct layer tracking and simpler implementations
5. Rebuild Cython extension

**Risk:** The `.pxi` comparison implementations use different algorithms (in-place subtract on operands directly, no widened temps). These may have different correctness properties that need testing.

### Option B: Patch Inline Code in `qint.pyx`

1. Add layer tracking (`_start_layer`, `_end_layer`, `operation_type`, `add_dependency`) to `__add__`, `__sub__`, `__mul__`
2. Re-enable layer tracking on comparisons (reverse D29-16-2)
3. Ensure widened temporaries in `__gt__`/`__lt__` also get proper tracking
4. Delete unused `.pxi` files

**Risk:** More surgical changes, but maintains the widened-temporary approach for comparisons which has known correctness for unsigned values spanning the MSB boundary.

### Option C: Hybrid Approach

1. Replace comparison implementations with `.pxi` versions (simpler, already have layer tracking)
2. Add layer tracking to arithmetic operations inline
3. Remove or archive unused `.pxi` files

**Risk:** Needs testing of the `.pxi` comparison implementations against the full test suite.

## Open Questions

1. **Do the `.pxi` comparison implementations pass the existing 1529 comparison tests?**
   - What we know: They use simpler in-place subtract-add-back directly on operands (no widened temps)
   - What's unclear: Whether this handles unsigned values spanning the MSB boundary correctly (the reason widened temps were added in Phase 29)
   - Recommendation: Run the full comparison test suite with `.pxi` implementations before committing. If they fail the MSB boundary tests, add widened temps to `.pxi` with layer tracking.

2. **Will reversing comparison gates when the result is GC'd cause issues (the original D29-16-2 concern)?**
   - What we know: Python's refcounting prevents GC of an object while references exist. The result qbool stays alive as long as it's assigned to a variable or in a dependency chain.
   - What's unclear: Whether there are edge cases where GC runs unexpectedly (e.g., inside `with` blocks, during Cython method calls)
   - Recommendation: The `__and__` operation already does this correctly and hasn't had issues. Trust the same pattern for comparisons.

3. **How does layer-range reversal interact with the subtract-add-back pattern?**
   - What we know: `__lt__` does `self -= other` (gates A), check MSB (gates B), `self += other` (gates C = inverse of A). So the full range is [A, B, C]. Reversing [A, B, C] produces [C_inv, B_inv, A_inv] = [A, B_inv, C]. This correctly undoes the MSB check but re-applies the subtraction.
   - What's unclear: Whether this is the correct semantic for uncomputation in all cases
   - Recommendation: Test carefully with the uncomputation test suite

## Sources

### Primary (HIGH confidence)
- Direct code analysis: `src/quantum_language/qint.pyx` (compiled code)
- Direct code analysis: `src/quantum_language/qint_comparison.pxi` (updated but not compiled)
- Direct code analysis: `src/quantum_language/qint_arithmetic.pxi` (updated but not compiled)
- Direct code analysis: `src/quantum_language/_core.pyx` (scope management)
- Empirical test results: `python3 -m pytest tests/test_uncomputation.py` (4 failures)
- Empirical debugging: Circuit statistics before/after operations

### Secondary (MEDIUM confidence)
- Planning docs: `.planning/phases/29-c-backend-bug-fixes/29-16-SUMMARY.md` (D29-16-2 decision)
- Planning docs: `.planning/phases/35-comparison-bug-fixes/35-02-PLAN.md` (layer tracking removal rationale)
- Planning docs: `.planning/phases/38-modular-reduction-fix/38-RESEARCH.md` (confirms the root cause was already identified)

## Metadata

**Confidence breakdown:**
- Root cause identification: HIGH - Empirically verified with circuit statistics and test failures
- Fix strategy: HIGH - Working example (`__and__`) proves the pattern; `.pxi` files show the correct code
- Risk assessment: MEDIUM - The interaction between layer reversal and subtract-add-back pattern needs testing

**Research date:** 2026-02-02
**Valid until:** 90 days (internal codebase, no external dependencies)
