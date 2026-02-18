# Phase 47: Detail Mode & Public API - Research

**Researched:** 2026-02-03
**Domain:** PIL/Pillow rendering, Python API design, zoom-level visualization
**Confidence:** HIGH

## Summary

Phase 47 extends the existing overview-mode renderer (`draw.py`, 121 lines) with a detail mode (8-12px per gate with readable labels) and wraps everything in a clean `ql.draw_circuit()` public API. The existing infrastructure is solid: `draw.py` already renders gates as NumPy arrays converted to PIL Images, the `draw_data()` method on circuit objects returns a structured dict with `num_layers`, `num_qubits`, `gates` (each with `layer`, `target`, `type`, `angle`, `controls`), and `qubit_map`.

The detail mode requires text rendering (gate labels like "H", "X", "Rx") which means using `PIL.ImageDraw` for text operations. This is acceptable since detail mode targets smaller circuits (<=30 qubits, <=200 layers) where per-gate ImageDraw calls are not a performance bottleneck. The auto-zoom logic, public API function, and lazy Pillow import are straightforward Python patterns.

**Primary recommendation:** Add a `render_detail()` function to `draw.py` that uses ImageDraw for gate boxes with text labels at 10px cell size, then add `draw_circuit()` to `__init__.py` as a standalone function that calls the appropriate renderer based on auto-zoom or user override.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.0 (installed) | Image creation, text rendering, PNG output | Already a dependency in setup.py (`Pillow>=9.0`). PIL.ImageDraw provides text rendering needed for gate labels. |
| NumPy | (installed) | Canvas array operations | Already used in overview mode. Detail mode can also use NumPy for background/wires, then ImageDraw for text. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PIL.ImageFont | (bundled with Pillow) | Font loading for gate labels | `ImageFont.load_default(size=8)` provides a clean built-in font at small sizes, no external font files needed. |
| PIL.ImageDraw | (bundled with Pillow) | Drawing rectangles and text on PIL Images | For gate boxes with borders and text labels in detail mode. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ImageDraw for detail mode | Pure NumPy pixel manipulation for text | Would require hand-rolling a bitmap font. Not worth it for detail mode's small circuit target. |
| Pillow's built-in default font | External TTF file | Would add a file dependency and font licensing concern. Pillow's default font is clean at 8-10px. |

**Installation:** No new dependencies needed. Pillow is already declared in `setup.py` line 96.

## Architecture Patterns

### Current File Structure
```
src/quantum_language/
├── __init__.py         # Public API, exports ql.* functions
├── _core.pyx           # Cython: circuit class with draw_data() method
├── _core.pxd           # Cython declarations including draw_data_t struct
├── draw.py             # Current overview renderer (121 lines)
├── qint.py             # Quantum integer type
├── qbool.py            # Quantum boolean type
├── ...
tests/
├── test_draw_render.py # 21 tests for overview renderer (442 lines)
├── test_draw_data.py   # Tests for draw_data extraction
```

### Pattern 1: Single Module with Mode Dispatch
**What:** Keep all rendering in `draw.py`. Add `render_detail()` alongside existing `render()`. Add a top-level `draw_circuit()` function that handles mode selection.
**When to use:** This phase -- keeps rendering code cohesive.
**Example:**
```python
# In draw.py:
def render(draw_data, cell_size=3):
    """Overview mode renderer (existing)."""
    ...

def render_detail(draw_data, cell_size=10):
    """Detail mode renderer with gate labels."""
    ...

def draw_circuit(draw_data, mode=None, save=None):
    """Auto-zoom dispatcher + public API."""
    ...
```

### Pattern 2: Lazy Import with Helpful Error
**What:** Defer Pillow import to function call time, raise ImportError with install instructions if missing.
**When to use:** For `ql.draw_circuit()` in `__init__.py`.
**Example:**
```python
# In __init__.py:
def draw_circuit(circuit, mode=None, save=None):
    """Render circuit as image."""
    try:
        from .draw import draw_circuit as _draw
    except ImportError:
        raise ImportError(
            "Pillow is required for circuit visualization. "
            "Install with: pip install Pillow"
        )
    return _draw(circuit.draw_data(), mode=mode, save=save)
```

### Pattern 3: Gate Type Integer-to-Label Mapping
**What:** The C backend defines gate types as enum: `X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9`. The draw_data dict provides `type` as an integer. Detail mode needs a mapping to string labels.
**Example:**
```python
GATE_LABELS = {
    0: "X", 1: "Y", 2: "Z", 3: "R", 4: "H",
    5: "Rx", 6: "Ry", 7: "Rz", 8: "P", 9: "M",
}
```

