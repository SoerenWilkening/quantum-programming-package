# Phase 60: C Hot Path Migration - Research

**Researched:** 2026-02-06
**Domain:** Python/Cython to C migration, performance optimization, profiling
**Confidence:** HIGH

## Summary

This phase migrates the top 3 hot paths (identified by fresh profiling) from Python/Cython to pure C, eliminating Python/C boundary crossing overhead. The codebase already has a mature C backend (`c_backend/src/`) with a well-defined interface through Cython `.pxd` declarations and a `run_instruction()` gateway. The primary overhead to eliminate is the per-operation pattern of: (1) Python accessor calls to read global state, (2) qubit array population in Cython, (3) C function call for sequence generation, (4) `run_instruction()` applying gates to circuit. By moving entire operation paths to C, all four steps collapse into a single C function call.

The architecture is well-suited for this migration. Each arithmetic/bitwise/comparison operation follows a consistent pattern: read circuit pointer and control state, populate `qubit_array` with indices, call a C sequence generator (e.g., `QQ_add`), and pass to `run_instruction()`. The C backend already has all the infrastructure (`circuit_t`, `gate_t`, `add_gate()`, `allocator_alloc/free`) to perform these operations natively. The key challenge is moving Python global state access (circuit pointer, controlled flag, control qubit, ancilla) into C-accessible state.

