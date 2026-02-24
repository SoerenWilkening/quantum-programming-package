---
phase: 88-binary-size-reduction
plan: 02
subsystem: build-system
tags: [size-optimization, benchmarking, Os-vs-O3]
requires: [88-01]
provides: [final-optimization-level, benchmark-results]
affects: [setup.py]
tech-stack:
  added: []
  patterns: [Os-optimization, benchmark-methodology]
key-files:
  created:
    - .planning/phases/88-binary-size-reduction/88-BENCHMARK.md
  modified:
    - setup.py
key-decisions:
  - "-Os chosen over -O3: 57.0% size reduction, 26.7% faster (no regression)"
requirements-completed: [SIZE-03]
duration: 12 min
completed: 2026-02-24
---

# Phase 88 Plan 02: Benchmark -Os vs -O3 Summary

Evaluated -Os vs -O3 for Release builds. -Os is both smaller (0.8% further reduction) and faster (26.7% faster than -O3). Final configuration: -Os + gc-sections + strip achieves 57.0% total size reduction.

## Duration
- Start: 2026-02-24T17:18:22Z
- End: 2026-02-24T17:28:25Z
- Duration: ~12 min
- Tasks: 1
- Files: 2

## Task Results

### Task 1: Benchmark -O3 vs -Os
- -O3 + gc-sections + strip: 27.9 MB total, 0.95 ms median circuit gen time
- -Os + gc-sections + strip: 27.7 MB total, 0.70 ms median circuit gen time
- -Os performance regression: -26.7% (faster, not slower)
- Decision: -Os chosen (size preference + actually faster)
- setup.py updated to use -Os in Release mode
- BENCHMARK.md created with full comparison data
- Commit: a4101ed

## Deviations from Plan

- Benchmark script adapted: `ql.reset_circuit()` does not exist in quantum_language; each benchmark run creates fresh qints instead (circuit state accumulates across runs, but timing is still valid for comparison)
- All benchmark runs within the same process (no isolation), which is consistent between -O3 and -Os so comparison is valid

## Next

Phase 88 complete. All 3 requirements (SIZE-01, SIZE-02, SIZE-03) addressed. Ready for Phase 89 (Test Coverage).
