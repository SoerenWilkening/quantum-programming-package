---
phase: 04-module-separation
plan: 02
subsystem: optimizer
completed: 2026-01-26
duration: 5 min

requires:
  - 04-01 (types.h foundation module)
  - 03-03 (Python bindings with allocator integration)

provides:
  - optimizer.c module with gate optimization logic
  - Clean separation of gate optimization from circuit management
  - Reduced QPU.c from god object to minimal state holder

affects:
  - 04-03 (Will use separated module structure)
  - 04-04 (Will complete module separation)

tech-stack:
  added: []
  patterns:
    - Module separation pattern (optimizer.c extracted from QPU.c)
    - Forward declaration pattern (circuit_s for cross-module types)
    - Scope-limited globals (instruction state only for sequence generation)

key-files:
  created:
    - Backend/include/optimizer.h
    - Backend/src/optimizer.c
  modified:
    - Backend/include/QPU.h
    - Backend/src/QPU.c
    - Backend/src/Integer.c
    - python-backend/setup.py

decisions:
  - id: optimizer-module-extraction
    what: Extract all gate optimization logic into dedicated optimizer.c module
    why: Split QPU.c god object (~200 lines) into focused modules
    impact: Clear separation of concerns, easier to maintain and test
    alternatives: Keep in QPU.c (rejected - maintains god object anti-pattern)

  - id: instruction-state-scope
    what: Keep instruction_list/QPU_state/instruction_counter globals but scope to sequence generation
    why: CQ_add/CC_mul functions in IntegerAddition.c etc. require these globals
    impact: Globals remain but with clear documented scope and future refactoring path
    alternatives: Refactor all sequence generation functions (rejected - out of scope for this plan)

  - id: setting-seq-removal
    what: Remove setting_seq() function from Integer.c
    why: Used QPU_state global, never called from Python bindings
    impact: One less dead code path, cleaner codebase
    alternatives: Keep dead code (rejected - violates cleanup objectives)

  - id: circuit-typedef-fix
    what: Change circuit_t typedef from anonymous struct to struct circuit_s
    why: Matches forward declaration in optimizer.h, prevents typedef conflicts
    impact: Consistent type system across modules
    alternatives: Use different names (rejected - inconsistent)

tags:
  - c
  - module-separation
  - refactoring
  - optimizer
---

# Phase 04 Plan 02: Extract Optimizer Module Summary

**One-liner:** Extracted gate optimization logic from QPU.c into dedicated optimizer.c module, reducing QPU.c from 201 lines to 18 lines while maintaining all functionality

## Objective Completion

✅ Created optimizer.c/optimizer.h module with gate optimization logic
✅ Eliminated QPU.c god object anti-pattern (201 → 18 lines)
✅ All 59 characterization tests pass without modification
✅ add_gate function works exactly as before (same signature, same behavior)

## What Was Built

### 1. Optimizer Module

**Backend/include/optimizer.h:**
- Gate optimization API declarations
- Forward declaration for circuit_t
- 7 functions: add_gate, minimum_layer, smallest_layer_below_comp, merge_gates, colliding_gates, apply_layer, append_gate
- Compiles independently (verified)

**Backend/src/optimizer.c (208 lines):**
- Complete implementation of layer assignment algorithm
- Gate merging (inverse gate cancellation) logic
- Collision detection between gates
- All logic previously in QPU.c

### 2. QPU.c Reduction

**Before:** 201 lines
- 7 gate optimization functions
- Global instruction state
- Mixed responsibilities

**After:** 18 lines
- Only global instruction state declarations
- Clear comments documenting scope
- No function implementations

**Reduction:** 91% code removal from QPU.c

### 3. Build System Integration

**python-backend/setup.py:**
- Added optimizer.c to sources_circuit list
- Placed after QPU.c in compilation order
- Successful Cython extension build

**Backend/include/QPU.h:**
- Added optimizer.h include for backward compatibility
- Fixed circuit_t typedef to match forward declaration (struct circuit_s)
- Restored instruction state globals with scope documentation

## Technical Details

### Module Extraction Pattern

```
BEFORE (QPU.c - 201 lines):
├── Global instruction state (3 variables)
├── smallest_layer_below_comp() (13 lines)
├── minimum_layer() (17 lines)
├── merge_gates() (41 lines)
├── apply_layer() (17 lines)
├── append_gate() (15 lines)
├── colliding_gates() (28 lines)
└── add_gate() (54 lines)

AFTER:
optimizer.c (208 lines):
├── All 7 functions moved
└── Complete optimization logic

QPU.c (18 lines):
├── Global instruction state only
└── Documentation comments
```

### Forward Declaration Pattern

**optimizer.h uses forward declaration:**
```c
struct circuit_s;
typedef struct circuit_s circuit_t;
```

