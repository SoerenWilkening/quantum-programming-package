# Technology Stack

**Project:** Quantum Assembly - Pixel-Art Circuit Visualization
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

Pixel-art circuit visualization requires exactly one new dependency: Pillow (PIL). The existing project has no image dependencies. Pillow 12.1.0 provides everything needed for pixel-level rendering, text labeling, palette-mode PNG export, and nearest-neighbor upscaling. No other libraries are needed. NumPy (already a project dependency) accelerates bulk pixel operations when Pillow's per-pixel methods are too slow.

The approach: build a compact pixel-art renderer entirely in Python, consuming circuit data exposed through existing Cython bindings. Each gate becomes a 2-3px colored block on qubit wire lines, with control connections as vertical pixel lines. Output is a small PNG (palette mode, lossless) that can be optionally upscaled with nearest-neighbor interpolation for display.

## New Dependencies

### Required: Pillow

| Package | Version | Purpose | Why This Version |
|---------|---------|---------|------------------|
| Pillow | >=12.1.0 | Image creation, pixel drawing, PNG export | Latest stable (Jan 2, 2026). Python 3.10-3.14 support. Mature (status 6). MIT-CMU license. |

**Installation:**
```bash
pip install "Pillow>=12.1.0"
```

**Add to pyproject.toml:**
```toml
[project.optional-dependencies]
viz = ["Pillow>=12.1.0"]
# Or add to main dependencies if visualization is a core feature:
# dependencies = [..., "Pillow>=12.1.0"]
```

**Rationale:** Pillow is the de facto standard for image manipulation in Python. It is a direct dependency (not test-only) because visualization is a user-facing feature. It has zero compiled sub-dependencies beyond its own C extensions (which are bundled in wheels).

### Already Present: NumPy

| Package | Current Spec | Purpose for Visualization |
|---------|-------------|---------------------------|
| numpy | >=1.24 | Fast bulk pixel array construction via `Image.fromarray()` |

NumPy is already a project dependency. For pixel-art rendering, it provides a critical performance path: instead of calling `putpixel()` in loops (slow), construct a NumPy array of the full image and convert with `Image.fromarray(arr)`. This is 10-100x faster for images with thousands of pixels.

## Pillow API Recommendations for Pixel-Art Rendering

### Image Creation

```python
from PIL import Image, ImageDraw

# For small pixel-art (direct rendering at 1:1 scale)
# Use "P" (palette) mode for smallest file size with known color set
img = Image.new("P", (width, height), 0)  # 0 = background palette index

# For rendering with transparency support
img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
```

**Recommendation:** Use **RGB mode** during construction, then convert to **P (palette) mode** before saving. This gives full color flexibility during drawing while producing the smallest possible PNG output.

```python
# Construction phase
img = Image.new("RGB", (width, height), (255, 255, 255))
draw = ImageDraw.Draw(img)
# ... draw circuit ...

# Save phase - convert to palette for compact output
img_p = img.quantize(colors=32)  # Our palette has ~15-20 colors max
img_p.save("circuit.png", optimize=True)
```

### Drawing Methods (Ranked by Usefulness)

| Method | Use Case in Circuit Rendering | Performance |
|--------|-------------------------------|-------------|
| `draw.rectangle(xy, fill)` | Gate blocks (2-3px squares) | Fast |
| `draw.line(xy, fill, width)` | Qubit wires (horizontal lines), control connections (vertical lines) | Fast |
| `draw.point(xy, fill)` | Individual control dots, single-pixel markers | Fast for few points |
| `draw.text(xy, text, fill, font)` | Qubit labels (q0, q1...), gate labels if upscaled | Moderate |
| `Image.fromarray(arr)` | Bulk construction of entire image from NumPy | Fastest for full image |

**Performance hierarchy (fastest to slowest):**
1. `Image.fromarray(numpy_array)` - construct entire image at once
2. `Image.paste(color, box)` - fill rectangular regions
3. `ImageDraw.rectangle()` / `ImageDraw.line()` - draw primitives
4. `Image.putpixel(xy, color)` - individual pixels (AVOID in loops)

### Recommended Approach: NumPy Array Construction

For a compact pixel-art renderer where every pixel is deliberate, the fastest approach is:

