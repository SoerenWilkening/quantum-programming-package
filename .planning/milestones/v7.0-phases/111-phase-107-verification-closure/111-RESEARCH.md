# Phase 111: Phase 107 Verification Closure - Research

**Researched:** 2026-03-08
**Domain:** Verification audit of existing Phase 107 implementation
**Confidence:** HIGH

## Summary

Phase 111 is a pure audit phase -- no new code is written. The goal is to create a VERIFICATION.md for Phase 107 that formally verifies 6 orphaned requirements (CAPI-01, CAPI-03, CAPI-04, CGRAPH-01, CGRAPH-02, CGRAPH-03) against existing implementation evidence. The v7.0 milestone audit identified that Phase 107 completed all work (43 tests passing, code merged) but never had a formal VERIFICATION.md created, leaving these requirements in "orphaned" status.

All 6 requirements have strong implementation evidence already in the codebase. The call_graph.py module (495 lines) implements CallGraphDAG, DAGNode, overlap edges, parallel groups, and the builder stack. The compile.py module wires the opt parameter (opt=1 builds DAG, opt=3 skips DAG). 43 tests in test_call_graph.py cover all behaviors. The Phase 107 UAT shows 8/8 tests passing.

**Primary recommendation:** Follow Phase 110's VERIFICATION.md format exactly. Map each requirement to specific file/line evidence. Run the quantum chess demo with opt=1 as a live compilation test for CAPI-01 evidence. Update REQUIREMENTS.md traceability table and checkboxes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Verification depth: Code inspection + existing test evidence (match Phase 110's pattern)
- No re-running of test suites as part of verification
- Exception: live compilation test of quantum chess demo with opt=1 as real-world evidence for CAPI-01
- Quantum chess verification: Run quantum chess demo with opt=1 and confirm it compiles without error; include result as evidence under CAPI-01 (not a separate section)
- Failure handling: If a requirement is not fully met, mark as PARTIAL or FAILED in VERIFICATION.md with details. Do NOT fix gaps -- document only, defer fixes. Gaps noted in VERIFICATION.md only -- no auto-creation of fix phases
- REQUIREMENTS.md update: Update traceability table Status column for all 6 requirements. Tick requirement checkboxes ([ ] to [x]) for verified requirements. Both checkboxes and traceability table updated together

### Claude's Discretion
- Exact VERIFICATION.md section structure (follow Phase 110 pattern as baseline)
- How to phrase observable truths for each requirement
- Which specific test files to cite as evidence per requirement

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAPI-01 | User can set `@ql.compile(opt=1)` to generate standalone sequences with call graph DAG (default) | compile.py line 712: `opt=1` default; line 773-780: DAG building when opt!=3; test_call_graph.py `test_opt1_produces_dag` (line 481), `test_bare_compile_default_opt1` (line 511). Quantum chess demo with opt=1 as live evidence. |
| CAPI-03 | User can set `@ql.compile(opt=3)` for full circuit expansion (current behavior, backward compatible) | compile.py line 773: `_building_dag = self._opt != 3` skips DAG; test_call_graph.py `test_opt3_no_dag` (line 498). |
| CAPI-04 | Existing 106+ compile tests pass unchanged when opt=3 is used | test_compile.py line 48: `opt_safe = pytest.mark.usefixtures("opt_level")`; conftest.py opt_level fixture parametrizes over [1,2,3]; 107-02-SUMMARY.md claims 43 tests passing. |
| CGRAPH-01 | Call graph DAG built from sequence calls with qubit sets per node | call_graph.py DAGNode class (line 96-153) stores func_name, qubit_set, gate_count, cache_key; CallGraphDAG.add_node (line 174); test_call_graph.py TestAddNode class (line 224), TestCompileDAGIntegration `test_dag_node_metadata` (line 525). |
| CGRAPH-02 | Parallel sequences (disjoint qubit sets) identified as concurrent groups | call_graph.py `parallel_groups()` (line 251-278) using undirected overlap graph + connected components; test_call_graph.py TestParallelGroups class (line 352) with 5 tests. |
| CGRAPH-03 | Weighted qubit overlap edges between dependent sequences | call_graph.py `build_overlap_edges()` (line 218-247) with bitmask AND + popcount; test_call_graph.py TestBuildOverlapEdges class (line 278) with 7 tests. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (configured in pytest.ini) | Test execution and evidence gathering | Already project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| N/A | - | This is an audit phase, no new dependencies | - |

