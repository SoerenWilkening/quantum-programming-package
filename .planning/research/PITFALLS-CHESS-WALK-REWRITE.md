# Domain Pitfalls: Quantum Chess Walk Rewrite (v8.0)

**Domain:** Quantum move legality checking in quantum walk framework, compile infrastructure numpy migration
**Researched:** 2026-03-08
**Confidence:** HIGH (based on direct codebase analysis of existing code and known limitations)

---

## Critical Pitfalls

Mistakes that cause rewrites, OOM crashes, or fundamentally broken circuits.

### Pitfall 1: Combinatorial Explosion in Variable-Branching Diffusion

**What goes wrong:** The current `apply_diffusion` in `chess_walk.py` iterates over `itertools.combinations(range(d_max), d_val)` for every possible branching factor `d_val` from 1 to `d_max`. For `d_max = 20` moves this produces 1,048,575 pattern combinations. For the target of up to 218 moves, this is `2^218 - 1` -- a number with 65 digits. The circuit generation loop is literally impossible to execute.

**Why it happens:** The v6.0/v6.1 variable-branching diffusion was designed for SAT demos with `d_max <= 3`. It enumerates every subset of validity ancillae that could yield a particular `d(x)` count, emitting multi-controlled Ry gates for each. This approach is O(2^d_max) in the number of gate emission calls.

**Consequences:** Circuit generation hangs indefinitely or OOMs. Even `d_max = 25` would take years. The entire diffusion operator must be redesigned for large branching factors.

**Prevention:**
- Replace per-pattern enumeration with an arithmetic counting circuit: use a quantum adder tree to sum validity ancillae into a `d_count` register, then condition diffusion angles on the `d_count` value (O(d_max * log(d_max)) gates instead of O(2^d_max)).
- Alternatively, compute the Hamming weight of validity bits via a balanced binary adder tree, then dispatch on the count register value. The count register is O(log(d_max)) qubits wide, so conditioning on each possible count value is O(d_max) iterations, not O(2^d_max).
- Phase ordering: this redesign must happen BEFORE integrating quantum predicates into the walk, or the walk will never produce a circuit.

**Detection:** Circuit generation taking more than a few seconds for a single diffusion call. Gate count growing exponentially with move count.

**Phase assignment:** Must be addressed in the first phase of v8.0 (diffusion redesign). Blocks everything else.

---

### Pitfall 2: Raw qbool Allocation Per Predicate Call Causing Qubit Explosion

**What goes wrong:** Each call to `evaluate_children` allocates `d_max` validity ancillae plus one `reject` qbool per child (line 307 in chess_walk.py: `reject = alloc_qbool()`). For 218 children at each depth level, that is 436 fresh qubits per level. Over a depth-3 walk tree, that is 1,308 ancilla qubits just for validity -- on top of the 192 board qubits (3 x 8x8 qbool arrays) and walk registers. This is the documented limitation: "Raw predicate qubit allocation: each predicate call allocates new qbools, making SAT demos infeasible at depth >= 2 without compiled predicates."

**Why it happens:** The framework allocates physical qubits sequentially via `_allocate_qubit()`. There is no qubit recycling between predicate evaluations for different children. The `reject` qbool allocated at line 307 is never uncomputed (the comment says "adjoint of trivial predicate is identity" -- but the qubit is still allocated). With a real quantum predicate (not trivial), uncomputation produces even more ancillae.

**Consequences:** Circuit qubit count grows as `O(d_max * depth * predicate_ancillae)`. For chess with 218 moves and non-trivial predicates, expect 2,000+ qubits minimum. Qiskit simulation is impossible (17-qubit limit). Even circuit generation may OOM from the gate array sizes at MAXLAYERINSEQUENCE = 300,000.

**Prevention:**
- Implement qubit recycling: after evaluating child `i` and storing its validity result, uncompute and deallocate the predicate ancillae before evaluating child `i+1`.
- Use `@ql.compile(inverse=True)` for the predicate so `.inverse()` properly uncomputes all internal ancillae.
- Keep the validity ancillae (d_max qubits) alive across all children, but recycle everything else per-child.
- Consider compiled predicates that reuse the same ancilla pool across calls.
- The pattern should be: allocate reject ancilla -> evaluate predicate -> store result in validity[i] -> uncompute predicate (via .inverse()) -> deallocate reject ancilla -> move to child i+1.

