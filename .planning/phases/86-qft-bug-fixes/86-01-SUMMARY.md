---
phase: 86-qft-bug-fixes
plan: 01
subsystem: qft-addition
tags: [qft, addition, mixed-width, zero-extension, bug-fix]

requires: []
provides:
  - Mixed-width QFT addition zero-extension in qint_arithmetic.pxi
  - Correct results for all width combinations up to 8 bits
affects: [tests/test_add.py]

tech-stack:
  added: []
  patterns: [zero-extend-narrower-operand]

key-files:
  created:
    - tests/test_add.py (mixed-width test cases added)
  modified:
    - src/quantum_language/qint_arithmetic.pxi

key-decisions:
  - "Zero-extend narrower operand at Python level before passing to C hot_path_add_qq"
  - "Fix applied to __add__, __radd__, __sub__, __rsub__ for QQ path only (CQ unaffected)"
  - "C-level QQ_add left unchanged -- operates correctly when both operands have same width"

patterns-established:
  - "Width normalization before C dispatch: pad narrower qint to result_width via XOR copy"

requirements-completed: [BUG-04]

duration: ~15min
completed: 2026-02-24
---

# Plan 86-01: Fix mixed-width QFT addition (BUG-04) Summary

**Zero-extend narrower operand in Python-level __add__/__sub__ to match C QQ_add expectations**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-24
- **Completed:** 2026-02-24
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed mixed-width QFT addition: narrower operand zero-extended to result_width before C dispatch
- Applied same fix to __add__, __radd__, __sub__, __rsub__ for QQ operand paths
- Added mixed-width test cases to test_add.py covering off-by-one and max-asymmetry width combinations
- All same-width addition tests continue to pass (zero regressions)

## Task Commits

1. **Task 1 + Task 2: Fix + verification** - `c764932` (fix)

## Files Created/Modified
- `src/quantum_language/qint_arithmetic.pxi` - Zero-extend narrower operand in QQ add/sub
- `tests/test_add.py` - Mixed-width addition test cases

## Decisions Made
- Fix at Python level (zero-extend before C call) rather than modifying C hot_path_add_qq
- CQ path unaffected since CQ_add only requires target register width

## Deviations from Plan
None.

## Issues Encountered
None.

## User Setup Required
None.

---
*Phase: 86-qft-bug-fixes*
*Completed: 2026-02-24*
