# Phase 45: Data Extraction Bridge - Research

**Researched:** 2026-02-03
**Domain:** C-to-Python circuit data extraction via Cython, qubit index compaction
**Confidence:** HIGH

## Summary

This phase bridges the C backend circuit representation (`circuit_t` with nested `gate_t` arrays organized by layer) into a Python dictionary that downstream renderers consume. The established pattern in this codebase is a single C function that serializes the full circuit into a flat structure, with Cython converting it to a Python dict in one boundary crossing. This is exactly how `circuit_to_qasm_string()` works (in `circuit_output.c`) and how `openqasm.pyx` wraps it.

The second requirement -- qubit index compaction -- eliminates unused qubit rows by building a sparse-to-dense index map. The C backend uses qubit indices up to `used_qubits` (which can be 8000+ due to `MAXQUBITS`), but many indices may be unused. The circuit already tracks usage via `used_occupation_indices_per_qubit[qubit]` (nonzero means used). Compaction scans this array once, assigns dense row indices (0, 1, 2, ...) only to used qubits, and remaps all gate target/control references in the output.

**Primary recommendation:** Add a new C function `circuit_to_draw_data()` in `circuit_output.c` that returns a heap-allocated `draw_data_t` struct with flat arrays. Add the Cython binding as a `draw_data()` method on the `circuit` class in `_core.pyx`. Perform qubit compaction in the C function (single pass to build remap table, then apply during gate serialization).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | (already in project) | C-to-Python bridge | Used throughout codebase for all C bindings |
| C stdlib (malloc/free) | N/A | Memory allocation for draw_data_t | Same pattern as circuit_to_qasm_string() |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (already in project) | Integration testing | Verify draw_data() returns correct dict |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flat C struct + Cython | JSON string from C | Adds JSON dependency to C, string parsing overhead; Cython struct-to-dict is faster and type-safe |
| Single C extraction function | Multiple Cython per-gate accessors | Thousands of C-Python boundary crossings for large circuits; single extraction crosses once |
| C-side compaction | Python-side compaction | Both viable, but C-side avoids creating large temporary Python data with sparse indices |

## Architecture Patterns

### Recommended Project Structure
```
c_backend/
  include/
    circuit_output.h   # Add draw_data_t struct and function declarations
  src/
    circuit_output.c   # Add circuit_to_draw_data() and free_draw_data() implementations

src/quantum_language/
    _core.pxd          # Add extern declarations for draw_data_t, circuit_to_draw_data, free_draw_data
    _core.pyx          # Add draw_data() method to circuit class
```

No new .pyx files needed. No new C source files. This follows the existing pattern where `circuit_output.c` holds all circuit serialization functions and `_core.pyx` holds the `circuit` class methods.

### Pattern 1: Flat C Struct with Parallel Arrays
**What:** Instead of returning an array of structs (one per gate), return a struct of parallel arrays (one array per field). Each array has `num_gates` elements, indexed in lockstep.
**When to use:** When Cython needs to convert C data to Python lists/dicts efficiently.
**Example:**
```c
// In circuit_output.h
typedef struct {
    unsigned int num_layers;
    unsigned int num_qubits;     // Dense count (after compaction)
    unsigned int num_gates;
    // Parallel arrays -- one entry per gate, indexed 0..num_gates-1
    unsigned int *gate_layer;     // Layer index for this gate
    unsigned int *gate_target;    // Target qubit (COMPACTED index)
    unsigned int *gate_type;      // Standardgate_t cast to unsigned int
    double       *gate_angle;     // GateValue (meaningful for P, Rx, Ry, Rz)
    unsigned int *gate_num_ctrl;  // Number of controls for this gate
    // Control qubits stored as flattened array with offsets
    unsigned int *ctrl_qubits;    // All control qubit indices concatenated (COMPACTED)
    unsigned int *ctrl_offsets;   // ctrl_qubits[ctrl_offsets[i]..+gate_num_ctrl[i]]
} draw_data_t;

draw_data_t *circuit_to_draw_data(circuit_t *circ);
void free_draw_data(draw_data_t *data);
```

**Why flat arrays:** Cython iterates flat C arrays efficiently in a single loop. No per-element struct-to-dict conversion needed.

