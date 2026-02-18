# Phase 54: qarray Support in @ql.compile - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable `ql.qarray` objects to be passed as arguments to `@ql.compile`-decorated functions with correct capture, caching, and replay. Functions can also return qarrays. Supports iteration, index access, and slicing within compiled functions.

</domain>

<decisions>
## Implementation Decisions

### Cache key semantics
- Cache key based on shape only (array length), not element widths
- Strict remapping: qubit-by-qubit. Error if element widths don't match between calls (user ensures consistency)
- For mixed arguments (qarray + qint), cache key = total qubit count across all args (flattened)
- Empty qarrays (length 0) raise error — not supported as input

### Multi-qarray arguments
- Support any number of qarray arguments per function
- Any argument order allowed — mixed qarray and qint args work in any position
- No restriction on element widths across multiple qarray args (each tracked independently)
- Full support for returning qarray from compiled functions (works with inverse/adjoint tracking)

### Error behavior
- Detailed error messages for shape mismatches: "Expected qarray of length X, got length Y"
- In-place modification of qarray elements is allowed — caller sees changes
- Runtime error if qarray contains deallocated qubits (stale reference detection)
- Strict type checking: passing Python list instead of ql.qarray raises type error

### Iteration support
- For-loop iteration over qarray is supported — loop unrolled during capture
- Classical index access only (arr[i] where i is Python int)
- Slice access (arr[start:end]) is supported
- Modification during iteration is allowed

### Claude's Discretion
- Internal data structures for tracking qarray qubit mappings
- Exact error message wording
- Cache eviction strategy if needed
- Implementation of loop unrolling during capture

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches consistent with existing compile infrastructure.

</specifics>

<deferred>
## Deferred Ideas

- **Quantum indexing**: arr[qi] where qi is a qint creates controlled access across superposition — future phase
- **Quantum loop boundaries**: Loops with quantum-valued start/end bounds — future phase

</deferred>

---

*Phase: 54-qarray-compile-support*
*Context gathered: 2026-02-05*
