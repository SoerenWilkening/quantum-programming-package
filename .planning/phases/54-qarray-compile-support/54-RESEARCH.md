# Phase 54: qarray Support in @ql.compile - Research

**Researched:** 2026-02-05
**Domain:** Extending @ql.compile infrastructure to handle ql.qarray arguments, caching, and replay
**Confidence:** HIGH

## Summary

Phase 54 extends the existing `@ql.compile` decorator (from Phases 48-51) to support `ql.qarray` arguments. The current `compile.py` infrastructure handles `qint` arguments through `_classify_args()`, `_get_qint_qubit_indices()`, and `_input_qubit_key()` functions. These functions need extension to recognize and handle `qarray` objects, which are essentially containers of `qint`/`qbool` elements stored in a flattened list (`_elements`) with shape metadata.

The key insight is that a `qarray` is a collection of `qint`/`qbool` objects, each with its own qubit indices. For capture/replay purposes, we flatten all element qubits into a single ordered sequence. Cache keys incorporate array length (shape) per CONTEXT.md decision. Element widths are validated at replay time (must match) rather than included in the cache key.

**Primary recommendation:** Extend `_classify_args()` to recognize `qarray` via `isinstance()` check. Add `_get_qarray_qubit_indices()` that iterates over `arr._elements` and extracts qubit indices from each element. Modify `_input_qubit_key()` to handle both `qint` and `qarray`. Update cache key building to include array lengths. All changes are pure Python in `compile.py` -- no Cython or C backend changes needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `compile.py` (existing) | Phase 48-51 | `CompiledFunc`, `CompiledBlock`, gate capture/replay | All qarray support extends these existing classes |
| `qarray.pyx` (existing) | Phase 22-25 | `qarray` cdef class with `_elements`, `_shape`, `_dtype`, `_width` | Defines the qarray structure to support |
| `qint.pyx` (existing) | Phase 1-17 | `qint` cdef class with `qubits`, `width` attributes | Elements of qarray, qubit extraction pattern established |
| `qbool.pyx` (existing) | Phase 3 | `qbool` cdef class (subclass of qint, width=1) | Optional qarray element type, same qubit extraction |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `isinstance()` | builtin | Type checking for qarray vs qint | In `_classify_args()` to detect qarray arguments |
| `collections.OrderedDict` | stdlib | Cache management | Already used in `CompiledFunc._cache` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `isinstance(arg, qarray)` check | Duck typing on `_elements` attribute | Explicit type check is clearer and safer; qarray is a cdef class with fixed attributes |
| Flattening all element qubits | Tracking element boundaries separately | Flattening is simpler; element boundaries can be reconstructed from widths during replay if needed |
| Shape in cache key | Total element count in cache key | Shape is more precise; per CONTEXT.md, shape (length) only, not widths |

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
  compile.py               # MODIFY: Add qarray support to _classify_args, _get_qarray_qubit_indices, etc.
  qarray.pyx               # READ-ONLY: Reference for qarray structure
tests/
  test_compile.py          # MODIFY: Add qarray-specific tests for capture, replay, caching
```

### Pattern 1: Qubit Index Extraction from qarray
**What:** Extract all physical qubit indices from a qarray by iterating over its elements
**When to use:** In capture and replay to build virtual-to-real mappings
**Example:**
```python
# Source: Pattern from existing _get_qint_qubit_indices in compile.py

def _get_qarray_qubit_indices(arr):
    """Extract all real qubit indices from a qarray, ordered by element then by bit position.

    Returns a flat list of qubit indices: [elem0_bit0, elem0_bit1, ..., elem1_bit0, ...].
    """
    from .qarray import qarray  # Import here to avoid circular dependency

    indices = []
    for elem in arr._elements:
        # Each element is a qint or qbool; use same pattern as _get_qint_qubit_indices
        elem_indices = _get_qint_qubit_indices(elem)
        indices.extend(elem_indices)
    return indices
```

### Pattern 2: Extended Argument Classification
**What:** Extend `_classify_args()` to recognize and classify qarray arguments alongside qint
**When to use:** When processing function arguments in `CompiledFunc.__call__`
**Example:**
```python
# Source: Pattern from existing _classify_args in compile.py lines 587-615

from .qarray import qarray  # At top of file

def _classify_args(self, args, kwargs):
    """Separate quantum (qint, qarray) and classical arguments.

    Returns (quantum_args, classical_args, widths_or_shapes).
    For qint: widths is the bit width
    For qarray: widths_or_shapes encodes (array_length, element_count, total_qubits)
    """
    quantum_args = []
    classical_args = []
    widths_or_shapes = []

    for arg in args:
        if isinstance(arg, qarray):
            quantum_args.append(arg)
            # Per CONTEXT.md: cache key based on shape (array length) only
            # Store as negative to distinguish from qint widths, or use tuple
            widths_or_shapes.append(('arr', len(arg)))
        elif isinstance(arg, qint):
            quantum_args.append(arg)
            widths_or_shapes.append(arg.width)
        else:
            classical_args.append(arg)

    # ... kwargs processing (same pattern)
    return quantum_args, classical_args, widths_or_shapes
