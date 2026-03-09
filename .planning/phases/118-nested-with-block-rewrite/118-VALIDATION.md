---
phase: 118
slug: nested-with-block-rewrite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 118 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini (project root) |
| **Quick run command** | `pytest tests/python/test_nested_with_blocks.py -v` |
| **Full suite command** | `pytest tests/python/ -v --timeout=120` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_nested_with_blocks.py -v`
- **After every plan wave:** Run `pytest tests/python/ -v --timeout=120`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 118-01-01 | 01 | 1 | CTRL-01, CTRL-05 | unit | `pytest tests/python/test_nested_with_blocks.py -v` | Exists (xfail, needs rewrite) | pending |
| 118-01-02 | 01 | 1 | CTRL-01 | unit | `pytest tests/python/test_nested_with_blocks.py::TestThreeLevelNesting -v` | W0 | pending |
| 118-01-03 | 01 | 1 | CTRL-04 | unit | `pytest tests/python/test_nested_with_blocks.py -k invert -v` | W0 | pending |
| 118-02-01 | 02 | 1 | CTRL-01 | unit | `pytest tests/python/test_nested_with_blocks.py::TestNestedWithBlocks -v` | Exists (xfail) | pending |
| 118-02-02 | 02 | 1 | CTRL-05 | integration | `pytest tests/python/ -v --timeout=120` | Exists | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] Rewrite 6 xfail tests in `test_nested_with_blocks.py` to use `qbool(True/False)` instead of comparisons (reduces qubit count from ~38 to ~6)
- [ ] Add `TestThreeLevelNesting` class with 3-level and 4-level smoke tests
- [ ] Add `~qbool` inside `with` block tests (CTRL-04 coverage)
- [ ] Add `TypeError` test for multi-bit qint in `with` block

*These must be created before or alongside implementation tasks.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
