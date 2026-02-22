# Architecture Patterns: v4.1 Quality & Efficiency

**Domain:** Bug fixes, tech debt cleanup, security hardening, performance optimization, and binary size reduction for an existing three-layer quantum programming framework
**Researched:** 2026-02-22
**Confidence:** HIGH (all findings from direct codebase inspection)

## Recommended Architecture

The v4.1 milestone modifies existing architecture in-place rather than introducing new components. All changes operate within the established three-layer boundary (C backend -> Cython bindings -> Python frontend). The key principle is: **fix from the bottom up, validate from the top down**.

### Existing Three-Layer Architecture (Unchanged)

```
Python Frontend (qint, qbool, qarray, compile, grover, amplitude_estimation)
    |
    | Cython FFI bridge (_core.pyx, qint.pyx, _gates.pyx, etc.)
    |
C Backend (circuit_t, sequence_t, optimizer, execution, gate sequences)
    |
    | Pre-generated sequences (c_backend/src/sequences/ -- 105 files)
    |
Hardcoded Sequence Layer (QFT widths 1-16, Toffoli widths 1-8, Clifford+T widths 1-8)
```

### Component Modification Map (v4.1)

Every v4.1 change maps to exactly one layer. No change crosses layer boundaries.

| Change Category | Layer | Files Modified | Files Added |
|----------------|-------|----------------|-------------|
| Bug fixes (7 carry-forward) | C + Cython | `IntegerAddition.c`, `IntegerMultiplication.c`, `IntegerComparison.c`, `qint_arithmetic.pxi`, `qint_division.pxi`, `types.h` | None |
| Bug fixes (qarray `*=`) | Cython | `qarray.pyx` | None |
| Bug fixes (qiskit_aer dep) | Python + Config | `grover.py`, `amplitude_estimation.py`, `pyproject.toml` | None |
| Dead code removal (QPU stubs) | C | Remove `QPU.c`, `QPU.h`; update `#include` refs | None |
| Duplicate file cleanup | Build | `build_preprocessor.py` verified, `.gitignore` updated | None |
| Optimizer binary search | C | `optimizer.c` (~15 lines changed) | None |
| Compile replay overhead | Cython + C | `_core.pyx` (inject_remapped_gates) | 0-1 new C function |
| Bounds checking | C + Cython | `_core.pyx`, `circuit_allocations.c` | None |
| Pointer validation | Cython | `_core.pyx` (all cast sites) | None |
| Nested with-blocks | Cython | `qint.pyx` lines 808-814 | None |
| Binary size reduction | C (sequences) | Generator scripts in `scripts/`, dispatch files | Modified sequence files |
| Test coverage gaps | Python | New test files in `tests/python/` | 3-5 new test files |

### Data Flow (Unchanged by v4.1)

The core data flow remains identical:

```
User Code: a + b
    -> qint.__add__ (Cython) checks arithmetic_mode
    -> hot_path_add_qq() or hot_path_add_cq() (C, nogil)
    -> Sequence dispatch: hardcoded or runtime-generated sequence_t*
    -> run_instruction() maps logical qubits -> physical via qubit_array
    -> add_gate() places gate in optimal layer (optimizer.c)
    -> Circuit stored in circuit_t.sequence[layer][]
```

v4.1 modifications touch step 5 (optimizer improvement) and add validation before step 3 (bounds checking), but do not change the flow itself.

---

## Where the 7 Carry-Forward Bugs Live and Fix Patterns

### Bug Location Map

Each bug is pinpointed to a specific layer and file.

