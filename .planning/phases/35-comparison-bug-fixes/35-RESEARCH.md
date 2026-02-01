# Phase 35: Comparison Bug Fixes - Research

**Researched:** 2026-02-01
**Domain:** C backend equality comparison circuits and Python comparison operator logic
**Confidence:** HIGH

## Summary

Phase 35 fixes three critical bugs in the comparison operators discovered during Phase 31 verification:

1. **BUG-CMP-01 (Equality Inversion)**: eq and ne operators return inverted results for ALL inputs at ALL widths. The `CQ_equal_width` C function appears to generate circuits that produce 0 when values are equal (should be 1) and 1 when different (should be 0). This affects 488 xfail tests across both QQ (qint==qint) and CQ (qint==int) variants.

2. **BUG-CMP-02 (Ordering Comparison Error)**: lt, gt, le, ge operators produce incorrect results for specific (width, a, b) triples where operands span the MSB boundary. Phase 29 fixed three root causes but verification revealed additional failure patterns enumerated in test_compare.py failure sets.

3. **BUG-CMP-03 (Circuit Size Explosion)**: gt and le operators generate circuits that exceed available simulation memory at widths >= 6. Tests are limited to width 5 maximum to avoid memory exhaustion.

The verification framework from Phase 28/31 provides exhaustive test coverage with precise failure predicates. All bugs are documented via xfail markers with strict=True, making it clear when fixes succeed (tests will xpass).

**Primary recommendation:** Fix BUG-CMP-01 first (eq/ne inversion in C backend), then BUG-CMP-02 (ordering comparison logic), then investigate BUG-CMP-03 (circuit explosion root cause). Each fix should be validated against the existing xfail test suite which will automatically convert to passes.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C backend | Project | Circuit generation for comparisons | CQ_equal_width, cCQ_equal_width in IntegerComparison.c |
| Cython | 3.2.4 | Python-C bindings | qint_comparison.pxi contains operator implementations |
| pytest | 8.x+ | Test framework | Existing verification suite in test_compare.py |
| Qiskit | 2.3.0 | Circuit simulation | verify_circuit fixture uses Qiskit for validation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gdb | System | C debugger | Debug C-level circuit generation bugs |
| valgrind | System | Memory profiler | Investigate BUG-CMP-03 memory usage |
| verify_helpers | Project | Test data generation | Already provides exhaustive/sampled pair generation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fix C backend CQ_equal_width | Rewrite in Python | C version is optimized; Python would be slower |
| Fix ordering comparison logic | Rewrite using different algorithm | Current subtract-MSB-check is standard; issue is implementation detail |
| Reduce circuit size for gt/le | Limit supported widths | Would restrict language capability; should fix root cause |

**Installation:**
```bash
# All dependencies already available in project
# C backend compiled via setup.py build_ext --inplace
```

## Architecture Patterns

### Recommended Bug Fix Structure

```
Phase 35 (Comparison Bug Fixes)
├── 35-01: Fix eq/ne comparison inversion in C backend
│   ├── Locate: CQ_equal_width circuit generation logic
│   ├── Diagnose: Why circuit produces inverted result
│   ├── Fix: Minimal change to produce correct result
│   └── Verify: 488 xfail tests should pass
└── 35-02: Fix MSB boundary errors and circuit explosion for ordering comparisons
    ├── Locate: Ordering comparison failure patterns
    ├── Diagnose: Why specific (width,a,b) triples fail
    ├── Fix: Correct MSB boundary logic
    └── Investigate: Circuit explosion at width >= 6
```

### Pattern 1: C Backend Equality Circuit (BUG-CMP-01)

**What:** The `CQ_equal_width` function generates XOR-based equality comparison circuits.

**Current implementation:**
```c
// c_backend/src/IntegerComparison.c lines 35-205
sequence_t *CQ_equal_width(int bits, int64_t value) {
    // Algorithm:
    // 1. Flip qubits where classical bit is 0 (X gates)
    // 2. Multi-controlled X to set result qubit (all must be |1> = equal)
    // 3. Uncompute: reverse the flips

    // Phase 1: X gates where bin[i] == 0
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            x(&seq->seq[current_layer][...], i + 1);
        }
    }

    // Phase 2: Multi-controlled X
    if (bits == 1) {
        cx(&seq->seq[current_layer][...], 0, 1);  // Result qubit 0, control qubit 1
    } else if (bits == 2) {
        ccx(&seq->seq[current_layer][...], 0, 1, 2);
    } else {
        mcx(&seq->seq[current_layer][...], 0, controls, bits);
    }

    // Phase 3: Uncompute X gates
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            x(&seq->seq[current_layer][...], i + 1);
        }
    }
}
```

