# Architecture: Pixel-Art Circuit Visualization

**Domain:** Quantum circuit rendering (pixel-art style)
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

This document defines how a pixel-art circuit renderer integrates with the existing three-layer architecture (C backend -> Cython bindings -> Python frontend). The recommended approach is: extract circuit data to Python via a new Cython function that returns a structured dictionary of gate/layer/qubit data, then render entirely in pure Python using Pillow. No C-level rendering is needed or wanted.

The key architectural decision is **where to cross the C-Python boundary**. Two options exist:

1. **One Cython call, structured extraction** -- A single new C function serializes the entire circuit into a flat representation, Cython converts to Python dict. Rendering happens in pure Python.
2. **Multiple Cython calls, field-by-field** -- Python code iterates layers/gates by calling existing Cython accessors repeatedly.

**Recommendation: Option 1** -- A single extraction function. This minimizes C-Python boundary crossings (which are expensive for large circuits) and keeps the renderer decoupled from C internals.

## Integration Points with Existing Components

### What Already Exists

| Component | Relevant State | How Viz Uses It |
|-----------|---------------|-----------------|
| `circuit_t` (C) | `sequence[layer][gate_index]` -- all gates by layer | Source of truth for gate data |
| `circuit_t.used_layer` | Number of layers | Determines image width |
| `circuit_t.used_qubits` | Number of qubits | Determines image height |
| `circuit_t.used_gates_per_layer[layer]` | Gates per layer | Iteration bounds |
| `gate_t` (C) | `Gate` (enum), `Target`, `Control[]`, `large_control`, `NumControls`, `GateValue` | Per-gate rendering info |
| `circuit_visualize()` (C) | Text-based ASCII renderer in `circuit_output.c` | Reference for iteration pattern -- reuse same loop structure |
| `_core.pyx` / `_core.pxd` | Cython bindings, `_circuit` global pointer | Entry point for data extraction |
| `circuit` class (Python) | `.visualize()`, `.depth`, `.qubit_count`, `.gate_counts` | API home for new `.draw()` method |
| `__init__.py` | Module exports | Will export `draw_circuit()` convenience function |
| `openqasm.pyx` | Separate .pyx module pattern for C -> Python data | Architectural precedent for dedicated Cython module |

### What Needs to Change

| Component | Change | Scope |
|-----------|--------|-------|
| **C backend** | New function `circuit_to_draw_data()` in `circuit_output.c` | ~80 lines new C code |
| **circuit_output.h** | Declare new struct + function | ~20 lines |
| **New: `_core.pxd`** | Add extern declarations for new C struct/function | ~15 lines |
| **New: `draw.py`** | Pure Python renderer module | ~300-500 lines, bulk of new code |
| **`_core.pyx`** | New method `circuit.draw_data()` returning Python dict | ~40 lines |
| **`__init__.py`** | Export `draw_circuit` function | ~5 lines |
| **New: pixel art assets** | PNG sprite sheets or inline pixel data | Asset files or embedded constants |

## Recommended Architecture

### Component Diagram

```
User calls: ql.draw_circuit() or circuit_obj.draw()
                    |
                    v
  +-----------------------------------------+
  | Python: __init__.py                      |
  |   draw_circuit() -> PIL.Image            |
  |     calls circuit_obj.draw_data()        |
  |     passes dict to renderer              |
  +-----------------------------------------+
                    |
        +-----------+-----------+
        |                       |
        v                       v
  +------------------+   +---------------------------+
  | Cython: _core.pyx|   | Python: draw.py           |
  | .draw_data()     |   | render(draw_data) -> Image |
  |  calls C func    |   |  - layout engine           |
  |  returns dict    |   |  - sprite placement        |
  +------------------+   |  - wire drawing            |
        |                |  - label rendering          |
        v                +---------------------------+
  +------------------+
  | C: circuit_output|
  | circuit_to_      |
  |  draw_data()     |
  | serializes gates |
  | to flat struct   |
  +------------------+
```

