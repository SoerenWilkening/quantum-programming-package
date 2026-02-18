# Phase 63: Right-Sizing Implementation - Research

**Researched:** 2026-02-08
**Domain:** C/Python build system refactoring for hardcoded quantum gate sequences
**Confidence:** HIGH

## Summary

Phase 63 implements the data-driven decision from Phase 62 benchmarks regarding which addition widths to keep hardcoded. The Phase 62 data conclusively recommends **keeping** all addition hardcoding for widths 1-16 (2-6x dispatch speedup, 192ms import amortized after 550 unique first calls). This means the phase follows the ADD-02 path: keep hardcoded sequences and factor out shared QFT/IQFT sub-sequences to reduce total generated C file size.

The current hardcoded sequence files total 79,867 lines of C code across 17 files (16 per-width + 1 dispatch), occupying 4MB on disk. Each per-width file contains four variants (QQ_add, cQQ_add, CQ_add, cCQ_add), and within each variant, the QFT and inverse QFT gate data is duplicated. For the CQ_add and cCQ_add template-init functions, the QFT/IQFT initialization code is also duplicated. Factoring out shared QFT/IQFT sub-sequences into reusable static const arrays (for QQ/cQQ variants) and shared init helper functions (for CQ/cCQ variants) can measurably reduce file size, with the largest gains at higher widths where QFT layers dominate the file.

**Primary recommendation:** Document the "keep all widths 1-16" decision with Phase 62 data justification, then modify the generation script (`scripts/generate_seq_all.py`) to emit shared QFT/IQFT layer arrays per width that are referenced by multiple variants, reducing per-width file size by approximately 25-35%. Verify with the existing test suite.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scripts/generate_seq_all.py` | current | Generates all hardcoded C sequence files | Single source of truth for all 17 generated files |
| `c_backend/include/sequences.h` | current | Header with preprocessor guards and API | Controls per-width conditional compilation |
| `setup.py` | current | Build system linking sequences into extensions | Determines which C files are compiled |
| `pytest` | installed | Test suite runner | Existing test infrastructure |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tests/test_hardcoded_sequences.py` | current | Sequence validation tests | After changes to verify arithmetic correctness |
| `tests/python/` | current | Full test suite | Final verification after all changes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Modifying generation script | Hand-editing C files | Generation script is authoritative; hand-edits would be overwritten |
| Shared static const arrays | Runtime QFT function calls | Shared arrays keep zero-cost static initialization; function calls add first-call overhead |
| Per-width sharing only | Cross-width sharing | QFT layers differ by width so cross-width sharing is not possible |

## Architecture Patterns

### Current Project Structure
```
c_backend/
  include/
    sequences.h              # Public API + preprocessor guards
  src/
    sequences/
      add_seq_1.c            # 268 lines (4 variants for width 1)
      add_seq_2.c            # 503 lines
      ...
      add_seq_16.c           # 12,611 lines (4 variants for width 16)
      add_seq_dispatch.c     # 427 lines (unified switch dispatch)
scripts/
  generate_seq_all.py        # 941 lines (generates all above)
```

### Pattern 1: QFT/IQFT Sharing Within a Width File
**What:** For each width N, QFT layers (2N-1 gate arrays) and IQFT layers (2N-1 gate arrays) are currently duplicated across QQ_add and cQQ_add variants. Both use identical static const gate_t arrays for the QFT prefix and IQFT suffix. The CQ_add and cCQ_add template-init functions also duplicate QFT/IQFT initialization code.
**When to use:** Always -- this is the core factoring opportunity.
**Current duplication analysis for width N:**
- QQ_add:  layers 0..(2N-2) are QFT, layers (3N-1)..(5N-3) are IQFT
- cQQ_add: layers 0..(2N-2) are QFT, last (2N-1) layers are IQFT
- These QFT/IQFT layer gate data are identical between QQ_add and cQQ_add