```

### Pattern 3: Qubit Mapping for Mixed Arguments
**What:** Build virtual-to-real qubit mappings that handle both qint and qarray arguments
**When to use:** In `_capture_inner()` and `_replay()` to build `param_qubit_indices`
**Example:**
```python
# Source: Pattern from _capture_inner in compile.py lines 637-639

def _get_quantum_arg_qubit_indices(qa):
    """Get qubit indices from a quantum argument (qint or qarray).

    Returns list of list of qubit indices (one inner list per 'unit'):
    - For qint: [[q0, q1, ...]] (single unit)
    - For qarray: [[elem0_q0, elem0_q1, ...], [elem1_q0, ...], ...] (one per element)

    This preserves element boundaries for accurate return value reconstruction.
    """
    if isinstance(qa, qarray):
        # Return list of lists: one per element
        return [_get_qint_qubit_indices(elem) for elem in qa._elements]
    else:
        # qint: single element
        return [_get_qint_qubit_indices(qa)]
```

### Pattern 4: Cache Key with Array Shape
**What:** Build cache keys that distinguish qarrays by their shape/length
**When to use:** In `_build_cache_key()` logic within `__call__`
**Example:**
```python
# Cache key format with qarrays:
# (classical_args, widths_or_shapes, control_count, qubit_saving)
# where widths_or_shapes contains:
#   - integers for qint widths (e.g., 4, 8)
#   - tuples for qarray shapes (e.g., ('arr', 3) for 3-element array)

# Per CONTEXT.md decision:
# - Cache key based on shape only (array length), not element widths
# - For mixed args: total qubit count across all args (flattened)
# - Strict remapping: error if element widths don't match at replay

cache_key = (
    tuple(classical_args),
    tuple(widths_or_shapes),  # e.g., (4, ('arr', 3), 8) for qint(w=4), qarray(len=3), qint(w=8)
    control_count,
    qubit_saving,
)
```

### Pattern 5: qarray Return Value Construction
**What:** Reconstruct a qarray return value during replay from virtual-to-real mappings
**When to use:** When the compiled function returns a qarray (supports returning qarrays per CONTEXT.md)
**Example:**
```python
# Source: Pattern from _build_return_qint in compile.py lines 438-467

def _build_return_qarray(block, virtual_to_real, original_arr, start_layer, end_layer):
    """Construct a qarray return value from replay-mapped qubits.

    Creates new qint/qbool elements with qubits mapped from virtual space.
    Preserves the original array's shape and dtype.
    """
    # Determine where return array qubits start in virtual space
    ret_start, ret_qubit_count = block.return_qubit_range

    # Create new elements with remapped qubits
    new_elements = []
    virt_offset = ret_start
    for orig_elem in original_arr._elements:
        elem_width = orig_elem.width if hasattr(orig_elem, 'width') else 1

        # Build qubit array for this element
        ret_qubits = np.zeros(64, dtype=np.uint32)
        for i in range(elem_width):
            virt_q = virt_offset + i
            real_q = virtual_to_real[virt_q]
            ret_qubits[64 - elem_width + i] = real_q
        virt_offset += elem_width

        # Create element with existing qubits
        new_elem = qint(create_new=False, bit_list=ret_qubits, width=elem_width)
        new_elem.allocated_start = virtual_to_real[ret_start + len(new_elements) * elem_width]
        new_elem.allocated_qubits = True
        new_elem._start_layer = start_layer
        new_elem._end_layer = end_layer
        new_elem.operation_type = "COMPILED"
        new_elements.append(new_elem)

    # Create qarray view with new elements
    return qarray._create_view(new_elements, original_arr._shape)
