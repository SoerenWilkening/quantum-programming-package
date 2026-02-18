# Phase 71: Carry Look-Ahead Adder - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement O(log n) depth addition using carry look-ahead algorithms as an alternative to the CDKM ripple-carry adder (RCA). Two variants: Kogge-Stone (depth-optimized, default) and Brent-Kung (ancilla-optimized, qubit-saving mode). Dispatched automatically by width threshold within the existing Toffoli arithmetic backend. Covers all four addition variants (QQ, CQ, cQQ, cCQ) plus subtraction.

</domain>

<decisions>
## Implementation Decisions

### Prefix tree variant
- Implement **both** Kogge-Stone and Brent-Kung in Phase 71
- Kogge-Stone is the **default** (depth-optimized, ~n*log(n) ancilla)
- Brent-Kung activates when **qubit-saving option** is enabled (2n-2 ancilla, slightly more depth)
- Each variant is **inline/self-contained** (no shared generate/propagate abstraction)

### Dispatch strategy
- **Automatic width threshold**: below threshold use RCA, above use CLA — transparent to user
- Claude determines the exact threshold empirically during research (benchmark RCA vs CLA depth at various widths)
- Expose **override option** (e.g., `ql.option('cla', False)`) to force RCA regardless of width, useful for benchmarking
- **Toffoli mode only**: CLA does not get a QFT variant — QFT adders are considered legacy due to error correction overhead
- QFT mode stays as-is without CLA investment

### Operation coverage
- **All four variants**: QQ, CQ, cQQ, cCQ all get CLA implementations
- **Subtraction** via reversed gate sequence, same pattern as RCA
- **Mixed-width** supported via zero-extension of shorter operand
- **Composition into mul/div**: Claude's discretion whether CLA propagates into multiplication/division internal adder calls (safety and testing considerations)

### Ancilla constraints
- **No ancilla cap**: Kogge-Stone uses whatever it needs; Brent-Kung available for qubit-constrained scenarios
- **Silent fallback to RCA** when ancilla allocation can't satisfy CLA requirements — no warning, no error
- **Ancilla reuse** across consecutive additions (e.g., in multiplication loops) — allocate once, reuse for multiple operations in sequence

### Claude's Discretion
- Whether CLA propagates into multiplication/division or stays isolated to direct add/sub
- Whether a QFT CLA variant is practical (user leans no — QFT is legacy)
- Exact automatic width threshold value
- Internal code structure for controlled CLA variants (CCX/MCX patterns)

</decisions>

<specifics>
## Specific Ideas

- "QFT adders might be far worse in the long run, when incorporating error correction. So these might be used as little as possible" — reinforces Toffoli-first strategy
- Qubit-saving option already exists in the codebase — reuse it for Brent-Kung vs Kogge-Stone dispatch
- Draper et al. (2004) is the reference paper for the CLA algorithm

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 71-carry-look-ahead-adder*
*Context gathered: 2026-02-15*
