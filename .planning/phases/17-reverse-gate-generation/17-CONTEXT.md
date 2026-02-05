# Phase 17: C Reverse Gate Generation - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate adjoint gate sequences for uncomputation. The existing `run_instruction` function already has an inverse boolean parameter. This phase ensures all gate types reverse correctly and provides the interface for Python to trigger reversal of specific instruction ranges.

</domain>

<decisions>
## Implementation Decisions

### API Surface
- Hybrid approach: Python stores instruction indices on qbool objects, calls C with those indices
- Each qbool is object-based — tracks its own instruction indices and reverses its own gates
- Adjoint gates append directly to the same circuit (in-place)
- Leverages existing `run_instruction` inverse parameter

### Gate Ordering
- Strict LIFO order — exact reverse of original gates, predictable and correct by construction
- Multi-controlled gates preserve control structure (CCX adjoint is CCX with same controls)
- Phase gates use explicit inverse types: T→Tdg, S→Sdg (not computed angles)

### Error Handling
- Unsupported gate type: hard error, raise exception immediately (fail fast)
- Invalid instruction range: assert in debug builds, undefined in release
- Empty instruction range (start == end): no-op, valid and silent

### Validation
- No ownership verification — Python layer responsible for correct indices
- No entanglement checks — user's responsibility to uncompute in correct order
- Debug logging available — optional verbose mode prints each reversed gate
- Parameter validation (angles, qubit indices): debug builds only

### Claude's Discretion
- Self-adjoint gate handling (X, H, CX, CCX) — explicit recognition vs generic lookup
- Where to track "already uncomputed" state (C vs Python)
- Internal data structures for instruction tracking

</decisions>

<specifics>
## Specific Ideas

- `run_instruction` already has inverse parameter — build on this existing infrastructure
- Keep C code simple — trust Python layer for correctness, verify only in debug
- Strict LIFO ensures mathematical correctness without complex dependency analysis

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-reverse-gate-generation*
*Context gathered: 2026-01-28*
