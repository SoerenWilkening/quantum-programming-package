---
phase: 04-module-separation
plan: 03
subsystem: build-system
completed: 2026-01-26
duration: 4 min

requires:
  - 04-01 (types.h foundation module)
  - 04-02 (optimizer.c module extraction)

provides:
  - circuit.h as main public API header
  - circuit_output.h/c for visualization and export
  - Fixed filename typo (ciruict -> circuit)

affects:
  - 04-04 (Will use circuit.h as main header)
  - Future development (circuit.h is now the recommended include)

tech-stack:
  added: []
  patterns:
    - Main API header pattern (circuit.h consolidates all modules)
    - Backward compatibility wrapper (QPU.h includes circuit.h)
    - Module separation (circuit_output.h/c for printing/QASM)

key-files:
  created:
    - Backend/include/circuit.h
    - Backend/include/circuit_output.h
  modified:
    - Backend/src/circuit_output.c (renamed from ciruict_outputs.c)
    - Backend/include/QPU.h (now wrapper)
    - python-backend/setup.py

decisions:
  - id: circuit-h-main-api
    what: Create circuit.h as primary user-facing header
    why: Users should include one header for full API, not hunt for individual modules
    impact: circuit.h includes types, gates, optimizer, output, allocator
    alternatives: Force users to include each module separately (rejected - poor UX)

  - id: qpu-h-backward-compat
    what: Keep QPU.h as thin wrapper including circuit.h
    why: Existing code includes QPU.h, preserve compatibility while improving structure
    impact: QPU.h just includes circuit.h plus instruction_t definition
    alternatives: Delete QPU.h entirely (rejected - breaks existing code)

  - id: circuit-output-module
    what: Separate circuit printing/QASM export into dedicated module
    why: Output functionality is distinct from core circuit operations
    impact: circuit_output.h/c contains visualization logic
    alternatives: Keep in QPU.c (rejected - violates single responsibility)

  - id: fix-filename-typo
    what: Rename ciruict_outputs.c to circuit_output.c
    why: Typo in filename makes project look unprofessional
    impact: Consistent naming across codebase
    alternatives: Leave typo (rejected - technical debt)

tags:
  - c
  - headers
  - module-organization
  - refactoring
  - api-design
---

# Phase 04 Plan 03: Create Main API Header Summary

**One-liner:** Established circuit.h as main public API header, separated circuit_output module, fixed filename typo

## Objective Completion

✅ Created circuit.h as the main public API header
✅ Created circuit_output.h for visualization/export functions
✅ Renamed ciruict_outputs.c to circuit_output.c (fixed typo)
✅ Updated QPU.h to be a thin backward compatibility wrapper
✅ Updated build system (setup.py) with corrected filename
✅ All 59 tests pass

## What Was Built

### 1. circuit_output.h Module

Created `Backend/include/circuit_output.h` containing:
- **print_circuit()** - Text-based circuit visualization with ASCII art
- **circuit_to_opanqasm()** - OpenQASM 3.0 export functionality
- Forward-declares circuit_t to avoid circular dependencies
- Clean separation of output concerns from core circuit logic

**Dependency level:** Depends on types.h only (foundation module)

### 2. circuit_output.c Implementation

Renamed from `Backend/src/ciruict_outputs.c` (fixing typo):
- Updated header includes to use circuit_output.h
- Added dependency documentation comments
- Kept all existing functionality (print_circuit, circuit_to_opanqasm, helpers)
- No functional changes, purely structural improvement

### 3. circuit.h Main API Header

Created `Backend/include/circuit.h` as the primary user-facing header:
- **Consolidates all circuit functionality** in one include
- Includes: types.h, gate.h, qubit_allocator.h, optimizer.h, circuit_output.h
- Contains circuit_t struct definition (moved from QPU.h)
- Contains quantum_int_t struct definition
- Declares circuit lifecycle functions (init_circuit, free_circuit)
- Declares memory allocation functions (allocate_more_*)
- Documents module organization clearly in header comments

**Module organization documented:**
```
types.h         - Core types (qubit_t, gate_t, circuit_t, etc.)
gate.h          - Gate creation functions (x, cx, h, p, etc.)
optimizer.h     - Gate placement and optimization (add_gate)
circuit_output.h - Visualization and export
qubit_allocator.h - Qubit lifecycle management
```

### 4. Updated QPU.h as Backward Compatibility Wrapper

Transformed `Backend/include/QPU.h`:
- Now simply includes circuit.h
- Retains instruction_t type for sequence generation (CQ_add/CC_mul functions)
- Retains global instruction state (instruction_list, QPU_state)
- Removed duplicate circuit_t, quantum_int_t definitions (now in circuit.h)
- Removed duplicate function declarations (now in circuit.h)
- Reduced from 103 lines to 41 lines

**Backward compatibility preserved:**
- Existing code including QPU.h continues to work
- New code should prefer circuit.h directly

### 5. Updated Build System

Modified `python-backend/setup.py`:
- Changed `ciruict_outputs.c` → `circuit_output.c` in sources list
- Build succeeds with corrected filename
- All 59 characterization tests pass

## Technical Details

### Module Hierarchy

```
circuit.h (main API header)
  ↓ includes
  ├── types.h (foundation)
  ├── gate.h (gate operations)
  ├── qubit_allocator.h (memory management)
  ├── optimizer.h (gate placement)
  └── circuit_output.h (visualization/export)

QPU.h (backward compat wrapper)
  ↓ includes
  └── circuit.h (full API)
```

### User Experience

**Before (Phase 03):**
```c
#include "QPU.h"  // Unclear what this provides
```

**After (Phase 04-03):**
```c
#include "circuit.h"  // Clear: this is the circuit API
```

