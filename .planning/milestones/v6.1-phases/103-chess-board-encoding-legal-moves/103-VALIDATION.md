---
phase: 103
slug: chess-board-encoding-legal-moves
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-03
---

# Phase 103 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured) |
| **Config file** | tests/python/conftest.py (clean_circuit fixture) |
| **Quick run command** | `pytest tests/python/test_chess.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_chess.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 103-01-01 | 01 | 1 | CHESS-01 | unit | `pytest tests/python/test_chess.py::TestBoardEncoding -x` | ❌ W0 | ⬜ pending |
| 103-01-02 | 01 | 1 | CHESS-02 | unit | `pytest tests/python/test_chess.py::TestKnightMoves -x` | ❌ W0 | ⬜ pending |
| 103-01-03 | 01 | 1 | CHESS-03 | unit | `pytest tests/python/test_chess.py::TestKingMoves -x` | ❌ W0 | ⬜ pending |
| 103-01-04 | 01 | 1 | CHESS-04 | unit | `pytest tests/python/test_chess.py::TestLegalMoveFiltering -x` | ❌ W0 | ⬜ pending |
| 103-02-02 | 02 | 2 | CHESS-05 | unit + subcircuit | `pytest tests/python/test_chess.py::TestMoveOracle -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/python/test_chess.py` — created via TDD in Plan 01 Task 1 (tests written before implementation)
- No framework install needed (pytest already configured)
- No conftest changes needed (`clean_circuit` fixture already exists)

*Wave 0 satisfied by TDD pattern: Plan 01 Task 1 writes all test stubs before implementation code.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (TDD tasks create tests inline before implementation)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-03
