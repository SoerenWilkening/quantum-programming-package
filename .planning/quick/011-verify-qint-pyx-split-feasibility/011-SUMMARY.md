---
phase: quick
plan: 011
subsystem: cython-build
tags: [cython, refactor, preprocessor, modularity, qint]
dependency-graph:
  requires: [quick-004, quick-010]
  provides: ["Build-time .pxi preprocessor for Cython cdef class splitting", "Modular qint.pyx (701 lines + 4 .pxi files)"]
  affects: []
tech-stack:
  added: []
  patterns: ["Build-time include preprocessing for Cython 3.x cdef class workaround"]
key-files:
  created:
    - build_preprocessor.py
    - src/quantum_language/qint_arithmetic.pxi
    - src/quantum_language/qint_bitwise.pxi
    - src/quantum_language/qint_comparison.pxi
    - src/quantum_language/qint_division.pxi
  modified:
    - src/quantum_language/qint.pyx
    - setup.py
    - .gitignore
decisions:
  - id: Q011-D1
    description: "Use build-time preprocessor to work around Cython 3.x cdef class include restriction"
    rationale: "Quick-004 confirmed include directives cannot be inside cdef class bodies; preprocessor inlines .pxi content before Cython sees it"
    alternatives: ["Keep single 2795-line file", "Subclass approach (breaks cohesion)"]
metrics:
  duration: ~5 min
  completed: 2026-02-03
---

# Quick Task 011: Split qint.pyx via Build Preprocessor - Summary

**One-liner:** Build-time preprocessor inlines 4 .pxi section files into qint.pyx before Cython compilation, reducing source from 2795 to 701 lines while maintaining identical compiled output.

## What Was Done

### Task 1: Create preprocessor and split qint.pyx into .pxi files

Created `build_preprocessor.py` at project root with:
- `process_includes(source_file, output_file)` - scans for `include "file.pxi"` directives and inlines content
- `preprocess_all(src_dir)` - finds all .pyx files with includes and generates `*_preprocessed.pyx` files
- Uses `re.MULTILINE` flag for correct multi-line file scanning

Extracted 4 operation sections from qint.pyx into .pxi files:

| File | Lines | Content |
|------|-------|---------|
| qint_arithmetic.pxi | 641 | Addition, subtraction, multiplication, QFT operations |
| qint_bitwise.pxi | 657 | AND, OR, XOR, NOT, shift operations |
| qint_comparison.pxi | 468 | Equality, less-than, greater-than, with layer tracking |
| qint_division.pxi | 333 | Floor division, modulo, divmod |

Replaced sections in qint.pyx with `include "qint_*.pxi"` directives. Result: 701 lines (down from 2795).

Added `*_preprocessed.pyx` to `.gitignore` (build artifacts).

### Task 2: Integrate preprocessor into setup.py

Modified setup.py to:
1. Import `preprocess_all` from `build_preprocessor`
2. Call `preprocess_all()` before extension discovery
3. Skip `*_preprocessed.pyx` files from the glob loop
4. Swap source to preprocessed version for files with include directives
5. Module name stays `quantum_language.qint` (not `qint_preprocessed`)

Build and test verification:
- `python3 setup.py build_ext --inplace` compiles cleanly
- `from quantum_language.qint import qint` imports successfully
- All tests pass identically to baseline (33 passed, 1 pre-existing failure, same as before)

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 482d4fb | refactor | Split qint.pyx into core + 4 .pxi section files |
| fb9bdb8 | feat | Integrate build preprocessor into setup.py |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| `wc -l qint.pyx` | 701 lines (under 800 target) |
| 4 .pxi files exist | qint_arithmetic, qint_bitwise, qint_comparison, qint_division |
| `python3 build_preprocessor.py` | Runs cleanly, produces qint_preprocessed.pyx |
| Preprocessed matches original | Diff shows zero differences (excluding BEGIN/END markers) |
| `grep -c 'include "qint_' qint.pyx` | 4 |
| `python3 -c "from quantum_language.qint import qint"` | OK |
| Tests | 33 passed, 1 failed (pre-existing), identical to baseline |
| `*_preprocessed.pyx` in .gitignore | Yes |

## Key Technical Detail

The approach works by running the preprocessor *before* Cython's `cythonize()` in setup.py. The preprocessed file is a build artifact (gitignored) that contains the full monolithic source Cython expects. The source `.pxi` files are the maintained artifacts, giving developers modular 600-line files instead of one 2800-line file.

---

*Quick task completed: 2026-02-03*
*Duration: ~5 minutes*
*Outcome: Success - qint.pyx split working with preprocessor*