**Observed behavior:**
- qint(3) == qint(3) returns 0 (should be 1)
- qint(3) == qint(5) returns 1 (should be 0)
- Results are consistently inverted across all test cases

**Hypothesis:**
The multi-controlled X gate (mcx) may have:
1. Target/control qubit order reversed in function call
2. Incorrect initialization of result qubit (should start at |0>)
3. Logic inversion in how "all bits match" maps to result

**Where to look:**
- `c_backend/src/IntegerComparison.c` lines 155-191 (mcx call)
- `c_backend/src/gate.c` mcx implementation
- Result qubit initialization in qbool (src/quantum_language/qbool.pyx)

### Pattern 2: Ordering Comparison MSB Boundary (BUG-CMP-02)

**What:** Ordering comparisons fail when operands span the MSB boundary.

**Current implementation:**
```python
# src/quantum_language/qint_comparison.pxi lines 175-262
def __lt__(self, other):
    # In-place subtraction on self
    self -= other
    # Check MSB (sign bit) - if 1, result is negative (self < other)
    msb = self[64 - self.bits]  # BUG: Should be self[63] for right-aligned storage
    result = qbool()
    result ^= msb  # Copy MSB to result
    # Restore operand
    self += other
    return result
```

**Known issue (partially fixed in Phase 29):**
- Phase 29-16 fixed MSB index to use `self[63]` instead of `self[64 - self.bits]`
- But test_compare.py still shows specific failure patterns for ordering comparisons
- Failure sets in _LT_GE_FAIL_PAIRS and _GT_LE_FAIL_PAIRS enumerate problematic (width,a,b) triples

**Examples of failing cases:**
```python
_LT_GE_FAIL_PAIRS = {
    (1, 1, 0),    # width=1: 1 < 0 returns wrong result
    (2, 0, 3),    # width=2: 0 < 3 (spans MSB) returns wrong result
    (3, 7, 3),    # width=3: 7 < 3 returns wrong result
    # ... 70 total failure cases at widths 1-4
}
```

**Pattern observation:**
- Failures occur when MSB values differ between a and b
- At width=3, MSB=1 means value >= 4; failing cases often have one operand >= 4, one < 4
- Suggests MSB check is not correctly identifying negative results from unsigned subtraction

**Where to look:**
- MSB extraction: qint.__getitem__ implementation for bit indexing
- Subtraction implementation: ensure proper two's complement behavior
- Width extension logic: gt/le use (n+1)-bit widened comparison

### Pattern 3: Circuit Size Explosion (BUG-CMP-03)

**What:** gt and le operators generate exponentially large circuits at widths >= 6.

**Observed behavior:**
```python
# From test_compare.py lines 26-27:
# "Widths >= 6 are excluded because gt/le operators generate circuits
#  that exceed available simulation memory"
```

**Current implementation:**
```python
# src/quantum_language/qint_comparison.pxi lines 264-339
def __gt__(self, other):
    # For qint operand
    if type(other) == qint:
        # a > b means (b - a) is negative
        # Subtract self from other (in-place on other, then restore)
        other -= self
        msb = other[64 - (<qint>other).bits]
        result = qbool()
        result ^= msb
        # Restore operand
        other += self
        return result

    # For int operand: a > b is NOT(a <= b)
    if type(other) == int:
        return ~(self <= other)
```

```python
# src/quantum_language/qint_comparison.pxi lines 341-436
def __le__(self, other):
    # For qint operand
    if type(other) == qint:
        self -= other
        # Check MSB (negative)
        is_negative = self[64 - self.bits]
        # Check zero using Phase 13 pattern
        is_zero = (self == 0)
        # OR combination: result = is_negative | is_zero
        result = qbool()
        result ^= is_negative
        temp_zero = qbool()
        temp_zero ^= is_zero
        result |= temp_zero  # OR gate on qbools
        # Restore operand
        self += other
        return result
```

**Hypothesis:**
- le combines MSB check + zero check + OR operation
- Zero check uses subtract-add-back pattern with CQ_equal_width
- This creates nested operations that may allocate temporary qubits
- At width >= 6, the combination explodes circuit size

