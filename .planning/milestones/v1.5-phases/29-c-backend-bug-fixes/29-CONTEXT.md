# Phase 29: C Backend Bug Fixes - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix four known C backend bugs: subtraction underflow (BUG-01), less-or-equal comparison (BUG-02), multiplication segfault (BUG-03), and QFT addition with nonzero operands (BUG-04). BUG-05 (circuit() state reset) is explicitly excluded. No new features or refactoring beyond what's needed for the fixes.

</domain>

<decisions>
## Implementation Decisions

### Fix ordering & dependencies
- Fix bugs in dependency order — analyze which bugs share root causes and fix foundational ones first
- One commit per bug, even if two bugs share a root cause — separate commits for independent trackability and revertability
- Each fix must not regress any existing tests — no regressions allowed
- BUG-05 (circuit() state reset) is excluded entirely from this phase

### Fix scope & approach
- Minimal targeted patches — change only what's necessary to fix each bug, smallest possible diff
- Memory allocation changes acceptable for multiplication segfault (BUG-03) if scoped to the multiplication code path only
- Fix wherever the bug actually is — if root cause is Python-side rather than C backend, fix it in Python
- QFT addition (BUG-04) must be fixed, not replaced — no fallback to ripple-carry addition

### Validation strategy
- Both C-level unit tests AND full pipeline verification (Phase 28 framework) for each fix
- Test coverage: reproduce the specific failing case plus a few nearby cases — exhaustive testing deferred to Phases 30-31
- Bug fix tests in separate subdirectory (e.g., tests/bugfix/)
- One test file per bug: test_bug01_subtraction.py, test_bug02_comparison.py, etc.

### Edge case handling
- New bugs discovered during fixing: fix if small and in the same code area, otherwise document as BUG-06+ and defer
- Partial fixes acceptable — if a bug is mostly fixed but not all cases, document remaining cases and move on
- Test through the path where the bug was originally observed (not necessarily both C and OpenQASM paths)

### Claude's Discretion
- Exact dependency ordering between the four bugs
- C-level test framework choice and structure
- Specific debugging approach for each bug

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-c-backend-bug-fixes*
*Context gathered: 2026-01-30*
