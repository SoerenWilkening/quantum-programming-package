---
phase: quick
plan: 011
type: execute
wave: 1
depends_on: []
files_modified:
  - src/quantum_language/qint.pyx
  - src/quantum_language/qint_arithmetic.pxi
  - src/quantum_language/qint_bitwise.pxi
  - src/quantum_language/qint_comparison.pxi
  - src/quantum_language/qint_division.pxi
  - build_preprocessor.py
  - setup.py
autonomous: true

must_haves:
  truths:
    - "qint.pyx source file is under 800 lines with include directives replacing operation sections"
    - "Build preprocessor inlines .pxi files into a temporary preprocessed .pyx before Cython compilation"
    - "pip install -e . succeeds and all existing tests pass identically to baseline"
  artifacts:
    - path: "build_preprocessor.py"
      provides: "Include directive preprocessor"
      contains: "process_includes"
    - path: "src/quantum_language/qint_arithmetic.pxi"
      provides: "Arithmetic operations section"
    - path: "src/quantum_language/qint_bitwise.pxi"
      provides: "Bitwise operations section"
    - path: "src/quantum_language/qint_comparison.pxi"
      provides: "Comparison operations section"
    - path: "src/quantum_language/qint_division.pxi"
      provides: "Division operations section"
    - path: "setup.py"
      provides: "Build integration calling preprocessor before cythonize"
      contains: "process_includes"
  key_links:
    - from: "setup.py"
      to: "build_preprocessor.py"
      via: "import and call before cythonize"
      pattern: "process_includes"
    - from: "src/quantum_language/qint.pyx"
      to: "src/quantum_language/qint_*.pxi"
      via: "include directives"
      pattern: 'include "qint_'
---

<objective>
Split qint.pyx (2795 lines) into a slim core file plus 4 .pxi section files, using a build-time preprocessor to inline includes before Cython compilation.

Purpose: qint.pyx is the largest file in the codebase. Cython 3.x forbids `include` inside `cdef class` bodies (confirmed in quick-004), but a build preprocessor can inline .pxi content before Cython sees it, giving modular source with monolithic compilation.

Output: qint.pyx reduced to ~700 lines, 4 .pxi files for operation sections, build_preprocessor.py, updated setup.py, all tests passing.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
@.planning/quick/010-split-qint-qarray-into-modules/010-SUMMARY.md
@setup.py
@src/quantum_language/qint.pyx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create build_preprocessor.py and split qint.pyx into .pxi files</name>
  <files>
    build_preprocessor.py
    src/quantum_language/qint.pyx
    src/quantum_language/qint_arithmetic.pxi
    src/quantum_language/qint_bitwise.pxi
    src/quantum_language/qint_comparison.pxi
    src/quantum_language/qint_division.pxi
  </files>
  <action>
**Step 1: Capture baseline test results.**
Run `python -m pytest tests/ -x -q` and record the pass/fail/skip counts.

**Step 2: Create build_preprocessor.py at project root.**
Adapt the proven preprocessor from the old python-backend (provided in planning context). Key behavior:
- `process_includes(source_file: Path, output_file: Path)` scans for `include "file.pxi"` lines
- For each match, reads the .pxi file relative to the source file's directory
- Replaces the include line with the .pxi content, wrapped in `# BEGIN include` / `# END include` comments
- Writes the result to `output_file`
- Add a `preprocess_all()` function that finds all .pyx files in `src/quantum_language/` containing include directives and preprocesses them to `*_preprocessed.pyx` in the same directory
- The preprocessed files should be written alongside the originals (e.g., `src/quantum_language/qint_preprocessed.pyx`)

**Step 3: Extract .pxi files from qint.pyx.**
Using the section markers in qint.pyx, extract 4 sections into .pxi files in `src/quantum_language/`:

| File | Start marker | End marker | Approx lines |
|------|-------------|------------|---------------|
| qint_arithmetic.pxi | `# ARITHMETIC OPERATIONS` (line 698) | `# BITWISE OPERATIONS` (line 1339) | ~641 |
| qint_bitwise.pxi | `# BITWISE OPERATIONS` (line 1339) | `# COMPARISON OPERATIONS` (line 1996) | ~657 |
| qint_comparison.pxi | `# COMPARISON OPERATIONS` (line 1996) | `# DIVISION OPERATIONS` (line 2464) | ~468 |
| qint_division.pxi | `# DIVISION OPERATIONS` (line 2464) | end of class | ~331 |

Each .pxi file should:
- Start with the section header comment (e.g., `# ARITHMETIC OPERATIONS`)
- Contain all the method definitions from that section
- Preserve exact indentation (these are class methods, indented with tabs/spaces)
- NOT contain any import statements (those stay in qint.pyx)