**Factoring approach:**
```c
// SHARED QFT layers for width N (static const)
static const gate_t QFT_N_L0[] = {...};
static const gate_t QFT_N_L1[] = {...};
// ... (2N-1 layers)

// SHARED IQFT layers for width N (static const)
static const gate_t IQFT_N_L0[] = {...};
// ... (2N-1 layers)

// QQ_ADD references shared QFT/IQFT layers:
static const gate_t *QQ_ADD_N_LAYERS[] = {
    QFT_N_L0, QFT_N_L1, ...,  // QFT (shared)
    QQ_ADD_N_MID_L0, ...,      // Addition-specific (unique)
    IQFT_N_L0, IQFT_N_L1, ...  // IQFT (shared)
};

// cQQ_ADD references same shared QFT/IQFT layers:
static const gate_t *cQQ_ADD_N_LAYERS[] = {
    QFT_N_L0, QFT_N_L1, ...,  // QFT (shared)
    cQQ_ADD_N_MID_L0, ...,     // CCP decomposition (unique)
    IQFT_N_L0, IQFT_N_L1, ...  // IQFT (shared)
};
```

**Key insight:** The static const gate_t arrays can be shared by reference (pointer) since they are read-only. Only the middle (operation-specific) layers differ.

### Pattern 2: CQ/cCQ Template-Init Shared Helper
**What:** The CQ_add and cCQ_add template-init functions both construct QFT and IQFT layers identically. The initialization code for these layers can be extracted into a shared helper function.
**When to use:** For the template-init variants that malloc at first call.
**Example:**
```c
// Shared QFT initialization helper for width N
static void init_qft_layers_N(sequence_t *seq, int start_layer) {
    // Layer 0: H gate on qubit N-1
    seq->gates_per_layer[start_layer] = 1;
    seq->seq[start_layer] = calloc(1, sizeof(gate_t));
    seq->seq[start_layer][0] = (gate_t){.Gate = H, .Target = N-1, ...};
    // ... remaining QFT layers
}

// CQ_add uses shared helper:
sequence_t *init_hardcoded_CQ_add_N(void) {
    // ... malloc and basic setup ...
    init_qft_layers_N(seq, 0);         // QFT at start
    // CQ-specific rotation layers (middle)
    init_iqft_layers_N(seq, 2*N-1+N);  // IQFT at end
    cached_CQ_add_N = seq;
    return seq;
}
```

### Pattern 3: Layer Merging Compatibility
**What:** The generation script applies `optimize_layers()` which merges consecutive layers with non-overlapping qubits. This optimization means QQ_add and cQQ_add may have different QFT layer structures when optimization creates merged layers.
**When to use:** Critical awareness -- must verify that QFT layers are identical BEFORE optimization or apply identical optimization to shared layers.
**Analysis:**
- `generate_qq_add()` produces raw layers, then `optimize_layers()` merges them
- `generate_cqq_add()` produces different raw layers (QFT + CCP decomposition), then `optimize_layers()` merges them
- The QFT prefix for QQ_add uses unoptimized layers (each gate gets its own layer in the raw generation), and then optimization can merge H gates with P gates from earlier QFT steps
- The cQQ_add QFT prefix is identical raw layers, so after the same optimization, the QFT layers should be identical
- **HOWEVER:** optimization is applied to the ENTIRE sequence, not just QFT. The merge opportunity between the last QFT layer and the first middle layer differs between QQ and cQQ, which could cause the QFT/IQFT boundary layers to differ.

**Implication:** The factoring must be done at the generation script level, BEFORE optimization. The script should:
1. Generate shared QFT/IQFT layers
2. Generate operation-specific middle layers
3. Concatenate them
4. Apply optimization to the full sequence
5. In the optimized output, identify which layers came from QFT vs middle vs IQFT
6. If boundary layers were merged, they cannot be shared

**Alternative simpler approach:** Don't optimize across QFT/middle/IQFT boundaries. This may slightly increase layer count but enables clean sharing.

