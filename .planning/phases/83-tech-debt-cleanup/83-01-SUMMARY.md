---
phase: 83-tech-debt-cleanup
plan: 01
subsystem: infra
tags: [c-backend, cython, build-system, pre-commit, preprocessor]

# Dependency graph
requires:
  - phase: 11-global-state-removal
    provides: "circuit.h API that replaced QPU_state"
provides:
  - "QPU.h/QPU.c dead code fully removed from repository"
  - "All C/Cython includes migrated to circuit.h"
  - "Pre-commit hook for preprocessor drift detection"
affects: [build-system, c-backend, cython-bindings]

# Tech tracking
tech-stack:
  added: []
  patterns: ["pre-commit hook auto-fix pattern (regenerate-and-stage)"]

key-files:
  created: []
  modified:
    - "c_backend/src/Integer.c"
    - "c_backend/src/IntegerComparison.c"
    - "c_backend/src/circuit_allocations.c"
    - "c_backend/src/circuit_output.c"
    - "c_backend/src/qubit_allocator.c"
    - "c_backend/src/optimizer.c"
    - "c_backend/src/ToffoliMultiplication.c"
    - "c_backend/include/Integer.h"
    - "c_backend/include/LogicOperations.h"
    - "c_backend/include/execution.h"
    - "c_backend/include/hot_path_add.h"
    - "c_backend/include/hot_path_mul.h"
    - "c_backend/include/hot_path_xor.h"
    - "c_backend/include/toffoli_arithmetic_ops.h"
    - "src/quantum_language/_core.pxd"
    - "src/quantum_language/openqasm.pxd"
    - "src/quantum_language/_core.pyx"
    - "setup.py"
    - "CMakeLists.txt"
    - "tests/c/Makefile"
    - "main.c"
    - "c_backend/src/execution.c"
    - "build_preprocessor.py"
    - ".pre-commit-config.yaml"

key-decisions:
  - "Used git add -f in sync-and-stage hook since preprocessed .pyx files are in .gitignore"
  - "Used python3 in hook entry (system only has python3, not python)"
  - "Pre-commit hook always returns 0 after auto-fixing (auto-fix pattern, not blocking pattern)"

patterns-established:
  - "Pre-commit auto-fix hook: regenerate derived files and auto-stage with git add -f"

requirements-completed: [DEBT-01, DEBT-02]

# Metrics
duration: 49min
completed: 2026-02-23
---

# Phase 83 Plan 01: Remove QPU Dead Code and Add Preprocessor Drift Hook Summary

**Deleted QPU.c/QPU.h backward-compatibility shims, migrated 14+ files to circuit.h, cleaned build configs, and installed pre-commit hook for qint_preprocessed.pyx drift detection**

## Performance

- **Duration:** 49 min
- **Started:** 2026-02-23T15:33:44Z
- **Completed:** 2026-02-23T16:22:43Z
- **Tasks:** 2
- **Files modified:** 28

## Accomplishments
- Deleted QPU.c and QPU.h entirely from the repository (dead backward-compatibility stubs since Phase 11)
- Replaced `#include "QPU.h"` with `#include "circuit.h"` in all 14 C source/header files
- Updated Cython .pxd declarations and build configs (setup.py, CMakeLists.txt, tests/c/Makefile) to remove all QPU references
- Added `--sync-and-stage` mode to build_preprocessor.py for pre-commit hook auto-fix
- Fixed `--check` mode to actually compare content (was identical to default mode)
- Registered `sync-preprocessed-pyx` local hook in .pre-commit-config.yaml
- Cleaned up all QPU-related comments across the entire C backend (zero QPU references remain)

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove QPU.c/QPU.h and migrate all references to circuit.h** - `c5918c5` (feat)
2. **Task 2: Add pre-commit hook for preprocessor drift detection** - `a84b141` (feat)

**Plan metadata:** [final docs commit hash] (docs: complete plan)