### Anti-Patterns to Avoid
- **Importing Pillow at module level in `__init__.py`:** This would make `import quantum_language` fail when Pillow is not installed. The draw.py module can import PIL at module level (it already does), but `__init__.py` must NOT import draw.py at module level.
- **Using ImageDraw for overview mode:** Overview mode works well with pure NumPy. Don't refactor it to use ImageDraw -- it's slower for large circuits.
- **Passing the circuit object directly to draw.py:** Keep the boundary clean. `__init__.py` calls `circuit.draw_data()` and passes the dict to the renderer. The renderer should not know about circuit objects.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text rendering at small sizes | Bitmap font array | `ImageFont.load_default(size=8)` + `ImageDraw.text()` | Pillow's built-in font is anti-aliased and handles all ASCII characters cleanly |
| Checkerboard scaling for measurement | Manual pixel loops at detail scale | Scale up the 2x2 pattern to fill the cell with a tiled pattern | Consistent with overview mode decision |
| Auto-zoom threshold logic | Complex heuristic | Simple AND condition: `num_qubits > 30 AND num_layers > 200` -> overview | Per context decision, hardcoded constants |

**Key insight:** Pillow already provides everything needed for detail mode. The only new capability is text rendering, which `ImageDraw.text()` handles trivially.

## Common Pitfalls

### Pitfall 1: Pillow Import at Module Load Time
**What goes wrong:** If `draw.py` is imported from `__init__.py` at module level, and Pillow is not installed, `import quantum_language` fails entirely -- breaking all non-visualization functionality.
**Why it happens:** Natural tendency to add `from .draw import draw_circuit` at the top of `__init__.py`.
**How to avoid:** Use a wrapper function in `__init__.py` that does a lazy import of `.draw` only when `draw_circuit()` is called.
**Warning signs:** `ImportError: No module named 'PIL'` when importing `ql` on a system without Pillow.

### Pitfall 2: Font Size vs Cell Size Mismatch
**What goes wrong:** Gate labels overflow their boxes or are too small to read if font size doesn't match cell size.
**Why it happens:** Pillow font sizes don't map 1:1 to pixel dimensions. A "size 8" font can produce glyphs wider than 8px (e.g., "Rx" at size 8 is 11px wide per testing).
**How to avoid:** Use `font.getbbox(label)` to measure text size. Choose cell_size large enough for the widest label ("Rx", "Ry", "Rz" at ~11px wide at size 8). A cell size of 10-12px with font size 7-8 works well. Test empirically.
**Warning signs:** Labels clipped or overlapping gate borders.

### Pitfall 3: Detail Mode on Large Circuits
**What goes wrong:** User forces detail mode on a 200-qubit x 10K-layer circuit, producing a 120K x 2400 pixel image (enormous).
**Why it happens:** Detail mode uses 10-12px cells instead of 3px.
**How to avoid:** Print a warning when detail mode is forced on large circuits (per context decision). Still honor the request.
**Warning signs:** Very large image dimensions, high memory usage, slow rendering.

### Pitfall 4: Measurement Gate Without Label
**What goes wrong:** Measurement gates should use a scaled-up checkerboard icon, NOT an "M" text label. If treated like other gates, it breaks the visual distinction.
**Why it happens:** Natural tendency to label all gates with text.
**How to avoid:** Special-case gate type 9 (M) in detail mode: render a larger checkerboard pattern instead of text. This is explicitly decided in context.
**Warning signs:** Measurement gates look identical to other gates with just an "M" label.

### Pitfall 5: Wire Continuation After Measurement
**What goes wrong:** Wire lines continue past measurement gates, suggesting further quantum operations are possible.
**Why it happens:** Overview mode renders wires across the full width. Same pattern in detail mode would violate the context decision.
**How to avoid:** In detail mode, track which qubits have been measured. Stop drawing wire pixels after the measurement gate's layer.
**Warning signs:** Horizontal wire lines extending to the right of measurement gates.

## Code Examples

### Verified: Pillow Default Font at Small Sizes
```python
# Tested on Pillow 12.1.0 (installed in this project)
from PIL import ImageFont

font = ImageFont.load_default(size=8)
# "H"  bounding box: (0, 3, 7, 8)  -> 7px wide, 5px tall
# "Rx" bounding box at size 10: (0, 2, 11, 10) -> 11px wide, 8px tall
# "Rx" bounding box at size 12: (0, 3, 13, 12) -> 13px wide, 9px tall
```
**Source:** Local testing, Pillow 12.1.0

