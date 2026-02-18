# Phase 8: Circuit Optimization - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add automatic circuit optimization, visualization, and statistics. Users can visualize circuits for debugging, query circuit metrics programmatically, and run optimization passes to reduce circuit size. This phase provides developer tooling — new quantum operations or algorithms belong in other phases.

</domain>

<decisions>
## Implementation Decisions

### Visualization format
- Horizontal orientation (time flows left-to-right, qubits are rows)
- Compact symbols for gates: single chars where possible (─H─, ─X─, ─●─)
- Vertical lines connect multi-qubit gates (● connected by | to ⊕)
- Full labels: qubit indices on left, layer numbers on top

### Statistics API
- Core metrics: gate count, circuit depth, qubit count, gate type breakdown
- Access via properties: `circuit.gate_count`, `circuit.depth`, etc.
- Gate type breakdown as dict: `circuit.gate_counts` → `{'H': 5, 'CNOT': 12, 'T': 3}`
- On-demand computation (no caching)

### Optimization behavior
- Off by default — user explicitly enables optimization
- Returns new circuit (original preserved for comparison)
- Essential passes only: gate merging (consecutive same-type) and inverse cancellation (X-X, H-H)
- Silent by default — no optimization summary unless user compares stats manually

### Pass control interface
- Named passes: `circuit.optimize(passes=['merge', 'cancel_inverse'])`
- `optimize()` with no arguments runs all passes
- Fixed pass order (optimal sequence determined by implementation)
- `circuit.available_passes` or module-level constant for discoverability

### Claude's Discretion
- Exact ASCII character choices for gate rendering
- Internal pass ordering logic
- How to handle edge cases in visualization (very wide circuits, gates with long names)

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches for quantum circuit visualization and optimization.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-circuit-optimization*
*Context gathered: 2026-01-26*
