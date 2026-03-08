# Architecture Research: Quantum Chess Walk Rewrite (v8.0)

**Domain:** Quantum move legality predicates + compile infrastructure optimization
**Researched:** 2026-03-08
**Confidence:** HIGH (based on direct codebase analysis of existing architecture)

## System Overview

### Current Architecture (v6.1)

```
Classical Layer (circuit construction time)
+-----------------------------------------------------------------+
|  chess_encoding.py                                              |
|  +---------------------------+  +-----------------------------+ |
|  | legal_moves_{white,black} |  | get_legal_moves_and_oracle  | |
|  | (Python set filtering)    |  | (_make_apply_move factory)  | |
|  +------------+--------------+  +--------------+--------------+ |
|               |                                |                |
|       Classical move list            @ql.compile(inverse=True)  |
|       (branch index = move index)    apply_move(wk,bk,wn,br)   |
+-----------------------------------------------------------------+
              |                                  |
Quantum Layer (gate emission)                    |
+-----------------------------------------------------------------+
|  chess_walk.py                                                  |
|  +-----------------------+  +-------------------------------+   |
|  | evaluate_children     |  | apply_diffusion               |   |
|  | (per-child loop:      |  | (O(2^d_max) pattern enum      |   |
|  |  encode branch,       |  |  via itertools.combinations)  |   |
|  |  oracle fwd/inv,      |  |                               |   |
|  |  TRIVIAL predicate)   |  |                               |   |
|  +-----------------------+  +-------------------------------+   |
|  +-------------------+  +-----------------------------------+   |
|  | r_a / r_b         |  | walk_step (compiled U=R_B*R_A)    |   |
|  +-------------------+  +-----------------------------------+   |
+-----------------------------------------------------------------+
              |
Compile Infrastructure
+-----------------------------------------------------------------+
|  compile.py                                                     |
|  +--------------------------------+                             |
|  | qubit_set: Python set()        |                             |
|  | built via repeated .update()   |                             |
|  | converted to frozenset         |                             |
|  +--------------------------------+                             |
|  call_graph.py                                                  |
|  +--------------------------------+                             |
|  | DAGNode.bitmask: Python int    |                             |
|  | built via loop: |= 1 << q     |                             |
|  | overlap: frozenset intersection|                             |
|  +--------------------------------+                             |
+-----------------------------------------------------------------+
```

### Target Architecture (v8.0)

```
Classical Layer (circuit construction time)
+-----------------------------------------------------------------+
|  chess_encoding.py (MODIFIED)                                   |
|  +---------------------------+  +-----------------------------+ |
|  | Raw move destinations     |  | encode_position (unchanged) | |
|  | knight_destinations(sq)   |  |                             | |
|  | king_destinations(sq)     |  |                             | |
|  | (ALL reachable squares,   |  |                             | |
|  |  no legality filtering)   |  |                             | |
|  +------------+--------------+  +-----------------------------+ |
+-----------------------------------------------------------------+
              |
Quantum Layer (gate emission)
+-----------------------------------------------------------------+
|  chess_predicates.py (NEW)                                      |
|  +---------------------------+  +----------------------------+  |
|  | piece_exists_on_source    |  | target_not_friendly        |  |
|  | (qbool = board[r,f])     |  | (qbool = ~board[r,f])      |  |
|  +---------------------------+  +----------------------------+  |
|  +---------------------------+  +----------------------------+  |
|  | king_not_in_check         |  | move_is_legal (AND of all) |  |
|  | (attack line enumeration) |  | @ql.compile(inverse=True)  |  |
|  +---------------------------+  +----------------------------+  |
|                                                                 |
|  chess_walk.py (MODIFIED)                                       |
|  +-----------------------------------------------------------+ |
|  | evaluate_children: uses chess_predicates.move_is_legal     | |
|  | instead of trivial always-valid predicate                  | |
|  +-----------------------------------------------------------+ |
+-----------------------------------------------------------------+
              |
Compile Infrastructure (MODIFIED)
+-----------------------------------------------------------------+
|  compile.py                                                     |
|  +--------------------------------+                             |
|  | qubit_set: numpy uint32 array  |                             |
|  | built via np.union1d           |                             |
|  | converted via np.unique        |                             |
|  +--------------------------------+                             |
|  call_graph.py                                                  |
|  +--------------------------------+                             |
|  | DAGNode.qubit_array: np.array  |                             |
|  | overlap: np.intersect1d        |                             |
|  | bitmask: Python int (kept)     |                             |
|  +--------------------------------+                             |
+-----------------------------------------------------------------+
```

## Component Responsibilities

