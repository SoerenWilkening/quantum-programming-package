# Feature Research

**Domain:** Quantum programming framework -- nested conditional controls, 2D quantum arrays, chess engine rewrite
**Researched:** 2026-03-09
**Confidence:** HIGH (existing codebase thoroughly analyzed; nested control patterns well-established in quantum computing literature)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must work for the milestone to be considered complete. Without these, the chess engine example cannot be written in its target natural-programming style.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Nested `with qbool:` blocks (2 levels) | The chess_engine.py example has `with black_king[*index] == 1:` containing `with white_knight[a,b]:` -- two levels of quantum conditional control. Currently raises NotImplementedError for controlled bitwise ops. | HIGH | Core blocker. Current `__exit__` unconditionally resets `_controlled=False` and `_control_bool=None`, destroying outer control context. Also, bitwise AND/OR/XOR raise NotImplementedError when `_controlled=True`. |
| Nested `with` control restoration | When exiting an inner `with` block, the outer block's control qubit must be restored as the active control. | MEDIUM | `__exit__` must pop from `_list_of_controls` stack and restore prior `_control_bool`. The `_list_of_controls` list already exists but `__exit__` never uses it. |
| Toffoli AND control composition | Inner `with` inside outer `with` requires a 2-qubit controlled gate (CCX/Toffoli) -- the operation is controlled on BOTH the outer and inner qbool simultaneously. | HIGH | When entering nested `with`, `__enter__` already does `_control_bool &= self` (line 816), producing a Toffoli AND ancilla. The `&` operator on qbool allocates a fresh ancilla qubit. This ancilla must be properly tracked and uncomputed on `__exit__`. |
| Controlled bitwise ops inside `with` | Operations like `~result` (qbool NOT/flip) inside a `with` block are the most common pattern in chess predicates. Currently: `Controlled classical-quantum XOR not yet supported`. | HIGH | All 6 controlled bitwise variants (CQ/QQ for AND/OR/XOR) raise NotImplementedError. At minimum, controlled XOR (for `~qbool`) must work -- it's a CNOT controlled on the control qubit, which is just a Toffoli gate. |
| 2D qarray construction via `dim=(rows, cols)` | The chess_engine.py example uses `ql.qarray(dim=(8,8), dtype=ql.qbool)`. Currently fails with TypeError in `_infer_width`. | LOW | The `dim=` path in `qarray.__init__` already handles tuples correctly (lines 53-80 in qarray.pyx). The bug is in the `data=` path when data is passed to `_infer_width` with a non-flat structure. Need to verify/fix the specific crash scenario. |
| 2D qarray element access `arr[r, f]` | Chess board access `black_king[0, 4]` via tuple indexing. Must return the element qbool and support `with arr[r, f]:` for conditional control. | LOW | Already implemented in `_handle_multi_index` with `_multi_to_flat` for all-integer tuples. Tested and working in v1.3+. |
| 2D qarray in-place mutation `arr[r, f] += 1` | Chess engine does `black_king[pp, np] += 1` to set/clear board squares. | LOW | `__setitem__` with tuple key already delegates to `_multi_to_flat` for element assignment (line 265). Augmented assignment works through Python's `__getitem__` + operator + `__setitem__` chain. |
| `@ql.compile(opt=1)` for chess engine | The chess_engine.py uses `ql.compile(opt=1)` as decorator. opt=1 is the DAG-only level (no merge, no full expansion). | LOW | Already implemented in v7.0. The compile decorator accepts `opt=1` and builds a CallGraphDAG without merging. No new work needed. |

### Differentiators (Competitive Advantage)

