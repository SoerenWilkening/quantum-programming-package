# Phase 65: Infrastructure Prerequisites - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix infrastructure bugs that would silently corrupt Toffoli circuits before algorithm work begins. Three fixes: `reverse_circuit_range()` negating GateValue for self-inverse gates, `allocator_alloc()` only reusing single qubits (not contiguous blocks), and missing ancilla lifecycle assertions. Existing QFT arithmetic must not regress.

</domain>

<decisions>
## Implementation Decisions

### Self-inverse gate detection
- Whitelist self-inverse gates explicitly: X, Y, Z, H, M
- Inline check (switch/case) directly in `reverse_circuit_range()` — no helper function
- For self-inverse gates, skip negation entirely (leave GateValue unchanged)
- All other gate types (P, Rx, Ry, Rz, R) continue to have GateValue negated as before

### Ancilla block allocator
- `allocator_alloc(count > 1)` must return guaranteed contiguous qubit indices
- `allocator_free()` updated to accept block free: `allocator_free(alloc, start, count)`
- When no contiguous block available in free-list, always allocate fresh qubits (no defragmentation)
- Internal data structure for free-list tracking: Claude's discretion

### Ancilla verification
- C structural assertion only (no Python-level state vector checks)
- Debug-only: compiled out in release builds (`#ifdef DEBUG`)
- On failure: `fprintf` diagnostic message identifying leaked ancilla qubit, then `assert(0)` to crash
- Check triggers at `allocator_destroy()` — all ancilla allocated with `is_ancilla=true` must have been freed by then

### Regression strategy
- Full test suite: `pytest tests/python/ -v` must pass with zero regressions
- New dedicated C-level unit test for `reverse_circuit_range()` with X/CCX gates — verify GateValue unchanged after reversal
- New C-level unit tests for allocator block alloc/free (various sizes, contiguity, reuse)
- New Python integration test for end-to-end ancilla block lifecycle
- All new C tests in `tests/c/` directory (alongside existing test_hot_path_*)

### Claude's Discretion
- Internal data structure for block free-list (sorted list, block pairs, or hybrid approach)
- Exact test case details and edge cases covered
- Any additional assertions or safety checks deemed necessary

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: changes must not break the QFT arithmetic path that has been stable since v2.3.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 65-infrastructure-prerequisites*
*Context gathered: 2026-02-14*
