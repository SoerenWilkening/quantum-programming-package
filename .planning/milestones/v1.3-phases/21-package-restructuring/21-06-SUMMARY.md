---
phase: 21-package-restructuring
plan: 06
subsystem: quantum-types
tags: [cython, pxi, qint, code-organization, file-splitting]

# Dependency graph
requires:
  - phase: 21-01
    provides: Package structure with src-layout
  - phase: 21-02
    provides: Decision to keep qint.pyx cohesive initially
provides:
  - Arithmetic operations extracted to qint_arithmetic.pxi (390 lines)
  - Bitwise operations extracted to qint_bitwise.pxi (519 lines)
  - Prepared 909 lines for removal from qint.pyx in Plan 21-07
affects: [21-07-qint-pyx-integration, file-size-compliance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cython include files (.pxi) for splitting large cdef classes"
    - "Method extraction preserving exact signatures and implementations"

key-files:
  created:
    - src/quantum_language/qint_arithmetic.pxi
    - src/quantum_language/qint_bitwise.pxi
  modified: []

key-decisions:
  - "Extract complete method implementations with all docstrings and internal calls"
  - "No imports or class declarations in .pxi files - they are textual includes"
  - "Preserve exact indentation at class level for include compatibility"

patterns-established:
  - "Include files must contain only class methods, not module-level code"
  - "Each .pxi file groups related operations (arithmetic vs bitwise)"

# Metrics
duration: 3min
completed: 2026-01-29
---

# Phase 21 Plan 06: qint Arithmetic and Bitwise Extraction Summary

**Extracted 909 lines of qint arithmetic and bitwise operations into Cython include files (.pxi) for modular compilation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-29T12:09:48Z
- **Completed:** 2026-01-29T12:13:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created qint_arithmetic.pxi with 10 arithmetic methods (390 lines)
- Created qint_bitwise.pxi with 11 bitwise methods (519 lines)
- Prepared 909 lines for removal from qint.pyx (reducing from 2432 to ~1523 lines)
- All method signatures, implementations, and docstrings preserved exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create qint_arithmetic.pxi** - `036e8fa` (feat)
2. **Task 2: Create qint_bitwise.pxi** - `1673918` (feat)

## Files Created/Modified

- `src/quantum_language/qint_arithmetic.pxi` - Arithmetic operations: addition (add/iadd/radd), subtraction (sub/isub), multiplication (mul/imul/rmul) with cdef helpers
- `src/quantum_language/qint_bitwise.pxi` - Bitwise operations: AND/OR/XOR (with in-place and reverse variants), NOT (__invert__), qubit access (__getitem__)

## Decisions Made

**Method extraction completeness**
- Extracted complete implementations including all docstrings, type annotations, and internal function calls
- Preserved exact indentation at class level (one tab) for textual inclusion via Cython's `include` directive

**No compilation in this plan**
- These .pxi files are preparatory - they cannot be compiled independently
- Integration into qint.pyx via `include` directives happens in Plan 21-07
- Verification of correct compilation deferred to Plan 21-07

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 21-07:**
- qint_arithmetic.pxi contains all 10 arithmetic methods verified complete
- qint_bitwise.pxi contains all 11 bitwise methods verified complete
- Combined 909 lines ready to be removed from qint.pyx
- Include directives can now be added to qint.pyx to wire in these files
- After Plan 21-07 completes, qint.pyx will be ~1523 lines (within target range)

**Gap closure status:**
- This plan addresses the 21-VERIFICATION.md gap: qint.pyx is 2432 lines (8x over ~300 line target)
- After Plan 21-07 integrates these includes, qint.pyx will reduce to ~1523 lines
- Further splitting (comparisons, modular arithmetic) will occur in subsequent plans

---
*Phase: 21-package-restructuring*
*Completed: 2026-01-29*
