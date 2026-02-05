# Phase 18: Basic Uncomputation Integration - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatically uncompute intermediate qubits when the final qbool goes out of scope. Cascade through dependencies in reverse creation order (LIFO). This phase covers the core uncomputation mechanism — context manager integration (`with` blocks) and user control modes are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Scope trigger behavior
- Trigger via Python `__del__` when garbage collector destroys the qbool object
- Provide `.uncompute()` method for explicit early uncomputation
- If `.uncompute()` called while other references exist, raise exception immediately
- Silent by default — no debug output when implicit uncomputation occurs

### Cascade semantics
- Full cascade: uncomputing A also uncomputes its dependencies B and C (if not referenced elsewhere)
- Shared dependencies use reference counting — B uncomputes only when all consumers (A, D) are gone
- Strict LIFO based on creation order — B uncomputes before C if B was created first
- Trust the dependency graph from Phase 16 — no runtime integrity checks

### Failure handling
- `__del__` failures: print warning only (Python discourages exceptions in `__del__`)
- Explicit `.uncompute()` is idempotent — calling twice is a no-op, no error
- No `.is_uncomputed` property — keep API minimal, user tracks their own state
- Using qbool after uncomputation raises exception: "qbool has been uncomputed and cannot be used"

### Integration with allocator
- Immediate reuse — freed qubits go back to pool instantly
- Reverse gates only — trust adjoint returns to |0⟩, no explicit reset
- Single pool — all free qubits are equivalent, no tracking of recycled vs fresh
- No usage query API — allocation is internal implementation detail

### Claude's Discretion
- Exact warning message format for `__del__` failures
- Internal tracking mechanism for "already uncomputed" state
- Order of operations when multiple qbools die in same GC cycle

</decisions>

<specifics>
## Specific Ideas

- Uncomputation should be invisible in normal use — user writes natural code, qubits clean up automatically
- Reference counting on dependencies mirrors Python's own object model — familiar semantics

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-basic-uncomputation*
*Context gathered: 2026-01-28*
