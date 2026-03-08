---
phase: 108
slug: call-graph-analysis-visualization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 108 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_call_graph.py -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_call_graph.py -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 108-01-01 | 01 | 1 | CGRAPH-04 | unit | `pytest tests/python/test_call_graph.py::test_node_depth -v` | ❌ W0 | ⬜ pending |
| 108-01-02 | 01 | 1 | CGRAPH-04 | unit | `pytest tests/python/test_call_graph.py::test_node_t_count -v` | ❌ W0 | ⬜ pending |
| 108-01-03 | 01 | 1 | CGRAPH-05 | unit | `pytest tests/python/test_call_graph.py::test_aggregate -v` | ❌ W0 | ⬜ pending |
| 108-02-01 | 02 | 1 | VIS-01 | unit | `pytest tests/python/test_call_graph.py::test_to_dot -v` | ❌ W0 | ⬜ pending |
| 108-02-02 | 02 | 1 | VIS-02 | unit | `pytest tests/python/test_call_graph.py::test_report -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_call_graph.py` — extend existing test file with stubs for CGRAPH-04, CGRAPH-05, VIS-01, VIS-02

*Existing test infrastructure covers framework and fixtures.*

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
