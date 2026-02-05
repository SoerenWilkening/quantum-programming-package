---
phase: 20-modes-and-control
plan: 03
subsystem: error-handling
tags: [python, cython, error-messages, uncomputation, developer-experience]

# Dependency graph
requires:
  - phase: 18-uncomputation
    provides: Basic uncomputation infrastructure with _check_not_uncomputed and uncompute methods
  - phase: 20-01
    provides: Option API and mode-aware __del__
provides:
  - Clear, actionable error messages for uncomputation failures
  - "Cannot [action]:" error message pattern
  - Consistent ValueError usage across uncomputation errors
affects: [20-04, future-debugging, user-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Error message pattern: 'Cannot [action]: [reason]. [suggestion]'"
    - "ValueError for all uncomputation failures"
    - "Actionable suggestions in error messages (e.g., mention .keep())"

key-files:
  created: []
  modified:
    - python-backend/qint_operations.pxi

key-decisions:
  - "Use ValueError instead of RuntimeError for all uncomputation failures"
  - "Follow 'Cannot [action]:' prefix pattern for consistency"
  - "Include actionable suggestions in error messages (mention .keep(), reference counts)"

patterns-established:
  - "Error messages start with 'Cannot [action]:' for clarity"
  - "Error messages include specific actionable suggestions"
  - "Warnings go to stderr, not stdout"

# Metrics
duration: 5min
completed: 2026-01-28
---

# Phase 20 Plan 03: Enhanced Error Messages Summary

**Clear, actionable error messages for uncomputation failures using "Cannot [action]:" pattern with ValueError**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-28T19:09:16Z
- **Completed:** 2026-01-28T19:14:33Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Enhanced _check_not_uncomputed error message with .keep() suggestion
- Updated uncompute() error messages with reference count details
- Verified _do_uncompute error handling pattern consistency
- All error messages follow "Cannot [action]:" pattern
- Consistent ValueError usage across all uncomputation failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Update _check_not_uncomputed error message** - `2783718` (feat)

**Note:** Tasks 2 and 3 were already completed as part of plan 20-02 execution, which added the .keep() method and updated the uncompute() method with enhanced error messages. The changes were already present in commits `0c48c44` and `af42be7`.

## Files Created/Modified
- `python-backend/qint_operations.pxi` - Enhanced error messages in _check_not_uncomputed, uncompute, and _do_uncompute methods

## Decisions Made

**Use ValueError instead of RuntimeError**
- Decision: Changed all uncomputation failure exceptions from RuntimeError to ValueError
- Rationale: ValueError is semantically more appropriate for invalid operations (using uncomputed qbool, uncomputing with active references)

**"Cannot [action]:" error pattern**
- Decision: Standardized all error messages to start with "Cannot [action]:"
- Rationale: Provides immediate clarity about what operation failed and why
- Examples:
  - "Cannot use qbool: already uncomputed."
  - "Cannot uncompute: qbool still in use (2 references exist)."

**Include actionable suggestions**
- Decision: Error messages include specific suggestions for how to fix the issue
- Rationale: Reduces debugging time, improves developer experience
- Examples:
  - "Create a new qbool or call .keep() to prevent automatic cleanup."
  - "Delete other references first or let automatic cleanup handle it."

**Reference count transparency**
- Decision: Show actual reference count in error messages
- Rationale: Helps users understand exactly how many references exist and what needs to be cleaned up

## Deviations from Plan

None - plan executed exactly as written.

**Note:** Tasks 2 and 3 were found to be already completed from plan 20-02. This is expected workflow overlap where .keep() addition (20-02) naturally required updating the error messages that 20-03 planned to enhance.

## Issues Encountered

None - all tasks completed smoothly. Build succeeded, verification tests passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Error message infrastructure complete and tested. Ready for:
- Plan 20-04: User documentation showing example error messages
- Future debugging: Clear error messages will reduce user support requests
- Integration testing: Error messages can be tested for expected patterns

## Verification

All verification tests passed:
- ✓ _check_not_uncomputed raises ValueError with "Cannot use qbool:" pattern
- ✓ Error message mentions .keep() suggestion
- ✓ uncompute() raises ValueError with "Cannot uncompute:" pattern
- ✓ Reference count included in error message
- ✓ Actionable suggestions provided
- ✓ Warnings go to stderr (not stdout)
- ✓ Idempotent behavior works (warning on second uncompute)

---
*Phase: 20-modes-and-control*
*Completed: 2026-01-28*
