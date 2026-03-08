---
phase: 114
slug: core-quantum-predicates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 114 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed, configured in conftest.py) |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_chess_predicates.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_chess_predicates.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 114-01-01 | 01 | 0 | PRED-01, PRED-02, PRED-05 | unit stubs | `pytest tests/python/test_chess_predicates.py -x` | No - W0 | ⬜ pending |
| 114-02-01 | 02 | 1 | PRED-01 | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestPieceExists -x` | No - W0 | ⬜ pending |
| 114-02-02 | 02 | 1 | PRED-02 | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestNoFriendlyCapture -x` | No - W0 | ⬜ pending |
| 114-02-03 | 02 | 1 | PRED-05 | unit (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestCompileInverse -x` | No - W0 | ⬜ pending |
| 114-02-04 | 02 | 1 | PRED-01, PRED-02 | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestClassicalEquivalence -x` | No - W0 | ⬜ pending |
| 114-02-05 | 02 | 1 | PRED-01, PRED-02 | smoke (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestScaling -x` | No - W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_chess_predicates.py` — stubs for PRED-01, PRED-02, PRED-05
- [ ] No new conftest fixtures needed (clean_circuit already exists)
- [ ] No new framework installs needed

*Existing infrastructure covers framework and fixture needs.*

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
