# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** Phase 6 COMPLETE - Ready for Phase 7

## Current Position

Phase: 7 of 10 (Extended Arithmetic) - IN PROGRESS
Plan: 1 of 5 in current phase - COMPLETE
Status: In progress
Last activity: 2026-01-26 - Completed 07-02-PLAN.md: Comparison operators

Progress: [███████░░░] 71%

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 5.4 min
- Total execution time: 2.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 - Testing Foundation | 3 | 18 min | 6 min |
| 02 - C Layer Cleanup | 3 | 18 min | 6 min |
| 03 - Memory Architecture | 3 | 22 min | 7.3 min |
| 04 - Module Separation | 4 | 15 min | 3.8 min |
| 05 - Variable-Width Integers | 4 | 28 min | 7 min |
| 06 - Bitwise Operations | 4 | 23 min | 5.75 min |
| 07 - Extended Arithmetic | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 06-02 (6 min), 06-03 (7 min), 06-04 (7 min), 07-02 (3 min)
- Trend: Fast execution for stub implementations and Python operators

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Bottom-up restructuring (C first): Foundation must be solid before adding features
- Open source release target: Requires clean code, docs, tests
- Keep circuit compilation model: Direct execution is future work
- Use Ruff instead of Black + isort + Flake8: Single tool, 10-100x faster (01-01)
- Use LLVM style for clang-format: Standard, readable, 100-column limit (01-01)
- Pre-commit hooks auto-fix formatting: Reduce manual work, ensure consistency (01-01)
- Characterization tests capture current behavior as-is: Purpose is regression detection, not correctness validation (01-02)
- Tests organized by functional area: qint operations, qbool operations, circuit generation (01-02)
- Auto-detect compiler in Makefile: Search for gcc/clang/cc rather than hardcoding (01-03)
- Use calloc for sequence_t array allocations: Ensures zero-initialization and prevents undefined behavior (02-01)
- Standard sequence_t initialization pattern: Allocate gates_per_layer and seq arrays immediately after malloc(sizeof(sequence_t)) (02-01)
- Cleanup-on-error pattern for complex allocations: Free in reverse order on any allocation failure (02-02)
- Temp pointer pattern for realloc: Preserves original pointer on failure (02-02)
- Return NULL from all allocation functions: Enables error propagation to callers (02-02)
- Explicit context passing via circuit_t* parameter: No global circuit variable (02-03)
- OWNERSHIP comments document memory responsibilities: Added at every allocation point (02-03)
- Keep instruction_list and QPU_state as globals for now: Stateless sequence generation, will address in Phase 4 (02-03)
- Hard-coded ALLOCATOR_MAX_QUBITS limit (8192): Prevents runaway allocation bugs (03-01)
- Freed stack only reuses single-qubit allocations initially: Simplified implementation, multi-qubit reuse can be added later (03-01)
- DEBUG_OWNERSHIP conditional compilation: Zero runtime overhead in production, enables ownership tracking for debugging (03-01)
- circuit_get_allocator() accessor for Python bindings: Follows C API pattern for opaque structs (03-01)
- QINT/QBOOL use allocator_alloc() with is_ancilla=true flag: Enables ancilla tracking, matches semantic meaning (03-02)
- free_element determines width from MSB: Enables correct allocator_free(start, width) for both QINT and QBOOL (03-02)
- Backward compat tracking maintained with documented quirk: Original decrement-by-1 behavior preserved during migration (03-02)
- Cast circuit_t* to circuit_s* in Cython calls: Matches C function signatures with forward-declared structs (03-03)
- Add qubit_allocator.c to setup.py sources: Required for linking circuit_get_allocator symbol (03-03)
- Cython cdef declarations at function start: Language requirement, before any Python statements (03-03)
- types.h as foundation module: Single source of truth for shared types (qubit_t, gate_t, sequence_t) with zero dependencies (04-01)
- definition.h as backward compatibility wrapper: Enables gradual migration from old code (04-01)
- Dependency comments in headers: Makes include hierarchy explicit and maintainable (04-01)
- optimizer.c module extraction: Gate optimization logic separated from QPU.c, reducing god object from 201 to 18 lines (04-02)
- Instruction state scope clarified: Globals kept only for sequence generation (CQ_add, CC_mul), not gate optimization (04-02)
- circuit_t typedef uses named struct: struct circuit_s pattern for forward declaration compatibility (04-02)
- circuit.h as main API header: Consolidates types, gates, optimizer, output, allocator into single user-facing include (04-03)
- circuit_output.h/c module: Separated print_circuit and circuit_to_opanqasm into dedicated module (04-03)
- QPU.h as backward compat wrapper: Now includes circuit.h, preserves instruction_t for sequence generation (04-03)
- Fixed filename typo: ciruict_outputs.c -> circuit_output.c for consistency and professionalism (04-03)
- module_deps.md as comprehensive dependency documentation: Includes ASCII graph, line counts, responsibilities, and historical context (04-04)
- No .pxd changes needed for Cython: QPU.h backward compatibility wrapper sufficient for module separation (04-04)
- Verification includes full test suite: 59 tests confirm module separation doesn't break functionality (04-04)
- Right-aligned q_address array layout: indices [64-width] through [63] stores qubits for variable-width integers (05-01)
- Width stored as unsigned char: Supports 1-64 bit widths efficiently (05-01)
- QBOOL as QINT(circ, 1) wrapper: Single allocation code path, reduced complexity (05-01)
- MSB field kept for backward compat: Now points to first used element (64-width) (05-01)
- QINT_DEFAULT macro: Backward compatibility for C code calling QINT(circ) (05-01)
- QQ_add(int bits) signature: Width-parameterized addition replaces fixed INTEGERSIZE (05-02)
- cQQ_add(int bits) signature: Width-parameterized controlled addition (05-02)
- precompiled_XX_add_width[65] caches: Index 0 unused, 1-64 valid for width-specific caching (05-02)
- Legacy globals auto-populated: precompiled_QQ_add set when bits == INTEGERSIZE (05-02)
- width parameter primary with bits alias: Clean API, backward compat maintained (05-03)
- Default width 8 bits: Matches INTEGERSIZE constant (05-03)
- UserWarning for overflow, not error: Per CONTEXT.md, modular arithmetic expected (05-03)
- qbool unsigned 1-bit [0,1]: True=1 should not warn (05-03)
- Extract used qubits from right-aligned: C backend expects compact arrays (05-03)
- Variable-width tests organized by requirement: VINT-01 through VINT-04, ARTH-01, ARTH-02 (05-04)
- TestPhase5SuccessCriteria for explicit verification: Maps directly to ROADMAP.md success criteria (05-04)
- Fixed CQ_add/cCQ_add offset for variable-width: Changed from INTEGERSIZE-bits to 0 (05-04)
- Fixed QFT/QFT_inverse offset for variable-width: Same fix pattern (05-04)
- CQ_add/cCQ_add/CQ_mul/cCQ_mul take explicit int64_t value parameter: Eliminated QPU_state->R0 global dependency (quick-001)
- Q_not/cQ_not parallel/sequential X/CX gates for width-parameterized NOT (06-01)
- Q_xor/cQ_xor parallel/sequential CNOT/Toffoli gates for width-parameterized XOR (06-01)
- Q_and uses single layer of parallel Toffoli gates (06-02)
- Q_or uses A XOR B XOR (A AND B) = A OR B identity with 3 layers (06-02)
- CQ_and: CNOT for 1s, skip for 0s (0 AND x = 0) (06-02)
- CQ_or: X for 1s (1 OR x = 1), CNOT for 0s (0 OR x = x) (06-02)
- Bitwise ops return qint (not qbool) with max width of operands (06-03)
- In-place bitwise ops swap qubit references rather than copy (06-03)
- Classical XOR via individual X gates (no dedicated CQ_xor function) (06-03)
- Test widths capped at 12-16 bits for AND/OR due to circuit complexity (06-04)
- Fixed __iand__/__ior__ cdef attribute access with Cython cast (06-04)
- XOR-based equality check: O(n) gates vs O(n²) subtraction-based (07-02)
- Ancilla for comparison temp storage: preserve input operands during comparison (07-02)
- C comparison stubs for Phase 7: full C implementation deferred to Phase 8 (07-02)
- Derived comparisons: __gt__ = other < self, __le__ = NOT (other < self) (07-02)

