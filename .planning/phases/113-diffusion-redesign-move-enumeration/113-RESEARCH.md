# Phase 113: Diffusion Redesign & Move Enumeration - Research

**Researched:** 2026-03-08
**Domain:** Quantum walk diffusion operator redesign, chess move enumeration
**Confidence:** HIGH

## Summary

Phase 113 replaces the combinatorial explosion in the current variable-branching diffusion with an arithmetic counting circuit, and creates a fixed all-moves enumeration table based on piece-type geometric offsets. The current implementation in both `walk.py:_variable_diffusion()` and `chess_walk.py:apply_diffusion()` iterates over all `itertools.combinations(range(d_max), d_val)` patterns for each d_val from 1 to d_max -- this is O(2^d_max) total patterns, which is intractable for d_max=24 (the KNK endgame branching factor for white).

The replacement design sums validity bits into a count register using `qarray.sum()`, then dispatches rotations via `count == d_val` comparison in an O(d_max) loop. The move enumeration table provides a fixed mapping from branch index to (piece_id, dx, dy) that is computed classically at circuit construction time.

**Primary recommendation:** Implement the counting circuit first (it is the critical path), verify equivalence on small cases (d_max=2,3,4) via statevector comparison against the old combinatorial code, then build the move table and integrate.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Counting circuit uses qarray sum reduction (`sum(validity_arr)`) to sum validity bits into a count register
- Count register width: `ceil(log2(d_max + 1))` qubits, computed dynamically
- Wrap counting logic in `@ql.compile(inverse=True)` for clean forward/inverse lifecycle
- Compare-and-rotate loop: iterate d from 1 to d_max, compare `count == d`, then controlled-Ry(phi(d)) -- O(d_max) iterations, each O(w) gates
- S_0 reflection stays unchanged: `ql.diffusion(h_child, branch_reg)` controlled on h[depth]
- Cascade rotations still operate on branch register qubits, controlled by count comparison flag
- Validity-gated cascade: only rotate into branch states for valid children, using `with validity[i]:` as control on each cascade Ry
- Fixed move indices based on (piece_instance, geometric_offset) -- NOT a flat list of all (src, dst) pairs
- d_max = 8 per piece x number of pieces: white KNK = 24 (K:8 + N1:8 + N2:8), black K = 8
- Python precomputation function: takes classically known piece configuration, returns move table mapping branch index to (piece_id, dx, dy offset)
- Piece positions are in superposition; piece configuration (which types exist) is classically known
- Table is a Python-level data structure (not quantum-encoded) -- oracle reads it at circuit construction time
- Separate tables per side: white and black have independent move tables with different sizes and branch register widths
- Replace old combinatorial diffusion entirely in both walk.py and chess_walk.py -- no coexistence
- chess_walk.py shares the new diffusion from walk.py (single implementation, no duplication)
- Verify equivalence via statevector comparison on small cases (d_max=2, 3, 4) before removing old code
- Existing walk tests (SAT demo, reflection property tests) must pass with the new counting-based diffusion

### Claude's Discretion
- Exact qarray sum reduction implementation details (handling of 1-bit width elements)
- Cascade angle computation internals (reuse existing `_plan_cascade_ops` or redesign)
- Module organization for the shared diffusion function (method on QWalkTree vs standalone)
- How the move table builder handles edge-of-board filtering for geometric offsets

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WALK-01 | All-moves enumeration table precomputes every geometrically possible (piece_type, src, dst) triple for knights (8 per square) and kings (8 per square) | Move table builder using existing `_KNIGHT_OFFSETS` and `_KING_OFFSETS` from chess_encoding.py; edge-of-board filtering via rank/file bounds check |
| WALK-03 | Diffusion operator redesigned with arithmetic counting circuit (sum validity bits into count register) replacing O(2^d_max) itertools.combinations enumeration | qarray.sum() for popcount, qint.__eq__ for comparison dispatch, @ql.compile(inverse=True) for lifecycle management |
</phase_requirements>

## Standard Stack

