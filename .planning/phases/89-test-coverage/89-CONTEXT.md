# Phase 89: Test Coverage - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure all bugs fixed in milestone v4.1 (Phases 82-88) have regression tests, close coverage gaps identified during the milestone, and integrate C backend tests into the pytest test suite. This phase does NOT add new features or fix additional bugs — it strengthens the test harness for what was already delivered.

</domain>

<decisions>
## Implementation Decisions

### xfail Conversion Scope
- Convert xfails ONLY for bugs actually fixed in Phases 82-88 (optimizer fixes, QFT addition fixes, scope/segfault fixes, etc.)
- Leave known architectural limitations as xfail (QFT division at widths 3+, BK CLA not implemented, BUG-DIV-02, etc.) — these are still broken
- When removing xfail markers, preserve the original bug context as a brief docstring/comment for regression tracking
- Just remove the xfail decorator/call — existing test assertions are sufficient, no need to strengthen them
- If a supposedly-fixed xfail still fails when unmarked: re-mark as xfail with a note flagging it as a regression/incomplete fix; don't block the test suite

### C Test Integration
- Compile C tests on-the-fly from source within the pytest subprocess wrapper (no dependency on pre-built CMake binaries)
- Wrap ALL C tests in tests/c/ — test_allocator_block, test_reverse_circuit, test_comparison, and hot-path tests
- Show stdout + stderr only on failure; clean output on success
- If gcc/cc is not found, pytest.skip() the C tests with a clear warning message — don't block Python-only developers

### Coverage Measurement
- Use pytest-cov for Python coverage measurement
- Python code only (python-backend/) — no C coverage via gcov
- Establish baseline measurement first, then success = any measurable increase after adding new tests
- Local dev command only for now — no CI integration in this phase

### Nested With-Block Tests
- Test 2 levels deep: with-block inside with-block (quantum conditional inside quantum conditional)
- Test arithmetic + assignment operations inside nested conditionals
- Verify both true-path and false-path branches at each nesting level
- Use small qubit widths (2-3 bit QInts) to stay safely under the 17-qubit simulation limit

### Claude's Discretion
- Exact test file organization and naming
- Which specific bugs from Phases 82-88 map to which xfail markers (requires code analysis)
- Circuit reset test design details
- pytest-cov configuration options

</decisions>

<specifics>
## Specific Ideas

- 17-qubit max and 4-thread max for all Qiskit simulations (project-wide constraint)
- C test wrapper should be self-contained — compile, run, check exit code, capture output
- Coverage baseline should be measured before any new tests are added in this phase

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 89-test-coverage*
*Context gathered: 2026-02-24*
