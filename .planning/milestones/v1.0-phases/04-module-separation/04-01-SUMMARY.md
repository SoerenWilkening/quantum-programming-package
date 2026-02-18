---
phase: 04-module-separation
plan: 01
subsystem: build-system
completed: 2026-01-26
duration: 3 min

requires:
  - 03-03 (Python bindings with allocator integration)

provides:
  - types.h foundation module
  - Clean header dependency hierarchy
  - Zero circular dependencies

affects:
  - 04-02 (Will use types.h as foundation)
  - 04-03 (Will use types.h as foundation)
  - 04-04 (Will use types.h as foundation)

tech-stack:
  added: []
  patterns:
    - Foundation module pattern (types.h with zero dependencies)
    - Backward compatibility wrapper (definition.h)

key-files:
  created:
    - Backend/include/types.h
  modified:
    - Backend/include/gate.h
    - Backend/include/definition.h
    - Backend/include/QPU.h
    - Backend/include/qubit_allocator.h

decisions:
  - id: types-h-foundation
    what: Create types.h as single source of truth for shared types
    why: Eliminates duplicate definitions, establishes clear dependency hierarchy
    impact: All modules now include types.h instead of definition.h
    alternatives: Keep definitions scattered across headers (rejected - causes duplication)

  - id: definition-h-compat
    what: Keep definition.h as backward compatibility wrapper
    why: Existing C files still include definition.h, gradual migration safer
    impact: No immediate changes needed to .c files
    alternatives: Force immediate migration to types.h (rejected - higher risk)

  - id: dependency-comments
    what: Add dependency comment headers to all files
    why: Makes include hierarchy explicit and maintainable
    impact: Clear documentation of which headers depend on what
    alternatives: Rely on implicit understanding (rejected - not sustainable)

tags:
  - c
  - headers
  - module-organization
  - refactoring
---

# Phase 04 Plan 01: Create types.h Foundation Summary

**One-liner:** Extracted all shared types (qubit_t, gate_t, sequence_t) into types.h foundation module with zero dependencies

## Objective Completion

✅ Created types.h as single source of truth for shared types
✅ Reorganized header include chains to use types.h
✅ Eliminated duplicate type definitions across headers
✅ Established clean include hierarchy with no circular dependencies

## What Was Built

### 1. types.h Foundation Module

Created `Backend/include/types.h` containing:
- **Basic types:** qubit_t, layer_t, num_t, decompose_toffoli_t
- **Size constants:** INTEGERSIZE, QBITSIZE, QBYTESIZE, etc.
- **Control constants:** MAXCONTROLS, INVERTED, DECOMPOSETOFFOLI
- **Memory constants:** POINTER, VALUE, Qu, Cl
- **Sequence constants:** MAXLAYERINSEQUENCE, MAXGATESPERLAYER
- **Gate types:** Standardgate_t enum, gate_t struct, sequence_t struct

**Dependency level:** 0 (foundation - no other project headers)

### 2. Updated Header Hierarchy

**gate.h:**
- Now includes only types.h (removed definition.h)
- Removed duplicate type definitions
- Kept only function declarations
- Verified independent compilation

**definition.h:**
- Converted to backward compatibility wrapper
- Simply includes types.h
- Enables gradual migration from old code

**QPU.h:**
- Explicitly includes types.h (in addition to gate.h)
- Clear dependency chain: types.h → gate.h → QPU.h

**qubit_allocator.h:**
- Changed from definition.h to types.h
- Direct dependency on foundation module

### 3. Added Dependency Documentation

All headers now have comment headers documenting:
- Module purpose
- Explicit dependencies
- Position in include hierarchy

## Technical Details

### Include Hierarchy

```
types.h (foundation - no dependencies)
  ↑
  ├── gate.h (gate operations)
  ├── qubit_allocator.h (memory management)
  └── definition.h (backward compat)
       ↑
       └── QPU.h (circuit management)
```

### Verification Steps Taken

