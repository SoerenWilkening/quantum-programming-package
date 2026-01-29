# Phase 22: Array Class Foundation - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Create ql.array with qint/qbool support and Python integration. Users can create and manipulate multi-dimensional quantum arrays with natural Python syntax — `ql.array([1, 2, 3])`, NumPy-style indexing, iteration. Mixed-type arrays raise clear errors.

</domain>

<decisions>
## Implementation Decisions

### Width Inference
- Use minimum required bits to fit largest value in array
- But never narrower than qint's default width (consistency with scalar type)
- When explicit width provided but value doesn't fit: warn then truncate (user sees issue, code proceeds)
- When creating from NumPy array: use NumPy's dtype to determine width (respects NumPy intent)

### Shape Behavior
- Auto-detect shape from nested lists (like NumPy) — `[[1,2],[3,4]]` → shape `(2,2)`
- Support unlimited dimensions (no artificial cap)
- Provide `reshape()` method that returns new array with same qubits
- Jagged lists (e.g., `[[1,2],[3]]`) raise ValueError immediately — strict, clear errors

### Element Assignment
- Arrays are **immutable** — no `arr[0] = value` assignment after creation
- No copy-with-modification methods — build new array from scratch if changes needed
- Indexing (`arr[0]`) returns the actual qint object (shared qubit reference)
- Slicing (`arr[1:3]`) returns a **view** (shares qubits with original) — memory efficient

### Printing/repr
- Compact format: `ql.array<qint:8, shape=(3,)>[1, 2, 3]` — type, width, shape, values
- Truncate large arrays (first/last few elements with `...`) — NumPy-style
- Nested brackets for multi-dimensional, not matrix-style newlines
- Shape and dtype always visible in repr — full info at a glance

### Claude's Discretion
- Exact truncation threshold for large arrays
- Internal storage implementation details
- Error message wording
- How views track their parent array

</decisions>

<specifics>
## Specific Ideas

- Compact repr format explicitly requested: `ql.array<qint:8, shape=(3,)>[1, 2, 3]`
- Immutable arrays with view-based slicing — functional style but memory efficient
- Width inference matches qint default as floor — don't create 1-bit arrays from `[0, 1, 0]`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-array-class-foundation*
*Context gathered: 2026-01-29*
