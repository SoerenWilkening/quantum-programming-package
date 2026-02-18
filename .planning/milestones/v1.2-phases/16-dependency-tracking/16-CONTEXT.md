# Phase 16: Dependency Tracking Infrastructure - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Record parent→child dependencies when qbool operations create intermediate results. This infrastructure enables downstream phases (17-20) to know what to uncompute and in what order. This phase builds the tracking system; it does not perform uncomputation.

</domain>

<decisions>
## Implementation Decisions

### Dependency Representation
- Dependencies use weak references to parents (auto-clear when parent deleted)
- Each dependency edge stores: parent reference + operation type (AND, OR, XOR, comparison, etc.)
- Claude decides: storage location (attribute on qbool vs separate registry) and whether to add reverse tracking (parent→children)

### Tracking Triggers
- Multi-operand qbool operations create dependencies: `a & b`, `a | b`, `a ^ b` record operands as parents
- Single-operand operations (`~a`) do NOT create dependency records
- Arithmetic temporaries (e.g., overflow qubits) ARE tracked as dependencies
- Dependency creation is automatic — operations implicitly record parents, no user action needed

### Graph Structure
- Multiple parents allowed (e.g., `a & b` tracks both `a` and `b`)
- Shared ownership model — multiple children can share a parent
- Parent uncomputes when last child using it is done
- Cycles prevented by design: dependencies only flow from older to newer (creation order implies direction)
- Use Python garbage collection + weakref callbacks to detect when intermediates are no longer needed (no manual refcounting)

### Layer Awareness
- Layer info derived from gates at uncomputation time (not stored on dependency edges)
- Uncomputation follows reverse layer order (strict LIFO: later layers before earlier)
- Track which dependencies were created inside each `with` block as separate scopes
- Dependencies record their control context (which control qubits were active when created)

### Claude's Discretion
- Storage location: attribute on qbool instance vs centralized registry
- Whether to implement bidirectional tracking (parent→children) now for Phase 20 eager mode
- Exact data structure for scope tracking
- How to handle qint comparison dependency tracking (track qints vs ancillas)

</decisions>

<specifics>
## Specific Ideas

- Weakref pattern validated in research phase — use Python's weakref module with finalizer callbacks
- Creation order for cycle prevention aligns with existing circuit layer model
- Scope tracking prepares for Phase 19's `with` block integration

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-dependency-tracking*
*Context gathered: 2026-01-28*
