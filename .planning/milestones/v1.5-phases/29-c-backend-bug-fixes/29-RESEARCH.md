# Phase 29: C Backend Bug Fixes - Research

**Researched:** 2026-01-30
**Domain:** C backend debugging, quantum circuit arithmetic, QFT-based operations
**Confidence:** HIGH

## Summary

This phase fixes four known bugs in the C backend quantum arithmetic implementation: subtraction underflow (BUG-01), less-or-equal comparison (BUG-02), multiplication segfault (BUG-03), and QFT addition with nonzero operands (BUG-04). Research reveals these bugs span Python operator logic, C memory allocation, and QFT phase rotation calculations.

The verification framework from Phase 28 provides the test infrastructure (verify_circuit fixture, input generators, failure formatters). The codebase has no C-level unit testing infrastructure - verification is end-to-end through Python API → C backend → OpenQASM → Qiskit simulation.

**Primary recommendation:** Debug each bug through the full verification pipeline, fix at the appropriate layer (Python vs C), validate with targeted tests before exhaustive verification in Phases 30-33.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | Latest in .venv | Python test framework | Already used for Phase 28 verification framework |
| qiskit | 0.43.2 | OpenQASM simulation | Used by verify_circuit fixture for result validation |
| qiskit-aer | 0.12.1 | Quantum simulator backend | Provides AerSimulator for statevector simulation |
| gdb | System | C debugger | Standard tool for C backend debugging |
| valgrind | System (optional) | Memory debugger | Detect segfaults and memory issues (BUG-03) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Cython | 3.2.4 | Python-C bridge | Debugging Python→C interaction bugs |
| printf debugging | N/A | C logging | Quick inspection of C values/flow |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full pipeline tests | C unit tests with Check/Unity | Would need test infrastructure build-out, deferred beyond v1.5 scope |
| gdb | lldb | Platform-specific preference, gdb more universal on Linux |
| Manual debugging | Automated bisection | Manual more targeted for known bug symptoms |

**Installation:**
```bash
# Already available in project
pytest  # via .venv
qiskit  # via .venv
gdb     # system package (apt-get install gdb / brew install gdb)
```

## Architecture Patterns

### Bug Fix Pattern: Locate-Reproduce-Fix-Verify

**Structure:**
```
1. Locate bug layer (Python operator vs C implementation)
2. Reproduce with minimal test case
3. Apply minimal fix at correct layer
4. Verify through full pipeline (Phase 28 framework)
5. Verify no regressions (run existing tests)
```

### Pattern 1: Python Operator Logic Bugs

**What:** Bugs in Python-level arithmetic/comparison operator implementation (qint.pyx)

**When to use:** When bug involves operator semantics, not C circuit generation

**Example (BUG-01: Subtraction underflow):**
```python
# qint.pyx line 852-854
def __sub__(self, other):
    a = qint(value = self.value, width = result_width)
    a -= other  # Calls addition_inplace(other, invert=True)
    return a

# Problem: Creates new qint with self.value, but self.value is
# the *initialization* value, not the current quantum state.
# For out-of-place operations, should track quantum result,
# not copy classical initialization value.
```

**Fix approach:**
- Operator copies initialization value instead of quantum state
- Out-of-place subtraction creates fresh qint, adds/subtracts operand
- Bug is semantic, not circuit-level

### Pattern 2: Comparison Logic Bugs

**What:** Comparison operators using MSB check + zero check patterns

**When to use:** BUG-02 (less-or-equal comparison)

**Example (BUG-02: 5<=5 returns 0):**
```python
# qint.pyx lines 1947-1959
def __le__(self, other):
    self -= other  # 5-5 = 0
    is_negative = self[64 - self.bits]  # MSB check
    is_zero = (self == 0)  # Zero check via equality
    result = qbool()
    result ^= is_negative
    temp_zero = qbool()
    temp_zero ^= is_zero
    result |= temp_zero  # OR combination: negative OR zero
    self += other  # Restore
    return result

# Bug: Logic error in how is_negative and is_zero are combined.
# Self-comparison (5<=5) should return True (zero case).
```

