---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - python-backend/quantum_language.pyx
  - python-backend/quantum_language.pxd
  - python-backend/qint_ops.pyx
  - python-backend/qint_ops.pxd
  - python-backend/qint_mod_class.pyx
  - python-backend/qint_mod_class.pxd
  - python-backend/setup.py
autonomous: true

must_haves:
  truths:
    - "quantum_language.pyx is under 400 lines (core infrastructure only)"
    - "qint_ops.pyx contains all qint operation methods"
    - "qint_mod_class.pyx contains qint_mod class"
    - "All tests pass after refactoring"
    - "Build system compiles all modules correctly"
  artifacts:
    - path: "python-backend/quantum_language.pyx"
      provides: "Core classes (circuit, qint shell, qbool) and module functions"
      max_lines: 400
    - path: "python-backend/qint_ops.pyx"
      provides: "All qint operation methods via cdef extern include"
      max_lines: 500
    - path: "python-backend/qint_mod_class.pyx"
      provides: "qint_mod modular arithmetic class"
      max_lines: 400
    - path: "python-backend/setup.py"
      provides: "Build configuration for single quantum_language extension"
  key_links:
    - from: "setup.py"
      to: "quantum_language.pyx"
      via: "Extension source"
      pattern: "quantum_language\\.pyx"
---

<objective>
Refactor quantum_language.pyx from 1057 lines to ~400 lines by extracting operations into separate files using Cython's verbatim include mechanism.

Purpose: Previous refactoring used .pxi includes requiring preprocessing workaround. This refactoring consolidates operations properly while keeping build simple. The 1057 line main file is still too large for maintainability.

Output: quantum_language.pyx under 400 lines, operation files properly organized, build working, quantum_language_preprocessed.pyx and build_preprocessor.py removed.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@python-backend/quantum_language.pyx
@python-backend/quantum_language.pxd
@python-backend/setup.py
@python-backend/build_preprocessor.py
@python-backend/qint_arithmetic.pxi
@python-backend/qint_bitwise.pxi
@python-backend/qint_comparison.pxi
@python-backend/qint_division.pxi
@python-backend/qint_modular.pxi
</context>

<tasks>

<task type="auto">
  <name>Task 1: Consolidate qint operations into single include file</name>
  <files>
    python-backend/qint_operations.pxi
    python-backend/quantum_language.pyx
    python-backend/qint_arithmetic.pxi (delete)
    python-backend/qint_bitwise.pxi (delete)
    python-backend/qint_comparison.pxi (delete)
    python-backend/qint_division.pxi (delete)
  </files>
  <action>
    1. Create `qint_operations.pxi` by concatenating the 4 qint operation files:
       - qint_arithmetic.pxi (362 lines)
       - qint_bitwise.pxi (500 lines)
       - qint_comparison.pxi (456 lines)
       - qint_division.pxi (384 lines)
       Total: ~1700 lines in single operations file

    2. Update quantum_language.pyx:
       - Replace the 4 include statements with single: `include "qint_operations.pxi"`
       - Keep qint_modular.pxi include as-is (module-level class)

    3. Delete the 4 individual .pxi files after consolidation:
       - qint_arithmetic.pxi
       - qint_bitwise.pxi
       - qint_comparison.pxi
       - qint_division.pxi

    Rationale: The 4-file split was an attempt at granularity but created more complexity.
    A single operations file is easier to maintain and still separates concerns from core infrastructure.
  </action>
  <verify>
    - `wc -l python-backend/qint_operations.pxi` shows ~1700 lines
    - `wc -l python-backend/quantum_language.pyx` shows ~960 lines (3 includes removed, 1 added)
    - `ls python-backend/*.pxi` shows only qint_operations.pxi and qint_modular.pxi
  </verify>
  <done>
    Operations consolidated into single qint_operations.pxi file.
    quantum_language.pyx has 2 includes instead of 5.
    Four redundant .pxi files deleted.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extract qint __init__ and tracking methods</name>
  <files>
    python-backend/quantum_language.pyx
    python-backend/qint_operations.pxi
  </files>
  <action>
    1. Extract from qint class in quantum_language.pyx to qint_operations.pxi:
       - `add_dependency()` method (~12 lines)
       - `get_live_parents()` method (~10 lines)
       - `_do_uncompute()` method (~50 lines)
       - `uncompute()` method (~25 lines)
       - `_check_not_uncomputed()` method (~12 lines)
       - `print_circuit()` method (~3 lines)
       - `__del__()` method (~20 lines)
       - `__str__()` method (~2 lines)
       - `__enter__()` method (~20 lines)
       - `__exit__()` method (~25 lines)
       - `measure()` method (~5 lines)

       These are ~185 lines of methods that belong with operations.

    2. quantum_language.pyx qint class should retain ONLY:
       - Class declaration with cdef attributes (~25 lines)
       - `__init__()` method (~160 lines - core initialization logic)
       - `width` property (~10 lines)
       - Single `include "qint_operations.pxi"` at end of class

    3. The qint class in quantum_language.pyx should be ~200 lines total after extraction.

    Note: The include must appear INSIDE the class body for the methods to be class methods.
    The preprocessor handles inlining at build time (Cython 3 compatibility).
  </action>
  <verify>
    - `grep -c "def " python-backend/quantum_language.pyx` shows reduced method count (only __init__, width)
    - `wc -l python-backend/quantum_language.pyx` shows ~775 lines (960 - 185 extracted)
    - `grep "add_dependency\|get_live_parents\|_do_uncompute" python-backend/qint_operations.pxi` finds methods
  </verify>
  <done>
    qint utility methods extracted to qint_operations.pxi.
    qint class in main file has only __init__ and width property.
    quantum_language.pyx reduced by ~185 lines.
  </done>