**Where to investigate:**
- Count qubit allocations in le circuit at width=5 vs width=6
- Check if OR operation on qbools allocates temporary circuits
- Determine if the issue is gate count or qubit count (memory)
- Use circuit statistics to identify explosion point

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test case generation | Manual test lists | Existing test_compare.py with EXHAUSTIVE_QQ/CQ parametrization | 488 xfail tests already enumerate all known failures |
| Failure prediction | Custom logic | _qq_will_fail, _cq_will_fail predicates in test_compare.py | Precisely enumerate which (width,a,b,op) tuples fail |
| Result validation | Custom pipeline | verify_circuit fixture with width=1 | Proven framework from Phase 28/31 |
| Bug discovery | Manual testing | Run pytest tests/test_compare.py and observe xfail/xpass | Systematic coverage already exists |

**Key insight:** The verification infrastructure already comprehensively documents all bugs via xfail markers. Fixes should be validated by running the existing test suite and observing xfail tests convert to passes.

## Common Pitfalls

### Pitfall 1: Fixing Only One Variant (QQ or CQ)

**What goes wrong:** eq/ne bug affects BOTH qint==qint (QQ) and qint==int (CQ) variants because QQ delegates to CQ via `self == 0` after subtraction.

**Why it happens:** The Python QQ implementation is:
```python
def __eq__(self, other):
    if type(other) == qint:
        self -= other
        result = self == 0  # Calls CQ path with value=0
        self += other
        return result
```

**How to avoid:** Fix the C backend `CQ_equal_width` function. This will automatically fix both QQ and CQ variants since QQ delegates to CQ.

**Warning signs:** CQ tests pass but QQ tests still fail, or vice versa.

### Pitfall 2: Not Checking Controlled Variant

**What goes wrong:** `cCQ_equal_width` (controlled equality) may have the same inversion bug as `CQ_equal_width`.

**Why it happens:** Both functions share similar logic (lines 35-205 vs 207-369 in IntegerComparison.c).

**How to avoid:** After fixing CQ_equal_width, inspect cCQ_equal_width for identical issue. Check if any tests use controlled equality (via `with qbool:` context).

**Warning signs:** Regular comparisons pass but conditional comparisons fail.

### Pitfall 3: Assuming MSB Index Fix Solves All BUG-CMP-02 Cases

**What goes wrong:** Phase 29 fixed MSB index from `64-width` to `63`, but test_compare.py still shows 70+ failing (width,a,b) triples for lt/ge and gt/le.

**Why it happens:** The MSB index fix was necessary but not sufficient. There may be additional issues in:
- How subtraction handles two's complement at boundaries
- How MSB is extracted from right-aligned qubit storage
- How the OR combination works in le/ge

**How to avoid:** Use the precise failure sets (_LT_GE_FAIL_PAIRS, _GT_LE_FAIL_PAIRS) to identify patterns. Test specific failing cases to understand root cause.

**Warning signs:** Some ordering tests pass after MSB fix but many still fail at MSB boundary values.

### Pitfall 4: Trying to Fix Circuit Explosion Without Understanding Root Cause

**What goes wrong:** Attempting to optimize le/gt without knowing why circuits explode leads to incorrect fixes.

**Why it happens:** Circuit explosion could be caused by:
- Qubit allocation (memory issue)
- Gate count (simulation time issue)
- Nested operations creating cascading temporary allocations
- Bug in circuit compilation that generates redundant gates

**How to avoid:**
1. Generate circuits at width=5 and width=6 for le operator
2. Use circuit statistics to count qubits and gates
3. Compare circuit structure to identify explosion point
4. Determine if this is a memory limit or an algorithmic issue

**Warning signs:** "Fixes" that reduce functionality (e.g., limiting width) without addressing root cause.

### Pitfall 5: Breaking Self-Comparison Optimizations

**What goes wrong:** Comparison operators have self-comparison shortcuts (e.g., `a == a` returns True without generating circuit). Bug fixes might accidentally remove these optimizations.

**Why it happens:**
```python
def __eq__(self, other):
    if self is other:
        return qbool(True)  # Shortcut - no circuit generated
```

**How to avoid:** Ensure fixes preserve `self is other` checks at the top of each operator. Verify tests don't accidentally use the same qint instance for both operands.

**Warning signs:** Tests that compare `qint(5) == qint(5)` (two separate instances) pass but performance regresses for repeated self-comparisons.

### Pitfall 6: Forgetting Operand Restoration

**What goes wrong:** In-place subtract-check-add-back pattern must restore operand to original value. Forgetting the add-back leaves operand corrupted.

**Why it happens:** Bug fixes that change control flow may skip the restoration step.

**How to avoid:** All comparison operators must follow pattern:
```python
self -= other
# ... check MSB or zero ...
self += other  # MUST restore
```