**Detection:** Qubit count reported by `ql.stats()` growing linearly with `d_max` times depth. Exceeding 500 qubits for a depth-1 walk.

**Phase assignment:** Must be solved alongside diffusion redesign. The predicate architecture determines how validity bits are computed.

---

### Pitfall 3: Nested `with qbool:` Limitation Breaks Quantum Predicate Composition

**What goes wrong:** The framework cannot nest `with qbool:` blocks. This is a documented limitation worked around via "V-gate CCRy decomposition and inline gate emission." A quantum legality predicate needs to check multiple conditions simultaneously (piece exists on source AND target not same-color occupied AND king not in check after move). If any of these conditions itself produces a qbool used in a `with` block inside another `with` block, the circuit is wrong.

**Why it happens:** The `with` statement sets a global control context (`_set_controlled`, `_set_control_bool`). Nesting overwrites the outer control, causing the outer condition to be silently dropped from subsequent gates.

**Consequences:** Predicate logic silently produces incorrect circuits. A move that should be marked illegal could be marked legal (or vice versa), corrupting the entire walk's detection algorithm.

**Prevention:**
- Build legality predicates using only flat (non-nested) controlled operations. Decompose multi-condition checks into sequences of Toffoli-based AND gates that compute intermediate results into ancilla qubits.
- Pattern: `a_and_b = qbool(); toffoli(a, b, a_and_b);` then `with a_and_b: <action>`. Never `with a: with b: <action>`.
- Use the existing V-gate CCRy decomposition pattern from walk.py for multi-controlled operations.
- Wrap the predicate in `@ql.compile` which captures a flat gate list, avoiding the nesting issue entirely since all gates are recorded with their full control context at capture time.
- Design the predicate as: compute each condition into a separate ancilla qbool, AND them together into a single result qbool, then use that single qbool for the validity decision.

**Detection:** Statevector verification showing incorrect validity outcomes. Gates emitted inside nested `with` blocks missing one or more control qubits. Test with known-illegal moves and verify they are correctly rejected.

**Phase assignment:** Predicate design phase. The predicate API must be designed around this constraint from the start.

---

### Pitfall 4: Oracle Assumes Classical Pre-Filtering -- Quantum Predicates Need All-Moves Enumeration

**What goes wrong:** The current `_make_apply_move` factory in `chess_encoding.py` takes a classically-computed `move_list` and creates an oracle that only handles those specific moves. When the board is in superposition (which it is at non-root nodes of the walk tree), the classically-computed move list is wrong -- it was computed for the root position, not the superposed position.

**Why it happens:** The v6.1 design assumes positions are known at circuit construction time: "All move generation is purely classical since starting positions are known at circuit construction time" (chess_encoding.py docstring). This is true for the root but false for derived positions in the walk tree.

**Consequences:** The quantum walk applies the root position's legal moves at every depth level, ignoring that pieces have moved. The tree search explores a fictional game tree, producing meaningless detection results.

**Prevention:**
- The oracle must enumerate ALL geometrically possible moves for each piece type at circuit construction time: 8 destinations per knight square, 8 destinations per king square, for all 64 possible source squares. That is up to 218 geometric moves.
- Legality (piece exists on source, target not same-color occupied, not in check) is determined by quantum predicates at circuit runtime, not classical pre-filtering.
- The branch register indexes into the full geometric move table, not a filtered legal move list.
- The predicate sets the validity ancilla to |1> only when the move is actually legal given the current (superposed) board state.

**Detection:** Circuit verification at depth > 0 showing board states inconsistent with the move applied. Classical simulation of small instances revealing wrong moves at non-root nodes.

**Phase assignment:** Core architecture decision. Must be resolved before any oracle or predicate implementation begins.

---

### Pitfall 5: MAXLAYERINSEQUENCE Overflow with Large Chess Circuits

**What goes wrong:** The C backend pre-allocates a fixed-size array of 300,000 layers (`MAXLAYERINSEQUENCE` in `c_backend/include/types.h` line 50). A chess circuit with 218 moves, each requiring comparison operations plus conditional board updates, will exceed this limit. Each comparison is roughly 100-200 gates for 6-bit indices; 218 comparisons per predicate evaluation = ~30,000 gates per level; times depth, times walk iterations, times 2 (forward + adjoint) = millions of gates.

**Why it happens:** `MAXLAYERINSEQUENCE` was increased from 10K to 300K for 32-bit multiplication. Chess circuits at this scale require orders of magnitude more.

