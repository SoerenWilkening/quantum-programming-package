# Phase 84: Security Hardening - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Guard unsafe C pointer operations and buffer accesses at the Cython boundary with validation that converts crashes into clear Python exceptions. Run static analysis on the C backend and fix all findings. This phase does NOT add new functionality — it hardens existing code paths.

</domain>

<decisions>
## Implementation Decisions

### Validation behavior
- C entry-point functions validate pointers and return error codes; Cython translates error codes into Python exceptions
- Only entry-point C functions (called from Cython) perform validation; internal C-to-C calls trust the pointer
- Validate NULL pointers only — no magic-number or dangling-pointer detection
- Performance constraint: validation must not measurably impact runtime

### Bounds checking strategy
- Scratch buffer limit is hardcoded at 384 slots (compile-time constant)
- Bounds checks happen at function entry (pre-check total slot requirement), not per individual write
- Only write operations are bounds-checked; reads are not guarded
- Performance is critical: pre-check-at-entry pattern chosen specifically to minimize overhead

### Error messaging
- Error messages include diagnostic details (function name, pointer context) — not just user-friendly text
- Strict template format across all validation points: `[Category] error in [function]: [detail]`
- Buffer overflow messages indicate the max was exceeded (e.g., "slot count exceeded, max 384") without including the requested count
- OverflowError for buffer overflow; ValueError for invalid pointer
- Exception only — no separate stderr logging from C side

### Static analysis scope
- Run both cppcheck AND clang-tidy on all C backend source files
- Fix findings at ALL severities (HIGH, MEDIUM, LOW) — not just HIGH
- False positives handled via central suppression file (suppressions.txt) with justification per entry
- Manual execution during this phase; no CI or pre-commit integration yet

### Claude's Discretion
- Error code convention (return codes vs global error state) — pick what fits existing codebase patterns
- Exact validation macro/function design
- clang-tidy check selection
- Suppression file location and format

</decisions>

<specifics>
## Specific Ideas

- Performance of bounds checks is a strong concern — the pre-check-at-entry pattern was chosen to avoid per-write overhead
- Error template: `[Category] error in [function]: [detail]` — consistent and parseable
- Success criteria explicitly requires: no performance regression beyond 15% on existing benchmarks

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 84-security-hardening*
*Context gathered: 2026-02-23*