**QPU.h defines full struct:**
```c
typedef struct circuit_s {
    // ... full definition
} circuit_t;
```

This pattern allows optimizer.h to compile independently while QPU.h provides the full definition.

### Instruction State Scope

The `instruction_list`, `QPU_state`, and `instruction_counter` globals were initially targeted for elimination but are required by:
- `CQ_add()` in IntegerAddition.c
- `CC_mul()` in IntegerMultiplication.c
- Similar functions in IntegerComparison.c, LogicOperations.c

These functions generate gate sequences from classical inputs and use the instruction state. They are **not related** to the gate optimization logic moved to optimizer.c.

**Documentation added:** TODO(Phase 5+) to refactor sequence generation API to accept parameters instead of using globals.

## Deviations from Plan

### 1. [Rule 3 - Blocking] Instruction State Globals Retained

**Found during:** Task 2 (Eliminate global state)
**Issue:** Removing instruction_list/QPU_state/instruction_counter broke compilation of IntegerAddition.c, IntegerMultiplication.c, IntegerComparison.c, LogicOperations.c
**Root cause:** These files have sequence generation functions (CQ_add, CC_mul, etc.) that use QPU_state global
**Fix:** Restored globals in QPU.h/QPU.c with clear scope documentation
**Files affected:** Backend/include/QPU.h, Backend/src/QPU.c
**Commit:** c5cad47

**Why this deviation was necessary:**
- Sequence generation functions are called from Python bindings (verified in quantum_language.pyx)
- Refactoring these functions to accept circuit_t* parameter is out of scope for 04-02
- Globals are now scoped to sequence generation only, not gate optimization
- Future work clearly documented with TODO comments

### 2. [Rule 3 - Blocking] circuit_t Typedef Conflict

**Found during:** Task 3 (Build system update)
**Issue:** Compilation error: conflicting types for 'circuit_t'
**Root cause:** QPU.h used `typedef struct { ... } circuit_t;` (anonymous struct) while optimizer.h used `typedef struct circuit_s circuit_t;` (forward declaration)
**Fix:** Changed QPU.h to use named struct: `typedef struct circuit_s { ... } circuit_t;`
**Files affected:** Backend/include/QPU.h
**Commit:** c5cad47

## Testing

### Build Verification
✅ optimizer.h compiles independently
✅ Cython extension builds successfully
✅ No compilation errors or warnings (except pre-existing LogicOperations.c warning)

### Smoke Test
✅ `qint()` creation works (uses add_gate internally)
✅ Circuit has correct layer count
✅ No runtime errors

### Full Test Suite
✅ All 59 characterization tests pass
- 18 circuit generation tests
- 23 qbool operation tests
- 18 qint operation tests

### Regression Detection
✅ No test modifications required
✅ Behavior unchanged (tests capture current behavior as golden master)
✅ Gate optimization still works identically

## Architecture Impact

### Before (Phase 03)
```
QPU.c (god object):
├── Circuit allocation
├── Gate optimization
├── Circuit output
└── Instruction state
```

### After (Phase 04-02)
```
circuit_allocations.c:
└── Circuit memory management

optimizer.c:
└── Gate optimization (NEW)

ciruict_outputs.c:
└── Circuit output/printing

QPU.c (minimal):
└── Instruction state only
```

### Dependencies
```
optimizer.h (depends on: types.h)
    ↓
QPU.h (depends on: types.h, gate.h, optimizer.h, qubit_allocator.h)
    ↓
[All C files]
```

## Next Phase Readiness

**Phase 4 Progress:** 2 of 4 plans complete (50%)

**04-03 (Next):** Further module separation
- Can now build on clean optimizer.c foundation
- Module pattern established for other extractions

**04-04 (Final):** Complete module reorganization
- All modules cleanly separated
- Clear dependency hierarchy

**Blockers:** None
**Concerns:** None
**Dependencies satisfied:** Yes (04-01 complete)

## Performance

**Build time:** ~10 seconds (Cython extension compilation)
**Test time:** 0.19 seconds (59 tests)
**Execution time:** 5 minutes (3 tasks, 3 commits)

## Files Changed

**Created (2):**
- Backend/include/optimizer.h (38 lines)
- Backend/src/optimizer.c (208 lines)

**Modified (4):**
- Backend/include/QPU.h (added optimizer.h include, fixed circuit_t typedef, restored globals with docs)
- Backend/src/QPU.c (reduced from 201 to 18 lines)
- Backend/src/Integer.c (removed setting_seq() dead code)
- python-backend/setup.py (added optimizer.c to sources)

**Net change:** +246 lines created, -249 lines removed from other files

## Commits

1. **52cf26a** - feat(04-02): create optimizer module with layer assignment and gate merging
2. **60a76c6** - refactor(04-02): eliminate global state and clean up QPU.c
3. **c5cad47** - fix(04-02): restore instruction state for sequence generation functions
