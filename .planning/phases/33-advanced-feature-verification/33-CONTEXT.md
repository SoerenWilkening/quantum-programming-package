# Phase 33: Advanced Feature Verification - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify that advanced language features — automatic uncomputation, quantum conditionals (`with qbool:`), and array operations (`ql.array`) — produce correct results through the full pipeline (Python → C circuit → OpenQASM 3.0 → Qiskit simulate → result check). This is a verification phase, not feature-building.

</domain>

<decisions>
## Implementation Decisions

### Uncomputation scope
- Test with arithmetic (add, subtract, multiply) and comparison operations — skip bitwise
- Bit widths: 2-3 bits only (uncomputation circuits grow fast)
- Verification method: measure ALL qubits in circuit, check non-result qubits are |0⟩
- Must also verify the computation result is still correct (not just ancilla cleanup)
- Include compound boolean expressions with 2-3 sub-expressions (e.g., `(a == 2) & (b < 3)`, `(a > 1) | (b == 0)`)

### Conditional behavior
- Test simple gating only — single condition controlling a single operation block
- No nested or chained conditionals
- Gate arithmetic operations inside conditionals (e.g., `with (a > 2): b += 1`)
- Verify BOTH branches: condition=true (operation happens) AND condition=false (operation skipped)
- Condition sources: comparison operator results (e.g., `a > 2`, `a == b`, `a <= 3`)

### Array operations
- Verify reductions (sum, AND-reduce, OR-reduce) AND element-wise operations (array + scalar, array + array)
- Array sizes: 2-3 elements, plus single-element edge case
- Element bit widths: 2-3 bits per element
- Include edge cases: single-element arrays (reductions should return that element)

### Known bug interaction
- Test EVERYTHING, xfail tests that hit known bugs
- All xfail markers: non-strict with `reason="BUG-XX"` (consistent with phases 31-32)
- Multi-bug cases: single xfail marker listing all relevant bugs in reason string
- Produce a feature status summary table at phase end: feature | status | blocking bugs

### Claude's Discretion
- Exact test parameterization strategy (exhaustive vs representative for each operation)
- Which specific comparison operators to use in conditional tests
- How to structure the feature status summary table
- Circuit size management and simulation timeout handling

</decisions>

<specifics>
## Specific Ideas

- Compound boolean expressions like `(a == 2) & (b < 3) | (a > 2)` should be tested with uncomputation — these stress-test the uncomputation engine since each sub-expression generates ancillae
- Feature status table should be useful for future milestone planning (what works, what's blocked, by which bugs)
- Keep circuit sizes manageable — user explicitly chose smaller widths/sizes across all areas

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-advanced-feature-verification*
*Context gathered: 2026-02-01*
