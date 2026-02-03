# Requirements: Quantum Assembly v1.9

**Defined:** 2026-02-03
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.9 Requirements

Requirements for pixel-art circuit visualization milestone.

### Data Access

- [ ] **DATA-01**: Cython function extracts circuit gate data as Python dict (gate type, target, controls, angle, layer)
- [ ] **DATA-02**: Qubit index compaction — skip unused qubits, remap sparse indices to dense rows

### Rendering

- [ ] **REND-01**: Horizontal qubit wire lines rendered for each active qubit
- [ ] **REND-02**: Distinct 2-3px gate icons with color-coding for all 10 gate types (X, Y, Z, R, H, Rx, Ry, Rz, P, M)
- [ ] **REND-03**: Vertical control-target connection lines for multi-qubit gates (CNOT, CCX, MCX)
- [ ] **REND-04**: Control dots rendered at control qubit positions
- [ ] **REND-05**: NumPy array-based bulk rendering (not per-pixel ImageDraw)
- [ ] **REND-06**: Circuits up to 200+ qubits and 10,000+ gates render successfully

### Zoom

- [ ] **ZOOM-01**: Overview mode — 2-3px per gate, full circuit visible
- [ ] **ZOOM-02**: Detail mode — 8-12px per gate, readable gate labels
- [ ] **ZOOM-03**: Auto zoom selection based on circuit size (detail <= 30 qubits/200 layers, overview otherwise)
- [ ] **ZOOM-04**: User override via `mode` parameter ("overview" or "detail")

### Output

- [ ] **OUT-01**: `ql.draw_circuit()` Python API returning PIL Image
- [ ] **OUT-02**: Save to PNG via `.save()` method on returned Image
- [ ] **OUT-03**: Lazy Pillow import with helpful error if not installed

## Future Requirements

Deferred to later milestones.

### Visualization Enhancements

- **VIZ-F01**: Color legend showing gate type to color mapping
- **VIZ-F02**: Jupyter notebook inline display via `_repr_png_`
- **VIZ-F03**: Circuit density heatmap overlay in overview mode
- **VIZ-F04**: Region-of-interest rendering (subset of qubits/layers at detail zoom)
- **VIZ-F05**: Dark theme option
- **VIZ-F06**: Custom color palette support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Interactive zoom/pan GUI | Requires GUI framework, massive scope increase |
| LaTeX rendering | Qiskit already does this well |
| SVG output | Pixel art is inherently raster |
| Animated circuits | Different product entirely |
| matplotlib backend | Duplicates Qiskit functionality |
| Real-time visualization during circuit building | Performance/architecture complexity |
| Folding/wrapping (Qiskit-style) | Contradicts "see entire circuit" value |
| C-level rendering | Python/Pillow fast enough, simpler |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | TBD | Pending |
| DATA-02 | TBD | Pending |
| REND-01 | TBD | Pending |
| REND-02 | TBD | Pending |
| REND-03 | TBD | Pending |
| REND-04 | TBD | Pending |
| REND-05 | TBD | Pending |
| REND-06 | TBD | Pending |
| ZOOM-01 | TBD | Pending |
| ZOOM-02 | TBD | Pending |
| ZOOM-03 | TBD | Pending |
| ZOOM-04 | TBD | Pending |
| OUT-01 | TBD | Pending |
| OUT-02 | TBD | Pending |
| OUT-03 | TBD | Pending |

**Coverage:**
- v1.9 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15

---
*Requirements defined: 2026-02-03*
*Last updated: 2026-02-03 after initial definition*
