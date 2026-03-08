# Stack Research

**Domain:** Quantum chess move legality in superposition + compile infrastructure optimization
**Researched:** 2026-03-08
**Confidence:** HIGH

## Recommended Stack

### Core Technologies (NO changes needed)

The existing stack is sufficient. No new core technologies are required for v8.0.

| Technology | Version | Purpose | Status for v8.0 |
|------------|---------|---------|-----------------|
| Python | 3.11+ (running 3.13.7) | Frontend language | Already installed, no change |
| NumPy | >=1.24 (running 2.4.2) | Array ops, qubit set optimization | Already installed, use MORE of it |
| Cython | >=3.0.11 | C bindings layer | Already installed, no change |
| C backend | Custom | Gate primitives, circuit management | Already installed, no change |
| rustworkx | 0.17.1 | Call graph DAG (CallGraphDAG) | Already installed, no change |

### Supporting Libraries (NO additions needed)

| Library | Version | Purpose | Status for v8.0 |
|---------|---------|---------|-----------------|
| Qiskit | 2.3.0 | Verification only (optional) | Already installed, no change |
| qiskit-aer | installed | Simulation verification | Already installed, no change |
| Pillow | >=9.0 | Circuit visualization | Already installed, no change |
| scipy | >=1.10 | Numerical utilities | Already installed, no change |

### Development Tools (NO additions needed)

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Testing | Already configured, use for new quantum predicate tests |
| ruff | Linting/formatting | Already configured |
| pytest-cov | Coverage | Already configured |

## What v8.0 Actually Needs: Deeper Use of Existing Stack

The milestone does NOT require new dependencies. It requires using numpy more aggressively in two areas and writing new quantum predicate logic using the existing ql.compile/qint/qbool/qarray infrastructure.

### 1. NumPy for Qubit Set Operations in Compile Infrastructure

**Current state:** `compile.py` and `call_graph.py` use Python `set()` and `frozenset()` for qubit tracking. The `DAGNode` already has a `bitmask` field (Python int with bit-per-qubit), but overlap computation in `build_overlap_edges()`, `parallel_groups()`, and `merge_groups()` still uses `frozenset` intersection (`len(qs_i & qs_j)`).

**What to change (no new deps):**

```python
# CURRENT (call_graph.py lines 208-215): O(n^2) frozenset intersection
for i in range(n):
    qs_i = self._nodes[i].qubit_set
    for j in range(i + 1, n):
        w = len(qs_i & self._nodes[j].qubit_set)

# OPTIMIZED: numpy boolean array intersection
# Pre-allocate matrix of shape (n_nodes, max_qubit+1), dtype=bool
# qubit_matrix[i, q] = True if node i touches qubit q
# Overlap = (qubit_matrix[i] & qubit_matrix[j]).sum()
# Or batch: overlap_matrix = qubit_matrix @ qubit_matrix.T
```

Key numpy operations to use:
- `np.zeros((n_nodes, max_qubit + 1), dtype=np.bool_)` for qubit membership matrix
- Matrix multiply `qubit_matrix.astype(np.int32) @ qubit_matrix.astype(np.int32).T` for all-pairs overlap in one shot
- `np.nonzero()` for extracting overlap edges from the result matrix
- Replace `bitmask` Python int loops with numpy bitwise ops for nodes with >64 qubits

**Why numpy over keeping bitmasks:** The bitmask approach (Python arbitrary-precision int) works for overlap checks but cannot batch across all node pairs. numpy matrix multiply computes ALL pairwise overlaps in a single vectorized call, which matters when the call graph has dozens of nodes (chess walk with per-move oracles).

**Why NOT use bitarray or other packages:** numpy is already a core dependency, already imported in compile.py. Adding another dependency for bit manipulation provides no benefit over numpy boolean arrays.

### 2. NumPy for Compile.py Gate Processing Loops

**Current state:** `compile.py` uses numpy minimally (only for `np.zeros(64, dtype=np.uint32)` in qubit index extraction at lines 613 and 654). The gate list optimizer iterates Python lists of dicts.

**What to change (no new deps):**

The qubit set construction in compile.py (lines 843-856, 885-894, 1154-1172) builds sets via Python loops:
```python
qubit_set = set()
for qa in quantum_args:
    qubit_set.update(_get_quantum_arg_qubit_indices(qa))
```

Replace with numpy array concatenation:
```python
qubit_arrays = [_get_quantum_arg_qubit_indices_array(qa) for qa in quantum_args]
all_qubits = np.unique(np.concatenate(qubit_arrays)) if qubit_arrays else np.array([], dtype=np.int32)
```

The bitmask computation (lines 1169-1171) can use numpy:
```python
# CURRENT: Python loop
bitmask = 0
for q in qubit_set:
    bitmask |= 1 << q

# OPTIMIZED: numpy reduce (for nodes with many qubits)
bitmask = int(np.bitwise_or.reduce(1 << np.array(list(qubit_set), dtype=np.int64)))
```

### 3. Quantum Move Legality Predicates (Pure ql.* API, no new deps)

**Current state:** `chess_encoding.py` uses classical pre-filtering. Move legality (piece exists, target not friendly, not in check) is evaluated classically at circuit construction time via `legal_moves_white()` / `legal_moves_black()`.

**What to build (using existing stack):**

All quantum legality checking uses existing ql infrastructure:
- `qarray` (8x8 qbool) for board state -- already exists
- `qbool` operations (AND, OR, NOT) for predicate logic -- already exists
- `@ql.compile(inverse=True)` for reversible predicates -- already exists
- `with qbool:` conditional blocks for controlled operations -- already exists
- `qint` comparisons for branch register matching -- already exists