### Pattern 2: Qubit Index Compaction via Remap Table
**What:** Build a `remap[sparse_index] = dense_index` array in one pass over `used_occupation_indices_per_qubit`, then apply it to all target/control indices during gate serialization.
**When to use:** When circuit has sparse qubit usage (e.g., qubits 0, 1, 62, 63 used out of 64 allocated).
**Example:**
```c
// Build remap table: sparse C index -> dense row index
int *remap = calloc(circ->used_qubits + 1, sizeof(int));
int dense_count = 0;
for (int q = 0; q <= circ->used_qubits; q++) {
    if (circ->used_occupation_indices_per_qubit[q] != 0) {
        remap[q] = dense_count++;
    } else {
        remap[q] = -1;  // Unused qubit
    }
}
// dense_count is now the total number of active qubit rows
// When serializing gates, use remap[gate->Target] instead of gate->Target
```

### Pattern 3: Cython draw_data() Method (Following openqasm.pyx Pattern)
**What:** A method on the `circuit` class that calls the C extraction function, converts to Python dict, and frees the C memory.
**When to use:** This is the only pattern for extracting structured data from the C circuit.
**Example:**
```python
# In _core.pyx, inside circuit class
def draw_data(self):
    """Extract circuit gate data as Python dict for rendering.

    Returns dict with keys: num_layers, num_qubits, gates (list of dicts).
    Each gate dict: {layer, target, type, angle, controls}.
    Qubit indices are compacted (sparse -> dense).
    """
    cdef draw_data_t *data = circuit_to_draw_data(<circuit_t*>_circuit)
    if data == NULL:
        raise RuntimeError("Failed to extract draw data")
    try:
        gates = []
        for i in range(data.num_gates):
            controls = []
            for j in range(data.gate_num_ctrl[i]):
                controls.append(int(data.ctrl_qubits[data.ctrl_offsets[i] + j]))
            gates.append({
                'layer': int(data.gate_layer[i]),
                'target': int(data.gate_target[i]),
                'type': int(data.gate_type[i]),
                'angle': float(data.gate_angle[i]),
                'controls': controls,
            })
        return {
            'num_layers': int(data.num_layers),
            'num_qubits': int(data.num_qubits),
            'gates': gates,
        }
    finally:
        free_draw_data(data)
```

### Anti-Patterns to Avoid
- **Exposing raw C pointers to Python:** Never return a C pointer or let Python code hold references to C-allocated memory. Always convert to Python objects inside the Cython function and free C memory in a `finally` block.
- **Iterating gates from Python via repeated Cython calls:** Each call crosses the C-Python boundary. For 10,000+ gates, this is significantly slower than a single bulk extraction.
- **Modifying draw_data_t after creation:** Treat it as read-only. Create once, convert to Python, free. No mutation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate type string names | Manual switch/case in Python | Int enum mapping from Standardgate_t | Gate enum values (X=0, Y=1, Z=2, ...) are stable; define a Python dict mapping int -> string once |
| Control qubit extraction | Custom linked list traversal | Flat ctrl_qubits array with offsets | Control qubits already have two storage modes (inline Control[2] and large_control pointer); flatten in C, not Python |
| Qubit compaction | Python-side post-processing | C-side remap during extraction | Doing it in C avoids creating a large Python dict with sparse keys that needs compaction later |

**Key insight:** The C backend already has all the iteration infrastructure (`used_gates_per_layer`, `sequence[layer][gate_idx]`, `used_occupation_indices_per_qubit`). Reuse the same loop structure as `circuit_to_qasm_string()` and `circuit_visualize()` -- just serialize to a struct instead of a string or stdout.

## Common Pitfalls

### Pitfall 1: MAXCONTROLS Boundary for Control Qubits
**What goes wrong:** `gate_t.Control[MAXCONTROLS]` is a fixed array of size 2. Gates with more than 2 controls store controls in `gate_t.large_control` (heap-allocated pointer).
**Why it happens:** Easy to forget the dual storage path and only read `Control[]`.
**How to avoid:** Always use the helper pattern from `_get_control_qubit()` in `circuit_output.c`:
```c
static qubit_t get_ctrl(gate_t *g, int index) {
    if (g->NumControls > MAXCONTROLS && g->large_control != NULL) {
        return g->large_control[index];
    }
    return g->Control[index];
}
```
**Warning signs:** Tests with multi-controlled gates (3+ controls) crash or return wrong control qubits.