**Consequences:** Buffer overflow in C backend (segfault or memory corruption). The bug from v4.1 (BUG-01) reappears.

**Prevention:**
- Before implementing chess predicates, estimate total gate count: `(gates_per_move_check) * d_max * depth * walk_iterations * 2`.
- If estimate exceeds 300K, either increase `MAXLAYERINSEQUENCE` or implement dynamic allocation for the layer array.
- The deferred sparse circuit array feature (SPARSE-01/02/03) may need to be pulled forward.
- Use `@ql.compile` aggressively to capture and replay gate sequences rather than re-generating them (replay uses `inject_remapped_gates` which is more memory-efficient).

**Detection:** Segfaults during circuit generation. `ql.stats()` showing gate counts approaching 300K.

**Phase assignment:** Infrastructure preparation phase (before full circuit generation).

---

## Moderate Pitfalls

### Pitfall 6: Python Set to NumPy Migration Breaking frozenset Semantics in compile.py

**What goes wrong:** `compile.py` uses Python `set()` for `qubit_set` in ~6 locations, and `call_graph.py` uses `frozenset` for `DAGNode.qubit_set` with intersection operations for overlap detection. Migrating to numpy arrays changes semantics in breaking ways:
- numpy arrays are not hashable (cannot be used in frozensets or as dict keys)
- Set intersection becomes `np.intersect1d()` (sorts both arrays, O(n log n) instead of O(min(m,n)))
- Membership tests change from `x in set` (O(1) average) to `np.isin()` (O(n log n))
- The `bitmask` field on DAGNode already provides O(1) overlap detection via `popcount(a & b)` for arbitrary qubit counts (Python int has unlimited precision)

**Prevention:**
- Keep `frozenset` for `DAGNode.qubit_set` -- hashability is needed for cache key construction and set operations in `build_overlap_edges`.
- The existing bitmask approach is already optimal for overlap detection. `len(qs_i & qs_j)` on frozensets could be replaced with `bin(nodes[i].bitmask & nodes[j].bitmask).count('1')` if frozenset intersection is measured as a bottleneck.
- Use numpy only where large arrays of gates are processed (e.g., gate list manipulation in `_optimize_gate_list`), not for qubit set bookkeeping.
- Danger: replacing `qubit_set = set(); qubit_set.update(...)` with numpy concatenation introduces temporary array allocations that are slower for small qubit counts (< 100).

**Detection:** Benchmark regression in compile time. `TypeError: unhashable type: 'numpy.ndarray'`. Incorrect overlap detection changing merge group composition.

**Phase assignment:** Compile infrastructure optimization phase. Profile first, migrate only proven bottlenecks.

---

### Pitfall 7: Check Detection Requiring Full Board State Analysis in Superposition

**What goes wrong:** Determining if a king is "in check" after a move requires scanning the board for attacking pieces. In the quantum setting, every piece position is in superposition. A naive implementation checks all 64 squares for each piece type against all attack patterns. For knights alone, checking if any of up to 2 knights attacks the king involves: for each of 64 possible knight positions, check if a knight is there AND if that square attacks the king's position. That is 64 lookups + 8 attack-pattern comparisons = 512 controlled operations per knight.

**Prevention:**
- Pre-compute attack tables classically at circuit construction time. For each possible destination square of the moving king, the set of board squares from which an enemy piece could attack it is known classically (depends only on piece type and king destination, not board state).
- Encode check detection as: "is any opponent piece on a square in the king's attack footprint?" This reduces to OR-reduction over a small set of qarray element lookups.
- Use `board_array[rank, file]` access (which compiles to single-qubit controlled operations) to check specific squares, avoiding expensive general comparisons.
- For king-king adjacency: the 8 squares adjacent to the new king position are known classically. Check `opponent_king_array[r, f]` for each. That is 8 lookups + OR-reduction = ~20 gates.
- For knight attacks on king: the up-to-8 knight-attack squares for the king's new position are known classically. Check `knight_array[r, f]` for each. Also ~20 gates.

**Detection:** Qubit count or gate count doubling when check detection is added. Predicate function taking seconds to compile.

**Phase assignment:** Predicate design phase. Must use pre-computed attack tables from the start.

---

### Pitfall 8: Variable Branching Validity Ancillae Leaking Between Depth Levels

**What goes wrong:** The Montanaro walk requires R_A and R_B to act on disjoint qubit subsets at each depth level. When validity ancillae from one depth level's `apply_diffusion` call are not properly uncomputed and deallocated before the next depth level, the operators may share qubits, violating the walk's correctness.