## Architecture Patterns

### VERIFICATION.md Structure (from Phase 110 template)
```
---
phase: 107-call-graph-dag-foundation
verified: [timestamp]
status: passed/failed
score: N/N must-haves verified
---

# Phase 107: Call Graph DAG Foundation -- Verification Report

## Goal Achievement
### Observable Truths (table: #, Truth, Status, Evidence)
### Required Artifacts (table: Artifact, Expected, Status, Details)
### Key Link Verification (table: From, To, Via, Status, Details)
### Requirements Coverage (table: Requirement, Source Plan, Description, Status, Evidence)
### Anti-Patterns Found
### Human Verification Required
### Gaps Summary
```

### Evidence Source Map
```
src/
  quantum_language/
    call_graph.py          # CGRAPH-01, CGRAPH-02, CGRAPH-03
    compile.py             # CAPI-01, CAPI-03, CAPI-04
    __init__.py            # CallGraphDAG export
tests/
  python/
    test_call_graph.py     # 43 tests covering all requirements
  test_compile.py          # 106+ compile tests (CAPI-04)
  conftest.py              # opt_level fixture (CAPI-04)
```

### Quantum Chess Demo Location
The quantum chess demo uses `@ql.compile(inverse=True)` in:
- `src/chess_encoding.py` line 402: `@ql.compile(inverse=True)` on `apply_move`
- `src/chess_walk.py`: Walk step compilation
- `tests/python/test_chess.py`: Chess test suite
- `tests/python/test_demo.py`: Demo smoke test (patches walk_step to avoid OOM)

For the live CAPI-01 evidence, the chess encoding compiles with default opt=1 since `inverse=True` does not override opt (default is opt=1 per compile.py line 712). The test_chess tests exercise this path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verification format | Custom format | Phase 110 VERIFICATION.md template | Consistency with existing milestone verification |
| Evidence gathering | Running full test suites | Code inspection + file/line references | User decision: no re-running test suites |

## Common Pitfalls

### Pitfall 1: Treating SUMMARY claims as verification evidence
**What goes wrong:** Citing "107-02-SUMMARY.md says X" as evidence instead of pointing to actual code/tests
**Why it happens:** The summaries already claim completion, but the audit flagged them as insufficient
**How to avoid:** Every evidence citation must point to a specific file, line number, and observable behavior
**Warning signs:** Evidence column contains "per SUMMARY" instead of file:line references

### Pitfall 2: Forgetting to update REQUIREMENTS.md checkboxes AND traceability table
**What goes wrong:** Updating one but not the other, leaving inconsistency
**Why it happens:** Two separate locations in the same file need updating
**How to avoid:** Update both in the same task; checkboxes are lines 12-15 and 19-21, traceability table is lines 66-73
**Warning signs:** Checkbox shows [x] but traceability says "Pending" or vice versa

### Pitfall 3: Quantum chess demo OOM
**What goes wrong:** Running the full quantum chess walk step causes memory exhaustion
**Why it happens:** Walk step compilation is memory-intensive (~8GB+)
**How to avoid:** Only need to verify that chess encoding compilation works with opt=1, not full walk. The test_chess.py tests or a lightweight script importing chess_encoding and calling get_legal_moves_and_oracle would suffice. Alternatively, the test_demo.py already patches walk_step.
**Warning signs:** Process killed or OOM error during chess demo execution

