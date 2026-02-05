---
phase: quick-002
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - python-backend/quantum_language.pyx
  - python-backend/quantum_language.pxd
  - python-backend/qint_arithmetic.pxi
  - python-backend/qint_bitwise.pxi
  - python-backend/qint_comparison.pxi
  - python-backend/qint_division.pxi
  - python-backend/qint_modular.pxi
autonomous: true

must_haves:
  truths:
    - "All existing tests pass after refactor"
    - "quantum_language.pyx is under 400 lines"
    - "Each .pxi file is 200-350 lines"
    - "All public API unchanged"
  artifacts:
    - path: "python-backend/quantum_language.pyx"
      provides: "Core module with circuit, qint shell, qbool"
      max_lines: 400
    - path: "python-backend/qint_arithmetic.pxi"
      provides: "qint arithmetic operations (+, -, *)"
      min_lines: 200
      max_lines: 350
    - path: "python-backend/qint_bitwise.pxi"
      provides: "qint bitwise operations (&, |, ^, ~)"
      min_lines: 200
      max_lines: 350
    - path: "python-backend/qint_comparison.pxi"
      provides: "qint comparison operations (==, !=, <, >, <=, >=)"
      min_lines: 200
      max_lines: 350
    - path: "python-backend/qint_division.pxi"
      provides: "qint division operations (//, %, divmod)"
      min_lines: 200
      max_lines: 350
    - path: "python-backend/qint_modular.pxi"
      provides: "qint_mod class for modular arithmetic"
      min_lines: 150
      max_lines: 300
  key_links:
    - from: "python-backend/quantum_language.pyx"
      to: "python-backend/qint_*.pxi"
      via: "Cython include directive"
      pattern: "include.*\\.pxi"
---

<objective>
Refactor quantum_language.pyx (3068 lines) into smaller files using Cython's include directive.

Purpose: Improve maintainability by splitting the monolithic file into logical modules of ~200-300 lines each.

Output: quantum_language.pyx (~400 lines) + 5 .pxi include files (~250 lines each)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@python-backend/quantum_language.pyx
@python-backend/quantum_language.pxd
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract arithmetic operations to qint_arithmetic.pxi</name>
  <files>
    python-backend/qint_arithmetic.pxi
    python-backend/quantum_language.pyx
  </files>
  <action>
Create python-backend/qint_arithmetic.pxi containing:
- The `addition_inplace` cdef method (lines 867-925)
- The `__add__`, `__radd__`, `__iadd__` methods (lines 927-1008)
- The `__sub__`, `__isub__` methods (lines 1010-1062)
- The `multiplication_inplace` cdef method (lines 1065-1133)
- The `__mul__`, `__rmul__`, `__imul__` methods (lines 1135-1224)

Add header comment:
```
# qint_arithmetic.pxi - Arithmetic operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly
```

In quantum_language.pyx, after the qint class `measure()` method (around line 1246), add:
```
include "qint_arithmetic.pxi"
```

Remove the original arithmetic methods from quantum_language.pyx.

Note: The include directive inserts code at that point in the class definition, so the indentation in the .pxi file must match class method indentation (one tab).
  </action>
  <verify>
Run `python -c "from quantum_language import qint, circuit; c = circuit(); a = qint(5); b = qint(3); print((a+b).measure())"` returns 8
  </verify>
  <done>qint_arithmetic.pxi exists with ~280 lines, arithmetic operations work</done>
</task>

<task type="auto">
  <name>Task 2: Extract bitwise operations to qint_bitwise.pxi</name>
  <files>
    python-backend/qint_bitwise.pxi
    python-backend/quantum_language.pyx
  </files>
  <action>
Create python-backend/qint_bitwise.pxi containing:
- The `__and__`, `__iand__`, `__rand__` methods (lines 1248-1370)
- The `__or__`, `__ior__`, `__ror__` methods (lines 1372-1494)
- The `__xor__`, `__ixor__`, `__rxor__` methods (lines 1496-1673)
- The `__invert__` method (lines 1675-1719)
- The `__getitem__` method (lines 1721-1743)

Add header comment:
```
# qint_bitwise.pxi - Bitwise operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly
```

