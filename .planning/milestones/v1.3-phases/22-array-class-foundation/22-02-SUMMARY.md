---
phase: 22-array-class-foundation
plan: 02
subsystem: array
tags: [cython, qarray, numpy-indexing, view-semantics, multi-dimensional]

# Dependency graph
requires:
  - phase: 22-array-class-foundation
    plan: 01
    provides: qarray Cython extension type with core data structure
provides:
  - NumPy-style multi-dimensional indexing (arr[i,j], arr[:, j])
  - View semantics with shared qint object references
  - Negative index support across all indexing modes
  - Row and column slicing for 2D arrays
affects: [22-03-numpy-construction, quantum-algorithms]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Row-major flattened storage with multi-dimensional index translation"
    - "View arrays share qint object references, not copies"
    - "Cython extension type view creation with explicit cdef initialization"

key-files:
  created: []
  modified:
    - src/quantum_language/qarray.pyx

key-decisions:
  - "Single int on multi-dimensional array returns row view (NumPy behavior)"
  - "View arrays created via qarray.__new__() with manual cdef attribute initialization"
  - "Multi-dimensional indexing uses _multi_to_flat for row-major index calculation"

patterns-established:
  - "_multi_to_flat converts (i,j) coordinates to flat index using row-major strides"
  - "_handle_multi_index dispatches based on key pattern (all-int vs mixed int/slice)"
  - "_create_view as @staticmethod using cdef qarray declaration for proper initialization"

# Metrics
duration: 8min
completed: 2026-01-29
---

# Phase 22 Plan 02: Multi-Dimensional Indexing and View Semantics Summary

**One-liner:** NumPy-style indexing (arr[i,j], arr[:, 0]) with view semantics sharing underlying qint objects

## What Was Built

Implemented comprehensive multi-dimensional indexing for qarray with NumPy-compatible semantics:

1. **Multi-dimensional element access:** `arr[0, 1]` returns qint at row 0, column 1
2. **Row slicing:** `arr[0]` on 2D array returns first row as view
3. **Column slicing:** `arr[:, 0]` returns first column as view
4. **Negative indices:** `arr[-1]` works across all modes
5. **View semantics:** Sliced arrays share qint object references with original

**Key implementation details:**
- `_multi_to_flat(indices)`: Converts multi-dimensional indices to flat index using row-major stride calculation
- `_handle_multi_index(key)`: Dispatches based on tuple key pattern (all-int, row slice, column slice)
- `_create_view(elements, shape)`: Creates view array sharing qint references, using Cython-specific initialization

## Technical Implementation

### Multi-Dimensional Index Translation

Row-major storage formula: `flat_idx = i*cols + j` (for 2D)

General algorithm processes dimensions in reverse:
```python
flat = 0
stride = 1
for dim in reversed(range(len(shape))):
    flat += indices[dim] * stride
    stride *= shape[dim]
```

### View Creation Pattern

Cython extension types require special handling:
```python
@staticmethod
def _create_view(elements, shape):
    cdef qarray arr = qarray.__new__(qarray)
    arr._elements = elements  # Shared list reference
    arr._shape = shape
    # ... infer dtype/width from elements
    return arr
```

**Why this pattern:** Cython cdef attributes cannot be set on instances created via normal `__new__(cls)`. Must use `qarray.__new__(qarray)` with `cdef qarray` declaration.

### Single Index Behavior on Multi-Dimensional Arrays

When `arr[0]` is called on 2D array with shape (2, 3):
- Convert to tuple: `arr[0]` → `arr[0, :]`
- Call `_handle_multi_index((0, slice(None)))`
- Return row view with shape (3,)

This matches NumPy behavior where single index selects from first dimension.

## Verification Results

All success criteria met:

1. ✓ Multi-dimensional arrays constructed from nested lists
2. ✓ Jagged arrays rejected with clear error message
3. ✓ Single element access via tuple index (arr[i,j])
4. ✓ Slice returns view sharing underlying qints
5. ✓ Negative indices normalized correctly
6. ✓ Column slicing works (arr[:, j])

**View semantics confirmed:**
```python
arr = qarray([[1,2,3],[4,5,6]])
row = arr[0]
arr[0, 0] is row[0]  # True - same qint object
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed view creation for Cython extension types**
- **Found during:** Task 2 verification
- **Issue:** `AttributeError: 'qarray' object has no attribute '_elements'` when creating views
- **Root cause:** Cython extension types with cdef attributes cannot use `cls.__new__(cls)` and direct attribute assignment
- **Fix:** Changed `_create_view` to use `cdef qarray arr = qarray.__new__(qarray)` with manual attribute initialization
- **Files modified:** src/quantum_language/qarray.pyx
- **Commit:** b2e8693

**2. [Rule 2 - Missing Critical] Added multi-dimensional behavior for single int index**
- **Found during:** Task 2 verification
- **Issue:** `arr[0]` on 2D array returned single qint instead of row view
- **Why critical:** NumPy compatibility requires single index to select from first dimension
- **Fix:** Modified `__getitem__` to detect multi-dimensional arrays and convert single int to tuple indexing
- **Files modified:** src/quantum_language/qarray.pyx
- **Commit:** b2e8693 (included in same commit)

## Next Phase Readiness

**Ready for plan 22-03:** NumPy-style array construction

**Provides:**
- Working multi-dimensional indexing infrastructure
- View semantics pattern for slicing operations
- Multi-to-flat index translation for advanced operations

**Known constraints:**
- Complex slicing patterns (e.g., arr[::2, 1:3]) raise NotImplementedError
- Only 2D slicing patterns implemented (row, column, element)
- Future plans may need to extend _handle_multi_index for N-dimensional support

## Lessons Learned

1. **Cython extension type initialization:** cdef attributes require explicit handling after `__new__()` - cannot use Python's normal `__new__(cls)` pattern
2. **NumPy compatibility:** Single integer index on multi-dimensional array must return first-dimension slice, not flattened element
3. **View semantics verification:** Test with `is` operator, not equality - must verify actual object reference sharing

## Files Changed

| File | Lines Changed | Description |
|------|---------------|-------------|
| src/quantum_language/qarray.pyx | +6 -4 | Fixed _create_view Cython initialization |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| b2e8693 | fix | Correct _create_view for Cython extension type |

Note: Core multi-dimensional indexing implementation was already present from previous work. This plan verified functionality and fixed view creation bug.