### Data Flow: circuit_t -> Python dict -> pixel coordinates -> PIL Image

**Step 1: C Extraction** (`circuit_output.c`)

The C function iterates the circuit exactly once and produces a flat, serializable representation:

```c
// New struct for draw data
typedef struct {
    unsigned int num_layers;
    unsigned int num_qubits;
    unsigned int num_gates;
    // Flat arrays -- one entry per gate
    unsigned int *gate_layer;    // which layer this gate is in
    unsigned int *gate_target;   // target qubit
    unsigned int *gate_type;     // Standardgate_t as int
    double *gate_angle;          // GateValue (for P gates)
    unsigned int *gate_num_ctrl; // number of controls
    // Control qubits stored as flattened array with offsets
    unsigned int *ctrl_qubits;   // all control qubits concatenated
    unsigned int *ctrl_offsets;  // ctrl_qubits[ctrl_offsets[i]..ctrl_offsets[i]+gate_num_ctrl[i]]
} draw_data_t;

draw_data_t *circuit_to_draw_data(circuit_t *circ);
void free_draw_data(draw_data_t *data);
```

Why flat arrays: Cython can convert flat C arrays to Python lists efficiently in a single pass. Nested structs would require per-element conversion.

**Step 2: Cython Conversion** (`_core.pyx`)

```python
def draw_data(self):
    """Extract circuit structure as Python dict for rendering.

    Returns
    -------
    dict
        Keys: num_layers, num_qubits, gates (list of gate dicts)
        Each gate dict: {layer, target, gate_type, angle, controls}
    """
    cdef draw_data_t *data = circuit_to_draw_data(<circuit_t*>_circuit)
    if data == NULL:
        raise RuntimeError("Failed to extract draw data")
    try:
        result = {
            'num_layers': data.num_layers,
            'num_qubits': data.num_qubits,
            'gates': []
        }
        ctrl_idx = 0
        for i in range(data.num_gates):
            controls = []
            for j in range(data.gate_num_ctrl[i]):
                controls.append(data.ctrl_qubits[data.ctrl_offsets[i] + j])
            result['gates'].append({
                'layer': data.gate_layer[i],
                'target': data.gate_target[i],
                'type': data.gate_type[i],
                'angle': data.gate_angle[i],
                'controls': controls,
            })
        return result
    finally:
        free_draw_data(data)
```

**Step 3: Python Layout Engine** (`draw.py`)

Maps logical positions (layer, qubit) to pixel coordinates:

```python
# Constants (pixel art grid)
CELL_WIDTH = 32    # pixels per layer column
CELL_HEIGHT = 32   # pixels per qubit row
WIRE_Y_OFFSET = 16 # wire runs through middle of cell
MARGIN_LEFT = 48   # space for qubit labels
MARGIN_TOP = 24    # space for layer labels

def layer_to_x(layer: int) -> int:
    return MARGIN_LEFT + layer * CELL_WIDTH

def qubit_to_y(qubit: int) -> int:
    return MARGIN_TOP + qubit * CELL_HEIGHT
```

**Step 4: Sprite Rendering** (`draw.py`)

Uses Pillow to composite sprites onto canvas:

```python
from PIL import Image, ImageDraw

def render(draw_data: dict) -> Image.Image:
    width = MARGIN_LEFT + draw_data['num_layers'] * CELL_WIDTH + MARGIN_LEFT
    height = MARGIN_TOP + draw_data['num_qubits'] * CELL_HEIGHT + MARGIN_TOP

    img = Image.new('RGBA', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Draw qubit wires (horizontal lines)
    # 2. Draw gate sprites at (layer_to_x, qubit_to_y)
    # 3. Draw control connections (vertical lines between control and target)
    # 4. Draw labels (qubit indices, layer numbers)

    return img
```

## Alternative Considered: Direct Field Access via Cython

Instead of a dedicated C extraction function, the renderer could call existing Cython properties repeatedly:

```python
# REJECTED approach
depth = circuit_obj.depth
qubits = circuit_obj.qubit_count
# Then iterate layers/gates via new per-layer accessor...
```