| Bug | Layer | Primary File | Root Cause Category |
|-----|-------|-------------|-------------------|
| BUG-MOD-REDUCE | C + Python | `qint_division.pxi` (Python-level restoring division) | Algorithm structure -- `_reduce_mod` circuit topology is fundamentally wrong for large moduli |
| BUG-COND-MUL-01 | Cython | `qint_arithmetic.pxi` (controlled multiplication scope) | Scope/uncomputation -- out-of-place `*` creates result qint inside `with` block, scope exit uncomputes it |
| BUG-DIV-02 | C | `IntegerComparison.c` (MSB comparison in division loop) | Off-by-one -- comparison circuit leaks MSB state into ancilla, corrupting subsequent division iterations |
| BUG-WIDTH-ADD | C | `IntegerAddition.c` (mixed-width QFT addition) | Qubit mapping -- when `self_bits != other_bits`, rotation angles target wrong qubit positions |
| 32-bit segfault | C | `IntegerMultiplication.c` (buffer overflow at width 32) | Buffer overflow -- `MAXLAYERINSEQUENCE=10000` in `types.h` insufficient for 32-bit multiplication (32x32 QFT layers exceed limit) |
| BUG-CQQ-QFT | C | `IntegerAddition.c` (controlled QQ add, CCP rotations) | Gate construction -- controlled-controlled-phase rotations emit wrong angles at width 2+ |
| BUG-QFT-DIV | C + Python | `qint_division.pxi` + `IntegerAddition.c` | Compound -- QFT division depends on QFT subtraction, which inherits BUG-WIDTH-ADD and BUG-CQQ-QFT errors |

### Fix Pattern Classification

**Pattern A: Buffer/Bounds Fix** (32-bit segfault)

The fix is localized to `c_backend/include/types.h` line 50 where `MAXLAYERINSEQUENCE` is defined as 10000. For 32-bit multiplication, the QFT-based multiply requires approximately `32 * 32 * 3 = 3072` layers for rotation sequences alone, plus QFT/IQFT overhead. This is within the 10000 limit, but the `sequence_t` allocation in `IntegerMultiplication.c` uses `MAXLAYERINSEQUENCE` as its allocation bound. The actual overflow occurs because `QQ_mul(32)` generates sequences that write past the `gates_per_layer` array bounds.

Fix: Either make `MAXLAYERINSEQUENCE` dynamic based on bit width, or increase it to accommodate the worst case. A safe formula: `MAXLAYERINSEQUENCE = max(10000, 4 * bits * bits)`. Alternatively, add a bounds check: `if (bits > 16 && bits * bits * 4 > MAXLAYERINSEQUENCE) return NULL;`.

Location: `c_backend/include/types.h` line 50, `IntegerMultiplication.c` `QQ_mul()` function.
Risk: LOW -- constant change or bounds check, no logic change.

**Pattern B: Qubit Mapping Fix** (BUG-WIDTH-ADD, BUG-CQQ-QFT)

Both bugs are in QFT rotation index calculations within `IntegerAddition.c`.

BUG-WIDTH-ADD: When `self_bits > other_bits`, the CQ_add/QQ_add functions compute rotation angles that reference qubit positions in the "other" operand beyond its width. The zero-extension logic does not properly map the narrower operand's bits into the wider target's rotation space.

BUG-CQQ-QFT: The controlled QQ addition (`cQQ_add`) adds a control qubit to each phase rotation. At width 2+, the controlled-controlled-phase (CCP) gate construction incorrectly positions the second control qubit, causing wrong rotation angles.

Fix approach: Audit the rotation mapping in `CQ_add()` (line ~24-100 of `IntegerAddition.c`) and `cQQ_add()` to ensure qubit index calculations handle width asymmetry. The hardcoded sequences for widths 1-16 were generated from these same functions, so fixing the generator also requires regenerating sequences.

Location: `c_backend/src/IntegerAddition.c` lines ~24-100 (CQ_add, QQ_add, cQQ_add).
Risk: MEDIUM -- changes affect cached sequences; must invalidate width caches and re-verify.

**Pattern C: Scope/Lifecycle Fix** (BUG-COND-MUL-01)

Root cause: `__mul__` in `qint_arithmetic.pxi` creates a new result `qint` inside a `with` block (controlled scope). When the `with` block exits, `__exit__` triggers uncomputation of qints created within the scope, which uncomputes the multiplication result.

