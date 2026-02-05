# Phase 37: Division Overflow Fix - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the division algorithm so it produces correct results for all operand combinations, particularly when divisor >= 2^(w-1). The bug manifests as "divisor << bit_pos" overflowing the register width, interacting with comparison operator issues. This phase fixes division correctness — it does not add new division features or change the division API.

</domain>

<decisions>
## Implementation Decisions

### Fix strategy
- Start with minimal patch — preserve existing algorithm structure
- If minimal patch won't work cleanly, escalate to rework is acceptable
- Fix may touch comparison operators if they are part of the root cause (not limited to division code only)
- Preserve current ancilla qubit count — no additional ancillas for the fix

### Test coverage
- Fix existing xfail-marked tests — no new exhaustive test suites needed
- Validate at 4-bit width only (matching existing tests)
- If fix reveals additional failing cases not currently marked xfail, fix them too (same root cause)
- Verify division-by-zero behavior is unchanged after the fix

### Regression scope
- Run division tests after fix (not full comparison suite — that's Phase 41)
- Run modular arithmetic tests (mod, reduce_mod) to check for shared-code regressions
- Check if the 2 known xfail tests for dirty ancilla in gt/le happen to be resolved by the fix — if so, remove xfail; otherwise leave
- Regression policy on previously-passing tests: Claude's discretion (case-by-case evaluation)

### Width handling
- Fix targets 4-bit division specifically
- If the fix naturally covers mixed-width division (e.g., 8-bit / 4-bit), include it; don't add special handling
- Fix approach: prevent the overflow by restructuring loop bounds (calculate max safe iteration count upfront)
- Do not use runtime guards — restructure loop bounds to avoid the problematic shift entirely

### Claude's Discretion
- Whether to escalate from minimal patch to rework (based on root cause analysis)
- Exact loop bound calculation approach
- Whether regression in previously-passing tests is acceptable (case-by-case)
- How comparison operator changes (if needed) are scoped

</decisions>

<specifics>
## Specific Ideas

- The overflow happens when `divisor << bit_pos` exceeds register width — fix by restructuring loop bounds rather than handling overflow
- Bug description mentions "comparison overflow or MSB leak" as contributing factors
- Approach: calculate maximum safe iteration count upfront, skip iterations where shift would overflow

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 37-division-overflow-fix*
*Context gathered: 2026-02-02*