**Why rejected:**
- No existing per-gate accessor in Cython -- would need to add many new accessors
- Each Cython call crosses the C-Python boundary (overhead per call)
- For a 1000-layer, 64-qubit circuit, that is potentially thousands of boundary crossings
- The single-extraction approach crosses the boundary exactly once
- Follows the established pattern from `circuit_to_qasm_string()` (bulk extraction)

## Alternative Considered: JSON Serialization in C

Serialize circuit to JSON string in C, parse in Python:

**Why rejected:**
- Adds JSON dependency to C backend (or requires hand-rolled JSON formatter)
- String parsing overhead vs direct struct-to-dict conversion in Cython
- JSON is meant for interop with external tools, not internal data passing
- Cython struct-to-dict is type-safe and faster

## Alternative Considered: Rendering in C with libpng

**Why rejected:**
- Adds heavy C dependency (libpng or similar)
- Pixel art requires flexible composition (sprites, transparency, text)
- Pillow is already a Python ecosystem standard, likely already installed
- Python-level rendering is fast enough (we are generating static images, not real-time)
- Easier to iterate on visual design in Python than C
- C backend should remain focused on circuit logic, not presentation

## Sprite Strategy

### Option A: Embedded Pixel Data (Recommended)

Define gate sprites as Python constants (small 2D arrays of color values):

```python
# Each sprite is a small grid, e.g., 16x16 or 24x24 pixels
SPRITE_H = [
    [0, 0, 1, 1, 0, 0, 1, 1],
    [0, 0, 1, 1, 0, 0, 1, 1],
    [0, 0, 1, 1, 1, 1, 1, 1],
    [0, 0, 1, 1, 1, 1, 1, 1],
    [0, 0, 1, 1, 0, 0, 1, 1],
    [0, 0, 1, 1, 0, 0, 1, 1],
]
# 0 = transparent, 1 = foreground color
```

**Pros:** No external files needed, works anywhere, version-controlled.
**Cons:** Harder to edit visually (but sprites are small and few).

### Option B: External PNG Sprite Sheet

Store sprites in a PNG file, load at render time:

```python
SPRITES = Image.open(Path(__file__).parent / "assets" / "gate_sprites.png")
# Slice regions for each gate type
```

**Pros:** Easy to edit in any pixel art editor.
**Cons:** Requires bundling asset file, package_data in setup.py.

**Recommendation:** Start with Option A (embedded). Migrate to Option B only if the sprite set grows large or needs frequent visual iteration.

### Required Sprites

| Sprite | Size | Content | Used For |
|--------|------|---------|----------|
| `gate_x` | 24x24 | "X" in box | X/Pauli-X gate |
| `gate_y` | 24x24 | "Y" in box | Y/Pauli-Y gate |
| `gate_z` | 24x24 | "Z" in box | Z/Pauli-Z gate |
| `gate_h` | 24x24 | "H" in box | Hadamard gate |
| `gate_p` | 24x24 | "P" in box | Phase gate |
| `gate_m` | 24x24 | Meter icon | Measurement |
| `control_dot` | 8x8 | Filled circle | Control qubit |
| `target_dot` | 16x16 | Circle with + | CNOT target (when controlled X) |
| `wire_h` | cell_width x 2 | Horizontal line | Qubit wire |
| `wire_v` | 2 x variable | Vertical line | Control-target connection |

## Rendering Pipeline Detail

