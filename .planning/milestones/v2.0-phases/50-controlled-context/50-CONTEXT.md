# Phase 50: Controlled Context - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Compiled functions (`@ql.compile`) work correctly inside `with qbool:` blocks, producing controlled gate variants. The compilation cache stores both uncontrolled and controlled sequences. Nested `with` blocks are handled by the existing `with` block infrastructure (ANDing control bools), not by the compilation system.

</domain>

<decisions>
## Implementation Decisions

### Controlled variant derivation
- Do NOT re-capture the function body for controlled variants
- Derive the controlled sequence from the optimized uncontrolled sequence
- Transform each gate into its controlled variant, with gate decompositions where a gate has no direct controlled form
- If derivation fails for any gate, silently fall back to re-capture as a fallback
- No user-visible warning on fallback (silent operation)

### Cache key design
- Cache key includes: classical parameters + qint widths + control count (0 or 1)
- Uncontrolled (0 controls) and controlled (1 control) are separate cache entries
- Only single-control variant is pre-compiled — nested `with` blocks produce a single AND'd control qbool, so the compiled function always sees at most 1 control

### Eager compilation
- On first call, compile both uncontrolled and single-controlled variants immediately (back-to-back)
- Both variants are cached before the first call returns
- Controlled variant is derived from the optimized uncontrolled sequence (not a separate execution)

### Control qubit handling
- Controlled sequences store gates with a generic/placeholder control reference
- At replay time, the actual control qubit from the `with` block's qbool is substituted via remapping (same pattern as argument qubit remapping)

### Nested `with` blocks
- Nested `with` blocks AND the current control bool with the new one, producing a single control qbool
- From the compiled function's perspective, it is always controlled by at most one qbool
- No multi-control gate derivation needed in the compilation system — nesting complexity is handled by the `with` block infrastructure

### Claude's Discretion
- Gate decomposition strategy for gates without native controlled variants
- Internal data structures for storing controlled sequences in the cache
- Re-capture fallback implementation details

</decisions>

<specifics>
## Specific Ideas

- Use the optimized uncontrolled circuit as the basis for deriving the controlled variant, potentially requiring gate decompositions for certain gate types
- The existing `with` block AND mechanism means the compilation system stays simple — always single-control

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 50-controlled-context*
*Context gathered: 2026-02-04*
