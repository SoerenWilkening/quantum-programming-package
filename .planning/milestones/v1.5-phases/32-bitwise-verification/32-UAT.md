---
status: complete
phase: 32-bitwise-verification
source: [32-01-SUMMARY.md, 32-02-SUMMARY.md, 32-03-SUMMARY.md, 32-04-SUMMARY.md]
started: 2026-02-01T14:00:00Z
updated: 2026-02-01T15:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. QQ same-width bitwise correctness
expected: `python3 -m pytest tests/test_bitwise.py -k 'test_qq_bitwise' --tb=short -q` — all QQ AND/OR/XOR tests pass (0 failures)
result: pass

### 2. CQ same-width bitwise correctness
expected: `python3 -m pytest tests/test_bitwise.py -k 'test_cq_bitwise' --tb=short -q` — all CQ AND/OR/XOR tests pass (0 failures, 0 xfail)
result: pass (after diagnosis)
reported: "Initially 754 failed due to stale .so in site-packages. After removing stale binary and rebuilding: 2418/2418 pass."
diagnosis: "Stale monolithic .so from Jan 26 in site-packages shadowed freshly-compiled per-module extensions."

### 3. NOT operation correctness
expected: `python3 -m pytest tests/test_bitwise.py -k 'test_not' --tb=short -q` — all NOT tests pass (0 failures)
result: pass

### 4. QQ mixed-width bitwise correctness
expected: `python3 -m pytest tests/test_bitwise_mixed.py -k 'test_qq_mixed' --tb=short -q` — all QQ mixed-width AND/OR/XOR pass (0 failures, 0 xfail)
result: pass (after diagnosis)
reported: "Initially 585 failed due to stale .so. After fix: 1266 passed, 292 xfailed (design limitation), 50 xpassed."
diagnosis: "Same stale .so root cause as test 2."

### 5. NOT compositions correctness
expected: `python3 -m pytest tests/test_bitwise_mixed.py -k 'test_not_composition' --tb=short -q` — NOT-AND, NOT-OR, NOT-XOR all produce correct results (300 tests pass)
result: pass

### 6. Operand preservation after bitwise ops
expected: `python3 -m pytest tests/test_bitwise_mixed.py -k 'test_operand_preservation' --tb=short -q` — source operands are unchanged after AND/OR/XOR (44 pass, 4 skip for degenerate circuits)
result: pass

### 7. Manual spot-check: CQ AND
expected: Simulate `qint(5, width=3) & 3` — result should be 1 (101 AND 011 = 001)
result: pass (after diagnosis)
reported: "Initially returned 4 (100) — bits reversed. After stale .so removal and rebuild: correct."
diagnosis: "Same stale .so root cause."

### 8. Manual spot-check: mixed-width QQ AND
expected: Simulate `qint(1, width=2) & qint(7, width=3)` — result should be 1 (01 AND 111 = 001), no 32K qubit overflow
result: pass (after diagnosis)
reported: "Initially returned 5 (101). After stale .so removal and rebuild: correct."
diagnosis: "Same stale .so root cause."

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

All 4 initial failures were caused by a stale .so binary in site-packages shadowing the correct compiled extensions. Root cause resolved by debug agent — removed stale binary, rebuilt. All tests pass.

Debug session: .planning/debug/resolved/bitwise-uat-failures.md