### Pending Todos

None yet.

### Blockers/Concerns

**Critical Path Dependencies:**
- Phase 7 Plan 01 BLOCKING - IntegerMultiplication.c partially modified, causing compilation errors
- Phase 7 Plan 02 COMPLETE - Comparison operators implemented (Python-level)

**Research Flags:**
- Phase 6: Medium priority - quantum bit shift/rotate circuits
- Phase 7: High priority - QFT-based arithmetic and modular operations

**Current Concerns:**
- IntegerMultiplication.c has incomplete modifications blocking full compilation (07-02)
- Comparison operators verified by code review, integration tests pending 07-01 completion (07-02)
- Virtual environment symlinks point to macOS paths, need proper venv setup for local development (01-01, 01-02)
- Existing codebase has 65+ Ruff violations (bare except, tabs vs spaces) that need cleanup (01-01)
- IntegerComparison.c uses conservative +10 buffer for layer allocation - may need precise calculation in future (02-01)
- All 213 tests pass with variable-width arithmetic and comprehensive test coverage (125 + 88 Phase 6)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | CQ operations refactored to take value parameter | 2026-01-26 | 7f3cd62 | [001-refactor-cq-operations](./quick/001-refactor-cq-operations-to-take-value-par/) |

## Session Continuity

Last session: 2026-01-26
Stopped at: Completed 07-02-PLAN.md - Comparison operators (Phase 7 Plan 2)
Resume file: None