## Files Created/Modified
- `c_backend/include/QPU.h` - DELETED (backward-compat header)
- `c_backend/src/QPU.c` - DELETED (backward-compat source)
- `c_backend/src/Integer.c` - QPU.h -> circuit.h include migration
- `c_backend/src/IntegerComparison.c` - QPU.h -> circuit.h include migration
- `c_backend/src/circuit_allocations.c` - QPU.h -> circuit.h include migration
- `c_backend/src/circuit_output.c` - QPU.h -> circuit.h include migration
- `c_backend/src/qubit_allocator.c` - QPU.h -> circuit.h include migration
- `c_backend/src/optimizer.c` - QPU.h -> circuit.h include migration
- `c_backend/src/ToffoliMultiplication.c` - QPU.h -> circuit.h include migration
- `c_backend/src/execution.c` - QPU comment cleanup
- `c_backend/src/IntegerAddition.c` - QPU comment cleanup
- `c_backend/src/LogicOperations.c` - QPU comment cleanup
- `c_backend/include/Integer.h` - QPU.h -> circuit.h include migration
- `c_backend/include/LogicOperations.h` - QPU.h -> circuit.h include migration
- `c_backend/include/execution.h` - QPU.h -> circuit.h include migration
- `c_backend/include/hot_path_add.h` - QPU.h -> circuit.h include migration
- `c_backend/include/hot_path_mul.h` - QPU.h -> circuit.h include migration
- `c_backend/include/hot_path_xor.h` - QPU.h -> circuit.h include migration
- `c_backend/include/toffoli_arithmetic_ops.h` - QPU.h -> circuit.h include migration
- `c_backend/include/arithmetic_ops.h` - QPU comment cleanup
- `c_backend/include/comparison_ops.h` - QPU comment cleanup
- `src/quantum_language/_core.pxd` - QPU.h -> circuit.h extern declaration
- `src/quantum_language/openqasm.pxd` - QPU.h -> circuit.h extern declaration
- `src/quantum_language/_core.pyx` - QPU comment cleanup
- `setup.py` - Removed QPU.c from c_sources list
- `CMakeLists.txt` - Removed QPU.c from source list
- `tests/c/Makefile` - Removed QPU.c from 4 source lists
- `main.c` - QPU comment cleanup
- `build_preprocessor.py` - Added --sync-and-stage and fixed --check mode
- `.pre-commit-config.yaml` - Added sync-preprocessed-pyx local hook

## Decisions Made
- Used `git add -f` in the sync-and-stage hook because qint_preprocessed.pyx is listed in .gitignore (generated file), but the hook needs to force-stage it when drift is detected
- Changed hook entry from `python` to `python3` since the build environment only has python3 in PATH
- Pre-commit hook returns 0 always (auto-fix pattern) -- it fixes the drift and stages the result rather than blocking the commit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed git add failure for gitignored preprocessed file**
- **Found during:** Task 2 (pre-commit hook testing)
- **Issue:** `git add` fails for qint_preprocessed.pyx because it's in .gitignore
- **Fix:** Changed to `git add -f` to force-add ignored files in the sync-and-stage function
- **Files modified:** build_preprocessor.py
- **Verification:** `python3 build_preprocessor.py --sync-and-stage` succeeds with drift detection
- **Committed in:** a84b141 (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed python -> python3 in pre-commit hook entry**
- **Found during:** Task 2 (pre-commit hook testing)
- **Issue:** `pre-commit run sync-preprocessed-pyx` failed with "Executable `python` not found"
- **Fix:** Changed hook entry from `python` to `python3`
- **Files modified:** .pre-commit-config.yaml
- **Verification:** `pre-commit run sync-preprocessed-pyx --all-files` passes
- **Committed in:** a84b141 (Task 2 commit)

**3. [Rule 2 - Missing Critical] Cleaned additional QPU references in comments**
- **Found during:** Task 1 (post-migration grep scan)
- **Issue:** Plan listed 15 files for QPU.h include replacement, but grep found QPU references in comments across 6 additional files (IntegerAddition.c, LogicOperations.c, Integer.c, arithmetic_ops.h, comparison_ops.h, main.c)
- **Fix:** Updated all QPU_state references in comments to use neutral language (e.g., "global state" instead of "QPU_state->R0")
- **Files modified:** c_backend/src/IntegerAddition.c, c_backend/src/LogicOperations.c, c_backend/src/Integer.c, c_backend/include/arithmetic_ops.h, c_backend/include/comparison_ops.h, main.c
- **Verification:** `grep -r "QPU" c_backend/ src/quantum_language/ setup.py CMakeLists.txt tests/c/Makefile main.c` returns zero matches
- **Committed in:** c5918c5 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 missing critical)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- Build compilation takes ~10 minutes due to multiple Cython extensions each linking 80+ C object files
- Pre-existing test failure (test_qint_default_width) confirmed not related to QPU removal changes
- Pre-existing qarray/array test segfault (known Phase 87 issue) prevents full test suite completion

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Codebase is clean of all QPU dead code references
- Pre-commit hook is active for preprocessor drift detection
- Ready for Phase 83 Plan 02 (additional tech debt cleanup)

## Self-Check: PASSED

- QPU.c and QPU.h confirmed deleted
- Both commit hashes (c5918c5, a84b141) found in git log
- Zero QPU references in target files confirmed by grep
- Pre-commit hook registered and sync_and_stage function present
- Build compilation (`python3 setup.py build_ext --inplace --force`) completed successfully

---
*Phase: 83-tech-debt-cleanup*
*Completed: 2026-02-23*