### Verified: ImageDraw Rectangle + Text for Gate Box
```python
from PIL import Image, ImageDraw, ImageFont

cell = 10  # 10px per cell for detail mode
img = Image.new('RGB', (width, height), BG_COLOR)
draw = ImageDraw.Draw(img)
font = ImageFont.load_default(size=8)

# Gate box with 1px border
x, y = layer * cell, qubit * cell
draw.rectangle([x+1, y+1, x+cell-2, y+cell-2], fill=gate_color, outline=border_color)

# Centered text label
bbox = font.getbbox(label)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = x + (cell - tw) // 2
ty = y + (cell - th) // 2 - bbox[1]
draw.text((tx, ty), label, fill=(255, 255, 255), font=font)
```
**Source:** Local testing

### Existing draw_data Dict Structure
```python
# From _core.pyx draw_data() method (line 413):
{
    'num_layers': int,     # Number of circuit layers
    'num_qubits': int,     # Number of active qubits (compacted)
    'gates': [             # List of gate dicts
        {
            'layer': int,      # Layer index (x position)
            'target': int,     # Target qubit (y position, compacted)
            'type': int,       # Gate type 0-9 (X,Y,Z,R,H,Rx,Ry,Rz,P,M)
            'angle': float,    # Rotation angle
            'controls': [int], # Control qubit indices (compacted)
        },
        ...
    ],
    'qubit_map': [int],    # Maps dense row -> original sparse qubit
}
```
**Source:** `src/quantum_language/_core.pyx` lines 413-461

### Existing Public API Pattern in __init__.py
```python
# Current pattern: functions imported directly from _core
from ._core import (circuit, circuit_stats, get_current_layer, option, ...)

# draw_circuit should follow the SAME pattern but with lazy import:
def draw_circuit(circuit, mode=None, save=None):
    """..."""
    try:
        from .draw import draw_circuit as _impl
    except ImportError:
        raise ImportError("Pillow is required...")
    return _impl(circuit.draw_data(), mode=mode, save=save)
```
**Source:** `src/quantum_language/__init__.py` lines 41-49

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ImageFont.load_default()` (no size param) | `ImageFont.load_default(size=N)` | Pillow 10.0+ | Can specify font size without external TTF file |
| Manual bitmap fonts for small text | Pillow's built-in DejaVu-based default font | Pillow 10.0+ | Clean anti-aliased text at all sizes |

**Note:** `ImageFont.load_default(size=N)` requires Pillow >= 10.0. The project requires `Pillow>=9.0` in setup.py. This should be bumped to `Pillow>=10.0` to ensure `load_default(size=...)` works. Alternatively, use `ImageFont.load_default()` without size (returns size-10 font) or use `ImageFont.truetype()` with a system font path.

**Recommendation:** Bump the Pillow dependency to `>=10.0` in setup.py. The installed version is 12.1.0, so no practical impact.

## Open Questions

1. **Exact cell size for detail mode**
   - What we know: Requirements say 8-12px per gate. Font testing shows "Rx" at size 8 is 11px wide. A cell of 10px is tight for 2-character labels with 1px border on each side.
   - What's unclear: Whether 10px or 12px cells look better. 12px gives more breathing room.
   - Recommendation: Use 12px cell size with 8px font. This gives 10px inner space (after 1px borders), which fits "Rx" (11px) tightly. Alternatively, 14px cells for more padding. This is Claude's discretion per context -- test during implementation.

2. **Wire termination after measurement in overview mode**
   - What we know: Context says wires do NOT continue after measurement. Currently overview mode draws wires across full width.
   - What's unclear: Whether this applies to overview mode too, or only detail mode.
   - Recommendation: Implement wire termination in detail mode (per context). Leave overview mode unchanged for now (it's already verified and working).

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/draw.py` -- Existing overview renderer, all constants and render() function
- `src/quantum_language/__init__.py` -- Current public API surface and import patterns
- `src/quantum_language/_core.pyx` lines 413-461 -- draw_data() method and return structure
- `src/quantum_language/_core.pxd` lines 78-92 -- draw_data_t C struct definition
- `c_backend/include/types.h` line 64 -- `Standardgate_t` enum (X=0..M=9)
- `setup.py` line 96 -- Current Pillow dependency declaration
- `tests/test_draw_render.py` -- 21 existing tests, test helpers, synthetic data patterns
- Local Pillow 12.1.0 testing -- Font sizes, bounding boxes, ImageDraw behavior

### Secondary (MEDIUM confidence)
- `.planning/phases/46-core-renderer/46-VERIFICATION.md` -- Phase 46 completion status and requirements satisfied

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pillow already installed and tested, no new dependencies
- Architecture: HIGH -- Existing code structure is clear, extension points obvious
- Pitfalls: HIGH -- All identified from direct code analysis and local testing

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (stable domain, no fast-moving dependencies)
