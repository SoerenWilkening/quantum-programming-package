# Phase 59: Hardcoded Sequences (9-16 bit) - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend pre-computed addition gate sequences to cover widths 9-16 bit. Includes restructuring all sequence files to one-per-width, adding CQ_add/cCQ_add coverage for all widths 1-16, and creating a unified generation script. Subtraction variants are out of scope.

</domain>

<decisions>
## Implementation Decisions

### File splitting strategy
- One C source file per bit width: `add_seq_1.c` through `add_seq_16.c`
- Retroactively split existing 1-8 bit files (replace `add_seq_1_4.c` and `add_seq_5_8.c`)
- Naming convention: `add_seq_N.c` (e.g., `add_seq_9.c`, `add_seq_16.c`)

### Operation coverage
- All four addition variants for all widths 1-16: QQ_add, cQQ_add, CQ_add, cCQ_add
- Backfill CQ_add and cCQ_add for widths 1-8 (currently only QQ_add/cQQ_add)
- CQ_add/cCQ_add use parametric approach: hardcode gate structure, inject classical rotation angles at runtime (one sequence per width)

### Generation approach
- Single unified Python script that generates all 16 width files (`add_seq_1.c` through `add_seq_16.c`)
- Script calls the C backend's dynamic generation as reference (guaranteed to match)
- Old generation scripts (`generate_seq_5_8.py`, etc.) kept as reference but marked deprecated
- No Makefile target — standalone script only

### Fallback threshold
- `MAX_HARDCODED_WIDTH` compile-time constant in `sequences.h` (set to 16)
- Design allows extending beyond 16 in the future (door left open, not planned)
- Graceful fallback via preprocessor guards (`#ifdef SEQ_WIDTH_N`) — allows partial builds
- Unavailable widths conditionally excluded at compile time, caller falls back to dynamic generation

### Claude's Discretion
- Internal function naming within generated files
- Exact preprocessor guard naming convention
- How to structure the unified generation script internally
- Whether to use a template approach or direct string generation

</decisions>

<specifics>
## Specific Ideas

- The unified script should be the single source of truth for all hardcoded sequences
- CQ_add parametric approach: structure is fixed (QFT, controlled rotations, inverse QFT), only rotation angles vary with the classical value
- Preprocessor guards enable partial builds — useful during development and testing

</specifics>

<deferred>
## Deferred Ideas

- Hardcoded subtraction sequences (QQ_sub, cQQ_sub, etc.) — could be a future optimization phase
- Extending hardcoded sequences beyond 16-bit — leave door open but no current plans

</deferred>

---

*Phase: 59-hardcoded-sequences-9-16*
*Context gathered: 2026-02-06*