**Fix approach:**
- Verify MSB extraction logic (bit indexing)
- Verify zero-check equality operator
- Verify OR combination logic
- May be issue in qbool initialization or XOR/OR operations

### Pattern 3: C Memory Allocation Bugs

**What:** Segfaults from insufficient memory allocation in C backend

**When to use:** BUG-03 (multiplication segfault)

**Example (BUG-03: Multiplication segfaults):**
```c
// IntegerMultiplication.c line 107
for (int i = 0; i < mul->num_layer; ++i) {
    mul->seq[i] = calloc(2 * bits, sizeof(gate_t));
    // Allocates 2*bits gates per layer
    // May be insufficient for actual gate count in multiplication
}

// num_layer = bits * (2 * bits + 6) - 1  (line 91)
// But gates_per_layer may exceed 2*bits for certain bit widths
```

**Fix approach:**
- Use valgrind to detect exact segfault location
- Check if gates_per_layer exceeds allocated size
- Increase allocation or calculate exact max gates per layer
- Scoped to multiplication code path only (per context decisions)

### Pattern 4: QFT Phase Rotation Bugs

**What:** Incorrect phase rotation angles in QFT-based addition

**When to use:** BUG-04 (QFT addition with nonzero operands)

**Example (BUG-04: QFT addition fails with 3+5):**
```c
// IntegerAddition.c CQ_add function (lines 49-56)
for (int i = 0; i < bits; ++i) {
    for (int j = 0; j < bits - i; ++j) {
        rotations[j + i] += bin[bits - i - 1] * 2 * M_PI / (pow(2, j + 1));
    }
}

// QFT addition: QFT -> phase rotations -> inverse QFT
// Bug likely in:
// - Rotation angle calculation
// - Qubit indexing (offset issues)
// - Phase accumulation logic
```

**Fix approach:**
- Test with simple cases: 0+1, 1+0, 1+1, 3+5
- Compare against known-correct QFT addition formula
- Check qubit offset calculations (lines 23-30 layout comments)
- Verify bin[] two's complement conversion

### Anti-Patterns to Avoid

- **Changing multiple bugs per commit:** Each fix must be separate commit for revertability
- **Refactoring during bug fixes:** Minimal patches only, no cleanup beyond what's needed
- **Fixing BUG-05:** Explicitly excluded from Phase 29 scope
- **Adding exhaustive tests now:** Deferred to Phases 30-33, this phase uses targeted tests

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| C unit test framework | Custom assertion macros | Phase 28 verify_circuit + pytest | Full pipeline already working, C unit tests are infrastructure build-out |
| Memory leak detection | printf + manual tracking | valgrind | Industry standard, catches issues missed by manual inspection |
| Quantum circuit validation | Custom simulator | Qiskit AerSimulator | Already integrated, trusted reference implementation |
| Test case generation | Manual test lists | verify_helpers.py generators | Already provides exhaustive + sampled patterns |

**Key insight:** Phase 28 already built the verification harness. Don't rebuild testing infrastructure - use what exists and focus on bug fixes.

## Common Pitfalls

### Pitfall 1: Debugging Wrong Layer

**What goes wrong:** Spending time debugging C backend when bug is in Python operator logic

**Why it happens:** Assumption that "quantum operations = C code"

**How to avoid:**
1. Read Python operator implementation first (qint.pyx)
2. Check if bug involves operator semantics (value copying, operand ordering)
3. Only dive into C if Python logic is correct

**Warning signs:**
- Bug involves out-of-place operations (__add__, __sub__, not __iadd__)
- Bug involves initialization value vs quantum state confusion
- Bug reproduces with simple Python expressions

### Pitfall 2: Incomplete Test Coverage

**What goes wrong:** Fixing specific case (3-7) but missing other underflow cases