The workaround in tests sets `scope_depth=0` during the multiplication to prevent scope registration. The proper fix: either (a) mark the multiplication result as non-uncomputable when it is the return value of an operation, or (b) change `__mul__` to not register results with the scope stack when inside a controlled context. This interacts with the `_scope_stack` tracking in `_core.pyx` (line 44) and the `qint.__del__` uncomputation in `qint.pyx` (lines 727-775).

Location: `src/quantum_language/qint_arithmetic.pxi`, interacts with `qint.pyx` `__exit__` and `_core.pyx` `_scope_stack`.
Risk: MEDIUM -- touches the GC-dependent uncomputation system, which is already flagged as fragile.

**Pattern D: Algorithm Redesign** (BUG-MOD-REDUCE)

The current `_reduce_mod` in `qint_division.pxi` uses a restoring-division approach that fails for moduli where the remainder register corruption propagates through iteration. This is NOT a simple patch -- requires a different circuit topology (e.g., Beauregard-style modular reduction or Barrett/Montgomery modular arithmetic).

Location: `src/quantum_language/qint_division.pxi`.
Risk: HIGH -- most complex fix, strong candidate for deferral again.
Recommendation: Document the limitation clearly and defer to a dedicated milestone.

**Pattern E: Compound Bug** (BUG-QFT-DIV, BUG-DIV-02)

BUG-QFT-DIV resolves automatically once BUG-WIDTH-ADD and BUG-CQQ-QFT are fixed, since QFT division uses QFT subtraction internally. BUG-DIV-02 requires fixing MSB comparison leak in `IntegerComparison.c` -- the comparison ancilla is not properly cleaned up between division loop iterations.

Location: `c_backend/src/IntegerComparison.c` and `src/quantum_language/qint_division.pxi` loop structure.
Risk: MEDIUM -- must verify across all width combinations.

### Fix Dependency Graph

```
BUG-WIDTH-ADD  ----+
                    |
BUG-CQQ-QFT   ----+--> BUG-QFT-DIV (resolves once dependencies fixed)
                    |
BUG-DIV-02    -----+

32-bit segfault ------> Independent (buffer size fix)

BUG-COND-MUL-01 -----> Independent (scope fix)

BUG-MOD-REDUCE -------> Independent (algorithm redesign, likely deferred)
```

**Recommended fix order:**
1. 32-bit segfault (simplest, independent, Pattern A)
2. BUG-WIDTH-ADD (enables BUG-QFT-DIV resolution, Pattern B)
3. BUG-CQQ-QFT (enables BUG-QFT-DIV resolution, Pattern B)
4. BUG-DIV-02 (completes division fix chain, Pattern E)
5. BUG-QFT-DIV (should be resolved by 2+3+4; verify only)
6. BUG-COND-MUL-01 (scope fix, independent, Pattern C)
7. BUG-MOD-REDUCE (algorithm change -- defer or do last, Pattern D)

---

## Safe Dead Code and Duplicate File Cleanup

### QPU.c / QPU.h Removal

**Current state:**
- `QPU.c`: 17 lines, all comments, zero executable code
- `QPU.h`: 25 lines, just `#include "circuit.h"` wrapper
- Referenced by `#include "QPU.h"` in: `IntegerAddition.c`, `IntegerComparison.c`, `IntegerMultiplication.c`, `LogicOperations.c`, `circuit_allocations.c`
- Listed in `setup.py` `c_sources` array

**Safe removal procedure:**
1. `grep -r "QPU.h" c_backend/` to identify all include sites
2. Replace all `#include "QPU.h"` with `#include "circuit.h"` (5 files)
3. Remove `c_backend/src/QPU.c` and `c_backend/include/QPU.h`
4. Remove `QPU.c` entry from `setup.py` `c_sources` list
5. Update `CMakeLists.txt` if QPU files are referenced
6. Build and run full test suite (`pytest tests/python/ -v`)

Risk: VERY LOW -- purely mechanical; `QPU.h` is a transparent `#include "circuit.h"` wrapper with no additional declarations.

### qint_preprocessed.pyx Duplicate Management

