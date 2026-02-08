# Phase 61: Memory Optimization - Research

**Researched:** 2026-02-08
**Domain:** C memory allocation optimization, memray profiling, arena allocators
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Profiling scope
- Use **memray** for memory profiling (already in Phase 55 infrastructure)
- Profile **both** targeted hot paths (8-bit add/mul/xor) AND end-to-end circuit generation
- Profile at **three widths**: 8-bit, 16-bit, and 32-bit to reveal scaling behavior
- 8-bit = common case, 16-bit = largest hardcoded, 32-bit = dynamic generation path
- **Save baseline + optimized** profiling snapshots as persistent artifacts for comparison

#### Pooling strategy
- **Single-threaded only** -- no locking overhead, circuit generation is currently single-threaded
- **Dynamic growth** -- pool grows as needed with no artificial cap, overflow not a concern
- **Reset per call** -- pool is cleared after each operation completes for simpler lifetime management

#### Optimization targets
- Priority: **highest impact first** -- let profiling data determine which malloc sites to optimize
- **Include sequence_t allocation path** alongside gate_t in optimization scope
- **gate_t struct layout changes acceptable** if they help -- no need to preserve current layout
- No specific known pain points -- let profiling discover the bottlenecks without preconceptions
- If profiling shows malloc is NOT a significant bottleneck (<5% of time): **still take easy wins** (e.g., stack allocation for small sequences) rather than skipping entirely

#### Success thresholds
- **10% benefit means 10% faster throughput** -- operations per second improvement, not just allocation count
- Optimize for **both throughput AND peak memory** -- especially important for large circuits (16-bit, 32-bit)
- Compare final benchmarks against **Phase 60 baseline** (post hot-path migration) to show incremental improvement

### Claude's Discretion
- Pool type selection (arena vs free-list) based on profiling evidence
- Specific malloc sites to optimize -- driven by profiling data
- Whether to use stack allocation, pre-allocation, or pooling for each bottleneck
- Exact profiling scripts and memray configuration
- Number of plans needed based on what profiling reveals

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Summary

This research investigates memory allocation patterns in the quantum circuit generation C backend to identify optimization opportunities for Phase 61. The investigation uncovered a **critical memory leak** in `run_instruction()` and `reverse_circuit_range()` that causes every gate processed to leak ~40 bytes. Beyond the leak, there are three distinct categories of allocation overhead: (1) per-gate malloc in the gate injection path, (2) per-gate temporary allocation in `colliding_gates()`, and (3) massive upfront sequence allocations for multiplication.

The recommended approach is:
1. **Profile first** with memray to quantify the actual memory impact at 8/16/32-bit widths
2. **Fix the memory leak** in `run_instruction()` and `reverse_circuit_range()` -- this is the highest-impact win and may be achieved by eliminating the malloc entirely (use stack allocation)
3. **Eliminate the per-gate malloc** by using stack-allocated `gate_t` in `run_instruction()`
4. **Eliminate per-gate `colliding_gates()` allocation** by passing a stack-allocated array
5. **If profiling warrants it**, implement an arena allocator for remaining dynamic allocation paths

**Primary recommendation:** The `run_instruction()` per-gate malloc is both a memory leak AND a throughput bottleneck. Replacing it with a stack-allocated `gate_t` is a zero-cost fix that eliminates both problems simultaneously.

## Critical Finding: Memory Leak in Gate Injection Path

### The Leak (execution.c lines 26-27)

In `run_instruction()`, for **every gate** in a sequence:

```c
gate_t *g = malloc(sizeof(gate_t));      // line 26 -- allocates ~40 bytes
memcpy(g, &res->seq[layer][gate], sizeof(gate_t));  // line 27 -- copies gate data
// ... remaps qubits ...
add_gate(circ, g);                        // passes pointer to add_gate
// g is NEVER FREED
```

Inside `add_gate()` -> `append_gate()` (optimizer.c line 126):
```c
memcpy(&circ->sequence[min_possible_layer][pos], g, sizeof(gate_t));
```

The gate data is copied into the circuit's pre-allocated storage. The original `malloc`'d `g` pointer is never freed. This is a **memory leak of sizeof(gate_t) per gate**.

### The Same Leak in reverse_circuit_range() (execution.c lines 74-101)

