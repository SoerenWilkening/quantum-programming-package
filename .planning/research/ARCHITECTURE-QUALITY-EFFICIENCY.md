# Architecture Patterns: v4.1 Quality & Efficiency

**Domain:** Bug fixes, security hardening, and quality improvements to a C/Cython/Python quantum framework
**Researched:** 2026-02-22

## Architecture Context

This milestone does NOT change the architecture. The three-layer design (C backend -> Cython bridge -> Python frontend) is validated and stays. This document describes patterns for making changes WITHIN the existing architecture safely.

## Patterns to Follow

### Pattern 1: Defensive C Function Entry

**What:** Add NULL checks and bounds validation at the entry point of every public C function that receives a pointer or index parameter.

**When:** Applying to all functions called from Cython that accept `circuit_t*`, `sequence_t*`, or qubit indices.

**Why:** CONCERNS.md identifies that `_core.pyx` casts circuit pointers via `<circuit_t*><unsigned long long>` without validation. A corrupted or freed pointer leads to segfault or memory corruption.

**Example:**
```c
// BEFORE: No validation
void run_instruction(sequence_t *seq, qubit_t *qubits, int invert, circuit_t *circ) {
    for (int i = 0; i < seq->length; i++) {
        add_gate(circ, &seq->gates[i], ...);
    }
}

// AFTER: Defensive entry
void run_instruction(sequence_t *seq, qubit_t *qubits, int invert, circuit_t *circ) {
    if (!seq || !qubits || !circ) return;  // Silent return for NULL
    if (!circ->allocator) return;           // Circuit not initialized
    for (int i = 0; i < seq->length; i++) {
        add_gate(circ, &seq->gates[i], ...);
    }
}
```

**Trade-off:** NULL checks add ~1 instruction per function call. For hot-path functions called millions of times (like `add_gate`), use `assert()` instead of runtime checks -- asserts are compiled out in release builds.

### Pattern 2: Bounds-Checked Scratch Buffer Access

**What:** Validate required slot count before writing into the `qubit_array` global buffer.

**When:** Any Cython wrapper that populates `qubit_array` before calling a C function.

**Why:** `qubit_array` is fixed at `4 * 64 + NUMANCILLY = 384` elements. Deep binary operations on wide qints can exceed this silently.

**Example:**
```python
# In _core.pyx, before any operation that fills qubit_array:
cdef inline void _validate_qubit_array(int required_slots) except *:
    if required_slots > QUBIT_ARRAY_SIZE:
        raise ValueError(
            f"Operation requires {required_slots} qubit slots but buffer has {QUBIT_ARRAY_SIZE}. "
            f"Reduce operand width or file a bug report."
        )

# Usage before each C backend call:
_validate_qubit_array(a.width + b.width + ANCILLA_OVERHEAD)
```

### Pattern 3: Binary Search for Sorted Arrays

**What:** Replace linear scan with binary search in `smallest_layer_below_comp()`.

**When:** The `occupied_layers_of_qubit[qubit]` array is monotonically sorted by construction.

**Why:** Every `add_gate()` call invokes this function. For circuits with 10K+ layers per qubit, the O(L) scan becomes a bottleneck.

**Example:**
```c
// BEFORE: Linear scan O(L)
static layer_t smallest_layer_below_comp(circuit_t *circ, int qubit, layer_t comp) {
    for (int i = circ->used_occupation_indices_per_qubit[qubit] - 1; i >= 0; i--) {
        if (circ->occupied_layers_of_qubit[qubit][i] < comp) {
            return circ->occupied_layers_of_qubit[qubit][i];
        }
    }
    return -1;
}

// AFTER: Binary search O(log L)
static layer_t smallest_layer_below_comp(circuit_t *circ, int qubit, layer_t comp) {
    int lo = 0;
    int hi = circ->used_occupation_indices_per_qubit[qubit] - 1;
    layer_t result = -1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (circ->occupied_layers_of_qubit[qubit][mid] < comp) {
            result = circ->occupied_layers_of_qubit[qubit][mid];
            lo = mid + 1;  // Search for larger values still below comp
        } else {
            hi = mid - 1;
        }
    }
    return result;
}
```

### Pattern 4: Coverage-Guided Test Writing

**What:** Use coverage reports to prioritize which tests to write, not intuition.

**When:** After setting up pytest-cov and running the first coverage report.

**Why:** The project has 8,365+ tests but no coverage measurement. Some files may have 95% coverage while others have 20%. Intuition-based test writing often duplicates existing coverage instead of filling gaps.

