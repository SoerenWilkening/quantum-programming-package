# Phase 3: Memory Architecture - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Centralize qubit lifecycle management and establish clear ownership between circuit and quantum types. Create a qubit allocator module, track ownership for debugging, handle ancilla allocation, and eliminate memory leaks.

</domain>

<decisions>
## Implementation Decisions

### Allocator Interface
- Per-circuit allocator (each circuit_t owns its allocator)
- Minimal metadata: only qubit index tracked
- Allocate qubits in contiguous blocks, but only as many as needed (1 qubit for qbool, N for N-bit qint)
- Transparent API: expose allocator struct fields for direct access

### Ownership Model
- Borrow semantics: circuit owns qubits, qint/qbool hold references
- Debug-only ownership tracking: track which type uses each qubit in debug builds only
- Conditional qubit reuse: qubits can return to pool only if uncomputed back to |0⟩
- Track uncompute operations as heuristic for reuse eligibility

### Type Layer
- C operations (qint_add, etc.) take bit width and return standardized circuits
- add_gates receives qubit indices to apply gates to specific qubits
- qint/qbool are thin wrappers holding qubit indices
- Track operation history for debugging (Claude's discretion: debug-only compile flag)

### Ancilla Handling
- Ancillas allocated from main allocator (no separate pool)
- Automatic allocation: operations request ancillas internally
- Optional uncompute flag: caller can control whether operations auto-uncompute ancillas
- Track ancilla usage for circuit statistics (peak count, total allocations)

### Error Behavior
- Auto-expand on allocation failure (grow qubit capacity automatically)
- Hard-coded maximum qubit limit to prevent runaway allocation
- Always return error on double-free (strict detection)
- Python receives None/error on allocation failure (not exceptions)

### Claude's Discretion
- Exact hard-coded qubit limit value
- Operation history implementation (likely debug-only compile flag)
- Specific uncompute tracking heuristic
- How to expose circuit statistics to Python

</decisions>

<specifics>
## Specific Ideas

- "Enable reuse after freeing, only if qubits are in state 0 again" — conditional reuse based on uncompute tracking
- C generates gate sequences parametrized by width; qubit assignment happens separately via add_gates
- Operation history useful now for debugging, may remove later if overhead becomes concern

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-memory-architecture*
*Context gathered: 2026-01-26*
