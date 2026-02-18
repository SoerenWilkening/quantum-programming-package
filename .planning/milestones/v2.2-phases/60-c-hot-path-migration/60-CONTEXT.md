# Phase 60: C Hot Path Migration - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate top hot paths identified by profiling to execute entirely in C, eliminating Python/C boundary crossing overhead. Includes incorporating deferred CYT-04 (nogil) from Phase 57 where relevant. Does not add new features or change public API — purely internal performance optimization.

</domain>

<decisions>
## Implementation Decisions

### Migration scope
- Strictly follow profiling data: migrate the top 3 hot paths identified by fresh profiling (re-profile at start of phase to account for phases 57-59 optimizations)
- Always migrate top 3 regardless of improvement percentage — no minimum threshold to qualify
- Success measured by either per-operation OR aggregate >20% improvement (either counts)
- Include partial-C paths as candidates if profiling shows remaining boundary crossings are the bottleneck (Claude's discretion per path)

### Code approach
- Hand-written C code (not generated)
- One separate C file per migrated path (not a single hot_paths.c)
- Replace Python/Cython version entirely after verification — no fallback path kept
- Port style: Claude decides per path whether to do a faithful port or clean reimplementation based on complexity and optimization potential

### Skip criteria
- No hard blockers — always migrate top 3, work around any obstacles
- run_instruction() elimination is one optimization among many, not mandatory for every path
- Include CYT-04 (nogil) as part of this phase where it makes sense in context of C migration

### Validation approach
- Existing test suite + new targeted C-level unit tests for each migrated function
- Per-path before/after benchmarks using pytest-benchmark (statistical analysis)
- Atomic transition per path: write C, verify tests pass, remove Python code, one commit per path

</decisions>

<specifics>
## Specific Ideas

- Fresh profiling baseline at start of phase (phases 57-59 may have shifted hot paths significantly)
- CYT-04 (nogil) deferred from Phase 57 should be incorporated here
- Phase 55 benchmark infrastructure (pytest-benchmark, `make benchmark`) already available for measurement

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 60-c-hot-path-migration*
*Context gathered: 2026-02-06*
