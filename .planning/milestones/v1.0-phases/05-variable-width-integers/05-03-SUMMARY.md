---
phase: 05-variable-width-integers
plan: 03
subsystem: python-bindings
tags: [python, cython, qint, qbool, variable-width, api]

# Dependency graph
requires:
  - phase: 05-01
    provides: quantum_int_t with width field, right-aligned q_address[64]
  - phase: 05-02
    provides: QQ_add(int bits), cQQ_add(int bits) parameterized functions
provides:
  - qint(value, width=N) creates N-bit quantum integers
  - qint.width property (read-only)
  - Width validation (ValueError for < 1 or > 64)
  - Overflow warnings when value exceeds width range
  - qbool as syntactic sugar for qint(width=1)
affects:
  - 05-04 (multiplication and other operations)
  - User-facing Python API

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Width parameter with bits backward compat alias"
    - "Right-aligned qubit extraction for C backend"
    - "1-bit unsigned range for qbool (0-1 not -1 to 0)"

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pyx

key-decisions:
  - "width parameter primary, bits as backward compat alias"
  - "Default width is 8 bits (INTEGERSIZE)"
  - "ValueError for width < 1 or > 64"
  - "UserWarning for value overflow (warn, don't fail)"
  - "qbool treated as unsigned 1-bit [0,1] for warnings"
  - "Extract only used qubits from right-aligned array for C backend"

patterns-established:
  - "Width-aware Python API: qint(value, width=N)"
  - "Right-aligned extraction for mixed-width operations"

# Metrics
duration: 11min
completed: 2026-01-26
---

# Phase 5 Plan 3: Python qint Width Support Summary

**Width-aware Python qint class with validation, warnings, and read-only width property**

## Performance

- **Duration:** 11 min
- **Started:** 2026-01-26T14:31:42Z
- **Completed:** 2026-01-26T14:43:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- qint(value, width=N) creates N-bit quantum integers
- qint(value, bits=N) works for backward compatibility
- Default width is 8 bits per INTEGERSIZE
- width property returns stored width (read-only)
- ValueError raised for width < 1 or > 64
- UserWarning issued when value exceeds width range
- qbool uses width=1 with unsigned [0,1] range
- Fixed qubit array extraction for C backend compatibility
- All 59 tests pass

## Task Commits

1. **Tasks 1+2: Width parameter, validation, warnings, property** - `e30fd8d` (feat)
   - width parameter (primary) with bits alias
   - Width validation: ValueError for < 1 or > 64
   - Overflow warning for values outside signed range
   - Read-only width property
   - Updated arrays to 64 elements for max width support

2. **Task 3: qbool uses width=1, fix qubit extraction** - `13c80a1` (feat)
   - qbool docstring and width=1 parameter
   - Fixed qbool(True) warning: 1-bit uses unsigned [0,1]
   - Fixed addition_inplace qubit extraction
   - Fixed multiplication_inplace qubit extraction
   - Fixed logic operations (and, or, invert) layout

## Files Modified

- `python-backend/quantum_language.pyx` - Complete qint class update

## Key Changes

### qint.__init__ with width validation
```python
def __init__(self, value=0, width=None, bits=None, classical=False, ...):
    # Handle width/bits parameter (width takes precedence)
    if width is None and bits is None:
        actual_width = INTEGERSIZE  # Default 8 bits
    elif width is not None:
        actual_width = width
    else:
        actual_width = bits  # Backward compatibility

    # Width validation
    if actual_width < 1 or actual_width > 64:
        raise ValueError(f"Width must be 1-64, got {actual_width}")

    # Overflow warning
    if value != 0:
        if actual_width == 1:
            max_value, min_value = 1, 0  # Unsigned for qbool
        else:
            max_value = (1 << (actual_width - 1)) - 1
            min_value = -(1 << (actual_width - 1))
        if value > max_value or value < min_value:
            warnings.warn(f"Value {value} exceeds range...")
```

### width property
```python
@property
def width(self):
    """Get the bit width (read-only)."""
    return self.bits
```

### Qubit extraction for C backend
```python
# Extract only used qubits from right-aligned 64-element array
self_offset = 64 - self.bits
qubit_array[:self.bits] = self.qubits[self_offset:64]
```

## Decisions Made

1. **width as primary parameter:** Clean API, bits kept for backward compat
2. **8-bit default width:** Matches existing INTEGERSIZE constant
3. **Warn on overflow, don't fail:** Per CONTEXT.md, user may want modular arithmetic
4. **qbool unsigned 1-bit:** True=1 should not warn, treat as [0,1] range
5. **Extract used qubits:** C backend expects compact arrays, not 64-element blocks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 64-element array incompatibility with C backend**
- **Found during:** Task 1 (addition tests hanging)
- **Issue:** C backend expects compact qubit arrays, not 64-element blocks
- **Fix:** Extract only used qubits from right-aligned storage
- **Files modified:** python-backend/quantum_language.pyx
- **Commit:** 13c80a1

**2. [Rule 1 - Bug] Fixed qbool(True) spurious warning**
- **Found during:** Task 3 (qbool tests)
- **Issue:** 1-bit signed range is [-1, 0], causing warning for True=1
- **Fix:** Treat 1-bit as unsigned [0, 1] for warning purposes
- **Files modified:** python-backend/quantum_language.pyx
- **Commit:** 13c80a1

## Issues Encountered

- Initial implementation used 64-element qubit array blocks which broke C backend compatibility
- Logic operations (and, or, invert) still use INTEGERSIZE layout, adapted Python bindings

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Python API now supports variable-width quantum integers
- All arithmetic operations use parameterized widths
- Ready for 05-04: Multiplication and remaining operations
- Full test suite verified passing (59 tests)

---
*Phase: 05-variable-width-integers*
*Completed: 2026-01-26*
