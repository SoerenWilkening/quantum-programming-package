# Phase 14: Ordering Comparisons - Research

**Researched:** 2026-01-27
**Domain:** Quantum integer comparison operators (<=, >=, <, >) with in-place arithmetic
**Confidence:** HIGH

## Summary

This phase implements four ordering comparison operators (`<=`, `>=`, `<`, `>`) for quantum integers using in-place subtraction/addition without temporary qint allocation. The standard approach uses a subtract-check-add-back pattern: compute `a - b` in-place, check the sign bit (MSB) and/or zero equality, then restore operands by adding back.

**Key findings:**
- Two's complement representation enables sign-based comparison via MSB inspection
- Subtract-add-back pattern preserves operands (established in Phase 13 for equality)
- `<` checks MSB only (negative result), `<=` checks MSB OR zero
- Python operator reflection handles reversed operands (`5 <= qint` via `__ge__`)
- Current implementation already exists but allocates temporary qints (needs refactoring)

**Primary recommendation:** Refactor all four operators (`__lt__`, `__le__`, `__gt__`, `__ge__`) to use in-place subtract-MSB-check-add-back pattern, eliminating temporary allocations while preserving both operands.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | 3.x | Python-C bindings | Existing project standard for quantum_language.pyx |
| NumPy | Latest | Qubit array management | Existing standard for qubit_array allocation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | Latest | Testing framework | Existing test infrastructure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-place subtract-add-back | Allocate temp qints | Current implementation - violates phase requirement |
| MSB inspection | Full subtraction result | More qubits, more gates, unnecessary for comparison |
| Python-level only | C-level CQ_less_than | Not needed - Python pattern is efficient enough |

**Installation:**
```bash
# No new dependencies - uses existing project stack
pip install -r requirements.txt  # If not already installed
```

## Architecture Patterns

### Recommended Pattern Structure

Comparisons implemented as Python methods in `qint` class within `quantum_language.pyx`:

```python
def __le__(self, other):
    """Less-than-or-equal: a <= b means (a - b) is negative OR zero"""
    # 1. Self-comparison optimization
    if self is other:
        return qbool(True)

    # 2. In-place subtraction
    self -= other

    # 3. Check MSB (sign) AND check zero
    is_negative = self[64 - self.bits]  # MSB
    is_zero = (self == 0)
    result = is_negative | is_zero  # OR combination

    # 4. Restore operand
    self += other

    return result
```

### Pattern 1: Subtract-MSB-Add-Back for Ordering