### Core
| Library/Module | Location | Purpose | Why Standard |
|----------------|----------|---------|--------------|
| `qarray.sum()` | `qarray.pyx:652` | Popcount of validity bits into count register | Framework's own tree reduction, handles qbool elements, returns qint |
| `qint.__eq__` | `qint_comparison.pxi:6` | Compare count register to classical d value | O(n) gate CQ_equal_width circuit, returns qbool usable as control |
| `@ql.compile(inverse=True)` | `compile.py:1959` | Forward/inverse lifecycle for counting logic | Established pattern for automatic uncomputation |
| `ql.diffusion()` | `diffusion.py:77` | S_0 reflection operator | Unchanged from current implementation |
| `_plan_cascade_ops()` | `walk.py:50` | Pre-compute cascade Ry operations for d-way superposition | Existing infrastructure, handles up to 2 control levels |
| `_emit_multi_controlled_ry()` | `walk.py:291` | Multi-controlled Ry with V-gate decomposition | Handles arbitrary control depth via recursive peeling |
| `_emit_cascade_multi_controlled()` | `walk.py:385` | Execute cascade ops with additional controls | Forward/inverse via sign parameter |

### Supporting
| Module | Location | Purpose | When to Use |
|--------|----------|---------|-------------|
| `chess_encoding._KNIGHT_OFFSETS` | `chess_encoding.py:41` | 8 L-shaped offsets for knights | Move table generation |
| `chess_encoding._KING_OFFSETS` | `chess_encoding.py:53` | 8 adjacency offsets for kings | Move table generation |
| `chess_encoding.knight_attacks()` | `chess_encoding.py:103` | Board-aware attack squares | Reference for validation, but move table uses raw offsets |
| `chess_encoding.king_attacks()` | `chess_encoding.py:125` | Board-aware attack squares | Reference for validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| qarray.sum() for popcount | Manual ripple-carry adder tree | qarray.sum() already implements tree reduction; custom adder adds no benefit |
| qint == d_val for dispatch | Bit-pattern matching on count register | qint.__eq__ uses CQ_equal_width (O(n) gates), cleaner than manual bit checks |
| Reuse _plan_cascade_ops | Redesign cascade planning | Existing cascade handles up to 2 controls; for d_max=24 with 5-bit branch, the cascade depth is manageable. Reuse is safer. |

## Architecture Patterns

### Recommended Module Organization

The new counting-based diffusion should be a standalone function in `walk.py` (or a method on QWalkTree) that both `QWalkTree._variable_diffusion` and `chess_walk.apply_diffusion` delegate to. This avoids code duplication.

```
src/
  quantum_language/
    walk.py              # Add _counting_diffusion() replacing _variable_diffusion()
                         # QWalkTree.local_diffusion delegates to counting version
  chess_walk.py          # apply_diffusion() calls shared function from walk.py
  chess_encoding.py      # Add build_move_table() for all-moves enumeration
```

### Pattern 1: Counting Circuit for Variable Diffusion

**What:** Replace itertools.combinations enumeration with arithmetic popcount + compare-and-rotate dispatch.

**When to use:** Always (replaces old code entirely).

**Current (BROKEN for large d_max):**
```python
# O(2^d_max) -- EXPONENTIAL in d_max
for d_val in range(1, d_max + 1):
    for pattern in itertools.combinations(range(d_max), d_val):
        zeros = [j for j in range(d_max) if j not in pattern]
        for z in zeros:
            emit_x(validity_qubits[z])
        # ... rotations controlled on ALL validity qubits ...
        for z in zeros:
            emit_x(validity_qubits[z])
```

**New (O(d_max)):**
```python
# Step 1: Sum validity bits into count register
validity_arr = ql.qarray(validity, dtype=ql.qbool)  # wrap list of qbool
count = validity_arr.sum(width=count_width)  # popcount -> qint

# Step 2: For each possible d value, compare and rotate
for d_val in range(1, d_max + 1):
    cond = (count == d_val)  # qbool
    with cond:
        # Parent-child Ry split
        emit_ry(h_child_qubit, phi(d_val))
        # Cascade into branch states (validity-gated)
        for i in range(d_max):
            with validity[i]:
                # Cascade Ry for child i's branch state
                ...

# Step 3: S_0 reflection (unchanged)
with h_control:
    diffusion(h_child, branch_reg)

# Step 4: Forward U (mirror of step 2)
# ... same structure, forward angles ...

# Step 5: Uncompute count register via @ql.compile inverse
```

### Pattern 2: Move Enumeration Table

**What:** Pre-compute a fixed table of all geometrically possible moves indexed by (piece_instance, offset_index).