**Why it happens:** The current `uncompute_children` function in `chess_walk.py` allocates NEW `reject` qbools during uncomputation (line 376: `reject = alloc_qbool()`), which means the uncompute path uses different physical qubits than the compute path. This is the "raw predicate qubit allocation" limitation.

**Consequences:** Validity ancillae from depth `d` remain allocated when processing depth `d-1`. The walk operators R_A and R_B, which should act on disjoint sets, end up sharing leaked ancilla qubits. Walk detection produces incorrect results.

**Prevention:**
- Strictly scope validity ancillae: allocate at `apply_diffusion` entry, uncompute before `apply_diffusion` exit (already attempted but broken by fresh qbool allocation in uncompute path).
- Use compiled predicates where the same physical ancillae are used in both compute and uncompute paths (via `@ql.compile(inverse=True)`).
- Add qubit set assertions verifying R_A qubits and R_B qubits are disjoint (the existing `all_walk_qubits` pattern can be extended).
- The `_make_qbool_wrapper(qubit_idx)` pattern from walk.py should be used in uncompute paths to reference the SAME physical qubit as the compute path, not allocate new ones.

**Detection:** Walk step compilation reporting qubit overlap between R_A and R_B components. Total qubit count increasing with each walk iteration.

**Phase assignment:** Walk operator integration phase. Depends on predicate architecture being correct first.

---

### Pitfall 9: Compile Cache Key Not Distinguishing Quantum Predicate Variants

**What goes wrong:** The `@ql.compile` cache key is built from argument widths and mode flags (`_get_mode_flags()`). If the legality predicate function is used with different move indices but the same argument widths, cache collisions cause the wrong gate sequence to be replayed.

**Why it happens:** The oracle uses a factory pattern (`_make_apply_move`) that creates distinct compiled functions per move list. If the rewrite consolidates predicates into fewer functions, the cache key distinction is lost.

**Prevention:**
- Use the `key=` parameter of `@ql.compile` to include predicate-distinguishing information: `@ql.compile(key=lambda *args: ("predicate", piece_type, level))`.
- Alternatively, the oracle forces `parametric=False` decision from v5.0 already handles this -- structural parameters require per-value caching. Follow this pattern for predicates.
- If using a single predicate function across multiple contexts, ensure the cache key captures the structural differences.

**Detection:** Replayed gate sequence having different gate count than the original capture. Statevector verification failures after cache warm-up.

**Phase assignment:** Compile infrastructure integration phase.

---

### Pitfall 10: 14-15 Pre-Existing test_compile.py Failures Masking New Regressions

**What goes wrong:** The known 14-15 pre-existing test failures in `test_compile.py` (qarray, replay gate count, nesting, auto-uncompute) create noise that masks new failures introduced by v8.0 changes. When numpy migration or predicate compilation introduces new bugs, they may be lost in the existing failure count.

**Why it happens:** No systematic tracking of which specific tests are known-failing. Developers compare total failure counts, which is unreliable when new failures cancel with fixed old ones.

**Prevention:**
- Before starting v8.0 work, create a baseline test run recording the exact set of failing tests by name and reason.
- Any new test failures not in the baseline set are regressions and must be fixed immediately.
- Consider adding `@pytest.mark.xfail(reason="pre-existing v7.0 failure")` to known failures so new failures are clearly visible in pytest output.
- Run `pytest tests/python/test_compile.py -v --tb=no` to get a clean pass/fail list for comparison.

**Detection:** Test count changing between runs. New `FAILED` entries not in the baseline.

**Phase assignment:** First action in v8.0 -- establish baseline before any code changes.

---

## Minor Pitfalls

### Pitfall 11: Board qarray Size at 64-Qubit qint Width Boundary

**What goes wrong:** Each board qarray is 8x8 = 64 qbools, which is exactly at the 64-qubit qint width limit. Three qarrays = 192 qubits. The `all_walk_qubits` function already works around this by passing board qarrays as separate `@ql.compile` arguments. But new predicate functions that need to reference multiple board arrays simultaneously may attempt to combine them into a single register, hitting the limit.

**Prevention:** Follow the existing pattern: pass board qarrays as separate `@ql.compile` arguments, never combine into a single qint. The compile infrastructure already supports multi-argument caching with `('arr', length)` cache key tuples.

---

### Pitfall 12: Move Index Encoding Wasting Branch Register States