| Component | Responsibility | New vs Modified | Integration Points |
|-----------|----------------|-----------------|-------------------|
| `chess_predicates.py` | Quantum legality checks: piece exists, no friendly capture, no self-check | **NEW** | Uses qarray element access, qbool, calls chess_encoding for attack tables |
| `chess_encoding.py` | Raw move destination generation (no legality filter) + board encoding | **MODIFIED** | Remove `legal_moves_*` filtering from oracle path; keep for classical use |
| `chess_walk.py` | Walk register scaffolding, evaluate_children with real predicates | **MODIFIED** | `evaluate_children` calls `chess_predicates.move_is_legal` instead of trivial predicate |
| `compile.py` | Gate capture/replay with numpy-based qubit set construction | **MODIFIED** | `_build_qubit_set` helper replaces 3 inline set-building blocks |
| `call_graph.py` | DAG node with numpy qubit arrays, vectorized overlap computation | **MODIFIED** | `DAGNode` stores `qubit_array`; overlap methods use `np.intersect1d` |

## Recommended Project Structure

```
src/
+-- chess_encoding.py       # Board encoding, attack tables, raw destinations
+-- chess_predicates.py     # NEW: quantum legality predicates
+-- chess_walk.py           # Walk registers, evaluate_children, r_a/r_b, walk_step
+-- quantum_language/
    +-- compile.py          # @ql.compile with numpy qubit_set helper
    +-- call_graph.py       # CallGraphDAG with numpy overlap
    +-- walk.py             # QWalkTree (unchanged)
    +-- ...
```

### Structure Rationale

- **chess_predicates.py at src/ level:** Same level as chess_encoding.py and chess_walk.py. These are application-level modules, not framework internals. chess_predicates imports from both chess_encoding (attack tables) and quantum_language (qbool, compile).
- **compile.py/call_graph.py modifications are internal:** The numpy optimization is transparent to callers. No API changes.

## Architectural Patterns

### Pattern 1: Quantum Predicate as Compiled Oracle

**What:** Each legality condition is a separate `@ql.compile(inverse=True)` function producing a qbool result. The top-level `move_is_legal` AND-combines them via Toffoli gates.
**When to use:** Whenever the walk framework needs to determine child validity in superposition.
**Trade-offs:**
- PRO: Each sub-predicate is independently testable; inverse is auto-generated for uncomputation
- PRO: Compiled predicates auto-uncompute their ancillae (solves known "raw predicate qubit allocation" limitation)
- CON: AND-combining qbools requires explicit multi-controlled gates (framework `with qbool:` cannot nest)
- CON: More compiled function invocations = more cache entries and DAG nodes

**Example:**
```python
@ql.compile(inverse=True)
def piece_exists_on_source(board_arr, src_rank, src_file):
    """Returns qbool |1> if board_arr[src_rank, src_file] == |1>."""
    return board_arr[src_rank, src_file]  # Already a qbool

@ql.compile(inverse=True)
def target_not_same_color(own_boards, dst_rank, dst_file):
    """Returns qbool |1> if no same-color piece at destination."""
    occupied = ql.qbool()
    for board in own_boards:
        occupied |= board[dst_rank, dst_file]
    return ~occupied
```

### Pattern 2: Classical Attack Table, Quantum Lookup

**What:** Attack tables (which squares a knight/king can reach) are precomputed classically. The quantum predicate iterates these tables at circuit construction time, emitting controlled gates only for relevant squares. No quantum arithmetic for move geometry.
**When to use:** For check detection -- "is the king attacked?" examines all squares that could attack the king.
**Trade-offs:**
- PRO: Zero quantum overhead for move enumeration (classical loop at construction time)
- PRO: Circuit size proportional to piece count, not board size
- CON: Board position must be known at construction time for attack table (consistent with existing oracle factory pattern)

**Example:**
```python
def king_not_in_check(board_arrs, king_sq, opponent_piece_type):
    """Quantum predicate: king on king_sq is not attacked."""
    in_check = ql.qbool()
    # Check opponent knight attacks on king_sq
    for attacker_sq in knight_attacks(king_sq):
        r, f = divmod(attacker_sq, 8)
        in_check |= board_arrs['knights'][r, f]
    # Check opponent king adjacency
    for adj_sq in king_attacks(king_sq):
        r, f = divmod(adj_sq, 8)
        in_check |= board_arrs['king'][r, f]
    return ~in_check  # Valid if NOT in check
```

### Pattern 3: Numpy Qubit Set Operations in Compile Infrastructure

