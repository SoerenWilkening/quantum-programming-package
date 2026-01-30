# Phase 28: Verification Framework & Init - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Reusable, parameterized test framework that builds any operation circuit, exports to OpenQASM, simulates via Qiskit, and reports clear pass/fail diagnostics. Proven working with qint initialization tests. Bug fixes and operation-specific verification suites are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Test output & diagnostics
- Compact one-liner on failure: `FAIL: add(3,5) 4-bit: expected=8, got=6`
- Summary only on failure (total passed/failed/skipped); silent summary on all-pass
- Passing runs show one line per category: `init: 256/256 passed`
- Default is continue-all (run every test); flag available to fail fast for debugging

### Parameterization strategy
- Framework auto-generates all input pairs from bit width (e.g., 4-bit = 0-15 x 0-15)
- Exhaustive testing for 1-4 bit widths, sampled for 5+ bits
- Sampling strategy for larger widths: always include edge cases (0, 1, max, max-1) plus random pairs
- Support running a single operation type in isolation (filter to specific operations)

### Test invocation & organization
- Separate files per operation category (verify_init.py, verify_arithmetic.py, verify_comparison.py, etc.)
- Files live flat in tests/ alongside existing test files
- Build on the existing v1.4 verification script -- refactor into reusable framework
- Test runner approach: Claude's discretion

### Init verification scope
- Value correctness only: initialize qint(N), measure, confirm measured value equals N
- Exhaustive for 1-4 bit widths, sampled for 5-8 bit widths (consistent with general strategy)
- Full pipeline only: Python -> C circuit -> OpenQASM -> Qiskit simulate -> check result
- Statevector (exact) simulation -- deterministic, no shot noise

### Claude's Discretion
- Test runner choice (standalone script vs pytest vs other)
- Exact sampling count for larger widths
- Internal framework API design
- Error state handling and edge case presentation

</decisions>

<specifics>
## Specific Ideas

- Build on the existing v1.4 verification script as the starting point
- One line per category on success keeps output scannable without being noisy
- Fail-fast flag useful during debugging cycles; continue-all for CI-style runs

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 28-verification-framework-init*
*Context gathered: 2026-01-30*