**What goes wrong:** With 218 possible moves and an 8-bit branch register (256 states), 38 states are unused. If the circuit places the branch register in uniform superposition, these 38 "garbage" states produce invalid move applications.

**Prevention:** The quantum predicate approach naturally handles this: unused branch indices will have their validity ancilla set to |0> (invalid), so they contribute d(x) = 0 for those states. The diffusion correctly ignores them. Verify that the predicate evaluates to "reject" for out-of-range indices, not undefined behavior. Add explicit "index >= d_max implies reject" logic in the predicate.

---

### Pitfall 13: numpy Array Creation Overhead Slower Than Python Sets for Small Qubit Counts

**What goes wrong:** Replacing Python `set()` operations with numpy in compile.py introduces array creation overhead. Each `np.array()` call allocates memory and copies data. For small sets (< 50 elements, typical for most compiled functions), Python sets are faster due to numpy's fixed overhead of ~1-2 microseconds per array creation.

**Prevention:** Profile the actual hot paths before migrating. Focus on:
- `inject_remapped_gates`: processes lists of gate dicts -- potential numpy win for gate array operations.
- `_optimize_gate_list`: iterates gate lists for cancellation -- numpy structured arrays could help.
- `qubit_set` operations in `__call__`: typically < 100 qubits -- Python sets + bitmask approach is likely faster.

---

### Pitfall 14: Diffusion S_0 Reflection Gate Count Growing with Branch Width

**What goes wrong:** The S_0 zero-state reflection uses `ql.diffusion()` which applies an MCZ gate on the branch register. For 8-bit branch registers (218 moves), this is an 8-control MCZ, decomposing via AND-ancilla into ~6 Toffoli gates = 42 T-gates per S_0 call. Multiplied across depth levels, walk iterations, and forward + adjoint = significant T-count contribution.

**Prevention:** Acceptable but must be accounted for in circuit size estimates. Not a blocker. Consider pre-compiling the diffusion operator via `@ql.compile` for replay efficiency.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Diffusion redesign | Combinatorial explosion (P1) | CRITICAL | Arithmetic counting circuit, not pattern enumeration |
| Predicate architecture | Nested `with` limitation (P3) | CRITICAL | Flat Toffoli-AND decomposition, no nested controls |
| Predicate architecture | Qubit explosion (P2) | CRITICAL | Per-child ancilla recycling, compiled predicates |
| Oracle rewrite | Classical pre-filter assumption (P4) | CRITICAL | All-moves enumeration with quantum legality |
| Infrastructure | MAXLAYERINSEQUENCE overflow (P5) | CRITICAL | Gate count estimation, dynamic allocation |
| Check detection | Full-board scan cost (P7) | MODERATE | Pre-computed classical attack tables |
| Walk integration | Validity ancilla leaks (P8) | MODERATE | Compiled predicates with same-qubit uncompute |
| Compile cache | Key collisions (P9) | MODERATE | Use `key=` parameter, per-value caching |
| Test baseline | Masked regressions (P10) | MODERATE | xfail annotation before v8.0 work begins |
| Compile numpy | frozenset semantics break (P6) | MODERATE | Profile first, keep frozenset for DAGNode |
| Compile numpy | Array overhead for small sets (P13) | MINOR | Profile before migrating |
| Board encoding | 64-qubit width limit (P11) | MINOR | Separate qarray arguments pattern |
| Branch register | Wasted states (P12) | MINOR | Predicate rejects out-of-range indices |
| Diffusion | S_0 gate count (P14) | MINOR | Pre-compile, budget in estimates |

## Sources

- Direct codebase analysis: `src/chess_walk.py` (lines 250-540), `src/chess_encoding.py`, `src/quantum_language/walk.py`, `src/quantum_language/compile.py` (lines 830-1175), `src/quantum_language/call_graph.py`
- PROJECT.md known limitations: "Raw predicate qubit allocation", "QWalkTree nested `with qbool:` limitation", "14-15 pre-existing test failures in test_compile.py"
- PROJECT.md key decisions: factory pattern oracles, V-gate CCRy decomposition, oracle forces parametric=False
- `c_backend/include/types.h` line 50: `#define MAXLAYERINSEQUENCE 300000`
- Combinatorial analysis: sum of C(218, d) for d=1..218 = 2^218 - 1 (verified via Python computation)
- Confidence: HIGH -- all pitfalls derived from direct code inspection and mathematical analysis of existing algorithms