**Primary recommendation:** Create thin C wrapper functions (one per hot path) that accept `circuit_t*`, control state, and qubit indices as parameters, eliminating all Python boundary crossings within the operation. The Cython layer becomes a single function call that passes pre-fetched state.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Migration scope:**
- Strictly follow profiling data: migrate the top 3 hot paths identified by fresh profiling (re-profile at start of phase to account for phases 57-59 optimizations)
- Always migrate top 3 regardless of improvement percentage -- no minimum threshold to qualify
- Success measured by either per-operation OR aggregate >20% improvement (either counts)
- Include partial-C paths as candidates if profiling shows remaining boundary crossings are the bottleneck (Claude's discretion per path)

**Code approach:**
- Hand-written C code (not generated)
- One separate C file per migrated path (not a single hot_paths.c)
- Replace Python/Cython version entirely after verification -- no fallback path kept
- Port style: Claude decides per path whether to do a faithful port or clean reimplementation based on complexity and optimization potential

**Skip criteria:**
- No hard blockers -- always migrate top 3, work around any obstacles
- run_instruction() elimination is one optimization among many, not mandatory for every path
- Include CYT-04 (nogil) as part of this phase where it makes sense in context of C migration

**Validation approach:**
- Existing test suite + new targeted C-level unit tests for each migrated function
- Per-path before/after benchmarks using pytest-benchmark (statistical analysis)
- Atomic transition per path: write C, verify tests pass, remove Python code, one commit per path

### Claude's Discretion

- Port style per path (faithful port vs clean reimplementation)
- Whether partial-C paths qualify as candidates
- Where CYT-04 (nogil) makes sense in context

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| cProfile + pstats | stdlib | Fresh profiling at phase start | Already established in Phase 55, no dependencies |
| pytest-benchmark | >=5.2.3 | Per-path before/after measurement | Already installed, `make benchmark` target exists |
| gcc/clang | system | C compilation | Already used for c_backend, -O3 flags configured |
| Cython | >=3.0 | Thin wrapper layer | Already the compilation layer, .pxd declarations exist |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| make profile-cprofile | N/A | cProfile with quantum operations | Initial hot path identification |
| make profile-cython | N/A | Cython annotation HTML | Verify yellow-line elimination |
| QUANTUM_PROFILE=1 build | N/A | Function-level Cython profiling | When cProfile needs Cython function names |
| make verify-optimization | N/A | Full rebuild + annotate + test + benchmark | Final verification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cProfile | py-spy | py-spy gives native frames but requires privileges; cProfile sufficient for Python-level hot paths |
| Hand-written C | Code generation script | User locked decision: hand-written C for this phase |
| Per-path C files | Single hot_paths.c | User locked decision: separate files |

**Installation:**
```bash
# Already available
pip install '.[profiling]'  # pytest-benchmark
QUANTUM_PROFILE=1 pip install -e .  # Cython profiling build
```

## Architecture Patterns

### Recommended Project Structure

```
c_backend/
  include/
    hot_path_iadd.h          # Header for iadd hot path
    hot_path_xor.h           # Header for xor hot path
    hot_path_add.h           # Header for add hot path (or whichever top 3)
  src/
    hot_path_iadd.c          # Implementation
    hot_path_xor.c           # Implementation
    hot_path_add.c           # Implementation
src/quantum_language/
  _core.pxd                  # Add cdef extern declarations for new C functions
  qint_preprocessed.pyx      # Replace Cython operations with thin C calls
setup.py                     # Add new .c files to c_sources list
tests/
  c/
    test_hot_path_iadd.c     # C-level unit tests
    test_hot_path_xor.c
    test_hot_path_add.c
  benchmarks/
    test_qint_benchmark.py   # Per-path before/after benchmarks
```

### Pattern 1: Current Operation Flow (Before Migration)

**What:** Every qint operation follows this pattern through Python/Cython/C layers:
```
Python operator (__iadd__)
  -> Cython cdef method (addition_inplace)
    -> Python call: _get_circuit()          # boundary crossing
    -> Python call: _get_controlled()       # boundary crossing
    -> Python call: _get_control_bool()     # boundary crossing
    -> qubit_array population (Cython loop) # mixed Python/C
    -> C call: QQ_add(bits) or CQ_add()    # pure C, returns sequence_t*
    -> C call: run_instruction(seq, arr, invert, circ)  # pure C
```

**Overhead sources:**
1. `_get_circuit()` -- Python function call to read cdef global, returns unsigned long long
2. `_get_controlled()` -- Python function call to read cdef global
3. `_get_control_bool()` -- Python function call to read cdef global
4. `_get_ancilla()` -- Python function call to get numpy array
5. `qubit_array` population -- Cython typed loops but still in Python runtime
6. `run_instruction()` per-gate malloc/memcpy -- allocates gate_t for each gate individually

### Pattern 2: Migrated Operation Flow (After Migration)

**What:** Entire operation executes in C with single Cython entry point:
```
Python operator (__iadd__)
  -> Cython thin wrapper:
    - fetch circuit_t* (one C cast)
    - fetch self.qubits, self.bits
    - C call: c_iadd_inplace(circuit, self_qubits, self_bits, other_qubits, other_bits, controlled, control_qubit)
      -> builds qubit_array in C
      -> calls QQ_add() / CQ_add() in C
      -> calls run_instruction() in C (or inlines it)
      -> all in single C function, no Python callbacks
```

**Key change:** The qubit array population, sequence generation, and gate injection all happen in a single C function with no Python boundary crossings.

### Pattern 3: C Hot Path Function Signature

**What:** Each migrated C function takes all necessary state as parameters:
```c
// Example for iadd (in-place addition)
void hot_path_iadd(
    circuit_t *circ,           // From _get_circuit() cast
    unsigned int *self_qubits, // From self.qubits numpy array
    int self_bits,             // From self.bits
    unsigned int *other_qubits,// From other.qubits (NULL for int operand)
    int other_bits,            // From other.bits (0 for int operand)
    int64_t classical_value,   // For int operand
    int invert,                // For subtraction (invert=1)
    int controlled,            // From _get_controlled()
    unsigned int control_qubit,// From _get_control_bool().qubits[63]
    unsigned int *ancilla,     // From _get_ancilla()
    int num_ancilla            // NUMANCILLY
);
```

### Pattern 4: CYT-04 (nogil) Integration

**What:** Release GIL for C-only code paths where no Python callbacks occur.

Where it applies:
- The new C hot path functions contain no Python calls
- Cython wrapper can use `with nogil:` around the C function call
- Benefit: allows other Python threads to run during circuit generation

Where it does NOT apply:
- qint.__init__() -- calls Python accessors, scope stack, dependency tracking
- __del__() / _do_uncompute() -- calls Python list operations, sort
- Operations that create new qint objects (allocate, set properties)

**Practical impact for this project:** Likely minimal since circuit generation is typically single-threaded. However, it is correct to implement and eliminates a class of future bottlenecks. Apply nogil to the C function calls in the Cython wrappers.

### Anti-Patterns to Avoid

- **Partial migration that still calls Python:** If the C function needs to call back into Python (e.g., to access global state), the boundary crossing overhead remains. All state must be passed as parameters.
- **Duplicating Python object management in C:** Do not try to manage qint Python objects from C. The C layer only manipulates the circuit_t and qubit arrays.
- **Changing the public API:** This is purely internal. `qint.__iadd__`, `qint.__xor__`, etc. must continue to work identically.
- **Forgetting `setup.py` updates:** Each new `.c` file must be added to `c_sources` list in setup.py. Missing this causes linker errors.
- **Breaking the preprocessor pipeline:** `qint.pyx` uses `include` directives processed by `build_preprocessor.py`. Changes to `.pxi` files must be verified through the preprocessor.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate sequence generation | Custom gate loop | Existing `QQ_add()`, `CQ_add()`, etc. | These are the C backend's core functions, already correct and cached |
| Gate injection to circuit | Manual layer management | Existing `run_instruction()` / `add_gate()` | Complex layer optimization logic already handles placement |
| Qubit allocation | Custom allocator | Existing `allocator_alloc()` / `allocator_free()` | Pool-based allocator with stats tracking already works |
| Benchmark infrastructure | Custom timing | `pytest-benchmark` with `benchmark.pedantic()` | Already configured with `setup` callbacks for state isolation |
| Profiling infrastructure | Custom profiler | `cProfile + pstats` via `make profile-cprofile` | Already established, Cython function visibility with QUANTUM_PROFILE=1 |

**Key insight:** The C backend already has all the building blocks. The migration is about calling them from C instead of from Cython, not about reimplementing them.

## Common Pitfalls

### Pitfall 1: Qubit Array Layout Mismatch

**What goes wrong:** C function receives qubit indices in wrong order, producing incorrect circuits.
**Why it happens:** The qint.qubits array is right-aligned (indices `[64-width]` through `[63]`), and different operations have different qubit layout conventions (QQ_add: `[target, b-register]`, cQQ_add: `[target, b, control]`).
**How to avoid:** Extract qubit indices in the Cython wrapper (which already knows the layout) and pass a flat C array to the C function. Do not pass the raw 64-element numpy array.
**Warning signs:** Test failures in simulation/verification tests, wrong gate counts.

### Pitfall 2: Global State Consistency

**What goes wrong:** C function reads stale circuit state because Python globals changed between Cython fetching the pointer and the C function using it.
**Why it happens:** The circuit_t* is a module-level cdef variable in _core.pyx. If circuit() is called between fetching and using it, the pointer is invalidated.
**How to avoid:** This is the existing pattern -- each operation fetches circuit_t* at the start. The C migration simply moves the fetch to the Cython entry point and passes it down. No new risk introduced.
**Warning signs:** Segfaults, circuit corruption.

### Pitfall 3: Memory Ownership in run_instruction

**What goes wrong:** `run_instruction()` currently `malloc`s a new `gate_t` for every gate in the sequence and `memcpy`s from the source. This is a significant per-gate overhead.
**Why it happens:** The function was designed for generality -- sequences are templates that get qubit-remapped into the circuit.
**How to avoid:** For this phase, keep using `run_instruction()` as-is. Optimizing the per-gate allocation would be a deeper change. The primary win is eliminating the Python boundary crossings, not the C-internal allocation.
**Warning signs:** Attempting to optimize `run_instruction()` internals can break the qubit remapping logic.

### Pitfall 4: Controlled Operation State

**What goes wrong:** Migrated C path doesn't handle the `_controlled` / `_control_bool` context correctly, especially for nested `with qbool:` blocks.
**Why it happens:** The controlled context is managed via Python globals (`_controlled`, `_control_bool`, `_list_of_controls`). The C function needs to receive this state explicitly.
**How to avoid:** Pass `controlled` flag and `control_qubit` index as parameters to the C function. The Cython wrapper reads these from the Python globals and passes them down.
**Warning signs:** Controlled operations produce uncontrolled circuits, or vice versa.

### Pitfall 5: CYT-04 nogil with Python Object Access

**What goes wrong:** Using `with nogil:` around code that accesses Python objects (numpy arrays, lists) causes crashes.
**Why it happens:** GIL release allows other threads to mutate Python objects. Cython does NOT allow Python object access inside `with nogil:` blocks (compile-time error for typed objects, but raw pointers can slip through).
**How to avoid:** Extract all data from Python objects BEFORE the `with nogil:` block. Inside the block, only pass C pointers and scalar values. The numpy `.data` pointer or typed memory view `.data` is safe.
**Warning signs:** Cython compilation errors mentioning "Python object" in nogil context, or runtime crashes.

### Pitfall 6: Build System Integration

**What goes wrong:** New C files aren't compiled, causing linker errors.
**Why it happens:** setup.py has a hardcoded `c_sources` list. Each Cython extension links against ALL C sources (not just the ones it uses), so missing a file breaks all extensions.
**How to avoid:** Add each new `.c` file to the `c_sources` list in `setup.py` immediately after creating it. The C test Makefile (tests/c/Makefile) also needs updating for standalone C tests.
**Warning signs:** `undefined reference to ...` linker errors during `pip install -e .`

## Code Examples

### Example 1: Current iadd Pattern (Cython)

```cython
# From qint_arithmetic.pxi
cdef addition_inplace(self, other, int invert=False):
    cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()  # Python call
    cdef bint _controlled = _get_controlled()                                  # Python call
    cdef object _control_bool = _get_control_bool()                           # Python call

    # Populate qubit_array (Cython loops)
    self_offset = 64 - self.bits
    for i in range(self.bits):
        qubit_array[i] = self.qubits[self_offset + i]
    start += self.bits

    # ... (more qubit array setup, control handling)

    seq = QQ_add(result_bits)  # C call for sequence
    arr = qubit_array
    run_instruction(seq, &arr[0], invert, _circuit)  # C call to inject gates
```

### Example 2: Migrated iadd Pattern (C + thin Cython wrapper)

```c
// c_backend/src/hot_path_iadd.c
#include "hot_path_iadd.h"
#include "arithmetic_ops.h"
#include "execution.h"

void hot_path_iadd_qq(
    circuit_t *circ,
    const unsigned int *self_qubits,  // Already extracted, self.bits elements
    int self_bits,
    const unsigned int *other_qubits, // Already extracted, other_bits elements
    int other_bits,
    int invert,
    int controlled,
    unsigned int control_qubit,
    const unsigned int *ancilla_arr,
    int num_ancilla
) {
    int result_bits = (self_bits > other_bits) ? self_bits : other_bits;

    // Build qubit array locally (stack allocated)
    unsigned int qa[256];  // Max possible size
    int pos = 0;

    // Self qubits
    for (int i = 0; i < self_bits; i++) qa[pos++] = self_qubits[i];

    // Other qubits
    for (int i = 0; i < other_bits; i++) qa[pos++] = other_qubits[i];

    sequence_t *seq;
    if (controlled) {
        qa[2 * result_bits] = control_qubit;
        for (int i = 0; i < num_ancilla; i++) qa[2 * result_bits + 1 + i] = ancilla_arr[i];
        seq = cQQ_add(result_bits);
    } else {
        for (int i = 0; i < num_ancilla; i++) qa[pos + i] = ancilla_arr[i];
        seq = QQ_add(result_bits);
    }

    run_instruction(seq, qa, invert, circ);
}
```

```cython
# Thin Cython wrapper in qint_arithmetic.pxi (or the preprocessed file)
cdef addition_inplace(self, other, int invert=False):
    cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
    cdef bint _controlled = _get_controlled()

    # Extract qubit indices (minimal Python interaction)
    cdef unsigned int self_qa[64]
    cdef unsigned int other_qa[64]
    cdef int self_offset = 64 - self.bits
    cdef int i

    for i in range(self.bits):
        self_qa[i] = self.qubits[self_offset + i]

    if type(other) == int:
        # CQ path
        hot_path_iadd_cq(_circuit, self_qa, self.bits, other, invert, ...)
    else:
        cdef int other_offset = 64 - (<qint>other).bits
        for i in range((<qint>other).bits):
            other_qa[i] = (<qint>other).qubits[other_offset + i]
        hot_path_iadd_qq(_circuit, self_qa, self.bits, other_qa, (<qint>other).bits, invert, ...)
```

### Example 3: CYT-04 nogil Integration

```cython
# Where nogil makes sense: around the C hot path call
cdef addition_inplace(self, other, int invert=False):
    # ... fetch state (WITH GIL -- accesses Python objects) ...

    cdef unsigned int self_qa[64]
    # ... populate self_qa from Python objects ...

    # Release GIL for the C-only computation
    with nogil:
        hot_path_iadd_qq(circ, self_qa, self.bits, other_qa, other_bits, invert,
                         controlled, control_qubit, ancilla_qa, num_ancilla)

    return self
```

### Example 4: C-level Unit Test

```c
// tests/c/test_hot_path_iadd.c
#include <assert.h>
#include <stdio.h>
#include "circuit.h"
#include "hot_path_iadd.h"

void test_iadd_qq_basic() {
    circuit_t *circ = init_circuit();
    unsigned int self_qubits[] = {0, 1, 2, 3, 4, 5, 6, 7};  // 8-bit
    unsigned int other_qubits[] = {8, 9, 10, 11, 12, 13, 14, 15};
    unsigned int ancilla[] = {16, 17};  // dummy

    hot_path_iadd_qq(circ, self_qubits, 8, other_qubits, 8,
                     0 /*not inverted*/, 0 /*not controlled*/, 0, ancilla, 2);

    // Verify circuit has gates
    assert(circ->used_layer > 0);
    printf("PASS: test_iadd_qq_basic (layers=%u)\n", circ->used_layer);

    free_circuit(circ);
}

int main() {
    test_iadd_qq_basic();
    return 0;
}
```

### Example 5: Benchmark Before/After Pattern

```python
# Already in tests/benchmarks/test_qint_benchmark.py
# Add before/after comparison test:
class TestHotPathMigration:
    """Before/after benchmarks for Phase 60 hot path migration."""

    def test_iadd_8bit_migrated(self, benchmark, clean_circuit):
        """Benchmark migrated iadd path."""
        a = ql.qint(5, width=8)

        def do_iadd():
            nonlocal a
            a += 3
            return a

        benchmark(do_iadd)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python-level accessor functions for globals | Python function calls from Cython | Phase 11 (QPU state removal) | Introduced accessor overhead |
| Slice-based qubit array population | Explicit Cython loops (CYT-03) | Phase 57 | Eliminated NumPy overhead in loops |
| Dynamic sequence generation for all widths | Hardcoded sequences for widths 1-16 | Phases 58-59 | Eliminated generation overhead for common widths |
| All operations go through run_instruction | (This phase) Hot paths bypass Python layer | Phase 60 | Eliminates boundary crossing overhead |

**Deprecated/outdated:**
- QPU_state global: Removed in Phase 11, replaced with accessor functions
- Slice-based qubit array operations: Replaced with explicit loops in Phase 57

## Likely Hot Path Candidates

Based on Phase 57 baseline benchmarks and architecture analysis:

### Candidate 1: `iadd` (in-place addition) -- 25 us, 40K ops/sec
- **Pattern:** `addition_inplace()` in qint_arithmetic.pxi
- **Boundary crossings:** 3 Python accessor calls + qubit array loop + run_instruction
- **Migration potential:** HIGH -- pure qubit array setup + C call, no Python object creation
- **CYT-04 applicable:** YES -- entire C path can run without GIL

### Candidate 2: `xor` / `ixor` (XOR operations) -- 30 us, 33K ops/sec
- **Pattern:** `__ixor__` / `__xor__` in qint_bitwise.pxi
- **Boundary crossings:** 3 Python accessor calls + qubit array loop + run_instruction
- **Migration potential:** HIGH -- similar to iadd, simple qubit array setup
- **CYT-04 applicable:** YES for ixor (in-place), partial for xor (creates new qint)

### Candidate 3: `add` (out-of-place addition) -- 53 us, 18K ops/sec
- **Pattern:** `__add__` in qint_arithmetic.pxi
- **Boundary crossings:** Same as iadd PLUS qint allocation + dependency tracking
- **Migration potential:** MEDIUM -- the C path portion can be migrated, but qint creation involves Python
- **Note:** `__add__` calls `qint(width=N)` then `^=` then `+=`. Only the `+=` part (addition_inplace) can be fully C-migrated. The qint creation and dependency tracking must stay in Python.

### Alternative Candidate: `eq` (equality comparison) -- 100 us, 10K ops/sec
- Higher absolute time but lower ops/sec
- Uses `CQ_equal_width` C function + qubit reversal loop
- Would be a candidate if profiling shows it in top 3

### Alternative Candidate: `qint.__init__` (object creation) -- implicitly measured in all benchmarks
- Every out-of-place operation creates 1-3 qint objects
- Heavy Python interaction (allocator, numpy, scope stack, dependency tracking)
- Partial migration possible for the qubit allocation + X-gate initialization
- CYT-04 NOT applicable (Python object management throughout)

**Important:** Fresh profiling at phase start is mandatory (locked decision). The phases 57-59 optimizations (Cython typing, hardcoded sequences) may have shifted the hot paths significantly. The above are predictions based on pre-optimization benchmarks.

## Profiling Methodology

### Step 1: Fresh Profiling Build

```bash
QUANTUM_PROFILE=1 pip install -e .
```

### Step 2: Identify Top 3 Hot Paths

```bash
make profile-cprofile  # Quick overview
# Or more detailed:
python3 -c "
import cProfile, pstats, io
pr = cProfile.Profile()
pr.enable()
import quantum_language as ql
c = ql.circuit()
a = ql.qint(12345, width=16)
b = ql.qint(6789, width=16)
# Run representative workload
for _ in range(1000):
    a += b
    a += 42
    c2 = a ^ b
    result = a == b
    result2 = a < b
    c3 = a * b
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(30)
print(s.getvalue())
"
```

### Step 3: Per-Path Benchmark (Before)

```bash
make benchmark  # Captures baseline for all operations
```

### Step 4: After Each Migration

```bash
pip install -e .  # Rebuild with migrated C code
make benchmark    # Compare to baseline
pytest tests/python/ -v  # Verify correctness
```

## Implementation Order

For each hot path (1, 2, 3):

1. **Write C function** (`c_backend/src/hot_path_*.c` + `c_backend/include/hot_path_*.h`)
2. **Write C unit test** (`tests/c/test_hot_path_*.c`)
3. **Add to build** (update `setup.py` c_sources, update `_core.pxd` declarations)
4. **Replace Cython** (modify `.pxi` to call C function instead)
5. **Verify tests** (`pytest tests/python/ -v`)
6. **Benchmark** (`make benchmark`)
7. **Remove old code** (clean up replaced Cython)
8. **Commit** (one commit per path)

## Open Questions

1. **How much did phases 57-59 shift the hot paths?**
   - What we know: Hardcoded sequences (58-59) eliminated sequence generation overhead for widths 1-16. Cython typing (57) reduced accessor overhead.
   - What's unclear: Whether iadd/xor/add are still the top 3, or whether eq/lt/mul have moved up.
   - Recommendation: Fresh profiling is mandatory (locked decision). Be prepared to migrate different paths than the predicted candidates.

2. **Is `run_instruction()` per-gate malloc a significant bottleneck?**
   - What we know: `run_instruction()` calls `malloc(sizeof(gate_t))` and `memcpy` for every gate in the sequence. For an 8-bit QQ_add (58 layers, many gates), this is hundreds of allocations.
   - What's unclear: Whether this is measurable compared to boundary crossing overhead.
   - Recommendation: Do NOT optimize run_instruction internals in this phase. Focus on boundary crossing elimination. If profiling shows run_instruction as significant after migration, flag it for future work.

3. **Should `qint.__init__` be considered a hot path?**
   - What we know: Every out-of-place operation creates 1-3 qint objects. Each involves Python accessors, numpy allocation, scope tracking.
   - What's unclear: Whether the init overhead shows up as a distinct hot path in profiling, or is distributed across callers.
   - Recommendation: Include it as a candidate if profiling data supports it. The C-migratable portion is limited (allocator + X-gate init), so the improvement might be modest.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `src/quantum_language/qint_arithmetic.pxi`, `qint_bitwise.pxi`, `qint_comparison.pxi`
- Direct codebase analysis: `c_backend/src/execution.c` (run_instruction implementation)
- Direct codebase analysis: `c_backend/include/arithmetic_ops.h`, `bitwise_ops.h`, `comparison_ops.h`
- Direct codebase analysis: `src/quantum_language/_core.pyx` (accessor functions, global state)
- Direct codebase analysis: `src/quantum_language/_core.pxd` (C extern declarations)
- Direct codebase analysis: `setup.py` (build configuration)
- Direct codebase analysis: `tests/benchmarks/test_qint_benchmark.py` (benchmark patterns)
- Direct codebase analysis: `.planning/STATE.md` (Phase 57 baseline benchmarks, decisions)

### Secondary (MEDIUM confidence)
- Cython nogil documentation (from training data, verified against Cython 3.x behavior)
- C-to-Python boundary crossing overhead characteristics (established compiler knowledge)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools already established in the project
- Architecture: HIGH -- patterns derived from direct codebase analysis, existing C backend is mature
- Pitfalls: HIGH -- based on actual code structure and known project issues (BUG-CQQ-ARITH pattern)
- Hot path predictions: MEDIUM -- based on pre-optimization benchmarks; fresh profiling may change rankings

**Research date:** 2026-02-06
**Valid until:** 2026-03-06 (stable domain, internal optimization)
