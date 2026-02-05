# Feature Landscape: Pixel-Art Circuit Visualization

**Domain:** Quantum circuit visualization (compact pixel-art rendering)
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH

## Executive Summary

Quantum circuit visualization is a solved problem for small circuits (under 20 qubits) -- Qiskit's matplotlib drawer, Cirq's SVG renderer, and PennyLane's text drawer all handle this well. However, **visualization breaks down at scale**: Qiskit's `mpl` drawer becomes unreadable above ~40 qubits and unusable above ~60. The existing ASCII `circuit_visualize` in this framework caps display at 60 layers and skips rendering entirely above 2000 gates. Pixel-art rendering fills a genuine gap -- compact, scalable visualization of circuits with 100-200+ qubits and thousands of gates, where each gate occupies only 2-3 pixels and the full circuit structure remains visible.

The key insight from Quantivine (IEEE TVCG 2023) is that large-circuit visualization requires **semantic abstraction** -- not just shrinking the same diagram. For a pixel-art approach, this translates to two zoom levels: an overview mode showing circuit structure/density and a detail mode showing individual gates. This is the project's core differentiator.

## Table Stakes

Features users expect from any graphical circuit visualization. Missing any of these makes the output confusing or incomplete.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Horizontal qubit wires** | Universal convention -- qubits are horizontal lines, time flows left-to-right | **Low** | PIL ImageDraw lines | Every circuit diagram ever uses this layout |
| **Distinct gate symbols per type** | Users must tell X from H from P at a glance | **Medium** | Pixel icon design (2-3px shapes) | Color + shape combination needed at small scale |
| **Control-target connections** | Multi-qubit gates shown with vertical lines connecting control dot to target | **Medium** | Vertical line drawing between qubit rows | CNOT = filled dot + target circle/plus, connected by vertical line |
| **Qubit labels** | Users need to know which wire is which qubit | **Low** | Text rendering at left margin | `q0`, `q1`, ... at start of each wire |
| **Save to PNG** | Standard image output format | **Low** | `PIL.Image.save()` | Trivial with Pillow |
| **Return PIL Image object** | Programmatic access for Jupyter display, embedding, further processing | **Low** | Return `Image` from render function | `_repr_png_` enables Jupyter inline display |
| **Measurement gates** | Measurement is a distinct operation users must see | **Low** | Distinct icon (meter symbol or M box) | Standard circuit element |
| **Layer/time axis indication** | Users need to understand temporal ordering | **Low** | Optional column numbers or tick marks | Can be subtle at pixel scale |
| **Wire continuity** | Qubit wires must be continuous lines even when no gate is present | **Low** | Draw wire segments between gates | Empty columns get plain horizontal line |
| **Color legend** | At 2-3px per gate, color is the primary distinguishing feature -- legend is essential | **Medium** | Separate legend region or optional overlay | Without legend, pixel art is meaningless to new users |

## Differentiators

Features that make pixel-art visualization uniquely valuable compared to Qiskit/Cirq/text approaches. These justify building a new renderer rather than wrapping an existing one.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Overview zoom level** (2-3px gates) | See the ENTIRE circuit structure at once for 100+ qubit circuits -- no other tool does this | **Medium** | NumPy array for fast pixel placement, PIL Image.fromarray() | Core differentiator. Qiskit folds at 25 layers; this shows all layers |
| **Detail zoom level** (8-12px gates) | Readable gate labels for smaller circuits or selected regions | **Medium** | Larger icons with text labels | Matches what Qiskit/Cirq provide but in PIL format |
| **Scalability to 200+ qubits** | No existing open-source tool renders 200-qubit circuits legibly | **High** | Efficient layout algorithm, NumPy array rendering | Quantivine handles 100 qubits; this targets 200+ |
| **Color-coded gate categories** | Instant visual pattern recognition -- "where are all the phase gates?" | **Low** | Color palette definition per gate type | Qiskit supports this via style dict; pixel art makes it the PRIMARY identifier |
| **Circuit density heatmap** (overview) | Show where the circuit is "busy" vs "sparse" -- reveals optimization opportunities | **Medium** | Gate count per region, color intensity mapping | Novel feature -- no existing tool does this as a built-in |
| **Idle wire suppression** | Skip rendering unused qubit wires to compress vertical space | **Low** | Check `used_occupation_indices_per_qubit` from C backend | Already available: `circuit_visualize` skips unused qubits |
| **Fast rendering** (NumPy backend) | Render 10,000+ gate circuits in under 1 second | **Medium** | NumPy array manipulation instead of PIL pixel-by-pixel | PIL putpixel is slow; NumPy array + Image.fromarray() is 10-100x faster |
| **No matplotlib dependency** | Lighter weight than Qiskit's mpl drawer; PIL/Pillow only | **Low** | Pillow is the only dependency | Simpler install, no matplotlib/LaTeX |

