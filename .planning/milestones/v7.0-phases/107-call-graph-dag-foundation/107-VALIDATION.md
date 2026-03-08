---
phase: 107
slug: call-graph-dag-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 107 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in pytest.ini) |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/python/test_call_graph.py -x -q` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_call_graph.py -x -q`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 107-01-01 | 01 | 1 | CAPI-01 | unit | `pytest tests/python/test_call_graph.py::test_opt1_produces_dag -x` | Wave 0 | pending |
| 107-01-02 | 01 | 1 | CAPI-03 | unit | `pytest tests/python/test_call_graph.py::test_opt3_backward_compat -x` | Wave 0 | pending |
| 107-01-03 | 01 | 1 | CAPI-04 | regression | `pytest tests/python/ -v --ignore=tests/python/test_call_graph.py` | Existing | pending |
| 107-02-01 | 02 | 1 | CGRAPH-01 | unit | `pytest tests/python/test_call_graph.py::test_dag_node_metadata -x` | Wave 0 | pending |
| 107-02-02 | 02 | 1 | CGRAPH-02 | unit | `pytest tests/python/test_call_graph.py::test_parallel_groups -x` | Wave 0 | pending |
| 107-02-03 | 02 | 1 | CGRAPH-03 | unit | `pytest tests/python/test_call_graph.py::test_overlap_edges -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_call_graph.py` — stubs for CAPI-01, CAPI-03, CGRAPH-01, CGRAPH-02, CGRAPH-03
- [ ] No framework install needed (pytest already configured)
- [ ] No conftest changes needed (existing conftest.py sufficient)

*Existing infrastructure covers regression testing (CAPI-04).*

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