**Warning signs:** Operand preservation tests in test_compare_preservation.py fail after comparison.

## Code Examples

### Debugging CQ_equal_width Inversion (BUG-CMP-01)

**Minimal test case:**
```python
# Test equality comparison inversion
import quantum_language as ql

# Case 1: Equal values (should return 1)
ql.circuit()
a = ql.qint(3, width=3)
result_eq = a == 3
qasm_eq = ql.to_openqasm()
# Simulate and check: currently returns 0 (BUG), should return 1

# Case 2: Unequal values (should return 0)
ql.circuit()
b = ql.qint(3, width=3)
result_ne = b == 5
qasm_ne = ql.to_openqasm()
# Simulate and check: currently returns 1 (BUG), should return 0
```

**Debugging approach:**
```bash
# 1. Add printf debugging to CQ_equal_width
# c_backend/src/IntegerComparison.c after line 186:
printf("MCX gate: target=%d, controls=[", 0);
for (int i = 0; i < bits; i++) printf("%d,", controls[i]);
printf("], num_controls=%d\n", bits);

# 2. Rebuild and test
python setup.py build_ext --inplace
python -c "import quantum_language as ql; ql.circuit(); a = ql.qint(3, width=3); r = a == 3"

# 3. Check if mcx target/control order is correct
# Expected: mcx(target=0, controls=[1,2,3], num=3)
# If target is 0 and all controls are 1, result should be 1
```

**Likely fix locations:**
```c
// Option 1: Result qubit initialization issue
// Check if result qubit starts at |0> or |1>

// Option 2: MCX gate target/control swap
// Line 186: mcx(&seq->seq[current_layer][...], 0, controls, bits);
// May need to be: mcx(..., controls, 0, bits); depending on mcx signature

// Option 3: Inversion in gate definition
// Check gate.h mcx signature: void mcx(gate_t *g, qubit_t target, qubit_t *controls, num_t num_controls);
```

### Investigating Circuit Explosion (BUG-CMP-03)

**Test script:**
```python
import quantum_language as ql

def test_le_circuit_size(width):
    """Generate le circuit and report statistics."""
    ql.circuit()
    a = ql.qint(3, width=width)
    b = ql.qint(5, width=width)
    result = a <= b
    qasm = ql.to_openqasm()

    # Count qubits and gates
    lines = qasm.splitlines()
    qubit_count = len([l for l in lines if l.startswith('qubit')])
    gate_count = len([l for l in lines if any(g in l for g in ['cx', 'x', 'h', 'mcx'])])

    print(f"Width {width}: {qubit_count} qubits, {gate_count} gates, {len(lines)} total lines")
    return qubit_count, gate_count

# Test progression
for w in [3, 4, 5, 6]:
    try:
        test_le_circuit_size(w)
    except MemoryError as e:
        print(f"Width {w}: MemoryError - {e}")
        break
```

**Analysis approach:**
1. Run for width 3, 4, 5 to see growth pattern
2. Identify if growth is linear, quadratic, or exponential
3. Check if issue is qubit count (memory) or gate count (simulation time)
4. Compare le (has explosion) vs lt (no explosion) at same width

### Verifying Fixes with Existing Test Suite

**Run specific bug tests:**
```bash
# Test BUG-CMP-01 (eq/ne inversion) - 488 xfail tests
pytest tests/test_compare.py -k "eq or ne" -v
# After fix: expect 488 xpass (previously xfail, now pass)

# Test BUG-CMP-02 (ordering boundary) - 70+ xfail tests
pytest tests/test_compare.py -k "lt or gt or le or ge" -v --tb=short
# After fix: expect failure sets to convert to passes

# Test specific width
pytest tests/test_compare.py -k "width=3" -v
# Focus on one width to isolate issues
```