No new quantum primitives needed. The legality predicate is pure composition:
```python
@ql.compile(inverse=True)
def is_legal(wk, bk, wn, src_rank, src_file, dst_rank, dst_file):
    # Check: piece exists at source (qbool read from board qarray)
    piece_present = wn[src_rank, src_file]  # qbool
    # Check: destination not same-color occupied
    dest_free = ~(wk[dst_rank, dst_file] | wn[dst_rank, dst_file])  # qbool ops
    # Combine: legal = piece_present & dest_free & ~in_check
    ...
```

### 4. Quantum Check Detection (Pure ql.* API, no new deps)

Check detection requires evaluating whether the king is attacked after a candidate move. This is a quantum predicate over the board state.

**Approach using existing stack:**
- Knight attack patterns are fixed (8 L-shaped offsets per square) -- compute classically, apply as quantum OR over those squares
- King adjacency is 8 squares -- same pattern
- For each candidate move: apply move (compiled oracle), evaluate attack pattern, record result, unapply move (inverse)
- All operations compose from existing `qbool`, `qarray`, `@ql.compile`

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| numpy bool matrix for overlaps | Keep frozenset intersection | When call graph has <10 nodes (not worth optimizing) |
| numpy bool matrix for overlaps | scipy.sparse for overlap matrix | When qubit indices are very sparse (>10K qubits); not needed for chess circuits |
| Python int bitmask (current) | numpy packed bitarray | When >1000 qubits per node; Python int is fine for chess-scale circuits |
| Inline check detection predicate | python-chess for attack computation | Never -- python-chess operates classically; we need quantum predicates over superposition states |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| python-chess | Classical chess library; cannot evaluate positions in quantum superposition | Custom quantum predicates using ql.qbool/qarray |
| Cirq / PennyLane | Would require rewriting circuit backend; project has its own | Existing ql.* framework |
| bitarray package | Extra dependency for something numpy already does | numpy boolean arrays |
| New C code for legality | Legality is compositional (AND/OR over board squares), not compute-intensive at gate level | Pure Python using existing @ql.compile |
| scipy.sparse for qubit sets | Overkill for chess-scale circuits (hundreds of qubits, not millions) | Dense numpy arrays |
| Numba JIT for compile loops | Adds complex dependency, compile.py loops are not pure-numerical | numpy vectorization of the hot paths |

## Stack Patterns by Variant

**For the qubit set optimization:**
- Use numpy `bool_` matrix when node count > 5 and max qubit index < 10K
- Keep frozenset as fallback/validation path for correctness testing
- The optimization is in `call_graph.py` (overlap computation) and `compile.py` (qubit set construction + bitmask computation)

**For quantum legality predicates:**
- Use `@ql.compile(inverse=True)` for all predicates (enables oracle use in walk)
- Separate predicates per piece type (knight_legal, king_legal) then combine
- Check detection as a sub-predicate called within legality predicate
- Classical pre-computation of attack patterns (which squares to check) done outside @ql.compile, quantum evaluation of board state inside

**For check detection specifically:**
- Pre-compute attack square offsets classically (these are geometric constants)
- In quantum predicate: OR over the relevant board squares to see if any attacker present
- Use qarray element access (already supports `board[rank, file]` indexing)

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| numpy 2.4.2 | Python 3.13, Cython 3.x | Already working in project |
| rustworkx 0.17.1 | Python 3.13 | Already working, used by CallGraphDAG |
| Qiskit 2.3.0 | Python 3.13 | Verification only, optional dependency |

No version changes needed. All packages are current and compatible.

## Installation

```bash
# No new packages to install. Existing dependencies cover v8.0 completely.
# The project's pyproject.toml already declares:
#   numpy>=1.24, Pillow>=9.0, scipy>=1.10
#   optional: qiskit>=1.0, qiskit-aer>=0.13, rustworkx (implicit via existing use)
```

## Integration Points for New Code

### compile.py changes (numpy qubit sets)
- `_get_quantum_arg_qubit_indices()` (line ~613): Already returns numpy array -- build on this
- DAG node creation blocks (lines ~843, ~885, ~1154): Replace set() accumulation with numpy concatenation
- `DAGNode.__init__` bitmask loop (call_graph.py line ~116): Replace with numpy bitwise reduce

### call_graph.py changes (numpy overlap matrix)
- `build_overlap_edges()` (line ~190): Replace O(n^2) frozenset loop with matrix multiply
- `parallel_groups()` (line ~219): Same optimization
- `merge_groups()` (line ~248): Same optimization

### chess_encoding.py changes (quantum predicates)
- Add new functions: `quantum_knight_legal()`, `quantum_king_legal()`, `quantum_check_detect()`
- These compose from existing `@ql.compile`, `qbool`, `qarray` -- no new imports
- Replace classical `legal_moves_white()` / `legal_moves_black()` filtering with quantum predicate evaluation

### chess_walk.py changes (predicate integration)
- Replace classical move pre-filtering with quantum predicate as walk tree branching condition
- Variable branching via predicate-driven child counting already exists in walk.py
- Integration point is the predicate function passed to walk operators

## Sources

- Project codebase analysis: `compile.py`, `call_graph.py`, `chess_encoding.py`, `chess_walk.py`
- `pyproject.toml` for dependency declarations
- Installed package versions verified via `pip show`
- numpy 2.4.2 boolean matrix multiply verified as standard numpy operation (no special API needed)

---
*Stack research for: Quantum chess move legality + compile optimization*
*Researched: 2026-03-08*
