---
phase: quick-009
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - demo.py
autonomous: true

must_haves:
  truths:
    - "Cython extensions compile successfully in-place"
    - "A Python script imports quantum_language and runs without error"
  artifacts:
    - path: "demo.py"
      provides: "Demo script importing quantum_language"
    - path: "src/quantum_language/_core.cpython-*.so"
      provides: "Compiled Cython extension"
  key_links:
    - from: "demo.py"
      to: "src/quantum_language/__init__.py"
      via: "import quantum_language as ql"
      pattern: "import quantum_language"
---

<objective>
Compile the quantum_language Cython package in-place and create a demo Python file that imports and uses it.

Purpose: Verify the package builds and is importable, providing a ready-to-run entry point.
Output: Freshly compiled .so files in src/quantum_language/ and a demo.py at project root.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@setup.py
@pyproject.toml
@src/quantum_language/__init__.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Compile package in-place</name>
  <files>src/quantum_language/*.so (generated)</files>
  <action>
    Run in-place Cython compilation from the project root:

    ```bash
    python setup.py build_ext --inplace
    ```

    This compiles all .pyx files in src/quantum_language/ into .so shared objects
    placed alongside the source files (--inplace flag). The setup.py auto-discovers
    all .pyx files and links them against the C backend in c_backend/src/.

    If the build fails, check:
    1. Cython is installed (pip install cython>=3.0.11)
    2. C compiler is available (gcc/clang)
    3. c_backend/src/ and c_backend/include/ directories exist

    Verify the .so files are placed in src/quantum_language/ (not just build/).
  </action>
  <verify>
    ls src/quantum_language/*.so should show .so files for _core, qint, qbool, qint_mod, qarray.
    python -c "import sys; sys.path.insert(0, 'src'); import quantum_language as ql; print(ql.__version__)" prints "0.1.0".
  </verify>
  <done>.so files exist in src/quantum_language/ and the package imports successfully.</done>
</task>

<task type="auto">
  <name>Task 2: Create demo Python file</name>
  <files>demo.py</files>
  <action>
    Create demo.py at the project root that imports and exercises the quantum_language package.
    The file should:

    1. Add src/ to sys.path so it works without pip install
    2. Import quantum_language as ql
    3. Create a circuit with ql.circuit()
    4. Create qint variables (e.g., a = ql.qint(5, width=8), b = ql.qint(3, width=8))
    5. Perform arithmetic (result = a + b)
    6. Create a qbool
    7. Create a qarray using ql.array([1, 2, 3])
    8. Print circuit_stats at the end using ql.circuit_stats()
    9. Include brief comments explaining each step

    Keep the demo concise (under 40 lines). Use the API as documented in __init__.py.
    Do NOT use any internal/private APIs.
  </action>
  <verify>
    python demo.py runs without errors and prints circuit statistics output.
  </verify>
  <done>demo.py exists at project root, imports quantum_language, exercises core types (qint, qbool, qarray), and prints circuit stats.</done>
</task>

</tasks>

<verification>
1. `python setup.py build_ext --inplace` completes with exit code 0
2. `ls src/quantum_language/*.so` shows compiled extensions
3. `python demo.py` runs and produces output without errors
</verification>

<success_criteria>
- Cython extensions freshly compiled in src/quantum_language/
- demo.py at project root imports the package and runs successfully
- Demo exercises qint, qbool, qarray, circuit, and circuit_stats
</success_criteria>

<output>
After completion, create `.planning/quick/009-compile-the-package-inplace-and-create-a/009-SUMMARY.md`
</output>
