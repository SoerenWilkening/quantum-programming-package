# Phase 58: Hardcoded Sequences (1-8 bit) - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Pre-computed addition sequences for 1-8 bit widths that eliminate runtime QFT generation. Covers plain addition and controlled addition. Subtraction derived from addition at runtime. Multiplication is out of scope (separate concern).

</domain>

<decisions>
## Implementation Decisions

### Sequence Format
- Hardcoded in C as static const arrays (not Python)
- Use existing gate_t struct format for consistency with runtime paths
- Store rotation angles as exact double values (M_PI/4, etc.)
- Static compile-time allocation (zero runtime allocation overhead)
- Qubit indices are canonical; mapping to actual qints happens at runtime

### Code Organization
- Split by width range: 1-4 bit in one file, 5-8 bit in another (~400 LOC each)
- New subdirectory: `Backend/src/sequences/`
- Single header `sequences.h` exposes dispatch function and constants
- Existing API preserved: `QQ_add(width)` routes to hardcoded when width ≤ 8, falls back to dynamic otherwise

### Dispatch Mechanism
- Dispatch table approach (single function with switch/table lookup by width)
- Both plain add and controlled add variants fully hardcoded (no runtime derivation)
- Subtraction computed from add sequence at runtime (reverse sequence)

### Generation Approach
- Manual creation by transcribing from dynamic generator output
- Document generation process in header comment for reproducibility
- No build-time generation; sequences committed to repo
- Future updates: manual re-transcribe if dynamic generator changes

### Validation Strategy
- Gate-by-gate comparison against dynamic generation
- One-time verification (not in regular CI)
- Width > 8 returns explicit error; caller must handle fallback to dynamic
- No runtime override flag; hardcoded is final when present

### Claude's Discretion
- Exact dispatch table implementation
- Gate sequence ordering within static arrays
- Header file structure and includes

</decisions>

<specifics>
## Specific Ideas

- "Unroll" the current functions with respective bits — hardcoded functions return pointer to pre-built sequence
- Keep same API (`QQ_add(width)`) so callers don't change
- Controlled variants are separate hardcoded arrays (not derived from plain at runtime)

</specifics>

<deferred>
## Deferred Ideas

- Hardcoded multiplication sequences — separate concern, not this phase
- Runtime override flag for debugging — decided against, keeps code simpler

</deferred>

---

*Phase: 58-hardcoded-sequences-1-8*
*Context gathered: 2026-02-05*
