---
phase: 22-array-class-foundation
plan: 03
subsystem: array
tags: [cython, qarray, numpy-style, quantum-arrays, extended-api, dtype-support]

requires:
  - 22-01  # qarray core structure with flattened storage

provides:
  - Extended construction API with width/dtype/dim parameters
  - NumPy array integration with dtype-based width inference
  - qbool array support via dtype parameter
  - Dimension-based zero-initialized array creation
  - Type homogeneity validation

affects:
  - 22-04  # NumPy-style indexing will build on extended construction
  - 22-05  # Element access patterns will use dtype-aware logic

tech-stack:
  added:
    - numpy  # For np.ndarray type checking and dtype conversion
  patterns:
    - keyword-only parameters  # NumPy-style API design (*,  width=None, dtype=None)
    - type validation  # dtype must be qint or qbool
    - conditional construction  # Different paths for dim vs data

key-files:
  created: []
  modified:
    - src/quantum_language/qarray.pyx  # Extended __init__ with width/dtype/dim parameters

key-decisions:
  - "Use keyword-only parameters for width/dtype/dim to match NumPy API style"
  - "Homogeneity validation: mixed qint/qbool arrays are rejected at construction time"
  - "NumPy dtype.itemsize used for bit width calculation (bytes * 8)"
  - "dim parameter mutually exclusive with data - cannot specify both"
  - "qbool arrays always have width=1 regardless of width parameter"

metrics:
  duration: 395 seconds
  completed: 2026-01-29
---

# Phase 22 Plan 03: Extended Construction API Summary

**One-liner:** qarray now supports width/dtype/dim parameters for flexible construction from values, NumPy arrays, or dimensions

## What Was Built

Extended qarray.__init__() with three new keyword-only parameters:

1. **width parameter**: Explicit bit width override
   - Allows `qarray([1,2,3], width=16)` for 16-bit elements
   - Warns if values exceed specified width (will be truncated)
   - Overrides auto-inference from values

2. **dtype parameter**: Type specification (qint or qbool)
   - `dtype=qbool` creates qbool arrays
   - `dtype=qint` creates qint arrays (default)
   - Validates dtype is qint or qbool, raises TypeError otherwise
   - Enforces homogeneity: mixed qint/qbool raises ValueError

3. **dim parameter**: Dimension-based construction
   - `dim=5` creates 1D array of 5 elements
   - `dim=(3,3)` creates 3x3 array (9 elements)
   - Zero-initialized by default
   - Mutually exclusive with data parameter

4. **NumPy integration**:
   - Accepts np.ndarray as data
   - Uses dtype.itemsize * 8 for width inference
   - Converts to Python list internally for shape detection

## Implementation Details

### Parameter Processing Order

1. Check dim parameter first - if present, skip normal data processing
2. Handle NumPy arrays - convert to list, infer width from dtype
3. Process data normally - detect shape, flatten, validate types
4. Apply width/dtype parameters to element creation

### Type Validation

- Mixed qint/qbool objects in data raise ValueError with "homogeneous" message
- dtype parameter validated against (qint, qbool) tuple
- qbool arrays always get width=1 regardless of width parameter

### Width Handling

- For qint: width parameter > inferred width > INTEGERSIZE
- For qbool: always width=1
- Warning issued when explicit width too small for values

## Tasks Completed

| Task | Commit | Files Modified |
|------|--------|----------------|
| 1. Add width and dtype parameters | 755e7aa | src/quantum_language/qarray.pyx |
| 2. Add NumPy and dimension-based construction | 689ebc5 | src/quantum_language/qarray.pyx |

## Verification Results

All success criteria met:

✅ `qarray([1,2,3], width=16)` creates 16-bit elements
✅ `qarray([True, False], dtype=qbool)` creates qbool array
✅ `qarray([qint(1), qbool(True)])` raises ValueError about mixing types
✅ `qarray(np.array([1,2], dtype=np.int32))` uses width=32
✅ `qarray(dim=(3,3), dtype=qint)` creates 3x3 qint array
✅ `qarray(dim=5, dtype=qbool)` creates 5-element qbool array

## Decisions Made

### Keyword-Only Parameters

Used `*` in signature to force keyword-only for width/dtype/dim:
```python
def __init__(self, data=None, *, width=None, dtype=None, dim=None):
```

**Rationale:** Matches NumPy API conventions, prevents positional argument confusion

### Homogeneity Enforcement

Arrays must contain only qint OR only qbool, not both.

**Rationale:** Simplifies element access, iteration, and operations - dtype is array-level property

### NumPy Width Inference

Use `dtype.itemsize * 8` (bytes to bits) for width calculation.

**Rationale:** Direct mapping from NumPy types (int8→8, int16→16, int32→32, int64→64)

### dim/data Mutual Exclusivity

Specifying both `data` and `dim` raises ValueError.

**Rationale:** Ambiguous semantics - dimension-based creates zeros, data-based uses values

## Next Phase Readiness

**Blocks nothing.** Plan 22-04 (NumPy-style indexing) can proceed.

**Enables:**
- Multi-dimensional indexing can now work with dimension-created arrays
- Tests can use `qarray(dim=...)` for quick array creation
- qbool array operations can be implemented

**Known issues:** None

## Deviations from Plan

None - plan executed exactly as written.

## Technical Debt

None introduced. The API is clean and well-validated.

## Notes for Future Phases

- The dtype parameter will be used in future plans for element access patterns
- Width parameter sets up future width-aware operations
- Dimension-based construction enables testing without sample data
