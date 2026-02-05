# Phase 53: Qubit-Saving Auto-Uncompute - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

When `ql.option("qubit_saving")` is active, compiled functions automatically uncompute all internal ancillas after the forward call completes, preserving only the return value's qubits. Ancilla qubits are deallocated and returned to the allocator for immediate reuse.

</domain>

<decisions>
## Implementation Decisions

### Trigger & timing
- Auto-uncompute is triggered only by global `ql.option("qubit_saving")` — no per-function decorator flag
- Claude's discretion on exact timing (immediately after return vs deferred)
- Skip auto-uncompute if function modifies input qubits (side effects on inputs)
- Completely silent — no warnings or logging when auto-uncompute fires

### Qubit preservation
- Only return value qubits survive auto-uncompute — all other internally-allocated qubits are uncomputed and deallocated
- If a qubit is part of the return value, it is excluded from the ancilla set — never uncomputed (even if allocated inside the function)
- Functions returning None: all ancillas are uncomputed (nothing to preserve)
- Deallocated qubits go back to allocator pool immediately for reuse

### Per-function control
- No per-function opt-out — if qubit-saving is on, all compiled functions auto-uncompute
- `f.inverse(x)` still works after auto-uncompute — undoes the effect on return qubits even after ancillas are gone
- `f.adjoint(x)` remains always available — independent of qubit-saving mode
- Qubit-saving setting is part of the compilation cache key — changing it triggers recompilation with new behavior

### Nested & edge cases
- Nested compiled calls: inner function's ancillas are auto-uncomputed when inner function returns (before outer continues)
- Functions with no ancillas: auto-uncompute is a silent no-op
- Entangled ancillas: uncompute anyway — the adjoint circuit should disentangle them
- Controlled contexts: auto-uncompute fires the same way inside controlled contexts (uncompute gates are also controlled)

### Claude's Discretion
- Exact timing of auto-uncompute relative to forward call return
- Detection mechanism for "function modifies input qubits" to skip auto-uncompute
- How f.inverse(x) replays only non-ancilla gates after ancillas are already gone

</decisions>

<specifics>
## Specific Ideas

- User wants f.inverse(x) to remain functional even after auto-uncompute has cleaned up ancillas — the inverse should undo the forward computation on the return qubits
- Qubit-saving mode change should invalidate compilation cache (recompile with new behavior)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 53-qubit-saving-auto-uncompute*
*Context gathered: 2026-02-04*