**Documentation in circuit.h:**
Users can read the header to understand module organization without reading docs.

### Verification Steps Taken

1. ✅ Created circuit_output.h with function declarations
2. ✅ Renamed ciruict_outputs.c → circuit_output.c via git mv
3. ✅ Updated circuit_output.c includes
4. ✅ Created circuit.h with full API consolidation
5. ✅ Updated QPU.h to wrapper pattern
6. ✅ Updated setup.py with corrected filename
7. ✅ Built Cython extension successfully
8. ✅ All 59 characterization tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Testing

All 59 characterization tests pass:
- 18 circuit generation tests
- 23 qbool operation tests
- 18 qint operation tests

No test changes required - refactoring was transparent to Python interface.

Build warnings (pre-existing, not introduced):
- optimizer.c: unused variable 'delta' (pre-existing)
- execution.c: signedness comparison warnings (pre-existing)
- LogicOperations.c: memset overflow warning (pre-existing)

## Commits

| Task | Commit  | Description                                    | Files                                          |
| ---- | ------- | ---------------------------------------------- | ---------------------------------------------- |
| 1    | 2b97bee | Create circuit_output.h header                 | Backend/include/circuit_output.h               |
| 2    | 9103da9 | Rename ciruict_outputs.c to circuit_output.c   | Backend/src/circuit_output.c                   |
| 3    | 924d3db | Create circuit.h as main public API header     | Backend/include/circuit.h                      |
| 4    | da81e97 | Update build system and make QPU.h a wrapper   | python-backend/setup.py, Backend/include/QPU.h |

## Decisions Made

### DEC-01: circuit.h as Main API Header

**Decision:** Create circuit.h that includes all circuit functionality modules

**Rationale:**
- Users shouldn't need to hunt for which headers to include
- Single include point improves discoverability
- Clear module organization documented in header comments
- Modern API design pattern (e.g., React.h, Eigen/Dense)

**Impact:**
- circuit.h is now the recommended include for all users
- Contains circuit_t and quantum_int_t definitions
- Includes all necessary sub-modules automatically
- Self-documenting through header comments

### DEC-02: QPU.h as Backward Compatibility Wrapper

**Decision:** Keep QPU.h but make it a thin wrapper that includes circuit.h

**Rationale:**
- Many existing .c files include QPU.h
- Gradual migration safer than forced breaking change
- Wrapper pattern costs essentially nothing
- Preserves instruction_t and sequence generation globals

**Impact:**
- Existing code continues to work
- QPU.h reduced from 103 to 41 lines
- Future code should prefer circuit.h
- Can deprecate QPU.h in later phase if desired

### DEC-03: Separate circuit_output Module

**Decision:** Extract printing and QASM export into dedicated circuit_output.h/c module

**Rationale:**
- Output functionality is distinct from core circuit operations
- Follows single responsibility principle
- Makes dependencies explicit (only needs types.h)
- Easier to test and maintain separately

**Impact:**
- circuit_output.h declares print_circuit and circuit_to_opanqasm
- circuit_output.c contains implementation (renamed from ciruict_outputs.c)
- Clear module boundary

### DEC-04: Fix Filename Typo

**Decision:** Rename ciruict_outputs.c → circuit_output.c via git mv

**Rationale:**
- Typo ("ciruict" instead of "circuit") makes project look unprofessional
- Easy fix with git mv preserves history
- Naming consistency improves maintainability
- Now matches module name (circuit_output)

**Impact:**
- Filename is now correct: circuit_output.c
- setup.py updated with corrected filename
- Git history preserved through rename

## Next Phase Readiness

### Enables

- **04-04:** Can now use circuit.h as the standard header for unified allocator API
- **Future development:** Clear module structure makes adding new features easier
- **Documentation:** circuit.h serves as self-documenting API reference

### Concerns/Blockers

None identified.

### Recommendations

1. **New code:** Always include circuit.h instead of QPU.h
2. **Documentation:** Update any external docs to reference circuit.h
3. **Future cleanup:** Consider deprecating QPU.h in Phase 5+ if no longer needed
4. **Module additions:** Follow same pattern - create dedicated header, include in circuit.h

## Key Learnings

### What Worked Well

1. **Main API header pattern:** circuit.h provides one-stop include for users
2. **Backward compatibility wrapper:** QPU.h preserved without duplicating definitions
3. **Git mv for rename:** Preserved file history while fixing typo
4. **Module separation:** circuit_output.h/c is cleanly separated
5. **Pre-commit hooks:** Auto-formatted headers consistently

### What Could Be Improved

1. **Pre-existing warnings:** LogicOperations.c, execution.c have build warnings (not introduced by this phase)
2. **instruction_t placement:** Currently in QPU.h, might benefit from dedicated sequence.h in future

## Files Modified

### Created
- `Backend/include/circuit.h` (90 lines) - Main public API header
- `Backend/include/circuit_output.h` (27 lines) - Output function declarations

### Renamed
- `Backend/src/ciruict_outputs.c` → `Backend/src/circuit_output.c` (222 lines) - Fixed typo

### Modified
- `Backend/include/QPU.h` - Reduced from 103 to 41 lines (now wrapper)
- `python-backend/setup.py` - Updated source filename

**Total:** +117 lines created (circuit.h + circuit_output.h), -62 lines in QPU.h
**Net change:** +55 lines (better organization with slightly more documentation)

## Success Criteria Met

✅ circuit.h is the recommended single include for users
✅ File naming is consistent (circuit_output.c, not ciruict_outputs.c)
✅ Module dependencies are clearly documented in header comments
✅ Tests pass without modification
✅ Backward compatibility preserved (QPU.h still works)

## Phase Progress

Phase 04 Plan 03 of 04 complete - Main API header established with clean module organization.
