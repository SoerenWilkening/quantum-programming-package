---
phase: 110
slug: merge-verification-regression
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 110 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed) |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `pytest tests/python/test_merge_equiv.py -x -q` |
| **Full suite command** | `pytest tests/test_compile.py tests/python/test_merge.py tests/python/test_merge_equiv.py -q --tb=short` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/python/test_merge_equiv.py -x -q`
- **After every plan wave:** Run `pytest tests/test_compile.py tests/python/test_merge.py tests/python/test_merge_equiv.py -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 110-01-01 | 01 | 1 | MERGE-04a | integration | `pytest tests/python/test_merge_equiv.py::test_add_equiv -x` | W0 | pending |
| 110-01-02 | 01 | 1 | MERGE-04b | integration | `pytest tests/python/test_merge_equiv.py::test_mul_equiv -x` | W0 | pending |
| 110-01-03 | 01 | 1 | MERGE-04c | integration | `pytest tests/python/test_merge_equiv.py::test_grover_equiv -x` | W0 | pending |
| 110-01-04 | 01 | 1 | MERGE-04f | unit | `pytest tests/python/test_merge_equiv.py::TestParametricOptInteraction -x` | W0 | pending |
| 110-02-01 | 02 | 1 | MERGE-04d | regression | `pytest tests/test_compile.py -q --tb=short` | Exists | pending |
| 110-02-02 | 02 | 1 | MERGE-04e | regression | `pytest tests/python/test_merge.py -q --tb=short` | Exists | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_merge_equiv.py` — new file for statevector equivalence tests (MERGE-04a,b,c,f)
- [ ] Opt-level parametrization fixture in conftest (MERGE-04d,e)
- [ ] xfail markers for 15 pre-existing test_compile.py failures

*Existing infrastructure (conftest.py, verify_helpers.py, sim_backend.py) covers shared fixtures and helpers.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
