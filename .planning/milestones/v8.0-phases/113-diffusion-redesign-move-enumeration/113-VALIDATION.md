---
phase: 113
slug: diffusion-redesign-move-enumeration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 113 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest runs from project root |
| **Quick run command** | `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 113-01-01 | 01 | 0 | WALK-01 | unit | `pytest tests/python/test_move_table.py -x` | ❌ W0 | ⬜ pending |
| 113-01-02 | 01 | 0 | WALK-01 | unit | `pytest tests/python/test_move_table.py::test_table_sizes -x` | ❌ W0 | ⬜ pending |
| 113-01-03 | 01 | 0 | WALK-01 | unit | `pytest tests/python/test_move_table.py::test_offset_correctness -x` | ❌ W0 | ⬜ pending |
| 113-02-01 | 02 | 0 | WALK-03 | integration | `pytest tests/python/test_counting_diffusion.py::test_equivalence_d2 -x` | ❌ W0 | ⬜ pending |
| 113-02-02 | 02 | 0 | WALK-03 | integration | `pytest tests/python/test_counting_diffusion.py::test_equivalence_d3 -x` | ❌ W0 | ⬜ pending |
| 113-02-03 | 02 | 0 | WALK-03 | integration | `pytest tests/python/test_counting_diffusion.py::test_reflection -x` | ❌ W0 | ⬜ pending |
| 113-02-04 | 02 | 1 | WALK-03 | regression | `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x` | ✅ | ⬜ pending |
| 113-02-05 | 02 | 1 | WALK-03 | unit | `pytest tests/python/test_counting_diffusion.py::test_gate_count_linear -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_move_table.py` — stubs for WALK-01 (move enumeration table correctness)
- [ ] `tests/python/test_counting_diffusion.py` — stubs for WALK-03 (counting circuit equivalence, reflection, gate count)

*Existing infrastructure covers regression requirements (test_walk_variable.py, test_chess_walk.py).*

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