```

### Anti-Patterns to Avoid
- **Modifying qarray elements during type detection:** Do NOT mutate `arr._elements` during `_classify_args()`. The original qarray must remain usable.
- **Assuming uniform element widths:** Do NOT assume all qarray elements have the same width. While CONTEXT.md says "error if widths don't match between calls," this is a runtime validation, not a simplification of the data structures.
- **Copying qarray by value:** Do NOT create deep copies of qarrays. Use the existing `_create_view()` pattern that shares element references.
- **Ignoring qbool elements:** qarray can contain qbool elements (width=1). Handle these the same as qint with `width=1`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Qubit extraction from qint | Custom qubit reading logic | `_get_qint_qubit_indices(q)` (line 422-424) | Already handles the 64-element array layout with right-alignment |
| Virtual-to-real gate remapping | Custom gate rewriting | `_remap_gates(gates, mapping)` (line 411-419) | Handles target and controls uniformly |
| qarray element access | Index-based raw access | `arr._elements` iteration | cdef attribute, direct access is correct |
| Gate sequence optimization | Custom optimization | `_optimize_gate_list(gates)` (line 150-177) | Multi-pass cancellation/merge already implemented |

**Key insight:** The existing capture-replay infrastructure handles qubit remapping generically. A qarray is just a collection of qints/qbools; flatten all their qubits into the same namespace used for individual qints, and the existing machinery handles the rest.

## Common Pitfalls

### Pitfall 1: Import Cycle with qarray
**What goes wrong:** Importing `qarray` at module level in `compile.py` causes circular import
**Why it happens:** `compile.py` is imported early; `qarray.pyx` may import from compile or related modules
**How to avoid:** Import `qarray` inside functions that need it, or use string-based type checking
**Warning signs:** `ImportError` during module load, "partially initialized module" errors

### Pitfall 2: Element Width Mismatch at Replay
**What goes wrong:** Replay with qarray of different element widths than capture produces incorrect circuit
**Why it happens:** Virtual qubit mapping assumes same total qubit count; different widths = different count
**How to avoid:** Per CONTEXT.md: "Strict remapping: error if element widths don't match between calls". Validate total qubit count at replay start.
**Warning signs:** `IndexError` when accessing virtual_to_real mapping, incorrect gate targets

### Pitfall 3: Empty qarray Handling
**What goes wrong:** Empty qarray (length 0) causes division by zero or index errors
**Why it happens:** No elements to extract qubits from; empty list edge cases
**How to avoid:** Per CONTEXT.md: "Empty qarrays (length 0) raise error -- not supported as input". Check length at entry to `_classify_args()`.
**Warning signs:** Empty `param_qubit_indices`, zero `total_virtual_qubits`

### Pitfall 4: Mixed qint/qarray Argument Order
**What goes wrong:** Cache key differs based on argument order even when logically equivalent
**Why it happens:** Arguments are processed in positional order; `(qint, qarray)` vs `(qarray, qint)` produce different keys
**How to avoid:** This is actually correct behavior per CONTEXT.md ("any argument order allowed"). The cache key correctly includes argument order. No fix needed.
**Warning signs:** Cache misses when you expect hits (but this is by design)

### Pitfall 5: qarray Return Value Element Ownership
**What goes wrong:** Returned qarray elements don't have proper ownership metadata, causing issues in subsequent operations
**Why it happens:** Manually constructed qint elements via `create_new=False` need explicit ownership setting
**How to avoid:** Set `allocated_start`, `allocated_qubits`, `_start_layer`, `_end_layer`, `operation_type` on each new element (see Pattern 5)
**Warning signs:** "qubits already deallocated" errors, incorrect uncomputation

### Pitfall 6: Loop Unrolling Capture
**What goes wrong:** For-loop over qarray inside compiled function doesn't capture all iterations
**Why it happens:** Python loop executes normally during capture; all iterations' gates are captured in sequence
**How to avoid:** This actually works correctly because capture records all gates emitted in the layer range. The loop unrolls naturally during capture. No special handling needed.
**Warning signs:** None expected; this is the "naturally works" case

### Pitfall 7: In-Place Modification Detection for qarray
**What goes wrong:** Return value detection for in-place modified qarray fails
**Why it happens:** Comparing qarray identity vs comparing element qubit identity
**How to avoid:** For "is this return value the same as input?", compare the actual qubit indices from both, not Python object identity
**Warning signs:** `return_is_param_index` incorrectly set to None when it should be set

## Code Examples

### Complete Qubit Extraction for qarray
```python
# Source: Extension of pattern from compile.py line 422-424

def _get_quantum_arg_qubit_indices(qa):
    """Get qubit indices from a qint or qarray argument.

    For qint: Returns list of qubit indices [q0, q1, ...]
    For qarray: Returns list of qubit indices from all elements, flattened
    """
    if isinstance(qa, qarray):
        indices = []
        for elem in qa._elements:
            indices.extend(_get_qint_qubit_indices(elem))
        return indices
    else:
        return _get_qint_qubit_indices(qa)
```

### Cache Key Building with qarray Support
```python
# Source: Extension of pattern from compile.py __call__ method

def _build_cache_key_component(qa):
    """Build cache key component for a quantum argument.

    Per CONTEXT.md:
    - qint: width (int)
    - qarray: length only, not element widths
    """
    if isinstance(qa, qarray):
        return ('arr', len(qa))  # Use tuple to distinguish from int width
    else:
        return qa.width

# In __call__:
widths_or_shapes = [_build_cache_key_component(qa) for qa in quantum_args]
cache_key = (tuple(classical_args), tuple(widths_or_shapes), control_count, qubit_saving)
```

### Replay-Time Width Validation
```python
# Source: New validation for CONTEXT.md requirement

