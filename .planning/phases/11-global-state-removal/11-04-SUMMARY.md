---
phase: 11-global-state-removal
plan: 04
subsystem: backend-infrastructure
tags: [c, refactoring, global-state, cleanup]
requires: [11-01, 11-02, 11-03]
provides: [global-state-free-backend, qpu-cleanup]
affects: [future-backend-development]
tech-stack:
  added: []
  patterns: [explicit-parameters, stateless-architecture]
decisions:
  - id: DEC-11-04-01
    what: "Removed deprecated QPU_state wrapper functions (P_add, cP_add, CQ_equal, cCQ_equal)"
    why: "Functions still referenced QPU_state which was being removed, blocking compilation"
    impact: "Callers must use parameterized versions (_param suffix or _width suffix)"
  - id: DEC-11-04-02
    what: "Added M_PI definition to Integer.h and gate.h"
    why: "M_PI availability varies across platforms and compilers"
    impact: "Portable compilation on all platforms without math constant issues"
key-files:
  created: []
  modified:
    - Backend/src/QPU.c
    - Backend/include/QPU.h
    - Execution/src/execution.c
    - main.c
    - Backend/src/IntegerAddition.c
    - Backend/include/arithmetic_ops.h
    - Backend/src/IntegerComparison.c
    - Backend/include/comparison_ops.h
    - Backend/include/Integer.h
    - Backend/include/gate.h
metrics:
  duration: 340s
  completed: 2026-01-27
---

# Phase 11 Plan 04: Global State Infrastructure Removal Summary

**One-liner:** Removed QPU_state, instruction_list, instruction_t type, and all deprecated wrappers from C backend - achieving completely stateless architecture

## What Was Delivered

### Global State Elimination

1. **QPU.c cleaned up**
   - Removed `instruction_list[MAXINSTRUCTIONS]` array
   - Removed `QPU_state` pointer
   - Removed `instruction_counter` variable
   - Replaced with backward-compatibility comment

2. **QPU.h simplified**
   - Removed `instruction_t` type definition (Q0-Q3, R0-R3 registers)
   - Removed extern declarations for global state
   - Converted to thin wrapper around circuit.h
   - Documents legacy removal for future developers

3. **execution.c streamlined**
   - Removed `qubit_mapping()` function (depended on QPU_state->Q0/Q1/Q2/Q3)
   - Removed `execute()` function (depended on QPU_state)
   - Kept `run_instruction()` - takes explicit qubit_array parameter
   - Python layer already passes qubit arrays directly

4. **main.c refactored**
   - Removed QPU_state initialization
   - Removed instruction_counter usage
   - Initialize qubit arrays directly: `qubit_array[i] = i`
   - Calls run_instruction() with explicit parameters
   - Fixed uninitialized variable warning

### Deprecated Function Removal

Removed deprecated wrappers that still used QPU_state (blocking compilation):

1. **P_add() and cP_add()** - Phase gate wrappers
   - Used QPU_state->R0 for phase value
   - Callers must use P_add_param(phase_value) instead

2. **CQ_equal() and cCQ_equal()** - Comparison wrappers
   - Used QPU_state->R0 for classical value
   - Callers must use CQ_equal_width(bits, value) instead

### Portability Improvements

Added M_PI definitions to Integer.h and gate.h for cross-platform compatibility.

## Decisions Made

### DEC-11-04-01: Remove Deprecated Wrappers

**Decision:** Remove P_add(), cP_add(), CQ_equal(), cCQ_equal() instead of attempting to refactor them

**Rationale:**
- QPU_state being removed made these functions uncompilable
- Parameterized versions already exist (_param, _width suffixes)
- No callers found in codebase (only declarations)
- Deviation Rule 3 (auto-fix blocking issues) applies

**Alternatives Considered:**
- Keep wrappers with default values: Would perpetuate anti-pattern
- Add dummy QPU_state just for these: Defeats purpose of cleanup

