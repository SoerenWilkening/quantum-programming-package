# Phase 49: Optimization & Uncomputation - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize captured gate sequences from @ql.compile functions and integrate compiled function outputs with the automatic uncomputation system. Does NOT include controlled context support (Phase 50), inverse generation, or debug printing (Phase 51).

</domain>

<decisions>
## Implementation Decisions

### Optimization scope
- Moderate optimization level: adjacent inverse cancellation, gate merging (consecutive rotations on same qubit), redundant SWAP elimination
- Allow gate decomposition/recomposition if it reduces count (e.g., decompose Toffoli and resynthesize)
- No special treatment for controlled gates — same generic optimization rules apply to all gate types
- QFT-specific optimization patterns: Claude's discretion based on research into whether QFT-aware rules are worth the complexity

### Optimization timing
- Optimize at capture time (immediately after first call captures gates)
- Cache stores the optimized version — all replays benefit
- Opt-out via `@ql.compile(optimize=False)` — default is optimized
- The `optimize` flag controls all cache entries consistently (re-captures for new widths follow the flag)

### Uncomputation integration
- Intermediate qubit handling tied to existing qubit-saving mode:
  - Qubit-saving active: uncompute intermediates inside the compiled function before returning
  - Qubit-saving off: leave intermediates for the caller (shorter circuits, more qubits)
- Compiled function output registers with uncomputation tracker as a single block (not gate-by-gate)
- Uncomputation inverts the optimized sequence (not the original) — reversed gate list with adjoint applied to each gate
- No dependency on Phase 51's `.inverse()` feature
- Cache stores only compute gates; uncomputation gates generated at replay time from the cached compute sequence
- Inverse sequence is NOT re-optimized — straightforward reversal of the optimized forward sequence
- Basic with-block uncomputation support in this phase (not deferred to Phase 50)

### User visibility
- Silent by default — no optimization output printed
- CompiledFunc exposes stats programmatically: `original_gates`, `optimized_gates`, `reduction_percent`
- If optimizer fails on a sequence: fall back silently to unoptimized sequence, no warning or error

</decisions>

<specifics>
## Specific Ideas

- Qubit-saving mode already exists in the codebase — optimization should respect that existing toggle rather than introducing a new one
- Gate count stats on CompiledFunc will serve as foundation for Phase 51's debug mode

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 49-optimization-uncomputation*
*Context gathered: 2026-02-04*