```python
import numpy as np
from PIL import Image

def render_circuit(circuit_data, num_qubits, num_layers):
    # Calculate dimensions
    # Each gate cell: 3px wide x 3px tall
    # Qubit wire spacing: 5px (3px gate + 2px gap)
    # Layer spacing: 4px (3px gate + 1px gap)
    CELL_W, CELL_H = 3, 3
    WIRE_SPACING = 5
    LAYER_SPACING = 4
    MARGIN = 2

    width = MARGIN + num_layers * LAYER_SPACING + MARGIN
    height = MARGIN + num_qubits * WIRE_SPACING + MARGIN

    # Create pixel array (RGB)
    pixels = np.full((height, width, 3), 255, dtype=np.uint8)  # white bg

    # Draw qubit wires (horizontal gray lines)
    for q in range(num_qubits):
        y = MARGIN + q * WIRE_SPACING + CELL_H // 2
        pixels[y, MARGIN:width-MARGIN] = [180, 180, 180]  # gray wire

    # Draw gates as colored blocks
    for layer_idx, layer in enumerate(circuit_data):
        for gate in layer:
            x = MARGIN + layer_idx * LAYER_SPACING
            y = MARGIN + gate.target * WIRE_SPACING
            color = GATE_COLORS[gate.type]
            pixels[y:y+CELL_H, x:x+CELL_W] = color

    return Image.fromarray(pixels)
```

### Upscaling for Display

Pixel art at 1:1 is tiny. Use **nearest-neighbor** resampling to upscale without blurring:

```python
# Scale up 4x for display (each pixel becomes 4x4 block)
SCALE = 4
display_img = img.resize(
    (img.width * SCALE, img.height * SCALE),
    resample=Image.Resampling.NEAREST  # Critical: preserves hard edges
)
display_img.save("circuit_display.png")
```

**Resampling options and when to use:**
| Resampling | Effect | Use For |
|------------|--------|---------|
| `NEAREST` | Sharp pixel edges, no interpolation | Pixel art upscaling (USE THIS) |
| `BILINEAR` | Smooth blending | Photos (DO NOT use for pixel art) |
| `BICUBIC` | Smoother blending (default) | Photos (DO NOT use for pixel art) |
| `LANCZOS` | Sharpest smooth scaling | High-quality photo downscaling |

### Text Rendering for Labels

For qubit labels and gate annotations at small sizes:

```python
from PIL import ImageFont

# Option 1: Default bitmap font (always available, no file needed)
font = ImageFont.load_default()  # ~11px, monospaced-ish

# Option 2: Small TrueType font (if available)
try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", size=8)
except OSError:
    font = ImageFont.load_default()

# Anti-aliasing control for pixel art
draw = ImageDraw.Draw(img)
draw.fontmode = "1"  # Disable anti-aliasing (crisp pixel text)
draw.text((x, y), "q0", fill=(0, 0, 0), font=font)
```

**Recommendation:** Use `ImageFont.load_default()` for the base pixel-art view. It requires no external font files and works everywhere. For upscaled views (4x+), consider a small monospace TrueType font at 8-10px for crisper labels.

**Critical setting:** Set `draw.fontmode = "1"` to disable anti-aliasing. Anti-aliased text on a palette-mode image creates unwanted intermediate colors.

## Image Format Recommendations

### PNG (Primary Output)

| Setting | Value | Why |
|---------|-------|-----|
| Format | PNG | Lossless, perfect for pixel art, universal support |
| Mode | P (palette) | 1 byte/pixel instead of 3 (RGB), smallest files |
| `optimize` | `True` | Enables maximum ZLIB compression |
| `compress_level` | N/A (auto 9 with optimize) | optimize=True overrides to 9 |
| Colors | 16-32 via `quantize()` | Our palette is small; fewer colors = smaller file |
| `bits` | Auto (experimental if set) | Let Pillow choose based on palette size |

**Typical file sizes for circuit images:**
- 20 qubits x 50 layers, palette PNG: ~500 bytes to 2KB
- 100 qubits x 200 layers, palette PNG: ~5-15KB
- Same circuits upscaled 4x: ~2-8KB and ~20-60KB (PNG compresses repeated blocks well)

### Save Implementation

```python
def save_circuit_image(img, path, scale=1):
    """Save circuit image as optimized PNG."""
    if scale > 1:
        img = img.resize(
            (img.width * scale, img.height * scale),
            resample=Image.Resampling.NEAREST
        )

    # Convert to palette mode for smallest file
    if img.mode != "P":
        img = img.quantize(colors=32)

    img.save(path, format="PNG", optimize=True)
```

### SVG (Do NOT Implement)

**Why not SVG:**
- The entire point is pixel-art aesthetic, not scalable vector graphics
- SVG would be larger than PNG for pixel-level content
- SVG rendering varies across viewers for sub-pixel content
- Adds XML generation complexity with no benefit
- If users want SVG, they want a different visualization style entirely (not this milestone)

