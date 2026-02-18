# Phase 11: Global State Removal - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove QPU_state global dependency from C backend, eliminating the last remnant of global state. This includes removing the R0-R3 registers and converting all functions that used them to take explicit parameters. Purely classical functions that only wrote to registers (no quantum gate generation) should be removed entirely.

</domain>

<decisions>
## Implementation Decisions

### Register replacement strategy
- All data that was in R0-R3 becomes explicit function parameters
- Functions that need qubit counts or classical values receive them as input parameters, not from global state
- Functions that only wrote classical results to registers without generating quantum gates should be removed entirely
- QPU_state struct should be completely deleted — no empty shell for future use

### Migration approach
- Incremental migration by file — one commit per file/module
- Claude determines optimal migration order based on dependency analysis
- Python bindings updated together with C changes in the same commit
- Compilation verification only between commits; full test suite at the end

### Backwards compatibility
- Clean break — no wrapper/shim functions for old call signatures
- Purely internal API — only Python layer calls C functions, no external consumers
- Python API can change if needed (v1.1 is a breaking version)
- No documentation of removed functions — git history is sufficient

### Error handling
- Compile-time errors for any remaining global state references (undefined symbol)
- No debug mode or search scripts — compiler errors ensure completeness
- Debug assertions for parameter validation (debug builds only)
- Use existing centralized qubit allocator for memory management — no change to ownership model

### Claude's Discretion
- Exact migration order for files/modules
- Whether any intermediate refactoring steps are needed
- Debug assertion placement and messages

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for global state removal.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-global-state-removal*
*Context gathered: 2026-01-27*