**When to use:** At circuit construction time, before any quantum operations.

```python
def build_move_table(piece_config):
    """Build all-moves enumeration table.

    Args:
        piece_config: dict mapping piece_id to piece_type
            e.g., {"wk": "king", "wn1": "knight", "wn2": "knight"}

    Returns:
        list of (piece_id, dx, dy) tuples indexed by branch index
    """
    table = []
    for piece_id, piece_type in piece_config.items():
        offsets = _KNIGHT_OFFSETS if piece_type == "knight" else _KING_OFFSETS
        for dx, dy in offsets:
            table.append((piece_id, dx, dy))
    return table
```

**Key insight:** The table always has exactly `8 * num_pieces` entries (8 offsets per piece type for both knights and kings). Edge-of-board filtering is NOT done here -- it becomes part of the quantum validity predicate (Phase 114-115). The branch register encodes which table entry is being evaluated.

### Pattern 3: @ql.compile(inverse=True) Lifecycle

**What:** Wrap the count computation so it can be cleanly uncomputed after diffusion rotations.

```python
@ql.compile(inverse=True)
def compute_count(validity_arr, count_reg):
    """Compute popcount of validity bits into count register."""
    result = validity_arr.sum(width=count_reg.width)
    # Copy result into count_reg (or return and use directly)
    ...

# Usage:
compute_count(validity_arr, count_reg)      # Forward
# ... do diffusion rotations using count_reg ...
compute_count.inverse(validity_arr, count_reg)  # Uncompute
```

### Anti-Patterns to Avoid
- **Enumerating combinations:** The entire point of this phase is eliminating `itertools.combinations`. Never iterate over bit patterns of validity qubits.
- **Raw gate emission for counting:** Use `qarray.sum()` and `qint == d_val` -- the framework provides these as standard constructs.
- **Duplicate diffusion implementations:** chess_walk.py must call the same function as walk.py, not maintain a separate copy.
- **Filtering moves in the enumeration table:** The table contains ALL geometric moves. Legality filtering is the quantum predicate's job (Phase 114-115). Including legality filtering here defeats the purpose of quantum superposition evaluation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Popcount of validity bits | Manual adder tree with carry qubits | `qarray.sum()` | Already implements balanced tree reduction with proper width handling |
| Integer comparison | Bit-level equality gates | `qint.__eq__` (the `==` operator) | Uses C-level CQ_equal_width, handles controlled context, returns proper qbool |
| Uncomputation of count register | Manual inverse gate sequence | `@ql.compile(inverse=True)` + `.inverse()` | Framework records and reverses gate sequence automatically |
| S_0 reflection | Manual X-MCZ-X pattern | `ql.diffusion()` | Already compiled, handles arbitrary register sizes |
| Multi-controlled Ry | Custom Toffoli decomposition | `_emit_multi_controlled_ry()` | V-gate recursive decomposition, handles arbitrary control depth |

**Key insight:** Every building block for the counting circuit already exists in the framework. The phase is about wiring them together in the correct order, not implementing new primitives.

## Common Pitfalls

### Pitfall 1: qarray.sum() width for qbool elements
**What goes wrong:** `qarray.sum()` of qbool elements may default to 1-bit width, causing overflow for count > 1.
**Why it happens:** qbool has width 1; tree addition of 1-bit values needs explicit width override.
**How to avoid:** Pass `width=ceil(log2(d_max + 1))` to `.sum()`. Verify the returned qint has correct width.
**Warning signs:** Count register always reads 0 or 1 regardless of actual validity count.

### Pitfall 2: Count register == comparison under controlled context
**What goes wrong:** `count == d_val` returns a qbool, but using `with cond:` inside a loop creates nested controlled contexts which may interact with the h[depth] control.
**Why it happens:** The framework's `with qbool:` sets a global controlled flag; nesting can exceed supported depth.
**How to avoid:** Structure the dispatch so the h[depth] control is applied at the outermost level, and count==d_val is the inner control. Alternatively, use `_emit_multi_controlled_ry` with explicit control qubits (avoiding nested `with`).
**Warning signs:** Incorrect gate emission, gates applied unconditionally, or `with qbool:` nesting errors.

