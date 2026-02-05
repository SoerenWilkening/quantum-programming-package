# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-05)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v2.2 Performance Optimization

## Current Position

Phase: 58 - Hardcoded Sequences (1-8 bit)
Plan: 3/3 complete
Status: Phase complete
Last activity: 2026-02-05 — Completed quick task 014: cQQ_add qubit layout fix

Progress: [██████....] ~50% (v2.2: 5/7 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 167 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 11)
- Average duration: ~13 min/plan
- Total execution time: ~24.3 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | 33 | Complete (2026-02-01) |
| v1.6 Array & Comparison Fixes | 34-36 | 5 | Complete (2026-02-02) |
| v1.7 Bug Fixes & Array Optimization | 37, 40 | 2 | Complete (2026-02-02) |
| v1.8 Copy, Mutability & Uncomp Fix | 41-44 | 7 | Complete (2026-02-03) |
| v1.9 Pixel-Art Circuit Visualization | 45-47 | 7 | Complete (2026-02-03) |
| v2.0 Function Compilation | 48-51 | 8 | Complete (2026-02-04) |
| v2.1 Compile Enhancements | 52-54 | 6 | Complete (2026-02-05) |
| v2.2 Performance Optimization | 55-61 | TBD | Active |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

Recent decisions (v2.1):
- Only track forward calls when ancilla qubits exist
- f.inverse is @property returning _AncillaInverseProxy
- f.adjoint is @property returning _InverseCompiledFunc
- Auto-uncompute triggers after both replay and capture paths
- Cache key includes qubit_saving mode
- Use iteration protocol for qarray cdef access
- Cache key uses ('arr', length) tuple for qarray

Recent decisions (v2.2):
- Used cProfile + pstats directly for profiler (no external dependency)
- Benchmarks skip gracefully when pytest-benchmark not installed
- Benchmark fixtures create fresh circuit for state isolation
- Use PYTHONPATH=src for profiling targets (in-place builds)
- Process pyx files individually in profile-cython (include directive handling)
- Use inline cProfile API instead of -c flag (better compatibility)
- Forward/adjoint replays produce equal depths - no fix needed for that
- Real discrepancy is capture vs replay when capture allows parallelization
- Root cause is layer_floor constraint in compile.py lines 984-994
- ql.circuit() clears compilation cache - tests must warm cache before measuring
- Phase 56 success criterion met: f(x) depth == f.adjoint(x) depth (verified)
- Use benchmark.pedantic with setup for qubit-allocating operations
- CYTHON_DEBUG enables boundscheck, wraparound, initializedcheck
- Apply CYT-01 (static typing), CYT-02 (directives), CYT-03 (memory views) to hot paths
- Defer CYT-04 (nogil) to Phase 60 due to Python call dependencies in accessors

**Phase 58 decisions:**
- SEQ-01: Use SEQ_PI compile-time constant instead of M_PI (M_PI not constant expression)
- SEQ-02: Separate 1-4 and 5-8 bit widths into different source files
- SEQ-03: Use const gate_t arrays with designated initializers for compile-time allocation
- SEQ-04: Generate C code via Python script for 5-8 bit sequences (reproducibility)
- SEQ-05: Use const cast in IntegerAddition.c for hardcoded return (safe due to static lifetime)

### v2.2 Research Findings

Key constraints and guidance from research:
- Python 3.11 mandatory for Cython profiling (PEP-669 breaks profiling in 3.12+)
- Profile before optimizing (avoid premature optimization)
- f()/f.inverse() depth discrepancy is a quick win
- Move entire hot paths to C (not individual functions) to avoid boundary overhead
- Hardcoded sequences split into 4 files (~400 LOC each per constraint)
- MIG and MEM phases are conditional on profiling results

### Phase 57 Plan 01 Baseline Metrics

**Benchmark results (key operations):**
| Operation | Mean (us) | OPS |
|-----------|-----------|-----|
| iadd_8bit | 25 | 40,040 |
| xor_8bit | 30 | 33,546 |
| add_8bit | 53 | 18,733 |
| eq_8bit | 100 | 10,001 |
| lt_8bit | 152 | 6,572 |
| mul_8bit | 356 | 2,807 |
| mul_classical | 31,256 | 32 |

**Primary optimization targets:**
1. mul_classical (100x slower than mul_8bit)
2. qint_preprocessed.pyx (1.95 MB annotation file)
3. qarray.pyx (1.21 MB annotation file)

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)
- BUG-CQQ-ARITH: cQQ_add algorithm produces incorrect arithmetic for widths 2+ (discovered in quick-014)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 014 | cQQ_add qubit layout fix | 2026-02-05 | abbd87f | [014-cqq-add-hardcoded-or-not-doesn-t-seem-to](./quick/014-cqq-add-hardcoded-or-not-doesn-t-seem-to/) |