**What:** Replace Python `set()` / `frozenset` / Python-loop bitmask computation with numpy `uint32` arrays and vectorized operations in compile.py and call_graph.py.
**When to use:** Every qubit set operation in compile infrastructure (3 sites in compile.py, 1 in call_graph.py init, 3 in call_graph.py overlap/parallel/merge).
**Trade-offs:**
- PRO: `np.intersect1d` / `np.union1d` faster than frozenset for typical qubit counts (50-300 qubits)
- PRO: Eliminates repeated `set.update()` calls
- CON: Python int bitmask for >64 qubits cannot be vectorized in numpy (uint64 max); bitmask loop stays as Python int
- CON: Requires converting to/from numpy at API boundaries

**Critical constraint:** The bitmask MUST remain a Python `int` because chess walk circuits exceed 64 qubits. Numpy uint64 would silently overflow. Optimize the set operations with numpy; leave bitmask as Python int.

**Example:**
```python
# compile.py -- new helper
def _build_qubit_set(quantum_args, capture_vtr=None):
    """Build qubit set from quantum args + capture mapping."""
    arrays = [_get_quantum_arg_qubit_indices(qa) for qa in quantum_args]
    if capture_vtr:
        arrays.append(np.array(list(capture_vtr.values()), dtype=np.uint32))
    if arrays:
        return np.unique(np.concatenate(arrays))
    return np.array([], dtype=np.uint32)

# call_graph.py -- DAGNode with dual storage
class DAGNode:
    def __init__(self, func_name, qubit_set, gate_count, cache_key, **kw):
        self.qubit_array = np.array(sorted(qubit_set), dtype=np.uint32)
        self.qubit_set = frozenset(qubit_set)  # Backward compat
        # Bitmask stays as Python int for >64 qubit support
        bitmask = 0
        for q in self.qubit_array:
            bitmask |= 1 << int(q)
        self.bitmask = bitmask

# call_graph.py -- vectorized overlap
def build_overlap_edges(self):
    for i in range(n):
        arr_i = self._nodes[i].qubit_array
        for j in range(i + 1, n):
            w = len(np.intersect1d(arr_i, self._nodes[j].qubit_array))
            if w > 0 and (i, j) not in call_pairs:
                self._dag.add_edge(i, j, {"type": "overlap", "weight": w})
```

### Pattern 4: Predicate Integration in evaluate_children

**What:** The existing evaluate_children loop replaces the trivial `reject = qbool()` (always valid) with a real quantum predicate call. The oracle itself stays unchanged -- the predicate is separate.
**When to use:** In `evaluate_children` (chess_walk.py lines 250-328), between steps (c) oracle apply and (f) oracle inverse.
**Trade-offs:**
- PRO: Oracle and predicate are cleanly separated
- PRO: Predicate is compiled, so its ancillae are auto-uncomputed
- CON: More qubits per child evaluation = higher total qubit count
- CON: Predicate must be uncomputed before oracle inverse

**Current code (trivial predicate):**
```python
# Step (d) -- trivial, always valid
reject = alloc_qbool()  # Always |0>
reject_ctrl = _make_qbool_wrapper(reject_qubit)
with reject_ctrl:
    emit_x(validity_qubit)
emit_x(validity_qubit)
```

**Target code (real predicate):**
```python
# Step (d) -- quantum legality check
from chess_predicates import move_is_legal
move_spec = move_data['moves'][i]
src_rank, src_file = divmod(move_spec[0], 8)
dst_rank, dst_file = divmod(move_spec[1], 8)

is_legal = move_is_legal(board_arrs, src_rank, src_file, dst_rank, dst_file, side)
legal_qubit = int(is_legal.qubits[63])
legal_ctrl = _make_qbool_wrapper(legal_qubit)
with legal_ctrl:
    emit_x(validity_qubit)
# is_legal is positive-sense: no extra flip needed
```

## Data Flow

### Move Legality Check Flow (NEW)

```
Branch Register = i (child index)
    |
    v
Oracle Forward: apply_move(board, branch=i)
    |
    v
Board State at Child Node
    |
    +--> piece_exists_on_source(board, src) --> qbool p1
    +--> target_not_friendly(board, dst)    --> qbool p2
    +--> king_not_in_check(board, king_sq)  --> qbool p3
    |
    v
validity[i] = p1 AND p2 AND p3  (via Toffoli/multi-controlled-X)
    |
    v
Uncompute predicates (compiled inverse)
    |
    v
Oracle Inverse: apply_move.inverse(board, branch=i)
    |
    v
Board State Restored
```

### Compile Infrastructure Qubit Set Flow (MODIFIED)