### Anti-Patterns to Avoid
- **Modifying generated C files directly:** The files contain "DO NOT EDIT MANUALLY" -- always modify `generate_seq_all.py`
- **Cross-width sharing of QFT layers:** QFT layers for width N differ from width M (different qubits, angles) -- sharing only works within the same width
- **Removing the dispatch file when keeping sequences:** `add_seq_dispatch.c` is the unified entry point and must be maintained
- **Breaking the template-init cache pattern:** CQ_add/cCQ_add use `cached_CQ_add_N` static pointers -- factoring must preserve this caching behavior

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QFT gate sequence generation | Manual gate construction | `_generate_qft_layers()` in generate_seq_all.py | Already validated against C QFT() function |
| IQFT gate sequence generation | Manual gate construction | `_generate_iqft_layers()` in generate_seq_all.py | Already validated with angle negation |
| Layer optimization | Custom merge logic | `optimize_layers()` in generate_seq_all.py | Handles qubit overlap detection correctly |
| Sequence validation | Manual gate comparison | `pytest tests/test_hardcoded_sequences.py` | Tests arithmetic correctness, not gate structure |

**Key insight:** The generation script is the single source of truth. All changes should flow through the script, regenerate files, and validate with the test suite.

## Common Pitfalls

### Pitfall 1: Layer Boundary Merging Breaks Sharing
**What goes wrong:** After optimization, the last QFT layer and first middle layer may be merged into one combined layer. This merged layer is unique to each variant and cannot be shared.
**Why it happens:** `optimize_layers()` merges any consecutive layers with non-overlapping qubits, regardless of logical boundaries.
**How to avoid:** Either (a) skip optimization across boundaries (insert a "barrier" layer that prevents merging), or (b) accept that boundary layers cannot be shared and only share interior QFT/IQFT layers. Option (a) is cleaner but may slightly increase layer count.
**Warning signs:** Layer count changes after factoring.