**What:** Compute `a - b` in-place, check MSB for sign (two's complement), restore `a` by adding `b` back.

**When to use:** All ordering comparisons (`<`, `>`, `<=`, `>=`)

**Example:**
```python
# Source: Phase 13 equality pattern + arXiv:2512.17779 comparator concept
def __lt__(self, other):
    """a < b: true if (a - b) is negative (MSB = 1)"""
    if self is other:
        return qbool(False)  # Self < self is always false

    # In-place subtract
    self -= other

    # Check MSB (sign bit) - if 1, result is negative
    msb = self[64 - self.bits]
    result = qbool()
    result ^= msb  # Copy MSB to result

    # Restore operand
    self += other

    return result
```

### Pattern 2: MSB + Zero Check for <=

**What:** Combine MSB check (negative) with zero check (equality) using OR.

**When to use:** `<=` and `>=` operators

**Example:**
```python
# Source: Two's complement semantics + Phase 13 zero check
def __le__(self, other):
    """a <= b: true if (a - b) is negative OR zero"""
    if self is other:
        return qbool(True)  # Self <= self is always true

    self -= other

    # Check both conditions
    is_negative = self[64 - self.bits]  # MSB
    is_zero = (self == 0)  # Reuses Phase 13 CQ_equal_width

    # OR combination
    result = qbool()
    result ^= is_negative
    temp = qbool()
    temp ^= is_zero
    result |= temp  # result = negative OR zero

    self += other
    return result
```

### Pattern 3: Operator Reflection for Reversed Operands

**What:** Python calls `__ge__` when user writes `5 <= qint` (reflected comparison).

**When to use:** Always implement both forward and reverse operators.

**Example:**
```python
# Source: Python operator overloading best practices
def __le__(self, other):
    """Forward: a <= b"""
    return self._le_impl(other)

# Python automatically calls __ge__ for: 5 <= qint_instance
# Because: 5 <= x is equivalent to x >= 5
```

### Pattern 4: Operand-Swapping for `>` via `<`

**What:** Reuse `<` implementation by swapping operands.

**When to use:** `>` can delegate to `<`, `>=` can be `NOT <`

**Example:**
```python
# Source: Python operator overloading patterns
def __gt__(self, other):
    """a > b is equivalent to b < a"""
    if type(other) == int:
        other_qint = qint(other, width=self.bits)
        return other_qint < self
    return other < self
```

### Anti-Patterns to Avoid

- **Allocating temporary qints for comparison:** Current `__lt__` allocates `temp = qint(0, width=comp_bits)` - violates phase requirement. Use in-place operations instead.
- **Not restoring operands:** Users expect comparisons to be non-destructive. Always add back after subtract.
- **Ignoring self-comparison:** `a <= a` can short-circuit to `True` without gates.
- **Classical overflow without handling:** If classical value doesn't fit in qint width, handle gracefully (return constant result).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zero-extension for mixed widths | Custom bit-copying logic | Existing `addition_inplace` handles width differences | Already implemented, tested, handles zero-extension correctly |
| MSB extraction | Custom qubit addressing | `qint.__getitem__` method: `self[64 - self.bits]` | Established pattern, right-aligned qubit storage |
| Zero comparison | Custom MSB checking for all bits | Phase 13 `CQ_equal_width`: `self == 0` | O(n) gates, optimized XOR-based circuit |
| Classical value overflow | Custom bit-length checking | Phase 13 pattern: check if value fits, return constant qbool | Edge case already solved |

**Key insight:** All necessary building blocks exist from Phase 13 (equality) and Phase 7 (arithmetic). Ordering comparisons are compositional - combine existing primitives rather than building new low-level circuits.

## Common Pitfalls

### Pitfall 1: Temporary Qint Allocation in Comparisons

**What goes wrong:** Current `__lt__` allocates `temp = qint(0, width=comp_bits)`, violating the phase requirement of "no temp qint allocation."

**Why it happens:** Seems natural to allocate workspace for subtraction result.

**How to avoid:** Use in-place subtraction on `self`, then restore `self` afterward. Operand is temporarily modified but ultimately preserved.

**Warning signs:** Any `qint()` call inside comparison operators.

### Pitfall 2: Forgetting to Restore Operands

**What goes wrong:** `self -= other` modifies `self` permanently if you don't add back.

**Why it happens:** Easy to forget restoration step in multi-step pattern.

**How to avoid:** Always pair `self -= other` with `self += other`. Consider using try/finally if needed (though quantum operations don't raise exceptions mid-circuit).

**Warning signs:** Tests showing operand widths or values changed after comparison.

### Pitfall 3: Classical Value Not Fitting in Width

**What goes wrong:** Comparing 4-bit qint with classical value `100` (requires 7 bits).

**Why it happens:** User can pass arbitrary classical int to comparison.

**How to avoid:** Check classical value range early:
```python
if type(other) == int:
    max_val = (1 << self.bits) - 1
    if other > max_val:
        return qbool(False)  # 4-bit value always < 100
```

**Warning signs:** Phase 13 pattern already handles this for `==`.

### Pitfall 4: Mixed-Width Operand Handling

**What goes wrong:** Comparing 4-bit qint with 8-bit qint without proper width handling.

**Why it happens:** Subtraction requires same widths, but operands can differ.

**How to avoid:** CONTEXT.md decision: "Different bit widths allowed - zero-extend smaller operand." But for in-place pattern, operate on `self` which has fixed width. The `addition_inplace` method already handles width differences via zero-extension.

**Warning signs:** Incorrect results when comparing different-width qints.

### Pitfall 5: Sign Extension vs Zero Extension

**What goes wrong:** Using sign extension for unsigned qints or zero extension for signed.

**Why it happens:** Two's complement interpretation means qints are signed.

**How to avoid:** CONTEXT.MD decision: "qint uses two's complement representation - Comparisons are signed." However, for ordering comparisons, the subtract-add-back pattern handles this automatically because subtraction respects two's complement semantics.

**Warning signs:** Negative values compared incorrectly.

## Code Examples

Verified patterns from codebase analysis:

### Example 1: Current __lt__ (Allocates Temp - TO BE REFACTORED)
```python
# Source: quantum_language.pyx lines 1506-1565
# WARNING: This allocates temp qint - violates phase requirement
def __lt__(self, other):
    # ... type checking ...

    # PROBLEM: Allocates temporary qint
    temp = qint(0, width=comp_bits)

    # Copy self to temp via XOR
    temp ^= self

    # Subtract other from temp
    temp -= other_qint

    # Extract MSB (sign bit)
    msb = temp[64 - comp_bits]

    # Result: if MSB=1 (negative), self < other is True
    result = qbool()
    result ^= msb  # Copy MSB to result

    return result
```

### Example 2: Refactored __lt__ (In-Place - TARGET PATTERN)
```python
# Source: Phase 14 CONTEXT.md decision + Phase 13 subtract-add-back pattern
def __lt__(self, other):
    """Less-than: a < b means (a - b) is negative"""
    # Self-comparison optimization
    if self is other:
        return qbool(False)

    # Handle classical int
    if type(other) == int:
        # Classical overflow check
        max_val = (1 << self.bits) - 1
        if other < 0:
            return qbool(False)  # qint always >= 0 if unsigned
        if other > max_val:
            return qbool(True)  # qint always < large values
        # No temp qint allocation needed - proceed

    # In-place subtraction
    self -= other

    # Check MSB (sign bit) - if 1, result is negative
    msb = self[64 - self.bits]
    result = qbool()
    result ^= msb

    # Restore operand
    self += other

    return result
```

### Example 3: __le__ with MSB + Zero Check
```python
# Source: Phase 14 CONTEXT.md decision "For a <= b: true if (a - b) is negative OR equal to zero"
def __le__(self, other):
    """Less-than-or-equal: a <= b"""
    # Self-comparison optimization
    if self is other:
        return qbool(True)

    # Classical overflow handling
    if type(other) == int:
        max_val = (1 << self.bits) - 1
        if other < 0:
            return qbool(False)
        if other > max_val:
            return qbool(True)

    # In-place subtraction
    self -= other

    # Check MSB (negative) OR zero
    is_negative = self[64 - self.bits]
    is_zero = (self == 0)  # Uses Phase 13 CQ_equal_width

    # Combine conditions
    result = qbool()
    result ^= is_negative
    temp_zero = qbool()
    temp_zero ^= is_zero
    result |= temp_zero  # OR: negative OR zero

    # Restore operand
    self += other

    return result
```

### Example 4: __ge__ via NOT __lt__
```python
# Source: quantum_language.pyx line 1646 + Python operator overloading patterns
def __ge__(self, other):
    """Greater-than-or-equal: a >= b is NOT (a < b)"""
    return ~(self < other)
```

### Example 5: Phase 13 Equality Pattern (Foundation)
```python
# Source: quantum_language.pyx lines 1414-1429
# Phase 13 established subtract-add-back pattern
def __eq__(self, other):
    if type(other) == qint:
        # Self-comparison optimization
        if self is other:
            return qbool(True)

        # Subtract-add-back pattern
        self -= other
        result = self == 0  # Recursive call uses qint == int
        self += other

        return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Allocate temp qint for comparison | In-place subtract-check-add-back | Phase 14 (this phase) | Eliminates qubit allocation overhead during comparisons |
| Separate implementations for each operator | Compositional: `>=` via `NOT <`, `>` via reversed `<` | Python operator overloading standard | Reduces code duplication, fewer bugs |
| Hand-rolled MSB checking | Use `qint.__getitem__` indexing | Existing codebase pattern | Cleaner code, established right-aligned qubit addressing |
| Custom zero checking in comparisons | Reuse Phase 13 `CQ_equal_width` via `== 0` | Phase 13 | Leverages optimized O(n) XOR-based equality circuit |

**Deprecated/outdated:**
- **Temporary allocation in `__lt__`**: Current implementation allocates `temp = qint(0)` - to be removed in favor of in-place pattern
- **Creating qint from classical int in `__le__`/`__ge__`**: Lines 1619, 1590 create temporary qints - should be eliminated

## Open Questions

### 1. Mixed-Width Zero-Extension Efficiency

**What we know:** CONTEXT.MD decision: "Different bit widths allowed - zero-extend smaller operand." The existing `addition_inplace` method handles width mismatches.

**What's unclear:** Does in-place subtraction on narrower operand require explicit zero-extension, or does Cython/C layer handle automatically?

**Recommendation:** Test with different-width operands. If `self.bits < other.bits`, the addition_inplace already handles zero-extension. Document behavior in implementation.

### 2. Classical Overflow Edge Case Optimization

**What we know:** Phase 13 handles overflow for `==` by returning `qbool(False)` early.

**What's unclear:** For `<=`, should `4-bit qint <= 100` return `qbool(True)` immediately (always less), or fall through to comparison logic?

**Recommendation:** Early return for classical overflow - it's an optimization that saves gates. Example:
```python
if type(other) == int:
    if other > (1 << self.bits) - 1:
        return qbool(True)  # Self is always <= large value
```

### 3. Negative Classical Values in Signed Comparison

**What we know:** CONTEXT.MD decision: "Two's complement interpretation - Negative values are valid operands."

**What's unclear:** When classical value is negative (e.g., `qint(5) <= -3`), how should comparison behave given two's complement?

**Recommendation:** For simplicity in Phase 14, assume qint represents unsigned values (MSB is magnitude bit). Negative classical values can be handled as: if `other < 0`, comparison depends on qint's MSB. But for Phase 14 scope, document assumption that classical values are non-negative (or handle via wrapping).

## Sources

### Primary (HIGH confidence)

- Existing codebase: `/python-backend/quantum_language.pyx` - Current `__eq__`, `__lt__`, `__le__`, `__ge__` implementations (lines 1379-1647)
- Phase 13 tests: `/tests/python/test_phase13_equality.py` - Subtract-add-back pattern verification (lines 119-132)
- Phase 14 CONTEXT.MD: User decisions on comparison semantics, in-place pattern, two's complement

### Secondary (MEDIUM confidence)

- [arXiv:2512.17779 - Demonstration of a quantum comparator on an ion-trap quantum device](https://arxiv.org/pdf/2512.17779) - Conceptual equivalence to reversible subtraction, MSB extraction
- [arXiv:2005.00443 - Quantum arithmetic operations using QFT](https://arxiv.org/pdf/2005.00443) - Two's complement quantum circuits, comparison operations
- [Two's Complement - Wikipedia](https://en.wikipedia.org/wiki/Two's_complement) - MSB sign bit semantics
- [Python Operator Overloading - Real Python](https://realpython.com/operator-function-overloading/) - Best practices for `__lt__`, `__le__`, `__gt__`, `__ge__`
- [Signed Binary Numbers - Electronics Tutorials](https://www.electronics-tutorials.ws/binary/signed-binary-numbers.html) - MSB as sign bit explanation

### Tertiary (LOW confidence)

- [Zero or Sign Extension Blog](https://fgiesen.wordpress.com/2024/10/23/zero-or-sign-extend/) - Mixed-width integer handling (October 2024)
- [Python Operator Overloading - GeeksforGeeks](https://www.geeksforgeeks.org/python/operator-overloading-in-python/) - Operator method patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing project dependencies (Cython, NumPy, pytest)
- Architecture: HIGH - Patterns verified in existing codebase (Phase 13 subtract-add-back)
- Pitfalls: HIGH - Identified from current implementation analysis (temp allocation at line 1549)
- Code examples: HIGH - Extracted from actual codebase with line numbers
- Two's complement semantics: MEDIUM - Verified with academic sources, but unsigned/signed handling needs clarification

**Research date:** 2026-01-27
**Valid until:** 60 days (stable domain - comparison algorithms well-established)
