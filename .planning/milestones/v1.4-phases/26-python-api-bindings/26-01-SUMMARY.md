---
phase: 26-python-api-bindings
plan: 01
subsystem: api
tags: [cython, openqasm, python, export, qiskit]

# Dependency graph
requires:
  - phase: 25-c-backend-openqasm-export
    provides: circuit_to_qasm_string C function for string export
provides:
  - Python API ql.to_openqasm() for OpenQASM 3.0 export
  - Memory-safe Cython wrapper with automatic free() handling
  - Optional Qiskit verification dependency via extras_require
affects: [27-python-qiskit-verification, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cython .pxd/.pyx split for C function wrapping"
    - "try-finally pattern for C memory management in Python"
    - "extras_require for optional dependencies"

key-files:
  created:
    - src/quantum_language/openqasm.pxd
    - src/quantum_language/openqasm.pyx
  modified:
    - src/quantum_language/__init__.py
    - setup.py

key-decisions:
  - "Use try-finally for guaranteed C string cleanup"
  - "Cast circuit pointer via <circuit_t*><unsigned long long> pattern"
  - "Verify circuit initialization before export"
  - "NULL check after C function call to detect failures"

patterns-established:
  - "Pattern 1: Python wrapper calls accessor functions from _core"
  - "Pattern 2: Cast Python int to C pointer using explicit unsigned long long"
  - "Pattern 3: setup.py extras_require for optional verification tools"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 26 Plan 01: OpenQASM Python API Summary

**Memory-safe Python wrapper exposing ql.to_openqasm() with automatic C string cleanup and optional Qiskit verification dependency**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T14:27:20Z
- **Completed:** 2026-01-30T14:29:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created Cython wrapper with try-finally memory safety for C string export
- Exposed to_openqasm() at package level (ql.to_openqasm())
- Added extras_require to setup.py enabling pip install -e .[verification]
- Proper NULL checking and RuntimeError on uninitialized circuit

## Task Commits

Each task was committed atomically:

1. **Task 1: Create openqasm.pxd and openqasm.pyx Cython wrapper** - `1ffe69d` (feat)
2. **Task 2: Wire to_openqasm into package API and add extras_require** - `1a0c59e` (feat)

## Files Created/Modified
- `src/quantum_language/openqasm.pxd` - C declarations for circuit_t and circuit_to_qasm_string
- `src/quantum_language/openqasm.pyx` - Memory-safe to_openqasm() wrapper with try-finally cleanup
- `src/quantum_language/__init__.py` - Import and re-export to_openqasm in public API
- `setup.py` - Added extras_require with verification key containing qiskit>=1.0

## Decisions Made

**Use try-finally for C memory management**
- Ensures free() is called even if decode() or error handling throws
- Prevents memory leaks in all code paths

**Pointer casting pattern: <circuit_t*><unsigned long long>**
- _get_circuit() returns Python int (from C unsigned long long cast)
- Two-step cast required: int → unsigned long long → circuit_t*
- Matches existing pattern in other modules

**Verify circuit initialized before export**
- Call _get_circuit_initialized() first
- Raise RuntimeError with clear message if False
- Prevents NULL dereference in C code

**NULL check after C function call**
- circuit_to_qasm_string can return NULL on failure
- Check before decode() to avoid crash
- Raise RuntimeError with descriptive message

**extras_require for optional verification**
- Qiskit is large dependency (~500MB) not needed for core functionality
- Users install with pip install -e .[verification] when needed
- Enables Phase 27 verification without bloating base install

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly with existing C backend and accessor patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 27 (Qiskit Verification):**
- to_openqasm() API exposed and callable
- extras_require enables Qiskit installation
- Memory-safe C string handling verified

**No blockers or concerns.**

---
*Phase: 26-python-api-bindings*
*Completed: 2026-01-30*
