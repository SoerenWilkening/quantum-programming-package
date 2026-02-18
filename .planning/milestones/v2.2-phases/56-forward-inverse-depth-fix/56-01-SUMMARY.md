---
phase: 56-forward-inverse-depth-fix
plan: 01
subsystem: testing
tags: [depth, layer_floor, compile, diagnostics, circuit-optimization]

# Dependency graph
requires:
  - phase: 55-profiling-infrastructure
    provides: profiling tools for performance analysis
provides:
  - Diagnostic tests for depth discrepancy analysis
  - Root cause documentation for capture vs replay depth difference
  - Verified findings that forward/adjoint replays have equal depth
affects: [56-02, performance-optimization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Depth measurement pattern using get_current_layer() before/after"
    - "Layer floor diagnostic pattern using _get_layer_floor()"

key-files:
  created: []
  modified:
    - tests/test_compile.py

key-decisions:
  - "Forward and adjoint replays produce equal depths - no fix needed for that"
  - "Real discrepancy is capture vs replay when capture allows parallelization"
  - "Root cause is layer_floor constraint in compile.py lines 984-994"

patterns-established:
  - "DEPTH-DIAG test pattern: measure layer before/after operation"

# Metrics
duration: 5min
completed: 2026-02-05
---

# Phase 56 Plan 01: Depth Diagnostic Tests Summary

**Diagnostic tests prove forward/adjoint replays have equal depth; actual discrepancy is capture vs replay due to layer_floor constraint**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-05T13:55:21Z
- **Completed:** 2026-02-05T14:00:41Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created 5 diagnostic tests measuring capture, forward replay, and adjoint replay depths
- Identified that forward/adjoint replays produce EQUAL depths (no fix needed for that)
- Documented root cause: layer_floor constraint in _replay() prevents gate packing
- Proved mechanism with test_layer_floor_causes_depth_inflation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Diagnostic Depth Comparison Tests** - `edfd262` (test)
2. **Task 2: Profile and Document Root Cause** - `bd56ab4` (docs)

## Files Created/Modified

- `tests/test_compile.py` - Added 5 diagnostic tests and root cause documentation

## Decisions Made

1. **Forward/adjoint depth discrepancy does not exist** - Tests prove both replay paths produce equal circuit depth. The original concern from ROADMAP.md was based on a hypothesis that turned out to be incorrect.

2. **Real discrepancy is capture vs replay** - When capture occurs after operations on non-overlapping qubits, gates can pack into earlier layers (depth=0 possible). But replay sets layer_floor=current_layer, forcing gates to start at current position (higher depth).

3. **Two fix approaches identified:**
   - Option 1: Set layer_floor during capture too (consistency, simpler)
   - Option 2: Store relative layer offsets during capture, apply during replay (preserves optimization)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - diagnostics ran cleanly and produced clear results.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Diagnostic tests provide baseline for evaluating any fix in Plan 02
- Root cause documented with specific line numbers (compile.py:984-994)
- Key finding: The SUCCESS criterion from ROADMAP "f(x) produces circuit depth equal to f.inverse(x)" is ALREADY MET for replay paths

### Important Note for Plan 02

The original phase objective assumed forward/inverse depth discrepancy. Tests show:
- Forward replay depth == Adjoint replay depth (no fix needed)
- Capture depth can differ from replay depth (may or may not need fixing)

Plan 02 should reassess whether the capture/replay discrepancy is actually a problem:
- If both are correct circuit behavior, no fix needed
- If consistency is required, apply one of the documented fix approaches

---
*Phase: 56-forward-inverse-depth-fix*
*Completed: 2026-02-05*
