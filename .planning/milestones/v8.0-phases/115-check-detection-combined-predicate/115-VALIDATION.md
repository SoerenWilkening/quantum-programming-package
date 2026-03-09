---
phase: 115
slug: check-detection-combined-predicate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 115 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in tests/python/conftest.py) |
| **Config file** | tests/python/conftest.py (clean_circuit fixture) |
| **Quick run command** | `pytest tests/python/test_chess_predicates.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_chess_predicates.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 115-01-01 | 01 | 1 | PRED-03 | unit (statevector 2x2) | `pytest tests/python/test_chess_predicates.py::TestCheckDetection -x` | ❌ W0 | ⬜ pending |
| 115-01-02 | 01 | 1 | PRED-03 | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestCheckDetectionClassical -x` | ❌ W0 | ⬜ pending |
| 115-01-03 | 01 | 1 | PRED-03 | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestCheckDetection::test_adjoint_roundtrip -x` | ❌ W0 | ⬜ pending |
| 115-02-01 | 02 | 1 | PRED-04 | unit (statevector 2x2) | `pytest tests/python/test_chess_predicates.py::TestCombinedPredicate -x` | ❌ W0 | ⬜ pending |
| 115-02-02 | 02 | 1 | PRED-04 | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestCombinedClassical -x` | ❌ W0 | ⬜ pending |
| 115-XX-01 | 01/02 | 1 | PRED-03/04 | smoke (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestScalingPhase115 -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_chess_predicates.py::TestCheckDetection` — stubs for PRED-03
- [ ] `tests/python/test_chess_predicates.py::TestCombinedPredicate` — stubs for PRED-04
- [ ] `tests/python/test_chess_predicates.py::TestScalingPhase115` — 8x8 circuit-only smoke tests
- [ ] Classical equivalence helpers for check detection

*Existing test infrastructure (pytest, conftest.py, clean_circuit fixture) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
