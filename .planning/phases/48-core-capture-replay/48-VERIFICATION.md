---
phase: 48-core-capture-replay
verified: 2026-02-04T13:35:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 48: Core Capture-Replay Verification Report

**Phase Goal:** Users can decorate a quantum function with `@ql.compile` and call it multiple times with different quantum arguments, getting correct results from cached gate replay with qubit remapping

**Verified:** 2026-02-04T13:35:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A function decorated with `@ql.compile` produces the same circuit output as the undecorated version on first call | ✓ VERIFIED | Tests `test_first_call_matches_undecorated_gate_count` and `test_first_call_matches_undecorated_addition` pass. CompiledFunc._capture() executes function normally, gates flow to circuit as usual. |
| 2 | Calling the compiled function a second time with different qint arguments replays gates onto the new qubits (no re-execution of the function body) | ✓ VERIFIED | Tests `test_replay_no_reexecution`, `test_replay_targets_new_qubits`, and `test_replay_same_gate_count` pass. Side-effect counter proves function body NOT executed on replay. |
| 3 | The returned qint/qbool from a compiled function is usable in subsequent quantum operations | ✓ VERIFIED | Tests `test_return_value_usable_in_place`, `test_return_value_usable_new_qint`, and `test_replay_return_value_usable` pass. Return values constructed with proper ownership metadata (`allocated_qubits=True`, `operation_type='COMPILED'`). |
| 4 | Calling with different classical parameter values or different qint widths triggers re-capture (separate cache entries) | ✓ VERIFIED | Tests `test_different_widths_recapture`, `test_different_widths_different_gate_counts`, and `test_different_classical_args_recapture` pass. Cache key includes `(tuple(classical_args), tuple(widths))`. |
| 5 | Creating a new circuit via `ql.circuit()` invalidates the compilation cache | ✓ VERIFIED | Tests `test_circuit_reset_clears_cache` and `test_circuit_reset_replay_after_recapture` pass. Hook registered via `_register_cache_clear_hook()`, fires in `circuit.__init__()` line 282. |

**Score:** 5/5 truths verified

### Required Artifacts (Plan 48-01: Cython Infrastructure)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/_core.pyx` | extract_gate_range, inject_remapped_gates, layer_floor helpers, allocate_qubit, cache-clear hook | ✓ VERIFIED | Lines 646-694 (`extract_gate_range`), 727-776 (`inject_remapped_gates`), 779-805 (layer_floor helpers), 808-824 (`_allocate_qubit`), 828-851 (cache-clear hooks). All substantive implementations following C backend patterns. |
| `src/quantum_language/_core.pxd` | gate_t field access declarations | ✓ VERIFIED | gate_t fields accessible (Gate, Target, GateValue, NumControls, Control, large_control). circuit_s expanded with sequence and used_gates_per_layer. |

**Score:** 2/2 artifacts verified

### Required Artifacts (Plan 48-02: Python Decorator)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/compile.py` | CompiledFunc, CompiledBlock, compile decorator, virtual qubit mapping, cache management | ✓ VERIFIED | 447 lines (exceeds 150 min). Contains `CompiledFunc` class (lines 209+), `CompiledBlock` class (lines 65+), `compile()` decorator (line 404+), `_build_virtual_mapping()` (lines 115+), `_build_return_qint()` (lines 165+). All substantive implementations. |
| `src/quantum_language/__init__.py` | Public API: ql.compile | ✓ VERIFIED | Line 49: `from .compile import compile`, Line 179: `"compile"` in `__all__`. |
| `tests/test_compile.py` | Tests for all 5 success criteria | ✓ VERIFIED | 584 lines (exceeds 100 min). 22 tests covering: SC1 (2 tests), SC2 (3 tests), SC3 (3 tests), SC4 (3 tests), SC5 (2 tests), plus 9 additional tests for edge cases. All pass. |

**Score:** 3/3 artifacts verified

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `compile.py` | `_core.pyx` | Import extract_gate_range, inject_remapped_gates, helpers | ✓ WIRED | Lines 26-34 in compile.py import all required functions. Verified importable via Python test. |
| `compile.py` | `_core.pyx` | extract_gate_range called in _capture | ✓ WIRED | Line 314: `raw_gates = extract_gate_range(start_layer, end_layer)` in CompiledFunc._capture() |
| `compile.py` | `_core.pyx` | inject_remapped_gates called in _replay | ✓ WIRED | Line 378: `inject_remapped_gates(block.gates, virtual_to_real)` in CompiledFunc._replay() |
| `compile.py` | `_core.pyx` | layer_floor saved/restored in _replay | ✓ WIRED | Lines 373-375: `saved_floor = _get_layer_floor()`, `_set_layer_floor(start_layer)`. Line 382: `_set_layer_floor(saved_floor)`. |
| `compile.py` | `_core.pyx` | _allocate_qubit called for ancillas | ✓ WIRED | Line 370: `virtual_to_real[v] = _allocate_qubit()` in _replay() for internal qubits. |
| `compile.py` | `_core.pyx` | Cache-clear hook registration | ✓ WIRED | Line 59: `_register_cache_clear_hook(_clear_all_caches)`. Module-level registration ensures hook fires on circuit reset. |
| `_core.pyx` | circuit.__init__ | _clear_compile_caches called on circuit reset | ✓ WIRED | Line 282 in circuit.__init__: `_clear_compile_caches()` called after state reset. |
| `__init__.py` | `compile.py` | Import and expose compile decorator | ✓ WIRED | Line 49: `from .compile import compile`. Line 179: in `__all__`. |
| `test_compile.py` | `__init__.py` | import quantum_language as ql; ql.compile | ✓ WIRED | All 22 tests use `@ql.compile` decorator pattern. Verified via `hasattr(ql, 'compile')` = True. |