### Pitfall 2: Off-by-One in used_qubits
**What goes wrong:** `circuit_t.used_qubits` is the index of the highest used qubit, NOT the count. The count is `used_qubits + 1`. Iterating `for (q = 0; q < used_qubits; ...)` misses the last qubit.
**Why it happens:** Naming suggests count, but it is max-index.
**How to avoid:** Always iterate `for (q = 0; q <= circ->used_qubits; q++)`. This matches the pattern in `circuit_visualize()` line 211 and `circuit_to_qasm_string()` line 540.
**Warning signs:** Last qubit row missing from output.

### Pitfall 3: Memory Leak in Cython if Exception Occurs
**What goes wrong:** If the Cython code raises an exception after calling C `circuit_to_draw_data()` but before calling `free_draw_data()`, the C memory leaks.
**Why it happens:** Python exceptions bypass normal control flow.
**How to avoid:** Always wrap C allocation + Python conversion + C deallocation in a `try/finally` block, exactly as `openqasm.pyx` does.
**Warning signs:** Valgrind reports leaked blocks from `circuit_to_draw_data`.

### Pitfall 4: Empty Circuit Edge Case
**What goes wrong:** Circuit with 0 gates, 0 layers, or 0 used qubits causes division by zero or NULL dereference.
**Why it happens:** Arrays like `gate_layer` are not allocated (NULL) when `num_gates == 0`.
**How to avoid:** Check `circ->used == 0` early and return a valid `draw_data_t` with zero counts and NULL arrays. In Cython, return `{'num_layers': 0, 'num_qubits': 0, 'gates': []}`.
**Warning signs:** Segfault on `ql.circuit(); c.draw_data()` with no gates.

### Pitfall 5: Large Circuit Memory Allocation
**What goes wrong:** For 10,000+ gates with many controls, the total `ctrl_qubits` array can be large.
**Why it happens:** Each gate can have up to N controls; total controls across all gates could be 50K+.
**How to avoid:** Two-pass approach: first pass counts total controls to allocate exactly the right size. Second pass fills in data. This avoids realloc churn.
**Warning signs:** Performance degradation or OOM for circuits with many multi-controlled gates.

### Pitfall 6: Compaction Invalidates Gate-to-Qubit Cross-References
**What goes wrong:** After compaction, a gate's target qubit index no longer matches its original C index. Any code that needs to look up the original index loses the mapping.
**Why it happens:** Compaction is a one-way remap.
**How to avoid:** The returned dict should ONLY contain compacted indices. Downstream renderers never need the original sparse indices. If debugging needs arise, optionally include a `qubit_map` field mapping dense -> original sparse index.
**Warning signs:** Renderer draws gates on wrong qubit rows.

## Code Examples