```c
gate_t *g = malloc(sizeof(gate_t));  // line 74 -- another per-gate leak
// ... copies and inverts gate ...
add_gate(circ, g);                   // g is never freed
```

### Quantified Impact

- **gate_t size:** ~40-48 bytes (2 x uint32 Control + pointer + uint32 NumControls + enum Gate + double GateValue + uint32 Target + uint32 NumBasisGates)
- **8-bit QQ_add:** 38 layers x ~1 gate/layer = ~38 leaked gate_t allocations = ~1.5 KB per add
- **16-bit QQ_add:** 78 layers x ~1-2 gates/layer = ~120 leaked allocations = ~5 KB per add
- **8-bit QQ_mul:** ~1000+ gates = ~40 KB per multiplication
- **Cumulative in benchmark loop:** 100 iterations of 8-bit mul = ~4 MB leaked

### The Fix

Replace `malloc` + never-freed pointer with stack-allocated `gate_t`:

```c
// BEFORE (leaks):
gate_t *g = malloc(sizeof(gate_t));
memcpy(g, &res->seq[layer][gate], sizeof(gate_t));
// ... remap qubits on g ...
add_gate(circ, g);

// AFTER (zero allocation):
gate_t g;
memcpy(&g, &res->seq[layer][gate], sizeof(gate_t));
// ... remap qubits on &g ...
add_gate(circ, &g);
```

This requires `add_gate()` to accept `gate_t*` pointing to stack memory, which it already does -- `append_gate()` copies the data via `memcpy`, so the source pointer lifetime does not matter.

## Allocation Site Inventory

### Site 1: run_instruction() per-gate malloc [CRITICAL]
- **File:** `c_backend/src/execution.c:26`
- **Pattern:** `malloc(sizeof(gate_t))` per gate, never freed
- **Frequency:** Called once per gate in every sequence execution
- **Impact:** Memory leak + allocation overhead
- **Fix:** Stack allocation (zero cost)

### Site 2: reverse_circuit_range() per-gate malloc [CRITICAL]
- **File:** `c_backend/src/execution.c:74`
- **Pattern:** Same as Site 1 -- `malloc(sizeof(gate_t))` per gate, never freed
- **Frequency:** Called during uncomputation
- **Impact:** Memory leak + allocation overhead
- **Fix:** Stack allocation (zero cost)

### Site 3: colliding_gates() per-gate-add malloc [MODERATE]
- **File:** `c_backend/src/optimizer.c:138`
- **Pattern:** `malloc(3 * sizeof(gate_t*))` -- allocates 24 bytes for every `add_gate` call
- **Frequency:** Called once per gate added to circuit
- **Impact:** Allocation overhead (properly freed, no leak)
- **Fix:** Stack-allocate the array: `gate_t *coll[3] = {NULL, NULL, NULL};`

### Site 4: Sequence creation allocations [LOW -- cached]
- **Files:** `IntegerAddition.c`, `IntegerMultiplication.c`, `LogicOperations.c`
- **Pattern:** `malloc(sizeof(sequence_t))` + `calloc(layers, sizeof(gate_t*))` + per-layer `calloc(gates, sizeof(gate_t))`
- **Frequency:** Once per unique width (cached after first call for QQ/cQQ variants)
- **Impact:** One-time cost, amortized across all uses. CQ/cCQ variants also cached but require angle injection.
- **Note:** Multiplication uses `MAXLAYERINSEQUENCE = 10000` layers, each with `10 * bits` gate slots. For 8-bit: 10000 * 80 * 40 bytes = **~30 MB** per cached mul sequence. This is wasteful but a one-time cost.

### Site 5: Non-cached sequence creation (Q_not, Q_xor, etc.) [MODERATE]
- **Files:** `LogicOperations.c` functions `Q_not()`, `Q_xor()`, `cQ_not()`, `cQ_xor()`, `Q_and()`, `Q_or()`, etc.
- **Pattern:** Fresh `malloc`/`calloc` per call, caller responsible for freeing
- **Frequency:** Called from hot_path_xor (CQ path calls `Q_not(1)` per set bit)
- **Impact:** Small sequences (1-3 layers), low allocation cost, but NOT cached
- **Fix:** These could be cached or stack-allocated for small widths

