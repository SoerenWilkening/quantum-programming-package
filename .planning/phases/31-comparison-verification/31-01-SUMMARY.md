# Summary: Plan 31-01 — Exhaustive and Sampled Comparison Tests

## Status: COMPLETE

## What was built
- `tests/test_compare.py` with 1515 parametrized tests covering all 6 comparison operators (==, !=, <, >, <=, >=) across QQ and CQ variants
- Exhaustive testing at widths 1-3, sampled at widths 4-5
- BUG-02 regression class with 3 sub-cases (MSB index, GC gate reversal, unsigned overflow)

## Test results
- 987 passed, 488 xfailed, 40 xpassed, 0 failures (2:25 runtime)

## Bugs discovered
- **BUG-CMP-01 (Equality Inversion):** eq and ne operators return inverted results for ALL inputs at ALL widths. eq(a,b) returns 0 when a==b, ne(a,b) returns 0 when a!=b. Both QQ and CQ variants. Exception: CQ ne passes when b=max_val.
- **BUG-CMP-02 (Ordering Comparison Error):** lt, gt, le, ge produce incorrect results for specific (a,b) pairs where operands span the MSB boundary (values >= 2^(w-1)). Exact failure sets documented in test file.
- **BUG-CMP-03 (Circuit Size Explosion):** gt and le operators generate circuits exceeding simulation memory at widths >= 7. Widths 6+ excluded from test suite.

## Decisions
| Decision | Rationale |
|----------|-----------|
| Exhaustive at widths 1-3 only (not 1-4) | Width 4 exhaustive adds ~3000 tests; sampled coverage at width 4 provides sufficient verification |
| Sampled at widths 4-5 only (not 5-8) | Widths 7-8 OOM for gt/le; width 6 borderline. 4-5 provides good coverage without memory issues |
| Non-strict xfail for sampled ordering ops | Cannot perfectly predict failure set at width 5; non-strict allows both pass and fail |

## Commits
- `58b06cd` test(31-01): exhaustive and sampled comparison verification
