# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-05)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v2.2 Performance Optimization

## Current Position

Phase: 56 - Forward/Inverse Depth Fix
Plan: 2/2 complete
Status: Phase complete
Last activity: 2026-02-05 — Completed 56-02-PLAN.md (Depth Fix Implementation)

Progress: [███.......] ~20% (v2.2: 2/7 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 161 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 5)
- Average duration: ~13 min/plan
- Total execution time: ~24.1 hours

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

### v2.2 Research Findings

Key constraints and guidance from research:
- Python 3.11 mandatory for Cython profiling (PEP-669 breaks profiling in 3.12+)
- Profile before optimizing (avoid premature optimization)
- f()/f.inverse() depth discrepancy is a quick win
- Move entire hot paths to C (not individual functions) to avoid boundary overhead
- Hardcoded sequences split into 4 files (~400 LOC each per constraint)
- MIG and MEM phases are conditional on profiling results

### Phase 56 Findings (Plan 01)

**Key finding:** Forward/adjoint replays produce EQUAL depths. The original assumption of f(x)/f.inverse(x) depth discrepancy was incorrect.

**Actual discrepancy:** Capture vs replay depths differ when:
- Capture occurs after operations on non-overlapping qubits (gates pack into earlier layers)
- Replay sets layer_floor=current_layer (forces gates to start at current position)

**Root cause location:** compile.py lines 984-994 (_replay method)

**Fix options:**
1. Set layer_floor during capture too (consistency)
2. Store relative layer offsets, apply during replay (preserves optimization)

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)

### Phase 55 Deliverables

Profiling infrastructure now available:
- `pip install '.[profiling]'` — Install profiling dependencies
- `ql.profile()` — Inline profiling context manager
- `make profile-cprofile` — Run cProfile on quantum operations
- `make profile-cython` — Generate Cython annotation HTML
- `make benchmark` — Run pytest-benchmark tests
- `QUANTUM_PROFILE=1 pip install -e .` — Build with Cython profiling

### Phase 56 Complete (Plan 02)

**Outcome:** Success criterion met - f(x) and f.adjoint(x) produce equal circuit depth.

**No code fix was needed** - The layer_floor constraint in _replay() already guarantees depth equality. Plan 01 diagnostics confirmed this. Plan 02 converted diagnostics to permanent regression tests.

**Regression test suite established:**
- test_forward_adjoint_depth_equal (width 8)
- test_forward_adjoint_depth_equal_multiwidth (widths 4, 8, 16)
- test_controlled_depth_parity (controlled variants)
- test_depth_capture_vs_replay (capture/replay consistency)

## Session Continuity

Last session: 2026-02-05
Stopped at: Completed 56-02-PLAN.md (Depth Fix Implementation)
Resume file: .planning/phases/56-forward-inverse-depth-fix/56-02-SUMMARY.md
Resume action: Continue to next phase (57+)

---
*State updated: 2026-02-05 — Phase 56 complete (Forward/Inverse Depth Fix)*
