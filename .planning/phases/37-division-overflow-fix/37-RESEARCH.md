# Phase 37: Division Overflow Fix - Research

**Researched:** 2026-02-02
**Domain:** Quantum restoring division algorithm bug fix (Cython/Python)
**Confidence:** HIGH

## Summary

The division algorithm in `qint_division.pxi` has two related bugs that cause incorrect results for specific operand combinations. The first bug (BUG-DIV-01) occurs when `divisor << bit_pos` overflows the register width, causing the comparison `remainder >= trial_value` to operate on a value that cannot be represented in the register. The second bug (BUG-DIV-02) manifests as "MSB comparison leak" where comparison ancillae from one loop iteration corrupt subsequent iterations, specifically when values >= 2^(w-1) interact with the comparison operator.

Both bugs stem from the division loop iterating over all `bit_pos` values from `self.bits - 1` down to `0` without checking whether `divisor << bit_pos` fits within the register width. The fix approach -- per user decisions in CONTEXT.md -- is to restructure loop bounds to calculate the maximum safe iteration count upfront, avoiding the problematic shift entirely. No runtime guards; no additional ancilla qubits.

**Primary recommendation:** Calculate `max_bit_pos = width - divisor.bit_length()` (clamped to >= 0) and iterate from `max_bit_pos` down to `0` instead of from `width - 1` down to `0`. This single change eliminates BUG-DIV-01 completely and likely resolves BUG-DIV-02 as well (since the MSB leak only manifests when overflowing iterations produce corrupted comparison qbools that interfere with subsequent iterations). Apply the same fix to all four affected code paths: `__floordiv__`, `__mod__`, `__divmod__`, and `_reduce_mod` (if applicable).

## Standard Stack

Not applicable -- this is a bug fix within existing Cython code, not a new technology adoption.

### Core
| Component | Location | Purpose | Relevance |
|-----------|----------|---------|-----------|
| `qint_division.pxi` | `src/quantum_language/` | Division/modulo/divmod algorithms | **Primary fix target** |
| `qint_comparison.pxi` | `src/quantum_language/` | `__ge__`, `__lt__` comparison operators | Used by division; may need changes |
| `qint_mod.pyx` | `src/quantum_language/` | `_reduce_mod` method | Shares comparison+subtraction pattern; regression target |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `test_div.py` | `tests/` | Division verification tests | Remove xfail markers after fix |
| `test_mod.py` | `tests/` | Modulo verification tests | Remove xfail markers after fix |
| `test_modular.py` | `tests/` | Modular arithmetic tests | Regression check |
| `test_uncomputation.py` | `tests/` | Dirty ancilla xfail tests (gt/le) | Check if incidentally fixed |

## Architecture Patterns

### Current Division Algorithm Structure

The restoring division algorithm in `__floordiv__` (line 65-76 of `qint_division.pxi`):

```python
# Current (buggy) loop:
for bit_pos in range(self.bits - 1, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)
```

The bug: when `divisor << bit_pos >= 2^width`, `trial_value` exceeds the register capacity. The comparison `remainder >= trial_value` then calls `__ge__` -> `~(self < trial_value)` -> `__lt__` which has the overflow check:

```python
max_val = (1 << self.bits) - 1
if other > max_val:
    return qbool(True)  # qint always < large value
```

So `remainder >= overflowed_value` returns `qbool(False)` (always). This seems correct (skip the iteration), but the qbool creation still generates gates that interact with the circuit, and the "always False" qbool's internal state may not match what subsequent iterations expect.

### Fix Pattern: Restructured Loop Bounds

```python
# Fixed loop:
max_bit_pos = self.bits - divisor.bit_length()
if max_bit_pos < 0:
    max_bit_pos = 0
    # divisor > max_remainder, no subtraction possible at any shift
    # But divisor itself might still be <= remainder, so bit_pos=0 must run

# Only iterate where divisor << bit_pos < 2^width
for bit_pos in range(max_bit_pos, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)
```

The formula: `divisor << bit_pos < 2^width` iff `bit_pos < width - floor(log2(divisor))` iff `bit_pos <= width - divisor.bit_length()`.

