# Phase 51: Differentiators & Polish - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Compiled functions (`@ql.compile`) gain inverse generation, debug introspection, nested compilation support, and comprehensive test coverage. Core capture-replay, optimization, and controlled context are already implemented (Phases 48-50).

</domain>

<decisions>
## Implementation Decisions

### Inverse API design
- Both `.inverse()` method and `@ql.compile(inverse=True)` decorator parameter supported
- `.inverse()` is lazy (generates on first call); decorator param enables eager generation
- Claude's discretion on whether `.inverse()` returns a new callable or uses another pattern — pick what fits existing codebase
- Standard adjoint transformation: reverse gate order + adjoint each gate; raise error on non-reversible operations
- Inverse composes with controlled context — `with qbool: fn.inverse()(q)` produces controlled adjoint gates
- Inverse composes with nesting — inner `.inverse()` inside outer produces inlined adjoint gates

### Debug output format
- Debug info prints to stderr (not stdout, not logging)
- Claude's discretion on exact information shown per call (essentials like cache hit/miss, gate counts, plus whatever is useful for quantum debugging)
- `.stats` property exposed for programmatic access alongside stderr printing
- `.stats` is only populated when `debug=True` — returns None otherwise (no overhead when not debugging)

### Nesting behavior
- Inner compiled function gates are inlined into outer function's captured sequence (flat gate list)
- Depth limit for recursive/circular compiled function calls — error when exceeded (Claude picks reasonable default)
- Optimizer runs on the full flattened gate list — can optimize across inner/outer function boundaries
- Full composition: nesting, inverse, and controlled all compose freely

### Claude's Discretion
- Whether `.inverse()` returns a new callable vs other pattern
- Debug output detail level and formatting
- Recursion depth limit value
- Additional edge cases for test suite beyond specified ones
- Adjoint gate mapping specifics

</decisions>

<specifics>
## Specific Ideas

- Inverse of inverse (`fn.inverse().inverse()`) should equal the original — round-trip correctness is a requirement
- Empty compiled functions (no gates / identity) should be handled gracefully by inverse and debug
- Gate-level assertions for optimization/inverse tests, behavior-level assertions for nesting and integration tests

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 51-differentiators-polish*
*Context gathered: 2026-02-04*
