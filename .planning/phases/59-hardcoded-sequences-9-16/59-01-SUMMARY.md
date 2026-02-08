---
phase: 59-hardcoded-sequences-9-16
plan: 01
subsystem: codegen
tags: [python, code-generation, c-backend, hardcoded-sequences, QFT, addition]

# Dependency graph
requires:
  - phase: 58-hardcoded-sequences-1-8
    provides: "Existing generate_seq_1_4.py and generate_seq_5_8.py scripts, QQ_add/cQQ_add patterns"
provides:
  - "Unified generation script for all 16 per-width C files + dispatch file"
  - "CQ_add and cCQ_add template-init generation matching C QFT layout"
  - "Cross-validation infrastructure (--validate flag)"
affects: [59-02, 59-03, 59-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template-init pattern: pre-allocate sequence, inject angles at runtime"
    - "Unified code generation: single script replaces multiple per-range scripts"
    - "#ifdef SEQ_WIDTH_N conditional compilation per width"

key-files:
  created:
    - "scripts/generate_seq_all.py"
  modified: []

key-decisions:
  - "SEQ-06: Use C QFT() packed layer layout (2*n-1 layers) for CQ/cCQ templates"
  - "SEQ-07: Conditional compilation via #ifdef SEQ_WIDTH_N per-width files"
  - "SEQ-08: Template-init functions return mutable sequence_t* for angle injection"
  - "SEQ-09: Dispatch file uses switch(bits) with #ifdef guards per case"

patterns-established:
  - "Template-init pattern: init_hardcoded_CQ_add_N() allocates once, caches, returns mutable"
  - "Per-width files wrap all content in #ifdef SEQ_WIDTH_N for selective compilation"

# Metrics
duration: 7min
completed: 2026-02-06
---

# Phase 59 Plan 01: Unified Generation Script Summary

**Unified Python script (939 lines) generating all 4 addition variants (QQ, cQQ, CQ, cCQ) for widths 1-16 with dispatch routing and cross-validation**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-06T13:01:09Z
- **Completed:** 2026-02-06T13:08:01Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created unified generation script replacing both generate_seq_1_4.py and generate_seq_5_8.py
- Added CQ_add and cCQ_add template-init generation matching exact C QFT() layer layout
- Cross-validated all widths 1-8 against existing C files (layer counts and gate counts match)
- Verified CQ_add/cCQ_add templates produce correct 5*N-2 layer counts for widths 1-16
- Confirmed cQQ_add Block 2 fix from quick-015 preserved (bits+bit control for negative rotations)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create unified generation script** - `1ac89a6` (feat)
2. **Task 2: Cross-validate script output against existing sequences** - `8952744` (fix)

**Plan metadata:** (pending)

## Files Created/Modified
- `scripts/generate_seq_all.py` - Unified generation script (939 lines) for all 16 per-width C files + dispatch file

## Decisions Made
- **SEQ-06:** CQ_add/cCQ_add templates use C QFT() packed layer layout (2*n-1 layers with gate overlapping) rather than one-gate-per-layer. This ensures template layer indices match the dynamic C code exactly (start_layer = 2*bits-1).
- **SEQ-07:** Each per-width file is wrapped in `#ifdef SEQ_WIDTH_N` for selective compilation. This allows build system to include only needed widths.
- **SEQ-08:** Template-init functions return `sequence_t *` (mutable) instead of `const sequence_t *` because the caller needs to inject rotation angles at runtime.
- **SEQ-09:** Dispatch file uses `switch(bits)` with `#ifdef` guards per case, allowing the linker to resolve only compiled widths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed CQ_add/cCQ_add template layer count mismatch**
- **Found during:** Task 2 (Cross-validation)
- **Issue:** Template generators used one-gate-per-layer QFT layout (producing bits*(bits+1)/2 QFT layers) instead of matching the C QFT() packed layout (2*bits-1 layers). This caused layer counts like 15 instead of 13 for width 3.
- **Fix:** Rewrote template layer generators to use _generate_qft_layers() and _generate_iqft_layers() helpers that replicate the exact C QFT() gate packing (H and CP gates sharing layers when operating on independent qubits).
- **Files modified:** scripts/generate_seq_all.py
- **Verification:** --validate confirms all 16 widths produce correct 5*N-2 layer counts
- **Committed in:** 8952744 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- templates must match C layout exactly for angle injection to work at correct layer indices.

## Issues Encountered
- Plan referenced incorrect expected layer counts for QQ_add (3, 8, 13, 18...) and cQQ_add (7, 17, 28, 40...) which are the pre-optimization counts from the C dynamic generation, not the post-optimization counts from the Python scripts. The actual reference values from existing C files are QQ_add: 3, 8, 14, 23, 35, 50, 68, 89 and cQQ_add: 7, 15, 26, 40, 57, 77, 100, 126.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Unified script ready to generate all 16 per-width C files for Plan 02
- Dispatch file generation ready for Plan 03/04 build integration
- CQ_add/cCQ_add template pattern established for use in IntegerAddition.c routing
- No blockers for subsequent plans

---
*Phase: 59-hardcoded-sequences-9-16*
*Completed: 2026-02-06*
