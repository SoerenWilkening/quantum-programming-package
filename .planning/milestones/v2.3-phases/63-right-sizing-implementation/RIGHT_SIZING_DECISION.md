# Right-Sizing Decision: Addition Hardcoded Sequences

## Decision: KEEP all addition widths 1-16 hardcoded

**Date:** 2026-02-08
**Phase:** 63 (Right-Sizing Implementation)
**Based on:** Phase 62 benchmark data (verified)

## Data Justification (from Phase 62 benchmarks)

### Import Time Overhead
- **Median import time:** 192ms (one-time cost per process)
- This is amortized across all subsequent dispatch calls
- Acceptable for any non-trivial quantum computation

### Dispatch Speedup
- **Cached call speedup:** 2-6x for hardcoded vs dynamic dispatch
  - QQ_add width 8: 18us (hardcoded) vs 108us (dynamic) = 6x
  - cQQ_add width 8: similar ratio
- **First-call saving:** ~350us per unique (operation, width) pair

### Break-Even Analysis
- **First-call break-even:** 550 unique first calls to recoup 192ms import overhead
- **Cached-call break-even:** 3,533 cached calls to recoup import overhead
- Any realistic quantum program exceeds these thresholds

### Binary Size
- **Total .so size:** 16.4 MB across 6 extensions
  - qint: 4.8 MB, qarray: 3.7 MB, _core: 2.4 MB
  - qint_mod: 2.2 MB, qbool: 1.9 MB, openqasm: 1.7 MB
- Acceptable for a development/research tool

## Factoring Plan: Shared QFT/IQFT Sub-Sequences

### Approach
Within each per-width C file, the QFT and IQFT gate layer arrays are identical between QQ_add and cQQ_add variants. Factor these into shared static const arrays that both variants reference by pointer. Similarly, share QFT/IQFT initialization helper functions between CQ_add and cCQ_add template-init variants.

### Two sharing categories (const vs mutable separation)
1. **Static const sharing (QQ_add + cQQ_add):** Shared `SHARED_QFT_N_L*` and `SHARED_IQFT_N_L*` gate arrays referenced by both LAYERS[] arrays
2. **Template-init sharing (CQ_add + cCQ_add):** Shared `init_shared_qft_layers_N()` and `init_shared_iqft_layers_N()` helper functions called by both init functions

### Boundary Optimization Prevention
Optimization is applied independently to QFT, middle, and IQFT segments to prevent cross-boundary layer merging, which would make layers unshareable.

## Baseline Measurements (Before Factoring)

### Per-File Line Counts

| File | Lines |
|------|-------|
| add_seq_1.c | 268 |
| add_seq_2.c | 503 |
| add_seq_3.c | 820 |
| add_seq_4.c | 1,221 |
| add_seq_5.c | 1,706 |
| add_seq_6.c | 2,276 |
| add_seq_7.c | 2,930 |
| add_seq_8.c | 3,665 |
| add_seq_9.c | 4,487 |
| add_seq_10.c | 5,400 |
| add_seq_11.c | 6,392 |
| add_seq_12.c | 7,466 |
| add_seq_13.c | 8,626 |
| add_seq_14.c | 9,870 |
| add_seq_15.c | 11,199 |
| add_seq_16.c | 12,611 |
| add_seq_dispatch.c | 427 |
| **Total** | **79,867** |

### Directory Size
- **Before:** 4.0 MB on disk

### After Factoring (Actual Measurements)

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| add_seq_2.c | 503 | 438 | 65 (12.9%) |
| add_seq_8.c | 3,665 | 2,513 | 1,152 (31.4%) |
| add_seq_16.c | 12,611 | 8,182 | 4,429 (35.1%) |
| add_seq_dispatch.c | 427 | 427 | 0 (unchanged) |
| **All files total** | **79,867** | **53,598** | **26,269 (32.9%)** |

- **Total lines after:** 53,598 (after clang-format)
- **Lines reduced:** 26,269
- **Percentage reduction:** 32.9%

The reduction is much larger than the initial 5-8% estimate from the research phase because:
1. The shared QFT/IQFT static const arrays eliminate two full sets of layer definitions per width (QQ and cQQ each had their own QFT/IQFT)
2. The shared init helpers eliminate two full sets of QFT/IQFT initialization code per width (CQ and cCQ each had their own)
3. The packed QFT layout from `_generate_qft_layers()` produces fewer layers than the sequential approach, further reducing code
4. Segmented optimization (QFT/middle/IQFT independently) has minimal overhead (+1 layer for widths >= 2)

## Widths Excluded from Hardcoding

**None.** All widths 1-16 are retained as hardcoded sequences. Widths 17+ continue to use dynamic generation at runtime.

## Other Operations (NOT hardcoded per Phase 62 recommendations)

| Operation | Decision | Rationale |
|-----------|----------|-----------|
| Multiplication | Deferred (investigate later) | 48x addition cost, binary size concern, CQ_mul not cached |
| Bitwise (XOR, AND, OR) | Skip | Max 288us generation, trivial |
| Division | Skip | Python-level loop cost dominates, not C sequence generation |
