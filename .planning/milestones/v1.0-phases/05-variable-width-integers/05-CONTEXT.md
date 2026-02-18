# Phase 5: Variable-Width Integers - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable arbitrary bit-width quantum integers with dynamic allocation. QInt constructor accepts width parameter (8, 16, 32, 64 bits etc.), arithmetic operations validate width compatibility, and mixed-width operations work correctly. Addition and subtraction work for all variable-width integers.

</domain>

<decisions>
## Implementation Decisions

### Width Specification
- Both explicit parameter and default: `qint(5)` uses default, `qint(5, width=8)` overrides
- Default width is 8 bits (easier for testing, may increase later)
- Minimum width is 1 bit — `qint(0)` still uses 1 qubit
- Maximum width capped at 64 bits (reasonable practical limit)
- Width is read-only property after construction: `a.width` returns 8
- No resize methods — create new qint to change width: `qint(a.value, width=16)`

### Mixed-Width Arithmetic
- For k-bit + l-bit where k < l: use k+1 bit circuit with controls only on k lower bits
- Upper bits (index >= k) perform "perfect overflow" — no control, just targets
- Result width is larger of the two operands (l-bit)
- Subtraction uses inverse circuit (same width handling as addition)
- Comparisons (==, <, >) allowed with mixed widths — smaller conceptually extended

### Width Validation
- Value doesn't fit in width: raise warning, but don't fail program
- Arithmetic overflow: wrap silently (standard modular arithmetic)
- Invalid width parameter (negative, >64): raise ValueError exception
- Width accessible as read-only property after construction

### Memory/Qubit Strategy
- Width fixed at construction — qubits allocated once, no reallocation
- Width stored in both C struct and Python object
- Implicit circuit binding — uses current/global circuit, simpler API

### Claude's Discretion
- Allocation strategy (use existing allocator vs dedicated pool)
- Exact warning mechanism for value-doesn't-fit
- Internal C struct field names and layout
- Test case organization

</decisions>

<specifics>
## Specific Ideas

- "Adding 32-bit to 8-bit: use 8-bit circuit, as the bits with index >= 8 perform perfect overflow"
- The k+1 bit addition for k-bit + l-bit (k < l) differs from standard addition — controls only use k bits
- Subtraction performed by inverse circuit (see run_instruction pattern)
- Default 8 bits chosen for easier testing during development

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-variable-width-integers*
*Context gathered: 2026-01-26*