1. ✅ Compiled types.h independently
2. ✅ Compiled gate.h independently
3. ✅ Compiled qubit_allocator.h independently
4. ✅ Built Cython extension successfully
5. ✅ All 59 characterization tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Testing

All 59 characterization tests pass:
- 18 circuit generation tests
- 23 qbool operation tests
- 18 qint operation tests

No test changes required - refactoring was transparent.

## Commits

| Task | Commit | Description | Files |
|------|--------|-------------|-------|
| 1 | 508f781 | Create types.h with shared types | Backend/include/types.h |
| 2 | 1dfd93a | Update gate.h to use types.h | Backend/include/gate.h |
| 3 | 8b8227c | Update headers to use types.h | definition.h, QPU.h, qubit_allocator.h |

## Decisions Made

### DEC-01: types.h as Foundation Module

**Decision:** Create types.h with zero dependencies containing all shared types

**Rationale:**
- Eliminates duplicate definitions across gate.h and definition.h
- Provides single source of truth for type definitions
- Enables clear dependency hierarchy
- Foundation modules simplify future refactoring

**Impact:**
- All modules now include types.h
- Clear separation between types (types.h) and operations (gate.h, QPU.h)
- Easier to add new shared types in future

### DEC-02: Keep definition.h as Compatibility Wrapper

**Decision:** Preserve definition.h as backward compatibility wrapper instead of forcing immediate migration

**Rationale:**
- Many .c files currently include definition.h
- Gradual migration reduces risk
- Wrapper pattern costs nothing (just one include)
- Can migrate .c files in later phases if needed

**Impact:**
- No changes needed to existing .c files
- definition.h now just includes types.h
- Future code should include types.h directly

### DEC-03: Dependency Comments in Headers

**Decision:** Add comment headers documenting dependencies to all headers

**Rationale:**
- Makes include hierarchy explicit
- Helps future developers understand module structure
- Documents design intent
- Prevents accidental circular dependencies

**Impact:**
- All headers now have "Dependencies:" comment
- Easier to understand module relationships
- Self-documenting codebase

## Next Phase Readiness

### Enables

- **04-02:** Can now separate QPU state management (types.h provides foundation)
- **04-03:** Can now separate gate operations (types.h provides gate_t definition)
- **04-04:** Can now create unified allocator API (types.h provides qubit_t definition)

### Concerns/Blockers

None identified.

### Recommendations

1. **Future .c file changes:** When modifying .c files, prefer including types.h directly instead of definition.h
2. **New modules:** Always include types.h as first dependency
3. **Documentation:** Continue adding dependency comments to new headers

## Key Learnings

### What Worked Well

1. **Foundation module pattern:** Having a zero-dependency types.h makes header hierarchy clean
2. **Backward compatibility wrapper:** Kept existing code working while improving structure
3. **Independent compilation testing:** Verified each header compiles alone, catching dependency issues
4. **Pre-commit formatting:** Auto-formatted C headers consistently

### What Could Be Improved

1. **Virtual environment:** Still has broken symlinks to macOS paths (pre-existing issue)
2. **Compiler warnings:** Pre-existing warnings in LogicOperations.c, Integer.c (not introduced by this change)

## Files Modified

### Created
- `Backend/include/types.h` (84 lines) - Foundation module with all shared types

### Modified
- `Backend/include/gate.h` - Removed 26 lines (type definitions), added types.h include
- `Backend/include/definition.h` - Removed 35 lines (type definitions), now compat wrapper
- `Backend/include/QPU.h` - Added explicit types.h include
- `Backend/include/qubit_allocator.h` - Changed from definition.h to types.h

**Total:** +84 lines created, ~90 lines removed from other headers
**Net change:** -6 lines (more focused headers)

## Success Criteria Met

✅ types.h is the single source of truth for shared types
✅ No type definitions are duplicated across headers
✅ Include chains are clean (no circular dependencies)
✅ All tests pass without modification

## Phase Progress

Phase 04 Plan 01 of 04 complete - Module separation foundation established.