### Site 6: Circuit infrastructure allocations [LOW]
- **File:** `c_backend/src/circuit_allocations.c`
- **Pattern:** Block allocation with `realloc` growth (LAYER_BLOCK=128, QUBIT_BLOCK=128, GATES_PER_LAYER_BLOCK=32)
- **Frequency:** Only when circuit grows beyond current capacity
- **Impact:** Amortized O(1) per gate, good growth strategy already in place

## Architecture Patterns

### Pattern 1: Stack Allocation for Temporary Gates (Recommended)
**What:** Replace `malloc(sizeof(gate_t))` with stack-allocated `gate_t` in `run_instruction()` and `reverse_circuit_range()`
**When to use:** When the allocated object has function-local lifetime and is copied before the function returns
**Why:** Zero allocation overhead, fixes the memory leak, no API changes needed

```c
// In run_instruction():
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ) {
    if (res == NULL) return;
    int direction = (invert) ? -1 : 1;

    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t g;  // Stack allocated -- no malloc, no leak
            memcpy(&g, &res->seq[layer][gate], sizeof(gate_t));
            g.Target = qubit_array[g.Target];
            // ... remap controls ...
            g.GateValue *= pow(-1, invert);
            add_gate(circ, &g);
        }
    }
}
```

### Pattern 2: Stack Array for colliding_gates (Recommended)
**What:** Replace `malloc(3 * sizeof(gate_t*))` with stack array in `colliding_gates()`
**When to use:** When the allocation size is fixed and small

```c
// Change colliding_gates signature to accept caller-provided array:
void colliding_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer,
                     int *gate_index, gate_t **coll) {
    coll[0] = NULL; coll[1] = NULL; coll[2] = NULL;
    // ... rest of logic unchanged ...
}

// In add_gate:
gate_t *coll[3];  // Stack allocated
colliding_gates(circ, g, min_possible_layer, gate_index, coll);
// No free(coll) needed
```

### Pattern 3: Arena Allocator for Bulk Allocations (Conditional)
**What:** Pre-allocate a memory region, bump-allocate from it, reset after operation completes
**When to use:** If profiling shows remaining malloc sites are significant bottlenecks after Patterns 1-2
**Architecture:**

```c
typedef struct {
    char *buf;          // Pre-allocated memory region
    size_t capacity;    // Total capacity in bytes
    size_t offset;      // Current allocation offset
} arena_t;

void *arena_alloc(arena_t *a, size_t size) {
    // Align to 8 bytes
    size_t aligned = (size + 7) & ~7;
    if (a->offset + aligned > a->capacity) {
        // Grow: double capacity or add new block
        size_t new_cap = a->capacity * 2;
        if (new_cap < a->offset + aligned) new_cap = a->offset + aligned;
        char *new_buf = realloc(a->buf, new_cap);
        if (!new_buf) return NULL;
        a->buf = new_buf;
        a->capacity = new_cap;
    }
    void *ptr = a->buf + a->offset;
    a->offset += aligned;
    return ptr;
}

void arena_reset(arena_t *a) {
    a->offset = 0;  // Reset without freeing -- reuse buffer
}
```

**Key properties matching user decisions:**
- Single-threaded: no locking needed
- Dynamic growth: `realloc` when capacity exceeded
- Reset per call: `arena_reset()` at operation boundary

### Anti-Patterns to Avoid
- **Pooling gate_t when stack allocation works:** The temporary gates in run_instruction() have function-local lifetime. An arena or free-list is overengineering when a stack variable suffices.
- **Changing add_gate() to take ownership of gate_t*:** The current copy-in design (`memcpy` into circuit storage) is correct. Ownership transfer would complicate the API for no benefit.
- **Caching CQ_mul/cCQ_mul sequences:** These are value-dependent (classical value changes angles), so caching requires value-keyed lookup. Not worth the complexity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Memory profiling | Custom malloc wrappers | memray --native | Tracks all allocators, flame graphs, leak detection |
| Performance benchmarking | Custom timing loops | pytest-benchmark | Statistical rigor, comparison support |
| Throughput testing | time.perf_counter | pytest-benchmark pedantic mode | Handles warmup, outlier removal |
| Arena allocator (if needed) | Complex multi-block system | Simple bump allocator | Single-threaded reset-per-call needs only offset tracking |

**Key insight:** The biggest wins in this phase come from *eliminating* allocations (stack allocation), not from making allocations faster (pooling). Profiling should confirm this before adding any allocator infrastructure.

## Common Pitfalls