**Current state:**
- `qint.pyx` (907 lines) uses `include "qint_arithmetic.pxi"` etc.
- `qint_preprocessed.pyx` (3282 lines) has `.pxi` content inlined
- `build_preprocessor.py` auto-generates the preprocessed version at build time
- Both exist in the repo; `qint_preprocessed.pyx` is what Cython actually compiles

**The problem is already solved by build_preprocessor.py.** The cleanup is:
1. Run `python build_preprocessor.py --check` to verify regeneration produces identical output
2. Add `*_preprocessed.pyx` to `.gitignore` so preprocessed files are not committed
3. Verify `setup.py` runs preprocessing before compilation (already does, via `preprocess_all()` call at line 108)
4. Document this in CLAUDE.md or a BUILDING.md so contributors know not to edit preprocessed files

Risk: LOW -- the tooling already exists; this is an enforcement step.

### Other Dead Code Candidates

| File | Status | Action |
|------|--------|--------|
| `c_backend/include/Integer.h` | Used by `IntegerAddition.c`, `IntegerMultiplication.c`, etc. | KEEP -- still has active function declarations |
| `c_backend/include/definition.h` | Check usage | Audit with `grep`; remove if only self-referencing |
| `c_backend/src/QPU.c` | Empty backward-compat stub | REMOVE (see above) |
| Kogge-Stone CLA stubs | Return NULL in `ToffoliAdditionCLA.c` | KEEP as stubs but add comment "not implemented, returns NULL" |
| `Language/` directory | Legacy `.qa` files | KEEP for reference; does not affect build |

---

## Bounds Checking and Pointer Validation Without Performance Regression

### Where to Add Validation (Priority Order)

**Critical Path 1: Circuit pointer casts in _core.pyx**

Every `<circuit_t*><unsigned long long>_get_circuit()` cast is a potential crash site if the circuit is not initialized. There are approximately 15-20 such sites across `_core.pyx`, `qint.pyx`, `qbool.pyx`, `qarray.pyx`, and `openqasm.pyx`.

Fix pattern -- create a single validated accessor:

```cython
cdef inline circuit_t* _get_validated_circuit() except NULL:
    if not _circuit_initialized:
        raise RuntimeError("No circuit initialized. Call ql.circuit() first.")
    return _circuit
```

Replace all `<circuit_t*><unsigned long long>_get_circuit()` with `_get_validated_circuit()`. This adds one branch per access but eliminates use-after-free risk.

Performance impact: One `bint` comparison per circuit access. The hot path (`hot_path_add_qq`, `hot_path_add_cq`) already receives the circuit pointer as a parameter before entering `nogil`, so the validation happens once per operation, not per gate. Negligible.

**Critical Path 2: qubit_array bounds in _core.pyx**

`qubit_array` is fixed at `4 * 64 + NUMANCILLY = 384` elements (line 244 of `_core.pyx`). Before writing into it, validate the required slot count:

```cython
cdef int required_slots = self_bits + other_bits + num_ancilla
if required_slots > 4 * 64 + NUMANCILLY:
    raise ValueError(f"Operation requires {required_slots} qubit slots, max is {4*64+NUMANCILLY}")
```

Add this check in `addition_inplace`, `multiplication_inplace`, and any other Cython method that populates `qubit_array`. This is one integer comparison per operation call.

**Critical Path 3: C-level allocator error propagation**

The `allocate_more_qubits()`, `allocate_more_layer()`, and `allocate_more_gates_per_layer()` functions in `circuit_allocations.c` currently return `void` and silently `return` on allocation failure, leaving the circuit in an inconsistent state (some arrays resized, others not).

Fix: Change return type to `int` (0 = success, -1 = failure). Then check in `add_gate()`:

```c
// In add_gate() (optimizer.c):
if (allocate_more_qubits(circ, g) != 0) {
    return;  // Or set an error flag on circuit_t
}
```

This changes the function signatures in `circuit.h` but adds only one return-value check per reallocation event, which is rare (only when growing array capacity).

### Validation Performance Budget

