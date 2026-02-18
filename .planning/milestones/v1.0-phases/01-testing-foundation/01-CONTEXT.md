# Phase 1: Testing Foundation - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish characterization tests and developer tooling before any refactoring begins. This includes test suites capturing current behavior, memory checking integration (Valgrind/ASan), and pre-commit hooks for code quality. The tests document what exists today — bug fixes and behavior changes happen in later phases.

</domain>

<decisions>
## Implementation Decisions

### Test Coverage Scope
- Test all existing operations (every qint/qbool operation gets a characterization test)
- Document current behavior, even if buggy — bugs get fixed in later phases
- Default to testing final results only; optional flag to also verify circuit structure (gate counts, depth, qubit usage)
- Minimal edge case coverage — typical cases now, edge cases can come later

### Test Output Format
- Verbose output by default — show each test name, pass/fail, timing
- Failures display expected vs actual diff (side by side comparison)
- Per-test timing information to catch performance regressions
- JUnit XML output for CI integration (GitHub Actions, Jenkins, etc.)

### Memory Check Workflow
- Memory checks via separate command (e.g., `make memtest`), not on every test run
- Fail on memory leaks only — warnings are informational
- Both ASan and Valgrind available: ASan for fast checks during development, Valgrind for deep analysis

### Pre-commit Behavior
- Block commits on: lint errors AND quick test failures
- Auto-fix formatting/simple lint issues and stage the fixes
- Check both Python (Ruff) and C code (clang-format)
- Bypass via standard `--no-verify` flag when needed

### Claude's Discretion
- Memory check output detail level (file:line vs full stack traces) — pick appropriate level for each tool
- Specific Ruff rules and clang-format configuration
- Which tests qualify as "quick" for pre-commit
- Test file organization and naming conventions

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for pytest and pre-commit tooling.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-testing-foundation*
*Context gathered: 2026-01-25*
