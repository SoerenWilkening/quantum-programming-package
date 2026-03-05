---
phase: 106
slug: demo-scripts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 106 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_demo.py -v -x` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_demo.py -v -x`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 106-01-01 | 01 | 1 | DEMO-01 | smoke | `pytest tests/python/test_demo.py::test_demo_main -x` | No - W0 | pending |
| 106-02-01 | 02 | 1 | DEMO-02 | smoke | `pytest tests/python/test_demo.py::test_comparison_main -x` | No - W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_demo.py` -- smoke tests for DEMO-01 and DEMO-02

*Existing infrastructure covers all framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Output readability | DEMO-01 | Subjective formatting quality | Run `python src/demo.py` and visually inspect output |
| Comparison table alignment | DEMO-02 | Visual formatting check | Run `python src/chess_comparison.py` and inspect table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