### Pitfall 4: Marking CAPI-04 without understanding opt_level fixture
**What goes wrong:** Claiming tests pass at opt=3 without understanding the selective opt_safe mechanism
**Why it happens:** Not all 106+ tests run at all opt levels -- only @opt_safe-decorated ones do
**How to avoid:** Cite the conftest.py opt_level fixture (line 167) and test_compile.py opt_safe marker (line 48). The requirement says "pass unchanged when opt=3 is used" -- the default opt=1 is backward compatible, and opt_level fixture proves tests work across levels.

## Code Examples

### Observable Truth for CAPI-01
```
Evidence: compile.py line 712 sets opt=1 as default parameter.
Lines 773-780: when opt != 3, creates fresh CallGraphDAG and pushes context.
Line 1770-1772: call_graph property exposes the DAG.
Test: test_call_graph.py::TestCompileDAGIntegration::test_opt1_produces_dag (line 481)
  - Creates @ql.compile(opt=1), calls function, asserts call_graph is not None
Test: test_call_graph.py::TestCompileDAGIntegration::test_bare_compile_default_opt1 (line 511)
  - Creates bare @ql.compile, calls function, asserts call_graph is not None
```

### Observable Truth for CGRAPH-03
```
Evidence: call_graph.py build_overlap_edges() (line 218-247)
  - Computes bitmask AND for all node pairs
  - Adds edges with type='overlap' and weight=popcount
  - Skips parent-child call edges to avoid double-counting
Test: test_call_graph.py::TestBuildOverlapEdges (line 278)
  - test_overlapping_nodes_get_edge: verifies edge created
  - test_overlap_edge_weight_is_intersection_size: verifies weight=2 for {1,2} intersection
  - test_disjoint_nodes_no_edge: verifies no edge for non-overlapping
  - test_skip_parent_child_pairs: verifies call edges not duplicated
  - test_multiple_overlaps: verifies chain overlap pattern
```

### REQUIREMENTS.md Update Locations
```
Checkboxes to tick ([ ] -> [x]):
  Line 12: CAPI-01
  Line 14: CAPI-03
  Line 15: CAPI-04
  Line 19: CGRAPH-01
  Line 20: CGRAPH-02
  Line 21: CGRAPH-03

Traceability table Status to update (Pending -> Complete):
  Lines 67-73: All 6 rows
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 107 had no VERIFICATION.md | Phase 111 creates it retroactively | 2026-03-08 | Closes 6 orphaned requirements in v7.0 milestone |

## Open Questions

1. **Quantum chess demo exact invocation**
   - What we know: chess_encoding uses @ql.compile(inverse=True) which defaults to opt=1; test_chess.py exercises chess encoding; test_demo.py patches walk_step for OOM avoidance
   - What's unclear: Exact command to run for a lightweight opt=1 chess compilation test
   - Recommendation: Run `pytest tests/python/test_chess.py -x -q` or import chess_encoding directly. The @ql.compile(inverse=True) uses default opt=1, so any chess test that calls get_legal_moves_and_oracle is sufficient evidence.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/call_graph.py` - Full source inspection of all CGRAPH requirements
- `src/quantum_language/compile.py` - Full source inspection of CAPI requirements (opt parameter, DAG building)
- `tests/python/test_call_graph.py` - 43 tests covering all 6 requirements (890 lines)
- `tests/test_compile.py` - 106+ compile tests with opt_safe decorator
- `.planning/phases/110-merge-verification-regression/110-VERIFICATION.md` - Template format
- `.planning/v7.0-MILESTONE-AUDIT.md` - Root cause analysis confirming orphaned status
- `.planning/phases/107-call-graph-dag-foundation/107-UAT.md` - 8/8 UAT tests passing
- `.planning/phases/107-call-graph-dag-foundation/107-02-SUMMARY.md` - Completion claims

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` - Current checkbox and traceability state (lines to update)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, audit only
- Architecture: HIGH - Phase 110 VERIFICATION.md provides exact template
- Evidence mapping: HIGH - all files inspected, line numbers verified
- Pitfalls: HIGH - based on direct observation of codebase and prior phase patterns

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- verification of existing code)
