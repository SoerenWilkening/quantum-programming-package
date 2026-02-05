---
phase: quick-005
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - python-backend/quantum_language.pyx
  - python-backend/quantum_language.pxd
  - python-backend/quantum_language_preprocessed.pyx
  - python-backend/qint_operations.pxi
  - python-backend/qint_modular.pxi
  - python-backend/circuit_class.pxi
  - python-backend/build_preprocessor.py
  - python-backend/test.py
  - python-backend/quantum_language.c
  - python-backend/quantum_language_preprocessed.c
autonomous: true
must_haves:
  truths:
    - "Tests pass using new src/quantum_language/ package only"
    - "Old monolithic files in python-backend/ are removed"
    - "Build system still works (setup.py builds from src/)"
  artifacts:
    - path: "python-backend/setup.py"
      provides: "Build configuration for new package structure"
      retained: true
    - path: "src/quantum_language/__init__.py"
      provides: "Package entry point"
      exists: true
  key_links:
    - from: "python-backend/setup.py"
      to: "src/quantum_language/*.pyx"
      via: "glob.glob auto-discovery"
      pattern: "glob.glob.*src.*quantum_language"
---

<objective>
Remove legacy Python/Cython code from python-backend/ that is now fully superseded by the new modular src/quantum_language/ package structure.

Purpose: Phase 21 (Package Restructuring) migrated from a monolithic quantum_language.pyx to a modular package under src/. The old files in python-backend/ are now redundant and create confusion about which code is authoritative.

Output: Clean python-backend/ directory with only setup.py and build artifacts
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@python-backend/setup.py
@src/quantum_language/__init__.py

Reference: Phase 21 completed full migration to src/quantum_language/ with:
- _core.pyx (circuit, state management, utility functions)
- qint.pyx (quantum integer class with all operations)
- qbool.pyx (quantum boolean class)
- qint_mod.pyx (modular arithmetic)
- state/ subpackage (circuit_stats, get_current_layer)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify new package completeness</name>
  <files>tests/python/test_api_coverage.py</files>
  <action>
Run the test suite to confirm the new src/quantum_language/ package provides all required functionality:

```bash
python3 -m pytest tests/python/test_api_coverage.py -v --tb=short
```

Verify that:
1. All tests import from `quantum_language` (not legacy paths)
2. Core API tests pass: circuit, qint, qbool, qint_mod, array
3. The setup.py already builds from src/ (no legacy fallback needed)

If tests fail, document which functionality is missing before proceeding.
  </action>
  <verify>pytest tests/python/test_api_coverage.py runs and passes (failures due to known issues like segfaults are acceptable)</verify>
  <done>Tests confirm new package provides complete API coverage</done>
</task>

<task type="auto">
  <name>Task 2: Remove legacy source files from python-backend/</name>
  <files>
    python-backend/quantum_language.pyx
    python-backend/quantum_language.pxd
    python-backend/quantum_language_preprocessed.pyx
    python-backend/quantum_language_preprocessed.c
    python-backend/quantum_language.c
    python-backend/qint_operations.pxi
    python-backend/qint_modular.pxi
    python-backend/circuit_class.pxi
    python-backend/build_preprocessor.py
    python-backend/test.py
    python-backend/tic-tc-toe.py
  </files>
  <action>
Delete the following legacy files that are now superseded:

**Source files (migrated to src/quantum_language/):**
- `quantum_language.pyx` - monolithic source (now split into _core.pyx, qint.pyx, qbool.pyx, qint_mod.pyx)
- `quantum_language.pxd` - type declarations (now per-module .pxd files in src/)
- `quantum_language_preprocessed.pyx` - preprocessed output (no longer needed)
- `qint_operations.pxi`, `qint_modular.pxi`, `circuit_class.pxi` - include files (content now in qint.pyx)

**Build artifacts:**
- `quantum_language.c` - stub file (preprocessed builds differently now)
- `quantum_language_preprocessed.c` - generated C (will regenerate from src/)

**Obsolete tooling:**
- `build_preprocessor.py` - preprocessor script (no longer needed with modular structure)
- `test.py` - ad-hoc test file (tests are in tests/python/)
- `tic-tc-toe.py` - example/demo file (untracked, can be removed)

**KEEP:**
- `setup.py` - still needed to build the package
- `build/` directory - build cache
- `UNKNOWN.egg-info/` - package metadata

Commands:
```bash
cd python-backend
rm -f quantum_language.pyx quantum_language.pxd
rm -f quantum_language_preprocessed.pyx quantum_language_preprocessed.c quantum_language.c
rm -f qint_operations.pxi qint_modular.pxi circuit_class.pxi
rm -f build_preprocessor.py test.py tic-tc-toe.py
```
  </action>
  <verify>ls python-backend/ shows only setup.py, build/, UNKNOWN.egg-info/</verify>
  <done>Legacy source files removed, python-backend/ contains only build infrastructure</done>
</task>

<task type="auto">
  <name>Task 3: Verify build and tests still work</name>
  <files>python-backend/setup.py</files>
  <action>
Rebuild the package and run tests to confirm nothing broke:

```bash
cd /path/to/project
pip3 install -e . --force-reinstall
python3 -m pytest tests/python/test_api_coverage.py -v --tb=short
```

The setup.py already discovers .pyx files from src/quantum_language/, so it should build correctly without the legacy files.

If the build fails, check that setup.py's auto-discovery logic is working:
- `glob.glob(os.path.join(SRC_DIR, "quantum_language", "**", "*.pyx"), recursive=True)` should find files
- No fallback to legacy build should trigger (since src/ exists)
  </action>
  <verify>pip3 install -e . succeeds AND pytest tests/python/test_api_coverage.py passes</verify>
  <done>Package builds and tests pass after legacy file removal</done>
</task>

</tasks>

<verification>
- [ ] No .pyx or .pxi files remain in python-backend/
- [ ] python-backend/ contains only: setup.py, build/, UNKNOWN.egg-info/
- [ ] `pip3 install -e .` builds successfully
- [ ] `pytest tests/python/test_api_coverage.py` passes
- [ ] `import quantum_language as ql` works and imports from src/
</verification>

<success_criteria>
1. Legacy monolithic source files removed from python-backend/
2. Build system continues to work using src/quantum_language/
3. All API tests pass
4. No regression in package functionality
</success_criteria>

<output>
After completion, create `.planning/quick/005-remove-old-python-code-if-completely-cov/005-SUMMARY.md`
</output>