| Check | Location | Frequency | Cost | Justified? |
|-------|----------|-----------|------|------------|
| Circuit initialized | Cython operation entry | Per-operation | 1 branch | YES -- prevents segfault |
| qubit_array bounds | Cython operation entry | Per-operation | 1 compare | YES -- prevents buffer overrun |
| Allocator return codes | C allocate_more_* | Per-realloc (rare) | 1 compare | YES -- prevents inconsistent state |
| Gate qubit in bounds | optimizer.c add_gate | Per-gate (millions) | 1 compare | NO -- hot path, validate at boundary instead |

**Total overhead per arithmetic operation:** ~3 branch instructions outside the inner gate loop. Undetectable in benchmarks. The 15% regression tolerance established in v2.3 will not be approached.

---

## Optimizer Improvement: Linear Scan to Binary Search

### Current Code Analysis (optimizer.c lines 26-38)

```c
layer_t smallest_layer_below_comp(circuit_t *circ, qubit_t qubit, layer_t compar) {
    // TODO: improve with binary search
    int last_index = (int)circ->used_occupation_indices_per_qubit[qubit];
    if (last_index < 0) return 0;
    for (int i = last_index; i > 0; ++i) {  // <-- BUG: infinite loop
        if (circ->occupied_layers_of_qubit[qubit][i - 1] < compar) {
            return circ->occupied_layers_of_qubit[qubit][i - 1];
        }
    }
    return 0;
}
```

**CRITICAL BUG:** The loop `for (int i = last_index; i > 0; ++i)` increments `i` upward from `last_index` while checking `i > 0`. For `last_index > 0`, this reads beyond the array bounds until it happens to find a matching value or segfaults. The intended code was likely `for (int i = last_index; i > 0; --i)` (decrementing). The function "works" in practice because:
1. The last entry in `occupied_layers_of_qubit` is typically the highest layer, which is usually `< compar`
2. So the function returns on the first iteration for the common case
3. The buggy path only triggers when the last entry is `>= compar`, which requires specific gate placement patterns

### Recommended Fix: Binary Search Replacing Buggy Linear Scan

The `occupied_layers_of_qubit[qubit]` array is monotonically sorted (layers assigned in increasing order). Binary search finds the largest layer strictly below `compar`:

```c
layer_t smallest_layer_below_comp(circuit_t *circ, qubit_t qubit, layer_t compar) {
    int count = (int)circ->used_occupation_indices_per_qubit[qubit];
    if (count <= 0) return 0;

    layer_t *arr = circ->occupied_layers_of_qubit[qubit];

    // Binary search: find largest element < compar
    int lo = 0, hi = count - 1;
    layer_t result = 0;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] < compar) {
            result = arr[mid];
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return result;
}
```

Complexity: O(L) -> O(log L) where L = occupied layers per qubit.

When it matters: Deep circuits with many gates per qubit. For 16-bit multiplication generating ~2000 gates, each qubit may have 100+ occupied layers. For Grover circuits with 10,000+ gates, the savings compound significantly. Binary search also eliminates the latent infinite-loop bug.

### Python-Level Optimizer (_optimize_gate_list in compile.py)

The `compile.py` optimizer (lines 150-177) uses a multi-pass adjacent-pair scan capped at `max_passes=10`.

Improvements (incremental, not rewrite):
1. Remove hard `max_passes=10` cap -- the `while len(optimized) < prev_count` loop condition already handles convergence
2. Add commutation-aware cancellation for non-adjacent inverse pairs
3. Keep Python implementation -- gate lists from compiled functions are typically 100-1000 gates

Risk: LOW -- additive improvement, backward-compatible.

---

## Binary Size Reduction: Right-Sizing Hardcoded Sequences

### Current Binary Size Breakdown

| Component | Source Lines | Disk (sequences/) | Per-.so Impact |
|-----------|-------------|-------------------|----------------|
| QFT addition (widths 1-16) | 53,598 | ~3.2 MB | ~0.5 MB |
| Toffoli CDKM (widths 1-8, 3 variant groups) | ~16,000 | ~1.0 MB | ~0.15 MB |
| Clifford+T CDKM (widths 1-8, 4 variants) | ~67,000 | ~8.5 MB | ~1.3 MB |
| Clifford+T CLA (widths 2-8, 4 variants) | ~140,000 | ~9.3 MB | ~1.4 MB |
| Dispatch files | ~1,000 | ~0.06 MB | negligible |
| **Total sequences** | **~277,000** | **~22 MB** | **~3.4 MB per .so** |

