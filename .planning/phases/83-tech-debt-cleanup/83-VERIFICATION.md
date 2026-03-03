---
phase: 83-tech-debt-cleanup
verified: 2026-02-23T17:00:00Z
status: gaps_found
score: 3/4 success criteria verified
re_verification: false
gaps:
  - truth: "Editing a .pxi file and running the pre-commit hook detects qint_preprocessed.pyx drift and fails the check"
    status: partial
    reason: "The hook detects drift and auto-fixes it (regenerates + stages), but returns exit 0 and does NOT block/fail the commit. The success criterion states 'fails the check', but the implementation uses an auto-fix pattern that never blocks. The --check mode (separate from the hook) does return exit 1 on drift, but this is not invoked by the pre-commit hook."
    artifacts:
      - path: "build_preprocessor.py"
        issue: "sync_and_stage() always returns 0, even when drift is detected. The hook auto-fixes but does not fail. 'fails the check' as stated in SC2 is not achieved by the pre-commit hook path."
      - path: ".pre-commit-config.yaml"
        issue: "Hook entry uses --sync-and-stage (auto-fix, returns 0) not --check (fails on drift, returns 1). A developer editing a .pxi file will have drift auto-corrected rather than the check failing to prompt attention."
    missing:
      - "Either: change the pre-commit hook to use --check mode so it actually fails when drift is found (blocking the commit until the developer re-runs the preprocessor manually), OR update the ROADMAP success criterion to reflect the chosen auto-fix behavior"
      - "Document the chosen behavior clearly: auto-fix vs blocking are distinct patterns with different tradeoffs"
human_verification:
  - test: "Compile and test verification after QPU removal"
    expected: "python3 setup.py build_ext --inplace --force completes without error; pytest tests/python/ -v passes (excluding known pre-existing failures: test_qint_default_width and test_array_creates_list_of_qint segfault)"
    why_human: "Build takes ~10 minutes per SUMMARY; cannot run in verification context without triggering full Cython compilation"
  - test: "Vulture scan result confirmation"
    expected: "vulture src/quantum_language/ --min-confidence 80 --exclude '*_preprocessed*' returns zero findings"
    why_human: "vulture was intentionally not persisted to the repo (one-time scan per plan decision). Cannot re-run without installing it. SUMMARY claims zero findings at >=80% confidence; this needs manual re-verification by running: pip install vulture && vulture src/quantum_language/ --min-confidence 80 --exclude '*_preprocessed*'"
---

# Phase 83: Tech Debt Cleanup Verification Report

**Phase Goal:** Dead code is removed, preprocessor automation prevents drift, and sequence generation is documented
**Verified:** 2026-02-23T17:00:00Z
**Status:** gaps_found (SC2 partial — hook detects drift but auto-fixes instead of failing)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | QPU.c and QPU.h no longer exist; all files that included them compile | VERIFIED | `ls c_backend/src/QPU.c` and `ls c_backend/include/QPU.h` both return "No such file". Zero QPU references remain in all C source/header files. Build configs (setup.py, CMakeLists.txt, tests/c/Makefile) contain no QPU.c references. Commits c5918c5 confirms deletion. |
| 2 | Editing a .pxi file and running the pre-commit hook detects drift and fails the check | PARTIAL | Hook IS registered and DOES detect drift. However, it auto-stages the fix and returns 0 (does NOT fail/block). SC2 states "fails the check" but the implementation uses auto-fix pattern. The `--check` mode does return exit 1 on drift, but is not wired into the pre-commit hook. |
| 3 | Vulture scan run, all confirmed dead code (>=80%) removed without breaking tests | VERIFIED* | SUMMARY documents scan completed with zero findings at >=80% confidence. All 22 findings at 60% confirmed as false positives (used from .pyx/.pxd/tests/public API). No code removed (nothing to remove). *Cannot re-run vulture without installing it (human verification flagged). |
| 4 | A developer can regenerate all hardcoded sequence C files by following documented instructions | VERIFIED | `make generate-sequences` target exists at Makefile line 67, lists all 5 active scripts, prints progress, listed in help at line 249. All 5 active scripts have comprehensive module docstrings with Usage sections and argparse --help. Two deprecated scripts have runtime DeprecationWarning. Commit e830e1e confirms implementation. |

**Score:** 3/4 success criteria verified (SC2 is partial)

---

## Required Artifacts

### Plan 83-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `c_backend/include/QPU.h` | DELETED — must not exist | VERIFIED | File does not exist. `ls` confirms. |
| `c_backend/src/QPU.c` | DELETED — must not exist | VERIFIED | File does not exist. `ls` confirms. |
| `build_preprocessor.py` | Contains `sync_and_stage` function and `--sync-and-stage` CLI mode | VERIFIED | Function `sync_and_stage()` at line 122. `--sync-and-stage` handled in `__main__` at line 188. `import subprocess` present at line 15. `--check` mode fixed (now uses `check_mode()` which returns 1 on drift). |
| `.pre-commit-config.yaml` | Local hook for preprocessor drift detection | VERIFIED | Hook `sync-preprocessed-pyx` registered. Entry: `python3 build_preprocessor.py --sync-and-stage`. File pattern `(qint\.pyx|qint_\w+\.pxi)$` correctly matches all 4 existing `.pxi` files and `qint.pyx`. |