## Anti-Features

Features to explicitly NOT build. Common mistakes in circuit visualization tools.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Interactive zoom/pan** | Requires GUI framework (tkinter/Qt), massive scope increase, out-of-scope per PROJECT.md | Generate static images at chosen zoom level; user can open in any image viewer |
| **LaTeX rendering** | Requires LaTeX installation, slow, fragile; Qiskit already does this well | PIL-only rendering; recommend Qiskit for publication-quality output |
| **SVG output** | Adds complexity for little benefit in the pixel-art paradigm; SVG is for vector graphics | PNG output only; pixel art is inherently raster |
| **Animated circuits** | GIF/video of circuit execution is a different product entirely | Static circuit diagram is the deliverable |
| **Gate parameter text at overview zoom** | At 2-3px per gate, text is illegible; forcing it creates visual noise | Use color/shape only at overview; show parameters only at detail zoom |
| **Classical register / measurement outcome wires** | The framework has no classical registers; adding fake ones misleads | Show measurement gate (M icon) on qubit wire; no double-line classical wire |
| **Custom gate definitions** | Framework decomposes everything to standard gates; custom boxes add confusion | Render only the standard gate types (X, Y, Z, H, P, Rx, Ry, Rz, M) |
| **Matplotlib backend option** | Duplicates Qiskit's functionality; stick to PIL for uniqueness and simplicity | PIL/NumPy only; this IS the alternative to matplotlib |
| **Real-time circuit building visualization** | Requires live rendering during `add_gate`; performance and architecture nightmare | Render complete circuit after construction; this is a snapshot tool |
| **Folding/wrapping** (Qiskit-style) | Folding at N layers loses the "see entire circuit" advantage that is the core value proposition | Use horizontal scrolling (wide images) or overview zoom instead |

## Feature Dependencies

### Core Rendering Pipeline

```
Circuit data access (from C backend via Cython)
    |-- Already available: gate_count, depth, qubit_count, gate_counts
    |-- Already available: used_occupation_indices_per_qubit (skip unused)
    |-- NEEDED: layer-by-layer gate iteration from Python
    |       |-- Option A: Expose circuit_t fields via Cython (preferred)
    |       |-- Option B: Parse OpenQASM string (wasteful but works)
    |       |-- Option C: New C function returning structured gate list
    |
    v
Layout computation (Pure Python)
    |-- Map each gate to (x, y) pixel coordinates
    |-- Handle multi-qubit gate vertical spans
    |-- Compute image dimensions
    |
    v
Pixel rendering (NumPy + PIL)
    |-- Create NumPy array of correct size
    |-- Draw qubit wires (horizontal lines)
    |-- Draw gate icons at computed positions
    |-- Draw control lines (vertical segments)
    |-- Convert to PIL Image via Image.fromarray()
    |
    v
Output
    |-- Return PIL Image object
    |-- Optional: save to file path
    |-- Optional: display in Jupyter via _repr_png_
```

### Gate Icon Design Dependencies

```
Overview icons (2-3px) -- color is primary identifier
    |-- Single-qubit: colored square (2x2 or 3x3)
    |-- CNOT target: small plus or circle
    |-- Control dot: single dark pixel
    |-- Measurement: distinct color (e.g., gray)

Detail icons (8-12px) -- shape + text label
    |-- Single-qubit: colored box with 1-2 char label
    |-- CNOT target: circle with plus inside
    |-- Control dot: filled circle
    |-- Measurement: meter symbol or "M" box
    |-- Phase/rotation: box with angle indicator
```

### Zoom Level Dependencies

```
Overview mode (default for circuits > threshold)
    |-- Requires: gate icon set at 2-3px
    |-- Requires: color palette for gate categories
    |-- Requires: wire drawing at 1px height
    |-- Optional: density heatmap overlay
    |
Detail mode (default for circuits <= threshold)
    |-- Requires: gate icon set at 8-12px
    |-- Requires: text rendering for gate labels
    |-- Requires: wire drawing at 1-2px height
    |-- Threshold suggestion: 30 qubits / 100 layers
```

