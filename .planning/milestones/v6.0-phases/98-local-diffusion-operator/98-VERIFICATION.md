---
phase: 98-local-diffusion-operator
verified: 2026-03-02T19:10:00Z
status: passed
score: 3/3 must-haves verified
must_haves:
  truths:
    - "Local diffusion D_x for uniform branching uses phi = 2*arctan(sqrt(d)) and produces amplitudes matching 1/sqrt(d(x)+1)"
    - "Root node diffusion uses a separate phi_root formula and is controlled on the root height qubit h[max_depth]"
    - "Statevector tests confirm |psi_x| amplitudes match the 1/sqrt(d(x)+1) tolerance for non-root nodes and the correct root formula for the root node"
  artifacts:
    - path: "src/quantum_language/walk.py"
      provides: "_setup_diffusion(), local_diffusion(depth), diffusion_info(depth), _height_qubit(depth), _emit_cascade_h_controlled()"
    - path: "tests/python/test_walk_diffusion.py"
      provides: "25 statevector tests verifying DIFF-01, DIFF-02, DIFF-03"
  key_links:
    - from: "src/quantum_language/walk.py"
      to: "quantum_language._gates.emit_ry"
      via: "import and direct call for Ry rotations in cascade"
    - from: "src/quantum_language/walk.py"
      to: "quantum_language.diffusion._collect_qubits"
      via: "import for S_0 reflection qubit collection"
    - from: "src/quantum_language/walk.py"
      to: "quantum_language.qbool.qbool"
      via: "_make_qbool_wrapper for height qubit controlled context"
    - from: "tests/python/test_walk_diffusion.py"
      to: "src/quantum_language/walk.py"
      via: "import QWalkTree, call local_diffusion() and diffusion_info()"
    - from: "tests/python/test_walk_diffusion.py"
      to: "qiskit_aer"
      via: "_simulate_statevector() helper for circuit verification"
---

# Phase 98: Local Diffusion Operator Verification Report

