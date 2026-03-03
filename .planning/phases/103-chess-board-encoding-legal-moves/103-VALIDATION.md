---
phase: 103
slug: chess-board-encoding-legal-moves
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 103-02-01 | 02 | 2 | CHESS-04 | unit | `pytest tests/python/test_chess.py::TestLegalMoveFiltering -x` | ❌ W0 | ⬜ pending |
| 103-02-02 | 02 | 2 | CHESS-05 | unit + subcircuit | `pytest tests/python/test_chess.py::TestMoveOracle -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_chess.py` — stubs for CHESS-01 through CHESS-05
- No framework install needed (pytest already configured)
- No conftest changes needed (`clean_circuit` fixture already exists)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
