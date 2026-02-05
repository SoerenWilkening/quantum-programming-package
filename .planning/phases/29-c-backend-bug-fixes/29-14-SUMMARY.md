---
phase: 29-c-backend-bug-fixes
plan: 14
status: skipped
result: skipped
deviation: true
commits: []
files_modified: []
subsystem: multiplication
tags: ["QQ_mul", "BUG-03", "skipped"]
duration: 0min
completed: 2026-01-31
---

# Phase 29 Plan 14: Deeper QQ_mul Algorithm Investigation — SKIPPED

**Skipped: Plan 29-13 verification showed BUG-03 target qubit fix was incorrect and caused regressions. Changes reverted.**

## Reason for Skipping

Plan 29-13 applied the BUG-03 target qubit mapping changes (reversing `bits-i-1` to `i` in QQ_mul/cQQ_mul) and ran verification. Results showed:

1. **Multiplication got WORSE:** 1*1 returned 2 (was 1), 0*5 memory-exploded (was 0)
2. **BUG-05 memory explosion escalated:** 9 previously-working tests now fail with memory errors
3. **No improvement in any bug category**

The regression commit (6328d19) was reverted to restore baseline (14/19 passing tests when run in isolation).

## Plan 14 Premise Was Invalid

Plan 14 was designed to "investigate deeper if non-trivial products still fail after 29-13 rebuild." Since the 29-13 changes were themselves harmful and reverted, there is no basis for Plan 14's investigation path.

## Current State After Revert

- BUG-01: 5/5 PASS (when tests run in isolation — BUG-05 causes failures in combined pytest run)
- BUG-02: 0/2 FAIL (comparison still broken, blocked by BUG-05)
- BUG-03: 2/5 PASS (trivial cases work, non-trivial products wrong — same as 29-12 baseline)
- BUG-04: 7/7 PASS (stable)

## Remaining Gaps

BUG-02 and BUG-03 remain unfixed. Both are blocked or complicated by BUG-05 (circuit cache pollution). Fixing BUG-05 is a prerequisite for reliable verification and likely for fixing BUG-02 comparison logic.

---
*Phase: 29-c-backend-bug-fixes*
*Completed: 2026-01-31*
