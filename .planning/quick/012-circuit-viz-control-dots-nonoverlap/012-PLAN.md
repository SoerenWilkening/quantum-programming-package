---
phase: quick-012
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/quantum_language/draw.py
  - tests/test_draw_render.py
autonomous: true

must_haves:
  truths:
    - "Control dots are visually distinct from control connection lines"
    - "Non-overlapping mode spreads conflicting gates in the same layer into separate visual columns"
    - "Both render() and render_detail() support the new features"
    - "Default behavior is backward-compatible (existing tests still pass)"
  artifacts:
    - path: "src/quantum_language/draw.py"
      provides: "CTRL_DOT_COLOR constant, expand_overlapping_layers() helper, updated render/render_detail/draw_circuit"
    - path: "tests/test_draw_render.py"
      provides: "Tests for distinct dot color and non-overlapping mode"
  key_links:
    - from: "draw.py:render"
      to: "expand_overlapping_layers"
      via: "optional pre-processing of draw_data when overlap=False"
      pattern: "expand_overlapping_layers"
---

<objective>
Improve circuit visualization with two enhancements: (1) make control dots visually
distinct from control connection lines by using a different color, and (2) add an
optional non-overlapping rendering mode where gates whose control lines would visually
cross other gates in the same layer are spread into consecutive visual columns.

