# Phase 118: Nested With-Block Rewrite - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Rewrite `__enter__`/`__exit__` to compose control qubits via Toffoli AND at depth >= 2, fix controlled XOR (`~qbool`) inside `with` blocks, and verify correctness at arbitrary nesting depth. Phase 117's control stack infrastructure and AND-emission primitives are the foundation; this phase wires them into multi-level AND-ancilla composition.

</domain>

<decisions>
## Implementation Decisions

### Nesting depth
- Unlimited nesting depth — no cap, no warnings
- Linear chain composition: at depth N, AND(stack_top_control, new_qbool) -> new ancilla
- Each `__enter__` at depth >= 1 calls `_toffoli_and(_get_control_bool().qubits[63], self.qubits[63])` to produce AND-ancilla
- Push `(self, and_ancilla)` onto control stack; `_get_control_bool()` returns the AND-ancilla
- Each `__exit__` uncomputes AND-ancilla via `_uncompute_toffoli_and` before popping stack entry
- Use `_get_control_bool()` accessor to read current active control qubit (consistent with gate emission pattern)

### Controlled XOR fix
- Fix in gate emission layer, not in `__invert__` method
- `~qbool` and `~qint` inside nested `with` blocks controlled on the combined AND-ancilla (full multi-level control)
- `~qbool` returns a new qbool (consistent with current `__invert__` semantics on all qints)
- Fix applies to both 1-bit qbool and multi-bit qint — all bits go through same emit path

### Reuse and validation guards
- Allow `with cond: with cond:` (same qbool nested twice) silently — quantum-mechanically valid, no detection needed
- Do not detect `with a: with ~a:` contradictions — framework doesn't analyze semantic relationships
- Keep `_check_not_uncomputed()` validation at top of `__enter__` — prevents using garbage qubits as control
- Enforce qbool-only (width=1) for with-block conditions — raise TypeError for multi-bit qints

### Test coverage
- Remove all 6 xfail markers from existing 2-level tests in `test_nested_with_blocks.py` as part of implementation
- Add 3+ level tests in same file (`test_nested_with_blocks.py`):
  - 3-level all-true: verifies 3 AND-ancillas chain correctly
  - 3-level mixed conditions: various True/False combos at each depth
  - 3-level with arithmetic at each depth: operations at outer, middle, inner levels
  - 4+ level smoke test: single test verifying arbitrary depth
- Use 2-bit qints for 3+ level tests to stay safely under 17-qubit simulation limit
- All tests use direct Qiskit simulation via existing `_simulate_and_extract` pattern

### Claude's Discretion
- Exact error message for width != 1 TypeError in `__enter__`
- Whether to add a `TestThreeLevelNesting` class or inline into existing class
- Internal ordering of AND-ancilla uncomputation vs scope cleanup in `__exit__`
- Any additional edge case tests beyond the specified scenarios

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_toffoli_and(ctrl1_qubit, ctrl2_qubit)` in `_gates.pyx:232`: Allocates qbool AND-ancilla, emits CCX — ready to use in `__enter__`
- `_uncompute_toffoli_and(ancilla, ctrl1, ctrl2)` in `_gates.pyx:257`: Reverse CCX + deallocation — ready to use in `__exit__`
- `_get_control_bool()` in `_core.pyx:97-102`: Returns active control qubit from stack top — gate emission already uses this
- `_push_control(qbool_ref, and_ancilla)` in `_core.pyx:125`: Stack push — currently called with `None` for and_ancilla at depth 1
- `_pop_control()` in `_core.pyx:138`: Stack pop — currently used in `__exit__`
- `_simulate_and_extract()` in `test_nested_with_blocks.py:35`: Qiskit simulation helper — reuse for all new tests

### Established Patterns
- `__enter__` (qint.pyx:785): Currently pushes `(self, None)` — needs conditional AND composition when stack depth >= 1
- `__exit__` (qint.pyx:828): Currently just pops — needs AND-ancilla uncomputation before pop when entry has non-None ancilla
- Gate emission checks `_get_controlled()` then reads `_get_control_bool().qubits[63]` — no change needed; AND-ancilla automatically used as control when pushed
- Scope cleanup in `__exit__`: uncomputes scope-local qbools FIRST, then pops control — AND-ancilla uncomputation slots between these

### Integration Points
- `qint.pyx:785-826` (`__enter__`): Add AND composition logic when `len(_get_control_stack()) >= 1`
- `qint.pyx:828-872` (`__exit__`): Add AND-ancilla uncomputation when stack entry has non-None ancilla
- `_gates.pyx` or `qint_bitwise.pxi:534` (`__invert__`): Ensure controlled X emission works in controlled context
- `test_nested_with_blocks.py`: Remove xfail markers, add 3+ level test classes

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard quantum control composition following established codebase patterns and Phase 117's infrastructure design.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 118-nested-with-block-rewrite*
*Context gathered: 2026-03-09*