### Pitfall 3: Cascade rotation controls with counting circuit
**What goes wrong:** The cascade ops from `_plan_cascade_ops` are designed for controls on validity qubits. Switching to count-based control changes the control structure.
**Why it happens:** The old code controlled cascade on ALL validity qubits (the pattern). The new code controls on the count comparison qbool and individual validity[i] qbools.
**How to avoid:** The cascade Ry for branch state preparation must be controlled on: (1) h[depth], (2) count==d_val, and (3) validity[i] for the specific child. Use `_emit_multi_controlled_ry` with these 3 controls.
**Warning signs:** Branch register amplitudes don't match expected equal superposition over valid children.

### Pitfall 4: Forgetting to uncompute the count register
**What goes wrong:** Count register qubits remain entangled with validity qubits after diffusion, corrupting the walk.
**Why it happens:** The count register is computed from validity bits; if not uncomputed, it persists as garbage.
**How to avoid:** Use `@ql.compile(inverse=True)` for the counting step. Call `.inverse()` after both U_dagger * S_0 * U phases are done (but before uncomputing validity).
**Warning signs:** Extra qubits in entangled state, norm not preserved after full diffusion cycle.

### Pitfall 5: Move table size vs branch register width mismatch
**What goes wrong:** Branch register is too narrow to index all entries in the move table, or too wide (wasting qubits).
**Why it happens:** d_max = 8 * num_pieces. For white KNK: d_max=24, branch_width=ceil(log2(24))=5. For black K: d_max=8, branch_width=3. Off-by-one in width calculation.
**How to avoid:** `branch_width = ceil(log2(d_max))` when d_max is a power of 2, otherwise `ceil(log2(d_max))` may need +1. Verify: `2**branch_width >= d_max`.
**Warning signs:** Branch register cannot represent the highest move index.

### Pitfall 6: Validity-gated cascade for invalid table entries
**What goes wrong:** For branch indices beyond the number of valid children, the cascade creates garbage superposition.
**Why it happens:** Branch register can encode up to 2^w states but only d_max are meaningful. For d_max=24 with w=5, indices 24-31 are invalid.
**How to avoid:** The validity-gated cascade naturally handles this -- only children with validity[i]=|1> participate. Children beyond d_max have no validity qubit and get no amplitude.
**Warning signs:** Non-zero amplitude on branch register values >= d_max.

### Pitfall 7: Statevector comparison fails due to ancilla qubit count difference
**What goes wrong:** When comparing old vs new diffusion statevectors, the new code allocates different ancilla counts (count register qubits), making direct comparison impossible.
**Why it happens:** The counting circuit uses additional qubits not present in the old implementation.
**How to avoid:** Compare only the amplitudes on the subspace of the original qubits (height + branch registers). Use partial trace or project onto the original qubit subspace.
**Warning signs:** Statevector dimensions differ between old and new implementations.

## Code Examples

### Example 1: Building the Move Table

```python
# Source: chess_encoding.py patterns + CONTEXT.md decision
_KNIGHT_OFFSETS = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
_KING_OFFSETS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

def build_move_table(pieces):
    """Build all-moves enumeration table for one side.

    Args:
        pieces: list of (piece_id, piece_type) pairs
            e.g., [("wk", "king"), ("wn1", "knight"), ("wn2", "knight")]

    Returns:
        list of (piece_id, dr, df) where dr/df are rank/file deltas.
        Length = 8 * len(pieces). Index = branch register value.
    """
    table = []
    for piece_id, piece_type in pieces:
        offsets = _KNIGHT_OFFSETS if piece_type == "knight" else _KING_OFFSETS
        for dr, df in offsets:
            table.append((piece_id, dr, df))
    return table

# White KNK: 3 pieces * 8 offsets = 24 entries
white_table = build_move_table([("wk","king"),("wn1","knight"),("wn2","knight")])
assert len(white_table) == 24

# Black K: 1 piece * 8 offsets = 8 entries
black_table = build_move_table([("bk","king")])
assert len(black_table) == 8
```

### Example 2: Counting-Based Diffusion Core Loop