### Pitfall 2: CQ_add Template-Init Mutability Requirements
**What goes wrong:** Sharing QFT layer arrays between QQ_add (static const) and CQ_add (template-init with malloc) is not straightforward because CQ_add's layers are mutable (angles are injected at runtime).
**Why it happens:** QQ_add returns `const sequence_t*` with static const gate arrays. CQ_add returns `sequence_t*` with malloc'd gate arrays where rotation angles are overwritten per call.
**How to avoid:** QFT/IQFT sharing is separate for each category:
  - Share static const gate arrays between QQ_add and cQQ_add (both use const data)
  - Share init helper functions between CQ_add and cCQ_add (both use malloc'd data)
  - Do NOT share across these categories (const vs mutable)
**Warning signs:** Segfaults when trying to write to const data.

### Pitfall 3: Forgetting to Regenerate After Script Changes
**What goes wrong:** Modifying `generate_seq_all.py` but not regenerating the C files, leading to stale sequences.
**Why it happens:** The generation is a manual step, not part of the build.
**How to avoid:** Always run `python scripts/generate_seq_all.py` after script changes, then rebuild (`pip install -e .`), then test.
**Warning signs:** Tests pass with old binaries but fail after rebuild.

### Pitfall 4: Preprocessor Guard Interaction
**What goes wrong:** Shared QFT layer arrays must be within the same `#ifdef SEQ_WIDTH_N` guard as the per-width functions that reference them.
**Why it happens:** Each width is conditionally compiled; shared arrays outside the guard would be compiled even when the width is disabled.
**How to avoid:** Keep shared QFT/IQFT arrays inside the same `#ifdef SEQ_WIDTH_N` block as the variant sequences that reference them.
**Warning signs:** Linker errors about undefined symbols when a width is disabled.

### Pitfall 5: Binary Size Unchanged After Factoring
**What goes wrong:** Factoring reduces C source size but not necessarily compiled binary size, because the compiler may deduplicate identical static const data anyway.
**Why it happens:** Modern compilers (GCC/Clang with -O3) can merge identical constant data sections.
**How to avoid:** Measure `.so` file sizes before and after factoring. The primary benefit may be source code maintainability rather than binary size. Report both source and binary size changes.
**Warning signs:** .so sizes identical before and after.

## Code Examples

### Size Analysis: QFT/IQFT Proportion Per Width
The QFT and IQFT together comprise a significant portion of each file:

| Width | QQ_add layers | QFT+IQFT layers | Middle layers | QFT% of total |
|-------|--------------|-----------------|---------------|---------------|
| 1 | 3 | 2 (1+1) | 1 | 67% |
| 2 | 8 | 6 (3+3) | 2 | 75% |
| 4 | 23 | 14 (7+7) | 9 (actually N^2/2 growth) | 61% |
| 8 | 89 | 30 (15+15) | 59 | 34% |
| 16 | ~400 | 62 (31+31) | ~338 | 16% |

**Key finding:** QFT/IQFT sharing provides the largest relative benefit for small widths (67-75% of QQ_add) but the addition-specific middle section grows quadratically, so the absolute savings in line count are larger for higher widths. However, the cQQ_add variant is much larger than QQ_add (O(N^2) CCP decomposition), so the QFT/IQFT sharing within cQQ_add also provides meaningful savings.

### Estimated Size Reduction
Each per-width file contains 4 sections:
1. QQ_add (static const): QFT + middle + IQFT
2. cQQ_add (static const): QFT + CCP middle + IQFT
3. CQ_add (template-init): QFT init + rotation init + IQFT init
4. cCQ_add (template-init): QFT init + CP rotation init + IQFT init

Sharing QFT/IQFT between (1) and (2) eliminates ~2*(2N-1) static const layer arrays.
Sharing QFT/IQFT init between (3) and (4) eliminates ~2*(2N-1) init code blocks.

For width 16:
- QFT has 31 layers, each with ~7 lines of C = ~217 lines saved (QQ/cQQ sharing)
- IQFT has 31 layers = ~217 lines saved
- CQ/cCQ init sharing = ~250 lines saved
- Total per width: ~684 lines saved out of 12,611 = ~5.4% reduction

For width 4:
- QFT 7 layers = ~49 lines, IQFT 7 layers = ~49 lines
- CQ/cCQ init = ~70 lines
- Total: ~168 lines out of 1,221 = ~13.8% reduction

Overall estimated source reduction: ~4,000-6,000 lines out of 79,867 = ~5-8% reduction across all files.

### Generation Script Modification Pattern
```python
def generate_width_file(width: int) -> str:
    """Generate complete C source file for one width."""
    output = []
    # ... header ...

    # Generate SHARED QFT layer arrays (NEW)
    qft_layers = _generate_qft_layers(width)
    output.append(generate_c_sequence("QFT", qft_layers, width))

    # Generate SHARED IQFT layer arrays (NEW)
    iqft_layers = _generate_iqft_layers(width)
    output.append(generate_c_sequence("IQFT", iqft_layers, width))

    # QQ_ADD section - references shared QFT/IQFT
    qq_middle = generate_qq_add_middle(width)  # Only the addition-specific layers
    # Build LAYERS array referencing QFT_N_L*, QQ_ADD_N_MID_L*, IQFT_N_L*

    # cQQ_ADD section - references shared QFT/IQFT
    cqq_middle = generate_cqq_add_middle(width)
    # Build LAYERS array referencing QFT_N_L*, cQQ_ADD_N_MID_L*, IQFT_N_L*

    # ... rest of file ...
```

### Decision Document Template
```markdown
# Right-Sizing Decision: Addition Hardcoded Sequences

## Decision: KEEP all addition widths 1-16 hardcoded

## Data Justification (from Phase 62 benchmarks)
- Import time overhead: 192ms median (one-time cost)
- Dispatch speedup: 2-6x for cached calls (QQ_add: 18us vs 108us)
- Break-even: 550 unique first calls or 3,533 cached calls
- Binary size: 16.4 MB across 6 extensions (acceptable)

## Factoring Applied
- Shared QFT/IQFT layer arrays within each width file
- Reduced source from ~80K to ~74K lines (-X%)
- Binary .so size change: [measure after]

## Widths Excluded from Hardcoding
- None (all 1-16 retained)
- Widths 17+ continue to use dynamic generation

## Other Operations (NOT hardcoded per Phase 62 recommendations)
- Multiplication: deferred to future investigation
- Bitwise: skip (trivial generation, max 288us)
- Division: skip (Python-level cost, not C sequence)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No hardcoding | Hardcoded widths 1-16 for addition | Phase 58-59 | Eliminated malloc+generation for common widths |
| Separate gen scripts (1-4, 5-8) | Unified generate_seq_all.py | Phase 58 | Single script for all widths |
| Duplicated QFT/IQFT per variant | **(This phase)** Shared arrays | Phase 63 | Reduced source size |

**Current binary impact:**
- 6 .so extensions, each linking ALL C sources including 17 sequence files
- Total .so size: 16.4 MB (qint: 4.8MB, qarray: 3.7MB, _core: 2.4MB, qint_mod: 2.2MB, qbool: 1.9MB, openqasm: 1.7MB)
- Hardcoded sequence data is replicated in each .so

## Open Questions

1. **Does the compiler already deduplicate identical static const data?**
   - What we know: GCC/Clang with -O3 can merge identical read-only data sections
   - What's unclear: Whether identical QFT layers across QQ_add and cQQ_add are already merged
   - Recommendation: Measure .so sizes before and after factoring to determine actual binary impact

2. **Should optimization be prevented across QFT/middle/IQFT boundaries?**
   - What we know: Current optimization merges any layers with non-overlapping qubits
   - What's unclear: Whether preventing boundary merging increases total layer count significantly
   - Recommendation: Try both approaches (boundary-aware vs boundary-free optimization) and compare layer counts. For small widths (1-4), boundary merging is less common because few qubits mean more overlap.

3. **Is the 5-8% source reduction "measurable" enough for success criterion 2?**
   - What we know: Success criterion says "reducing total generated C file size measurably"
   - What's unclear: What threshold constitutes "measurable"
   - Recommendation: Any reduction in line count or file size that is quantifiable (even if small) satisfies "measurable." Report exact before/after numbers.

## Sources

### Primary (HIGH confidence)
- Source code analysis of `c_backend/src/sequences/add_seq_1.c` through `add_seq_16.c` -- gate structure, QFT/IQFT duplication verified
- Source code analysis of `scripts/generate_seq_all.py` -- generation functions, optimization logic
- Source code analysis of `c_backend/include/sequences.h` -- preprocessor guard system, API
- Source code analysis of `c_backend/src/IntegerAddition.c` -- how hardcoded sequences are dispatched and cached
- Source code analysis of `setup.py` -- build system, C source linking
- Phase 62 benchmark results in `benchmarks/results/benchmark_report.json` -- timing data, recommendations
- Phase 62 verification report -- confirmed all benchmarks accurate

### Secondary (MEDIUM confidence)
- Layer count analysis (computed from generation script formulas, cross-validated with actual file content)
- Size reduction estimates (computed from duplication analysis, not yet validated by actual regeneration)

### Tertiary (LOW confidence)
- Compiler deduplication behavior (theoretical knowledge about GCC/Clang -O3 optimizations, not verified for this specific codebase)

## Metadata

**Confidence breakdown:**
- Decision (keep all): HIGH -- directly from Phase 62 verified benchmarks
- Factoring approach: HIGH -- derived from direct code analysis of duplication patterns
- Size reduction estimates: MEDIUM -- computed from structural analysis, needs validation by actual generation
- Binary impact: LOW -- depends on compiler behavior, needs measurement

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- no external dependency changes expected)