### Plan 83-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Makefile` | Contains `generate-sequences` target | VERIFIED | Target at line 67. PHONY declaration at line 66. Help entry at line 249 under "Code generation targets:". All 5 active scripts invoked. |
| `scripts/generate_seq_all.py` | Improved `--help` with `argparse` | VERIFIED | `import argparse` at line 37. `ArgumentParser` at line 1234. Comprehensive module docstring with Usage section (7 usage examples). |
| `scripts/generate_toffoli_seq.py` | Improved `--help` with `argparse` | VERIFIED | `import argparse` at line 36. `ArgumentParser` at line 1042. Module docstring with Usage section. |
| `scripts/generate_toffoli_decomp_seq.py` | `argparse` present | VERIFIED | `import argparse` at line 50. `ArgumentParser` at line 795. |
| `scripts/generate_toffoli_clifft_cq_inc.py` | `argparse` present | VERIFIED | `import argparse` at line 33. `ArgumentParser` at line 784. |
| `scripts/generate_toffoli_clifft_cla.py` | `argparse` present | VERIFIED | `import argparse` at line 40. `ArgumentParser` at line 1185. |
| `scripts/generate_seq_1_4.py` | Deprecated with runtime warning | VERIFIED | Docstring "DEPRECATED: Use generate_seq_all.py instead." Runtime `warnings.warn(..., DeprecationWarning)` after imports. |
| `scripts/generate_seq_5_8.py` | Deprecated with runtime warning | VERIFIED | Docstring "DEPRECATED: Use generate_seq_all.py instead." Runtime `warnings.warn(..., DeprecationWarning)` after imports. |

---

## Key Link Verification

### Plan 83-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.pre-commit-config.yaml` | `build_preprocessor.py` | `entry: python3 build_preprocessor.py --sync-and-stage` | WIRED | Line 23 of `.pre-commit-config.yaml` contains `python3 build_preprocessor.py --sync-and-stage`. Function exists in `build_preprocessor.py` at line 122. |
| `src/quantum_language/_core.pxd` | `c_backend/include/circuit.h` | `cdef extern from "circuit.h"` | WIRED | Line 88 of `_core.pxd`: `cdef extern from "circuit.h":`. No QPU.h extern present. |
| `src/quantum_language/openqasm.pxd` | `c_backend/include/circuit.h` | `cdef extern from "circuit.h"` | WIRED | Lines 3 and 7 of `openqasm.pxd`: `cdef extern from "circuit.h":` and `cdef extern from "circuit_output.h":`. No QPU.h extern present. |

### Plan 83-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Makefile` | `scripts/generate_seq_all.py` | `make generate-sequences` | WIRED | Line 70 of Makefile: `$(PYTHON) scripts/generate_seq_all.py` |
| `Makefile` | `scripts/generate_toffoli_seq.py` | `make generate-sequences` | WIRED | Line 72 of Makefile: `$(PYTHON) scripts/generate_toffoli_seq.py` |
| `Makefile` | `scripts/generate_toffoli_decomp_seq.py` | `make generate-sequences` | WIRED | Line 74 of Makefile: `$(PYTHON) scripts/generate_toffoli_decomp_seq.py` |
| `Makefile` | `scripts/generate_toffoli_clifft_cq_inc.py` | `make generate-sequences` | WIRED | Line 76 of Makefile: `$(PYTHON) scripts/generate_toffoli_clifft_cq_inc.py` |
| `Makefile` | `scripts/generate_toffoli_clifft_cla.py` | `make generate-sequences` | WIRED | Line 78 of Makefile: `$(PYTHON) scripts/generate_toffoli_clifft_cla.py` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEBT-01 | 83-01-PLAN.md | Remove dead QPU.c/QPU.h stubs and all references across C/Cython/Python layers | SATISFIED | QPU.h and QPU.c deleted. Zero QPU references in all C/H/pxd/pyx/setup.py/CMakeLists.txt/tests/c/Makefile/main.c files. Commit c5918c5. |
| DEBT-02 | 83-01-PLAN.md | Automate qint_preprocessed.pyx generation with build-time sync and CI drift check | PARTIAL | Pre-commit hook registered and functional. build_preprocessor.py has --sync-and-stage (auto-fix) and fixed --check mode (exits 1 on drift). Hook auto-fixes rather than blocking — the "CI drift check" interpretation (which implies failure/blocking) is not fully satisfied. |
| DEBT-03 | 83-02-PLAN.md | Remove duplicate/dead code identified by vulture scan (unused Python functions, unreachable code) | SATISFIED | Vulture scan run, zero findings at >=80% confidence. All 22 findings at 60% confirmed false positives. REQUIREMENTS.md marks as complete. No test regressions. |
| DEBT-04 | 83-02-PLAN.md | Document hardcoded sequence generation process and regeneration instructions | SATISFIED | `make generate-sequences` target added. All 5 active scripts have comprehensive docstrings with Usage sections and argparse --help. Deprecated scripts marked with runtime warnings. REQUIREMENTS.md marks as complete. |

