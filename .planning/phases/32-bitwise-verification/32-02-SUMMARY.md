# Phase 32 Plan 02: Mixed-Width Bitwise, NOT Compositions, and Preservation Summary

Mixed-width AND/OR/XOR verification across adjacent width pairs, NOT-AND/NOT-OR/NOT-XOR compositions at widths 1-4, and operand preservation with per-operator calibration.

## Execution Details

| Field | Value |
|-------|-------|
| Phase | 32 |
| Plan | 02 |
| Type | execute |
| Duration | ~24 min |
| Completed | 2026-02-01 |

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Mixed-width bitwise, NOT compositions, preservation tests | a29ff51 | tests/test_bitwise_mixed.py |

## Results

**Test counts:** 1608 total
- 344 passed (300 NOT compositions + 44 preservation)
- 4 skipped (degenerate circuit preservation cases)
- 1110 xfailed (mixed-width BUG-BIT-01)
- 150 xpassed (mixed-width AND cases that accidentally produce correct results)

**Coverage:**
- Mixed-width QQ: 630 tests across (1,2), (2,3), (3,4), (4,5), (5,6) for AND/OR/XOR
- Mixed-width CQ: 630 tests same width pairs
- NOT compositions: 300 tests (NOT-AND, NOT-OR, NOT-XOR at widths 1-4)
- Operand preservation: 48 tests (AND/OR/XOR x QQ/CQ x 8 value pairs)

## Bugs Found

### BUG-BIT-01: Mixed-width bitwise operations completely broken

**Severity:** High
**Scope:** ALL mixed-width bitwise operations (AND, OR, XOR) in both QQ and CQ variants

**Manifestation A -- Qubit allocation overflow:**
- QQ AND, CQ AND, QQ OR allocate ~32K qubits for width pairs (1,2), (4,5), (5,6)
- Makes circuits unsimulatable (insufficient memory)

**Manifestation B -- Incorrect circuit logic:**
- QQ OR and QQ XOR produce wrong results for ALL tested adjacent width pairs
- QQ AND fails for ~44% of inputs at (2,3) and (3,4)
- CQ AND/OR/XOR produce wrong results when qa.width differs from classical value bit length

**Root cause:** C backend LogicOperations width-extension code does not correctly zero-extend the narrower operand or compute the result register at the correct width.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circuit builder keepalive pattern**
- **Found during:** Task 1, NOT composition tests failing
- **Issue:** circuit_builder returning plain expected value caused qint GC before OpenQASM export, injecting uncomputation gates
- **Fix:** Return `(expected, [qa, qb, _result])` tuple following established pattern from test_bitwise.py
- **Files modified:** tests/test_bitwise_mixed.py

**2. [Rule 1 - Bug] Calibration position detection for preservation**
- **Found during:** Task 1, preservation tests failing
- **Issue:** Naive left-to-right window search found coincidental bit patterns instead of actual register positions
- **Fix:** Try standard register layout first (qa rightmost, qb middle), fall back to search preferring rightmost a position
- **Files modified:** tests/test_bitwise_mixed.py

**3. [Rule 1 - Bug] Degenerate circuit handling in preservation**
- **Found during:** Task 1, CQ AND with classical value 0
- **Issue:** CQ AND(a, 0) produces 1-qubit circuit, calibration expects 6 bits
- **Fix:** Skip tests where bitstring length < calibrated position (4 cases)
- **Files modified:** tests/test_bitwise_mixed.py

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Non-strict xfail for all mixed-width tests | Some AND cases accidentally pass; strict would cause xpass failures |
| Skip (not xfail) for degenerate circuit preservation | Not a bug; CQ ops with classical 0 legitimately produce smaller circuits |
| BUG-BIT-01 covers both allocation and logic bugs | Same root cause: width-extension code in C backend |

## Success Criteria Status

- [x] tests/test_bitwise_mixed.py exists with mixed-width, NOT composition, and preservation tests
- [x] Mixed-width tested for adjacent pairs (1,2) through (5,6) for AND, OR, XOR in QQ and CQ
- [x] NOT-AND, NOT-OR, NOT-XOR produce correct results (300/300 pass)
- [x] Operand preservation confirmed for AND, OR, XOR via calibration (44/44 pass, 4 skip)
- [x] Zero hard test failures (all failures are xfail due to BUG-BIT-01)
- [x] Bug documented as BUG-BIT-01