**Why it happens:** Testing only documented bug symptom

**How to avoid:**
- Test a few nearby cases (2-6, 4-8, 1-5)
- Include edge cases (0-1, max-1, max-max)
- Use verify_helpers generators for systematic coverage

**Warning signs:**
- Only testing exact values from bug report
- Not testing boundary conditions
- Assuming single fix covers all cases

### Pitfall 3: QFT Addition Qubit Layout Confusion

**What goes wrong:** Fixing phase rotations but wrong qubits receive gates

**Why it happens:** QFT addition uses specific qubit layout (documented in code comments)

**How to avoid:**
```c
// From IntegerAddition.c line 27-30 (CQ_add layout)
// Qubit layout for CQ_add(bits):
// - Qubits [0, bits-1]: Target operand (modified in place)
// Classical value comes from value parameter

// From IntegerAddition.c line 132-134 (QQ_add layout)
// Qubit layout for QQ_add(bits):
// - Qubits [0, bits-1]: First operand (target, modified in place)
// - Qubits [bits, 2*bits-1]: Second operand (control)
```

**Verify:**
- Check offset calculations match layout comments
- Trace qubit_array mapping in Python (qint.pyx addition_inplace)
- Validate run_instruction() maps logical→physical qubits correctly

**Warning signs:**
- CQ_add (classical+quantum) works, QQ_add (quantum+quantum) fails
- Results vary with operand order
- Results correct for one operand being zero

### Pitfall 4: Segfault Root Cause Misdiagnosis

**What goes wrong:** Increasing buffer size without understanding actual memory issue

**Why it happens:** Treating symptom (segfault) without valgrind diagnosis

**How to avoid:**
1. Run valgrind to get exact fault address and access pattern
2. Check if fault is read-past-end vs write-past-end vs use-after-free
3. Calculate expected max gates_per_layer vs allocated size
4. Only increase allocation if proven insufficient

**Warning signs:**
- "Just doubling buffer size to be safe"
- Not checking actual gates_per_layer values
- Assuming all widths have same issue

## Code Examples

Verified patterns from codebase:

### Debugging C Backend with Python Test

```python
# tests/bugfix/test_bug01_subtraction.py
import pytest
from verify_helpers import format_failure_message
import quantum_language as ql

def test_subtraction_underflow(verify_circuit):
    """Test BUG-01: qint(3) - qint(7) on 4-bit integers."""
    def circuit_builder():
        a = ql.qint(3, width=4)
        b = ql.qint(7, width=4)
        result = a - b
        # Expected: (3 - 7) mod 16 = -4 mod 16 = 12
        return 12

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message(
        "sub", [3, 7], 4, expected, actual
    )
```

### Minimal Reproduction in Python REPL

```python
# Quick iteration during debugging
import quantum_language as ql

ql.circuit()  # Reset
a = ql.qint(5, width=4)
b = ql.qint(5, width=4)
result = a <= b

qasm = ql.to_openqasm()
# Simulate with qiskit, inspect result
# Should be 1 (True), currently returns 0 (BUG-02)
```

### Valgrind for Segfault Diagnosis

```bash
# Build with debug symbols
cmake -DCMAKE_BUILD_TYPE=Debug .
make

# Run through Python test with valgrind
valgrind --leak-check=full --track-origins=yes \
    python -m pytest tests/bugfix/test_bug03_multiplication.py -v

# Look for:
# - "Invalid write of size X"
# - "Address 0x... is 0 bytes after a block of size Y"
# Indicates gates_per_layer allocation too small
```

### Printf Debugging in C Backend

