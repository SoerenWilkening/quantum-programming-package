---
phase: 121
slug: chess-engine-rewrite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 121 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/python/conftest.py |
| **Quick run command** | `python examples/chess_engine.py` |
| **Full suite command** | `pytest tests/python/test_chess.py tests/python/test_compile_nested_with.py tests/python/test_call_graph.py -v --timeout=300` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python examples/chess_engine.py`
- **After every plan wave:** Run `pytest tests/python/test_chess.py tests/python/test_compile_nested_with.py tests/python/test_call_graph.py -v --timeout=300`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 121-01-01 | 01 | 1 | CHESS-02 | unit | `pytest tests/python/test_compile_dag_only.py -x -v` | ❌ W0 | ⬜ pending |
| 121-01-02 | 01 | 1 | CHESS-05 | unit | `pytest tests/python/test_call_graph.py -x -v` | ✅ | ⬜ pending |
| 121-02-01 | 02 | 2 | CHESS-01 | smoke | `python examples/chess_engine.py` | ✅ (broken) | ⬜ pending |
| 121-02-02 | 02 | 2 | CHESS-03 | smoke | `python examples/chess_engine.py` | ✅ (broken) | ⬜ pending |
| 121-02-03 | 02 | 2 | CHESS-04 | smoke | `python examples/chess_engine.py` | ✅ (broken) | ⬜ pending |
| 121-02-04 | 02 | 2 | CHESS-05 | smoke | `python examples/chess_engine.py` (prints stats) | ✅ (broken) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/python/test_compile_dag_only.py` — test that opt=1 replay does not inject gates (new)
- [ ] Smoke test: `python examples/chess_engine.py` runs to completion with stats output

*Existing infrastructure covers remaining requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Code reads like pseudocode | CHESS-01 | Subjective readability | Review `examples/chess_engine.py` — should have clear sections, nested `with` blocks, arithmetic operators, chess notation comments |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
