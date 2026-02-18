---
phase: 66-cdkm-ripple-carry-adder
plan: 01
subsystem: arithmetic
tags: [toffoli, cdkm, ripple-carry, adder, maj, uma, ancilla]

# Dependency graph
requires:
  - phase: 65-infrastructure-prerequisites
    provides: "qubit_allocator block-based alloc/free, run_instruction inversion fix"
provides:
  - "ToffoliAddition.c with toffoli_QQ_add and toffoli_CQ_add (CDKM adder)"
  - "toffoli_arithmetic_ops.h public API"
  - "arithmetic_mode_t enum and circuit_t arithmetic_mode field"
  - "Toffoli dispatch in hot_path_add.c with ancilla lifecycle"
affects: [66-02, 67-controlled-toffoli, 68-python-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [cdkm-maj-uma-chain, cq-classical-bit-simplification, toffoli-dispatch-fallback]

key-files:
  created:
    - c_backend/src/ToffoliAddition.c
    - c_backend/include/toffoli_arithmetic_ops.h
  modified:
    - c_backend/include/types.h
    - c_backend/include/circuit.h
    - c_backend/src/circuit_allocations.c
    - c_backend/src/hot_path_add.c

key-decisions:
  - "Separate precompiled cache for Toffoli QQ (not shared with QFT cache)"
  - "CQ sequences generated fresh each call (value-dependent structure), freed by caller via toffoli_sequence_free"
  - "Controlled operations fall back to QFT when ARITH_TOFFOLI (Phase 67 will add controlled Toffoli)"
  - "ARITH_QFT = 0 ensures backward-compatible default via calloc zeroing"

patterns-established:
  - "MAJ/UMA emit pattern: 3 gates per call, each on its own layer, using gate_func(&seq->seq[layer][gates_per_layer[layer]++]) idiom"
  - "CQ classical bit simplification: bit=0 -> 1 gate (CNOT only), bit=1 -> 3 gates (X + 2 CNOT or 2 CNOT + X)"
  - "Toffoli dispatch: check arithmetic_mode before QFT path, fall through for controlled ops"
  - "Ancilla lifecycle in hot path: allocator_alloc before sequence, allocator_free after run_instruction"

# Metrics
duration: 7min
completed: 2026-02-14
---

# Phase 66 Plan 01: CDKM Ripple-Carry Adder Summary

**CDKM ripple-carry adder using MAJ/UMA chain with Toffoli dispatch in hot path and per-call ancilla lifecycle**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-14T19:48:34Z
- **Completed:** 2026-02-14T19:55:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented CDKM ripple-carry adder (toffoli_QQ_add) with MAJ/UMA chain: 6n layers for n>=2, 1 CNOT for n=1
- Implemented classical-quantum Toffoli adder (toffoli_CQ_add) with value-dependent gate emission using classical bit simplification
- Added arithmetic_mode_t enum and circuit_t field for QFT/Toffoli mode switching
- Wired Toffoli dispatch into both hot_path_add_qq and hot_path_add_cq with proper ancilla alloc/free lifecycle
- Ensured backward compatibility: ARITH_QFT=0 default, controlled operations fall back to QFT

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ToffoliAddition.c with CDKM adder and supporting infrastructure** - `13cf301` (feat)
2. **Task 2: Wire Toffoli dispatch into hot_path_add.c with ancilla lifecycle** - `d1ece72` (feat)

## Files Created/Modified
- `c_backend/src/ToffoliAddition.c` - CDKM adder: toffoli_QQ_add (cached), toffoli_CQ_add (fresh per call), toffoli_sequence_free, MAJ/UMA emit helpers (414 lines)
- `c_backend/include/toffoli_arithmetic_ops.h` - Public API declarations for Toffoli arithmetic functions (68 lines)
- `c_backend/include/types.h` - Added arithmetic_mode_t enum (ARITH_QFT=0, ARITH_TOFFOLI=1)
- `c_backend/include/circuit.h` - Added arithmetic_mode field to circuit_t struct
- `c_backend/src/circuit_allocations.c` - Initialize arithmetic_mode to ARITH_QFT in init_circuit()
- `c_backend/src/hot_path_add.c` - Toffoli dispatch in hot_path_add_qq and hot_path_add_cq with ancilla lifecycle

## Decisions Made
- **Separate cache for Toffoli QQ:** Not shared with QFT precompiled sequences to avoid mixing paradigms. Cache indexed by bits (1-64).
- **No cache for Toffoli CQ:** Value-dependent gate structure prevents caching. Fresh allocation per call, freed by caller via toffoli_sequence_free().
- **Controlled fallback to QFT:** ARITH_TOFFOLI mode with controlled=true falls through to existing QFT path. Controlled Toffoli adder deferred to Phase 67.
- **ARITH_QFT = 0 default:** Ensures calloc/memset zeroing gives backward-compatible default without explicit initialization (though we initialize explicitly for clarity).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all files compiled cleanly on first attempt (after clang-format auto-formatting).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ToffoliAddition.c is ready for Python integration testing (66-02)
- The arithmetic_mode field can be set from Python/Cython to enable Toffoli path
- Controlled Toffoli adder (cQQ, cCQ) will be implemented in Phase 67

## Self-Check: PASSED

- All 7 files verified present on disk
- Both commit hashes (13cf301, d1ece72) verified in git log
- ToffoliAddition.c: 414 lines (exceeds 200 min_lines requirement)
- All C files compile without errors (gcc -Wall -Wextra)
- Existing QFT addition tests pass (backward-compatible)

---
*Phase: 66-cdkm-ripple-carry-adder*
*Completed: 2026-02-14*