So `max_bit_pos = width - divisor.bit_length()`. When `divisor.bit_length() > width`, `max_bit_pos` is negative, meaning no iterations run (the divisor is always larger than any possible remainder).

**Special case:** When `max_bit_pos < 0`, the divisor doesn't fit in the register width at all. Since the restoring division algorithm starts with the dividend copied to remainder, and the dividend fits in `width` bits, the divisor is larger than any possible value. Quotient stays 0 -- correct behavior with no iterations needed. However, we must handle the case where `divisor` has exactly `width` bits (e.g., divisor=8, width=4: `8.bit_length()=4`, `max_bit_pos=0`). In this case, bit_pos=0 should run because `8 << 0 = 8` which is `2^width` -- but this is OUT of range! So we need: `divisor << bit_pos < 2^width`, i.e., `divisor * 2^bit_pos < 2^width`. For bit_pos=0: `divisor < 2^width`. If divisor=8 and width=4: `8 < 16` -- yes, this is fine. But for divisor=9: `9 < 16` -- also fine. The formula `max_bit_pos = width - divisor.bit_length()` gives `4 - 4 = 0`, so bit_pos=0 runs. For divisor=16 and width=4: `16.bit_length()=5`, `max_bit_pos=-1`, no iterations -- correct since 16 > 15.