### Phase 55 Deliverables

Profiling infrastructure now available:
- `pip install '.[profiling]'` — Install profiling dependencies
- `ql.profile()` — Inline profiling context manager
- `make profile-cprofile` — Run cProfile on quantum operations
- `make profile-cython` — Generate Cython annotation HTML
- `make benchmark` — Run pytest-benchmark tests
- `QUANTUM_PROFILE=1 pip install -e .` — Build with Cython profiling
- `CYTHON_DEBUG=1 pip install -e .` — Build with all safety checks enabled

### Phase 56 Complete (Plan 02)

**Outcome:** Success criterion met - f(x) and f.adjoint(x) produce equal circuit depth.

**No code fix was needed** - The layer_floor constraint in _replay() already guarantees depth equality. Plan 01 diagnostics confirmed this. Plan 02 converted diagnostics to permanent regression tests.

**Regression test suite established:**
- test_forward_adjoint_depth_equal (width 8)
- test_forward_adjoint_depth_equal_multiwidth (widths 4, 8, 16)
- test_controlled_depth_parity (controlled variants)
- test_depth_capture_vs_replay (capture/replay consistency)

### Phase 57 Complete

**Outcome:** Cython hot paths optimized with static typing and compiler directives.

**Verified (7/7 must-haves):**
- CYT-01 (Static typing): Typed loop variables, memory views, intermediate values
- CYT-02 (Compiler directives): @cython.boundscheck(False), @cython.wraparound(False)
- CYT-03 (Memory views): Explicit loops replace slice operations
- CYT-04 (nogil): Deferred to Phase 60 (documented)

**Deliverables:**
- CYTHON_DEBUG=1 build mode for debugging
- Expanded benchmark suite (18 tests)
- verify-optimization Makefile target
- Annotation verification tests

### Phase 58 Plan 01 Complete

**Outcome:** Static QQ_add and cQQ_add sequences for 1-4 bit widths.

**Files created:**
- c_backend/include/sequences.h (53 lines) - dispatch function declarations
- c_backend/src/sequences/add_seq_1_4.c (1504 lines) - static gate arrays

**Layer counts:**
- QQ_add: 3, 8, 13, 18 layers for widths 1-4
- cQQ_add: 7, 17, 28, 40 layers for widths 1-4

**Build integration:** setup.py updated to include new source file

### Phase 58 Plan 02 Complete

**Outcome:** Static QQ_add and cQQ_add sequences for 5-8 bit widths with routing integration.

**Files created/modified:**
- c_backend/src/sequences/add_seq_5_8.c (6351 lines) - static gate arrays for 5-8 bit
- c_backend/src/IntegerAddition.c - routing to hardcoded sequences
- scripts/generate_seq_5_8.py - code generation script

**Layer counts (5-8 bit):**
- QQ_add: 35, 43, 51, 58 layers
- cQQ_add: 53, 71, 90, 110 layers

**Routing:** QQ_add() and cQQ_add() now return hardcoded sequences for widths 1-8

### Phase 58 Complete

**Outcome:** Hardcoded addition sequences for widths 1-8 with comprehensive validation.

**Plan 03 deliverables:**
- tests/test_hardcoded_sequences.py (220 lines, 61 tests)
- Verification: All 61 new tests pass
- Verification: All 888 existing addition tests pass
- Arithmetic correctness confirmed for widths 1-8
- Dynamic fallback confirmed for width 9+

**Phase 58 totals:**
- Static gate sequences: ~7,855 lines of C code
- QQ_add sequences: 8 widths (1-8 bits)
- cQQ_add sequences: 8 widths (1-8 bits)
- Validation tests: 61 test cases

### Phase 58 Verified

**Verification status:** passed (4/4 must-haves)
**Report:** .planning/phases/58-hardcoded-sequences-1-8/58-VERIFICATION.md

All success criteria met:
1. ✓ Addition operations for 1-4 bit widths use pre-computed gate sequences
2. ✓ Addition operations for 5-8 bit widths use pre-computed gate sequences
3. ✓ Validation tests confirm hardcoded output matches dynamic generation
4. ✓ Width > 8 automatically falls back to dynamic generation

## Session Continuity

Last session: 2026-02-05
Stopped at: Phase 58 complete and verified
Resume file: .planning/ROADMAP.md
Resume action: `/gsd:discuss-phase 59` to begin Hardcoded Sequences (9-16 bit)

---
*State updated: 2026-02-05 — Quick task 014 complete (cQQ_add qubit layout fix)*
