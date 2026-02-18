---
phase: 46
plan: 01
subsystem: visualization
tags: [renderer, pixel-art, PIL, numpy]
dependency-graph:
  requires: [45]
  provides: [core-renderer, draw-module, gate-colors]
  affects: [46-02, 46-03, 47]
tech-stack:
  added: [Pillow]
  patterns: [numpy-bulk-rendering, cell-grid-layout]
key-files:
  created:
    - src/quantum_language/draw.py
    - tests/test_draw_render.py
  modified:
    - setup.py
decisions:
  - id: REND-CELL-SIZE
    description: "3x3 pixel cells (2px gate + 1px gap)"
  - id: REND-WIRE-OVERLAP
    description: "Wires drawn before gates; measurement checkerboard may overlap wire pixels"
metrics:
  duration: "2m 30s"
  completed: "2026-02-03"
---

# Phase 46 Plan 01: Core Renderer Summary

**NumPy pixel-art renderer with 10 gate colors, wire lines, and measurement checkerboard pattern**

## What Was Done

### Task 1: Create draw.py renderer (074a37f)

Created `src/quantum_language/draw.py` with the full rendering pipeline:

- **Layout engine**: CELL_W=3, CELL_H=3 pixel grid mapping layers and qubits to canvas coordinates
- **Canvas allocation**: NumPy `np.full()` bulk initialization with dark background (20, 20, 30)
- **Wire rendering**: Horizontal lines at `q * CELL_H + CELL_H // 2` for each qubit
- **Gate rendering**: 2x2 colored blocks at `(layer * CELL_W, target * CELL_H)` positions
- **10 gate colors**: Pauli (purple), rotation (cyan), Hadamard (yellow), phase (green), measurement (red)
- **Measurement checkerboard**: Type 9 gates use alternating pixel pattern instead of solid block
- **Empty circuit handling**: Returns 1x1 BG image when num_layers or num_qubits is 0
- **PIL output**: `Image.fromarray(canvas, 'RGB')` for standard image format

Also added `Pillow>=9.0` to `setup.py` `install_requires`.

### Task 2: Add tests (88fe1ab)

Created `tests/test_draw_render.py` with 8 tests:

1. `test_empty_circuit` -- 1x1 image for empty draw_data
2. `test_canvas_dimensions` -- size matches layer/qubit counts
3. `test_background_color` -- majority pixels are BG_COLOR
4. `test_wire_rendering` -- wire color at correct y-coordinates
5. `test_single_qubit_gate_position` -- H gate 2x2 block at expected position
6. `test_all_gate_types_have_colors` -- all 10 types render non-BG colors
7. `test_measurement_checkerboard` -- alternating pattern verified
8. `test_numpy_bulk_operations` -- RGB mode, uint8 dtype confirmed

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| REND-CELL-SIZE | 3x3 pixel cells | 2px gate + 1px implicit gap gives clean pixel art |
| REND-WIRE-OVERLAP | Wires drawn before gates | Wire at y=1 can show through measurement checkerboard gaps; test accounts for this |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Measurement checkerboard test wire overlap**

- **Found during:** Task 2
- **Issue:** Test expected BG_COLOR at pixel (1,0) in measurement gate area, but wire line at y=CELL_H//2=1 makes this pixel WIRE_COLOR
- **Fix:** Updated test to verify (1,0) is not measurement color rather than asserting exact BG_COLOR
- **Files modified:** tests/test_draw_render.py

**2. [Rule 3 - Blocking] Pillow not installed**

- **Found during:** Task 1 verification
- **Issue:** `from PIL import Image` failed -- Pillow not in environment
- **Fix:** Installed Pillow via pip (already declared in setup.py)

## Next Phase Readiness

Plan 46-02 (multi-qubit gates) can proceed. The renderer provides:
- `CTRL_COLOR` constant already defined for control lines
- Gate rendering loop has placeholder comments for control lines and dots
- `cell_size` parameter allows flexibility for future scaling