### JPEG (Do NOT Use)

**Why not JPEG:**
- Lossy compression destroys pixel-perfect rendering
- Creates artifacts around sharp color boundaries (every gate edge)
- Larger than palette PNG for this type of content
- No transparency support

### WebP (Optional Future Enhancement)

WebP lossless can be smaller than PNG. Not worth adding now but note for future:
```python
img.save("circuit.webp", lossless=True)  # Pillow supports WebP natively
```

## Color Palette Design

### Gate Color Scheme

Design a compact palette where each gate type has a distinct, recognizable color. Use bold, saturated colors against white/light background for pixel-art readability.

| Gate | RGB Color | Hex | Rationale |
|------|-----------|-----|-----------|
| H (Hadamard) | (66, 133, 244) | #4285F4 | Blue - most common single-qubit gate |
| X (Pauli-X) | (234, 67, 53) | #EA4335 | Red - NOT gate, action/change |
| Y (Pauli-Y) | (251, 188, 4) | #FBBC04 | Yellow - Pauli family, distinct from X/Z |
| Z (Pauli-Z) | (52, 168, 83) | #34A853 | Green - Pauli family, distinct from X/Y |
| P (Phase) | (171, 71, 188) | #AB47BC | Purple - phase rotation |
| Rx | (255, 112, 67) | #FF7043 | Orange-red - rotation variant of X |
| Ry | (255, 202, 40) | #FFCA28 | Gold - rotation variant of Y |
| Rz | (102, 187, 106) | #66BB6A | Light green - rotation variant of Z |
| M (Measure) | (69, 69, 69) | #454545 | Dark gray - terminal operation |
| Control dot | (0, 0, 0) | #000000 | Black - control qubit marker |
| Wire | (189, 189, 189) | #BDBDBD | Light gray - qubit wires |
| Background | (255, 255, 255) | #FFFFFF | White - clean background |
| CNOT target | (234, 67, 53) | #EA4335 | Red circle/cross - matches X |
| CCX target | (234, 67, 53) | #EA4335 | Red - matches X family |

**Total unique colors: 14** (fits comfortably in palette mode with 16-32 color slots)

**Design principles:**
1. Pauli gates (X, Y, Z) use primary colors (red, yellow, green)
2. Rotation gates use lighter/warmer variants of their Pauli counterpart
3. H is blue (most common, needs to stand out)
4. Phase is purple (distinct from all Pauli colors)
5. Measurement is gray (terminal, non-unitary)
6. Control elements are black (maximum contrast)

### Palette as Python Constant

```python
# Gate color palette - RGB tuples
GATE_COLORS = {
    "H":       (66, 133, 244),   # Blue
    "X":       (234, 67, 53),    # Red
    "Y":       (251, 188, 4),    # Yellow
    "Z":       (52, 168, 83),    # Green
    "P":       (171, 71, 188),   # Purple
    "Rx":      (255, 112, 67),   # Orange-red
    "Ry":      (255, 202, 40),   # Gold
    "Rz":      (102, 187, 106),  # Light green
    "M":       (69, 69, 69),     # Dark gray
    "control": (0, 0, 0),        # Black
    "wire":    (189, 189, 189),  # Light gray
    "bg":      (255, 255, 255),  # White
}

# Map from C enum Standardgate_t values to color keys
GATE_TYPE_MAP = {
    0: "X",   # X = 0 in enum
    1: "Y",   # Y = 1
    2: "Z",   # Z = 2
    3: "Rx",  # R = 3 (generic rotation, map to Rx)
    4: "H",   # H = 4
    5: "Rx",  # Rx = 5
    6: "Ry",  # Ry = 6
    7: "Rz",  # Rz = 7
    8: "P",   # P = 8
    9: "M",   # M = 9
}
```

## What NOT to Add

### 1. Do NOT add matplotlib

**Why not:**
- Massive dependency tree (50+ MB)
- Designed for plots and charts, not pixel-art
- Antialiases everything by default (opposite of what we want)
- Pillow is 10x lighter and gives pixel-level control
- matplotlib circuit drawing exists in Qiskit but produces a completely different aesthetic

### 2. Do NOT add cairo / pycairo / cairocffi

**Why not:**
- Vector graphics library (we want raster pixel art)
- Complex system dependency (requires libcairo C library)
- Overkill for 3px gate blocks
- Cross-platform installation headaches

