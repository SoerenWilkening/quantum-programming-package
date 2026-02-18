# Phase 57: Cython Optimization - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize Cython hot paths for C-speed execution through static typing and compiler directives. Target: reduced yellow lines in `cython -a` output and 2-10x improvement in typed sections. This phase focuses on existing Cython code — new C migrations belong in Phase 60.

</domain>

<decisions>
## Implementation Decisions

### Prioritization Strategy
- Profile-driven only — only optimize functions that cProfile/benchmarks identify as hot
- Target top 5 hottest functions initially
- Continue optimizing while gains exceed 10% per function
- Strict one-by-one approach: optimize one function, verify, commit, then next
- Callee-first when hot functions call each other (inner functions first, gains compound)
- Re-profile after each optimization to check if rankings shifted

### Safety vs Speed Tradeoffs
- Conservative on boundscheck=False — only disable where loop bounds are provably safe
- More permissive on wraparound=False — disable in most hot paths since negative indexing is rare
- If optimization introduces bugs: debug and fix (preserve the gain, maintain correctness)
- Add CYTHON_DEBUG=1 build flag that re-enables all bounds checks for debugging

### Verification Approach
- Tests + benchmark required: existing tests must pass AND benchmark must show improvement
- If no improvement: investigate first before reverting — may reveal measurement issue
- Add annotation checks: tests verify `cython -a` shows no yellow lines in optimized functions
- Benchmark confidence: Claude determines appropriate statistical confidence per optimization

### Typing Depth
- Full cdef types on all parameters where possible (int, double, etc.)
- Arrays: case-by-case — memory views for numeric arrays, typed lists for object arrays
- Convert cpdef to cdef where functions are only called from Cython (eliminate Python dispatch)
- Explicit return type declarations on all optimized functions

### Claude's Discretion
- Python/Cython boundary priority — assess based on profiling data and boundary complexity
- Benchmark confidence thresholds — determine appropriate statistical significance per case
- Memory view vs typed list decisions — assess based on array contents and usage patterns

</decisions>

<specifics>
## Specific Ideas

- CYTHON_DEBUG=1 flag should toggle a build mode that re-enables all safety checks
- Annotation check tests should programmatically verify no yellow lines in optimized functions
- Re-profiling after each optimization is key — the hot path ranking will shift

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 57-cython-optimization*
*Context gathered: 2026-02-05*