## Gate Type Color Palette Recommendation

Based on quantum computing conventions (Qiskit textbook style, Qniverse color categories).

| Gate Category | Gates | Recommended Color | Hex | Rationale |
|---------------|-------|-------------------|-----|-----------|
| Pauli gates | X, Y, Z | Blue | `#4488CC` | Standard "basic operation" color |
| Hadamard | H | Green | `#44AA66` | Distinct from Pauli, common gate deserves own color |
| Phase/rotation | P, Rx, Ry, Rz | Orange | `#CC8844` | Parameterized gates grouped visually |
| Control dot | (control qubit) | Black | `#222222` | Universal convention: filled circle = control |
| CNOT target | (target of controlled-X) | Blue | `#4488CC` | Same as X gate (it IS an X gate) |
| Measurement | M | Gray | `#888888` | Non-unitary, visually distinct from gates |
| Wire | (qubit line) | Light gray | `#CCCCCC` | Background element, should not compete with gates |
| Background | | White | `#FFFFFF` | Clean, maximizes contrast |

Confidence: MEDIUM -- color choices are subjective; these follow established conventions from Qiskit's textbook theme and general UX principles for categorical color coding.

## MVP Recommendation

### Must Have (Phase 1: Core Renderer)

1. **Circuit data extraction from C backend to Python**
   - Iterate layers and gates from Python code
   - Get gate type, target qubit, control qubits, gate value for each gate
   - This is the critical dependency -- everything else is pure Python

2. **Overview mode rendering** (2-3px gates)
   - NumPy array-based rendering for performance
   - Horizontal qubit wires, colored gate pixels, vertical control lines
   - Color-coded by gate category
   - Handles circuits up to 200 qubits, 10,000+ gates

3. **Python API `ql.draw_circuit()`**
   - Returns PIL Image
   - Optional `filename` parameter for direct save
   - Optional `zoom` parameter (`"overview"` or `"detail"`)

4. **Color legend**
   - Rendered as part of the image (bottom or side panel)
   - Maps colors to gate type names

### Should Have (Phase 2: Detail + Polish)

5. **Detail mode rendering** (8-12px gates)
   - Gate label text inside boxes
   - Better for circuits under 30 qubits / 100 layers

6. **Auto zoom selection**
   - Automatically choose overview vs detail based on circuit size
   - Threshold: ~30 qubits or ~200 layers switches to overview

7. **Qubit labels** at left margin

### Nice to Have (Phase 3: Advanced)

8. **Circuit density heatmap** in overview mode
9. **Region-of-interest rendering** (render subset of qubits/layers at detail zoom)
10. **Jupyter `_repr_png_` integration** on circuit object

### Explicitly Deferred

