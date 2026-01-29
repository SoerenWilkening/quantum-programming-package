---
phase: quick
plan: 006
type: execute
wave: 1
depends_on: []
files_modified:
  - setup.py
  - .gitignore
autonomous: true
---

<objective>
Relocate setup.py to project root and remove python-backend directory.

Purpose: Clean up project structure after Phase 21 migration to src-layout. The python-backend/ folder is now obsolete - setup.py should live at project root for standard Python packaging. Additionally, Cython-generated files (.c from .pyx, .so binaries) should be gitignored.

Output:
- setup.py at project root with corrected paths
- python-backend/ directory removed
- .gitignore updated for Cython artifacts
</objective>

<context>
Current structure:
- python-backend/setup.py - needs to move to project root
- python-backend/build/ - build artifacts to delete
- python-backend/UNKNOWN.egg-info/ - stale egg-info to delete
- src/quantum_language/*.c - Cython-generated C files (should be gitignored)
- src/quantum_language/*.so - Compiled extensions (should be gitignored)
- Backend/ - C backend source (include/ and src/) - stays as-is
- Execution/ - Execution C source (include/ and src/) - stays as-is
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move setup.py to project root and update paths</name>
  <files>setup.py</files>
  <action>
    1. Copy python-backend/setup.py to project root
    2. Update PROJECT_ROOT calculation - now it's the current directory:
       - Change: `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`
       - To: `PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))`
    3. All other paths relative to PROJECT_ROOT remain correct (Backend/src, Execution/src, src/)
  </action>
  <verify>python -c "import sys; sys.path.insert(0, '.'); exec(open('setup.py').read().split('setup(')[0]); print('Extensions:', len(extensions))"</verify>
  <done>setup.py at project root, discovers all .pyx files in src/quantum_language/</done>
</task>

<task type="auto">
  <name>Task 2: Remove python-backend directory</name>
  <files>python-backend/ (deletion)</files>
  <action>
    Remove the entire python-backend/ directory:
    - python-backend/setup.py (now at root)
    - python-backend/build/ (build artifacts)
    - python-backend/UNKNOWN.egg-info/ (stale metadata)
  </action>
  <verify>ls python-backend 2>&1 | grep -q "No such file" && echo "Removed"</verify>
  <done>python-backend/ directory no longer exists</done>
</task>

<task type="auto">
  <name>Task 3: Update .gitignore for Cython artifacts</name>
  <files>.gitignore</files>
  <action>
    Update .gitignore to:
    1. Remove obsolete python-backend/ specific patterns
    2. Add comprehensive Cython artifact patterns:
       - src/quantum_language/*.c (generated from .pyx, NOT hand-written)
       - src/quantum_language/**/*.c (for state/ subpackage)
       - src/quantum_language/*.so (compiled extensions)
       - src/quantum_language/**/*.so
       - *.egg-info/ (already present but verify)
       - build/ (general, not just python-backend/build)

    Keep: Backend/src/*.c and Execution/src/*.c are hand-written, NOT gitignored

    Note: The .c files in src/quantum_language/ are Cython-generated (from .pyx) and should be ignored.
    The .c files in Backend/src/ and Execution/src/ are hand-written C code and should NOT be ignored.
  </action>
  <verify>git status --porcelain src/quantum_language/*.c | grep -q "^??" || echo "C files ignored or tracked"</verify>
  <done>.gitignore excludes Cython-generated .c and .so files in src/quantum_language/</done>
</task>

</tasks>

<verification>
- [ ] setup.py exists at project root
- [ ] python setup.py --help works
- [ ] python-backend/ directory does not exist
- [ ] git status does not show src/quantum_language/*.c as untracked
- [ ] git status does not show src/quantum_language/*.so as untracked
- [ ] Backend/src/*.c files are NOT ignored (hand-written C code)
</verification>

<success_criteria>
- setup.py relocated to project root with working path references
- python-backend/ completely removed
- Cython-generated files (.c from .pyx, .so binaries) gitignored
- Hand-written C backend code (Backend/, Execution/) unaffected
</success_criteria>

<output>
After completion, create `.planning/quick/006-relocate-setup-py-remove-python-backend-/006-SUMMARY.md`
</output>