### Pitfall 1: Optimizing Without Profiling First
**What goes wrong:** Implementing an arena allocator for paths that turn out not to be bottlenecks
**Why it happens:** Assumption that malloc is slow without measurement
**How to avoid:** Run memray at 8/16/32-bit widths FIRST, save baseline artifacts, then target the actual hotspots
**Warning signs:** Spending time on allocator infrastructure before having profiling data

### Pitfall 2: Missing the Memory Leak
**What goes wrong:** Profiling shows high memory usage but developer optimizes the wrong sites
**Why it happens:** The leak in run_instruction() is subtle -- gate_t* is passed to add_gate which copies it, but the original pointer is never freed
**How to avoid:** Fix the leak FIRST (stack allocation), then re-profile to see remaining allocation patterns
**Warning signs:** Peak memory grows linearly with number of operations even when circuit reuse is expected

### Pitfall 3: Breaking add_gate API Contract
**What goes wrong:** Changing add_gate() to accept stack-allocated gate_t causes issues with n-controlled gates that have malloc'd large_control
**Why it happens:** gate_t.large_control is a heap pointer that gets memcpy'd into circuit storage but the pointer itself is shallow-copied
**How to avoid:** For gates with large_control (NumControls > 2), the large_control pointer in the circuit's copy still points to the original sequence's data. This is already the existing behavior -- the circuit stores pointers into sequence data. Just ensure sequences outlive the circuit.
**Warning signs:** Segfaults when accessing control qubits of n-controlled gates after sequence is freed

### Pitfall 4: memray on macOS ARM64
**What goes wrong:** memray --native may have issues on Apple Silicon
**Why it happens:** Platform-specific memory tracking APIs
**How to avoid:** Test memray early in Phase 61; if --native doesn't work, use without --native (still captures Python-level malloc calls through C extensions)
**Warning signs:** memray fails to produce flame graphs or shows incomplete stacks

### Pitfall 5: Multiplication Sequence Over-Allocation
**What goes wrong:** MAXLAYERINSEQUENCE (10000) layers with 10*bits gate slots each wastes ~30MB per 8-bit multiplication sequence
**Why it happens:** Static overestimate of layer count to avoid runtime growth
**How to avoid:** Profile first to confirm this is worth fixing. The allocation is one-time (cached), so it only matters for peak memory, not throughput.
**Warning signs:** memray shows large upfront allocation in QQ_mul/cQQ_mul

## Code Examples

### Example 1: Fixed run_instruction() (Stack Allocation)
```c
// Source: c_backend/src/execution.c -- proposed fix
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ) {
    if (res == NULL) return;
    int direction = (invert) ? -1 : 1;

    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t g;  // STACK allocated -- fixes leak AND removes malloc overhead
            memcpy(&g, &res->seq[layer][gate], sizeof(gate_t));
            g.Target = qubit_array[g.Target];

            if (g.NumControls > 2 && res->seq[layer][gate].large_control != NULL) {
                g.large_control = malloc(g.NumControls * sizeof(qubit_t));
                if (g.large_control != NULL) {
                    for (int i = 0; i < (int)g.NumControls; ++i) {
                        g.large_control[i] = qubit_array[res->seq[layer][gate].large_control[i]];
                    }
                    g.Control[0] = g.large_control[0];
                    g.Control[1] = g.large_control[1];
                }
            } else {
                for (int i = 0; i < (int)g.NumControls && i < MAXCONTROLS; ++i) {
                    g.Control[i] = qubit_array[g.Control[i]];
                }
            }
            g.GateValue *= pow(-1, invert);
            add_gate(circ, &g);
        }
    }
}
```

### Example 2: Fixed colliding_gates() (Caller-Provided Array)
```c
// Source: c_backend/src/optimizer.c -- proposed fix
// Change from: gate_t **colliding_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int *gate_index)
// Change to: void colliding_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int *gate_index, gate_t **coll)

// In add_gate():
gate_t *coll[3];
colliding_gates(circ, g, min_possible_layer, gate_index, coll);
// ... use coll ...
// No free needed -- stack allocated
```