```
Current:
  quantum_args --> set() --> .update() loop --> frozenset --> Python loop bitmask

Target:
  quantum_args --> np.array(uint32) --> np.concatenate + np.unique --> frozenset + Python int bitmask
                                           |
                       np.intersect1d for overlap computation in call_graph.py
```

### Key Data Flows

1. **Predicate evaluation flow:** For each child in evaluate_children, oracle applies move to board state in superposition, then chess_predicates checks legality on the resulting state, stores result in validity ancilla, then oracle inverse restores board.
2. **Qubit set construction flow:** `_build_qubit_set()` collects physical qubit indices from quantum args and capture mappings into numpy arrays, concatenates, and deduplicates via `np.unique()`.

## Integration Points

### New Component to Existing Component

| New/Modified | Integrates With | How | Notes |
|--------------|-----------------|-----|-------|
| `chess_predicates.py` | `chess_encoding.py` | Imports `knight_attacks`, `king_attacks` | Attack functions already exist, pure-classical |
| `chess_predicates.py` | `quantum_language` | Uses `ql.qbool`, `ql.compile`, qarray element access | Standard framework operations |
| `chess_predicates.py` | `chess_walk.py` | Called from `evaluate_children` step (d) | Replaces trivial predicate |
| `chess_walk.py` (modified) | `chess_predicates.py` | Imports `move_is_legal` | New dependency |
| `compile.py` (modified) | numpy | `np.unique`, `np.concatenate` | numpy already imported |
| `call_graph.py` (modified) | numpy | `np.intersect1d`, `np.array` | Needs new numpy import |

### Internal Boundaries

| Boundary | Communication | Considerations |
|----------|---------------|----------------|
| chess_predicates <--> chess_walk | Function call returning qbool | Predicate must use `@ql.compile(inverse=True)` for clean uncomputation |
| chess_predicates <--> board qarrays | Element access: `board[rank, file]` | Existing qarray indexing; no new infrastructure |
| compile.py qubit_set <--> call_graph.py | numpy array passed to `DAGNode.__init__` | DAGNode accepts both set and numpy array |
| chess_walk <--> move data | Dict with 'moves' key per level | v8.0 provides ALL possible destinations, not just legal ones |

## Anti-Patterns

### Anti-Pattern 1: Embedding Legality in the Oracle

**What people do:** Put legality checks inside `_make_apply_move` so the oracle only applies legal moves.
**Why it is wrong:** After depth > 0, board state is in superposition. The oracle cannot know which moves are legal at circuit construction time because legality depends on superposition state. Legality must be checked AFTER the oracle applies the move.
**Do this instead:** Keep oracle as pure move application. Check legality via separate quantum predicate on the resulting board state.

### Anti-Pattern 2: Numpy for Bitmask Arithmetic on >64 Qubit Sets

**What people do:** Use `np.uint64` arrays for bitmask operations assuming numpy handles arbitrary precision.
**Why it is wrong:** Numpy integers are fixed-width. For chess walk with 100+ qubits, bit 100 cannot be represented in uint64. Silent overflow produces incorrect overlap detection.
**Do this instead:** Use numpy only for set operations (intersect, union). Keep bitmask as Python `int`. Use `len(np.intersect1d(...))` instead of bitmask popcount for overlap weight.

### Anti-Pattern 3: Raw Qbool Allocation per Predicate Without Compilation

**What people do:** Each predicate sub-check allocates a fresh qbool without `@ql.compile`.
**Why it is wrong:** Known limitation: "Raw predicate qubit allocation in QWalkTree: each predicate call allocates new qbools, making SAT demos infeasible at depth >= 2 without compiled predicates."
**Do this instead:** Compile each predicate with `@ql.compile(inverse=True)`. Compiled predicates auto-uncompute ancillae. Only the final validity qbool persists.

### Anti-Pattern 4: Nesting `with qbool:` for Predicate AND

**What people do:** Nest `with p1:` / `with p2:` blocks to AND-combine predicate results.
**Why it is wrong:** Known limitation: "Nested quantum conditionals require quantum-quantum AND implementation (future work)" and "Framework `with qbool:` cannot nest."
**Do this instead:** Use explicit Toffoli (CCX) gates or multi-controlled X to compute AND into an ancilla within a compiled function.

## Key Architectural Decisions

### Decision 1: Predicate Separate from Oracle

The move oracle (apply_move) must NOT include legality checking. Reasons:
1. Oracle encodes piece movements; predicate checks legality on resulting state
2. Separation enables independent testing of predicates
3. Walk framework already separates "navigate to child" from "evaluate predicate"
4. Oracle is compiled once per position; predicate evaluates per child in superposition

### Decision 2: Classical Move Enumeration Stays