### Example 1: C Extraction Function Structure
```c
// Source: follows pattern of circuit_to_qasm_string() in circuit_output.c
draw_data_t *circuit_to_draw_data(circuit_t *circ) {
    if (circ == NULL) return NULL;

    draw_data_t *data = calloc(1, sizeof(draw_data_t));
    if (data == NULL) return NULL;

    // Step 1: Build qubit remap table
    int *remap = calloc(circ->used_qubits + 1, sizeof(int));
    int dense_count = 0;
    for (int q = 0; q <= (int)circ->used_qubits; q++) {
        if (circ->used_occupation_indices_per_qubit[q] != 0) {
            remap[q] = dense_count++;
        } else {
            remap[q] = -1;
        }
    }

    data->num_layers = circ->used_layer;
    data->num_qubits = dense_count;
    data->num_gates = (unsigned int)circ->used;

    if (data->num_gates == 0) {
        free(remap);
        return data;  // Valid empty result
    }

    // Step 2: Allocate parallel arrays
    data->gate_layer    = malloc(data->num_gates * sizeof(unsigned int));
    data->gate_target   = malloc(data->num_gates * sizeof(unsigned int));
    data->gate_type     = malloc(data->num_gates * sizeof(unsigned int));
    data->gate_angle    = malloc(data->num_gates * sizeof(double));
    data->gate_num_ctrl = malloc(data->num_gates * sizeof(unsigned int));
    data->ctrl_offsets  = malloc(data->num_gates * sizeof(unsigned int));

    // Step 3: First pass -- count total controls for ctrl_qubits allocation
    unsigned int total_controls = 0;
    for (unsigned int layer = 0; layer < circ->used_layer; layer++) {
        for (unsigned int gi = 0; gi < circ->used_gates_per_layer[layer]; gi++) {
            total_controls += circ->sequence[layer][gi].NumControls;
        }
    }
    data->ctrl_qubits = (total_controls > 0) ? malloc(total_controls * sizeof(unsigned int)) : NULL;

    // Step 4: Second pass -- fill arrays
    unsigned int gate_idx = 0;
    unsigned int ctrl_idx = 0;
    for (unsigned int layer = 0; layer < circ->used_layer; layer++) {
        for (unsigned int gi = 0; gi < circ->used_gates_per_layer[layer]; gi++) {
            gate_t *g = &circ->sequence[layer][gi];
            data->gate_layer[gate_idx]    = layer;
            data->gate_target[gate_idx]   = remap[g->Target];
            data->gate_type[gate_idx]     = (unsigned int)g->Gate;
            data->gate_angle[gate_idx]    = g->GateValue;
            data->gate_num_ctrl[gate_idx] = g->NumControls;
            data->ctrl_offsets[gate_idx]  = ctrl_idx;

            for (unsigned int c = 0; c < g->NumControls; c++) {
                qubit_t cq = (g->NumControls > MAXCONTROLS && g->large_control != NULL)
                             ? g->large_control[c] : g->Control[c];
                data->ctrl_qubits[ctrl_idx++] = remap[cq];
            }
            gate_idx++;
        }
    }

    free(remap);
    return data;
}
```

### Example 2: Free Function
```c
void free_draw_data(draw_data_t *data) {
    if (data == NULL) return;
    free(data->gate_layer);
    free(data->gate_target);
    free(data->gate_type);
    free(data->gate_angle);
    free(data->gate_num_ctrl);
    free(data->ctrl_qubits);
    free(data->ctrl_offsets);
    free(data);
}
```

### Example 3: Cython extern Declarations (for _core.pxd)
```cython
cdef extern from "circuit_output.h":
    ctypedef struct draw_data_t:
        unsigned int num_layers
        unsigned int num_qubits
        unsigned int num_gates
        unsigned int *gate_layer
        unsigned int *gate_target
        unsigned int *gate_type
        double *gate_angle
        unsigned int *gate_num_ctrl
        unsigned int *ctrl_qubits
        unsigned int *ctrl_offsets

    draw_data_t *circuit_to_draw_data(circuit_t *circ)
    void free_draw_data(draw_data_t *data)
```