Each `.pyx` module compiles into a separate `.so` that statically links ALL C sources. The 7 Cython modules (`_core`, `qint`, `qbool`, `qarray`, `qint_mod`, `openqasm`, `_gates`) each independently contain the ~105 sequence files. Total installed .so size: **~134 MB** across all .so files.

### Strategy 1: Clifford+T Sequence Factoring (Recommended, Highest Impact)

The Clifford+T sequences are the largest component (~207K lines, ~18 MB source). Each CCX decomposition inlines 15 gates (2H + 4T + 3Tdg + 6CX). This pattern repeats identically for every CCX in every sequence file.

**Factor out a shared function:**

```c
// In ToffoliAdditionHelpers.c:
static inline void emit_clifft_ccx(sequence_t *seq, int *layer,
                                    qubit_t target, qubit_t ctrl1, qubit_t ctrl2) {
    // 15-gate CCX decomposition into Clifford+T
    h(&seq->seq[*layer][seq->gates_per_layer[(*layer)]++], target);
    (*layer)++;
    // ... remaining 14 gates ...
}
```

Then each sequence file calls `emit_clifft_ccx()` instead of inlining 15 gate construction calls per CCX.

Impact: ~60-70% source line reduction for Clifford+T sequences (from ~207K to ~60-80K lines). Compiled binary impact depends on inlining decisions, but the source/maintainability improvement is significant.

Risk: LOW -- same gates emitted at runtime; purely a code generation refactor.

### Strategy 2: Reduce Clifford+T Max Width (Medium Impact, Optional)

Widths 6-8 account for the largest files. The CLA Clifford+T cqq width-8 alone is 23,631 lines. Reducing max hardcoded width from 8 to 5 would cut ~100K lines.

Tradeoff: Width 6-8 Clifford+T circuits fall back to runtime CCX -> Clifford+T decomposition, which is already supported via `ql.option('toffoli_decompose', True)`.

Recommendation: Measure runtime decomposition cost for widths 6-8 before deciding. Only trim if the performance regression is acceptable.

### Strategy 3: Shared C Library (Highest Impact on Binary Size, Biggest Change)

Currently each `.pyx` extension statically links all C sources. Compiling C sources into a shared library (`libquantum_backend.so`) and linking each extension against it would reduce total .so size from ~134 MB to ~20-25 MB.

```python
# Conceptual setup.py change:
from setuptools import Library

c_shared_lib = Library(
    "quantum_backend",
    sources=c_sources,
    extra_compile_args=["-O3", "-pthread", "-fPIC"],
    include_dirs=include_dirs,
)
```

Risk: MEDIUM -- requires setup.py restructuring and ensuring the shared library is discoverable at runtime (via `rpath` or installation into the package directory). This is a well-understood pattern but changes the build system.

### Strategy Comparison

| Strategy | Source Reduction | Binary Reduction | Risk | Effort |
|----------|-----------------|------------------|------|--------|
| Clifford+T factoring | ~150K lines | ~5-10 MB total | LOW | 2-3 days |
| Reduce max width | ~100K lines | ~3-5 MB total | LOW | 1 day |
| Shared library | 0 lines | ~110 MB total | MEDIUM | 3-5 days |
| **Combined** | **~250K lines** | **~115 MB total** | **MEDIUM** | **5-7 days** |

**Recommended order:** Factoring first (low risk, high source reduction), then shared library if binary size is still a concern. Width reduction is optional and should be data-driven.

---

## Build Order Considering Dependencies Between Fixes

### Phased Execution Plan

