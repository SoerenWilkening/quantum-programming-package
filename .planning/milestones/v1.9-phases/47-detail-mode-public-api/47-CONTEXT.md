# Phase 47: Detail Mode & Public API - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Two-level zoom visualization (detail + overview) with automatic mode selection and a clean `ql.draw_circuit()` public API. Detail mode renders gates at 8-12px with readable labels for circuits up to ~30 qubits. Auto-zoom selects the appropriate mode. Users can override with explicit mode parameter.

</domain>

<decisions>
## Implementation Decisions

### Gate label rendering
- Show gate type only (e.g. "Rx", "H", "X") — no angle values in labels
- Measurement gates use scaled-up checkerboard icon (not "M" text) — visual distinction from unitary gates
- Control dots rendered as larger filled circles — no text labels needed
- Qubit wire lines do NOT continue after a measurement gate

### Font style
- Claude's discretion on pixel font vs TTF — pick what looks best at 8-12px

### Detail vs overview threshold
- Auto-zoom uses AND logic: overview mode only when circuit exceeds BOTH 30 qubits AND 200 layers
- Thresholds are hardcoded constants (not configurable parameters)
- When user explicitly requests detail mode on a large circuit: print a warning, then honor the request
- When auto-zoom selects a mode, print the selection (e.g. "Rendering in overview mode (52 qubits, 340 layers)")

### API surface
- `ql.draw_circuit(circuit)` as standalone function (not a circuit method)
- Importable from top-level `ql` namespace
- Accepts optional `save="filename.png"` parameter for convenience (still returns PIL Image)
- Accepts `mode="overview"` or `mode="detail"` for manual override; default is auto-zoom
- When Pillow not installed: raise ImportError with message "Pillow is required for circuit visualization. Install with: pip install Pillow"

### Visual style at detail zoom
- Same color palette as overview mode, just scaled up — consistent look between modes
- Qubit labels (q0, q1, q2, ...) shown on the left side of each wire in detail mode
- Gate boxes have thin 1px border for definition — gates stand out from wires

### Claude's Discretion
- Font choice (pixel bitmap vs system TTF) for gate labels
- Whether qubit labels also appear in overview mode or detail only
- Exact gate box sizing and spacing at detail scale
- Wire thickness at detail zoom
- Control line visual style at detail scale

</decisions>

<specifics>
## Specific Ideas

- Measurement checkerboard should scale up visually, not be replaced with text
- Wire lines stop after measurement — no continuation past measurement gates
- Warning + honor approach for forced detail mode on large circuits

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 47-detail-mode-public-api*
*Context gathered: 2026-02-03*
