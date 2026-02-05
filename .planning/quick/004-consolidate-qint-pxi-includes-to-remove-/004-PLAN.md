---
phase: quick
plan: 004
type: execute
wave: 1
depends_on: []
files_modified:
  - src/quantum_language/qint.pyx
autonomous: true

must_haves:
  truths:
    - "qint.pyx uses include statements for .pxi files"
    - "No duplicate code between qint.pyx and .pxi files"
    - "Package compiles successfully with pip install -e ."
  artifacts:
    - path: "src/quantum_language/qint.pyx"
      provides: "qint class with include statements"
      contains: "include \"qint_arithmetic.pxi\""
  key_links:
    - from: "src/quantum_language/qint.pyx"
      to: "src/quantum_language/qint_*.pxi"
      via: "Cython include directive"
      pattern: "include \"qint_"
---

<objective>
Consolidate qint.pyx with .pxi files by replacing duplicate code with include statements.

Purpose: Remove ~1788 lines of duplicated code between qint.pyx and the four .pxi files (qint_arithmetic.pxi, qint_bitwise.pxi, qint_comparison.pxi, qint_division.pxi).

Output: A clean qint.pyx that uses Cython include directives to pull in operation methods from .pxi files.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/quantum_language/qint.pyx
@src/quantum_language/qint_arithmetic.pxi
@src/quantum_language/qint_bitwise.pxi
@src/quantum_language/qint_comparison.pxi
@src/quantum_language/qint_division.pxi
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace duplicate arithmetic operations with include</name>
  <files>src/quantum_language/qint.pyx</files>
  <action>
    In qint.pyx, locate the ARITHMETIC OPERATIONS section (lines ~674-1055).

    Remove the following methods that exist in qint_arithmetic.pxi:
    - cdef addition_inplace(self, other, int invert=False)
    - def __add__(self, other)
    - def __radd__(self, other)
    - def __iadd__(self, other)
    - def __sub__(self, other)
    - def __isub__(self, other)
    - cdef multiplication_inplace(self, other, qint ret)
    - def __mul__(self, other)
    - def __rmul__(self, other)
    - def __imul__(self, other)

    Replace with:
    ```
    # ====================================================================
    # ARITHMETIC OPERATIONS
    # ====================================================================

    include "qint_arithmetic.pxi"
    ```

    The include must be placed at the proper indentation level INSIDE the cdef class body (one tab indent).
  </action>
  <verify>Check that the include statement is at correct indentation (one tab inside class)</verify>
  <done>Arithmetic section replaced with single include statement</done>
</task>

<task type="auto">
  <name>Task 2: Replace duplicate bitwise, comparison, and division operations</name>
  <files>src/quantum_language/qint.pyx</files>
  <action>
    Continue in qint.pyx to replace the remaining three sections:

    BITWISE OPERATIONS section (~lines 1056-1566):
    Remove all methods (__and__, __iand__, __rand__, __or__, __ior__, __ror__, __xor__, __ixor__, __rxor__, __invert__, __getitem__) and replace with:
    ```
    # ====================================================================
    # BITWISE OPERATIONS
    # ====================================================================

    include "qint_bitwise.pxi"
    ```

    COMPARISON OPERATIONS section (~lines 1567-2034):
    Remove all methods (__eq__, __ne__, __lt__, __gt__, __le__, __ge__) and replace with:
    ```
    # ====================================================================
    # COMPARISON OPERATIONS
    # ====================================================================

    include "qint_comparison.pxi"
    ```

    DIVISION OPERATIONS section (~lines 2035-2433):
    Remove all methods (__floordiv__, _floordiv_quantum, __mod__, _mod_quantum, __divmod__, _divmod_quantum, __rfloordiv__, __rmod__, __rdivmod__) and replace with:
    ```
    # ====================================================================
    # DIVISION OPERATIONS
    # ====================================================================

    include "qint_division.pxi"
    ```

    All include statements must be at one-tab indentation (inside class body).
  </action>
  <verify>Verify qint.pyx has 4 include statements total, file is ~650 lines (down from ~2433)</verify>
  <done>All four operation sections replaced with include statements</done>
</task>

<task type="auto">
  <name>Task 3: Verify compilation</name>
  <files>src/quantum_language/qint.pyx</files>
  <action>
    Run compilation to verify the include pattern works:

    ```bash
    cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly
    pip install -e . --no-build-isolation
    ```

    Then run a quick smoke test:
    ```bash
    python -c "from quantum_language import qint; a = qint(5, width=8); b = a + 3; print('Addition works:', b.value)"
    ```

    If compilation fails with "include directive not supported inside cdef class", the .pxi files need adjustment - but based on STATE.md Phase 21-07, this was the documented limitation. If this happens, revert and document that the include pattern is not viable for this codebase.
  </action>
  <verify>pip install -e . completes without error; smoke test prints "Addition works: 8"</verify>
  <done>Package compiles and basic operations work</done>
</task>

</tasks>

<verification>
1. qint.pyx file size reduced from ~2433 lines to ~650 lines
2. qint.pyx contains exactly 4 include statements for .pxi files
3. pip install -e . completes successfully
4. Basic operations work: qint(5) + 3 produces value 8
</verification>

<success_criteria>
- No duplicate code between qint.pyx and .pxi files
- Package compiles with pip install -e .
- All tests that previously passed still pass (run pytest if needed)
</success_criteria>

<output>
After completion, create `.planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md`
</output>
