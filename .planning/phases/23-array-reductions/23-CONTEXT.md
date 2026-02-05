# Phase 23: Array Reductions - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement reduction operations on qarray: AND/OR/XOR/sum that reduce arrays to single values. Reductions use pairwise tree structure (O(log n) depth) by default, with linear chain (O(n) depth) when qubit_saving mode is active. Axis-based reductions are out of scope — always flatten first. Element-wise operations belong in Phase 24.

</domain>

<decisions>
## Implementation Decisions

### Reduction syntax
- Methods on qarray: `arr.all()` (AND), `arr.any()` (OR), `arr.parity()` (XOR), `arr.sum()`
- Also expose module-level functions: `ql.all(arr)`, `ql.any(arr)`, `ql.parity(arr)`, `ql.sum(arr)`
- `sum(arr)` (Python built-in) also works via `arr.sum()` — both `sum(arr)` and `arr.sum()` supported

### Return types by input dtype
- qint arrays: `all()` returns qint (bitwise AND across elements), `any()` returns qint (bitwise OR), `parity()` returns qint (bitwise XOR), `sum()` returns qint
- qbool arrays: `all()` returns qbool (logical AND), `any()` returns qbool (logical OR), `parity()` returns qbool (logical XOR), `sum()` returns qint (popcount)

### Sum width behavior
- Default result width matches input element width (no auto-expansion)
- Optional `width=` parameter to override: `arr.sum(width=16)` for wider result
- qbool array sum (popcount): result width = ceil(log2(n+1)) — minimum bits for 0..n

### Tree structure and qubit_saving
- Default (qubit_saving OFF): pairwise tree reduction with O(log n) depth, fresh intermediate qubits at each level
- qubit_saving ON: linear chain reduction — accumulate sequentially element[0] op element[1] -> result, result op element[2] -> result, etc. — O(n) depth, minimal qubits
- Odd elements carry forward to next tree level (no identity padding)

### Multi-dimensional handling
- Always flatten before reduction (row-major order, matching iteration order from Phase 22)
- Axis parameter NOT supported this phase — deferred to future work
- Views (slices) can be reduced directly — reduce only the viewed elements

### Edge cases
- Empty array: raise ValueError ("cannot reduce empty array")
- Single-element array: return the element directly (no circuit operations)
- Fresh qubit allocation for results — original array unchanged, supports uncomputation

### Claude's Discretion
- Exact pairwise tree implementation details
- Intermediate qubit management within tree levels
- How built-in sum() hooks into arr.sum() (likely via __add__ and initial value)

</decisions>

<specifics>
## Specific Ideas

- Tree reduction follows established `qubit_saving` option: tree (log depth) when OFF, linear chain when ON
- This matches existing project patterns for circuit depth vs qubit tradeoff

</specifics>

<deferred>
## Deferred Ideas

- Axis-based reductions (arr.sum(axis=0)) — future phase
- min/max reductions — not in current scope

</deferred>

---

*Phase: 23-array-reductions*
*Context gathered: 2026-01-29*