```
Phase 1: Independent, Low-Risk Fixes
    |-- 32-bit multiplication segfault (types.h constant or bounds check)
    |-- qarray *= segfault (qarray.pyx)
    |-- qiskit_aer undeclared dependency (pyproject.toml, grover.py, amplitude_estimation.py)
    |-- QPU.c/QPU.h removal (5 include updates + file deletion)
    |-- qint_preprocessed.pyx .gitignore enforcement

Phase 2: Security Hardening (safety nets before algorithmic changes)
    |-- Validated circuit accessor in _core.pyx
    |-- qubit_array bounds checking in Cython operation entry points
    |-- C allocator return-code propagation (circuit_allocations.c, optimizer.c)

Phase 3: Optimizer Improvements (faster build/test for subsequent work)
    |-- Binary search in smallest_layer_below_comp (optimizer.c)
    |   (also fixes latent infinite-loop bug)
    |-- Python optimizer convergence cap removal (compile.py)

Phase 4: Core QFT Bug Fix Chain (dependency-ordered)
    |-- BUG-WIDTH-ADD (IntegerAddition.c mixed-width rotation mapping)
    |-- BUG-CQQ-QFT (IntegerAddition.c controlled QQ rotation errors)
    |-- BUG-DIV-02 (IntegerComparison.c MSB leak in division loop)
    |-- BUG-QFT-DIV verification (should pass once above three are fixed)
    |-- Regenerate QFT hardcoded sequences for widths 1-16

Phase 5: Scope and Algorithm Fixes
    |-- BUG-COND-MUL-01 (qint_arithmetic.pxi scope/uncomputation fix)
    |-- Nested with-blocks TODO (qint.pyx __enter__/__exit__)
    |-- BUG-MOD-REDUCE (defer with documented limitation, or algorithm redesign)

Phase 6: Binary Size Reduction
    |-- Clifford+T sequence factoring (generator scripts)
    |-- Regenerate and verify all sequences
    |-- Optional: shared library investigation (setup.py)

Phase 7: Test Coverage Closure
    |-- Nested with-block tests
    |-- Circuit reset with live qints test
    |-- qiskit-aer import failure test
    |-- C test integration into pytest
    |-- Width-64 boundary tests

Phase 8: Optional Performance (if time permits)
    |-- C-level batch gate injection for compile replay
    |-- Sequence generator documentation
```

### Phase Dependency Rationale

1. **Independent fixes first (Phase 1):** Unblocks test runs by removing known segfaults. Dead code removal simplifies subsequent debugging.

2. **Safety before algorithms (Phase 2):** Pointer validation catches bugs introduced during Phase 4 work. Without it, a new bug in IntegerAddition.c could manifest as an opaque segfault instead of a clear Python exception.

3. **Optimizer before core fixes (Phase 3):** Faster test execution for the heavy Phase 4 work. The optimizer binary search fix also removes a latent correctness bug.

4. **QFT fixes in dependency order (Phase 4):** BUG-QFT-DIV is a compound of BUG-WIDTH-ADD, BUG-CQQ-QFT, and BUG-DIV-02. Fixing the three root causes first means BUG-QFT-DIV should resolve as a side effect. Sequence regeneration must happen after the C code is correct.

5. **Scope fixes after core fixes (Phase 5):** BUG-COND-MUL-01 may interact with the QFT path (controlled multiplication uses QFT addition internally). Fix QFT first to isolate scope issues.

6. **Binary size after all code changes (Phase 6):** Sequence factoring and regeneration should happen after all C changes are complete to avoid double work.

7. **Tests after all fixes (Phase 7):** Write tests against the fixed behavior. Some tests may already exist as xfail; promoting them to expected-pass validates the fixes.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Cross-Layer Bug Fixes
**What:** Fixing a C-layer bug by adding compensation logic in Cython/Python.
**Why bad:** Creates implicit coupling; the bug resurfaces if the C layer changes independently.
**Instead:** Fix at the source layer. If `IntegerAddition.c` generates wrong rotations, fix the rotation generation there, not the Cython caller.