</task>

<task type="auto">
  <name>Task 3: Extract circuit class to separate include file</name>
  <files>
    python-backend/circuit_class.pxi
    python-backend/quantum_language.pyx
  </files>
  <action>
    1. Create `circuit_class.pxi` with the entire circuit class (~260 lines):
       - Class declaration
       - __init__() method
       - add_qubits() method
       - visualize() method
       - gate_count, depth, qubit_count, gate_counts properties
       - available_passes property
       - optimize() method
       - can_optimize() method
       - __dealloc__() method

    2. In quantum_language.pyx, replace circuit class definition with:
       `include "circuit_class.pxi"`

    3. Move the circuit class include BEFORE the qint class (since qint inherits from circuit).

    Result: quantum_language.pyx now contains:
    - Imports and module globals (~50 lines)
    - `include "circuit_class.pxi"` (1 line)
    - qint class shell with __init__ + `include "qint_operations.pxi"` (~200 lines)
    - qbool class (~55 lines)
    - `include "qint_modular.pxi"` (1 line)
    - Module functions (~100 lines)
    Total: ~410 lines (close to target of 400)
  </action>
  <verify>
    - `wc -l python-backend/circuit_class.pxi` shows ~260 lines
    - `wc -l python-backend/quantum_language.pyx` shows ~410-420 lines
    - `grep "cdef class circuit" python-backend/circuit_class.pxi` finds class
    - `grep "include.*circuit_class" python-backend/quantum_language.pyx` finds include
  </verify>
  <done>
    circuit class extracted to circuit_class.pxi (~260 lines).
    quantum_language.pyx reduced to ~410 lines.
    Main file now contains only essential scaffolding.
  </done>
</task>

<task type="auto">
  <name>Task 4: Clean up build system and verify</name>
  <files>
    python-backend/setup.py
    python-backend/build_preprocessor.py (keep)
    python-backend/quantum_language_preprocessed.pyx (generated)
  </files>
  <action>
    1. Verify setup.py still works with new include structure:
       - build_preprocessor.py will inline all .pxi files (circuit_class, qint_operations, qint_modular)
       - No changes needed to setup.py if preprocessor handles all includes

    2. Run full build:
       ```bash
       cd python-backend
       python3 setup.py build_ext --inplace
       ```

    3. Run verification tests:
       ```bash
       cd python-backend
       python3 test.py
       ```

    4. Verify quantum_language_preprocessed.pyx is generated correctly:
       - Should contain all code concatenated
       - Should be ~3100 lines (similar to before)

    5. Quick functional verification:
       ```python
       from quantum_language import circuit, qint, qbool, qint_mod, array, circuit_stats
       c = circuit()
       a = qint(5, width=8)
       b = qint(3, width=8)
       result = a + b
       print(f"Gate count: {c.gate_count}")  # Should show gates
       ```

    Note: Do NOT delete build_preprocessor.py or quantum_language_preprocessed.pyx.
    The preprocessor is required for Cython 3 compatibility (include inside class body).
    The preprocessed file is the actual compilation source.
  </action>
  <verify>
    - Build completes without errors
    - `python3 -c "from quantum_language import circuit, qint, qbool; c=circuit(); a=qint(5); b=qint(3); print(f'OK: {(a+b).measure()}')"` prints "OK: 8"
    - `python3 test.py` passes all tests
    - `wc -l python-backend/quantum_language_preprocessed.pyx` shows ~3100 lines
  </verify>
  <done>
    Build system verified working.
    All tests pass.
    Preprocessor correctly inlines new include structure.
    quantum_language_preprocessed.pyx generated correctly.
  </done>
</task>

</tasks>

<verification>
After all tasks:
1. File organization:
   - quantum_language.pyx: ~410 lines (was 1057)
   - circuit_class.pxi: ~260 lines (new)
   - qint_operations.pxi: ~1900 lines (consolidated from 4 files + extracted methods)
   - qint_modular.pxi: ~346 lines (unchanged)
   - Total: ~2916 lines across 4 files (was 6215 across 7 files)

2. Build verification:
   - `python3 setup.py build_ext --inplace` succeeds
   - quantum_language.cpython-*.so generated

3. Test verification:
   - `python3 test.py` passes all Phase 16-19 tests
   - Basic operations work (arithmetic, bitwise, comparison, modular)

4. File cleanup:
   - qint_arithmetic.pxi, qint_bitwise.pxi, qint_comparison.pxi, qint_division.pxi deleted
   - build_preprocessor.py retained (required for Cython 3)
   - quantum_language_preprocessed.pyx retained (generated at build time)
</verification>

<success_criteria>
- quantum_language.pyx is under 420 lines (target: 400)
- All .pxi include files properly organized
- Build completes successfully
- All existing tests pass
- API unchanged (circuit, qint, qbool, qint_mod, array, circuit_stats available)
</success_criteria>

<output>
After completion, create `.planning/quick/003-revisit-refactoring-quantum-language-pyx/003-SUMMARY.md`
</output>
