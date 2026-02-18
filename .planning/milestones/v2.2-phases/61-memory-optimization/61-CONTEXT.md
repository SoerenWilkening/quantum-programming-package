# Phase 61: Memory Optimization - Context

**Gathered:** 2026-02-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce memory allocation overhead in gate creation paths based on profiling data. Profile malloc patterns with memray, optimize gate_t and sequence_t allocation if warranted, and confirm throughput and peak memory improvements. This phase does NOT add new functionality — it makes existing operations faster and lighter.

</domain>

<decisions>
## Implementation Decisions

### Profiling scope
- Use **memray** for memory profiling (already in Phase 55 infrastructure)
- Profile **both** targeted hot paths (8-bit add/mul/xor) AND end-to-end circuit generation
- Profile at **three widths**: 8-bit, 16-bit, and 32-bit to reveal scaling behavior
- 8-bit = common case, 16-bit = largest hardcoded, 32-bit = dynamic generation path
- **Save baseline + optimized** profiling snapshots as persistent artifacts for comparison

### Pooling strategy
- **Claude's discretion** on pool type (arena vs free-list) — decide based on profiling evidence of gate_t lifetime patterns
- **Single-threaded only** — no locking overhead, circuit generation is currently single-threaded
- **Dynamic growth** — pool grows as needed with no artificial cap, overflow not a concern
- **Reset per call** — pool is cleared after each operation completes for simpler lifetime management

### Optimization targets
- Priority: **highest impact first** — let profiling data determine which malloc sites to optimize
- **Include sequence_t allocation path** alongside gate_t in optimization scope
- **gate_t struct layout changes acceptable** if they help — no need to preserve current layout for its own sake
- No specific known pain points — let profiling discover the bottlenecks without preconceptions
- If profiling shows malloc is NOT a significant bottleneck (<5% of time): **still take easy wins** (e.g., stack allocation for small sequences) rather than skipping entirely

### Success thresholds
- **10% benefit means 10% faster throughput** — operations per second improvement, not just allocation count
- Optimize for **both throughput AND peak memory** — especially important for large circuits (16-bit, 32-bit)
- Compare final benchmarks against **Phase 60 baseline** (post hot-path migration) to show incremental improvement

### Claude's Discretion
- Pool type selection (arena vs free-list) based on profiling evidence
- Specific malloc sites to optimize — driven by profiling data
- Whether to use stack allocation, pre-allocation, or pooling for each bottleneck
- Exact profiling scripts and memray configuration
- Number of plans needed based on what profiling reveals

</decisions>

<specifics>
## Specific Ideas

- Three-width profiling (8, 16, 32-bit) to reveal how allocation patterns scale with width
- Save profiling artifacts in the same style as Phase 60 baseline JSON
- Even if profiling shows memory isn't a major bottleneck, look for easy wins like stack allocation for small, fixed-size sequences

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 61-memory-optimization*
*Context gathered: 2026-02-08*
