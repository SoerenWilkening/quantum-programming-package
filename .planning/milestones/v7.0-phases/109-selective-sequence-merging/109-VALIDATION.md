---
phase: 109
slug: selective-sequence-merging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 109 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=7.0 |
| **Config file** | pyproject.toml (project-level) |
| **Quick run command** | `pytest tests/python/test_merge.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_merge.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 109-01-01 | 01 | 1 | MERGE-01 | unit | `pytest tests/python/test_merge.py::test_merge_group_detection -x` | ❌ W0 | ⬜ pending |
| 109-01-02 | 01 | 1 | MERGE-02 | unit | `pytest tests/python/test_merge.py::test_gate_ordering_preserved -x` | ❌ W0 | ⬜ pending |
| 109-01-03 | 01 | 1 | MERGE-03 | integration | `pytest tests/python/test_merge.py::test_cross_boundary_cancellation -x` | ❌ W0 | ⬜ pending |
| 109-02-01 | 02 | 1 | CAPI-02 | integration | `pytest tests/python/test_merge.py::test_opt2_basic -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_merge.py` — stubs for CAPI-02, MERGE-01, MERGE-02, MERGE-03

*Existing infrastructure covers framework install (pytest in project dependencies).*

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
