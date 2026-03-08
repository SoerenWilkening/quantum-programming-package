# Phase 111: Phase 107 Verification Closure - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Formally verify 6 orphaned Phase 107 requirements (CAPI-01, CAPI-03, CAPI-04, CGRAPH-01, CGRAPH-02, CGRAPH-03) by creating VERIFICATION.md with pass/fail evidence for each. No new code — pure audit of existing implementation against requirements.

</domain>

<decisions>
## Implementation Decisions

### Verification depth
- Code inspection + existing test evidence (match Phase 110's pattern)
- No re-running of test suites as part of verification
- Exception: live compilation test of quantum chess demo with opt=1 as real-world evidence for CAPI-01

### Quantum chess verification
- Run quantum chess demo with opt=1 and confirm it compiles without error
- Include result as evidence under CAPI-01 (not a separate section)

### Failure handling
- If a requirement isn't fully met: mark as PARTIAL or FAILED in VERIFICATION.md with details
- Do NOT fix gaps in this phase — document only, defer fixes
- Gaps noted in VERIFICATION.md only — no auto-creation of fix phases

### REQUIREMENTS.md update
- Update traceability table Status column for all 6 requirements
- Tick requirement checkboxes ([ ] → [x]) for verified requirements
- Both checkboxes and traceability table updated together

### Claude's Discretion
- Exact VERIFICATION.md section structure (follow Phase 110 pattern as baseline)
- How to phrase observable truths for each requirement
- Which specific test files to cite as evidence per requirement

</decisions>

<specifics>
## Specific Ideas

- Follow Phase 110's VERIFICATION.md format: observable truths table, required artifacts, key link verification
- Quantum chess with opt=1 is a strong integration evidence point — user specifically requested this
- The 6 requirements map directly to Phase 107's success criteria in ROADMAP.md

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 110 VERIFICATION.md: Template pattern with observable truths table, artifact checks, key link verification
- `python-backend/quantum_language/compile.py`: Core implementation of opt parameter and call graph DAG
- `python-backend/quantum_language/call_graph.py`: CallGraphDAG, DAGNode, overlap edges, parallel groups
- `tests/test_compile.py`: 106+ compile tests with opt_safe decorator
- `tests/python/test_merge.py`: Merge tests wired to opt_level fixture

### Established Patterns
- VERIFICATION.md follows: frontmatter → goal achievement → observable truths table → required artifacts → key link verification
- Evidence cites specific file paths and line numbers
- Status uses VERIFIED / PARTIAL / FAILED

### Integration Points
- REQUIREMENTS.md traceability table: 6 rows to update (CAPI-01, CAPI-03, CAPI-04, CGRAPH-01, CGRAPH-02, CGRAPH-03)
- REQUIREMENTS.md checkboxes: 6 checkboxes to tick
- Quantum chess demo: likely in tests/ or examples/ — needs location confirmed during research

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 111-phase-107-verification-closure*
*Context gathered: 2026-03-08*
