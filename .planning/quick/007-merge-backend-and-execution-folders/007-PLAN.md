---
phase: quick-007
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - c_backend/include/*.h
  - c_backend/src/*.c
  - setup.py
  - CMakeLists.txt
  - Makefile
  - tests/c/Makefile
autonomous: true

must_haves:
  truths:
    - "All C source and header files exist in c_backend/"
    - "Backend/ and Execution/ directories are removed"
    - "Package builds successfully with pip install -e ."
    - "Pytest tests pass"
  artifacts:
    - path: "c_backend/include/"
      provides: "All C header files"
    - path: "c_backend/src/"
      provides: "All C source files"
  key_links:
    - from: "setup.py"
      to: "c_backend/"
      via: "c_sources and include_dirs paths"
---

<objective>
Merge Backend/ and Execution/ directories into a single c_backend/ directory.

Purpose: Simplify project structure by consolidating all C backend code into one location. Currently split across Backend/ (circuit, integer ops, optimizer) and Execution/ (execution runtime) with no clear reason for separation.

Output: Single c_backend/ directory with include/ and src/ subdirectories containing all C code.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@setup.py
@CMakeLists.txt
@Makefile
@tests/c/Makefile
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create c_backend/ and move all C files</name>
  <files>
    c_backend/include/*.h
    c_backend/src/*.c
  </files>
  <action>
    1. Create c_backend/ directory with include/ and src/ subdirectories
    2. Move all files from Backend/include/ to c_backend/include/ (18 header files)
    3. Move all files from Backend/src/ to c_backend/src/ (13 source files)
    4. Move all files from Execution/include/ to c_backend/include/ (1 header: execution.h)
    5. Move all files from Execution/src/execution.c to c_backend/src/ (1 source file)
    6. Do NOT move Execution/src/run_circuit.py - this is a Python file, not C code
    7. Remove Backend/ and Execution/ directories (including .DS_Store files)

    File inventory:
    - Backend/include/: definition.h, circuit.h, types.h, circuit_output.h, IntegerComparison.h, optimizer.h, QPU.h, gate.h, comparison_ops.h, qubit_allocator.h, arithmetic_ops.h, Integer.h, bitwise_ops.h, circuit_stats.h, circuit_optimizer.h, LogicOperations.h, module_deps.md, old_div
    - Backend/src/: QPU.c, optimizer.c, gate.c, qubit_allocator.c, IntegerMultiplication.c, IntegerAddition.c, LogicOperations.c, circuit_optimizer.c, Integer.c, circuit_stats.c, circuit_allocations.c, circuit_output.c, IntegerComparison.c
    - Execution/include/: execution.h
    - Execution/src/: execution.c

    No file naming conflicts exist between directories.
  </action>
  <verify>
    ls -la c_backend/include/ c_backend/src/
    # Should show 19 headers in include/, 14 .c files in src/
    # Backend/ and Execution/ should not exist
    ls Backend/ 2>&1 | grep -q "No such file"
    ls Execution/ 2>&1 | grep -q "No such file"
  </verify>
  <done>All C code consolidated in c_backend/, old directories removed</done>
</task>

<task type="auto">
  <name>Task 2: Update all path references in build files</name>
  <files>
    setup.py
    CMakeLists.txt
    Makefile
    tests/c/Makefile
  </files>
  <action>
    Update path references in build configuration files:

    **setup.py:**
    - Change all "Backend/src/*.c" paths to "c_backend/src/*.c"
    - Change all "Backend/include" to "c_backend/include"
    - Remove separate "Execution/src/*.c" and "Execution/include" references
    - Simplify include_dirs to just c_backend/include (was two dirs)

    **CMakeLists.txt:**
    - Change Backend/src/*.c paths to c_backend/src/*.c
    - Change Execution/src/execution.c to c_backend/src/execution.c
    - Change target_include_directories to point to c_backend/include only
    - Note: Assembly/ references can remain (separate concern)

    **Makefile:**
    - Change BACKEND_SRC = Backend/src/*.c to c_backend/src/*.c
    - Change BACKEND_INC = -IBackend/include -IExecution/include to -Ic_backend/include
    - Change EXEC_SRC = Execution/src/*.c to empty or remove (merged into BACKEND_SRC)
    - Update asan-test target accordingly

    **tests/c/Makefile:**
    - Change CFLAGS include path from ../../Backend/include to ../../c_backend/include
    - Change BACKEND_SRC from ../../Backend/src to ../../c_backend/src
  </action>
  <verify>
    grep -r "Backend/" setup.py CMakeLists.txt Makefile tests/c/Makefile
    # Should return no matches
    grep -r "Execution/" setup.py CMakeLists.txt Makefile tests/c/Makefile
    # Should return no matches
    grep "c_backend" setup.py CMakeLists.txt Makefile tests/c/Makefile
    # Should show new paths in all files
  </verify>
  <done>All build files reference c_backend/ instead of Backend/ and Execution/</done>
</task>

<task type="auto">
  <name>Task 3: Verify build and tests</name>
  <files>None (verification only)</files>
  <action>
    1. Clean any cached build artifacts:
       rm -rf build/ *.so src/quantum_language/*.so src/quantum_language/**/*.so

    2. Rebuild the package:
       pip install -e . --no-build-isolation

    3. Run the test suite:
       pytest tests/python -v --tb=short

    4. If build fails, check for:
       - Missing include paths
       - Incorrect source file references
       - Header include issues within C code itself
  </action>
  <verify>
    pip install -e . --no-build-isolation 2>&1 | tail -5
    # Should show successful install
    pytest tests/python -v --tb=short -x
    # Tests should pass (or fail for pre-existing reasons noted in STATE.md)
  </verify>
  <done>Package builds and tests pass (excluding known pre-existing failures)</done>
</task>

</tasks>

<verification>
- c_backend/ exists with include/ and src/ subdirectories
- Backend/ and Execution/ directories no longer exist
- All 19 header files in c_backend/include/
- All 14 source files in c_backend/src/
- pip install -e . completes successfully
- pytest tests/python passes (with known exceptions)
- grep finds no "Backend/" or "Execution/" in build config files
</verification>

<success_criteria>
- Single c_backend/ directory contains all C code
- Old Backend/ and Execution/ directories removed
- Package builds with no path errors
- Test suite passes (excluding pre-existing failures)
</success_criteria>

<output>
After completion, create `.planning/quick/007-merge-backend-and-execution-folders/007-SUMMARY.md`
</output>
