# Phase 46: Core Renderer - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

NumPy-based pixel-art rendering of quantum circuits as PNG images. Produces overview-scale visualization showing all gates, wires, and control connections. Handles circuits with 200+ qubits and 10,000+ gates. Detail mode and public API are Phase 47.

</domain>

<decisions>
## Implementation Decisions

### Color scheme & visual style
- Dark/black background
- Gate colors grouped by category (Pauli gates share a color, rotation gates share another, etc.) — fewer colors, cleaner look
- Muted/pastel palette for gate colors on dark background
- Hadamard (H) gets its own distinct color — stands out from other single-qubit gates since it's the most common
- Measurement gates (M) are visually distinct from unitary gates — unique marker or pixel pattern

### Layout & spacing
- Ultra-compact: 1-2px per cell for maximum density at overview scale
- No gaps between layers — packed tight, wires flow continuously
- Natural image size — width = layers × cell size, height = qubits × cell size (can be very wide for large circuits)

### Gate icon design
- Gates rendered as 2×2 colored blocks
- All gates within a category are the same block shape — distinguished by color only, no shape variation
- Measurement gates get a visually distinct treatment (unique brightness or pixel pattern)
- CNOT target looks the same as standalone X gate — the vertical control line indicates it's controlled

### Control line rendering
- Control dots: single bright pixel at control qubit position
- Vertical control lines in a distinct bright color (not wire color) — makes multi-qubit connections stand out
- Full vertical span from topmost to bottommost involved qubit for MCX/multi-controlled gates
- Control dots + line + target gate block = complete multi-qubit gate visual

### Claude's Discretion
- Wire color (should contrast well with dark background and muted gate colors)
- Qubit labels on left margin (decide based on what makes sense at overview scale)
- Exact muted/pastel color palette selection per gate category
- Exact pixel pattern for measurement gate distinction
- Compression and format settings for PNG output

</decisions>

<specifics>
## Specific Ideas

- Dark background + muted pastels = similar aesthetic to dark-themed IDEs or terminal color schemes
- At 2×2 gate blocks with no layer gaps, a 10,000-gate circuit on 200 qubits would produce roughly a 20,000×400px image — manageable as a PNG
- Hadamard distinction helps users see superposition structure in circuit layout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-core-renderer*
*Context gathered: 2026-02-03*