In quantum_language.pyx, after the arithmetic include:
```
include "qint_bitwise.pxi"
```

Remove the original bitwise methods from quantum_language.pyx.
  </action>
  <verify>
Run `python -c "from quantum_language import qint, circuit; c = circuit(); a = qint(0b1100, width=4); b = qint(0b0011, width=4); print((a | b).measure())"` returns 15
  </verify>
  <done>qint_bitwise.pxi exists with ~300 lines, bitwise operations work</done>
</task>

<task type="auto">
  <name>Task 3: Extract comparison and division operations to separate .pxi files</name>
  <files>
    python-backend/qint_comparison.pxi
    python-backend/qint_division.pxi
    python-backend/qint_modular.pxi
    python-backend/quantum_language.pyx
  </files>
  <action>
Create python-backend/qint_comparison.pxi containing:
- The `__eq__` method (lines 1745-1876)
- The `__ne__` method (lines 1878-1902)
- The `__lt__` method (lines 1904-1989)
- The `__gt__` method (lines 1991-2064)
- The `__le__` method (lines 2066-2159)
- The `__ge__` method (lines 2161-2195)

Create python-backend/qint_division.pxi containing:
- The `__floordiv__` method (lines 2197-2266)
- The `_floordiv_quantum` method (lines 2268-2309)
- The `__mod__` method (lines 2311-2370)
- The `_mod_quantum` method (lines 2372-2400)
- The `__divmod__` method (lines 2402-2462)
- The `_divmod_quantum` method (lines 2464-2494)
- The `__rfloordiv__`, `__rmod__`, `__rdivmod__` methods (lines 2496-2575)

Create python-backend/qint_modular.pxi containing:
- The entire `qint_mod` class definition (lines 2631-2970)

Add header comments to each file.

In quantum_language.pyx, add includes after bitwise:
```
include "qint_comparison.pxi"
include "qint_division.pxi"
```

After the qint class definition closes (after `__rdivmod__`), add:
```
include "qint_modular.pxi"
```

Note: qint_modular.pxi contains a complete class definition, so it goes AFTER the qint class closes, not inside it.

Remove all the original methods from quantum_language.pyx.
  </action>
  <verify>
Run the test suite: `cd python-backend && python test.py` - all tests should pass.
Additionally verify:
- Comparison: `python -c "from quantum_language import qint, circuit; c = circuit(); a = qint(5); print((a == 5).measure())"`
- Division: `python -c "from quantum_language import qint, circuit; c = circuit(); a = qint(17, width=8); print((a // 5).measure())"`
- Modular: `python -c "from quantum_language import qint_mod, circuit; c = circuit(); x = qint_mod(15, N=17); print((x + 5).measure())"`
  </verify>
  <done>
Three .pxi files created:
- qint_comparison.pxi (~300 lines)
- qint_division.pxi (~300 lines)
- qint_modular.pxi (~250 lines)
All tests pass, quantum_language.pyx is under 400 lines
  </done>
</task>

</tasks>

<verification>
1. Line counts:
   - `wc -l python-backend/quantum_language.pyx` should be < 400
   - `wc -l python-backend/qint_arithmetic.pxi` should be 200-350
   - `wc -l python-backend/qint_bitwise.pxi` should be 200-350
   - `wc -l python-backend/qint_comparison.pxi` should be 200-350
   - `wc -l python-backend/qint_division.pxi` should be 200-350
   - `wc -l python-backend/qint_modular.pxi` should be 150-300

2. Compilation: `cd python-backend && python setup.py build_ext --inplace` succeeds

3. Tests: `cd python-backend && python test.py` all pass

4. API unchanged:
   ```python
   from quantum_language import circuit, qint, qbool, qint_mod, array, circuit_stats
   # All exports still available
   ```
</verification>

<success_criteria>
- quantum_language.pyx reduced from 3068 to ~400 lines
- 5 new .pxi files created, each 200-350 lines
- All existing functionality preserved (tests pass)
- Public API unchanged
- Cython compilation succeeds
</success_criteria>

<output>
After completion, create `.planning/quick/002-refactor-quantum-language-pyx-and-the-px/002-SUMMARY.md`
</output>