**Step 4: Replace extracted sections in qint.pyx with include directives.**
Replace each extracted section with:
```
    include "qint_arithmetic.pxi"
```
(indented to match the class body indentation level). The include directives go inside the cdef class body where the methods were.

After replacement, qint.pyx should be ~700 lines containing: imports, class definition, __init__/properties/utility methods, and 4 include directives.

**Step 5: Add .pxi to .gitignore exclusion and preprocessed to .gitignore.**
- Ensure `*_preprocessed.pyx` is in `.gitignore` (these are build artifacts)
- Ensure `.pxi` files are NOT gitignored (these are source files)
  </action>
  <verify>
- `build_preprocessor.py` exists at project root
- `python build_preprocessor.py` runs without error and produces `src/quantum_language/qint_preprocessed.pyx`
- `qint_preprocessed.pyx` has the same content as the original monolithic qint.pyx (diff the preprocessed output against git's last committed version of qint.pyx -- they should be semantically identical except for BEGIN/END include comments)
- `wc -l src/quantum_language/qint.pyx` shows ~700 lines
- All 4 .pxi files exist in `src/quantum_language/`
  </verify>
  <done>qint.pyx split into 5 files (1 core + 4 .pxi), preprocessor produces correct monolithic output</done>
</task>

<task type="auto">
  <name>Task 2: Integrate preprocessor into setup.py and verify full build + tests</name>
  <files>
    setup.py
  </files>
  <action>
**Step 1: Modify setup.py to run preprocessor before cythonize.**

In setup.py, add the preprocessor integration. Two approaches, use the cleaner one:

**Approach A (preferred): Modify the .pyx discovery to use preprocessed files.**
- Import `process_includes` from `build_preprocessor`
- Before the glob loop, call `preprocess_all()` to generate `*_preprocessed.pyx` files
- In the glob loop, skip `*_preprocessed.pyx` files from extension discovery
- For extensions whose source .pyx contains include directives, swap the source to the `_preprocessed.pyx` version

**Approach B (simpler): Preprocess inline.**
- Before creating extensions, run the preprocessor
- Map `qint.pyx` -> `qint_preprocessed.pyx` in the extensions list
- Keep all other .pyx files unchanged

Key constraints:
- The module name must remain `quantum_language.qint` (not `quantum_language.qint_preprocessed`)
- Other .pyx files (qarray.pyx, _core.pyx, etc.) that don't use includes should be unaffected
- The Extension `name` must stay `quantum_language.qint` but `sources` points to the preprocessed file

**Step 2: Build and test.**
- Run `pip install -e .` (or `python setup.py build_ext --inplace`)
- Verify compilation succeeds with no errors
- Run `python -c "from quantum_language.qint import qint; print('import OK')"` to verify the module loads
- Run `python -m pytest tests/ -x -q` and confirm pass/fail/skip counts match baseline exactly

**Step 3: Clean up preprocessed artifacts.**
- Ensure `*_preprocessed.pyx` files are in `.gitignore`
- The preprocessed .pyx should NOT be committed (it's a build artifact)
  </action>
  <verify>
- `pip install -e .` completes without error
- `python -c "from quantum_language.qint import qint; q = qint(3, 4); print(q)"` works
- `python -m pytest tests/ -x -q` shows identical pass/fail/skip to baseline
- `git diff --stat` shows no changes to test files
- `*_preprocessed.pyx` is in `.gitignore`
  </verify>
  <done>Full build pipeline works with preprocessor; all tests pass identically to pre-split baseline; preprocessed files are gitignored build artifacts</done>
</task>

</tasks>

<verification>
1. `wc -l src/quantum_language/qint.pyx` -- under 800 lines
2. `ls src/quantum_language/qint_*.pxi` -- 4 files exist
3. `python build_preprocessor.py` -- runs cleanly
4. `pip install -e . && python -m pytest tests/ -x -q` -- all tests pass, same counts as baseline
5. `grep -c 'include "qint_' src/quantum_language/qint.pyx` -- returns 4
6. `python -c "from quantum_language.qint import qint"` -- imports successfully
</verification>

<success_criteria>
- qint.pyx reduced from 2795 to ~700 lines
- 4 .pxi files contain the extracted operation sections
- build_preprocessor.py inlines .pxi files into preprocessed .pyx at build time
- setup.py integrates preprocessor seamlessly
- All existing tests pass with identical results
- Preprocessed files are gitignored (build artifacts only)
</success_criteria>

<output>
After completion, create `.planning/quick/011-verify-qint-pyx-split-feasibility/011-SUMMARY.md`
</output>
