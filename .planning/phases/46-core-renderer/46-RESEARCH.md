# Phase 46: Core Renderer - Research

**Researched:** 2026-02-03
**Domain:** NumPy array-based pixel-art rendering of quantum circuits as PNG images
**Confidence:** HIGH

## Summary

This phase implements a pure Python renderer that takes the structured `draw_data()` dict (from Phase 45) and produces a pixel-art PNG image of the quantum circuit. The renderer must use NumPy array bulk operations (not per-pixel ImageDraw calls) per REND-05, produce distinct gate icons as 2x2 colored blocks on a dark background, draw horizontal wire lines, and render vertical control connection lines for multi-qubit gates.

The core technique is: allocate a NumPy `uint8` array of shape `(height, width, 3)`, use array slice assignment to draw all visual elements (wires, gates, control lines), then convert to PIL Image via `Image.fromarray()` and save as PNG. This approach is dramatically faster than per-pixel ImageDraw calls because NumPy slice assignment executes in optimized C code rather than Python-level loops.

At the overview scale specified in the context (2x2 gate blocks, no layer gaps), a 10,000-gate circuit on 200 qubits produces approximately a 20,000 x 600 pixel image (~36 MB in memory as RGB uint8), which is well within reasonable limits.

**Primary recommendation:** Create a single `draw.py` module in `src/quantum_language/` that accepts the `draw_data()` dict, builds a NumPy array canvas, renders all elements via slice assignment, converts to PIL Image, and returns it. Add Pillow to setup.py dependencies. No Cython needed for the renderer.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NumPy | (already in project) | Canvas array allocation + bulk pixel operations | Required by REND-05; already imported in `_core.pyx` and `__init__.py` |
| Pillow (PIL) | >=9.0 | `Image.fromarray()` for NumPy-to-Image conversion, `.save()` for PNG export | De facto Python imaging standard; needed only for final conversion + save |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (already in project) | Testing renderer output | Verify image dimensions, pixel colors at known coordinates |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NumPy array + Image.fromarray() | ImageDraw line/rectangle calls | ImageDraw is slower for bulk pixel ops (per-call overhead); violates REND-05 |
| Pillow PNG save | Raw PNG via zlib | Pillow handles PNG encoding correctly; hand-rolling PNG is error-prone and unnecessary |
| RGB mode (3 channels) | RGBA mode (4 channels) | RGB is sufficient for dark-background pixel art with no transparency needs; saves 25% memory |

**Installation:**
Add to `setup.py`:
```python
install_requires=["Pillow>=9.0"],
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
    draw.py              # NEW: Pure Python renderer (NumPy + PIL)
    __init__.py          # Add draw_circuit() export
    _core.pyx            # Already has draw_data() method (Phase 45)
```

One file. No sprites module needed -- gate icons are 2x2 colored blocks defined as inline constants.

### Pattern 1: NumPy Canvas with Slice Assignment
**What:** Allocate a `(height, width, 3)` uint8 NumPy array as the canvas. Draw elements by assigning color values to array slices. Convert to PIL Image at the end.
**When to use:** All rendering in this phase.
**Example:**
```python
import numpy as np
from PIL import Image

# Allocate canvas
canvas = np.zeros((height, width, 3), dtype=np.uint8)
# Set background color (dark)
canvas[:, :] = [20, 20, 30]

# Draw horizontal wire line for qubit q (1px high)
y = q * cell_h + cell_h // 2
canvas[y, x_start:x_end] = [60, 60, 80]  # Wire color

# Draw 2x2 gate block at (gx, gy)
canvas[gy:gy+2, gx:gx+2] = [180, 130, 200]  # Gate color

# Draw vertical control line (1px wide)
canvas[y_top:y_bot, cx] = [255, 255, 100]  # Control line color

# Draw control dot (1px)
canvas[cy, cx] = [255, 255, 100]

# Convert to PIL Image
img = Image.fromarray(canvas, 'RGB')
img.save('circuit.png')
```

