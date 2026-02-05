# Domain Pitfalls: Pixel-Art Circuit Visualization

**Domain:** PIL/Pillow-based compact pixel-art quantum circuit renderer
**Researched:** 2026-02-03
**Confidence:** HIGH (Pillow docs verified, circuit data structures inspected, domain patterns from quantum viz literature)

## Executive Summary

Building a pixel-art circuit renderer for quantum circuits up to 200+ qubits and thousands of layers involves pitfalls in three categories: (1) PIL/Pillow performance and memory constraints that silently degrade or crash at scale, (2) circuit data extraction challenges specific to this project's C backend `circuit_s` structure, and (3) visual design mistakes that make large circuits unreadable despite being technically rendered. The most dangerous pitfalls are those that work fine during development with small test circuits (5-10 qubits) but fail catastrophically at production scale (100+ qubits, 1000+ layers).

---

## Critical Pitfalls

Mistakes that cause crashes, unusable output, or require architecture rewrites.

### Pitfall 1: Pillow Decompression Bomb Limits on Generated Images

**What goes wrong:** Pillow has a built-in `MAX_IMAGE_PIXELS` limit (default ~178 million pixels) that raises `DecompressionBombError` when exceeded. A 200-qubit, 2000-layer circuit with even 3px-per-gate spacing easily produces images of 6000x600+ pixels at detail zoom -- this is fine. But at overview zoom with labels, margins, and legends, or if the spacing math is slightly wrong, the pixel count can exceed the threshold. More critically, if someone accidentally creates an image at the wrong zoom level (e.g., detail zoom on a massive circuit), the image dimensions can balloon to 200,000+ pixels wide.

**Why it happens:** The limit is designed to prevent loading malicious images, not to constrain generation. Developers test with small circuits during development and never hit the limit. The first time a user visualizes their 150-qubit QFT circuit, it crashes.

**Consequences:**
- `PIL.Image.DecompressionBombError` or `DecompressionBombWarning` at runtime
- Users see a cryptic error unrelated to their quantum code
- If bypassed naively with `Image.MAX_IMAGE_PIXELS = None`, memory exhaustion becomes possible

**Warning signs:**
- No explicit image size calculation before `Image.new()`
- No maximum dimension capping logic
- Tests only use circuits under 20 qubits

**Prevention:**
- Calculate image dimensions BEFORE creating the `Image` object: `width = num_layers * px_per_layer + margins`, `height = num_qubits * px_per_qubit + margins`
- If dimensions exceed a configurable cap (e.g., 32000x32000), automatically switch to overview mode or tile
- Set `Image.MAX_IMAGE_PIXELS` explicitly to a known safe value rather than disabling it
- Add a pre-check: `if width * height > MAX_SAFE_PIXELS: raise ValueError("Circuit too large for detail mode, use overview")`

**Phase:** Address in the very first rendering phase (core renderer). Dimension calculation must be the first thing the renderer does.

