# Phase 32: Bitwise Verification - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify all bitwise operations (AND, OR, XOR, NOT) produce correct results through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check), including mixed-width operand combinations and operand preservation. No shift operations exist in the language.

</domain>

<decisions>
## Implementation Decisions

### Width coverage strategy
- Exhaustive testing at bit widths 1-4 (all input pairs)
- Sampled testing at widths 5-6 only (representative pairs: boundary values, random pairs, powers of 2)
- No testing above width 6 -- bitwise ops are straightforward and unlikely to break at higher widths
- Mixed-width: test all adjacent pairs (w, w+1) for each width in range -- (1,2), (2,3), (3,4), (4,5), (5,6)
- Mixed-width result is the width of the wider operand (narrower operand zero-extended)

### Operator variant coverage
- Test all four ops: AND, OR, XOR, NOT
- Both QQ (quantum-quantum) and CQ (classical-quantum) variants for all binary ops
- NOT tested as unary standalone plus composed with each binary op (NOT-AND, NOT-OR, NOT-XOR)
- No shift operations to test -- only AND/OR/XOR/NOT exist
- Operand preservation verified for all binary ops (after a & b, check a and b still hold original values)
- Same exhaustive/sampled pairs used for CQ as QQ -- no extra boundary emphasis needed

### Result extraction approach
- Reuse Phase 31 calibration pattern: empirical position detection via known-answer calibration tests
- NOT operations are in-place (flip bits of input register, result read from same qubits)
- Verify ancilla qubits return to |0> after operations -- catches cleanup bugs early

### Failure handling policy
- All bitwise tests must pass -- strict failures, no xfail
- If memory issues appear at a width, reduce the maximum test width ceiling rather than skipping individual tests
- Target execution time: under 5 minutes for the full suite
- Bug fixes: Claude's discretion -- trivial fixes inline in Phase 32, complex bugs documented as BUG-BIT-XX and deferred

### Claude's Discretion
- Bug fix vs defer decision based on severity
- Exact calibration implementation details
- Sampling strategy for widths 5-6 (specific pairs chosen)
- Test file organization and naming

</decisions>

<specifics>
## Specific Ideas

- Consistent with Phase 31 approach: empirical calibration, same test infrastructure
- NOT composition tests (NOT-AND, NOT-OR, NOT-XOR) add coverage beyond basic unary NOT
- Ancilla verification catches cleanup bugs that Phase 33 (uncomputation) would otherwise surface late

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 32-bitwise-verification*
*Context gathered: 2026-02-01*
