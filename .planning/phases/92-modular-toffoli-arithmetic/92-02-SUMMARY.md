---
phase: 92-modular-toffoli-arithmetic
plan: 02
subsystem: arithmetic
tags: [modular-multiplication, cython, qint-mod, beauregard, toffoli]

# Dependency graph
requires:
  - phase: 92-01
    provides: "Beauregard modular add/sub C functions (CQ, QQ, controlled variants)"
provides:
  - "C-level modular CQ multiplication (toffoli_mod_mul_cq)"
  - "C-level modular QQ multiplication (toffoli_mod_mul_qq)"
  - "Controlled modular multiplication (toffoli_cmod_mul_cq, toffoli_cmod_mul_qq)"
  - "Python qint_mod operators dispatching to C-level Beauregard primitives"
  - "qint_mod negation (__neg__)"
  - "qint_mod * qint_mod support (previously NotImplementedError)"
  - "int64_t _modulus supporting N up to 2^63-1"
affects: [92-03, shor-algorithm, parametric-compilation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["CQ multiply via n controlled modular additions with precomputed shifts", "QQ multiply via non-modular product + bit-decomposition modular reduction", "Direct C dispatch from Cython operators"]

key-files:
  created: []
  modified:
    - "c_backend/src/ToffoliModReduce.c"
    - "c_backend/include/toffoli_arithmetic_ops.h"
    - "src/quantum_language/qint_mod.pyx"
    - "src/quantum_language/qint_mod.pxd"
    - "src/quantum_language/_core.pxd"

key-decisions:
  - "CQ multiply: schoolbook shift-and-add with precomputed a_j = (c * 2^j) mod N, n controlled modular additions"
  - "QQ multiply: compute non-modular product into 2n-bit register, reduce via controlled CQ modular additions per product bit"
  - "Removed _reduce_mod_c entirely -- all operations dispatch directly to C Beauregard primitives"
  - "Negation uses QQ subtraction from zero: result = (0 - self) mod N"
  - "N validation changed from N <= 0 to N < 2 per CONTEXT.md"

patterns-established:
  - "qint_mod operator pattern: check type, extract qubits, dispatch to C, wrap result"
  - "Controlled context check: _get_controlled() / _get_control_bool() for controlled variants"

requirements-completed: [MOD-01, MOD-02, MOD-03, MOD-04]

# Metrics
duration: 30min
completed: 2026-02-25
---

# Phase 92-02: Modular Multiplication + Python Rewiring Summary

**C-level modular CQ/QQ multiplication and complete qint_mod operator rewiring to Beauregard primitives**

## Performance

- **Duration:** ~30 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented CQ modular multiplication at C level using schoolbook shift-and-add with precomputed modular shifts
- Implemented QQ modular multiplication using non-modular product + bit-decomposition reduction
- Completely rewired all qint_mod Python operators (__add__, __sub__, __mul__, __neg__) to dispatch directly to C functions
- Enabled qint_mod * qint_mod (previously NotImplementedError)
- Widened _modulus to int64_t for N up to 2^63-1

## Task Commits

1. **Task 1: C-level modular multiplication** - `66a6904` (feat) - CQ/QQ multiply + controlled variants
2. **Task 2: Python qint_mod rewiring** - `66a6904` (feat) - All operators dispatch to Beauregard C primitives

## Files Created/Modified
- `c_backend/src/ToffoliModReduce.c` - Added toffoli_mod_mul_cq, toffoli_cmod_mul_cq, toffoli_mod_mul_qq, toffoli_cmod_mul_qq
- `c_backend/include/toffoli_arithmetic_ops.h` - Multiplication function declarations
- `src/quantum_language/qint_mod.pyx` - Complete operator rewrite: __add__, __sub__, __mul__, __neg__, __radd__, __rmul__
- `src/quantum_language/qint_mod.pxd` - int64_t _modulus, added _extract_qubits declaration
- `src/quantum_language/_core.pxd` - Added extern declarations for 10 new C modular functions

## Decisions Made
- CQ multiply: precompute a_j = (c * 2^j) mod N for each bit j, do n controlled modular CQ additions
- QQ multiply: compute full 2n-bit product via toffoli_mul_qq, then reduce each product bit using controlled CQ modular addition of (2^k mod N)
- Negation: allocate result at zero, then QQ subtract self from it
- Removed _reduce_mod_c entirely (no longer needed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cython cdef placement error**
- **Found during:** Build after initial rewrite
- **Issue:** cdef variable declarations inside if/elif blocks cause "cdef statement not allowed here"
- **Fix:** Moved all cdef declarations to top of each method
- **Verification:** Build succeeds
- **Committed in:** 66a6904

**2. [Rule 3 - Blocking] Missing pxd declaration for _extract_qubits**
- **Found during:** Build after adding _extract_qubits to .pyx
- **Issue:** Cython requires cdef methods to be declared in .pxd for extension types
- **Fix:** Added `cdef void _extract_qubits(self, unsigned int *qa)` to qint_mod.pxd
- **Verification:** Build succeeds
- **Committed in:** 66a6904

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both were Cython compilation requirements. No scope creep.

## Issues Encountered
- Cython requires all cdef declarations at function top level (not inside control flow blocks)
- Extension type cdef methods must be declared in .pxd file

## Next Phase Readiness
- All modular operations functional, ready for exhaustive verification (Plan 03)
- CQ add/sub/mul and QQ add/sub verified with quick smoke tests

---
*Phase: 92-modular-toffoli-arithmetic*
*Completed: 2026-02-25*
