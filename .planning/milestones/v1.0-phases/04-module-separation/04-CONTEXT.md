# Phase 4: Module Separation - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Split QPU.c god object into focused modules with clear responsibilities. This includes eliminating the remaining global state (instruction_list, QPU_state). The result is 5-7 focused modules with well-defined interfaces and minimal coupling.

</domain>

<decisions>
## Implementation Decisions

### Module boundaries
- Primary split by data structure, with responsibility-based splits within that to keep files small
- Separate gate module (gate.c for gate creation/manipulation, circuit.c imports and uses gate types)
- Address instruction_list and QPU_state globals in this phase (not deferred)
- Target 5-7 modules total (medium granularity, ~200-400 lines each)

### Header organization
- Per-module public headers (circuit.h, gate.h, etc. — users include what they need)
- Full struct definitions exposed in public headers (not opaque types)
- Separate include/ directory for headers (include/circuit.h, src/circuit.c — standard C library layout)

### Dependency rules
- Minimal coupling preferred, no strict layering — allow pragmatic exceptions if needed
- Common types header (types.h with all shared structs — everyone includes it)
- Dependencies documented in each header file (comment at top listing dependencies)

### Naming conventions
- Module files: snake_case.c (circuit_builder.c, gate_ops.c)
- Functions: module_action pattern (circuit_create(), gate_add_x(), optimizer_run())
- Types: module_type_t pattern (circuit_t, gate_t, sequence_t — lowercase with _t suffix)
- Constants/macros: MODULE_CONSTANT pattern (CIRCUIT_MAX_QUBITS, GATE_TYPE_X — uppercase with module prefix)

### Claude's Discretion
- Internal header organization per module (whether to use _internal.h suffix or keep static in .c)
- Whether qubit_allocator is a foundation layer or peer module (based on actual usage patterns)
- Exact function groupings within the 5-7 module target

</decisions>

<specifics>
## Specific Ideas

- Keep file sizes manageable — the point is to break up the god object
- Standard C library layout (include/ and src/ separation) for professional appearance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-module-separation*
*Context gathered: 2026-01-26*