**Score:** 9/9 key links wired

### Requirements Coverage

| Requirement | Status | Supporting Evidence |
|-------------|--------|---------------------|
| CAP-01: @ql.compile captures gate sequences on first call | ✓ SATISFIED | Truth 1 verified. CompiledFunc._capture() calls extract_gate_range() after function execution. |
| CAP-02: Gates stored with virtual qubit references | ✓ SATISFIED | _build_virtual_mapping() maps real qubits to virtual namespace. CompiledBlock stores virtual gates. |
| CAP-03: Subsequent calls replay with remapping | ✓ SATISFIED | Truth 2 verified. CompiledFunc._replay() builds virtual-to-real map and calls inject_remapped_gates(). |
| CAP-04: Cache key includes function, widths, classical args | ✓ SATISFIED | Truth 4 verified. Line 256 in compile.py: `cache_key = (tuple(classical_args), tuple(widths))`. |
| CAP-05: Cache cleared on ql.circuit() | ✓ SATISFIED | Truth 5 verified. Hook registered and fires in circuit.__init__(). |
| CAP-06: Return values usable in subsequent operations | ✓ SATISFIED | Truth 3 verified. _build_return_qint() creates qint with ownership metadata. |
| INF-01: Cython helpers for gate extraction/injection | ✓ SATISFIED | extract_gate_range() and inject_remapped_gates() exist in _core.pyx and are substantive. |
| INF-02: Global state snapshot/restore | ✓ SATISFIED | Layer floor saved/restored during replay (lines 373-382 in compile.py). |

**Score:** 8/8 requirements satisfied

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns detected |

**Scan Results:**
- No TODO/FIXME/XXX/HACK comments in compile.py or test_compile.py
- No placeholder content or stub patterns
- No empty return statements or console.log-only implementations
- All functions have substantive implementations with proper error handling
- Layer floor management prevents gate reordering during replay
- Cache eviction with max_cache limit prevents unbounded growth

### Human Verification Required

None - all success criteria are programmatically verifiable through automated tests.

**Verification Notes:**
- 22 tests cover all 5 success criteria plus edge cases (decorator forms, cache eviction, error handling, metadata preservation)
- Manual smoke test confirms end-to-end workflow: capture, replay, cache invalidation
- Side-effect counter in tests proves function body NOT re-executed on replay
- Qubit index tracking in tests proves gates target new qubits on replay
- Return value arithmetic operations prove usability in subsequent operations

---

## Summary

Phase 48 goal **ACHIEVED**. All must-haves verified against actual codebase:

**Cython Infrastructure (Plan 48-01):**
- ✓ extract_gate_range: 49 lines, extracts gates from layer range with large_control handling
- ✓ inject_remapped_gates: 50 lines, injects gates with qubit remapping and malloc/free
- ✓ Layer floor helpers: _get_layer_floor() and _set_layer_floor() prevent gate reordering
- ✓ _allocate_qubit: wraps allocator_alloc() for ancilla allocation
- ✓ Cache-clear hooks: module-level list, registration function, clear function, wired into circuit.__init__

**Python Decorator (Plan 48-02):**
- ✓ compile.py: 447 lines with CompiledFunc, CompiledBlock, virtual qubit mapping, LRU cache
- ✓ CompiledFunc._capture(): records layers, collects param qubit indices, extracts gates, virtualizes mapping
- ✓ CompiledFunc._replay(): builds virtual-to-real map, allocates ancillas, saves/restores layer_floor, injects gates, constructs return qint
- ✓ Cache key: (classical_args, widths) tuple with custom key function support
- ✓ Cache invalidation: weak references, hook registration, clears on circuit reset
- ✓ Public API: ql.compile accessible, supports bare decorator and parens forms
- ✓ Test suite: 22 tests, 584 lines, all pass, no regressions

**Success Criteria:**
1. ✓ First call same as undecorated - verified via tests and gate count comparison
2. ✓ Replay without re-execution - verified via side-effect counter
3. ✓ Return value usable - verified via subsequent arithmetic operations
4. ✓ Re-capture on different args/widths - verified via cache key tests
5. ✓ Cache clear on circuit reset - verified via hook firing tests

**Requirements:**
- All 8 requirements (CAP-01 through CAP-06, INF-01, INF-02) satisfied

No gaps found. Phase ready for milestone v2.0 integration.

---

_Verified: 2026-02-04T13:35:00Z_
_Verifier: Claude (gsd-verifier)_