### Example 3: memray Profiling Script
```python
#!/usr/bin/env python3
"""Phase 61 memory profiling script.

Usage:
    memray run --native -o memray_8bit.bin -- python scripts/profile_memory.py 8
    memray run --native -o memray_16bit.bin -- python scripts/profile_memory.py 16
    memray run --native -o memray_32bit.bin -- python scripts/profile_memory.py 32

Then:
    memray flamegraph memray_8bit.bin -o memray_8bit.html
    memray stats memray_8bit.bin
"""
import sys
import quantum_language as ql

width = int(sys.argv[1]) if len(sys.argv) > 1 else 8
iterations = 100

# --- Addition hot path ---
c = ql.circuit()
a = ql.qint(1, width=width)
b = ql.qint(1, width=width)
for _ in range(iterations):
    a += b

# --- Multiplication hot path ---
c = ql.circuit()
a = ql.qint(1, width=width)
b = ql.qint(1, width=width)
for _ in range(iterations):
    r = a * b

# --- XOR hot path ---
c = ql.circuit()
a = ql.qint(1, width=width)
b = ql.qint(1, width=width)
for _ in range(iterations):
    a ^= b
```

## Data Structures Summary

### gate_t (types.h, ~40-48 bytes)
```c
typedef struct {
    qubit_t Control[MAXCONTROLS];  // 2 x uint32 = 8 bytes
    qubit_t *large_control;        // pointer = 8 bytes
    num_t NumControls;             // uint32 = 4 bytes
    Standardgate_t Gate;           // enum (int) = 4 bytes
    double GateValue;              // double = 8 bytes
    qubit_t Target;                // uint32 = 4 bytes
    num_t NumBasisGates;           // uint32 = 4 bytes
} gate_t;                          // Total: 40 bytes + possible padding
```

### sequence_t (types.h, ~24 bytes header)
```c
typedef struct {
    gate_t **seq;              // pointer to array of layers = 8 bytes
    num_t num_layer;           // uint32 = 4 bytes
    num_t used_layer;          // uint32 = 4 bytes
    num_t *gates_per_layer;    // pointer to per-layer gate counts = 8 bytes
} sequence_t;                  // Total: 24 bytes header + layer data
```

### Gate Count Estimates by Operation and Width

| Operation | 8-bit gates | 16-bit gates | 32-bit gates |
|-----------|-------------|--------------|--------------|
| QQ_add | ~38 | ~78 | ~158 |
| cQQ_add | ~200 | ~800 | ~3200 |
| CQ_add | ~38 | ~78 | ~158 |
| Q_xor | 8 | 16 | 32 |
| QQ_mul | ~1000+ | ~4000+ | ~16000+ |

For leaked allocations at 40 bytes/gate, 100 iterations:
- 8-bit iadd: 38 * 100 * 40 = ~150 KB leaked
- 8-bit mul: 1000 * 100 * 40 = ~4 MB leaked
- 16-bit iadd: 78 * 100 * 40 = ~312 KB leaked

## Phase 60 Baseline (Post Hot-Path Migration)

These are the throughput baselines to compare against:

| Operation | Mean (us) | Post-Phase 60 |
|-----------|-----------|---------------|
| ixor_8bit | 2.5 | -24.2% from Phase 60 baseline |
| ixor_quantum_8bit | 4.4 | -30.2% |
| iadd_8bit | 15.0 | -59.7% |
| isub_8bit | 16.5 | -47.1% |
| iadd_quantum_8bit | 44.0 | -29.5% |
| isub_quantum_8bit | 37.3 | -39.5% |
| iadd_16bit | 35.2 | -27.1% |
| add_8bit | 31.2 | -47.7% |
| mul_8bit | 201.5 | -14.7% |

## Existing Infrastructure

### Profiling Tools (Phase 55)
- **memray**: Installed in `[profiling]` optional dependency, Makefile target `profile-memory` exists
- **pytest-benchmark**: Tests in `tests/benchmarks/test_qint_benchmark.py` with pedantic mode
- **cProfile**: Makefile target `profile-cprofile`
- **py-spy**: Makefile target `profile-native`

### Benchmark Fixtures
- `tests/benchmarks/conftest.py`: `clean_circuit`, `qint_pair_8bit`, `qint_pair_16bit`, `qint_width` (parametrized 4/8/16/32)
- `tests/benchmarks/test_qint_benchmark.py`: Comprehensive benchmark suite including hot path baselines

### Build System
- `setup.py` includes all C source files
- `QUANTUM_PROFILE=1` enables Cython profiling build
- Hot path C files (`hot_path_add.c`, `hot_path_mul.c`, `hot_path_xor.c`) already in build