### Pattern 2: Gate Color Lookup Table
**What:** A dict mapping gate type int (from Standardgate_t enum) to RGB tuple. Gate categories share colors per the context decisions.
**When to use:** When rendering any gate.
**Example:**
```python
# Standardgate_t: X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9

GATE_COLORS = {
    0: (180, 130, 200),   # X  - Pauli (muted purple)
    1: (180, 130, 200),   # Y  - Pauli (muted purple)
    2: (180, 130, 200),   # Z  - Pauli (muted purple)
    3: (130, 180, 200),   # R  - Rotation (muted cyan)
    4: (200, 180, 100),   # H  - Hadamard (distinct warm yellow)
    5: (130, 180, 200),   # Rx - Rotation (muted cyan)
    6: (130, 180, 200),   # Ry - Rotation (muted cyan)
    7: (130, 180, 200),   # Rz - Rotation (muted cyan)
    8: (100, 200, 150),   # P  - Phase (muted green)
    9: (200, 100, 100),   # M  - Measurement (muted red, visually distinct)
}
```

### Pattern 3: Layout Calculation from draw_data
**What:** Compute image dimensions and coordinate mapping from the draw_data dict.
**When to use:** Before rendering.
**Example:**
```python
CELL_W = 3   # Pixels per layer column (2px gate + 1px wire gap = 3, or just 2 for max density)
CELL_H = 3   # Pixels per qubit row (2px gate + 1px wire gap)
WIRE_COLOR = (60, 60, 80)
BG_COLOR = (20, 20, 30)

def compute_layout(draw_data):
    num_layers = draw_data['num_layers']
    num_qubits = draw_data['num_qubits']
    width = num_layers * CELL_W
    height = num_qubits * CELL_H
    return width, height
```

### Pattern 4: Vectorized Gate Rendering via Loop
**What:** Iterate gates once, use NumPy slice assignment for each. Even though there is a Python loop over gates, each gate's rendering is a single NumPy slice operation (no per-pixel Python loop).
**When to use:** For all gate rendering.
**Example:**
```python
for gate in draw_data['gates']:
    gx = gate['layer'] * CELL_W
    gy = gate['target'] * CELL_H
    color = GATE_COLORS[gate['type']]
    # Single slice assignment -- bulk operation, not per-pixel
    canvas[gy:gy+2, gx:gx+2] = color
```

### Pattern 5: Control Line Rendering
**What:** For each gate with controls, draw a vertical line from min qubit to max qubit, then overlay control dots and the gate block.
**When to use:** Multi-qubit gates (CNOT, CCX, MCX).
**Example:**
```python
CTRL_COLOR = (255, 255, 100)  # Bright yellow for control lines

for gate in draw_data['gates']:
    if not gate['controls']:
        continue
    gx = gate['layer'] * CELL_W
    cx = gx  # Control line in same column as gate
    all_qubits = [gate['target']] + gate['controls']
    y_min = min(all_qubits) * CELL_H + CELL_H // 2
    y_max = max(all_qubits) * CELL_H + CELL_H // 2
    # Vertical control line (1px wide, full span)
    canvas[y_min:y_max+1, cx] = CTRL_COLOR
    # Control dots (single bright pixel at each control qubit)
    for ctrl in gate['controls']:
        cy = ctrl * CELL_H + CELL_H // 2
        canvas[cy, cx] = CTRL_COLOR
```

