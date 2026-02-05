---
phase: 47-detail-mode-public-api
plan: 02
subsystem: visualization
tags: [draw-circuit, auto-zoom, public-api, lazy-import]
depends_on: [47-01]
provides: [draw_circuit-api, auto-zoom-logic, lazy-pillow-import]
affects: []
tech-stack:
  added: []
  patterns: [lazy-import-for-optional-deps, auto-zoom-dispatch]
key-files:
  created: []
  modified:
    - src/quantum_language/draw.py
    - src/quantum_language/__init__.py
    - tests/test_draw_render.py
decisions:
  - id: VIZ-AUTOZOOM-BOTH
    description: "Overview only when BOTH qubits > 30 AND layers > 200 exceeded; detail otherwise"
metrics:
  duration: ~5 min
  completed: 2026-02-03
---

# Phase 47 Plan 02: Public API (draw_circuit) Summary

**One-liner:** draw_circuit() with auto-zoom dispatch, mode override, save parameter, and lazy Pillow import via ql namespace

## What Was Done

### Task 1: Add draw_circuit() with auto-zoom and lazy import
- Added `AUTO_DETAIL_MAX_QUBITS = 30` and `AUTO_DETAIL_MAX_LAYERS = 200` constants to draw.py
- Implemented `draw_circuit(circuit, *, mode=None, save=None)` function with:
  - Auto-zoom: selects detail mode unless BOTH thresholds exceeded
  - Mode override: `mode="overview"` or `mode="detail"` with validation
  - Warning when forcing detail mode on large circuits
  - Save parameter for writing image to file
- Added lazy import wrapper in `__init__.py` so `ql.draw_circuit()` works without Pillow at import time
- Added `draw_circuit` to `__all__`

### Task 2: Add auto-zoom, API, and boundary tests
- 8 new test classes with 10 test methods covering:
  - Auto-zoom selects detail for small circuits
  - Auto-zoom selects overview for large circuits (both thresholds exceeded)
  - Boundary: single threshold exceeded stays in detail mode (AND logic)
  - Mode override to overview on small circuit
  - Mode override to detail on large circuit (with warning)
  - Invalid mode raises ValueError
  - Save parameter writes PNG to disk
  - Return type is PIL.Image.Image

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed auto-zoom AND logic**
- **Found during:** Task 2 (test execution)
- **Issue:** Initial implementation used `detail = (q <= 30 AND l <= 200)` which meant overview when EITHER threshold exceeded. Plan specifies overview only when BOTH exceeded.
- **Fix:** Changed to `detail = (q <= 30 OR l <= 200)` so overview only triggers when both thresholds are exceeded simultaneously.
- **Files modified:** src/quantum_language/draw.py
- **Commit:** 6d00b76

**2. [Rule 3 - Blocking] Fixed ruff B904 lint error**
- **Found during:** Task 1 commit
- **Issue:** `raise ImportError(...)` inside `except ImportError` without `from` clause
- **Fix:** Added `from err` to the re-raise
- **Files modified:** src/quantum_language/__init__.py
- **Commit:** 33ebc8a

## Verification Results

- All 39 tests pass (29 existing + 10 new) with zero regressions
- `ql.draw_circuit()` accessible from top-level namespace
- Auto-zoom correctly dispatches based on circuit size
- Mode override works for both overview and detail
- Save parameter writes PNG to disk
- Invalid mode raises ValueError
- `draw_circuit` in `ql.__all__`

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| VIZ-AUTOZOOM-BOTH | Overview only when BOTH qubits AND layers thresholds exceeded | Keeps detail mode available for circuits that are large in only one dimension (many qubits but few layers, or vice versa) |

## Next Phase Readiness

This completes Phase 47 and the v1.9 milestone. The pixel-art circuit visualization system is fully functional with:
- Overview mode (3px cells, scales to 200+ qubits)
- Detail mode (12px cells, text labels, for readable circuits)
- Auto-zoom public API with smart defaults
- Lazy Pillow import for safe package loading