**Correction for edge case:** When `divisor.bit_length() == width`, `max_bit_pos = 0`. `divisor << 0 = divisor`. Since `divisor` can be up to `2^width - 1` (which fits in width bits), this is always valid. When `divisor = 2^width` exactly (doesn't fit), `divisor.bit_length() = width + 1`, so `max_bit_pos = -1` -- correct.

### Four Code Paths to Fix

All four share the same loop structure and need the same fix:

1. **`__floordiv__`** (line 65-76): Classical divisor floor division
2. **`__mod__`** (line 176-184): Classical divisor modulo
3. **`__divmod__`** (line 271-280): Classical divisor divmod
4. **`_reduce_mod` in `qint_mod.pyx`** (line 107-131): Uses `>=` comparison pattern, but with a fixed classical modulus -- different loop structure (iterates N times, not bit-position loop). **This is NOT affected by the same bug** -- it does `value >= self._modulus` where modulus fits in the register. Leave unchanged.

### Anti-Patterns to Avoid

- **Runtime guards instead of loop bound restructuring:** CONTEXT.md explicitly forbids runtime guards like `if trial_value >= (1 << width): continue`. The loop bounds themselves must prevent the overflow.
- **Adding extra ancilla qubits:** CONTEXT.md says preserve current ancilla count.
- **Touching quantum divisor paths:** The quantum divisor code (`_floordiv_quantum`, `_mod_quantum`, `_divmod_quantum`) uses repeated subtraction of the divisor itself (no shifting), so they are NOT affected by the overflow bug. Leave them unchanged.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bit length calculation | Manual log2 or bit counting | Python's `int.bit_length()` | Built-in, handles edge cases (0 returns 0) |
| Loop bound clamping | Complex conditional logic | `max(0, width - divisor.bit_length())` | Simple, readable, correct |

**Key insight:** The fix is purely a loop bound calculation -- no new algorithms, no new data structures, no changes to the quantum circuit generation. The existing comparison and subtraction operators work correctly when given representable values.

## Common Pitfalls

### Pitfall 1: Off-by-one in max_bit_pos calculation
**What goes wrong:** Iterating one position too many or too few.
**Why it happens:** Confusing `bit_length()` with `floor(log2())` -- they differ by 1 for powers of 2 vs non-powers.
**How to avoid:** Verify with concrete examples:
- divisor=1 (bit_length=1): max_bit_pos = width-1 (same as current, correct)
- divisor=2 (bit_length=2): max_bit_pos = width-2 (skips top position where 2<<(w-1) = 2^w)
- divisor=8, width=4 (bit_length=4): max_bit_pos = 0 (only bit_pos=0, since 8<<0=8 < 16)
- divisor=15, width=4 (bit_length=4): max_bit_pos = 0 (only bit_pos=0, since 15<<0=15 < 16)
- divisor=16, width=4 (bit_length=5): max_bit_pos = -1 (no iterations, quotient=0)
**Warning signs:** Any width-4 case with divisor 8-15 should have exactly 1 iteration (bit_pos=0).

### Pitfall 2: BUG-DIV-02 not resolved by loop bound fix alone
**What goes wrong:** After fixing loop bounds, the "MSB comparison leak" cases (e.g., 4//1 at width 3) may still fail.
**Why it happens:** These cases have `divisor=1`, so `max_bit_pos = width - 1` (all iterations valid, no overflow). The bug is in comparison ancilla interference between iterations, not in overflow.
**How to avoid:** Test BUG-DIV-02 cases separately after applying the loop bound fix. If they still fail, the comparison operator itself needs investigation. Per CONTEXT.md, "Fix may touch comparison operators if they are part of the root cause."
**Warning signs:** After fix, check cases like `(3, 4, 1)`, `(3, 5, 1)`, `(4, 13, 1)`, `(4, 15, 1)` -- these have divisor=1 and values >= 2^(w-1).

### Pitfall 3: Forgetting to fix all three classical-divisor code paths
**What goes wrong:** Fixing `__floordiv__` but not `__mod__` or `__divmod__`, leaving modulo/divmod broken.
**Why it happens:** The three methods have nearly identical loop structures but are separate code.
**How to avoid:** Fix all three methods in `qint_division.pxi` in a single pass. They share `KNOWN_DIV_FAILURES` and `KNOWN_MOD_FAILURES` sets (identical), confirming they share the same bug.

### Pitfall 4: Breaking division-by-zero behavior
**What goes wrong:** The loop bound fix accidentally changes behavior for divisor=0.
**Why it happens:** `0.bit_length() = 0`, so `max_bit_pos = width - 0 = width`, which could cause iteration beyond valid range.
**How to avoid:** Division by zero is caught by the `if divisor == 0: raise ZeroDivisionError` guard BEFORE the loop. The fix never executes for divisor=0. Verify this guard remains in place.

### Pitfall 5: Negative max_bit_pos causing range() issues
**What goes wrong:** `range(negative_value, -1, -1)` produces empty range in Python, which is correct (no iterations). But if someone adds `max(0, ...)` clamping, it might cause an unnecessary iteration.
**Why it happens:** When `divisor.bit_length() > width`, `max_bit_pos` is negative. `range(-1, -1, -1)` is empty -- correct. But `range(0, -1, -1)` iterates once with bit_pos=0, which might try to compare remainder >= divisor where divisor doesn't fit.
**How to avoid:** Check: when `max_bit_pos < 0`, either skip the loop entirely, or verify that `divisor << 0 = divisor < 2^width` always holds (it doesn't when `divisor >= 2^width`). Since divisor is an int parameter that can exceed 2^width, **do NOT clamp to 0** -- let the negative value produce an empty range, or use an explicit `if max_bit_pos >= 0:` guard before the loop.

## Code Examples

### Fix for `__floordiv__` (primary fix target)

```python
# Source: qint_division.pxi, lines 64-76
# BEFORE (buggy):
for bit_pos in range(self.bits - 1, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)

# AFTER (fixed):
max_bit_pos = self.bits - divisor.bit_length()
for bit_pos in range(max_bit_pos, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)
```

The change is a single line: replace `self.bits - 1` with `self.bits - divisor.bit_length()` in the range start. When `max_bit_pos < 0`, `range(negative, -1, -1)` is empty -- no iterations, quotient stays 0. This is correct: if the divisor doesn't fit in a single register-width shift, the quotient is 0.

### Fix for `__mod__` (identical pattern)

```python
# Source: qint_division.pxi, lines 176-184
# Same one-line change:
max_bit_pos = self.bits - divisor.bit_length()
for bit_pos in range(max_bit_pos, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
```

### Fix for `__divmod__` (identical pattern)

```python
# Source: qint_division.pxi, lines 271-280
# Same one-line change:
max_bit_pos = self.bits - divisor.bit_length()
for bit_pos in range(max_bit_pos, -1, -1):
    trial_value = divisor << bit_pos
    can_subtract = remainder >= trial_value
    with can_subtract:
        remainder -= trial_value
        quotient += (1 << bit_pos)
```

### Test xfail removal pattern

After the fix, remove failing cases from `KNOWN_DIV_FAILURES` and `KNOWN_MOD_FAILURES` in `test_div.py` and `test_mod.py`. If ALL cases are fixed, the entire `KNOWN_*_FAILURES` set and `_mark_*_cases` function can be simplified to just return the cases without xfail markers.

## State of the Art

| Aspect | Current | After Fix | Impact |
|--------|---------|-----------|--------|
| Division loop range | `range(self.bits - 1, -1, -1)` | `range(self.bits - divisor.bit_length(), -1, -1)` | Prevents overflow |
| xfail count (div) | 24 xfail | 0 expected (if BUG-DIV-02 also resolved) | All tests pass |
| xfail count (mod) | 24 xfail | 0 expected (if BUG-DIV-02 also resolved) | All tests pass |

## Open Questions

### 1. Will the loop bound fix resolve BUG-DIV-02 (MSB comparison leak)?

- **What we know:** BUG-DIV-02 affects cases like `(3, 4, 1)` where divisor=1 and value >= 2^(w-1). For divisor=1, `max_bit_pos = width - 1`, so ALL iterations still run. The overflow fix does NOT skip any iterations for these cases.
- **What's unclear:** Whether the "comparison leak" is caused by:
  (a) The overflowing iterations at higher bit positions producing corrupted qbools that leak into lower iterations (in which case the loop bound fix eliminates the source of corruption and BUG-DIV-02 is resolved)
  (b) An independent issue in the comparison operator where large values (>= 2^(w-1)) trigger MSB-related bugs in `__lt__`/`__ge__` regardless of the division loop (in which case BUG-DIV-02 persists)
- **Recommendation:** Apply the loop bound fix first, then run the BUG-DIV-02 test cases. If they still fail, investigate the `__lt__` implementation for values near 2^(w-1). The known "dirty ancilla" issue in gt/le comparisons (noted in `test_uncomputation.py`) may be a contributing factor. Per CONTEXT.md, touching comparison operators is in scope if needed.

### 2. Does `_reduce_mod` in `qint_mod.pyx` share this bug?

- **What we know:** `_reduce_mod` uses `value >= self._modulus` comparison in a loop, but it does NOT shift the modulus. The modulus is a fixed classical value that fits within the register width (by construction). So the overflow pattern `divisor << bit_pos >= 2^width` does not occur.
- **Recommendation:** No fix needed for `_reduce_mod`, but run modular arithmetic tests as regression check per CONTEXT.md.

### 3. Are the `KNOWN_DIV_FAILURES` and `KNOWN_MOD_FAILURES` sets accurate/complete?

- **What we know:** The sets were generated empirically during Phase 30 verification. They may be incomplete (not all failing cases at width 4 were tested due to sampling). After the fix, running the full test suite will reveal whether additional cases exist.
- **Recommendation:** After applying the fix, run the existing tests. If any xfail tests unexpectedly pass (xpass), that confirms the fix. If any non-xfail tests fail, investigate.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/qint_division.pxi` -- Direct source code inspection of division algorithm
- `src/quantum_language/qint_comparison.pxi` -- Direct source code inspection of comparison operators
- `tests/test_div.py` -- Known failure cases with detailed comments
- `tests/test_mod.py` -- Known failure cases matching division failures
- `.planning/phases/30-arithmetic-verification/30-03-SUMMARY.md` -- Original bug discovery documentation

### Secondary (MEDIUM confidence)
- `.planning/phases/37-division-overflow-fix/37-CONTEXT.md` -- User decisions constraining fix approach
- `.planning/STATE.md` -- Current project state and known blockers
- `.planning/PROJECT.md` -- Architecture context and known limitations

## Metadata

**Confidence breakdown:**
- Root cause analysis: HIGH -- Direct code inspection confirms overflow mechanism
- Fix approach: HIGH -- Loop bound restructuring is deterministic and mathematically provable
- BUG-DIV-02 resolution: MEDIUM -- Hypothesis that loop bound fix resolves it is plausible but unverified
- Regression risk: LOW -- Fix narrows loop iterations (fewer operations), unlikely to break passing tests

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable codebase, no external dependencies)
