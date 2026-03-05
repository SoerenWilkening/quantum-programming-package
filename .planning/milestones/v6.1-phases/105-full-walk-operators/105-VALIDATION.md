---
phase: 105
slug: full-walk-operators
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 105 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_chess_walk.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_chess_walk.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 105-01-01 | 01 | 1 | WALK-04 | unit (structural) | `pytest tests/python/test_chess_walk.py::TestHeightControlledCascade -x` | W0 | pending |
| 105-01-02 | 01 | 1 | WALK-05 | unit (structural) | `pytest tests/python/test_chess_walk.py::TestRA -x` | W0 | pending |
| 105-01-03 | 01 | 1 | WALK-06 | unit (structural) | `pytest tests/python/test_chess_walk.py::TestRB -x` | W0 | pending |
| 105-02-01 | 02 | 2 | WALK-07 | integration | `pytest tests/python/test_chess_walk.py::TestWalkStep -x` | W0 | pending |
| 105-02-02 | 02 | 2 | WALK-07 | unit | `pytest tests/python/test_chess_walk.py::TestAllWalkQubits -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `TestHeightControlledCascade` class in test_chess_walk.py — stubs for WALK-04
- [ ] `TestRA` class in test_chess_walk.py — stubs for WALK-05
- [ ] `TestRB` class in test_chess_walk.py — stubs for WALK-06
- [ ] `TestWalkStep` class in test_chess_walk.py — stubs for WALK-07
- [ ] `TestAllWalkQubits` class in test_chess_walk.py — stubs for WALK-07

*Existing test infrastructure (conftest.py, pytest) covers framework needs.*

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
