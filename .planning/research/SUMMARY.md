# Project Research Summary

**Project:** Quantum Assembly v1.9 - Pixel-Art Circuit Visualization
**Domain:** Quantum circuit visualization (compact pixel-art rendering at scale)
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

This research addresses v1.9's goal of adding pixel-art circuit visualization to the Quantum Assembly framework. Current quantum visualization tools (Qiskit matplotlib, Cirq SVG) fail at scale — they become unreadable above 40 qubits and unusable above 60. The existing ASCII renderer in this project caps at 60 layers and skips rendering above 2000 gates. Pixel-art fills a genuine gap: rendering circuits with 100-200+ qubits and thousands of gates where each gate occupies only 2-3 pixels, allowing the entire circuit structure to remain visible.

The recommended approach is: add Pillow (PIL) as the sole new dependency, extract circuit data from C backend to Python via a new Cython function, render entirely in pure Python using NumPy array operations for performance. The architecture follows existing patterns (`circuit_to_qasm_string` for bulk data extraction, OpenQASM module for Cython pattern). Two zoom levels (overview at 2-3px per gate, detail at 8-12px per gate) with automatic selection based on circuit size provide both "see everything" and "read details" modes.

The critical risks are: (1) Pillow's per-call ImageDraw overhead at scale (mitigated by NumPy array-based rendering), (2) missing Python API to iterate circuit gates (mitigated by building Cython extraction layer first), and (3) choosing wrong zoom level for given circuit size (mitigated by auto-selection thresholds). With these addressed, pixel-art visualization delivers 10-100x performance vs Qiskit matplotlib while handling circuits 5x larger.

## Key Findings

### Recommended Stack

Pixel-art visualization requires exactly one new dependency: **Pillow 12.1.0**. The existing project has no image dependencies. Pillow provides everything needed for pixel-level rendering, text labeling, palette-mode PNG export, and nearest-neighbor upscaling. NumPy (already a dependency) accelerates bulk pixel operations when Pillow's per-pixel methods are too slow.

**Core technologies:**
- **Pillow >=12.1.0**: Image creation, pixel drawing, PNG export — Latest stable (Jan 2026), Python 3.10-3.14 support, MIT-CMU license, zero compiled sub-dependencies
- **NumPy (existing)**: Fast bulk pixel array construction via `Image.fromarray()` — 10-100x faster than per-pixel `putpixel()` calls for images with thousands of pixels
- **Cython (existing)**: C backend bridge for circuit data extraction — follows pattern from OpenQASM export

**What NOT to add:** matplotlib (50+ MB dependency tree, antialiases everything), cairo/pycairo (vector graphics, complex system deps), pygame/arcade (require display server), imageio/scikit-image (scientific processing, not creation), niche pixel-art libraries (supply chain risk).

**Rendering in Python, not C:** C backend has no standard image library (would need libpng/zlib build deps). Python/Pillow is fast enough for static image generation. Keep C focused on quantum operations.

### Expected Features

Pixel-art visualization targets a specific niche: ultra-compact rendering of large circuits. The core value proposition is scalability — showing circuit structure for 100-200+ qubits where every other tool fails.

**Must have (table stakes):**
- Horizontal qubit wires (universal convention, time flows left-to-right)
- Distinct gate symbols per type (color + shape at 2-3px scale)
- Control-target connections (vertical lines with dots for multi-qubit gates)
- Qubit labels (q0, q1, ... at left margin)
- Save to PNG (lossless, palette mode for small files)
- Return PIL Image object (Jupyter inline display, programmatic access)
- Color legend (essential — without it, 2-3px icons are meaningless)

**Should have (differentiators):**
- **Overview zoom level (2-3px gates)** — see ENTIRE circuit for 100+ qubits, no existing tool does this
- **Detail zoom level (8-12px gates)** — readable gate labels for small circuits
- **Scalability to 200+ qubits** — no open-source tool handles this
- **Auto zoom selection** — choose mode based on circuit size
- **Fast rendering (NumPy backend)** — 10,000+ gates in under 1 second
- **No matplotlib dependency** — lighter weight than Qiskit drawer

**Defer (v2+):**
- Interactive zoom/pan (requires GUI framework, massive scope)
- LaTeX rendering (requires LaTeX install, slow, fragile)
- SVG output (contradicts pixel-art paradigm)
- Animation (different product entirely)
- Circuit density heatmap (nice visual but not essential)
- Region-of-interest rendering (advanced feature)