```c
// IntegerMultiplication.c - add before segfault location
printf("DEBUG: mul->num_layer=%d, layer=%d, gates_allocated=%d, gates_needed=%d\n",
       mul->num_layer, layer, 2*bits, mul->gates_per_layer[layer]);

// Recompile and run test
// Output shows gates_needed exceeds gates_allocated
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual circuit inspection | Qiskit simulation verification | Phase 28 (2026-01-30) | Automated bug detection through full pipeline |
| Inline test cases | Parametrized pytest with generators | Phase 28 (2026-01-30) | Systematic coverage, reproducible failures |
| C-only development | Python→C→OpenQASM→Qiskit pipeline | Phase 25-27 (2026-01-30) | Multiple validation points, export standard format |

**Deprecated/outdated:**
- Manual test.py inspection: Phase 28 replaced with pytest + verify_circuit
- CC_add/CC_mul: Phase 11 removed purely classical operations (no quantum gates)

## Open Questions

Things that couldn't be fully resolved:

1. **BUG-05 (circuit() state reset)**
   - What we know: circuit() doesn't reset gate accumulation (discovered Phase 28-02)
   - What's unclear: Root cause location (Python wrapper vs C backend state management)
   - Recommendation: Document and defer - explicitly excluded from Phase 29 per context decisions

2. **Multiplication segfault width pattern**
   - What we know: Segfaults "at certain widths" (BUG-03 description)
   - What's unclear: Exactly which widths fail (1-bit? 4-bit? Width-dependent?)
   - Recommendation: Test widths 1-4 exhaustively during bug reproduction to identify pattern

3. **QFT addition "both nonzero" specificity**
   - What we know: QFT addition fails with both operands nonzero (3+5 example)
   - What's unclear: Does 0+N or N+0 work? Is bug in phase accumulation or qubit indexing?
   - Recommendation: Test 0+0, 0+1, 1+0, 1+1, 3+5 to isolate failure pattern

4. **C unit test framework choice**
   - What we know: No C testing infrastructure exists (TESTING.md analysis)
   - What's unclear: Best lightweight framework (Check vs Unity vs manual)
   - Recommendation: Marked as "Claude's discretion" in context - defer or use minimal printf-based approach

## Sources

### Primary (HIGH confidence)

- **Codebase files** (Read tool):
  - `src/quantum_language/qint.pyx` - Python operator implementations
  - `c_backend/src/IntegerAddition.c` - QFT-based addition implementation
  - `c_backend/src/IntegerMultiplication.c` - Multiplication with potential segfault
  - `c_backend/src/IntegerComparison.c` - Comparison operator C implementations
  - `c_backend/src/gate.c` - QFT and QFT_inverse implementations
  - `tests/verify_helpers.py` - Phase 28 input generators
  - `tests/conftest.py` - Phase 28 verify_circuit fixture
  - `.planning/REQUIREMENTS.md` - Bug definitions (BUG-01 through BUG-04)
  - `.planning/STATE.md` - Known bugs list and Phase 28 completion status
  - `.planning/codebase/ARCHITECTURE.md` - C backend architecture patterns
  - `.planning/codebase/TESTING.md` - Current test infrastructure analysis
  - `.planning/codebase/STACK.md` - Technology stack and versions
  - `.planning/phases/29-c-backend-bug-fixes/29-CONTEXT.md` - Phase decisions and constraints
  - `.planning/phases/28-verification-framework-init/28-01-SUMMARY.md` - Phase 28 framework details

### Secondary (MEDIUM confidence)

- **Personal knowledge** (verified against codebase):
  - QFT-based quantum arithmetic: Phase rotation formula 2π/(2^k) for k-th controlled phase gate
  - Two's complement arithmetic: Subtraction via negation (invert=True) in addition_inplace
  - Qiskit statevector simulation: Deterministic results with shots=1

### Tertiary (LOW confidence)

None - all findings from codebase files or documented project state.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest/qiskit/gdb verified in codebase, standard tooling
- Architecture: HIGH - traced actual code, qubit layouts documented in C comments
- Pitfalls: HIGH - derived from actual bug symptoms and code patterns

**Research date:** 2026-01-30
**Valid until:** 30 days (codebase stable, stack mature)

---
*Research complete for Phase 29 planning*