Move ENUMERATION (which squares can a knight reach?) stays classical even though predicates are quantum. The quantum part only answers "is this reachable square actually legal given the current superposition state?" Reasons:
1. Move geometry (L-shape, adjacency) is fixed, not state-dependent
2. Only blocking/check conditions depend on superposition
3. Branch register width is determined at construction time

### Decision 3: Compile Infrastructure Gets Numpy via Helper Function

The numpy optimization is introduced as a helper function `_build_qubit_set()` called from the 3 existing sites in compile.py (lines 843-845, 885-887, 1154-1158) and adapted DAGNode in call_graph.py. This is a refactor, not a redesign:
1. Extract `_build_qubit_set(quantum_args, capture_vtr=None) -> np.ndarray`
2. In DAGNode, store `qubit_array` alongside `qubit_set` for numpy-fast overlap
3. Update `build_overlap_edges`, `parallel_groups`, `merge_groups` to use `np.intersect1d`
4. Keep `frozenset` on DAGNode for backward compatibility

### Decision 4: Keep Python Int Bitmask

Bitmask remains Python `int` (not numpy). Chess walk uses 100+ qubits; numpy uint64 would overflow. The bitmask construction loop is NOT the bottleneck -- the set operations (union, intersection) are. Optimize sets with numpy; leave bitmask as Python int.

## Qubit Budget Analysis

For KNK endgame at depth 1:

| Register | Qubits | Notes |
|----------|--------|-------|
| White king board | 64 (8x8 qbool) | Full board representation |
| Black king board | 64 | |
| White knights board | 64 | |
| Height register | 2 (depth 0,1) | One-hot encoding |
| Branch registers | ~4 per level | ceil(log2(max_moves)) |
| Validity ancillae | ~8 per level | One per possible child |
| Predicate ancillae | ~3 per child eval | Compiled, auto-uncomputed |
| **Total** | ~210 | Exceeds 17-qubit sim limit |

**Testing strategies given 17-qubit simulation constraint:**
1. Unit-test predicates on tiny boards (2x2, 3x3) within qubit budget
2. Test walk structure with mock predicates using fewer qubits
3. Verify circuit structure (gate counts, qubit wiring) without simulation
4. Use matrix_product_state simulator for medium circuits if needed

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| KNK (3 pieces) | Full 8x8 board qarrays; ~200 qubits; predicates check knight+king attacks |
| KNNK (4 pieces) | Add second knight array; ~260 qubits; predicate unchanged |
| General endgame | Board representation needs redesign (one qarray per piece type = O(types * 64)) |

### Scaling Priorities

1. **First bottleneck: apply_diffusion O(2^d_max)** -- For d_max = 8 (knight moves), the inner loop runs C(8,1)+...+C(8,8) = 255 iterations. Each emits multi-controlled gates. Mitigation: Hamming-weight-based rotation (future, not blocking v8.0 correctness).

2. **Second bottleneck: Qubit count** -- Each child evaluation needs oracle forward + predicate + oracle inverse. Compiled predicates auto-uncompute ancillae, but validity qbools (d_max of them) persist until uncompute_children.

## Suggested Build Order

Build order follows dependency chain. Each phase is independently testable.

### Phase A: Compile Infrastructure Numpy (no chess dependencies)
1. `_build_qubit_set` helper in compile.py
2. DAGNode dual storage (`qubit_array` + `qubit_set`)
3. Numpy overlap in call_graph.py (`np.intersect1d` in build_overlap_edges, parallel_groups, merge_groups)
4. Verification: run existing 186+ compile tests for equivalence

### Phase B: Chess Predicates (depends on framework, not Phase A)
1. `chess_predicates.py` module with sub-predicates
2. Unit tests per predicate on known board positions
3. Check detection correctness against classical attack tables

### Phase C: Walk Integration (depends on Phase B)
1. Modify `chess_encoding.py` for raw destination generation
2. Modify `evaluate_children` to use `move_is_legal`
3. Modify `prepare_walk_data` for raw destinations
4. End-to-end test on small KNK position

### Phase D: apply_diffusion Optimization (optional, depends on Phase C)
1. Profile O(2^d_max) pattern enumeration
2. If bottleneck: replace with Hamming-weight controlled rotation

## Sources

- Direct codebase analysis: `chess_walk.py`, `chess_encoding.py`, `compile.py`, `call_graph.py`, `walk.py`
- PROJECT.md known limitations and key decisions
- Montanaro 2015 (arXiv:1509.02374) for walk operator structure

---
*Architecture research for: Quantum Chess Walk Rewrite v8.0*
*Researched: 2026-03-08*