### Architecture Approach

Pixel-art renderer integrates with the existing three-layer architecture (C backend -> Cython bindings -> Python frontend) by extracting circuit data to Python via a new Cython function, then rendering entirely in pure Python using Pillow. No C-level rendering is needed.

**Major components:**

1. **C Extraction Layer (circuit_output.c)** — New function `circuit_to_draw_data()` serializes entire circuit into flat struct (`draw_data_t`) with gate type, target, controls, angle arrays. Single iteration over `circuit_s.sequence` produces all data. Follows pattern from `circuit_to_qasm_string`.

2. **Cython Bridge (_core.pyx)** — New method `circuit.draw_data()` converts C struct to Python dict. Flat array-to-list conversion in single pass. Returns `{'num_layers', 'num_qubits', 'gates': [...]}` where each gate is `{'layer', 'target', 'type', 'angle', 'controls'}`.

3. **Python Renderer (draw.py)** — Pure Python module consuming dict from Cython. Uses NumPy array operations for bulk pixel placement (wires, gates). Layout engine maps logical (layer, qubit) to pixel (x, y). Sprite system composites gate icons. Outputs PIL Image with `Image.fromarray(numpy_array)`.

**Data flow:** `circuit_t` (C) -> `draw_data_t` (C struct) -> Python dict (Cython) -> NumPy array (Python) -> PIL Image (Python) -> PNG file.

**Why this architecture:**
- Single boundary crossing (bulk extraction) vs thousands of per-gate Cython calls
- Pure Python renderer allows easy visual iteration (no C recompile)
- NumPy array rendering avoids Pillow's per-call overhead (10-100x speedup)
- Pillow is headless-compatible (works in CI/server environments)

### Critical Pitfalls

1. **Pillow Decompression Bomb Limits** — Default 178M pixel limit raises error on large circuits. A 200-qubit x 2000-layer circuit can exceed this at wrong zoom. **Prevention:** Calculate dimensions BEFORE `Image.new()`, cap at 32000x32000, auto-switch to overview mode if exceeded. Set explicit `Image.MAX_IMAGE_PIXELS` limit.

2. **ImageDraw Per-Call Overhead** — Each `draw.rectangle()` call crosses Python-C boundary. 100,000 gates = 100,000+ calls = 5-30 seconds. Natural nested loop approach is clean but slow. **Prevention:** Use NumPy array slice assignment (`arr[y1:y2, x1:x2] = color`) for bulk operations. Reserve ImageDraw only for text labels. Target <100ms for 1000-layer circuit.

3. **No Python API to Iterate Gates** — Existing Cython bindings expose aggregates (`gate_count`, `depth`) but not per-gate data. `circuit_s.sequence[layer][gate]` only accessible from C. **Prevention:** First implementation task must be Cython `get_circuit_data()` function. Everything depends on this. Cannot render without structured gate access.

4. **Wrong Zoom Level Selection** — Detail mode on 200-qubit circuit = 50,000px wide image (impractical). Overview mode on 5-qubit circuit = 100x50px where everything is a dot (useless). **Prevention:** Auto-select: detail when `qubits <= 30 AND layers <= 200`, overview otherwise. Allow manual override. Cap maximum dimensions.

5. **NEAREST Resampling Required** — Pillow defaults to BICUBIC which blurs pixel art into gray smudges. **Prevention:** Always use `Image.Resampling.NEAREST` for any scaling. Use only integer scale factors (2x, 3x, 4x). For overview, render at target resolution directly rather than render-large-then-shrink.

## Implications for Roadmap

Based on research, suggested build order follows dependency chain: data access first (can't render without it), single-qubit gates second (simplest case), multi-qubit complexity third (vertical connections hardest), polish last (labels/themes don't affect correctness).

### Phase 1: Cython Data Extraction Bridge
**Rationale:** Prerequisite for everything else. The renderer cannot access circuit data without this. Must validate C-Python data flow before investing in visual work.
**Delivers:** Python API to extract circuit structure: `circuit.draw_data()` returns dict of layers/gates/qubits with all gate fields (type, target, controls, angle).
**Addresses:** Pitfall #3 (no gate iteration API), establishes architecture pattern.
**Avoids:** Bolt-on solutions (parsing ASCII output, OpenQASM parsing) which are fragile and slow.
**Confidence:** HIGH — follows established `circuit_to_qasm_string()` pattern from codebase.