```
draw_data dict
    |
    v
[1] Calculate canvas size
    width = margin_left + num_layers * cell_width + margin_right
    height = margin_top + num_qubits * cell_height + margin_bottom
    |
    v
[2] Create RGBA canvas (background color)
    |
    v
[3] Draw horizontal wires for each active qubit
    For qubit q: draw line from (margin_left, qubit_to_y(q)) to (width - margin_right, qubit_to_y(q))
    |
    v
[4] Group gates by layer (they already have layer index)
    |
    v
[5] For each gate:
    a. Determine pixel position: (layer_to_x(layer), qubit_to_y(target))
    b. If gate has controls:
       - Draw vertical line from min(controls, target) to max(controls, target)
       - Draw control_dot at each control qubit position
       - Draw target sprite (target_dot for CX, gate sprite for other controlled gates)
    c. If gate has no controls:
       - Draw gate sprite at target position
    d. If gate is Phase type:
       - Optionally render angle text below sprite
    |
    v
[6] Draw labels
    - Qubit indices on left margin: "q0", "q1", ...
    - Layer numbers on top margin: "0", "5", "10", ...
    |
    v
[7] Return PIL.Image.Image
```

## Python Module Structure

```
src/quantum_language/
    __init__.py          # Add draw_circuit() export
    _core.pyx            # Add draw_data() method to circuit class
    _core.pxd            # Add extern declarations for draw_data_t
    draw.py              # NEW: Pure Python renderer (bulk of new code)
    sprites.py           # NEW: Embedded sprite definitions (or inline in draw.py)
```

**Why `draw.py` not `draw.pyx`:** No Cython needed. The renderer is pure Python operating on a Python dict. Pillow handles all pixel operations. Cython would add compilation complexity with zero performance benefit (bottleneck is Pillow image operations, not Python logic).

## Public API

### Primary: `ql.draw_circuit()`

```python
def draw_circuit(**kwargs) -> "PIL.Image.Image":
    """Render current circuit as pixel-art image.

    Parameters
    ----------
    scale : int, optional
        Pixel scale factor (default 1). Use 2 for retina.
    show_labels : bool, optional
        Show qubit/layer labels (default True).
    theme : str, optional
        Color theme: 'light', 'dark' (default 'light').
    max_layers : int, optional
        Maximum layers to render (default: all).

    Returns
    -------
    PIL.Image.Image
        RGBA image of circuit.
    """
```

### Secondary: `circuit.draw()`

```python
class circuit:
    def draw(self, **kwargs) -> "PIL.Image.Image":
        """Render this circuit as pixel-art image."""
        data = self.draw_data()
        from .draw import render
        return render(data, **kwargs)
```

### Convenience: Display in Jupyter

```python
# In draw.py
def render(draw_data, **kwargs):
    img = _render_impl(draw_data, **kwargs)
    return img  # PIL Image has _repr_png_ for Jupyter auto-display
```

PIL Images automatically display in Jupyter notebooks. No special integration needed.

## Dependency: Pillow

**Status:** Pillow (PIL) is the de facto standard Python imaging library.

- PyPI package: `Pillow`
- Current version: 10.x+ (stable, actively maintained)
- Already widely used in scientific Python ecosystem
- Likely already installed alongside numpy/scipy

**Recommendation:** Add `Pillow>=9.0` to `install_requires` in setup.py. This is a core rendering dependency, not optional.

**Alternative (no dependency):** Generate SVG strings instead of PIL Images. But SVG pixel art is awkward, and users expect PIL Image objects they can `.save()`, `.show()`, or display in Jupyter.

## Performance Considerations

| Circuit Size | Gates | Expected Render Time | Image Size |
|-------------|-------|---------------------|------------|
| Small (4 qubits, 10 layers) | ~20 | <50ms | ~400x200 px |
| Medium (16 qubits, 100 layers) | ~500 | ~200ms | ~3200x600 px |
| Large (64 qubits, 1000 layers) | ~10K | ~2s | ~32000x2100 px |
| Very Large (64 qubits, 10K layers) | ~100K | Truncate | Max ~60 layers shown |

**Truncation strategy:** Same as existing `circuit_visualize()` -- show first N layers with "(showing first N of M layers)" note. The `max_layers` parameter controls this.

**Data extraction:** The C function iterates the circuit once. For 100K gates, this is ~1ms. The bottleneck is always PIL rendering, not data extraction.

## Build Order (Suggested Phases)

### Phase 1: Data Extraction Layer

**Scope:** C function + Cython binding to extract circuit data as Python dict.