def _validate_qarray_replay_widths(original_quantum_args, replay_quantum_args):
    """Validate that qarray element widths match between capture and replay.

    Per CONTEXT.md: "Strict remapping: qubit-by-qubit. Error if element widths don't match."
    """
    for orig, replay in zip(original_quantum_args, replay_quantum_args):
        if isinstance(orig, qarray) and isinstance(replay, qarray):
            if len(orig) != len(replay):
                raise ValueError(
                    f"Expected qarray of length {len(orig)}, got length {len(replay)}"
                )
            for i, (o_elem, r_elem) in enumerate(zip(orig._elements, replay._elements)):
                o_width = o_elem.width if hasattr(o_elem, 'width') else 1
                r_width = r_elem.width if hasattr(r_elem, 'width') else 1
                if o_width != r_width:
                    raise ValueError(
                        f"qarray element {i}: expected width {o_width}, got {r_width}"
                    )
```

### Extended _input_qubit_key for Inverse Support
```python
# Source: Extension of pattern from compile.py line 427-432

def _input_qubit_key(quantum_args):
    """Build hashable key from physical qubits of all quantum arguments.

    Handles both qint and qarray arguments by flattening all qubit indices.
    """
    key_parts = []
    for qa in quantum_args:
        key_parts.extend(_get_quantum_arg_qubit_indices(qa))
    return tuple(key_parts)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| qint-only capture/replay | qint + qarray capture/replay | Phase 54 | Enables compiled functions with array arguments |
| Width-based cache key | Width for qint, length for qarray | Phase 54 | Correct cache separation for different array sizes |
| Single qint return | qint or qarray return | Phase 54 | Full support for array-returning compiled functions |

## Open Questions

1. **Element boundary tracking during replay**
   - What we know: Flattening qarray qubits works for capture. Replay needs to reconstruct array structure.
   - What's unclear: Should we store per-element qubit ranges in `CompiledBlock`, or derive them from widths at replay time?
   - Recommendation: Store a list of element widths in `CompiledBlock` alongside `param_qubit_ranges`. This enables accurate reconstruction without requiring the original qarray at replay time.

2. **Stale qarray detection**
   - What we know: Per CONTEXT.md, "Runtime error if qarray contains deallocated qubits"
   - What's unclear: How to detect deallocated qubits. The qint has `allocated_qubits` and `_is_uncomputed` flags.
   - Recommendation: Check each element's `_is_uncomputed` or `allocated_qubits` flag at the start of `_classify_args()`. Raise `ValueError` with message "qarray contains deallocated qubits" if any element is stale.

3. **qarray slice as argument**
   - What we know: qarray slices return new qarray views sharing element references
   - What's unclear: Does passing a slice (view) work correctly?
   - Recommendation: Yes, it should work because we extract qubits from `_elements`, and views share the same elements. Add a test to verify.

4. **Auto-uncompute with qarray ancillas**
   - What we know: Auto-uncompute in qubit_saving mode deallocates temp ancillas for qint returns.
   - What's unclear: How does this work when the return is a qarray with multiple elements?
   - Recommendation: The existing logic partitions ancillas into return vs temp based on virtual qubit ranges. For qarray returns, the return range spans all return element qubits. Same logic applies; just ensure the return range is correctly computed to cover all elements.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- Full implementation: `CompiledFunc`, `CompiledBlock`, `_get_qint_qubit_indices`, `_classify_args`, `_replay`, `_input_qubit_key` (1247 lines, read in full)
- `src/quantum_language/qarray.pyx` -- Full qarray implementation: `_elements`, `_shape`, `_dtype`, `_width`, iteration, indexing, `_create_view()` (974 lines, read in full)
- `src/quantum_language/qarray.pxd` -- cdef class declaration: `_elements` (list), `_shape` (tuple), `_dtype` (object), `_width` (int)
- `tests/test_compile.py` -- 70+ existing tests covering phases 48-51 (1300+ lines, read relevant sections)
- `tests/test_qarray_elementwise.py` -- qarray operation tests showing element access patterns (706 lines)
- `.planning/phases/54-qarray-compile-support/54-CONTEXT.md` -- All locked decisions for this phase

### Secondary (MEDIUM confidence)
- `.planning/phases/51-differentiators-polish/51-RESEARCH.md` -- Prior research on compile infrastructure (Phase 51 features)

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are existing codebase elements, direct inspection
- Architecture: HIGH -- patterns directly extend existing compile.py patterns
- Pitfalls: HIGH -- identified from concrete code analysis and CONTEXT.md constraints

**Research date:** 2026-02-05
**Valid until:** 2026-03-07 (30 days -- stable domain, internal project)