### Phase 2: Core Renderer - Single-Qubit Gates
**Rationale:** Validate layout engine, NumPy rendering approach, and PIL integration with simplest case before adding multi-qubit complexity.
**Delivers:** Python module `draw.py` that renders circuits with X, Y, Z, H, P, Rx, Ry, Rz, M gates. Horizontal qubit wires, colored gate blocks (2-3px overview or 8-12px detail), PNG export.
**Uses:** Pillow (Image.new, Image.fromarray), NumPy (array slice assignment for bulk pixels).
**Implements:** Layout engine (layer_to_x, qubit_to_y coordinate mapping), sprite system (embedded 2D color arrays), dimension calculation with caps.
**Addresses:** Pitfall #1 (dimension limits), Pitfall #2 (NumPy bulk operations), Pitfall #8 (all 10 gate types mapped).
**Confidence:** HIGH — single-qubit gates have no vertical connections, simplest visual case.

### Phase 3: Multi-Qubit Gates - Controls & Connections
**Rationale:** Control connections are the hardest visual element (variable-length vertical lines, potential overlaps). Tackle after basic rendering is proven.
**Delivers:** CNOT, Toffoli, multi-controlled gates with vertical connection lines, control dots at control qubits, target symbols.
**Implements:** Vertical line rendering between control and target qubits, overlap detection for same-layer controlled gates.
**Addresses:** Pitfall #7 (overlapping control lines) by using sub-columns when ranges overlap.
**Confidence:** MEDIUM — complex visual interactions, needs careful testing with dense circuits.

### Phase 4: Auto Zoom & Polish
**Rationale:** Polish after core functionality works. Zoom selection and labels don't affect rendering correctness but significantly impact usability.
**Delivers:** Auto zoom selection (detail vs overview based on circuit size), qubit labels, layer numbers, scale parameter, truncation for very large circuits.
**Addresses:** Pitfall #4 (wrong zoom level) with threshold-based auto-selection.
**Confidence:** HIGH — straightforward enhancements after renderer exists.

### Phase Ordering Rationale