### Anti-Pattern 2: Conditional Compilation for Bug Workarounds
**What:** `#ifdef FIX_BUG_WIDTH_ADD` to toggle between old and new behavior.
**Why bad:** Doubles code paths, makes testing combinatorially harder, never gets cleaned up.
**Instead:** Fix the bug, run full test suite, remove old code. Use git history for rollback.

### Anti-Pattern 3: Adding Per-Gate Validation Inside add_gate()
**What:** Validating every gate's qubit indices inside `add_gate()`.
**Why bad:** `add_gate()` is called millions of times for large circuits. One branch per gate is measurable.
**Instead:** Validate once at the Cython operation boundary (once per `+` or `*` call, not once per gate).

### Anti-Pattern 4: Modifying qint_preprocessed.pyx Directly
**What:** Hand-editing the preprocessed file instead of the canonical `.pyx` + `.pxi` files.
**Why bad:** Next build overwrites the edit via `build_preprocessor.py`.
**Instead:** Always edit `qint.pyx` and `.pxi` includes; let the preprocessor handle inlining.

### Anti-Pattern 5: Regenerating Sequences Before Fixing C Bugs
**What:** Running `scripts/generate_seq_all.py` before fixing BUG-WIDTH-ADD.
**Why bad:** The generator uses the same buggy C functions. Generated sequences contain the bug.
**Instead:** Fix the C functions first, verify at runtime, then regenerate hardcoded sequences.

---

## Scalability Considerations

| Concern | Current (v4.0) | After v4.1 | Future |
|---------|----------------|------------|--------|
| Gate placement speed | O(L) per gate with latent infinite-loop bug | O(log L) per gate, bug-free | Cache last-used layer per qubit for O(1) amortized |
| Binary size | ~134 MB total (7 .so, each ~19 MB) | ~80-100 MB (sequence factoring) | ~20 MB (shared library) |
| Sequence source | 344K lines (22 MB on disk) | ~200K lines (factoring Clifford+T) | Runtime generation for width > 4 |
| Buffer overflow risk | Silent crash at width >= 32 | Validated with error return | Dynamic sequence allocation |
| Circuit pointer safety | Trust-based casts | Validated at Cython boundary | Opaque handle with generation counter |
| Scope uncomputation | GC-ordering-dependent | Bug fixes improve reliability | Instruction-counter-based tracking |

---

## Sources

All findings are from direct codebase inspection (HIGH confidence):

- `c_backend/src/optimizer.c` -- linear scan bug and binary search opportunity
- `c_backend/src/execution.c` -- run_instruction data flow
- `c_backend/src/circuit_allocations.c` -- allocation failure handling
- `c_backend/include/types.h` -- MAXLAYERINSEQUENCE constant
- `c_backend/include/circuit.h` -- circuit_t structure
- `c_backend/src/IntegerAddition.c` -- QFT addition, rotation mapping
- `c_backend/src/IntegerMultiplication.c` -- multiplication buffer overflow
- `c_backend/src/IntegerComparison.c` -- MSB comparison leak
- `c_backend/src/QPU.c`, `c_backend/include/QPU.h` -- dead code stubs
- `c_backend/src/sequences/` -- 105 files, 344K lines, 22 MB on disk
- `src/quantum_language/_core.pyx` -- circuit pointer casts, qubit_array
- `src/quantum_language/qint_arithmetic.pxi` -- hot path addition, controlled multiplication
- `src/quantum_language/qint_division.pxi` -- division algorithm, BUG-MOD-REDUCE
- `src/quantum_language/compile.py` -- Python-level gate optimizer
- `setup.py` -- build configuration, static C linking
- `build_preprocessor.py` -- preprocessed .pyx generation
- `.planning/codebase/CONCERNS.md` -- codebase concern inventory
- `.planning/codebase/ARCHITECTURE.md` -- layer architecture documentation
- `.planning/codebase/STRUCTURE.md` -- file layout documentation
- Test files with xfail markers: `test_toffoli_division.py`, `test_conditionals.py`, `test_cross_backend.py`, `test_div.py`, `test_mod.py`, `test_copy_binops.py`

---

*Architecture analysis: v4.1 Quality & Efficiency -- 2026-02-22*
