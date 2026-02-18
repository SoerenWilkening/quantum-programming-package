# Phase 12: Comparison Function Refactoring - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor comparison functions (CQ_equal, cCQ_equal) to take classical values as explicit parameters instead of using global state. Remove CC_equal (purely classical, not needed). This is internal C API refactoring — no new user-facing functionality.

</domain>

<decisions>
## Implementation Decisions

### Function Signatures
- Keep same names (CQ_equal, cCQ_equal) with new parameter signatures
- CQ_equal(value, width) — takes classical value and bit width, returns standardized sequence
- cCQ_equal(value, width) — same signature as CQ_equal, control handled elsewhere
- No backward compatibility wrappers needed

### CC_equal Removal
- Delete CC_equal completely — purely classical, callers should use standard C comparison
- Search and fix all call sites before deletion
- Replace any Python binding calls with standard Python `==` comparison
- Only remove CC_equal in this phase (other classical functions addressed if found)

### Error Handling
- If value has bits set beyond width: return empty sequence (comparison can never be true)
- Assert/crash on width=0 or negative width (programming error)
- Assert if width > 64 (max supported)

### Testing Strategy
- Both new unit tests AND verify characterization tests still pass
- Explicit tests for edge cases (overflow detection, empty return)
- Python-level tests to verify bindings work with new signatures
- Representative width coverage: test 1, 8, 16, 32, 64 bits

### Claude's Discretion
- Exact sequence format returned by functions
- Internal implementation details
- Specific test file organization

</decisions>

<specifics>
## Specific Ideas

- Functions return "standardized sequences" — consistent format for downstream consumption
- Early return optimization: if value cannot fit in width, skip gate generation entirely

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-comparison-function-refactoring*
*Context gathered: 2026-01-27*
