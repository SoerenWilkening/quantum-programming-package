---
phase: 98-local-diffusion-operator
plan: 01
subsystem: quantum-walk
tags: [montanaro, backtracking, diffusion, ry-cascade, height-control, qbool, reflection]

requires:
  - phase: 97-tree-encoding-predicate-interface
    provides: QWalkTree with one-hot height register and per-level branch registers

provides:
  - _setup_diffusion() precomputes angles for all depth levels at construction
  - local_diffusion(depth) emits height-controlled D_x reflection gates
  - diffusion_info(depth) returns angle data for inspection/debugging
  - _height_qubit(depth) maps depth to physical qubit index
  - Flat cascade gate planning with CCRy decomposition for arbitrary d
  - _make_qbool_wrapper() creates proper 64-element qbool wrappers

affects: [98-02-statevector-tests, 99-walk-operators, 100-variable-branching, 101-detection-demo]

tech-stack:
  added: []
  patterns: [flat-cascade-planning, compiled-cascade-for-height-control, qbool-64-element-wrapper, ry-cascade-binary-splitting, ccry-v-gate-decomposition]

key-files:
  created: []
  modified:
    - src/quantum_language/walk.py

key-decisions:
  - "Flat cascade gate planning avoids framework nested control context limitation (qbool with blocks cannot nest)"
  - "Pre-planned cascade ops compiled via @ql.compile for height-controlled dispatch"
  - "CCRy decomposed using V-gate pattern: CRy(theta/2) CNOT CRy(-theta/2) CNOT CRy(theta/2)"
  - "_make_qbool_wrapper creates 64-element numpy arrays for gate emission compatibility"
  - "Binary splitting cascade uses balanced left=ceil(d/2), right=floor(d/2) for arbitrary d"

patterns-established:
  - "_make_qbool_wrapper(qubit_idx) pattern for wrapping existing qubits without allocation"
  - "Pre-plan gate ops at construction, compile, then replay inside controlled context"
  - "Module-level helper functions for cascade recursion (not class methods)"

requirements-completed: [DIFF-01, DIFF-02]

duration: 18min
completed: 2026-03-02
---

# Plan 98-01: Local Diffusion Operator Summary

**D_x local diffusion with Ry cascade, height-controlled dispatch via compiled cascade, and CCRy decomposition for arbitrary branching degree**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-02T18:04:16Z
- **Completed:** 2026-03-02T18:22:28Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- _setup_diffusion() precomputes phi, cascade angles, root_phi, and pre-plans cascade gate operations at construction
- local_diffusion(depth) emits the full U-S0-U_dagger reflection controlled on h[depth] for any depth
- Flat cascade gate planning resolves framework limitation where nested `with qbool:` contexts are not supported
- Supports arbitrary branching degree d (verified d=1 through d=5) with CCRy decomposition for d>4
- diffusion_info(depth) provides angle inspection data for debugging and testing

## Task Commits

1. **Task 1: Angle precomputation and diffusion_info** - `e2c9b58` (feat)
2. **Task 2: local_diffusion with height-controlled dispatch** - `b3aa054` (feat)

## Files Created/Modified
- `src/quantum_language/walk.py` - Added _setup_diffusion(), local_diffusion(), diffusion_info(), _height_qubit(), _make_qbool_wrapper(), _plan_cascade_ops(), _emit_cascade_ops(), and supporting helpers

## Decisions Made
- **Flat cascade planning**: The ql framework does not support nested `with qbool:` control contexts (quantum-quantum AND not implemented). Resolved by pre-planning all cascade gate operations at construction time as a flat list of (gate_type, qubit, angle, control) tuples, then compiling them via @ql.compile for height-controlled replay. This avoids all nesting.
- **_make_qbool_wrapper**: qbool(create_new=False, bit_list=[idx]) creates a 1-element list for qubits, but gate emission requires qubits[63] on a 64-element array. The helper creates proper numpy arrays.
- **CCRy decomposition**: For branching d>4 (3+ qubit registers), multi-controlled Ry gates are decomposed using the V-gate pattern with only single-controlled gates and CNOTs.
- **Binary splitting**: The cascade uses balanced binary splitting (ceil(d/2) left, floor(d/2) right) rather than sequential peeling, producing a shallower circuit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed qbool wrapper qubit array size**
- **Found during:** Task 2 (local_diffusion implementation)
- **Issue:** qbool(create_new=False, bit_list=[idx]) creates a 1-element qubit list, but emit_ry accesses ctrl.qubits[63] for the control qubit index, causing IndexError
- **Fix:** Created _make_qbool_wrapper() that builds proper 64-element numpy arrays with qubit at index 63
- **Files modified:** src/quantum_language/walk.py
- **Verification:** All controlled gate emissions work correctly inside `with qbool:` contexts
- **Committed in:** b3aa054

**2. [Rule 3 - Blocking] Resolved nested control context limitation**
- **Found during:** Task 2 (cascade implementation for d>2)
- **Issue:** Framework `with qbool:` contexts cannot nest (quantum-quantum AND not implemented). The recursive cascade uses `with qbool:` for conditional rotations, which fails inside the outer `with h_control:` height dispatch
- **Fix:** Replaced recursive cascade with pre-planned flat gate sequence. Cascade ops are pre-computed at construction and compiled via @ql.compile. When called inside `with h_control:`, the compile framework auto-derives the height-controlled variant from the captured gate sequence.
- **Files modified:** src/quantum_language/walk.py
- **Verification:** All branching degrees d=1..5 work correctly with height control
- **Committed in:** b3aa054

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes essential for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- local_diffusion(depth) ready for statevector verification tests (Plan 98-02)
- diffusion_info(depth) available for test angle verification
- Cascade compiled functions cached per (d, w) for efficient reuse
- Walk operators (Phase 99) can call local_diffusion(depth=k) in a loop

---
*Phase: 98-local-diffusion-operator*
*Completed: 2026-03-02*