### Anti-Patterns to Avoid
- **Using ImageDraw for per-pixel or per-line drawing:** Violates REND-05. Each ImageDraw call has Python-level overhead. Use NumPy slice assignment instead.
- **Allocating RGBA when RGB suffices:** Dark background + opaque pixel art needs no alpha channel. RGB saves 25% memory (important at 20K x 600 scale).
- **Per-gate Python loops with per-pixel inner loops:** The Python loop over gates is acceptable (10K iterations is fast). But within each gate, use a single slice assignment, not a nested pixel loop.
- **Dynamic resizing of the canvas array:** Pre-calculate dimensions from draw_data, allocate once. `np.resize` or concatenation during rendering wastes memory and time.
- **Storing gate sprites as separate image files:** At 2x2 pixels, gates are just colored rectangles. Inline RGB tuples in a dict are simpler, faster, and have no file I/O.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PNG encoding | Manual zlib/DEFLATE | `Image.fromarray(arr).save('file.png')` | PNG format is complex (chunks, CRC, IDAT); Pillow handles it correctly |
| Image resizing (for display) | Manual pixel duplication | `img.resize((w, h), Image.NEAREST)` | Pillow's NEAREST resampling preserves pixel-art sharpness |
| Color space conversion | Manual math | PIL mode parameter in `Image.fromarray()` | Pillow handles RGB/L/RGBA correctly from NumPy dtype and shape |
| Gate type -> name mapping | Ad-hoc string building | Constant dict `{0: 'X', 1: 'Y', ...}` (already in test_draw_data.py) | Standardgate_t enum is stable; a constant dict is sufficient |

**Key insight:** At 2x2 pixel gate blocks, there are no "sprites" to manage. Each gate is a colored rectangle rendered by a single NumPy slice assignment. The complexity lives in layout calculation and control line routing, not in pixel-level rendering.

## Common Pitfalls

### Pitfall 1: Wrong Array Axis Order (height, width) vs (width, height)
**What goes wrong:** NumPy arrays for images use `(rows, columns)` = `(height, width)`, not `(width, height)`. Confusing these produces a transposed image.
**Why it happens:** Intuition from coordinate systems where x comes first. But image arrays follow matrix convention: rows (y) first, columns (x) second.
**How to avoid:** Always use `canvas = np.zeros((height, width, 3), dtype=np.uint8)`. When indexing: `canvas[y, x]` not `canvas[x, y]`.
**Warning signs:** Image looks rotated 90 degrees; gates appear on wrong qubits.

### Pitfall 2: Integer Overflow in Canvas Dimensions
**What goes wrong:** For very large circuits (10K layers x 200 qubits), `num_layers * CELL_W` could exceed reasonable image dimensions if CELL_W is too large (e.g., 32px cells = 320,000px wide).
**Why it happens:** The architecture research doc suggested 32px cells, but the phase context specifies 2-3px per gate at overview scale.
**How to avoid:** Use CELL_W = 2 or 3 (per context decisions). At CELL_W=2: 10,000 layers = 20,000px wide. At CELL_W=3: 30,000px wide. Both are manageable. PIL supports images up to ~65,535 px in either dimension for PNG.
**Warning signs:** MemoryError or extremely slow rendering.

### Pitfall 3: Measurement Gate Not Visually Distinct
**What goes wrong:** If measurement (M) gate uses the same 2x2 solid block as unitary gates, it blends in despite having a different color.
**Why it happens:** Color alone may not be enough distinction at 2x2 scale, especially for colorblind users.
**How to avoid:** Use a distinct pixel pattern for M gates. For example, render M as a 2x2 checkerboard pattern instead of solid: `canvas[gy, gx] = M_COLOR; canvas[gy+1, gx+1] = M_COLOR; canvas[gy, gx+1] = BG_COLOR; canvas[gy+1, gx] = BG_COLOR`. This creates a visual texture difference even at small scale.
**Warning signs:** Users cannot distinguish measurement from other gates.

### Pitfall 4: Control Lines Obscured by Gate Blocks
**What goes wrong:** If gate blocks are rendered after control lines, the gate block overwrites part of the control line at the target qubit. This is actually desired. But if control lines are rendered after gate blocks, they cut through gate blocks at intermediate qubits.
**Why it happens:** Rendering order matters when elements overlap in the same column.
**How to avoid:** Render in this order: (1) background, (2) wires, (3) control lines, (4) gate blocks, (5) control dots. This ensures gate blocks sit on top of wires and control lines, while control dots remain visible.
**Warning signs:** Control lines appear to go through gate blocks of unrelated gates on intermediate qubits.