### Example 4: Test Pattern (following test_openqasm_export.py)
```python
def test_draw_data_returns_dict(clean_circuit):
    a = ql.qint(5, width=4)
    data = clean_circuit.draw_data()
    assert isinstance(data, dict)
    assert 'num_layers' in data
    assert 'num_qubits' in data
    assert 'gates' in data
    assert len(data['gates']) > 0

def test_draw_data_qubit_compaction(clean_circuit):
    """Verify sparse qubit indices are remapped to dense rows."""
    a = ql.qint(5, width=4)
    data = clean_circuit.draw_data()
    # All qubit indices in gates should be < num_qubits
    for gate in data['gates']:
        assert gate['target'] < data['num_qubits']
        for ctrl in gate['controls']:
            assert ctrl < data['num_qubits']

def test_draw_data_gate_fields(clean_circuit):
    a = ql.qint(5, width=4)
    data = clean_circuit.draw_data()
    for gate in data['gates']:
        assert 'layer' in gate
        assert 'target' in gate
        assert 'type' in gate
        assert 'angle' in gate
        assert 'controls' in gate
        assert isinstance(gate['controls'], list)

def test_draw_data_empty_circuit(clean_circuit):
    data = clean_circuit.draw_data()
    assert data['num_gates'] == 0 or data['num_layers'] == 0
    # Note: empty circuit may still report num_qubits >= 1 due to auto-init
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ASCII text `print_circuit()` | `circuit_visualize()` improved ASCII | Phase 25 era | Better formatting but still text-only |
| No programmatic access to gate data | `circuit_to_qasm_string()` serializes to OpenQASM | Phase 25 | First bulk extraction pattern; we extend this |
| Per-accessor field access | Single bulk extraction | This phase | Establishes the draw_data pattern for all future Python-side analysis |

**Deprecated/outdated:**
- `print_circuit()`: Still exists but limited (caps at 2000 gates, basic formatting). `circuit_visualize()` supersedes it for text output.
- Direct field access from Python: Not available and not needed. Cython bulk extraction is the pattern.

## Open Questions

1. **Gate type string names in Python**
   - What we know: `Standardgate_t` enum is `{X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9}`. The `draw_data()` dict returns these as integers.
   - What's unclear: Should the dict return string names ('X', 'H', etc.) or integer enum values?
   - Recommendation: Return integers in the dict (avoids string allocation in C and keeps the bridge thin). Provide a Python-side `GATE_NAMES = {0: 'X', 1: 'Y', ...}` constant for downstream code that needs names. This is what the renderer will use.

2. **Whether to include original (sparse) qubit indices**
   - What we know: Compaction remaps to dense indices. Downstream renderer only needs dense indices.
   - What's unclear: Future use cases (e.g., debugging) might want the original mapping.
   - Recommendation: Optionally include a `qubit_map` list in the dict where `qubit_map[dense_idx] = original_sparse_idx`. Cheap to produce (it is the inverse of the remap table). Defer to planner's judgment.

3. **Performance at 200+ qubits and 10,000+ gates**
   - What we know: The C extraction is O(total_gates + total_controls), which is fast. The Python dict construction is the bottleneck (10,000 dict allocations).
   - What's unclear: Exact timing on target hardware.
   - Recommendation: The dict-of-lists approach should be fine for 10K gates (~10ms in Python). If profiling reveals issues, a future optimization could return NumPy arrays instead of lists of dicts. But start with the simple approach.

## Sources

### Primary (HIGH confidence)
- `c_backend/include/types.h` -- `gate_t` struct: `Control[2]`, `large_control`, `NumControls`, `Gate` (Standardgate_t), `GateValue`, `Target`
- `c_backend/include/circuit.h` -- `circuit_t` struct: `sequence[layer][gate_idx]`, `used_layer`, `used_qubits`, `used_gates_per_layer[layer]`, `used_occupation_indices_per_qubit[qubit]`
- `c_backend/src/circuit_output.c` -- `circuit_to_qasm_string()` (lines 517-584): iteration pattern for layers/gates, buffer allocation, `_get_control_qubit()` helper
- `c_backend/src/circuit_output.c` -- `circuit_visualize()` (lines 178-277): qubit skip pattern using `used_occupation_indices_per_qubit[qubit] != 0`
- `src/quantum_language/openqasm.pyx` -- Cython bridge pattern: get C pointer, call C function, convert to Python, free C memory in finally block
- `src/quantum_language/_core.pxd` -- Existing extern declarations for `circuit_t`, `circuit_s`, `gate_counts_t`
- `src/quantum_language/_core.pyx` -- `circuit` class with `visualize()`, `gate_counts` property, `draw_data()` insertion point
- `src/quantum_language/__init__.py` -- Public API exports, `__all__` list
- `setup.py` -- Build configuration: all .pyx files auto-discovered, C sources list, include_dirs
- `.planning/research/ARCHITECTURE-PIXEL-VIZ.md` -- Prior architecture research confirming this approach

### Secondary (MEDIUM confidence)
- None needed; all findings verified from direct codebase inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Uses only existing Cython/C toolchain already in the project
- Architecture: HIGH -- Follows established `circuit_to_qasm_string()` pattern exactly, confirmed by architecture research doc
- Pitfalls: HIGH -- All pitfalls identified from direct code inspection of `gate_t.Control`/`large_control` dual path, `used_qubits` semantics, and memory management patterns

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (stable; C backend and Cython patterns change rarely)