Features that go beyond the minimum and provide real value over other quantum frameworks.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Arbitrary-depth nested `with` (3+ levels) | Q# supports `Controlled Controlled` arbitrarily via functor composition. This framework should match: `with a: with b: with c:` generating a 3-controlled gate via AND-ancilla cascade. | MEDIUM | Once 2-level nesting works, N-level is an incremental extension. Each additional level adds one Toffoli AND ancilla. The `_list_of_controls` stack already supports arbitrary depth. Ancilla management (allocation on enter, uncomputation on exit) is the key challenge. |
| Automatic AND-ancilla uncomputation | When exiting a nested `with` block, the Toffoli AND ancilla used for control composition should be automatically uncomputed (reversed). Users should not manage this manually. | MEDIUM | The scope-based uncomputation system (Phase 19) already handles qbool cleanup in scope frames. The AND ancilla produced by `_control_bool &= self` needs to be registered in the scope frame so `__exit__` uncomputes it. |
| Natural chess notation | The chess_engine.py example reads like a chess program, not a quantum circuit. `with black_king[*index] == 1:` is self-documenting. This natural-programming style is the framework's core differentiator. | LOW | Enabled by nested `with` + 2D qarray. No additional implementation beyond table stakes. The readability IS the feature. |
| Controlled arithmetic inside `with` | Beyond just `~qbool`, supporting `x += 1` inside nested `with` blocks (multi-controlled addition). The chess engine does `count += 1` inside conditional blocks. | MEDIUM | Single-level controlled arithmetic already works (v1.0). For nested `with`, the control qubit becomes the AND-ancilla. The C-level `cQQ_add` / `cCQ_add` functions already accept a control qubit parameter -- the question is whether they handle multi-qubit control lists. Currently they take a single control qubit; the AND-ancilla approach reduces multi-control to single-control + ancilla. |
| Compound predicates in `with` | `with black_king[*index] == 1:` evaluates a comparison and uses the result as control. The `== 1` comparison on a qbool element should be optimized away (identity for qbool). | LOW | Already works for single-level `with`. The comparison `qbool == 1` returns a new qbool that is a copy of the original. Could be optimized to avoid the copy when the comparison is trivially identity. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-qubit control lists (pass list of control qubits to C backend) | Seems cleaner than AND-ancilla decomposition -- just pass N control qubits and let C handle it. | The C backend's `large_control` mechanism handles multi-controlled X gates but not arbitrary multi-controlled operations. Adding general N-control support to every C operation would be a massive refactor of 50+ C functions. | AND-ancilla decomposition: compose N controls into a single ancilla qubit using a cascade of Toffoli AND gates. Each gate in the body sees a single control qubit. This is the standard approach used by Qiskit, Cirq, and Q#. |
| Dynamic qarray reshaping | Being able to change array dimensions after creation (like NumPy's `.reshape()`). | Quantum arrays are backed by physical qubits. Reshaping changes the logical view but not the physical layout. If users reshape and then pass to `@ql.compile`, the cache key (based on length) won't distinguish shapes, leading to silent bugs. | Create a new qarray with the desired shape from the start. The `dim=` parameter handles this. If views are needed, use slicing (`arr[0, :]` for row access). |
| Implicit board state in chess engine | Storing the board as module-level state that predicates access implicitly (closure capture). | Implicit state breaks `@ql.compile` because the decorator needs explicit arguments for cache key computation and qubit tracking. Module-level qints/qarrays captured by closure bypass the compile infrastructure. | Pass board qarrays explicitly as function arguments, as the current chess_predicates.py already does. The chess_engine.py example captures them in closure within `@ql.compile`, which works because `opt=1` traces the actual execution. |
| Quantum conditional `if/else` (classical branching on quantum state) | Users want `if qbool: ... else: ...` where only one branch executes. | Quantum computation requires both branches to be reversible and executed simultaneously (superposition). Classical `if/else` would collapse the quantum state. The `with` block correctly applies operations controlled on the qbool, which is the quantum equivalent. | Use `with qbool:` for the "if true" case. For "if false", use `with ~qbool:` (NOT the control). For XOR-style either/or, use separate `with` blocks. |
| Sparse 2D qarray | For 8x8 chess boards, most squares are empty. A sparse representation could save qubits. | On a quantum computer, every board position must exist in superposition -- sparsity is a classical concept. All 64 squares need qubits allocated regardless of occupancy because the piece locations are in superposition. | Use dense `ql.qarray(dim=(8,8), dtype=ql.qbool)` which allocates one qubit per square. Classical pre-filtering (which squares to check) is already done at circuit construction time by the predicate factories. |

## Feature Dependencies

```
[Nested with blocks (2+ levels)]
    |-- requires --> [Control state stack in __enter__/__exit__]
    |                    |-- requires --> [_list_of_controls stack restoration in __exit__]
    |                    |-- requires --> [AND-ancilla allocation on nested __enter__]
    |                    |-- requires --> [AND-ancilla uncomputation on nested __exit__]
    |
    |-- requires --> [Controlled bitwise XOR (at minimum)]
    |                    |-- implemented via --> Toffoli gate (control + target + ancilla)
    |
    |-- enables  --> [Chess engine natural-style rewrite]
                         |-- requires --> [2D qarray dim=(8,8) construction fix]
                         |-- requires --> [2D qarray element access/mutation]
                         |-- uses    --> [@ql.compile(opt=1)]

[Arbitrary-depth nesting (3+ levels)]
    |-- requires --> [Nested with blocks (2 levels)]
    |-- requires --> [AND-ancilla cascade (N-1 ancillas for N controls)]

[Chess engine rewrite]
    |-- conflicts --> [Current chess_walk.py / chess_predicates.py architecture]
                       (rewrite replaces, not extends)
```

### Dependency Notes

- **Nested `with` requires control stack restoration:** The `__exit__` method currently does `_set_controlled(False)` unconditionally. It must instead pop from the `_list_of_controls` stack and restore the previous `_control_bool`. This is the fundamental architectural fix.
- **Nested `with` requires controlled XOR:** The chess engine's most common pattern is `~qbool` (flip) inside a `with` block. Inside a nested `with`, this becomes a multi-controlled NOT, which requires the controlled XOR path to not raise NotImplementedError. The AND-ancilla approach means only single-control XOR is needed (the AND ancilla holds the multi-control result).
- **Chess engine rewrite requires 2D qarray:** The target chess_engine.py uses `ql.qarray(dim=(8,8), dtype=ql.qbool)` which must construct without error. The existing `dim=` path in qarray.pyx handles this correctly in theory, but the known bug `ql.array((rows, cols))` (non-keyword) fails with TypeError.
- **Chess engine rewrite replaces current chess modules:** The v8.0 chess implementation (chess_encoding.py, chess_predicates.py, chess_walk.py) uses factory patterns and manual predicate composition to work around nested-with limitations. Once nested `with` works, the chess engine can be rewritten in the natural style shown in examples/chess_engine.py, making the workaround code unnecessary for the demo.

## MVP Definition

### Launch With (v9.0)

Minimum features for the milestone to be complete.

- [ ] **Control state stack restoration in `__exit__`** -- Fix `__exit__` to restore outer `_control_bool` from `_list_of_controls` when exiting inner `with` block. Without this, nothing else works.
- [ ] **AND-ancilla lifecycle in nested `__enter__`/`__exit__`** -- The `&=` in `__enter__` creates an ancilla; `__exit__` must uncompute it. Register the AND-ancilla in the scope frame for automatic cleanup.
- [ ] **Controlled XOR for qbool** -- At minimum, `~qbool` inside a `with` block must work (emit Toffoli/CNOT). This unblocks all chess predicate patterns.
- [ ] **2D qarray `dim=(8,8)` construction** -- Fix the TypeError bug so `ql.qarray(dim=(8,8), dtype=ql.qbool)` works.
- [ ] **Chess engine rewrite in natural style** -- Rewrite examples/chess_engine.py using nested `with` blocks and 2D qarrays, matching the target code shown in the example file. Compile with `@ql.compile(opt=1)`.
- [ ] **2-level nesting verified** -- End-to-end test: `with a: with b: x += 1` produces correct multi-controlled addition circuit.

### Add After Validation (v9.x)

Features to add once the core nested control mechanism is proven correct.

- [ ] **Controlled AND/OR for qint** -- Currently raises NotImplementedError. Lower priority than XOR because chess patterns use `~` (XOR) almost exclusively. Enable after XOR is stable.
- [ ] **3+ level nesting** -- Extend AND-ancilla cascade beyond 2 levels. Test with `with a: with b: with c: x += 1`.
- [ ] **Optimized qbool identity comparison** -- `with qbool == 1:` could skip the comparison entirely since `qbool == True` is identity. Currently allocates a comparison ancilla unnecessarily.
- [ ] **Chess engine quantum verification** -- Run the rewritten chess engine on small board sizes (3x3 or 4x4) with Qiskit simulation to verify correct circuit behavior.

### Future Consideration (v10+)

Features to defer until the nested control mechanism is battle-tested.

- [ ] **Controlled multiplication inside `with`** -- Complex because multiplication uses many internal ancillas. Defer until arithmetic inside nested `with` is systematically audited.
- [ ] **Controlled division/modulo inside `with`** -- Even more complex. Currently QQ division has known ancilla leaks. Not a priority for chess.
- [ ] **General game engine API** -- `ql.game_tree()` or `ql.minimax()` that abstracts the quantum walk pattern. Needs the chess engine to stabilize first as a reference implementation.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Control stack restoration (`__exit__` fix) | HIGH | LOW | P1 |
| AND-ancilla lifecycle (nested enter/exit) | HIGH | MEDIUM | P1 |
| Controlled XOR for qbool (`~` inside `with`) | HIGH | MEDIUM | P1 |
| 2D qarray `dim=` construction fix | HIGH | LOW | P1 |
| Chess engine rewrite | HIGH | MEDIUM | P1 |
| 2-level nesting end-to-end test | HIGH | LOW | P1 |
| Controlled AND/OR for qint | MEDIUM | MEDIUM | P2 |
| 3+ level nesting | MEDIUM | LOW | P2 |
| Optimized qbool identity comparison | LOW | LOW | P3 |
| Chess engine quantum verification (sim) | MEDIUM | MEDIUM | P2 |
| Controlled multiplication inside `with` | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v9.0 milestone
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Q# | Qiskit | Cirq | Quantum Assembly (target) |
|---------|-----|--------|------|--------------------------|
| Nested controlled ops | `Controlled Controlled Op` via functor -- arbitrary depth, compiler-generated | `.control(N)` on any gate, ancilla decomposition via `MCXGate` | `.controlled_by()` method, `decompose_multi_controlled_x` for decomposition | `with a: with b: op` -- Python context managers with Toffoli AND composition |
| Multi-controlled gates | Arbitrary via `Controlled` functor stacking | MCMT gate library, ancilla-based decomposition | `ControlledGate` with arbitrary control values | AND-ancilla cascade reducing N-control to 1-control + (N-1) ancillas |
| Ancilla management | Automatic via compiler | Manual (user allocates/manages) | Manual | Automatic via scope-based uncomputation (AND ancillas cleaned up on `__exit__`) |
| 2D quantum arrays | No native support (use classical arrays of qubits) | No native array type | No native array type | `ql.qarray(dim=(8,8), dtype=ql.qbool)` with NumPy-style indexing |
| Natural game engine code | Not applicable (gate-level) | Not applicable (gate-level) | Not applicable (gate-level) | Chess engine reads like Python chess code with `with` conditionals |

## Sources

- Q# Controlled functor: [Microsoft Learn - Functor Application](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/expressions/functorapplication)
- Q# Operations and Functions: [Microsoft Learn - Operations](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/typesystem/operationsandfunctions)
- Cirq ControlledGate: [Google Quantum AI - ControlledGate](https://quantumai.google/reference/python/cirq/ControlledGate)
- Cirq multi-controlled decomposition: [Google Quantum AI - decompose_multi_controlled_x](https://quantumai.google/reference/python/cirq/decompose_multi_controlled_x)
- Qiskit MCMT gate: [IBM Quantum Documentation - MCMT](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.MCMT)
- Efficient multi-controlled gate decomposition: [arXiv:2404.02279](https://arxiv.org/pdf/2404.02279)
- Toffoli gate Wikipedia: [Wikipedia - Toffoli gate](https://en.wikipedia.org/wiki/Toffoli_gate)
- Codebase analysis: `src/quantum_language/qint.pyx` lines 784-882 (`__enter__`/`__exit__`), `src/quantum_language/_core.pyx` lines 24-43 (control state globals), `src/quantum_language/qint_bitwise.pxi` (NotImplementedError sites), `src/quantum_language/qarray.pyx` (dim= constructor), `examples/chess_engine.py` (target format), `src/chess_predicates.py` (current workaround patterns)

---
*Feature research for: Nested quantum controls and chess engine (v9.0 milestone)*
*Researched: 2026-03-09*
