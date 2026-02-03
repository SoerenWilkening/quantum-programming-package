# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** Phase 47 - Detail Mode & Public API (v1.9)

## Current Position

Phase: 47 of 47 (Detail Mode & Public API)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-03 -- Completed 47-01-PLAN.md (Detail Mode Renderer)

Progress: [████████████████████████████████████░░░░░] 86% (6/7 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 141 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 6)
- Average duration: ~13 min/plan
- Total execution time: ~23.4 hours

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
| v1.9 Pixel-Art Circuit Visualization | 45-47 | 7 | In Progress |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

Recent decisions for v1.9:
- Pure Python (PIL) renderer first; optimize to C only if needed
- Pixel-art over ASCII for large circuits (scales to 200+ qubits)
- NumPy array-based bulk rendering (not per-pixel ImageDraw)
- Cython data extraction follows circuit_to_qasm_string() pattern
- draw_data_t uses calloc + two-pass control counting for safe allocation
- Qubit compaction via used_occupation_indices_per_qubit detection
- 3x3 pixel cells (2px gate + 1px gap) for clean pixel art
- Wires drawn before gates; measurement checkerboard may overlap wire pixels
- Rendering order: wires -> control lines -> gate blocks -> control dots (VIZ-CTRL-ORDER)
- Synthetic draw_data dicts for scale tests to avoid Cython build dependency (VIZ-SCALE-SYNTH)
- 12px cell size with size-8 default font for detail mode gate labels (VIZ-DETAIL-CELL)
- 40px left margin for qubit labels in detail mode (VIZ-DETAIL-MARGIN)
- Measurement uses 2x2-block checkerboard at detail scale, not M text (VIZ-MEAS-CHECKER-DETAIL)

### Blockers/Concerns

**Carry forward (not in v1.9 scope):**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)

**Known limitations (not bugs):**
- Dirty ancilla in gt/le comparisons (by design)
- 4 pre-existing uncomputation test failures (architectural: layer counter vs instruction counter)

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 47-01-PLAN.md (Detail Mode Renderer)
Resume file: None
Resume action: Execute 47-02 (Public API)

---
*State updated: 2026-02-03 -- Completed 47-01 Detail Mode Renderer*