**Confidence:** HIGH -- verified from [Pillow limits documentation](https://pillow.readthedocs.io/en/stable/reference/limits.html) and [GitHub issue #5218](https://github.com/python-pillow/Pillow/issues/5218).

---

### Pitfall 2: ImageDraw Per-Call Overhead at Scale

**What goes wrong:** Each `ImageDraw.rectangle()`, `ImageDraw.line()`, or `ImageDraw.point()` call incurs Python-to-C boundary crossing overhead. For a 100-qubit, 1000-layer circuit, you need approximately: 100 horizontal wire lines + 100,000 gate icons (rectangles/points) + 50,000 control lines = 150,000+ individual draw calls. At ~10-50 microseconds per call, this takes 1.5-7.5 seconds just for drawing -- unacceptable for an API that should feel instant for small-to-medium circuits.

**Why it happens:** The natural approach is a nested loop: `for layer in layers: for qubit in qubits: draw.rectangle(...)`. This is clean code but slow code. Developers benchmark with 5-qubit circuits where 50 draw calls take <1ms, and never notice the O(qubits * layers) scaling problem.

**Consequences:**
- `ql.draw_circuit()` takes 5-30 seconds for large circuits
- Users perceive the framework as slow
- Temptation to "optimize later" but the architecture locks in per-call patterns

**Warning signs:**
- Individual `draw.rectangle()` calls inside nested loops
- No batching strategy in the design
- No performance test with circuits >50 qubits

**Prevention:**
- Use NumPy array operations for bulk pixel manipulation: create a NumPy array, use slice assignment (`arr[y1:y2, x1:x2] = color`) for filled rectangles, then convert to PIL Image with `Image.fromarray(arr)`
- For horizontal wire lines: `arr[y, x1:x2] = wire_color` (single array slice per qubit)
- For gate icons at 2-3px: pre-define gate patterns as small NumPy arrays and stamp them with slice assignment
- Reserve `ImageDraw` only for operations that genuinely need it (e.g., anti-aliased text for labels, if any)
- Benchmark target: <100ms for a 100-qubit, 1000-layer circuit

**Phase:** Must be decided in architecture phase. Switching from ImageDraw to NumPy after the renderer is built requires rewriting all drawing code.

**Confidence:** HIGH -- per-call overhead is a well-documented Pillow performance issue, confirmed by [Pillow issue #2450](https://github.com/python-pillow/Pillow/issues/2450) and the [Pillow performance page](https://python-pillow.github.io/pillow-perf/).

---

### Pitfall 3: No Python API to Iterate Circuit Gates from C Backend

**What goes wrong:** The existing `circuit` class in `_core.pyx` exposes aggregate statistics (`gate_count`, `depth`, `gate_counts`) and text output (`visualize()`, OpenQASM export), but does NOT expose a Python-accessible API to iterate over individual gates at specific layers and positions. The `circuit_s.sequence[layer][gate_index]` data is only accessible from C/Cython code. Building a pure-Python renderer requires either: (a) adding a new Cython function to extract gate data into Python objects, or (b) building the renderer in Cython.

**Why it happens:** The existing text-based `circuit_visualize()` and `circuit_to_qasm_string()` functions are implemented entirely in C, so they never needed to expose per-gate data to Python. A Python-based PIL renderer is the first consumer that needs gate-by-gate access from Python.

**Consequences:**
- If not addressed upfront, the renderer cannot access the data it needs to render
- Bolt-on solutions (parsing the text output of `visualize()`, parsing OpenQASM) are fragile and slow
- Scope creep: what was "just a renderer" becomes "renderer + Cython bindings refactor"

**Warning signs:**
- Renderer design assumes gate data is available as Python lists/dicts
- No Cython binding task in the plan
- Design doc references `circuit.gates` or similar API that doesn't exist

**Prevention:**
- First task must be creating a Cython function like `get_circuit_data()` that returns a Python-friendly structure:
  ```python
  # Returns list of layers, each layer is list of gate dicts
  [
    [{"type": "H", "target": 0, "controls": [], "value": 0.0}, ...],  # layer 0
    [{"type": "CX", "target": 3, "controls": [1], "value": 0.0}, ...],  # layer 1
    ...
  ]
  ```
- This function walks `circuit_s.sequence` and `circuit_s.used_gates_per_layer` in Cython, converting `gate_t` structs to Python dicts
- The `Standardgate_t` enum (`X, Y, Z, R, H, Rx, Ry, Rz, P, M`) maps to string names
- Must handle `large_control` (when `NumControls > 2`) by reading the dynamically allocated control array
- Keep the Cython binding minimal and stable; all rendering logic stays in pure Python

**Phase:** This is a prerequisite -- must be the very first implementation task before any rendering code.

**Confidence:** HIGH -- verified by reading `_core.pxd` (line 62-93), `_core.pyx` (line 302-344), `types.h` (line 64-82), and `circuit.h` (line 54-79). No per-gate Python API exists.

---

### Pitfall 4: Zoom Level Produces Unreadable Output at Wrong Scale

**What goes wrong:** Two zoom levels (overview and detail) sounds simple, but choosing the wrong one for a given circuit size makes the output useless. Detail mode on a 200-qubit circuit produces an image so wide/tall it's impractical. Overview mode on a 5-qubit circuit wastes the visual space and makes gates indistinguishable. Worse, if there's no automatic selection, users must manually pick -- and most won't know which to use.

**Why it happens:** Developers implement both modes and test each with appropriate circuits. They never test detail mode on huge circuits or overview mode on tiny ones, because they know which to use. Users don't.

**Consequences:**
- Users get a 50,000px wide image they can't view
- Users get a 100x50px overview where everything is a dot
- Complaints about "broken" visualization that's technically correct but practically useless

**Warning signs:**
- No automatic mode selection logic
- No maximum image dimension constraints
- Tests don't verify mode switching behavior at boundary sizes

**Prevention:**
- Implement automatic mode selection based on circuit dimensions:
  - Detail mode: `num_qubits <= 30 AND num_layers <= 200` (approximately)
  - Overview mode: everything else
  - Allow user override: `ql.draw_circuit(mode="overview")` / `ql.draw_circuit(mode="detail")`
- Cap maximum image dimensions (e.g., 8192px in any direction for default output)
- If the circuit exceeds even overview capacity, provide a clear error message with the circuit dimensions
- Return image dimensions in the API response so users can make informed decisions

**Phase:** Design phase -- the mode selection thresholds affect all rendering code.

---

## Moderate Pitfalls

Mistakes that cause visual bugs, performance issues, or technical debt.

### Pitfall 5: Resampling Filter Destroys Pixel Art on Zoom

**What goes wrong:** When scaling the rendered image (for overview mode or for display), using PIL's default `Resampling.BICUBIC` or `Resampling.LANCZOS` filter blurs the pixel-art gate icons into unrecognizable smudges. A carefully crafted 3px "H" gate icon becomes a blurry gray blob after downscaling with interpolation.

**Why it happens:** PIL's `Image.resize()` defaults to `Resampling.BICUBIC`. The developer calls `.resize()` without specifying the filter, or uses `LANCZOS` because it's "higher quality." For photographs, that's correct. For pixel art, it destroys the visual information.

**Consequences:**
- Gate icons become indistinguishable colored blobs
- Control dots blur into wire lines
- The "pixel art" aesthetic is lost entirely
- Particularly bad at non-integer scale factors

**Warning signs:**
- Any `.resize()` call without explicit `resample=Image.Resampling.NEAREST`
- Any `.thumbnail()` call (defaults to BICUBIC)
- Scale factors that aren't integers

**Prevention:**
- ALWAYS use `Image.Resampling.NEAREST` for any scaling operation
- Use only integer scale factors (2x, 3x, 4x) for upscaling -- never fractional
- For downscaling in overview mode, render at the target resolution directly rather than rendering large and shrinking
- Add a utility function that wraps resize with the correct filter to prevent mistakes:
  ```python
  def pixel_scale(img, factor):
      return img.resize((img.width * factor, img.height * factor),
                        resample=Image.Resampling.NEAREST)
  ```

**Phase:** Implement in the core renderer alongside any zoom/scale logic.

**Confidence:** HIGH -- verified from [Pillow resampling documentation](https://pillow.readthedocs.io/en/stable/handbook/concepts.html) and [Pillow issue #6200](https://github.com/python-pillow/Pillow/issues/6200). Default is BICUBIC since Pillow 2.7.0.

---

### Pitfall 6: PNG Save Latency for Large Circuit Images

**What goes wrong:** Pillow's PNG encoder uses zlib compression with a default compress level that prioritizes file size over speed. For a large circuit image (e.g., 8000x2000 RGB), saving to PNG can take 2-10 seconds. This is surprising when the rendering itself took <100ms.

**Why it happens:** PNG compression is the bottleneck, not rendering. Pillow's default PNG compression is more aggressive than OpenCV's (benchmarks show PIL is 4x slower than cv2.imwrite for PNG). Developers measure rendering time but not save time.

**Consequences:**
- `ql.draw_circuit()` followed by `.save("circuit.png")` takes 5+ seconds
- Users blame the renderer when the bottleneck is file I/O
- In Jupyter notebooks, displaying the PIL Image is fast (no PNG encode), but saving is slow

**Warning signs:**
- No `compress_level` parameter passed to `Image.save()`
- Performance benchmarks that measure rendering but not saving
- No guidance in docs about save performance

**Prevention:**
- Return the PIL Image object from `ql.draw_circuit()` (don't auto-save)
- When saving, use `compress_level=1` for speed: `img.save("circuit.png", compress_level=1)`
- Document that Jupyter display is instant but PNG save may be slow for large circuits
- For the `Image.save()` convenience wrapper, default to `compress_level=1` with an option for `compress_level=6` (smaller file)
- Consider offering BMP output for maximum speed (no compression) during development/iteration

**Phase:** Address when implementing the save/export functionality.

**Confidence:** HIGH -- verified from [Pillow issue #5986](https://github.com/python-pillow/Pillow/issues/5986) and [Pillow issue #1211](https://github.com/python-pillow/Pillow/issues/1211).

---

### Pitfall 7: Multi-Qubit Gate Control Lines Overlap and Obscure Each Other

**What goes wrong:** Controlled gates (CX, CCX, MCX) require vertical lines connecting control qubits to target qubits. When multiple controlled gates in the same layer have overlapping qubit ranges (e.g., CX from qubit 3 to 7, and CX from qubit 5 to 10), their control lines cross and become indistinguishable. At 2-3px icon size, there's no room for visual disambiguation.

**Why it happens:** In the `circuit_s` structure, a single layer can contain multiple gates that operate on overlapping qubit ranges (the optimizer packs gates into layers). The text-based `circuit_visualize()` handles this with multiple columns per layer, but a pixel renderer with fixed column width can't show overlapping lines clearly.

**Consequences:**
- Users can't tell which control connects to which target
- Multi-controlled gates (MCX with 5+ controls) become a vertical line indistinguishable from a wire
- The visualization is technically correct but practically misleading

**Warning signs:**
- No logic to detect overlapping gate ranges within a layer
- Single pixel column per layer with no sub-column support
- Tests only use circuits with non-overlapping gates per layer

**Prevention:**
- Detect overlapping gates within a layer (gate A's qubit range overlaps gate B's qubit range)
- When overlap detected, use sub-columns within the layer (widen that layer's column)
- Use distinct colors per gate type so overlapping lines are at least color-coded
- For overview mode, accept that individual control lines are unreadable and render gates as colored dots only (no control lines)
- For MCX gates with large_control (>2 controls), render as a colored vertical bar spanning the control range

**Phase:** Address during multi-qubit gate rendering (not in initial single-qubit rendering).

**Confidence:** HIGH -- verified from `types.h` lines 66-75 showing `gate_t` has `Control[MAXCONTROLS]`, `large_control`, and `NumControls` fields. The C `circuit_visualize()` code (circuit_output.c lines 104-120) already handles this complexity for text output.

---

### Pitfall 8: Gate Type Enum Mapping Incomplete or Incorrect

**What goes wrong:** The C backend defines gate types as `enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M }` (10 types in `Standardgate_t`). The renderer must map each to a distinct visual representation. If the mapping is incomplete (e.g., missing `Ry` or `M`), those gates render as blank space or crash. If gates are added to the C backend later, the renderer silently breaks.

**Why it happens:** The renderer developer maps the "common" gates (X, H, CX, P) and forgets the less common ones (Y, Ry, Rz, M). Or the enum values shift if a gate type is added to the C enum.

**Consequences:**
- Gates render as invisible (blank) or as the wrong icon
- KeyError/IndexError at runtime for unmapped gate types
- Silent incorrect visualization that looks plausible

**Warning signs:**
- Gate type mapping uses string matching instead of enum values
- No exhaustive test that renders every gate type
- No fallback rendering for unknown gate types

**Prevention:**
- Map ALL 10 gate types explicitly: X, Y, Z, R, H, Rx, Ry, Rz, P, M
- Add a fallback renderer for unknown types (render as "?" or generic colored square)
- Write a test that creates a circuit with every gate type and verifies the image is non-empty at each gate position
- Use the existing `gate_counts` property to verify: total rendered gates == sum of all gate type counts
- Consider controlled variants: CX (1 control + X), CCX (2 controls + X), MCX (n controls + X), CP (1 control + P), etc. These aren't separate enum values -- they're X/P/etc. with NumControls > 0

**Phase:** Core renderer -- gate icon definitions should be one of the first things implemented.

**Confidence:** HIGH -- verified from `types.h` line 64: `typedef enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M } Standardgate_t;`

---

### Pitfall 9: Memory Explosion from Intermediate Python Objects

**What goes wrong:** Converting the entire C circuit into Python dicts/lists before rendering can consume excessive memory. A 200-qubit, 5000-layer circuit with 10 gates per layer = 50,000 gate dicts. Each dict has ~5 keys with string/list values. In CPython, a dict with 5 keys uses ~300-400 bytes. Total: ~15-20MB just for the intermediate representation. This is manageable, but if the conversion creates unnecessary copies or nested structures, it can balloon.

**Why it happens:** The natural Cython binding approach (`get_circuit_data()` returning nested lists of dicts) creates all objects at once. For very large circuits, this is wasteful because the renderer processes gates layer-by-layer and doesn't need all data simultaneously.

**Consequences:**
- Unnecessary memory spike during rendering
- GC pressure from millions of small Python objects
- For extremely large circuits (10,000+ layers), may cause memory issues

**Warning signs:**
- `get_circuit_data()` returns the entire circuit as a single Python object
- No streaming/iterator-based access pattern
- Memory profiling shows spike during data extraction

**Prevention:**
- For v1 (simplicity): accept the full-extraction approach, it works for circuits up to ~10,000 layers
- Provide a `get_layer_data(layer_index)` function that extracts one layer at a time for future optimization
- Use tuples instead of dicts for gate data (less memory overhead): `(gate_type, target, controls_tuple, value)`
- Avoid string allocation for gate types -- use integer enum values and map to strings only at render time
- Pre-calculate image dimensions from `circuit.depth` and `circuit.qubit_count` (already available) before extracting gate data

**Phase:** Cython binding phase -- design the data extraction API with future streaming in mind even if v1 is bulk extraction.

---

### Pitfall 10: Qubit Index Gaps Waste Vertical Space

**What goes wrong:** The `circuit_s` structure uses qubit indices that may have gaps (not all indices from 0 to `used_qubits` are actually used). If the renderer naively allocates one pixel row per qubit index from 0 to max, unused qubits waste vertical space. For a circuit using qubits [0, 1, 2, 64, 65, 66] (common with the 64-bit right-aligned layout), the image would be 67 rows tall with 61 empty rows.

**Why it happens:** The `quantum_int_t` structure uses right-aligned layout in a 64-element array: `q_address[64-width]` through `q_address[63]`. Qubit allocation via `allocator_alloc()` is sequential but integer widths vary. After allocation and deallocation of ancilla qubits, the active qubit indices may be sparse.

**Consequences:**
- Images are much taller than necessary
- Most of the image is empty wire lines for unused qubits
- Overview mode wastes resolution on empty rows

**Warning signs:**
- Renderer uses `circuit.qubit_count` as image height without checking occupancy
- No qubit compaction/remapping logic
- Tests use contiguous qubit indices (which hides the problem)

**Prevention:**
- Extract the set of actually-used qubit indices from the circuit data
- The C structure has `used_occupation_indices_per_qubit[qubit]` -- qubits with 0 occupation indices are unused
- Create a qubit index remapping: map sparse indices to dense row indices
- Show the original qubit index as a label but render only occupied rows
- Alternatively, use `circuit_s.used_qubits` as a hint but still check per-qubit occupancy

**Phase:** Core renderer layout phase -- qubit compaction affects all coordinate calculations.

**Confidence:** HIGH -- verified from `circuit.h` lines 64-66 (`occupied_layers_of_qubit`, `used_occupation_indices_per_qubit`) and the right-aligned layout documented in `quantum_int_t`.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without architecture changes.

### Pitfall 11: Color Palette Indistinguishable for Color-Blind Users

**What goes wrong:** Using red/green color pairs (common in "stoplight" palettes) makes gates indistinguishable for the ~8% of males with red-green color blindness. If the only way to distinguish H gates from X gates is color, those users can't read the circuit.

**Prevention:**
- Use shape AND color as redundant encodings (X = square + red, H = diamond + blue)
- Choose a colorblind-safe palette (blue/orange, blue/yellow)
- At 2-3px, shapes are more important than colors anyway
- Test with a colorblindness simulator

**Phase:** Gate icon design phase.

---

### Pitfall 12: No Legend Makes Gates Unidentifiable

**What goes wrong:** A pixel-art circuit with 2-3px gate icons is inherently cryptic. Without a color/shape legend, users can't identify gate types at all. The visualization becomes a pretty but useless abstract image.

**Prevention:**
- Always include a legend region (right side or bottom) mapping gate icons to names
- Legend should use the same pixel-art style as the circuit
- For programmatic use, also provide a `gate_legend()` method that returns the mapping as a dict

**Phase:** Legend should be designed with the core renderer, implemented as a separate compositing step.

---

### Pitfall 13: Wire Lines Vanish at Overview Zoom

**What goes wrong:** In overview mode where each qubit row is 1px tall, the horizontal wire line IS the row. If gate icons are also 1px, the wire line, gate icon, and background all compete for the same pixel. The wire becomes invisible.

**Prevention:**
- In overview mode, skip wire rendering entirely -- just render gate positions as colored pixels on a dark background
- The wire is implied by the row; don't try to draw it separately
- Use a dark background (black or dark gray) with bright gate colors for maximum contrast at 1px scale

**Phase:** Overview mode implementation.

---

### Pitfall 14: Phase/Rotation Gate Values Lost in Pixel Art

**What goes wrong:** Phase gates (P) and rotation gates (Rx, Ry, Rz) have a continuous `GateValue` parameter (angle). In text/QASM output, this is rendered as a number. In 2-3px pixel art, there's no room for text. Users see a "P" gate but can't tell if it's P(pi/4) or P(pi/2).

**Prevention:**
- Accept this limitation in the pixel-art renderer -- it's a visual overview, not a detailed schematic
- Use color intensity or hue variation to encode angle magnitude (e.g., brighter = larger angle)
- For the few common angles (pi, pi/2, pi/4), use distinct icon variants
- Document that for angle details, users should use `circuit.visualize()` (text) or OpenQASM export
- In detail mode, consider adding tiny 1px text labels for common angles if font rendering works at that scale (it probably won't -- test first)

**Phase:** Gate icon refinement, after basic rendering works.

---

### Pitfall 15: Pillow Not Installed as Required Dependency

**What goes wrong:** Pillow is an optional dependency for this project (the core quantum framework doesn't need it). If `ql.draw_circuit()` is called without Pillow installed, the user gets `ModuleNotFoundError: No module named 'PIL'` -- an unhelpful error from inside the rendering code.

**Prevention:**
- Use a lazy import: `try: from PIL import Image; except ImportError: raise ImportError("Pillow is required for circuit visualization. Install with: pip install Pillow")`
- List Pillow as an optional dependency in setup.py: `extras_require={"viz": ["Pillow>=9.0"]}`
- Don't import Pillow at module level in `__init__.py` -- only when `draw_circuit()` is called
- Test the error message by running without Pillow installed

**Phase:** API integration phase (when `ql.draw_circuit()` is wired up).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Cython data extraction binding | Pitfall 3: No gate iteration API exists | Build `get_circuit_data()` first, before any rendering code |
| Core renderer architecture | Pitfall 2: ImageDraw per-call overhead | Design for NumPy array operations from the start |
| Image sizing / layout | Pitfall 1: Decompression bomb limits | Calculate dimensions first, cap maximums, auto-select mode |
| Gate icon design | Pitfall 8: Incomplete gate type mapping | Map all 10 Standardgate_t values explicitly |
| Multi-qubit gates | Pitfall 7: Overlapping control lines | Detect overlaps, use sub-columns or color coding |
| Qubit layout | Pitfall 10: Sparse qubit index gaps | Compact/remap qubit indices before rendering |
| Zoom / overview mode | Pitfall 4: Wrong zoom auto-selection | Threshold-based auto mode with user override |
| Zoom / scaling | Pitfall 5: Wrong resampling filter | Always use NEAREST, integer scale factors only |
| PNG export | Pitfall 6: Slow PNG save | Default to compress_level=1, return Image object |
| API integration | Pitfall 15: Pillow not installed | Lazy import with helpful error message |

---

## Sources

- [Pillow Limits Documentation](https://pillow.readthedocs.io/en/stable/reference/limits.html) -- MAX_IMAGE_PIXELS, memory limits
- [Pillow DecompressionBombError Issue #5218](https://github.com/python-pillow/Pillow/issues/5218) -- pixel count limits
- [Pillow ImageDraw Performance Issue #2450](https://github.com/python-pillow/Pillow/issues/2450) -- per-call overhead
- [Pillow PNG Save Performance Issue #5986](https://github.com/python-pillow/Pillow/issues/5986) -- 4x slower than OpenCV
- [Pillow PNG Save Slow Issue #1211](https://github.com/python-pillow/Pillow/issues/1211) -- compress_level settings
- [Pillow Resampling Concepts](https://pillow.readthedocs.io/en/stable/handbook/concepts.html) -- NEAREST vs BICUBIC
- [Pillow ANTIALIAS Deprecation Issue #6200](https://github.com/python-pillow/Pillow/issues/6200) -- filter selection
- [Quantivine: Large-Scale Quantum Circuit Visualization (arXiv:2307.08969)](https://arxiv.org/abs/2307.08969) -- semantic abstraction for 100+ qubit circuits
- [IBM Quantum Circuit Visualization Guide](https://quantum.cloud.ibm.com/docs/en/guides/visualize-circuits) -- practical rendering challenges
- Project source: `types.h` lines 64-82 (gate_t, Standardgate_t enum)
- Project source: `circuit.h` lines 54-79 (circuit_s structure, layer/gate storage)
- Project source: `_core.pxd` lines 62-148 (Cython declarations, no per-gate Python API)
- Project source: `circuit_output.c` lines 35-120 (existing text visualization approach)