## Recommended Plan Structure

Based on this research, the phase should have **2-3 plans**:

### Plan 01: Profile and Establish Baseline
- Run memray at 8/16/32-bit widths (add, mul, xor operations)
- Save profiling artifacts (memray .bin files + flame graphs)
- Document allocation hotspots with quantified data
- Identify which of the 6 allocation sites matter most

### Plan 02: Fix Memory Leaks and Eliminate Per-Gate Allocations
- Fix run_instruction() memory leak (stack allocation)
- Fix reverse_circuit_range() memory leak (stack allocation)
- Eliminate colliding_gates() per-gate malloc (stack array)
- Re-run benchmarks and memray to measure improvement
- Save post-optimization profiling artifacts

### Plan 03 (conditional): Arena/Further Optimization
- Only if Plan 02's profiling shows remaining significant allocation bottlenecks
- Implement arena allocator for any remaining hot-allocation paths
- Address multiplication sequence over-allocation if peak memory is a concern
- Final benchmark comparison against Phase 60 baseline

## Open Questions

1. **Exact gate_t size with compiler padding**
   - What we know: Fields sum to 40 bytes, but compiler may add padding
   - What's unclear: Whether the struct has 40 or 48 bytes on the target platform
   - Recommendation: Check with `sizeof(gate_t)` in profiling script or C test

2. **n-controlled gate large_control lifetime**
   - What we know: When run_instruction processes gates with NumControls > 2, it mallocs large_control for the remapped copy. This is copied into circuit storage via memcpy (shallow copy).
   - What's unclear: Whether the circuit's shallow-copied large_control pointer remains valid after sequences are freed
   - Recommendation: Verify in C unit tests that n-controlled gates work after sequence cache is evicted (if ever)

3. **Impact of pow(-1, invert) call per gate**
   - What we know: `pow(-1, invert)` is called per gate in run_instruction -- this is a floating-point math call for a value that is always 1.0 or -1.0
   - What's unclear: Whether the compiler optimizes this away
   - Recommendation: Replace with `(invert ? -1.0 : 1.0)` as a micro-optimization

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** -- Direct reading of all relevant C source files:
  - `c_backend/src/execution.c` (run_instruction, reverse_circuit_range)
  - `c_backend/src/optimizer.c` (add_gate, colliding_gates, append_gate)
  - `c_backend/src/circuit_allocations.c` (init_circuit, allocation growth)
  - `c_backend/include/types.h` (gate_t, sequence_t definitions)
  - `c_backend/src/IntegerAddition.c` (sequence creation patterns)
  - `c_backend/src/IntegerMultiplication.c` (multiplication allocation patterns)
  - `c_backend/src/LogicOperations.c` (xor/and/or sequence creation)
  - `c_backend/src/hot_path_add.c`, `hot_path_mul.c`, `hot_path_xor.c`
- **Phase 55 research** -- `.planning/phases/55-profiling-infrastructure/55-RESEARCH.md`
- **Phase 60 verification** -- `.planning/phases/60-c-hot-path-migration/60-VERIFICATION.md`
- **Phase 60 baseline data** -- `.planning/phases/60-c-hot-path-migration/60-01-SUMMARY.md`

### Secondary (MEDIUM confidence)
- [memray GitHub](https://github.com/bloomberg/memray) -- Native C extension profiling with --native flag
- [memray run documentation](https://bloomberg.github.io/memray/run.html) -- Run subcommand options
- [Arena allocator pattern](https://www.rfleury.com/p/untangling-lifetimes-the-arena-allocator) -- Bump allocation with reset
- [Arena tips and tricks](https://nullprogram.com/blog/2023/09/27/) -- Practical implementation guidance

### Tertiary (LOW confidence)
- [memray discussion on internals](https://github.com/bloomberg/memray/discussions/225) -- How PLT hooking works for malloc interception

## Metadata

**Confidence breakdown:**
- Memory leak finding: HIGH -- Direct code reading confirms malloc without free
- Stack allocation fix: HIGH -- add_gate copies via memcpy, so source pointer lifetime is irrelevant
- Allocation site inventory: HIGH -- Comprehensive grep + manual analysis of all C source files
- Gate count estimates: MEDIUM -- Based on formula analysis, not runtime measurement
- Arena pattern recommendation: MEDIUM -- Conditional on profiling results

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- codebase-specific, stable domain)