**Phase Goal:** Users can apply verified-correct local diffusion D_x to any tree node with proper amplitude coefficients
**Verified:** 2026-03-02T19:10:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Local diffusion D_x for uniform branching uses phi = 2*arctan(sqrt(d)) and produces amplitudes matching 1/sqrt(d(x)+1) for parent and each child | VERIFIED | Formula at walk.py:481 `phi = 2.0 * math.atan(math.sqrt(d))`. Amplitude tests: test_diffusion_d2_amplitudes (inner product overlap 1.0), test_amplitude_d2_psi_x_eigenstate (eigenstate preservation), D_x^2=I for d=2,3,4,5 all pass. |
| 2 | Root node diffusion uses a separate phi_root formula (different amplitude weighting) and is controlled on the root height qubit h[max_depth] | VERIFIED | Root formula at walk.py:527 `self._root_phi = 2.0 * math.atan(math.sqrt(n * d_root))`. Root tests: test_root_diffusion_d2_n2_amplitudes, test_root_diffusion_d3_n2_amplitudes, test_root_uses_different_formula_than_nonroot (phi != phi_root confirmed). Height control via `_make_qbool_wrapper(h_qubit_idx)` at walk.py:628. |
| 3 | Statevector tests confirm |psi_x| amplitudes match the 1/sqrt(d(x)+1) tolerance for non-root nodes and the correct root formula for the root node | VERIFIED | 25 tests in test_walk_diffusion.py all pass (25/25). Tests use Qiskit Aer statevector simulator with max_parallel_threads=4. Includes eigenstate preservation (|<psi_x|D_x|psi_x>| = 1.0), orthogonal reflection (eigenvalue -1), reflection property D_x^2=I for d=2,3,4,5, root amplitude matching, per-level branching, depth validation, leaf no-op, wrong-depth no-op, qubit preservation. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/walk.py` | _setup_diffusion(), local_diffusion(), diffusion_info(), _height_qubit(), cascade helpers | VERIFIED | 744 lines. Contains _setup_diffusion (line 454), local_diffusion (line 591), diffusion_info (line 548), _height_qubit (line 529), _make_qbool_wrapper (line 22), _plan_cascade_ops (line 45), _emit_cascade_ops (line 167), _emit_cascade_h_controlled (line 211). |
| `tests/python/test_walk_diffusion.py` | Statevector verification tests for DIFF-01, DIFF-02, DIFF-03 | VERIFIED | 584 lines, 25 tests across 3 classes: TestDiffusionNonRoot (11 tests), TestDiffusionRoot (6 tests), TestDiffusionAmplitudes (8 tests). All 25 pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| walk.py | _gates.emit_ry | `from ._gates import emit_ry, emit_x` (line 18) | WIRED | emit_ry called 11 times in walk.py for Ry rotations in cascade and parent-child split |
| walk.py | diffusion._collect_qubits | `from .diffusion import _collect_qubits` (line 654) | WIRED | Used at line 657 to collect S_0 reflection qubit indices for inline X-MCZ-X pattern |
| walk.py | qbool.qbool | `from .qbool import qbool` inside _make_qbool_wrapper (line 38) | WIRED | qbool(create_new=False, bit_list=arr) creates control wrappers without qubit allocation. Used throughout for height control and cascade control. |
| test_walk_diffusion.py | walk.py | `from quantum_language.walk import QWalkTree` (line 19) | WIRED | tree.local_diffusion() called 27 times, tree.diffusion_info() called 8 times across tests |
| test_walk_diffusion.py | qiskit_aer | `AerSimulator(method="statevector", max_parallel_threads=4)` (line 30) | WIRED | _simulate_statevector() helper used in every statevector test |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DIFF-01 | 98-01-PLAN.md | D_x local diffusion for uniform branching with phi = 2*arctan(sqrt(d)) | SATISFIED | walk.py:481 implements the formula. TestDiffusionNonRoot class (11 tests) verifies non-root D_x including reflection property for d=2,3,4,5, amplitude matching, angle inspection. |
| DIFF-02 | 98-01-PLAN.md | Root node diffusion with separate phi_root formula | SATISFIED | walk.py:527 implements phi_root = 2*arctan(sqrt(n*d)). TestDiffusionRoot class (6 tests) verifies root amplitudes, reflection property, root info, formula difference. |
| DIFF-03 | 98-02-PLAN.md | Statevector tests verifying |psi_x| amplitudes match 1/sqrt(d(x)+1) tolerance | SATISFIED | 25 tests in test_walk_diffusion.py: eigenstate preservation (D_x|psi_x> = |psi_x>), inner product overlap checks, D_x^2=I reflection, root formula amplitudes. All pass. |

No orphaned requirements. DIFF-04 (variable branching) is correctly mapped to Phase 100 in REQUIREMENTS.md and is not expected in Phase 98.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns found |

No TODO/FIXME/PLACEHOLDER comments. No empty implementations. No stub patterns detected. The `return []` at walk.py:71 in `_plan_cascade_ops` for `d <= 1` is correct behavior (no cascade operations needed when branching degree is 0 or 1).

### Human Verification Required

No human verification is required for this phase. All observable truths are verified programmatically via statevector simulation. The key behaviors (amplitude correctness, reflection property, eigenstate preservation) are all captured by the 25 automated tests.

### Gaps Summary

No gaps found. All three success criteria from the ROADMAP are fully verified:

1. The phi formula implementation matches the mathematical specification and is confirmed by amplitude matching tests.
2. The root formula is distinct from non-root and produces correct amplitudes verified by statevector simulation.
3. The test suite is comprehensive (25 tests, 584 lines) covering non-root, root, and amplitude verification including edge cases (leaf no-op, wrong depth no-op, depth validation, qubit preservation, per-level branching).

All 4 implementation commits are verified in git history (e2c9b58, b3aa054, 89462c5, d6abc7d). The Phase 97 regression suite (32 tests) passes without issues. The simulation budget constraint (max 17 qubits, max 4 threads) is respected across all tests.

---

_Verified: 2026-03-02T19:10:00Z_
_Verifier: Claude (gsd-verifier)_
