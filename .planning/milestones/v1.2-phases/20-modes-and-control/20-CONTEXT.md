# Phase 20: Modes and Control - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Provide user control over uncomputation strategy (lazy vs eager mode) and explicit override methods (.keep(), .uncompute()). This phase adds the user-facing API for controlling automatic uncomputation behavior established in Phases 16-19.

</domain>

<decisions>
## Implementation Decisions

### Mode API Design
- Global option: `ql.option('qubit_saving', True)` affects all subsequent circuits
- Option name follows roadmap wording: `'qubit_saving'` (not `'eager_uncompute'`)
- Mode changes affect new qbools only — existing qbools keep their original mode
- Same function for get/set: `ql.option('qubit_saving')` returns current value when called without argument

### Keep Semantics
- `.keep()` is scope-based — prevents auto-uncompute within current Python scope only
- Scope means Python function or block where `.keep()` was called
- `.keep()` returns None (no chaining)
- Calling `.keep()` on already-uncomputed qbool prints warning (not error, not silent)

### Error Messages
- Minimal error messages: "Cannot uncompute: qbool still in use" style
- Use `ValueError` for uncomputation failures (standard Python, no custom exceptions)
- Using an uncomputed qbool raises error (strict enforcement)
- No `.is_uncomputed` property — users handle errors with try/except

### Explicit Uncompute Behavior
- `.uncompute()` errors immediately if qbool still referenced elsewhere
- Cascade: uncomputing A also uncomputes any intermediates A depends on
- `.uncompute()` returns None
- Calling `.uncompute()` on already-uncomputed qbool prints warning (idempotent-ish)

### Claude's Discretion
- Internal implementation of scope tracking for `.keep()`
- Exact wording of error/warning messages
- How to detect "still referenced elsewhere" (refcount threshold)

</decisions>

<specifics>
## Specific Ideas

- Mode API mirrors existing `ql.option()` pattern if one exists (consistency)
- Error handling should be strict — quantum programming mistakes are hard to debug

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-modes-and-control*
*Context gathered: 2026-01-28*