Purpose: Better readability of multi-qubit gate circuits.
Output: Updated draw.py with both features, updated tests.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/quantum_language/draw.py
@tests/test_draw_render.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Distinct control dot color + non-overlapping layer expansion</name>
  <files>src/quantum_language/draw.py</files>
  <action>
  Two changes to draw.py:

  **1. Distinct control dot color:**
  - Add a new constant `CTRL_DOT_COLOR = (255, 255, 255)` (bright white) to distinguish
    control dots from the yellow `CTRL_COLOR = (255, 255, 100)` used for connection lines.
  - In `render()` (overview mode): Change the control dot rendering loop (line ~130) to use
    `CTRL_DOT_COLOR` instead of `CTRL_COLOR`. The control dot is a single pixel at
    `canvas[cy, gx]`. Keep the vertical control line as `CTRL_COLOR`.
  - In `render_detail()` (detail mode): Change the control dot ellipse fill (line ~284) to use
    `CTRL_DOT_COLOR` instead of `CTRL_COLOR`. Keep the vertical control line as `CTRL_COLOR`.

  **2. Non-overlapping layer expansion:**
  - Add a helper function `expand_overlapping_layers(draw_data)` that returns a NEW draw_data
    dict with potentially more layers but no visual overlaps within any layer.
  - Algorithm:
    1. Group gates by their layer index.
    2. For each layer, compute the "qubit span" of each gate: the set of qubits from
       min(target, *controls) to max(target, *controls) inclusive. Single-qubit gates
       (no controls) span only their target qubit.
    3. Greedily assign gates to sub-columns within the layer: for each gate (sorted by
       min qubit), check if its span overlaps any gate already in the current sub-column.
       If yes, start a new sub-column. A gate's span overlaps another if their qubit
       ranges intersect (i.e., not (a_max < b_min or b_max < a_min)).
    4. Remap: original layer L with K sub-columns becomes visual layers L', L'+1, ..., L'+K-1.
       All subsequent layers shift by K-1.
    5. Update `num_layers` to reflect the expanded count.
    6. Return a new dict (do NOT mutate the input).
  - Add `overlap` parameter to `render(draw_data, cell_size=3, overlap=True)`:
    - `overlap=True` (default): current behavior, backward compatible.
    - `overlap=False`: call `expand_overlapping_layers(draw_data)` before rendering.
  - Add same `overlap` parameter to `render_detail(draw_data, overlap=True)`.
  - Add `overlap` parameter to `draw_circuit(circuit, *, mode=None, save=None, overlap=True)`,
    passing it through to whichever render function is called.
  </action>
  <verify>
  Run existing tests to confirm backward compatibility:
  ```
  cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly
  python -m pytest tests/test_draw_render.py -x -q
  ```
  All existing tests must pass (they use default overlap=True behavior).
  </verify>
  <done>
  - CTRL_DOT_COLOR constant exists and differs from CTRL_COLOR
  - Control dots use CTRL_DOT_COLOR in both render() and render_detail()
  - expand_overlapping_layers() function exists
  - render(), render_detail(), draw_circuit() accept overlap parameter
  - All existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Tests for new features</name>
  <files>tests/test_draw_render.py</files>
  <action>
  Add tests to tests/test_draw_render.py. Import `CTRL_DOT_COLOR` from `quantum_language.draw`.

  **Control dot color tests:**

  1. `TestControlDotColorDistinct::test_ctrl_dot_color_differs_from_ctrl_color`:
     Assert `CTRL_DOT_COLOR != CTRL_COLOR`.

  2. `TestControlDotColorDistinct::test_overview_dot_uses_dot_color`:
     Create CNOT (target=2, control=0, layer=0, 3 qubits). Render with `render()`.
     Check pixel at control qubit wire center (y=1, x=0) equals CTRL_DOT_COLOR.
     Check a pixel on the control line between control and target (e.g., y=2, x=0) equals CTRL_COLOR.

  3. `TestControlDotColorDistinct::test_detail_dot_uses_dot_color`:
     Create CNOT (target=2, control=0, layer=1, 3 qubits). Render with `render_detail()`.
     Check pixel at control dot center (LABEL_MARGIN + 1*DETAIL_CELL + DETAIL_CELL//2, 0*DETAIL_CELL + DETAIL_CELL//2) equals CTRL_DOT_COLOR.

  **Non-overlapping mode tests:**

  4. `TestNonOverlappingMode::test_no_overlap_expands_layers`:
     Create two gates in same layer that overlap: gate A (layer=0, target=0, controls=[2])
     and gate B (layer=0, target=1, controls=[]). Gate B's target=1 is within A's span [0,2].
     Render with `render(dd, overlap=False)`. The image width should be > 1*CELL_W*cell_size
     (i.e., more than 1 layer wide) because the overlap forced expansion.

  5. `TestNonOverlappingMode::test_no_overlap_no_change_when_no_conflicts`:
     Create two gates in same layer that do NOT overlap: gate A (layer=0, target=0, controls=[])
     and gate B (layer=0, target=3, controls=[]). Render with overlap=False.
     Image width should equal 1*CELL_W (same as overlap=True) since no expansion needed.

  6. `TestNonOverlappingMode::test_overlap_true_is_default`:
     Create overlapping gates (same as test 4). Render with default params.
     Image width should equal 1*CELL_W (no expansion, default is overlap=True).

  7. `TestNonOverlappingMode::test_draw_circuit_passes_overlap`:
     Create mock circuit with overlapping gates. Call `draw_circuit(circuit, overlap=False)`.
     Verify the image is wider than with overlap=True.
  </action>
  <verify>
  ```
  cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly
  python -m pytest tests/test_draw_render.py -x -q
  ```
  All tests pass including new ones.
  </verify>
  <done>
  - 7 new tests exist and pass
  - Control dot color distinction verified in both overview and detail modes
  - Non-overlapping expansion verified: expands when needed, no-op when not needed
  - Default backward compatibility verified
  </done>
</task>

</tasks>

<verification>
1. All existing tests pass (backward compatibility)
2. New tests pass for both features
3. Manual smoke test: `python -c "from quantum_language.draw import CTRL_DOT_COLOR, CTRL_COLOR; print(f'Dot={CTRL_DOT_COLOR}, Line={CTRL_COLOR}'); assert CTRL_DOT_COLOR != CTRL_COLOR"`
</verification>

<success_criteria>
- Control dots render in CTRL_DOT_COLOR (white), distinct from CTRL_COLOR (yellow) connection lines
- overlap=False mode expands conflicting same-layer gates into consecutive visual columns
- overlap=True (default) preserves all existing behavior
- All tests pass (existing + 7 new)
</success_criteria>

<output>
After completion, create `.planning/quick/012-circuit-viz-control-dots-nonoverlap/012-SUMMARY.md`
</output>