**Files changed:**
- `c_backend/include/circuit_output.h` -- new struct and function declaration
- `c_backend/src/circuit_output.c` -- `circuit_to_draw_data()` implementation
- `src/quantum_language/_core.pxd` -- extern declarations
- `src/quantum_language/_core.pyx` -- `circuit.draw_data()` method

**Test:** `circuit.draw_data()` returns correct dict for known circuit.

**Rationale:** Start here because rendering depends on having structured data. Also validates the C-Python data flow before investing in visual work.

### Phase 2: Basic Renderer (Wire + Single-Qubit Gates)

**Scope:** Pure Python renderer that draws wires and single-qubit gates (X, H, Z, Y, P).

**Files created:**
- `src/quantum_language/draw.py` -- renderer with layout engine
- `src/quantum_language/sprites.py` -- embedded sprite definitions (optional, could be in draw.py)

**Files changed:**
- `src/quantum_language/__init__.py` -- export `draw_circuit()`
- `setup.py` or `pyproject.toml` -- add Pillow dependency

**Test:** Render a circuit with single-qubit gates, visually verify output.

**Rationale:** Single-qubit gates are the simplest case. Get the layout engine, sprite system, and wire drawing working before adding multi-qubit gate complexity.

### Phase 3: Multi-Qubit Gates (Controls + Connections)

**Scope:** Add control dots, CNOT targets, vertical connection lines, multi-control gates.

**Files changed:**
- `src/quantum_language/draw.py` -- add control rendering logic

**Test:** Render circuits with CNOT, Toffoli, multi-controlled gates.

**Rationale:** Control connections are the hardest visual element (variable-length vertical lines, overlapping with other wires). Tackle after basic rendering is solid.

### Phase 4: Labels, Themes, Polish

**Scope:** Qubit labels, layer numbers, color themes (light/dark), scale parameter, truncation for large circuits.

**Files changed:**
- `src/quantum_language/draw.py` -- labels, themes, scaling

**Test:** Visual comparison across themes, large circuit truncation works.

**Rationale:** Polish after core functionality works. Labels and themes do not affect correctness.

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Data extraction via C struct | HIGH | Follows established `circuit_to_qasm_string()` pattern |
| Cython dict conversion | HIGH | Standard Cython array-to-list, used throughout codebase |
| Pillow rendering | HIGH | Well-documented, stable API, widespread use |
| Sprite approach | MEDIUM | Embedded sprites work but visual quality needs iteration |
| Performance at scale | MEDIUM | Pillow handles large images but very large circuits need truncation |
| API design | HIGH | Follows existing `circuit.visualize()` and `ql.to_openqasm()` patterns |

## Sources

- **Existing codebase:** `circuit_output.c` lines 178-277 (`circuit_visualize()`) -- iteration pattern for layers/gates/qubits
- **Existing codebase:** `openqasm.pyx` -- pattern for dedicated Cython module calling C function
- **Existing codebase:** `types.h` -- `gate_t` struct definition, `Standardgate_t` enum
- **Existing codebase:** `circuit.h` -- `circuit_t` struct with layer/gate organization
- **Existing codebase:** `_core.pxd` -- current Cython extern declarations
- **Pillow documentation:** `Image.new()`, `ImageDraw`, `Image.paste()` for sprite composition

## Gaps and Open Questions

1. **Sprite visual design:** Exact pixel art style not defined. Need to decide: retro 8-bit look vs clean minimal pixel art. Recommend starting minimal and iterating.

2. **Font for labels:** Pillow's default font is adequate for small labels. For pixel-perfect text, may want to embed a small bitmap font. Defer to Phase 4.

3. **Qubit ordering:** The C backend uses qubit indices that may not be contiguous (some qubits unused). The renderer should skip unused qubits, matching `circuit_visualize()` behavior (which checks `used_occupation_indices_per_qubit[qubit] != 0`).

4. **Phase gate angle display:** Phase gates have angle values. Decide whether to show angle as text, as a color variation, or not at all. Recommend: show as small text below gate sprite for Phase 4.
