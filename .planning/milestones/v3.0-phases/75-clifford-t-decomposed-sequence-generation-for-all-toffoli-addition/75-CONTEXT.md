# Phase 75: Clifford+T Decomposed Sequence Generation for All Toffoli Addition - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate pre-computed Clifford+T hardcoded sequences for all Toffoli addition variants (CDKM and BK CLA), so that `toffoli_decompose=True` uses hardcoded lookup tables instead of dynamically decomposing CCX gates at runtime. Covers addition only -- multiplication/comparison remain on dynamic inline decomposition (Phase 74-04).

</domain>

<decisions>
## Implementation Decisions

### Variant coverage
- All 4 CDKM variants: QQ, CQ, cQQ, cCQ
- All 4 BK CLA variants: QQ, CQ, cQQ, cCQ
- CQ/cCQ increment-only (value=1) sequences also get Clifford+T variants
- Multiplication and comparison stay on dynamic inline decomposition for now (defer hardcoded mul/cmp sequences to a future phase if needed)

### Width range
- Widths 1-8 for all variants (CDKM and BK CLA alike)
- Matches existing hardcoded Toffoli sequence range

### Dispatch strategy
- Separate lookup tables/dispatch functions for Clifford+T sequences (e.g., `toffoli_decomp_clifft_QQ_add`)
- Same caching pattern as existing Toffoli sequences (first call: hardcoded -> cache, subsequent: cache hit)
- Widths 1-8 with `toffoli_decompose=True`: always use hardcoded Clifford+T sequence (no fallback to dynamic)
- Widths 9+: dynamic generators produce Clifford+T gates directly (skip CCX intermediate step)

### Generation approach
- Extend existing generation scripts with Clifford+T mode (e.g., `--clifford-t` flag)
- One C file per width per variant (e.g., `toffoli_clifft_qq_1.c`, `toffoli_clifft_cla_qq_1.c`)
- BK CLA: script implements BK prefix tree logic in Python and emits Clifford+T gates directly (manual construction, not simulation-based)
- Correctness verified via pytest tests only (not in generation script)

### Claude's Discretion
- Exact naming conventions for generated files and dispatch functions
- Internal organization of generation script extensions
- Whether to share CCX->Clifford+T expansion logic between scripts or duplicate
- CLA width-1 handling (falls back to RCA, so Clifford+T sequence may mirror CDKM)

</decisions>

<specifics>
## Specific Ideas

- User wants consistent hardcoded coverage across all Toffoli operation variants -- "use it for all CDKM and CLA variants"
- Dynamic multiplication Clifford+T decomposition is acceptable for now but could be hardcoded in a future phase "if not too costly"
- Each CCX expands to 15 gates (2H + 4T + 3Tdg + 6CX), so width-8 sequences will be ~300+ gates

</specifics>

<deferred>
## Deferred Ideas

- Hardcoded Clifford+T sequences for multiplication -- future phase if performance warrants it
- Hardcoded Clifford+T sequences for comparison (AND/OR/equal) -- future phase
- Extending hardcoded width range beyond 8 -- future phase

</deferred>

---

*Phase: 75-clifford-t-decomposed-sequence-generation-for-all-toffoli-addition*
*Context gathered: 2026-02-17*
