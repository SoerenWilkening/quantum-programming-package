# Project Research Summary

**Project:** Quantum Assembly v9.0 -- Nested Controls & Chess Engine
**Domain:** Quantum programming framework (DSL compiler, circuit generation, game-tree search)
**Researched:** 2026-03-09
**Confidence:** HIGH

## Executive Summary

Quantum Assembly v9.0 centers on a single architectural fix -- replacing the flat control-state globals (`_controlled`, `_control_bool`) with a proper control stack -- that unlocks nested `with qbool:` blocks and, by extension, a natural-programming-style chess engine. The existing framework already has all the necessary infrastructure (Toffoli AND via the C backend's `add_gate` with `large_control`, scope-based uncomputation, `@ql.compile` capture-replay, 2D qarray indexing) but the `__enter__`/`__exit__` methods on `qint` are broken for nesting: `__exit__` unconditionally resets control state to `(False, None)`, destroying the outer context. Every other feature in this milestone (controlled bitwise XOR, 2D qarray bug fix, chess engine rewrite) depends on or follows directly from fixing this one defect.

The recommended approach is a strict bottom-up build: (1) replace control globals with a stack and add a direct `emit_ccx` function for Toffoli AND ancilla management, (2) rewrite `__enter__`/`__exit__` with push/pop semantics plus AND-ancilla lifecycle (allocate on enter, uncompute on exit), (3) verify `@ql.compile` compatibility with the new stack, (4) fix the 2D qarray positional-tuple bug, and (5) rewrite the chess engine using nested `with` blocks. This ordering eliminates the primary risk: building the chess engine on an unproven foundation.

The key risks are ancilla lifecycle management and OOM during chess engine compilation. AND ancillas created for nested controls must be uncomputed in exactly the right order -- after scope-local qbool cleanup but before restoring the outer control context. The chess engine's triple-nested loops over an 8x8 board generate tens of thousands of conditional blocks; without compiled sub-predicates and explicit `gc.collect()` calls, the gate array will exhaust memory. Both risks are well-understood and have concrete mitigations documented in the research. No new dependencies, no C backend changes, and no build system modifications are needed -- the entire milestone is approximately 60-90 lines of Python/Cython changes plus the chess engine rewrite itself.

## Key Findings

### Recommended Stack

No stack changes are required. The existing technology stack (Python 3.11+, Cython 3.2.4, C23 backend, NumPy, rustworkx, Pillow, Qiskit/Aer) is validated and sufficient for all v9.0 features. All work is in the Python/Cython layer.

**Core technologies (unchanged):**
- **Python 3.11+ / Cython 3.2.4:** Frontend DSL and bindings -- all control stack changes are Cython-level modifications to existing files
- **C23 backend (`add_gate`):** Gate engine -- already handles arbitrary `NumControls` via `large_control` array; no modifications needed
- **rustworkx 0.17.1:** Call graph DAG for `@ql.compile(opt=1)` -- used unchanged for chess engine compilation

**What NOT to add:** No AST tracing for compile, no multi-controlled gate C functions, no control-flow-graph library, no separate 2D array class, no new gate decomposition library. See STACK.md "What NOT to Add" section for full rationale.

### Expected Features

**Must have (table stakes -- v9.0):**
- **Control stack restoration in `__exit__`** -- fixes the root cause; without this, nothing else works
- **AND-ancilla lifecycle** -- allocate on nested `__enter__`, uncompute on `__exit__`; prevents qubit leaks
- **Controlled XOR for qbool** -- `~qbool` inside `with` must emit Toffoli/CNOT; unblocks all chess predicate patterns
- **2D qarray `dim=(8,8)` construction** -- fix TypeError for positional tuple; chess engine needs `ql.qarray(dim=(8,8), dtype=ql.qbool)`
- **2-level nested `with` end-to-end** -- `with a: with b: x += 1` must produce correct multi-controlled circuit
- **Chess engine rewrite** -- natural-programming style using nested `with` and 2D qarrays

**Should have (differentiators -- v9.x):**
- **Arbitrary-depth nesting (3+ levels)** -- incremental once 2-level works; each level adds 1 Toffoli AND ancilla
- **Automatic AND-ancilla uncomputation** -- users never manage control ancillas manually (competitive vs Q#, Qiskit, Cirq where ancillas are manual)
- **Controlled AND/OR for qint** -- lower priority than XOR; chess patterns use `~` almost exclusively
- **Chess engine quantum verification** -- small-board simulation to confirm correct circuits

**Defer (v10+):**
- Controlled multiplication/division inside `with` -- complex ancilla interactions, not needed for chess
- General game engine API (`ql.game_tree()`, `ql.minimax()`) -- needs stable chess engine as reference first
- Sparse 2D qarray -- quantum computation requires all positions in superposition; sparsity is a classical concept

### Architecture Approach

The framework's three-layer architecture (Python DSL -> Cython bindings -> C gate engine) remains unchanged. The architectural fix is entirely at the Cython bindings layer: replacing three flat globals (`_controlled`, `_control_bool`, `_list_of_controls`) with a single `_control_stack` list. The existing accessor functions `_get_controlled()` and `_get_control_bool()` become thin wrappers over the stack (`len(stack) > 0` and `stack[-1]`), preserving backward compatibility across all arithmetic, comparison, and compile modules. A new `_toffoli_and` / `_uncompute_toffoli_and` pair handles AND-ancilla creation and cleanup using a direct `emit_ccx` gate emission (bypassing the heavyweight `__and__` operator).

**Major components modified:**
1. **`_core.pyx` control state** -- replace flat globals with `_control_stack` list; thin wrappers for backward compat
2. **`qint.pyx __enter__/__exit__`** -- push/pop control stack; Toffoli AND ancilla lifecycle; ~50-80 lines changed
3. **`_gates.pyx` or `_gates.py`** -- add `emit_ccx` for direct Toffoli gate emission (no `&` operator overhead)
4. **`compile.py` save/restore** -- save/restore `_control_stack` instead of flat globals during capture
5. **`qarray.pyx __init__`** -- route positional tuple-of-ints to `dim=` path; ~10 lines changed

### Critical Pitfalls

1. **`__exit__` unconditionally resets to `(False, None)`** -- silently corrupts outer control context; all operations after inner `with` execute uncontrolled. Prevent by implementing stack-based pop. The 6 xfail tests in `test_nested_with_blocks.py` catch this.

2. **AND-ancilla leak on nested entry** -- ancilla must be uncomputed in correct order: after scope-local qbool cleanup, before restoring outer control. Wrong ordering corrupts uncomputation gates or leaks qubits. Prevent by storing ancilla on control stack entry, sequencing `__exit__` as: (a) uncompute scope qbools, (b) reverse Toffoli, (c) deallocate ancilla, (d) restore outer control.

3. **`_control_bool &= self` uses multi-bit AND instead of single Toffoli** -- the `&=` operator dispatches to full multi-bit `Q_and` C function, which is overkill for 1-bit qbool and semantically wrong for multi-bit qint conditions. Prevent by using direct `emit_ccx` for AND-ancilla creation.

4. **Chess engine OOM from uncompiled loop expansion** -- triple-nested loops over 8x8 board generate ~32K conditional blocks without `@ql.compile`. Prevent by factoring into compiled sub-predicates and using `gc.collect()` between sections.

5. **Scope-local uncomputation uses wrong control qubit** -- qbools created under outer control but uncomputed under inner AND-ancilla control produce mismatched forward/reverse gates. Prevent by recording control context at creation and restoring it during uncomputation.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Control Stack Infrastructure

**Rationale:** Foundation that everything depends on. No external dependencies. Must be done first because Phases 2 and 3 cannot be tested without it.
**Delivers:** `_control_stack` replacing flat globals, `emit_ccx` function, `_toffoli_and`/`_uncompute_toffoli_and` helpers, backward-compatible accessor wrappers.
**Addresses:** Infrastructure for all nested control features.
**Avoids:** Pitfall 3 (multi-bit AND via `&=`), Pitfall 10 (global list corruption).
**Files:** `_core.pyx`, `_gates.pyx`/`_gates.py`, `qint.pxd`.
**Requires rebuild:** Yes (Cython).

### Phase 2: `__enter__`/`__exit__` Rewrite

**Rationale:** Direct dependency on Phase 1. This is the core feature -- once `__enter__`/`__exit__` work correctly, all nested `with` blocks function.
**Delivers:** Working 2-level nested `with qbool:` blocks, AND-ancilla lifecycle, existing xfail tests passing.
**Addresses:** Control stack restoration (P1 feature), AND-ancilla lifecycle (P1), controlled XOR for qbool (P1).
**Avoids:** Pitfall 1 (exit resets to False/None), Pitfall 2 (ancilla leak), Pitfall 6 (wrong control for uncomputation).
**Files:** `qint.pyx` (lines 804-882), `qint_bitwise.pxi` (controlled XOR).
**Requires rebuild:** Yes (Cython).

### Phase 3: Compile Module Compatibility

**Rationale:** Must verify `@ql.compile` works with nested controls before the chess engine depends on it. Cannot be tested until Phase 2 produces correct nested gate sequences.
**Delivers:** Compiled functions callable inside nested `with` blocks, correct controlled-variant derivation, cache key handling for nesting depth.
**Addresses:** Chess engine compilation (P1 feature), compile + nested control integration.
**Avoids:** Pitfall 7 (capture misses nested control context), Pitfall 12 (cache key ignores nesting depth).
**Files:** `compile.py` (save/restore, controlled variant derivation).

### Phase 4: 2D qarray Bug Fix

**Rationale:** Independent of Phases 1-3; can be done in parallel. Low complexity (5-10 lines). Must be done before chess engine rewrite.
**Delivers:** `ql.array((rows, cols))` positional tuple form working, clear error messages for ambiguous calls.
**Addresses:** 2D qarray construction fix (P1 feature).
**Avoids:** Pitfall 5 (API confusion tuple vs dim=).
**Files:** `__init__.py` `array()`, possibly `_qarray_utils.py`.

### Phase 5: Chess Engine Rewrite

**Rationale:** Depends on Phases 2, 3, and 4 all being complete and tested. The chess engine is the integration test and showcase for all prior work.
**Delivers:** `examples/chess_engine.py` rewritten in natural-programming style with nested `with` blocks, 2D qarrays, and `@ql.compile(opt=1)`.
**Addresses:** Chess engine rewrite (P1 feature), natural chess notation (differentiator).
**Avoids:** Pitfall 4 (OOM from uncompiled expansion), Pitfall 8 (building on unproven foundation), Pitfall 13 (GC races).
**Files:** `examples/chess_engine.py` (rewrite), new test file for circuit-build verification.

### Phase Ordering Rationale

- **Phases 1-2 are strictly sequential** because `__enter__`/`__exit__` cannot be rewritten without the control stack infrastructure.
- **Phase 3 must follow Phase 2** because compile compatibility testing requires working nested `with` blocks that produce correct gate sequences.
- **Phase 4 is independent** and can run in parallel with Phases 1-3, but must complete before Phase 5.
- **Phase 5 must be last** because it integrates all prior work. Building the chess engine before nested controls are proven correct risks wasted effort and silent circuit corruption (Pitfall 8).
- **This ordering avoids the single biggest risk:** declaring the chess engine "done" when nested controls are subtly broken, producing circuits that compile without errors but compute wrong results.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (`__enter__`/`__exit__` rewrite):** The uncomputation ordering for AND ancillas relative to scope-local qbools is subtle. The existing `_do_uncompute` mechanism, scope frame tracking, and `creation_scope` checks all interact. A detailed line-by-line analysis of the current `__exit__` and scope cleanup code is recommended before writing the new version.
- **Phase 3 (compile compatibility):** The compile decorator's save/restore of control state and controlled-variant derivation need careful audit. The `_capture_and_cache_both` function's interaction with the control stack during nested capture is non-obvious.

Phases with standard patterns (skip research-phase):
- **Phase 1 (control stack):** Well-understood data structure replacement (globals -> stack). The existing `_scope_stack` provides a direct pattern to follow.
- **Phase 4 (2D qarray fix):** Trivial bug fix with clear root cause. The `dim=` path already works; just need to route positional tuples correctly.
- **Phase 5 (chess engine):** The target code already exists in `examples/chess_engine.py`. The v8.0 chess implementation provides patterns for compiled predicate factories. The main work is adapting to nested `with` style.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from direct codebase analysis. No new dependencies needed. Verified against existing stack documentation. |
| Features | HIGH | Feature requirements derived from existing `examples/chess_engine.py` target code and `test_nested_with_blocks.py` xfail tests. Competitor analysis confirms AND-ancilla approach is standard. |
| Architecture | HIGH | Architecture changes identified via line-by-line source analysis. Control stack design validated against existing `_scope_stack` pattern. C backend confirmed to need no changes. |
| Pitfalls | HIGH | Critical pitfalls (1-4) identified from existing bugs visible in source code. Moderate pitfalls (5-8) confirmed by debug notes and OOM analysis. Academic references validate ancilla lifecycle concerns. |

**Overall confidence:** HIGH

All four research areas produced consistent, mutually reinforcing findings based on direct source code analysis. The core problem (broken `__exit__`), the solution (control stack), and the risks (ancilla lifecycle, OOM) are all concrete and verifiable. No speculative or poorly-sourced findings.

### Gaps to Address

- **Controlled XOR implementation detail:** The research identifies that `~qbool` inside `with` must work (controlled XOR), but the exact implementation path in `qint_bitwise.pxi` needs inspection during Phase 2 planning. The `NotImplementedError` sites in the bitwise code need to be audited to determine which controlled ops to enable first.
- **`emit_ccx` emission path:** The research recommends adding `emit_ccx` to `_gates.pyx` or `_gates.py`, but the exact gate format (which C function to call, gate type enum value for CCX) needs confirmation from the C backend's `types.h` and `gate_ops.c`.
- **Compile cache key for nesting depth:** Pitfall 12 identifies that the cache key may not distinguish different nesting depths. Whether this is a real problem or theoretical depends on how controlled-variant derivation handles the AND-ancilla as control qubit. Needs validation during Phase 3 planning.
- **`walk.py` simplification opportunity:** With nested `with` blocks working, the V-gate CCRy decomposition workaround in `walk.py` becomes potentially unnecessary. Whether to remove it or keep it as a performance optimization should be decided during or after Phase 5.

## Sources

### Primary (HIGH confidence)
- Direct source code analysis of `qint.pyx`, `_core.pyx`, `qint_bitwise.pxi`, `qint_arithmetic.pxi`, `qint_comparison.pxi`, `compile.py`, `qarray.pyx`, `_qarray_utils.py`, `walk.py`, `__init__.py`
- Existing test suite: `test_nested_with_blocks.py` (6 xfail tests), qarray tests, compile tests
- `examples/chess_engine.py` -- target code defining the milestone's deliverable
- `.planning/debug/test-compile-oom.md` -- OOM root cause analysis

### Secondary (MEDIUM confidence)
- [Unqomp: Synthesizing Uncomputation (PLDI 2021)](https://dl.acm.org/doi/pdf/10.1145/3453483.3454040) -- uncomputation ordering constraints
- [Reqomp: Space-constrained Uncomputation (ETH Zurich)](https://www.research-collection.ethz.ch/server/api/core/bitstreams/0d94612c-1514-496c-8a28-7ad6bedf87ea/content) -- ancilla reuse
- [Rise of Conditionally Clean Ancillae (Quantum, 2025)](https://quantum-journal.org/papers/q-2025-05-21-1752/pdf/) -- Toffoli depth vs ancilla tradeoffs
- [Efficient Multi-Controlled Gate Decomposition (arXiv:2404.02279)](https://arxiv.org/pdf/2404.02279) -- MCX decomposition
- [SPARE: Optimizing Ancilla-Based Circuits (POPL 2025)](https://dl.acm.org/doi/10.1145/3729253) -- ancilla lifecycle

### Tertiary (LOW confidence)
- Q# functor composition, Qiskit MCMT, Cirq ControlledGate -- competitor feature analysis for context only; no implementation derived from these

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
