---
phase: 98-local-diffusion-operator
plan: 02
subsystem: quantum-walk
tags: [montanaro, backtracking, diffusion, statevector, reflection, amplitude-verification, qiskit-aer]

requires:
  - phase: 98-local-diffusion-operator
    provides: QWalkTree.local_diffusion(depth) and diffusion_info(depth)

provides:
  - 25 statevector verification tests for D_x amplitudes across d=2,3,4,5
  - Reflection property D_x^2 = I verified for all branching degrees and depths
  - Root formula amplitude verification (1/sqrt(1+n*d) root, sqrt(n)/sqrt(1+n*d) children)
  - Eigenstate preservation test proving D_x|psi_x> = |psi_x>
  - Height-controlled no-op verification (wrong depth = no effect)

affects: [99-walk-operators, 100-variable-branching, 101-detection-demo]

tech-stack:
  added: []
  patterns: [v-gate-ccry-decomposition, height-controlled-cascade-without-nesting, inline-s0-reflection]

key-files:
  created:
    - tests/python/test_walk_diffusion.py
  modified:
    - src/quantum_language/walk.py

key-decisions:
  - "V-gate decomposition for CCRy avoids nested with-block limitation in height-controlled cascade"
  - "Inline S_0 reflection (X-MCZ-X) replaces @ql.compile diffusion call to avoid first-call control propagation bug"
  - "Toffoli decomposition via H-MCZ-H for CCX in cascade cx operations"
  - "Global phase -1 from S_0 convention is acceptable -- tests use inner product overlap for amplitude matching"

patterns-established:
  - "_emit_cascade_h_controlled pattern: height-controlled cascade emission with V-gate CCRy decomposition"
  - "Amplitude verification via inner product overlap (handles global phase correctly)"
  - "_prepare_at_depth helper for test state preparation"

requirements-completed: [DIFF-03]

duration: 17min
completed: 2026-03-02
---

# Plan 98-02: Statevector Verification Tests Summary

**25 statevector tests verifying D_x amplitude correctness for d=2,3,4,5, root formula, eigenstate preservation, and reflection property D_x^2=I with bug fix for height-controlled dispatch**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-02T18:26:07Z
- **Completed:** 2026-03-02T18:43:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- 25 comprehensive statevector tests covering DIFF-01 (non-root), DIFF-02 (root), and DIFF-03 (amplitude verification)
- Fixed critical bug in local_diffusion: compiled cascade functions did not propagate height control context on first call
- D_x^2 = I reflection property verified for d=2, 3, 4, 5 at both root and non-root depths
- Root formula amplitudes (1/sqrt(1+n*d), sqrt(n)/sqrt(1+n*d)) verified against Montanaro 2015
- Eigenstate preservation test: D_x|psi_x> = |psi_x> confirmed within 1e-6 tolerance

## Task Commits

1. **Bug fix: height-controlled dispatch** - `89462c5` (fix)
2. **Statevector verification tests** - `d6abc7d` (feat)

## Files Created/Modified
- `tests/python/test_walk_diffusion.py` - 584 lines, 25 tests: TestDiffusionNonRoot (11), TestDiffusionRoot (6), TestDiffusionAmplitudes (8)
- `src/quantum_language/walk.py` - Added _emit_cascade_h_controlled(), rewrote local_diffusion() to avoid nested with-blocks and @ql.compile first-call bug

## Decisions Made
- **V-gate CCRy decomposition**: For cascade CRy operations that need height control (creating CCRy), used the V-gate decomposition: CRy(t/2) CNOT CRy(-t/2) CNOT CRy(t/2) to avoid nested `with qbool:` contexts which the framework does not support
- **Inline S_0 reflection**: Replaced `ql.diffusion()` call (which is @ql.compile-decorated) with raw X-MCZ-X gate emission. The @ql.compile first-call mechanism emits uncontrolled gates when called inside a control context for the first time, then caches the controlled variant for subsequent calls. Since ql.circuit() resets caches, the first call per circuit is always uncontrolled.
- **Amplitude matching via inner product**: The S_0 convention (X-MCZ-X) introduces a global phase of -1 compared to the textbook 2|psi><psi|-I. Tests use |<expected|observed>| = 1 overlap check instead of direct amplitude comparison, correctly handling global phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed height-controlled dispatch for local_diffusion**
- **Found during:** Task 1 (writing statevector tests)
- **Issue:** @ql.compile compiled cascade functions emit uncontrolled gates on first call inside a `with qbool:` control context. The controlled variant is derived and cached, but the first call's gates are already emitted uncontrolled. Since ql.circuit() resets all caches, every circuit's first local_diffusion call emits incorrect uncontrolled cascade gates.
- **Fix:** Replaced compiled cascade calls with _emit_cascade_h_controlled() which emits each gate individually with height control. CCRy operations use V-gate decomposition (5 single-controlled gates). Inline S_0 reflection replaces @ql.compile diffusion call. The `with h_control:` block is used only for single-qubit gates (Ry, X) that don't need nested control.
- **Files modified:** src/quantum_language/walk.py
- **Verification:** D_x^2 = I confirmed for d=2,3,4,5 at root and non-root depths. All 25 tests pass.
- **Committed in:** 89462c5

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was essential for test correctness. Without it, no statevector test could pass. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- local_diffusion(depth) fully verified with statevector tests
- Walk operators (Phase 99) can call local_diffusion(depth=k) in a loop with confidence
- Height-controlled cascade pattern established for future use
- All 57 walk-related tests pass (18 tree + 14 predicate + 25 diffusion)

---
*Phase: 98-local-diffusion-operator*
*Completed: 2026-03-02*