**Check for regressions:**
```bash
# Run all comparison tests
pytest tests/test_compare.py -v
# Ensure previously passing tests still pass

# Run operand preservation tests
pytest tests/test_compare_preservation.py -v
# Ensure fixes don't corrupt operands
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual MSB index calculation | Fixed at index 63 | Phase 29-16 | Partially fixed BUG-CMP-02 |
| Layer tracking on comparison results | No layer tracking | Phase 29-16 | Fixed GC gate reversal bug |
| n-bit subtraction for GT | (n+1)-bit widened | Phase 29-16 | Fixed unsigned overflow |
| Unknown eq/ne inversion | Documented in test_compare.py | Phase 31 | 488 xfail tests enumerate bug |
| Unknown ordering failures | Precise failure sets enumerated | Phase 31 | _LT_GE_FAIL_PAIRS, _GT_LE_FAIL_PAIRS |
| Unknown circuit explosion | Width limited to 5 | Phase 31 | BUG-CMP-03 documented |

**Current comparison operator structure:**
- `__eq__` QQ: subtract-add-back + CQ_equal_width(0)
- `__eq__` CQ: CQ_equal_width(bits, value) — **INVERTED BUG**
- `__ne__`: ~(self == other)
- `__lt__` QQ/CQ: subtract-add-back + MSB[63] check
- `__gt__` QQ: (n+1)-bit widened, subtract, MSB[63] check
- `__gt__` CQ: create temp qint, delegate to QQ
- `__le__`: MSB check OR zero check — **CIRCUIT EXPLOSION**
- `__ge__`: ~(self < other)

**Known working operators:**
- Addition, subtraction (Phase 30 verified)
- Multiplication (Phase 30 verified, with known controlled bug BUG-COND-MUL-01)
- Bitwise operations (Phase 32 verified)

## Open Questions

1. **Root Cause of eq/ne Inversion**
   - What we know: CQ_equal_width generates inverted results consistently
   - What's unclear: Exact line in C code causing inversion (mcx call? result qubit init?)
   - Recommendation: Add printf debugging to IntegerComparison.c, trace mcx gate parameters

2. **Why MSB Boundary Cases Still Fail**
   - What we know: Phase 29 fixed MSB index to 63, but 70+ cases still fail
   - What's unclear: Is the issue in subtraction overflow, MSB extraction, or comparison logic?
   - Recommendation: Test specific failing triple (e.g., width=2, a=0, b=3) through full pipeline, inspect intermediate states

3. **Circuit Explosion Root Cause**
   - What we know: le/gt explode at width >= 6, lt/ge do not
   - What's unclear: Is explosion from qubit count, gate count, or nested operation depth?
   - Recommendation: Generate circuits at width 5 and 6, use circuit statistics to identify explosion point. May need to profile memory usage.

4. **Whether Controlled Equality is Also Inverted**
   - What we know: cCQ_equal_width has similar structure to CQ_equal_width
   - What's unclear: Does it have the same inversion bug?
   - Recommendation: After fixing CQ_equal_width, test controlled comparisons (via `with qbool:` context) to verify cCQ_equal_width works correctly

5. **Impact of Fixes on Circuit Optimization**
   - What we know: Fixes should not change gate count significantly
   - What's unclear: Will fixing eq inversion affect circuit size/depth?
   - Recommendation: Compare circuit statistics before/after fix to ensure no performance regression

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `c_backend/src/IntegerComparison.c` lines 35-369 — CQ_equal_width and cCQ_equal_width implementations
- Codebase inspection: `src/quantum_language/qint_comparison.pxi` lines 12-475 — all 6 comparison operator implementations
- Codebase inspection: `tests/test_compare.py` lines 1-574 — comprehensive verification suite with 488 xfail tests
- Phase 31 verification: `.planning/phases/31-comparison-verification/31-VERIFICATION.md` — bug discovery and enumeration
- Phase 29 fixes: `.planning/phases/29-c-backend-bug-fixes/29-16-PLAN.md` (implied from context) — MSB index fix
- Bug documentation: `tests/test_compare.py` lines 78-260 — _LT_GE_FAIL_PAIRS and _GT_LE_FAIL_PAIRS failure sets

### Secondary (MEDIUM confidence)
- Phase 31 research: `.planning/phases/31-comparison-verification/31-RESEARCH.md` — comparison operator patterns
- Phase 14 research: `.planning/phases/14-ordering-comparisons/14-RESEARCH.md` — MSB-based comparison design
- Phase 13 research: `.planning/phases/13-equality-comparison/13-RESEARCH.md` — XOR-based equality algorithm

### Tertiary (LOW confidence)
- Circuit explosion hypothesis — based on code reading, not empirical measurement
- MCX gate parameter order — need to verify against gate.h implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already available in project
- Bug enumeration: HIGH — 488 xfail tests precisely document BUG-CMP-01
- Failure patterns: HIGH — _LT_GE_FAIL_PAIRS and _GT_LE_FAIL_PAIRS enumerate BUG-CMP-02
- Circuit explosion: MEDIUM — documented in test comments but root cause not yet investigated
- Fix approach: HIGH — existing test suite provides clear validation path

**Research date:** 2026-02-01
**Valid until:** 90 days (bugs are stable, test suite is comprehensive)
