---
phase: 116
slug: walk-integration-demo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 116 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_demo.py -x -v` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_demo.py -x -v`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 116-01-01 | 01 | 1 | WALK-02 | unit | `pytest tests/python/test_chess_walk.py -x -v -k evaluate` | ❌ W0 | ⬜ pending |
| 116-01-02 | 01 | 1 | WALK-04 | integration | `pytest tests/python/test_demo.py -x -v` | ❌ W0 | ⬜ pending |
| 116-02-01 | 02 | 1 | WALK-05 | integration | `pytest tests/python/test_demo.py -x -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_demo.py` — complete rewrite (old tests depend on patched walk_step, new tests should be circuit-build-only)
- [ ] `tests/python/test_chess_walk.py` — update for new evaluate_children signature with quantum predicate

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Circuit statistics output is readable | WALK-05 | Output formatting is subjective | Run demo, verify qubit count/gate count/depth displayed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
