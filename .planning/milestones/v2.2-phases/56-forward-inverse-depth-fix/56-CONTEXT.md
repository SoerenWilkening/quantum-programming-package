# Phase 56: Forward/Inverse Depth Fix - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the depth discrepancy between forward compilation (`f(x)`) and inverse compilation (`f.inverse(x)`). Both paths should produce circuits of equal depth for equivalent operations. The fix approach is driven by profiling data from Phase 55.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

This is a pure bug fix with clear success criteria. All implementation decisions delegated to Claude:

- **Diagnostic approach** — Use profiling data from Phase 55 to identify where forward/inverse paths diverge
- **Fix strategy** — Determine optimal fix based on root cause analysis (bring forward up to inverse quality, or restructure both)
- **Test coverage** — Add appropriate depth comparison tests to prevent regression
- **Technical approach** — Architecture and implementation details based on what profiling reveals

</decisions>

<specifics>
## Specific Ideas

No specific requirements — approach driven by profiling results.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 56-forward-inverse-depth-fix*
*Context gathered: 2026-02-05*