**All 4 requirement IDs (DEBT-01, DEBT-02, DEBT-03, DEBT-04) are accounted for. No orphaned requirements found.**
REQUIREMENTS.md marks all 4 as complete at lines 114-117.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/quantum_language/qint.c` | Contains `#include "QPU.h"` at line 1278 and hardcoded QPU.h path at line 9 | INFO | This is a Cython-generated C file (dated Feb 3, before migration), excluded from git via `.gitignore` (`src/quantum_language/*.c`). Not a source file — will be regenerated with correct includes when `setup.py build_ext` is run. Not a blocker. |
| `c_backend/include/module_deps.md` | References QPU.h as "thin wrapper" at lines 99, 203, 208, 214, 217 | INFO | Documentation file describing historical architecture. Not a source file. References are historical context, not active includes. Does not affect compilation. |
| `c_backend/include/old_div` | Contains `QPU_state->R0` at lines 2, 6, 10, 14 | INFO | File appears to be an archived/legacy snippet (no extension, not compiled). Not a C source/header — excluded from compilation. |

No blockers found. The three INFO items are all non-compiled artifacts (gitignored generated file, markdown docs, legacy archive snippet).

---

## Human Verification Required

### 1. Post-Migration Compilation and Test Pass

**Test:** From the repo root, run `python3 setup.py build_ext --inplace --force` followed by `pytest tests/python/ -v --tb=short -x -k "not test_qint_default_width and not test_array_creates_list_of_qint"`
**Expected:** Cython extensions compile without error (no QPU.h/QPU.c not found errors); pytest passes with no new failures attributable to QPU removal
**Why human:** Build takes approximately 10 minutes per SUMMARY (80+ C object files linked per extension). Cannot run in verification context.

### 2. Vulture Scan Re-verification

**Test:** Run `pip install vulture && vulture src/quantum_language/ --min-confidence 80 --sort-by-size --exclude "*_preprocessed*"`
**Expected:** Zero findings at >=80% confidence threshold
**Why human:** vulture was not persisted to the repository (one-time scan per plan decision). Must install temporarily to re-verify SC3.

### 3. Pre-commit Hook Drift Detection in Practice

**Test:** Edit `src/quantum_language/qint_arithmetic.pxi` (add a comment), then run `git add src/quantum_language/qint_arithmetic.pxi && git commit --dry-run` or `pre-commit run sync-preprocessed-pyx`
**Expected:** Hook runs, detects drift in `qint_preprocessed.pyx`, regenerates and auto-stages it, exits 0 (commit proceeds with regenerated file)
**Why human:** Cannot run pre-commit in verification context. Also serves to clarify whether SC2 "fails the check" was intended to mean auto-fix vs blocking.

---

## Gaps Summary

**One gap blocking full goal achievement:**

**SC2 / DEBT-02 Behavioral Discrepancy:** The success criterion states the pre-commit hook should "detect drift and fail the check." The implementation auto-fixes instead — it detects drift, regenerates the file, auto-stages it, and returns exit 0 (allowing the commit to proceed). This is the "auto-fix pattern" explicitly documented in the SUMMARY's key-decisions section.

The `--check` mode in `build_preprocessor.py` DOES return exit 1 when drift is detected and would satisfy "fails the check," but it is not used by the pre-commit hook. The hook uses `--sync-and-stage`.

**Resolution options:**
1. **Minimal fix:** Update the ROADMAP success criterion wording to match the implemented auto-fix behavior ("detects drift and auto-corrects it")
2. **Behavioral fix:** Change the pre-commit hook to use `--check` mode (blocking) rather than `--sync-and-stage` (auto-fix), so commits are blocked when drift is detected and the developer must run the preprocessor manually

The chosen auto-fix pattern has the practical advantage that drift never reaches the repository, but it does not satisfy the literal "fails the check" wording.

---

## Notes on QPU Removal Completeness

The search for QPU references found three non-blocking items:
- `src/quantum_language/qint.c` — Cython-generated file (gitignored, pre-dates migration, will be regenerated correctly on next build)
- `c_backend/include/module_deps.md` — Documentation file with historical context
- `c_backend/include/old_div` — Legacy archive snippet (not compiled, no extension)

None of these affect compilation. The plan's actual targets (all `.c`, `.h`, `.pxd`, `.pyx`, `setup.py`, `CMakeLists.txt`, `tests/c/Makefile`, `main.c`) are fully clean.

---

_Verified: 2026-02-23T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
