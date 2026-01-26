# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** Phase 3: Memory Architecture

## Current Position

Phase: 3 of 10 (Memory Architecture)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-01-26 - Completed 03-01-PLAN.md

Progress: [██░░░░░░░░] 23%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 5.6 min
- Total execution time: 0.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 - Testing Foundation | 3 | 18 min | 6 min |
| 02 - C Layer Cleanup | 3 | 18 min | 6 min |
| 03 - Memory Architecture | 1 | 5 min | 5 min |

**Recent Trend:**
- Last 5 plans: 02-01 (4 min), 02-02 (9 min), 02-03 (5 min), 03-01 (5 min)
- Trend: Phase 3 started strong (5 min), maintaining consistent ~5-6 min velocity

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

### Pending Todos

None yet.

### Blockers/Concerns

**Critical Path Dependencies:**
- Phase 3 enables both Phase 4 (Module Separation) and Phase 5 (Variable-Width Integers)
- Phase 5 and Phase 6 can run in parallel

**Research Flags:**
- Phase 5: Medium priority - optimal gate sequences for variable-width arithmetic
- Phase 6: Medium priority - quantum bit shift/rotate circuits
- Phase 7: High priority - QFT-based arithmetic and modular operations

**Current Concerns:**
- Virtual environment symlinks point to macOS paths, need proper venv setup for local development (01-01, 01-02)
- Existing codebase has 65+ Ruff violations (bare except, tabs vs spaces) that need cleanup (01-01)
- Fixed critical C compilation issues in Integer.c and QPU.c (missing stdint.h) (01-02)
- IntegerComparison.c uses conservative +10 buffer for layer allocation - may need precise calculation in future (02-01)
- Phase 3 Plan 1 complete - allocator established, ready for Plan 2 (ownership tracking migration)
- Allocator not yet used by QINT/QBOOL - Plan 2 will migrate to use allocator
- qubit_indices/ancilla still in circuit_t for backward compatibility - TODO for Plan 2 removal

## Session Continuity

Last session: 2026-01-26
Stopped at: Completed 03-01-PLAN.md - Qubit allocator module created and integrated
Resume file: None