**Process:**
1. Run: `pytest tests/python/ --cov=quantum_language --cov-report=html`
2. Open `htmlcov/index.html`
3. Sort by coverage percentage (ascending)
4. Write tests for the least-covered files first, prioritizing:
   - Files with known bugs (qint_division.pxi, qint_mod.pyx)
   - Files with security concerns (_core.pyx pointer handling)
   - Files with fragility warnings (qint.__del__ uncomputation)

### Pattern 5: Bug Fix with Regression Test

**What:** Every bug fix MUST include a test that fails before the fix and passes after.

**When:** All 7 carry-forward bugs + 2 additional bugs (qarray `*=`, qiskit_aer).

**Why:** Without regression tests, bugs recur. The project already has a `xfail` pattern for known bugs.

**Process:**
```python
# Step 1: Write the test (should be xfail initially)
@pytest.mark.xfail(reason="BUG-MOD-REDUCE: _reduce_mod corruption", strict=True)
def test_modular_reduction_large_modulus():
    ql.circuit()
    a = ql.qint_mod(15, N=17)
    b = ql.qint_mod(3, N=17)
    c = a + b  # Should be (15+3) mod 17 = 1
    # Verify via QASM export + simulation

# Step 2: Fix the bug
# Step 3: Remove xfail marker
# Step 4: Verify test passes
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Fixing Bugs in the Preprocessed File

**What:** Editing `qint_preprocessed.pyx` directly to fix bugs.

**Why bad:** The preprocessed file is a generated artifact of `qint.pyx` + `.pxi` includes. Edits to the preprocessed file will be overwritten when `build_preprocessor.py` runs. The canonical source is `qint.pyx` and its `.pxi` includes.

**Instead:** Always edit `qint.pyx` or the relevant `.pxi` file, then regenerate the preprocessed version.

### Anti-Pattern 2: Conditional Compilation for Bug Fixes

**What:** Using `#ifdef FIX_BUG_XYZ` to gate bug fixes behind feature flags.

**Why bad:** Introduces combinatorial complexity. Every conditional doubles the number of code paths to test. Bug fixes should be unconditional -- the fixed behavior IS the correct behavior.

**Instead:** Fix the bug, update the tests, remove the xfail markers. If the fix changes behavior that some users depend on, it is a new version with release notes, not a feature flag.

### Anti-Pattern 3: Adding New Global State for Debugging

**What:** Adding module-level variables to `_core.pyx` to track debugging information.

**Why bad:** `_core.pyx` already has too much global state (CONCERNS.md: "Global module-level state in _core.pyx"). Every new global is another thing that `circuit()` must reset, another source of stale-state bugs, and another barrier to eventual multi-circuit support.

**Instead:** Use the existing `allocator_stats_t` for tracking, or add debug info to `circuit_t` (scoped to the circuit lifetime).

### Anti-Pattern 4: Optimizing Before Measuring

**What:** Applying binary size reduction flags without benchmarking before and after.

**Why bad:** The project established "profile before optimizing" as a key decision in v2.2. Compiler flags can have unexpected interactions (LTO was disabled due to a GCC bug). Size optimization flags like `-Os` can regress hot-path performance.

**Instead:** Always:
1. Measure baseline (size + performance benchmarks)
2. Apply change
3. Measure result
4. Revert if regression exceeds 15% tolerance

## Component Boundaries for This Milestone

| Component | What Changes | What Does NOT Change |
|-----------|-------------|---------------------|
| C backend (`c_backend/src/`) | Bug fixes in arithmetic/division, bounds checks added, optimizer binary search | Module structure, header organization, sequence files |
| Cython bridge (`*.pyx`) | Pointer validation, bounds checking, bug fixes in operator dispatch | API surface, class hierarchy, global state architecture |
| Python frontend (`*.py`) | No changes expected | compile.py, grover.py, amplitude_estimation.py |
| Build system (`setup.py`) | Compiler flag changes for binary size | Build discovery, extension definitions |
| Config (`pyproject.toml`) | New dependency groups, coverage config, qiskit-aer declaration | Ruff config, build-system |
| Tests | New regression tests, C test integration, coverage reporting | Test patterns, fixtures, conftest.py structure |
| Makefile | New targets (cppcheck, vulture, coverage) | Existing targets (test, memtest, asan-test, profile-*) |

## Sources

- `.planning/codebase/ARCHITECTURE.md` -- existing architecture documentation
- `.planning/codebase/CONCERNS.md` -- security, fragility, and performance concerns
- `c_backend/src/optimizer.c` -- linear scan code reviewed
- `src/quantum_language/_core.pyx` -- global state and pointer handling reviewed
- `setup.py` -- current compiler flags reviewed

---
*Architecture patterns for: v4.1 Quality & Efficiency*
*Researched: 2026-02-22*
