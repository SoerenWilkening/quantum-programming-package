---
phase: 112
slug: compile-infrastructure-optimization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 112 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest configuration in project root |
| **Quick run command** | `pytest tests/python/test_call_graph.py tests/python/test_merge.py -x -q` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_call_graph.py tests/python/test_merge.py -x -q`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 112-01-01 | 01 | 1 | COMP-03 | benchmark | `pytest tests/python/test_compile_performance.py -v -m benchmark -s` | Yes (needs extension) | ⬜ pending |
| 112-02-01 | 02 | 1 | COMP-01 | unit | `pytest tests/python/test_call_graph.py -x -q` | ✅ | ⬜ pending |
| 112-02-02 | 02 | 1 | COMP-02 | unit | `pytest tests/python/test_call_graph.py::TestBuildOverlapEdges -x -q` | ✅ | ⬜ pending |
| 112-02-03 | 02 | 1 | COMP-03 | benchmark | `pytest tests/python/test_compile_performance.py -v -m benchmark -s` | Yes (needs extension) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_compile_performance.py` — extend with qubit_set construction and overlap micro-benchmarks for COMP-03

*Existing infrastructure covers COMP-01 and COMP-02 behavioral requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profiling improvement assessment | COMP-03 | Requires human judgment on whether speedup is meaningful or overhead is negligible | Review benchmark output, compare before/after median times, document findings |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