### Pitfall 5: Empty Circuit Produces Zero-Size Image
**What goes wrong:** `np.zeros((0, 0, 3))` is valid but `Image.fromarray()` on it may behave unexpectedly. Saving a 0x0 image as PNG is undefined.
**Why it happens:** Circuit with no gates has `num_layers=0` and possibly `num_qubits=0`.
**How to avoid:** Return a minimal 1x1 pixel image (or raise a clear error) for empty circuits. Check dimensions before allocating.
**Warning signs:** Exception during `Image.fromarray()` or `.save()` for empty circuit.

### Pitfall 6: NumPy Temporary Array Allocation During Operations
**What goes wrong:** Certain NumPy operations (like boolean indexing or `np.where`) can allocate temporary arrays in int64, consuming 8x more memory than the uint8 canvas.
**Why it happens:** NumPy upcasts to int64 for intermediate computations by default.
**How to avoid:** Use only direct slice assignment (`canvas[y1:y2, x1:x2] = color`), which modifies in-place without temporaries. Avoid `np.where` or boolean masking on the full canvas.
**Warning signs:** Memory usage spikes far beyond the expected ~36 MB for a large circuit image.

## Code Examples

### Example 1: Complete Minimal Renderer Structure
```python
# Source: Synthesized from project architecture + NumPy/PIL docs
import numpy as np
from PIL import Image

# Gate type enum (from types.h: X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9)
GATE_COLORS = {
    0: (180, 130, 200),  # X - Pauli
    1: (180, 130, 200),  # Y - Pauli
    2: (180, 130, 200),  # Z - Pauli
    3: (130, 180, 200),  # R - Rotation
    4: (200, 180, 100),  # H - Hadamard (distinct)
    5: (130, 180, 200),  # Rx - Rotation
    6: (130, 180, 200),  # Ry - Rotation
    7: (130, 180, 200),  # Rz - Rotation
    8: (100, 200, 150),  # P - Phase
    9: (200, 100, 100),  # M - Measurement (distinct)
}

BG_COLOR = (20, 20, 30)
WIRE_COLOR = (60, 60, 80)
CTRL_COLOR = (255, 255, 100)

CELL_W = 3  # pixels per layer (2px gate + 1px gap)
CELL_H = 3  # pixels per qubit (2px gate + 1px gap)

def render(draw_data):
    """Render circuit draw_data dict to PIL Image."""
    num_layers = draw_data['num_layers']
    num_qubits = draw_data['num_qubits']

    if num_layers == 0 or num_qubits == 0:
        # Return minimal image for empty circuit
        canvas = np.full((1, 1, 3), BG_COLOR, dtype=np.uint8)
        return Image.fromarray(canvas, 'RGB')

    width = num_layers * CELL_W
    height = num_qubits * CELL_H

    # Step 1: Allocate canvas with background color
    canvas = np.full((height, width, 3), BG_COLOR, dtype=np.uint8)

    # Step 2: Draw horizontal wires (1px line through center of each qubit row)
    for q in range(num_qubits):
        wire_y = q * CELL_H + CELL_H // 2
        canvas[wire_y, :] = WIRE_COLOR

    # Step 3: Draw control lines (before gates, so gates overlay)
    for gate in draw_data['gates']:
        if not gate['controls']:
            continue
        gx = gate['layer'] * CELL_W
        all_qubits = [gate['target']] + gate['controls']
        y_min = min(all_qubits) * CELL_H + CELL_H // 2
        y_max = max(all_qubits) * CELL_H + CELL_H // 2
        canvas[y_min:y_max + 1, gx] = CTRL_COLOR

    # Step 4: Draw gate blocks (2x2 colored rectangles)
    for gate in draw_data['gates']:
        gx = gate['layer'] * CELL_W
        gy = gate['target'] * CELL_H
        color = GATE_COLORS.get(gate['type'], (150, 150, 150))
        if gate['type'] == 9:  # Measurement - checkerboard pattern
            canvas[gy, gx] = color
            canvas[gy + 1, gx + 1] = color
            # Leave other 2 pixels as BG for texture
        else:
            canvas[gy:gy + 2, gx:gx + 2] = color

    # Step 5: Draw control dots (single bright pixel, rendered last)
    for gate in draw_data['gates']:
        if not gate['controls']:
            continue
        gx = gate['layer'] * CELL_W
        for ctrl in gate['controls']:
            cy = ctrl * CELL_H + CELL_H // 2
            canvas[cy, gx] = CTRL_COLOR

    return Image.fromarray(canvas, 'RGB')
```