**Impact:** Callers (if any exist outside main tree) must migrate to parameterized APIs

### DEC-11-04-02: Portable M_PI Definition

**Decision:** Add `#define M_PI` with fallback to Integer.h and gate.h

**Rationale:**
- M_PI not guaranteed by C standard (POSIX extension)
- Compilation failed on test system without _USE_MATH_DEFINES
- Critical for phase gate calculations
- Deviation Rule 3 (auto-fix blocking issues)

**Impact:** Code compiles portably across all platforms

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed deprecated QPU_state wrapper functions**

- **Found during:** Task 4 compilation
- **Issue:** P_add(), cP_add(), CQ_equal(), cCQ_equal() still used QPU_state which was being removed. Compilation failed with "QPU_state undeclared" errors.
- **Fix:** Removed all four deprecated wrapper functions from source and headers. Added migration comments pointing to parameterized alternatives.
- **Files modified:** Backend/src/IntegerAddition.c, Backend/include/arithmetic_ops.h, Backend/src/IntegerComparison.c, Backend/include/comparison_ops.h
- **Commits:** 416b9bd
- **Why automatic:** Blocking issue preventing task completion (Rule 3). Functions had parameterized replacements already available.

**2. [Rule 3 - Blocking] Added M_PI definition for portability**

- **Found during:** Task 4 compilation
- **Issue:** Compilation failed with "M_PI undeclared" errors in IntegerAddition.c and gate.c on test system
- **Fix:** Added `#define _USE_MATH_DEFINES` and fallback `#define M_PI 3.14159265358979323846` to Integer.h and gate.h
- **Files modified:** Backend/include/Integer.h, Backend/include/gate.h
- **Commits:** 416b9bd
- **Why automatic:** Blocking issue preventing compilation (Rule 3). Standard portability fix for missing math constants.

**3. [Rule 1 - Bug] Fixed uninitialized variable warning**

- **Found during:** Task 4 verification
- **Issue:** main.c had `sequence_t *seq;` uninitialized, causing compiler warning and potential undefined behavior if run=0 path taken
- **Fix:** Initialize to NULL, add null check before free()
- **Files modified:** main.c
- **Commits:** 416b9bd
- **Why automatic:** Bug fix (Rule 1) - uninitialized pointer could cause crash

## Implementation Notes

### Architecture Impact

The C backend is now completely stateless:
- No global variables for instruction storage
- All functions take explicit parameters
- Circuit state managed through circuit_t* passed explicitly
- Quantum register state through qubit arrays passed explicitly

### Migration Path

Old code using removed functions:
```c
// Old (removed)
QPU_state->R0 = &phase_value;
seq = P_add();

// New
seq = P_add_param(phase_value);
```

```c
// Old (removed)
QPU_state->R0 = &classical_value;
seq = CQ_equal();

// New
seq = CQ_equal_width(bits, classical_value);
```

### Python Layer Unaffected

Python bindings already passed parameters explicitly:
- Never used qubit_mapping() or execute()
- Always called run_instruction() with explicit qubit arrays
- No changes needed to Python layer

## Testing Results

- Full C backend compiles without errors
- No remaining QPU_state references (verified via grep)
- No remaining instruction_list references
- No remaining instruction_t type usage
- Test binary (main.c) runs successfully
- Circuit output generated correctly

## Next Phase Readiness

**Phase 11-05 can proceed immediately:**
- Global state completely eliminated
- All functions use explicit parameters
- Test infrastructure working
- No blockers or concerns

**For future development:**
- New functions should never use global state
- All functions should take explicit parameters
- QPU.h exists only for backward compatibility
- Use circuit.h for new code

## Metrics

- **Tasks completed:** 4/4
- **Commits:** 4 atomic commits
- **Files modified:** 10
- **Lines removed:** 360+
- **Lines added:** 50
- **Duration:** 340 seconds (5.7 minutes)
- **Deviations:** 3 (all Rule 1 or Rule 3 - automatic fixes)
