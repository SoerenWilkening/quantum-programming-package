# Phase 19: Context Manager Integration - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend automatic uncomputation to work with quantum conditional blocks (`with` statements). When a `with` block exits, qbool intermediates created inside it are automatically uncomputed. Nested `with` statements uncompute in correct order (inner before outer). Uncomputation gates are generated inside the controlled context for quantum correctness.

</domain>

<decisions>
## Implementation Decisions

### Scope Boundary Behavior
- Always uncompute on block exit — no exceptions for escaped variables
- Early explicit `.uncompute()` inside block is allowed — block exit skips already-uncomputed values
- Automatic registration on creation — qbools created inside `with` automatically register with active scope
- Pre-existing qbools not touched — only qbools created inside the block are uncomputed on exit

### Nesting Semantics
- Strict LIFO order — inner scope must fully uncompute before outer scope starts, no interleaving
- Arbitrary nesting depth supported — use a stack to track scopes
- Trust Python scoping — no explicit scope-local marking needed

### Control Context Handling
- Uncompute gates generated inside the controlled context — quantum-correct behavior
- Scope-aware controlled tracking — scope stack integrates with `_controlled` state
- Condition qbool survives its own `with` block — not uncomputed by the block it controls
- Uncompute first, then restore context — uncompute while still controlled, then pop control context in `__exit__`

### Error/Exception Behavior
- Always uncompute on exception — cleanup happens in `__exit__` regardless of exceptions
- Raise error on uncomputation failure — fail loudly, don't hide bugs
- Always strict mode — no silent error suppression
- Invalid control context raises error immediately — fail fast on critical state issues

### Claude's Discretion
- Cross-scope dependency cascade behavior (inner creates qbool depending on outer)
- Exact scope stack data structure implementation
- Integration mechanism between scope stack and `_controlled` global

</decisions>

<specifics>
## Specific Ideas

- Uncompute timing: uncompute while still inside controlled context, THEN pop the control state
- This matches the quantum semantics: gates generated inside `with` are controlled, including uncomputation gates
- The condition qbool that controls the `with` block is NOT part of the block's scope — caller manages its lifetime

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-context-manager-integration*
*Context gathered: 2026-01-28*