### Example 2: Integration with circuit class
```python
# In __init__.py or draw.py, the public API:
def draw_circuit(**kwargs):
    """Render current circuit as pixel-art image.

    Returns
    -------
    PIL.Image.Image
        RGB image of circuit.
    """
    from ._core import circuit as _circuit_cls
    # Get the singleton circuit's draw_data
    c = _circuit_cls.__new__(_circuit_cls)
    data = c.draw_data()
    return render(data, **kwargs)
```

Note: The public API (draw_circuit, circuit.draw) belongs to Phase 47, not Phase 46. Phase 46 focuses on the render function itself.

### Example 3: PNG Save with Compression
```python
# PIL PNG compression level (0=no compression, 9=max; default=6)
img = render(draw_data)
img.save('circuit.png', compress_level=6)
```

### Example 4: Scale Testing
```python
# Memory estimation for large circuits:
# 200 qubits, 10,000 layers, CELL_W=3, CELL_H=3
# width = 10,000 * 3 = 30,000 px
# height = 200 * 3 = 600 px
# Memory = 30,000 * 600 * 3 bytes = 54,000,000 bytes = ~51.5 MB
# This is well within typical system memory limits.

import numpy as np
canvas = np.zeros((600, 30000, 3), dtype=np.uint8)
print(f"Memory: {canvas.nbytes / 1024 / 1024:.1f} MB")  # ~51.5 MB
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ASCII `circuit_visualize()` (C) | Pixel-art PNG renderer (Python) | This phase | Scales to 200+ qubits; visual clarity at scale |
| ImageDraw per-pixel calls | NumPy array bulk operations | Best practice | 10-100x faster for large images |
| RGBA with transparency | RGB on dark background | This phase | 25% less memory; simpler |
| Sprite sheets / external assets | Inline 2x2 color blocks | Context decision | No file I/O; no asset management |

## Cell Size Reconciliation

The context contains a potential conflict:
- REND-02 says "2-3px gate icons"
- ZOOM-01 says "2-3px per gate, full circuit visible"
- Context says "2x2 colored blocks" and "ultra-compact: 1-2px per cell"

**Resolution:** Use a **3x3 cell** (CELL_W=3, CELL_H=3) where:
- The **gate block** occupies a 2x2 region in the top-left of the cell
- The remaining 1px column and 1px row serve as implicit spacing
- The **wire** runs through the center row (y = q*3 + 1)
- This gives "2-3px gate icons" (2x2 block), "2-3px per gate" footprint (3px cell), and the wire flows through continuously

Alternative: Use **2x2 cells** (CELL_W=2, CELL_H=2) for maximum density where the gate block fills the entire cell and the wire is the background between gates. This matches "ultra-compact: 1-2px per cell" but makes wires invisible where gates are present. The 3x3 approach is recommended because it preserves wire visibility.

## Rendering Order

Critical for correct visual output:

1. **Background fill** -- `np.full((h, w, 3), BG_COLOR, dtype=np.uint8)`
2. **Horizontal wires** -- 1px lines through qubit row centers
3. **Vertical control lines** -- 1px lines spanning control-to-target range
4. **Gate blocks** -- 2x2 colored blocks (overwrites wire at gate position, which is correct)
5. **Control dots** -- 1px bright pixels at control qubit positions (rendered last so they are always visible)

## Memory Budget at Scale

| Circuit | Qubits | Layers | CELL=3 Dimensions | Memory (RGB) |
|---------|--------|--------|--------------------|--------------|
| Small | 8 | 50 | 150 x 24 | ~10 KB |
| Medium | 32 | 500 | 1500 x 96 | ~432 KB |
| Large | 64 | 5000 | 15000 x 192 | ~8.6 MB |
| Very Large | 200 | 10000 | 30000 x 600 | ~51.5 MB |
| Maximum | 200 | 30000 | 90000 x 600 | ~154 MB |

All sizes are within reason. PIL supports PNG images up to 65535 x 65535 (though very wide images may need `Image.MAX_IMAGE_PIXELS` override for loading, writing is unrestricted).

## Open Questions

1. **Exact muted/pastel color palette**
   - What we know: Dark background, gate colors grouped by category, H and M get distinct colors
   - What's unclear: Exact RGB values that look good together on a dark background
   - Recommendation: Start with the proposed palette (Pauli=muted purple, Rotation=muted cyan, H=warm yellow, P=muted green, M=muted red). Iterate visually. This is Claude's Discretion per context.

2. **Wire color**
   - What we know: Must contrast with dark background and muted gate colors, but not dominate
   - Recommendation: Dark gray-blue `(60, 60, 80)` -- visible but recessive. Claude's Discretion per context.

3. **Qubit labels on left margin**
   - What we know: Context marks this as Claude's Discretion
   - Recommendation: Skip labels at overview scale (Phase 46). At 3px per qubit row, text labels would be larger than the qubit rows themselves. Labels belong in the detail/zoom mode (Phase 47).

4. **CELL_W and CELL_H: 2 or 3?**
   - What we know: Context says "2x2 blocks" for gates and "ultra-compact: 1-2px per cell" but also "2-3px per gate"
   - Recommendation: Default CELL=3 (2px gate + 1px gap). Provide CELL=2 as a compact option. The render function should accept cell_size as a parameter for flexibility.

## Sources

### Primary (HIGH confidence)
- `c_backend/include/types.h` -- `Standardgate_t` enum: `{X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9}` (line 64)
- `c_backend/include/circuit_output.h` -- `draw_data_t` struct (lines 51-63), `circuit_to_draw_data()` and `free_draw_data()` declarations
- `src/quantum_language/_core.pyx` -- `draw_data()` method on circuit class (lines 413-461), returns dict with keys: num_layers, num_qubits, gates, qubit_map
- `.planning/phases/45-data-extraction-bridge/45-VERIFICATION.md` -- Phase 45 fully verified, draw_data() working and tested
- `.planning/research/ARCHITECTURE-PIXEL-VIZ.md` -- Prior architecture research confirming pure Python renderer approach
- `.planning/phases/46-core-renderer/46-CONTEXT.md` -- User decisions on colors, layout, gate design, control lines

### Secondary (MEDIUM confidence)
- [Pillow Image.fromarray documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html) -- API for NumPy array to PIL Image conversion
- [NumPy image processing with slicing](https://note.nkmk.me/en/python-numpy-image-processing/) -- Bulk slice assignment patterns for image pixel manipulation
- [PythonInformer: NumPy and images](https://www.pythoninformer.com/python-libraries/numpy/numpy-and-images/) -- Array shape conventions (height, width, channels)

### Tertiary (LOW confidence)
- [ImageDraw.point speed issues (Pillow #2450)](https://github.com/python-pillow/Pillow/issues/2450) -- Evidence that ImageDraw has significant per-call overhead, supporting the NumPy bulk approach
- [Pillow PNG save performance (Pillow #5986)](https://github.com/python-pillow/Pillow/issues/5986) -- PNG compression performance characteristics

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- NumPy already in project, Pillow is de facto standard, API is well-documented and stable
- Architecture: HIGH -- Single-file renderer with NumPy arrays is straightforward; all input data (draw_data dict) already verified working in Phase 45
- Pitfalls: HIGH -- Array axis order, rendering order, and memory estimation are well-understood; edge cases (empty circuit, large scale) identified from codebase inspection

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (stable; NumPy and Pillow APIs change rarely)
