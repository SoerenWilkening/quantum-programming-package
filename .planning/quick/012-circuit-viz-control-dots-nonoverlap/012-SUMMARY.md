---
phase: quick-012
plan: 01
subsystem: visualization
tags: [circuit-rendering, pixel-art, control-dots, non-overlapping]
dependency-graph:
  requires: [v1.9-circuit-visualization]
  provides: [distinct-control-dots, non-overlapping-mode]
  affects: []
tech-stack:
  added: []
  patterns: [greedy-bin-packing-for-layer-expansion]
key-files:
  created: []
  modified:
    - src/quantum_language/draw.py
    - tests/test_draw_render.py
decisions:
  - id: QDOT-01
    title: "White control dots for maximum contrast"
    choice: "CTRL_DOT_COLOR = (255, 255, 255)"
    reason: "Maximum visual distinction from yellow CTRL_COLOR = (255, 255, 100) control lines"
metrics:
  duration: ~4 min
  completed: 2026-02-03
---

# Quick Task 012: Circuit Viz Control Dots + Non-Overlapping Mode Summary

**One-liner:** White control dots distinct from yellow control lines, plus greedy non-overlapping layer expansion mode.

## What Was Done

### Task 1: Distinct control dot color + non-overlapping layer expansion
- Added `CTRL_DOT_COLOR = (255, 255, 255)` constant (bright white) to distinguish control dots from `CTRL_COLOR = (255, 255, 100)` (yellow) used for connection lines
- Updated `render()` overview mode: control dot pixel uses `CTRL_DOT_COLOR`
- Updated `render_detail()` detail mode: control dot ellipse fill uses `CTRL_DOT_COLOR`
- Added `expand_overlapping_layers(draw_data)` function: greedy bin-packing algorithm that splits overlapping gates in the same layer into consecutive visual sub-columns
- Added `overlap` parameter (default `True`) to `render()`, `render_detail()`, and `draw_circuit()`
- Updated 6 existing tests to expect `CTRL_DOT_COLOR` at dot positions instead of `CTRL_COLOR`

### Task 2: Tests for new features
- 3 tests for control dot color distinction (constant differs, overview dot pixel, detail dot pixel)
- 4 tests for non-overlapping mode (expands when needed, no-op when no conflicts, default backward compat, draw_circuit passthrough)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated existing tests for CTRL_DOT_COLOR**
- **Found during:** Task 1
- **Issue:** 6 existing tests checked for `CTRL_COLOR` at control dot positions, which now use `CTRL_DOT_COLOR`
- **Fix:** Updated tests to import `CTRL_DOT_COLOR` and check for the correct color at dot pixels, while keeping `CTRL_COLOR` checks for control line pixels
- **Files modified:** tests/test_draw_render.py
- **Commit:** cf0bef5

## Verification

- All 46 tests pass (39 existing + 7 new)
- Smoke test confirms `CTRL_DOT_COLOR != CTRL_COLOR`
- Default `overlap=True` preserves all existing behavior (backward compatible)