- Interactive visualization (out of scope per PROJECT.md)
- SVG or LaTeX output (not pixel-art's strength)
- Animation or step-by-step rendering
- Folding/wrapping (contradicts the "see everything" value proposition)
- Custom color themes (hardcode a good default first)

## Comparison With Existing Tools

| Capability | Qiskit `mpl` | Cirq SVG | ASCII (current) | Pixel-Art (proposed) |
|------------|-------------|----------|-----------------|---------------------|
| Max practical qubits | ~40 | ~30 | ~20 (60 layers cap) | 200+ |
| Max practical gates | ~500 | ~200 | ~2000 (skips rendering) | 10,000+ |
| Output format | matplotlib Figure | SVG/HTML | stdout text | PIL Image (PNG) |
| Dependencies | matplotlib, LaTeX (optional) | None (built-in) | None (C printf) | Pillow, NumPy |
| Gate labeling | Full text + parameters | Text labels | 1-char symbols | Color + shape (overview), text (detail) |
| Customization | Extensive (style dict) | Limited | None | Color palette only |
| Rendering speed | Slow (>5s for large) | Fast | Fast | Fast (NumPy) |
| Jupyter integration | Yes (inline) | Yes (SVG) | No (text only) | Yes (PIL _repr_png_) |

## Complexity Assessment

| Feature | Effort | Risk | Priority |
|---------|--------|------|----------|
| **Circuit data extraction (Cython bridge)** | 2-3 days | Medium | P0 -- everything depends on this |
| **Overview renderer (NumPy + PIL)** | 3-4 days | Low | P0 -- core feature |
| **Gate icon design (2-3px)** | 1 day | Low | P0 -- simple pixel patterns |
| **Color palette + legend** | 1 day | Low | P0 -- essential for readability |
| **Python API (`ql.draw_circuit()`)** | 1 day | Low | P0 -- user-facing interface |
| **Detail renderer (8-12px)** | 2-3 days | Low | P1 -- nice to have |
| **Auto zoom selection** | 0.5 day | Low | P1 -- convenience |
| **Qubit labels** | 0.5 day | Low | P1 -- expected |
| **Density heatmap** | 2 days | Medium | P2 -- differentiator |
| **Region-of-interest rendering** | 2-3 days | Medium | P2 -- advanced |
| **Total MVP (P0)** | **8-10 days** | **Low-Medium** | -- |
| **Total with P1** | **11-14 days** | **Low** | -- |

**Risk factors:**
- Circuit data extraction is the main risk -- need to expose C struct fields through Cython without breaking existing API
- Very large images (200 qubits x 10,000 layers = 2M+ pixels) need memory management
- PIL rendering performance for large images -- mitigated by NumPy array approach

## Open Questions

1. **How should circuit data be exposed to Python for rendering?**
   - Option A: New Cython function returning list of dicts (cleanest API)
   - Option B: Expose `circuit_t` fields directly (fastest, most fragile)
   - Option C: Parse the existing OpenQASM export (wasteful but zero C changes)
   - Recommendation: Option A -- new `circuit_to_gate_list()` Cython function
   - Confidence: MEDIUM

2. **What is the gate-width threshold for switching zoom levels?**
   - Suggestion: overview when `qubit_count > 30 OR depth > 200`
   - Needs experimentation with real circuits
   - Confidence: LOW

3. **Should the image have a fixed width or scale with circuit depth?**
   - Recommendation: Scale with circuit depth (proportional), cap at reasonable maximum (e.g., 16000px width)
   - Very wide images are fine -- users can scroll/zoom in image viewers
   - Confidence: MEDIUM

4. **Should unused qubits be rendered?**
   - Recommendation: No -- follow existing `circuit_visualize` pattern which skips unused qubits
   - The C backend already tracks `used_occupation_indices_per_qubit`
   - Confidence: HIGH

## Sources

### High Confidence (Official Documentation)

- [Qiskit circuit_drawer API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.visualization.circuit_drawer) -- Parameters, output formats, style customization
- [Qiskit Visualize Circuits Guide](https://quantum.cloud.ibm.com/docs/en/guides/visualize-circuits) -- fold, scale, interactive, themes
- [Pillow PixelAccess Documentation](https://pillow.readthedocs.io/en/stable/reference/PixelAccess.html) -- Performance characteristics of pixel-level access
- [Pillow Image Module](https://pillow.readthedocs.io/en/stable/reference/Image.html) -- Image.fromarray(), save(), modes
- [Azure Quantum Circuit Diagram Conventions](https://learn.microsoft.com/en-us/azure/quantum/concepts-circuits) -- Standard visual conventions

### Medium Confidence (Research / Multiple Sources)

- [Quantivine: Large-scale Quantum Circuit Visualization (IEEE TVCG 2023)](https://arxiv.org/abs/2307.08969) -- Semantic abstraction for 100-qubit circuits
- [Cirq SVG Rendering (GitHub)](https://github.com/quantumlib/Cirq/issues/4499) -- SVG circuit drawing features and limitations
- [Qiskit Circuit Style Customization (Medium)](https://medium.com/qiskit/learn-how-to-customize-the-appearance-of-your-qiskit-circuits-with-accessibility-in-mind-b9b59fc039f3) -- Color, font, displaytext options
- [Pillow ImageDraw.point Performance Issue #2450](https://github.com/python-pillow/Pillow/issues/2450) -- Why NumPy is preferred over putpixel for bulk operations

### Low Confidence (Single Source)

- [Reso Pixel-Art Circuit Simulator](https://lynndotpy.dev/posts/reso-intro/) -- Pixel-art approach to boolean circuits (not quantum, but related aesthetic)
- [Pixel-Oriented Data Visualization (FasterCapital)](https://fastercapital.com/content/Visualization-Techniques--Pixel-oriented-Techniques--Pixel-perfect--The-Art-of-Pixel-oriented-Data-Visualization.html) -- General pixel-oriented visualization principles

---

**Research complete.** This feature landscape provides clear prioritization for the v1.9 pixel-art circuit visualization milestone. The core value proposition is scalability: rendering circuits that are too large for any existing tool. NumPy-based pixel rendering keeps it fast, and two zoom levels bridge the gap between "see the whole circuit" and "read individual gates."