- **Phase 1 first because:** No rendering is possible without circuit data access. This validates the C-Python bridge design early.
- **Phase 2 before Phase 3 because:** Single-qubit gates exercise the full rendering pipeline (data extraction -> layout -> pixel rendering -> PNG export) without multi-qubit visual complexity. Gets NumPy bulk rendering working before vertical line logic.
- **Phase 3 before Phase 4 because:** Multi-qubit gates are a correctness requirement (can't skip them), while zoom/labels are usability enhancements.
- **Phase 4 last because:** Labels, themes, and auto-zoom can be added without changing the rendering core.

**Dependency chain:** Phase 1 (data access) -> Phase 2 (basic rendering) -> Phase 3 (multi-qubit) -> Phase 4 (polish). Each phase depends on the previous. No parallelization possible.

### Research Flags

**Needs deeper research during planning:**
- None — this is a well-scoped pixel rendering task with established tools (Pillow). All critical questions answered by this research.

**Standard patterns (skip research-phase):**
- **All phases** — Pillow documentation is excellent, NumPy array operations are standard, Cython data extraction follows existing OpenQASM pattern. No novel technical challenges beyond what's already documented in STACK.md, ARCHITECTURE.md, PITFALLS.md.

**Testing focus needed:**
- **Phase 2:** Dimension calculation and capping (test with circuits up to 200 qubits, 5000 layers)
- **Phase 2:** NumPy rendering performance (benchmark target: <100ms for 1000-layer circuit)
- **Phase 3:** Overlapping control lines detection (test with circuits where optimizer packed multi-qubit gates into same layer)
- **Phase 4:** Auto zoom threshold tuning (needs experimentation with real circuit sizes)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Pillow 12.1.0 verified from PyPI (Jan 2026), NumPy already in project, Cython pattern established |
| Features | MEDIUM-HIGH | Table stakes clear from quantum viz conventions, differentiators validated by Quantivine paper on large-circuit needs, anti-features based on PROJECT.md scope limits |
| Architecture | HIGH | C struct extraction follows `circuit_to_qasm_string()` pattern (lines verified in circuit_output.c), Cython dict conversion is standard, Pillow rendering is well-documented |
| Pitfalls | HIGH | All critical pitfalls verified from Pillow GitHub issues, codebase inspection shows no gate iteration API exists, dimension limits documented in Pillow reference |

**Overall confidence:** HIGH

### Gaps to Address

**Color palette accessibility:** The research proposes a specific color scheme (blue/red/green/yellow/purple for gate categories) but hasn't validated colorblind accessibility. **Handling:** Test with colorblindness simulator during Phase 2 icon design. Use shape AND color as redundant encodings at detail zoom.

**Zoom threshold values:** Research suggests `qubits <= 30 AND layers <= 200` for detail mode, but this needs empirical validation with real circuits. **Handling:** Make thresholds configurable parameters in Phase 4, tune based on user feedback and visual testing.

**Phase gate angle display:** Phase/rotation gates have continuous angle parameters that can't be shown as text at 2-3px scale. Research suggests accepting this limitation or using color intensity encoding. **Handling:** Defer to Phase 4 refinement. V1 shows Phase gates as distinct colored blocks without angle indication, document that users should use ASCII `visualize()` for angle details.

**Qubit index sparsity:** The C backend uses right-aligned layout in 64-element array, active qubit indices may be sparse (e.g., [0,1,2,64,65,66]). Renderer must compact to avoid 61 empty rows. **Handling:** Phase 2 layout engine must check `used_occupation_indices_per_qubit[qubit]` and create dense row mapping. Already documented in circuit.h lines 64-66.

## Sources

### Primary (HIGH confidence)
- [Pillow 12.1.0 on PyPI](https://pypi.org/project/pillow/) — version, compatibility, release date Jan 2, 2026
- [Pillow ImageDraw API Documentation](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) — drawing methods, per-call overhead notes
- [Pillow Image Module Documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html) — fromarray, resize, resampling filters, MAX_IMAGE_PIXELS
- [Pillow Limits Reference](https://pillow.readthedocs.io/en/stable/reference/limits.html) — decompression bomb limits (178M pixels default)
- [Pillow Image File Formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) — PNG save options, palette mode, compress_level
- **Codebase:** `circuit_output.c` lines 178-277 (`circuit_visualize()`) — iteration pattern for layers/gates
- **Codebase:** `types.h` line 64 (`Standardgate_t` enum: X, Y, Z, R, H, Rx, Ry, Rz, P, M)
- **Codebase:** `circuit.h` lines 54-79 (`circuit_s` struct with sequence[layer][gate])
- **Codebase:** `_core.pxd` lines 62-148 (Cython declarations, no per-gate Python API confirmed)
- **Codebase:** `openqasm.pyx` — pattern for dedicated Cython module calling C function

### Secondary (MEDIUM confidence)
- [Qiskit circuit_drawer API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.visualization.circuit_drawer) — existing tool comparison, fold/scale parameters
- [Quantivine: Large-Scale Quantum Circuit Visualization (IEEE TVCG 2023, arXiv:2307.08969)](https://arxiv.org/abs/2307.08969) — semantic abstraction for 100-qubit circuits, zoom level concepts
- [Pillow Performance Issues](https://python-pillow.github.io/pillow-perf/) — per-call overhead documentation
- [Pillow GitHub Issue #2450](https://github.com/python-pillow/Pillow/issues/2450) — putpixel performance, NumPy fromarray recommendation
- [Pillow GitHub Issue #5218](https://github.com/python-pillow/Pillow/issues/5218) — decompression bomb errors on generated images
- [Pillow GitHub Issue #5986](https://github.com/python-pillow/Pillow/issues/5986) — PNG save performance vs OpenCV
- [Azure Quantum Circuit Diagram Conventions](https://learn.microsoft.com/en-us/azure/quantum/concepts-circuits) — visual conventions for quantum gates

### Tertiary (LOW confidence)
- [Cirq SVG Rendering GitHub Discussion](https://github.com/quantumlib/Cirq/issues/4499) — SVG limitations at scale (needs validation)
- Pixel-art data visualization principles from FasterCapital blog — general guidance, not quantum-specific

---
*Research completed: 2026-02-03*
*Ready for roadmap: yes*