```python
# Source: Framework APIs verified in qarray.pyx:652 and qint_comparison.pxi:6
import math
import quantum_language as ql

def counting_diffusion(validity, d_max, branch_reg, h_qubit_idx, h_child_idx,
                       angles, root_angles, is_root):
    """Core counting-based diffusion replacing combinatorial enumeration.

    O(d_max) gate complexity instead of O(2^d_max).
    """
    count_width = math.ceil(math.log2(d_max + 1))

    # Step 1: Compute popcount
    validity_arr = ql.qarray(validity, dtype=ql.qbool)
    count = validity_arr.sum(width=count_width)

    # Step 2: U_dagger -- compare-and-rotate for each d value
    for d_val in range(1, d_max + 1):
        phi_d = angles[d_val]["phi"]
        if is_root:
            phi_d = root_angles.get(d_val, phi_d)

        cond = (count == d_val)
        ctrl_qubits = [h_qubit_idx, int(cond.qubits[63])]

        # Inverse cascade then inverse parent-child split
        cascade_ops_d = angles[d_val]["cascade_ops"]
        if d_val > 1 and cascade_ops_d:
            # Validity-gated cascade: each child i controlled on validity[i]
            _emit_cascade_validity_gated(branch_reg, cascade_ops_d,
                                          ctrl_qubits, validity, d_max, sign=-1)
        _emit_multi_controlled_ry(h_child_idx, -phi_d, ctrl_qubits)

    # Step 3: S_0 reflection (unchanged)
    h_control = _make_qbool_wrapper(h_qubit_idx)
    h_child = _make_qbool_wrapper(h_child_idx)
    with h_control:
        diffusion(h_child, branch_reg)

    # Step 4: U forward (mirror of step 2, positive angles)
    for d_val in range(1, d_max + 1):
        phi_d = angles[d_val]["phi"]
        if is_root:
            phi_d = root_angles.get(d_val, phi_d)

        cond = (count == d_val)
        ctrl_qubits = [h_qubit_idx, int(cond.qubits[63])]

        _emit_multi_controlled_ry(h_child_idx, phi_d, ctrl_qubits)
        cascade_ops_d = angles[d_val]["cascade_ops"]
        if d_val > 1 and cascade_ops_d:
            _emit_cascade_validity_gated(branch_reg, cascade_ops_d,
                                          ctrl_qubits, validity, d_max, sign=1)

    # Step 5: Uncompute count register
    # (handled by @ql.compile inverse lifecycle)
```

### Example 3: Edge-of-Board Filtering in Move Table

