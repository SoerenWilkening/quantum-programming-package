---
phase: 72-performance-polish
plan: 01
subsystem: performance
tags: [toffoli, hardcoded-sequences, cdkm, code-generation, static-const]

# Dependency graph
requires:
  - phase: 66-toffoli-addition
    provides: "CDKM adder algorithm (ToffoliAddition.c MAJ/UMA chains)"
  - phase: 58-hardcoded-sequences
    provides: "Hardcoded sequence infrastructure pattern (generate_seq_all.py)"
provides:
  - "Toffoli hardcoded sequence generation script (scripts/generate_toffoli_seq.py)"
  - "8 per-width C files for CDKM Toffoli addition (widths 1-8)"
  - "Toffoli sequence dispatch infrastructure (header + dispatch file)"
  - "Public API: get_hardcoded_toffoli_QQ_add(), get_hardcoded_toffoli_cQQ_add()"
affects: [72-02, 72-03, ToffoliAddition.c, hot_path_add.c]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Toffoli static const for CX/CCX-only sequences", "Dynamic init with caching for MCX(3 controls) sequences"]

key-files:
  created:
    - scripts/generate_toffoli_seq.py
    - c_backend/include/toffoli_sequences.h
    - c_backend/src/sequences/toffoli_add_seq_dispatch.c
    - c_backend/src/sequences/toffoli_add_seq_1.c
    - c_backend/src/sequences/toffoli_add_seq_2.c
    - c_backend/src/sequences/toffoli_add_seq_3.c
    - c_backend/src/sequences/toffoli_add_seq_4.c
    - c_backend/src/sequences/toffoli_add_seq_5.c
    - c_backend/src/sequences/toffoli_add_seq_6.c
    - c_backend/src/sequences/toffoli_add_seq_7.c
    - c_backend/src/sequences/toffoli_add_seq_8.c
  modified: []

key-decisions:
  - "QQ variant as static const (max 2 controls: CX/CCX), cQQ variant as dynamic init with caching (MCX needs large_control heap allocation)"
  - "Separate toffoli_sequences.h header (not merged into existing sequences.h) to avoid polluting QFT sequence namespace"

patterns-established:
  - "Toffoli hardcoded pattern: TOFFOLI_SEQ_WIDTH_N preprocessor guards, TOFFOLI_QQ_N_Lx layer naming"
  - "Dynamic init with cleanup goto for cQQ sequences with MCX(3 controls)"

requirements-completed: [INF-03]

# Metrics
duration: 5min
completed: 2026-02-16
---

# Phase 72 Plan 01: Toffoli Hardcoded Sequence Generation Summary

**CDKM Toffoli addition hardcoded sequences for widths 1-8: QQ as static const, cQQ as cached dynamic init, with Python generation script and C dispatch infrastructure**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-16T22:49:00Z
- **Completed:** 2026-02-16T22:54:07Z
- **Tasks:** 2
- **Files created:** 11

## Accomplishments
- Created scripts/generate_toffoli_seq.py (856 lines) that algorithmically generates CDKM gate sequences for widths 1-8, producing both QQ and cQQ variants
- Generated 8 per-width C files, each containing static const QQ sequences and dynamically initialized cQQ sequences with caching
- All generated C files compile without errors; CDKM gate sequences verified algorithmically against expected MAJ/UMA patterns
- Width 1: 1 layer (CX/CCX), Width N>=2: 6*N layers (N MAJ + N UMA chains)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Toffoli hardcoded sequence generation script** - `651d68d` (feat)
2. **Task 2: Verify generated C files compile** - verification only (no changes)

## Files Created/Modified
- `scripts/generate_toffoli_seq.py` - Python generation script for Toffoli CDKM hardcoded sequences
- `c_backend/include/toffoli_sequences.h` - Public API header with TOFFOLI_SEQ_WIDTH_N guards
- `c_backend/src/sequences/toffoli_add_seq_dispatch.c` - Unified dispatch routing to per-width implementations
- `c_backend/src/sequences/toffoli_add_seq_{1..8}.c` - Per-width C files with static const QQ and dynamic init cQQ

## Decisions Made
- **QQ as static const, cQQ as dynamic init**: QQ uses only CX (1 control) and CCX (2 controls), fitting in gate_t.Control[2] as static const. cQQ uses MCX with 3 controls requiring large_control heap allocation, so a one-time init function with caching is used instead.
- **Separate header file**: toffoli_sequences.h is kept separate from sequences.h (QFT) to maintain clean namespace separation between the two arithmetic backends.
- **No layer optimization**: Unlike QFT sequences which benefit from cross-layer merging (parallel gates on independent qubits), CDKM gates are inherently serial (each gate depends on the previous), so 1 gate per layer is correct and optimal.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit ruff linter caught unused variable and loop variable naming issues in the generation script; fixed inline before final commit.
- clang-format reformatted generated C files on first commit attempt; re-staged with formatted versions.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Toffoli hardcoded sequence C files and dispatch infrastructure ready for integration
- Plan 02 will wire get_hardcoded_toffoli_QQ_add() and get_hardcoded_toffoli_cQQ_add() into ToffoliAddition.c as a cache-first lookup before dynamic generation
- Plan 03 will add T-count exposure and MCX decomposition

## Self-Check: PASSED

- All 11 created files verified present on disk
- Task 1 commit 651d68d verified in git log
- SUMMARY.md exists at expected path

---
*Phase: 72-performance-polish*
*Completed: 2026-02-16*