### 3. Do NOT add Pygame or arcade

**Why not:**
- Game engines, not image generation libraries
- Require display server / windowing system
- Cannot run headless (server/CI environments)
- Pillow is headless-compatible

### 4. Do NOT add imageio or scikit-image

**Why not:**
- Scientific image processing libraries
- Add heavy dependencies (scipy, etc.)
- No drawing primitives (they process existing images)
- We need to CREATE images, not process them

### 5. Do NOT add wand (ImageMagick binding)

**Why not:**
- Requires ImageMagick system installation
- Heavier than Pillow for simple drawing
- No advantage for pixel-art use case

### 6. Do NOT add any pixel-art-specific libraries (pixelart, pyxel, etc.)

**Why not:**
- Niche libraries with uncertain maintenance
- Pillow + NumPy provides everything needed
- Adding niche dependencies creates supply-chain risk
- Our use case is simple enough for core Pillow

### 7. Do NOT render in C backend

**Why not:**
- C has no standard image library (would need libpng, zlib)
- Adds complex build dependencies
- Python/Pillow is fast enough (we're generating tiny images)
- Keep C backend focused on quantum operations
- Python layer has easier color/font/format handling

## Integration Architecture

```
Existing C Backend                    New Python Visualization Layer
========================             ==============================

circuit_t                            circuit_to_pixel_art()
  |-- used_layer                       |
  |-- used_qubits                      |-- reads circuit data via Cython
  |-- sequence[layer][gate]            |-- constructs NumPy pixel array
       |-- Gate (enum)                 |-- converts to PIL Image
       |-- Target (qubit_t)            |-- applies palette optimization
       |-- Control[] (qubit_t)         |-- saves as PNG
       |-- NumControls                 |
       |-- GateValue (double)          |-- optional: upscale with NEAREST
                                       |-- optional: add text labels

Data Flow:
  circuit_t (C) --> Cython exposure --> Python dict/list --> NumPy array --> PIL Image --> PNG file
```

### Cython Data Extraction

The visualization layer needs read access to circuit data. The existing Cython bindings expose `circuit_visualize()` (which prints to stdout), but for image rendering we need structured data. Options:

**Option A (Recommended): Add Cython method returning Python data**
```python
# In _core.pyx, add to circuit class:
def get_circuit_data(self):
    """Return circuit structure as Python dict for visualization."""
    cdef circuit_t* circ = <circuit_t*>_circuit
    layers = []
    for layer_idx in range(circ.used_layer):
        gates = []
        for gate_idx in range(circ.used_gates_per_layer[layer_idx]):
            g = circ.sequence[layer_idx][gate_idx]
            gates.append({
                'type': g.Gate,
                'target': g.Target,
                'controls': [g.Control[i] for i in range(g.NumControls)],
                'value': g.GateValue,
            })
        layers.append(gates)
    return {'layers': layers, 'num_qubits': circ.used_qubits + 1}
```

**Option B: Parse text output of circuit_visualize()**
Not recommended. Fragile, lossy (loses gate values), harder to maintain.

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|-----------|--------|-------|
| Pillow version (12.1.0) | HIGH | [PyPI](https://pypi.org/project/pillow/), [Official docs](https://pillow.readthedocs.io/en/stable/) | Released Jan 2, 2026 |
| Pillow drawing API | HIGH | [ImageDraw docs](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) | Stable API, extensively documented |
| NEAREST resampling | HIGH | [Image.resize docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) | Core feature, always available |
| PNG palette optimization | HIGH | [Image formats docs](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) | Well-documented save options |
| NumPy integration | HIGH | [Image.fromarray docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) | Standard NumPy interop |
| Font rendering | HIGH | [ImageFont docs](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html) | load_default() always available |
| Color palette design | MEDIUM | Design decision, not verified externally | Based on accessibility best practices |
| Gate enum mapping | HIGH | Codebase analysis of types.h line 64 | `enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M }` |

## Sources

- [Pillow 12.1.0 on PyPI](https://pypi.org/project/pillow/) - version and compatibility
- [Pillow ImageDraw Documentation](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) - drawing API
- [Pillow Image Documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html) - resize, fromarray, putpixel
- [Pillow ImageFont Documentation](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html) - font loading and text
- [Pillow Image File Formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) - PNG save options
- [Pillow GitHub Releases](https://github.com/python-pillow/Pillow/releases) - release history
- [Pillow Concepts - Modes](https://pillow.readthedocs.io/en/stable/handbook/concepts.html) - image modes (P, RGB, RGBA)
