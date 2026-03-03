---
phase: 104
slug: walk-register-scaffolding-local-diffusion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 104 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `pytest tests/python/test_chess_walk.py -v -x` |
| **Full suite command** | `pytest tests/python/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_chess_walk.py -v -x`
- **After every plan wave:** Run `pytest tests/python/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 104-01-01 | 01 | 1 | WALK-01 | unit | `pytest tests/python/test_chess_walk.py::TestHeightRegister -x` | ❌ W0 | ⬜ pending |
| 104-01-02 | 01 | 1 | WALK-02 | unit | `pytest tests/python/test_chess_walk.py::TestBranchRegisters -x` | ❌ W0 | ⬜ pending |
| 104-02-01 | 02 | 1 | WALK-03 | unit (circuit gen) | `pytest tests/python/test_chess_walk.py::TestDiffusion -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_chess_walk.py` — stubs for WALK-01, WALK-02, WALK-03
- [ ] No new conftest fixtures needed — `clean_circuit` from existing conftest.py suffices

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
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
