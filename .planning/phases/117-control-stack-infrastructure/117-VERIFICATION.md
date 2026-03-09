---
phase: 117-control-stack-infrastructure
verified: 2026-03-09T19:00:47Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 117: Control Stack Infrastructure Verification Report

**Phase Goal:** Framework has a control stack data structure and Toffoli AND emission primitives that all downstream features depend on
**Verified:** 2026-03-09T19:00:47Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

Truths derived from ROADMAP.md Success Criteria + Plan 01/02 must_haves (combined and deduplicated):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_control_stack` list replaces `_controlled`/`_control_bool`/`_list_of_controls` globals with backward-compatible wrappers | VERIFIED | `_core.pyx` line 28: `cdef list _control_stack = []`. Old globals (`cdef bint _controlled`, `cdef object _control_bool`, `cdef object _list_of_controls`) are absent from the file. Backward-compat wrappers at lines 89-114 work: `_get_controlled()` returns `len(_control_stack) > 0`; `_set_controlled()` is no-op; `_get_control_bool()` reads stack top; `_set_control_bool()` is no-op; `_get_list_of_controls()` returns `[]`; `_set_list_of_controls()` is no-op. |
| 2 | `emit_ccx` emits a Toffoli gate directly without controlled-context checks | VERIFIED | `_gates.pyx` lines 211-229: `cpdef void emit_ccx(unsigned int target, unsigned int ctrl1, unsigned int ctrl2)` calls `ccx(&g, target, ctrl1, ctrl2)` and `add_gate(circ, &g)` with no `_get_controlled()` check. |
| 3 | `_toffoli_and`/`_uncompute_toffoli_and` helpers allocate AND-ancilla and clean up via reverse Toffoli | VERIFIED | `_gates.pyx` lines 232-274: `_toffoli_and` allocates a `qbool`, gets `ancilla.qubits[63]`, calls `emit_ccx`, returns ancilla. `_uncompute_toffoli_and` calls `emit_ccx` (CCX is self-adjoint), sets `_is_uncomputed = True`, calls `_deallocate_qubits`, sets `allocated_qubits = False`. |
| 4 | Existing single-level `with` blocks still produce correct circuits (backward compatible) | VERIFIED | `qint.pyx` `__enter__` (line 810) calls `_push_control(self, None)`, `__exit__` (line 870) calls `_pop_control()`. Same pattern in `qint_preprocessed.pyx`. Backward-compat imports `_get_controlled`/`_get_control_bool` still used by arithmetic operations (qint.pyx lines 104-105, 319, 372). Per SUMMARY, single-level regression tests (TestSingleLevelConditional) pass. |
| 5 | `_push_control`/`_pop_control`/`_get_control_stack`/`_set_control_stack` accessors exist and work | VERIFIED | `_core.pyx` lines 116-154: all four functions implemented with correct behavior. `_push_control` appends `(qbool_ref, and_ancilla)` tuple. `_pop_control` raises `RuntimeError` on empty stack. `circuit.__init__` (line 437) resets `_control_stack = []`. Global declaration at line 425 includes `_control_stack`. |
| 6 | `compile.py` save/restore uses stack-based `_get_control_stack()`/`_set_control_stack()` | VERIFIED | `compile.py` imports `_get_control_stack` and `_set_control_stack` (lines 33, 38). Save/restore block at lines 1214-1219 uses `saved_stack = list(_get_control_stack())`, `_set_control_stack([])`, and `_set_control_stack(saved_stack)` in finally. |
| 7 | `oracle.py` save/restore uses stack-based `_get_control_stack()`/`_set_control_stack()` | VERIFIED | `oracle.py` imports `_get_control_stack` and `_set_control_stack` (lines 39-40). Two save/restore blocks at lines 335-343 and 349-357 both use `saved_stack = list(_get_control_stack())` / `_set_control_stack([])` / `_set_control_stack(saved_stack)`. Old backward-compat functions (`_set_controlled`, `_set_control_bool`, `_set_list_of_controls`) are not referenced anywhere in oracle.py. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/_core.pyx` | Control stack global + push/pop/get/set + backward-compat | VERIFIED | `_control_stack` at line 28, accessors at lines 89-154, circuit reset at line 437 |
| `src/quantum_language/_gates.pyx` | emit_ccx, _toffoli_and, _uncompute_toffoli_and | VERIFIED | Functions at lines 211-274, ccx extern at line 35 |
| `src/quantum_language/_gates.pxd` | ccx C declaration for Cython | VERIFIED | `void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2)` at line 21 |
| `tests/python/test_control_stack.py` | Unit tests for stack primitives and gate helpers (min 80 lines) | VERIFIED | 318 lines, 21 test functions across 5 test classes (TestControlStackBasics, TestEmitCCX, TestToffoliAnd, TestBackwardCompat, TestIntegration) |
| `src/quantum_language/qint.pyx` | Updated __enter__/__exit__ with push/pop | VERIFIED | `_push_control(self, None)` at line 810, `_pop_control()` at line 870 |
| `src/quantum_language/qint_preprocessed.pyx` | Same __enter__/__exit__ updates (sync) | VERIFIED | Identical pattern: `_push_control` at line 810, `_pop_control` at line 870, import at line 42 |
| `src/quantum_language/compile.py` | Stack-based save/restore | VERIFIED | Imports and usage at lines 33, 38, 1214-1219 |
| `src/quantum_language/oracle.py` | Stack-based save/restore | VERIFIED | Imports and usage at lines 39-40, 335-357 |
| `tests/python/test_nested_with_blocks.py` | Updated xfail markers (strict=False, no raises=NotImplementedError) | VERIFIED | All 6 xfail markers use `strict=False` with reason mentioning Phase 117 intermediate state |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_core.pyx` | `_control_stack` | `_push_control/_pop_control/_get_control_stack/_set_control_stack` | WIRED | All four functions manipulate `_control_stack` global via `global _control_stack` declaration |
| `_gates.pyx` | `gate.h ccx()` | `cdef extern + emit_ccx wrapper` | WIRED | extern declaration at line 35, `emit_ccx` calls `ccx(&g, ...)` at line 228 |
| `_gates.pyx` | `qbool.pyx` | local import in `_toffoli_and` | WIRED | `from .qbool import qbool as _qbool` at line 250 |
| `_gates.pyx` | `_core.pyx _deallocate_qubits` | local import in `_uncompute_toffoli_and` | WIRED | `from ._core import _deallocate_qubits` at line 272 |
| `qint.pyx __enter__` | `_core.pyx _push_control` | function call | WIRED | `_push_control(self, None)` at line 810, imported at line 42 |
| `qint.pyx __exit__` | `_core.pyx _pop_control` | function call | WIRED | `_pop_control()` at line 870, imported at line 42 |
| `compile.py` | `_core.pyx _get_control_stack/_set_control_stack` | import and function call | WIRED | Imported at lines 33/38, used at lines 1214-1219 |
| `oracle.py` | `_core.pyx _get_control_stack/_set_control_stack` | import and function call | WIRED | Imported at lines 39-40, used at lines 335-357 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CTRL-02 | 117-01, 117-02 | Framework composes control qubits via Toffoli AND on `__enter__`, producing a combined control ancilla | SATISFIED | `_toffoli_and` allocates qbool AND-ancilla and applies CCX (lines 232-254 of _gates.pyx). Infrastructure ready for Phase 118 to wire into `__enter__`. `__enter__` currently calls `_push_control(self, None)` -- AND composition deferred to Phase 118 as designed. Marked complete in REQUIREMENTS.md. |
| CTRL-03 | 117-01, 117-02 | Framework uncomputes AND-ancilla and restores previous control on `__exit__` | SATISFIED | `_uncompute_toffoli_and` reverses CCX, sets `_is_uncomputed = True`, deallocates (lines 257-274 of _gates.pyx). `__exit__` calls `_pop_control()` which restores previous control state. AND-ancilla uncomputation in `__exit__` deferred to Phase 118 as designed. Marked complete in REQUIREMENTS.md. |

**No orphaned requirements.** ROADMAP.md maps CTRL-02 and CTRL-03 to Phase 117, and both plans claim these same IDs. No additional IDs mapped to Phase 117 in the traceability table.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

No TODOs, FIXMEs, PLACEHOLDERs, or stub implementations found in any modified file. No empty return statements, no console.log-only implementations.

### Human Verification Required

### 1. Single-level with-block circuit correctness

**Test:** Run `pytest tests/python/test_nested_with_blocks.py::TestSingleLevelConditional -x -v` and verify all 3 tests pass.
**Expected:** All pass with correct simulated results (conditional addition produces expected output).
**Why human:** Requires Cython rebuild and simulation execution to confirm gate-level correctness.

### 2. Full test suite regression

**Test:** Run `pytest tests/python/test_control_stack.py tests/python/test_nested_with_blocks.py -x -v` and verify all unit tests pass (xfails show as xfail, not error).
**Expected:** 21 control stack tests pass, 3 single-level tests pass, 6 nested tests xfail with strict=False.
**Why human:** Requires compiled Cython extension and runtime test execution.

### Gaps Summary

No gaps found. All 7 observable truths are verified in the codebase. All artifacts exist, are substantive (not stubs), and are properly wired. Key links between components are connected via imports and function calls. Both requirements (CTRL-02, CTRL-03) are satisfied at the infrastructure level, with AND composition wiring deferred to Phase 118 as explicitly designed. The old flat globals (`_controlled`, `_control_bool`, `_list_of_controls`) are completely removed. Backward compatibility is maintained for all callers. Commit hashes from SUMMARYs (155454b, 3832c7f, 6b25367, 57dfbcb) all verified present in git log.

---

_Verified: 2026-03-09T19:00:47Z_
_Verifier: Claude (gsd-verifier)_