## Phase 7 Summary

**IN PROGRESS**

- **Plan 01:** Variable-width multiplication - BLOCKED (partially modified, needs completion)
- **Plan 02:** Comparison operators - COMPLETE
- **Plan 03:** Division operations - TODO
- **Plan 04:** Modular arithmetic - TODO
- **Plan 05:** Phase 7 test suite - TODO

**Plan 02 Achievements:**
- XOR-based equality check (__eq__) with O(n) gate complexity
- Subtraction-based less-than (__lt__) with MSB sign check
- Derived __gt__, __le__, __ge__, __ne__ from __lt__ and __eq__
- All comparison operators return qbool (1-bit qint)
- Input operands preserved via ancilla allocation
- IntegerComparison.c stub functions compile successfully

**Next Steps:**
- Complete Plan 01 (multiplication) to unblock compilation
- Plans 03-05 depend on working multiplication and comparison

## Phase 6 Summary

**COMPLETE**

- **Plan 01:** Width-parameterized NOT and XOR (Q_not, cQ_not, Q_xor, cQ_xor) - COMPLETE
- **Plan 02:** Width-parameterized AND and OR (Q_and, CQ_and, Q_or, CQ_or) - COMPLETE
- **Plan 03:** Python bindings for bitwise operations - COMPLETE
- **Plan 04:** Bitwise operations test suite (88 tests) - COMPLETE

**Key Achievements:**
- Q_not(bits): Parallel X gates for bitwise NOT (O(1) depth)
- cQ_not(bits): Controlled NOT with sequential CX gates (O(bits) depth)
- Q_xor(bits): Parallel CNOT for in-place XOR (O(1) depth)
- cQ_xor(bits): Controlled XOR with Toffoli gates (O(bits) depth)
- Q_and(bits): Parallel Toffoli gates for AND (O(1) depth)
- CQ_and(bits, value): CNOT gates for classical-quantum AND
- Q_or(bits): 3-layer CNOT+Toffoli for OR (O(3) depth)
- CQ_or(bits, value): X/CNOT gates for classical-quantum OR
- Python __and__, __or__, __xor__, __invert__ with variable-width support
- Augmented assignment (&=, |=, ^=) with qubit reference swap pattern
- 88 tests covering BITOP-01 through BITOP-05 requirements

**All Phase 6 Success Criteria Met:**
1. Bitwise AND, OR, XOR, NOT work on quantum integers
2. Python operator overloading works (&, |, ^, ~, &=, |=, ^=)
3. Operations respect variable-width integers (result = max width)
4. Circuit depth is reasonable for supported widths

**Next Phase:**
- Phase 7: Comparison Operations