```python
def is_on_board(rank, file, dr, df):
    """Check if (rank+dr, file+df) is within 8x8 board."""
    return 0 <= rank + dr < 8 and 0 <= file + df < 8

def build_move_table_with_bounds(pieces):
    """Build move table -- all 8 offsets per piece, regardless of board position.

    Board-bounds validity is checked by the quantum predicate at runtime
    since piece positions are in superposition. The table itself always
    has exactly 8 entries per piece.
    """
    table = []
    for piece_id, piece_type in pieces:
        offsets = _KNIGHT_OFFSETS if piece_type == "knight" else _KING_OFFSETS
        for dr, df in offsets:
            table.append((piece_id, dr, df))
    # Always 8 * len(pieces) entries -- no filtering here
    return table
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `itertools.combinations` pattern enum | Arithmetic counting circuit | Phase 113 (now) | Reduces gate count from O(2^d_max) to O(d_max) |
| Classical legality filtering before circuit | All-moves enumeration + quantum predicate | Phase 113 (table) + Phase 114-115 (predicate) | Enables superposition evaluation |
| Separate diffusion in walk.py and chess_walk.py | Single shared implementation | Phase 113 | Eliminates code duplication |
| `legal_moves_white/black` with classical position | `build_move_table` with piece config | Phase 113 | Position-independent move table for quantum walk |

**Deprecated/outdated:**
- `itertools.combinations` in `_variable_diffusion()` and `apply_diffusion()`: Replaced entirely by counting circuit
- `get_legal_moves_and_oracle()` classical move generation: Will be superseded by move table + quantum oracle (but remains for backward compat until Phase 116)
- Per-level `prepare_walk_data()`: Will be replaced by move-table-based data preparation

## Open Questions

1. **qarray.sum() width propagation for qbool inputs**
   - What we know: `qarray.sum()` accepts `width=` parameter, uses tree reduction
   - What's unclear: Does the tree reduction of qbool (1-bit) elements correctly widen intermediate results? If summing 24 qbools, intermediate additions must use sufficient width.
   - Recommendation: Test empirically with a small example (sum 4 qbools, verify result is a 3-bit qint). If width propagation fails, manually promote qbools to 1-bit qints before summing.

2. **Nested `with qbool:` depth for count comparison + h[depth] control**
   - What we know: Known limitation with nested `with qbool:` (STATE.md: "Nested with qbool limitation requires flat Toffoli-AND predicate design")
   - What's unclear: Whether `with (count == d_val):` inside `with h_control:` triggers the nesting limitation
   - Recommendation: Use `_emit_multi_controlled_ry` with explicit control qubit list `[h_qubit, count_cond_qubit]` instead of nested `with`. This avoids the nesting issue entirely.

3. **Cascade ops reuse vs redesign**
   - What we know: `_plan_cascade_ops` handles up to 2 control levels (raises NotImplementedError for 3+). Currently used with ctrl_qubits from validity patterns.
   - What's unclear: Whether the validity-gated cascade (controlling each child's rotation on validity[i]) fits within the 2-control limit when combined with count comparison and h[depth] controls.
   - Recommendation: Start by reusing `_plan_cascade_ops`. If control depth exceeds 2, the V-gate decomposition in `_emit_multi_controlled_ry` handles arbitrary depth via recursive peeling. The cascade is applied per-child with validity[i] as one additional control.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest runs from project root |
| Quick run command | `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WALK-01 | All-moves enumeration table has 8 entries per piece, correct (piece_id, dr, df) triples | unit | `pytest tests/python/test_move_table.py -x` | No -- Wave 0 |
| WALK-01 | White KNK table has 24 entries, black K has 8 | unit | `pytest tests/python/test_move_table.py::test_table_sizes -x` | No -- Wave 0 |
| WALK-01 | Knight offsets are exactly the 8 L-shapes, king offsets are 8 adjacencies | unit | `pytest tests/python/test_move_table.py::test_offset_correctness -x` | No -- Wave 0 |
| WALK-03 | Counting diffusion produces equivalent statevector to old combinatorial diffusion for d_max=2 | integration | `pytest tests/python/test_counting_diffusion.py::test_equivalence_d2 -x` | No -- Wave 0 |
| WALK-03 | Counting diffusion produces equivalent statevector for d_max=3 | integration | `pytest tests/python/test_counting_diffusion.py::test_equivalence_d3 -x` | No -- Wave 0 |
| WALK-03 | D_x^2 = I reflection property holds with counting circuit | integration | `pytest tests/python/test_counting_diffusion.py::test_reflection -x` | No -- Wave 0 |
| WALK-03 | Existing walk tests pass with new diffusion | regression | `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x` | Yes |
| WALK-03 | Gate count is O(d_max), not exponential | unit | `pytest tests/python/test_counting_diffusion.py::test_gate_count_linear -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_walk_variable.py tests/python/test_chess_walk.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_move_table.py` -- covers WALK-01 (move enumeration table)
- [ ] `tests/python/test_counting_diffusion.py` -- covers WALK-03 (counting circuit equivalence, reflection, gate count)

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/walk.py` -- Current _variable_diffusion implementation (lines 782-897), _plan_cascade_ops (lines 50-149), _emit_multi_controlled_ry (lines 291-354)
- `src/chess_walk.py` -- Current apply_diffusion implementation (lines 403-541), move data infrastructure
- `src/chess_encoding.py` -- _KNIGHT_OFFSETS (line 41), _KING_OFFSETS (line 53), knight_attacks/king_attacks functions
- `src/quantum_language/qarray.pyx:652` -- qarray.sum() implementation with width parameter
- `src/quantum_language/qint_comparison.pxi:6` -- qint.__eq__ with CQ_equal_width
- `src/quantum_language/diffusion.py` -- S_0 reflection operator

### Secondary (MEDIUM confidence)
- `tests/python/test_walk_variable.py` -- Existing variable branching tests (reflection property, amplitude verification)
- `tests/python/test_chess_walk.py` -- Existing chess walk tests (register creation, diffusion smoke tests)

### Tertiary (LOW confidence)
- qarray.sum() width propagation for qbool elements -- needs empirical verification (Open Question 1)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components verified in source code
- Architecture: HIGH -- pattern is clearly defined by user decisions, building blocks verified
- Pitfalls: HIGH -- derived from direct analysis of current code and known framework limitations (nested with qbool)

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- internal framework, no external dependency changes)
