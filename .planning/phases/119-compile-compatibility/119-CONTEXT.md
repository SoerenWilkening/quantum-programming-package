# Phase 119: Compile Compatibility - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

`@ql.compile` captured functions work correctly inside nested `with` blocks. Compiled functions called within 2+ level nested `with` blocks emit all gates controlled on the combined AND-ancilla qubit. Covers forward calls, inverse, adjoint, and compiled-calling-compiled. Does NOT include compiled functions whose body contains nested with blocks (body captures in uncontrolled mode, so internal nesting is a separate concern).

</domain>

<decisions>
## Implementation Decisions

### Approach
- Tests first, fix if needed — the existing architecture (AND-ancilla as single combined control qubit via `_get_control_bool()`) suggests it should already work
- Controlled variant derivation adds ONE virtual control qubit, which maps to `_get_control_bool().qubits[63]` during replay — this IS the AND-ancilla in nested contexts
- Save/restore uses `list(_get_control_stack())` shallow copy — should preserve full stack

### Test verification
- Qiskit simulation for all tests (proves end-to-end correctness, matches Phase 118 pattern)
- Tests use `qbool(True/False)` for conditions (1 qubit per condition, keeps circuits under 17-qubit limit)
- Tests live in new file: `tests/python/test_compile_nested_with.py`

### Test coverage
- Thorough 2-level nested with tests for compiled functions
- One 3-level smoke test to confirm arbitrary depth
- Inverse (`f.inverse(x)`) and adjoint (`f.adjoint(x)`) inside nested with blocks
- Compiled function calling another compiled function inside 2-level nested with (one test)
- Single-level with + compile regression test (ensure no regression from any changes)

### Scope boundaries
- Only compiled functions CALLED inside nested with blocks — not functions whose body contains nested with
- First call inside nested with emits uncontrolled gates (accepted trade-off, documented behavior) — test documents this is expected
- Parametric compilation inside nested with: skip testing (shared control path, if normal works parametric should too)
- 15 pre-existing test_compile.py failures: out of scope, don't regress them further

### Claude's Discretion
- Exact test scenarios and expected values
- Whether any compile.py code changes are needed (may be tests-only if architecture already works)
- Internal test organization within the new test file

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_simulate_and_extract()` in `tests/python/test_nested_with_blocks.py:35`: Qiskit simulation helper — reuse for all new tests
- `_get_control_bool()` in `_core.pyx:97-102`: Returns AND-ancilla from stack top in nested context
- `_get_control_stack()` / `_set_control_stack()` in `_core.pyx`: Full stack save/restore used by compile.py
- `_derive_controlled_gates()` in `compile.py:313`: Adds one control qubit to every gate — virtual index maps to AND-ancilla during replay

### Established Patterns
- compile.py `_capture_and_cache_both()`: Saves stack, clears for uncontrolled capture, derives controlled variant, caches both
- `_replay()`: Maps `block.control_virtual_idx` to `_get_control_bool().qubits[63]` — automatically gets AND-ancilla in nested context
- Phase 118 tests use `qbool(True/False)` with 2-bit result registers to stay under 17-qubit limit
- test_compile.py: 186 tests, 171 passing, 15 pre-existing failures (qarray, replay gate count, auto-uncompute)

### Integration Points
- `compile.py:1214-1219`: Stack save/restore in `_capture_and_cache_both` — may need verification for multi-entry stacks
- `compile.py:1470-1473`: Control qubit mapping in `_replay` — reads `_get_control_bool()` which returns AND-ancilla
- `compile.py:1574-1584`: Adjoint controlled variant derivation — same `_derive_controlled_gates` path
- `compile.py:1918`: Inverse controlled variant path

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard compile infrastructure verification following existing patterns. The key hypothesis is that the Phase 117/118 AND-ancilla mechanism makes nested-with compile compatibility "just work" through the existing `_get_control_bool()` indirection.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 119-compile-compatibility*
*Context gathered: 2026-03-09*
