# Phase 103: Chess Board Encoding & Legal Moves - Research

**Researched:** 2026-03-03
**Domain:** Chess endgame encoding with quantum primitives (qarray/qbool), classical move generation, compiled oracle
**Confidence:** HIGH

## Summary

Phase 103 builds a standalone chess module that encodes simplified endgame positions (2 kings + white knights) as quantum arrays and generates legal moves using a hybrid classical-quantum approach. The phase is entirely domain-application code -- no changes to the quantum_language core are needed.

The existing codebase already demonstrates the core pattern: `src/demo.py` contains `knight_moves()` for classical attack patterns and `attack()` as a `@ql.compile(inverse=True)` function using `with qbool:` conditionals over an 8x8 qarray. The chess module will extend this pattern with king moves, legal move filtering, and a deterministic enumeration mapping (piece, destination) pairs to indices 0..d-1 for Phase 104's branch registers.

**Primary recommendation:** Build a pure-Python chess module at `src/chess_encoding.py` (or `src/chess/`) that separates classical logic (move generation, filtering, enumeration) from quantum circuit construction (board encoding, compiled oracle). All move generation is classical since starting positions are known; the quantum oracle wraps the classical move list into a `@ql.compile` function that Phase 104 can call with branch register arguments.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Square-centric encoding: qarray of 64 qbools, one per square, storing whether a piece occupies that square
- Separate qarrays per piece type as needed (e.g., white knights, white king, black king)
- 64 qbools per layer
- Starting positions are classical input -- set via X gates at circuit initialization time
- Positions are configurable via Python parameters (not hardcoded)
- Legal moves represented as an enumerated index list (0..d-1)
- Each index maps to a (piece, destination) pair
- Deterministic ordering: sorted by piece index, then destination square
- Branch register stores the index -- maps directly to Montanaro's framework for Phase 104
- Per-side combined list: oracle returns all legal moves for the side to move (both knights + king)
- Hybrid move generation: classical precomputation where positions are known, quantum conditionals where branch superposition determines the position
- Standalone module: create a chess encoding module (not inline in demo.py)
- Reusable by Phase 106's demo scripts and comparison script
- Separate from the quantum_language core library -- this is a demo/application module
- Classical unit tests for move generation correctness
- Subcircuit spot-checks: small cases simulated via Qiskit within 17-qubit budget
- Tests in main test suite: tests/python/test_chess.py

### Claude's Discretion
- Exact qarray layering for piece types (one qarray per piece type vs combined encoding)
- Oracle API interface design (full position vs incremental)
- Default demo starting position (interesting endgame vs center placement)
- Spot-check priority ordering (encoding vs oracle first)
- Whether to print circuit statistics in Phase 103 or defer to Phase 106

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHESS-01 | 8x8 board with piece positions encoded as qarray (2 kings + white knights) | Square-centric encoding with separate qarrays per piece type; `qarray(dim=(8,8), dtype=ql.qbool)` pattern; X-gate initialization for classical positions |
| CHESS-02 | Knight attack pattern generation from any occupied square | Existing `knight_moves()` in demo.py reusable; 8 L-shaped offsets with boundary checking; classical precomputation |
| CHESS-03 | King move generation (8 adjacent squares, edge-aware) | New `king_moves()` function; 8 adjacent offsets with rank/file boundary checking; same classical pattern as knight |
| CHESS-04 | Legal move filtering -- destination not attacked by opponent, not occupied by friendly piece | Classical filtering: remove destinations occupied by friendly pieces; remove moves leaving own king in check; attack map intersection |
| CHESS-05 | Move oracle as `@ql.compile` function producing legal move set for current position | `@ql.compile(inverse=True)` wrapping enumerated move list; deterministic (piece, destination) ordering; branch-register-compatible output |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | 0.1.0 | Quantum types (qarray, qbool, qint), @ql.compile, circuit management | Project's own framework -- all quantum operations go through this |
| numpy | (installed) | Board representation, classical move arrays, position initialization | Already used by demo.py for 8x8 arrays; qarray accepts numpy arrays |
| itertools | stdlib | Product of ranks/files for board iteration | Already used in demo.py `attack()` function |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (installed) | Test framework | All tests in `tests/python/test_chess.py` |
| qiskit + qiskit_aer | (installed) | Subcircuit simulation spot-checks | Only for spot-check tests within 17-qubit budget |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom board class | Raw numpy + qarray | Raw arrays match existing demo.py pattern; a custom class adds abstraction but no quantum benefit |
| python-chess library | Hand-written move generation | python-chess is overkill for 2 piece types; our move generation is 30 lines per piece |

**Installation:** No new dependencies needed. All libraries already available.

## Architecture Patterns

### Recommended Project Structure
```
src/
  chess_encoding.py          # Standalone chess module (all of Phase 103)
  demo.py                    # Existing demo (untouched in Phase 103)
  quantum_language/           # Core framework (untouched in Phase 103)
tests/python/
  test_chess.py              # Phase 103 tests
```

**Rationale:** A single `chess_encoding.py` file keeps it simple. The module is self-contained (~300-500 lines) covering board encoding, move generation, filtering, enumeration, and the compiled oracle. If it grows beyond 500 lines, split into `src/chess/` package with `__init__.py`, `board.py`, `moves.py`, `oracle.py`.

### Pattern 1: Board Encoding with Separate Piece-Type qarrays
**What:** Create one `qarray(dim=(8,8), dtype=ql.qbool)` per piece type. For 4 pieces (2 white knights, 1 white king, 1 black king), use 3 layers: `white_knights`, `white_king`, `black_king`.
**When to use:** Always -- this is the locked decision.
**Example:**
```python
# Source: demo.py pattern + CONTEXT.md decision
import numpy as np
import quantum_language as ql

def encode_position(wk_sq, bk_sq, wn_squares):
    """Encode a chess position as qarrays.

    Parameters
    ----------
    wk_sq : int
        White king square (0-63, a1=0, h8=63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s).

    Returns
    -------
    dict with 'white_king', 'black_king', 'white_knights' qarrays.
    """
    wk = np.zeros((8, 8), dtype=int)
    wk[wk_sq // 8, wk_sq % 8] = 1

    bk = np.zeros((8, 8), dtype=int)
    bk[bk_sq // 8, bk_sq % 8] = 1

    wn = np.zeros((8, 8), dtype=int)
    for sq in wn_squares:
        wn[sq // 8, sq % 8] = 1

    return {
        'white_king': ql.qarray(wk, dtype=ql.qbool),
        'black_king': ql.qarray(bk, dtype=ql.qbool),
        'white_knights': ql.qarray(wn, dtype=ql.qbool),
    }
```

### Pattern 2: Classical Move Generation with Board-Boundary Checking
**What:** Pure Python functions that compute legal destinations for each piece type, returning lists of square indices.
**When to use:** For all move generation -- positions are classically known.
**Example:**
```python
# Source: Adapted from demo.py knight_moves()
def knight_attacks(square):
    """Return list of squares attacked by a knight on `square`.

    Parameters
    ----------
    square : int
        Square index 0-63 (rank * 8 + file).

    Returns
    -------
    list[int]
        Attacked square indices.
    """
    rank, file = divmod(square, 8)  # Note: row-major if rank=square//8
    offsets = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]
    attacks = []
    for dr, df in offsets:
        nr, nf = rank + dr, file + df
        if 0 <= nr < 8 and 0 <= nf < 8:
            attacks.append(nr * 8 + nf)
    return sorted(attacks)


def king_attacks(square):
    """Return list of squares attacked by a king on `square`."""
    rank, file = divmod(square, 8)
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    attacks = []
    for dr, df in offsets:
        nr, nf = rank + dr, file + df
        if 0 <= nr < 8 and 0 <= nf < 8:
            attacks.append(nr * 8 + nf)
    return sorted(attacks)
```

### Pattern 3: Move Enumeration and Legal Move Filtering
**What:** Combine attack patterns with occupancy/check filtering, then produce a deterministic enumerated list.
**When to use:** After computing raw attacks, before creating the oracle.
**Example:**
```python
def legal_moves_white(wk_sq, bk_sq, wn_squares):
    """Return enumerated legal moves for white.

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of (piece_square, destination_square) pairs.
        Index in list = branch register value.
    """
    moves = []
    friendly_squares = set(wn_squares + [wk_sq])

    # Black king attacks (squares white king can't move to)
    bk_attacks = set(king_attacks(bk_sq))

    # Knight moves
    for sq in sorted(wn_squares):
        for dest in knight_attacks(sq):
            if dest not in friendly_squares:
                # Knight can't capture own pieces
                # Also check: does moving this knight expose own king to check?
                # (simplified: in KNK endgame, knights don't block checks on own king)
                moves.append((sq, dest))

    # King moves
    for dest in king_attacks(wk_sq):
        if dest not in friendly_squares and dest not in bk_attacks:
            # King can't move to square attacked by opponent
            # Also can't move adjacent to opponent king
            moves.append((wk_sq, dest))

    # Sort by piece square, then destination (deterministic ordering)
    moves.sort()
    return moves
```

### Pattern 4: Compiled Move Oracle
**What:** `@ql.compile` function that wraps the classical move list for quantum circuit integration.
**When to use:** Phase 104 calls this oracle with branch registers.
**Example:**
```python
@ql.compile(inverse=True)
def move_oracle(position_qarrays, move_list):
    """Produce legal move set for a given position.

    The oracle is designed to be called with classical position data
    (since starting positions are known). For Phase 104's quantum walk,
    the oracle is invoked after replaying the move sequence from root.

    Parameters
    ----------
    position_qarrays : dict
        qarrays for each piece type.
    move_list : list[tuple[int, int]]
        Precomputed legal moves as (piece_sq, dest_sq) pairs.
    """
    # The move list IS the oracle output -- it's precomputed classically
    # The @ql.compile wrapper captures any quantum gates needed
    # to encode the move list into branch-register-compatible form
    pass
```

**Note on oracle design:** Since positions at the root are classically known, the Phase 103 oracle is essentially a classical-to-quantum bridge. The true quantum oracle emerges in Phase 104, where the position at each tree node depends on the superposition of branch register values. Phase 103 provides the building blocks that Phase 104 composes.

### Anti-Patterns to Avoid
- **Nesting `with qbool:` blocks:** The framework has a known limitation where `with qbool:` cannot nest properly (exiting inner block resets all control state). Use V-gate decomposition or sequential `with` blocks as the walk module does.
- **64-qubit qarray simulation:** Never attempt to simulate a full 8x8 qbool board via Qiskit -- that's 64 qubits minimum. All Qiskit spot-checks must use tiny subsets (4-8 qubits max, well within 17-qubit budget).
- **Hardcoding positions:** Positions must be parameterized via function arguments, not module-level constants.
- **Using qint for single-bit occupancy:** Use `qbool` (1-bit) for piece presence, not `qint` (wastes qubits).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Knight attack patterns | Custom offset lookup table | `knight_attacks()` with 8-offset boundary check | Boundary checking is 2 lines; a lookup table wastes memory |
| King attack patterns | Copy-paste from knight code | `king_attacks()` with 8-offset boundary check | Same pattern, different offsets -- share the boundary logic |
| Check detection | Full minimax evaluation | Simple "is king square attacked" test | Phase 103 only needs legal move filtering, not evaluation |
| Board serialization | Custom encoding format | Standard square indices (0-63, a1=0) | Matches chess convention; trivially maps to qarray[rank, file] |
| Move enumeration | Hash map or complex structure | Sorted list of (piece_sq, dest_sq) tuples | Branch register value = list index; deterministic and simple |

**Key insight:** All move generation in Phase 103 is classical. The quantum part is only the board encoding (qarrays with X-gate initialization) and the oracle wrapper (`@ql.compile`). Don't over-engineer the quantum side when the classical logic is straightforward.

## Common Pitfalls

### Pitfall 1: Square Indexing Convention Mismatch
**What goes wrong:** The existing `knight_moves()` in demo.py uses chess notation (file a-h, rank 1-8) with display-oriented `7 - rank` inversion, while qarray uses row-major [rank, file] indexing. Mixing conventions produces wrong attack patterns.
**Why it happens:** Chess has multiple indexing conventions (a1=bottom-left, h8=top-right, Lerf mapping, etc.) and numpy arrays have [row, col] = [rank, file] but with row 0 at top.
**How to avoid:** Define ONE canonical mapping early and use it everywhere:
- Square index: 0-63 where `sq = rank * 8 + file` (rank 0 = rank 1 in chess = bottom)
- qarray indexing: `board[rank, file]` where rank 0 is chess rank 1
- Conversion: `rank, file = divmod(sq, 8)`
**Warning signs:** Knight from d4 (sq=27) produces wrong number of attacks; king on a1 (sq=0) shows more than 3 moves.

### Pitfall 2: Forgetting Edge-Awareness for King Moves
**What goes wrong:** King move generation wraps around board edges (e.g., king on h1 appears to attack a2).
**Why it happens:** Adding offsets to file=7 gives file=8, which modulo 8 would be 0 (wrong rank). Without explicit bounds checking, this produces phantom attacks.
**How to avoid:** Always check `0 <= nr < 8 and 0 <= nf < 8` before accepting a move.
**Warning signs:** King on edge squares shows 8 moves instead of 3 (corner) or 5 (edge).

### Pitfall 3: Friendly-Piece Self-Capture
**What goes wrong:** Move list includes destinations occupied by friendly pieces.
**Why it happens:** Raw attack patterns don't exclude occupied squares.
**How to avoid:** After computing attacks, filter out squares occupied by friendly pieces.
**Warning signs:** Knight move count from a square seems too high; enumerated list contains (sq, dest) where dest has a friendly piece.

### Pitfall 4: King Moving into Check
**What goes wrong:** King's legal moves include squares attacked by opponent.
**Why it happens:** Only checking for occupied squares, not attacked squares.
**How to avoid:** Compute opponent attack map (black king attacks), then exclude those squares from white king's legal moves. Also exclude squares adjacent to opponent king (kings can't be adjacent).
**Warning signs:** Legal move list allows king to move next to opponent king.

### Pitfall 5: Qubit Budget Overflow in Spot-Check Tests
**What goes wrong:** Qiskit simulation exceeds 17-qubit limit, causing memory issues or crashes.
**Why it happens:** Even a "small" spot-check using 4x4 board subset with 2 piece types = 32 qubits.
**How to avoid:** For Qiskit spot-checks: use a single piece on a tiny board (e.g., 1 knight on a 3x3 or 4x4 subset = 9-16 qubits max). Most tests should be classical (pure Python, no quantum simulation).
**Warning signs:** Test runs slowly or crashes; pytest output shows memory allocation errors.

### Pitfall 6: Oracle Inverse Compatibility
**What goes wrong:** `@ql.compile(inverse=True)` oracle can't be properly uncomputed because it allocates non-reversible state.
**Why it happens:** The oracle creates qarrays or qbools inside the function that aren't properly cleaned up.
**How to avoid:** Keep the oracle function clean -- it should only perform reversible operations. Any classical precomputation happens OUTSIDE the oracle. The oracle body should only contain quantum operations (qarray manipulation, with-blocks, etc.).
**Warning signs:** `attack.inverse()` raises an error about ancilla delta.

## Code Examples

Verified patterns from the existing codebase:

### Board Encoding (from demo.py pattern)
```python
# Source: src/demo.py lines 72-78
import numpy as np
import quantum_language as ql

# Create 8x8 board with pieces
N_pos = np.zeros((8, 8))
N_pos[3, 5] = 1  # Knight on rank 3, file 5
N_pos[5, 4] = 1  # Knight on rank 5, file 4
knights = ql.qarray(N_pos, dtype=ql.qbool)
```

### Compiled Function with Quantum Conditionals (from demo.py)
```python
# Source: src/demo.py lines 83-95
@ql.compile(inverse=True)
def attack():
    arr = ql.qarray([[0] * 8] * 8, width=3)
    for i, j in itertools.product(
        ["a", "b", "c", "d", "e", "f", "g", "h"],
        range(1, 8)
    ):
        with knights[ord(i) - ord("a"), j]:  # conditional on knight presence
            arr += knight_moves((i, j))       # add attack pattern

    attacked = arr != 0
    king = ql.qarray([[0] * 8] * 8, dtype=ql.qbool)
    in_check = (king & attacked).any()
    return in_check
```

### qarray Operations (from framework API)
```python
# Source: src/quantum_language/qarray.pyx
board = ql.qarray(dim=(8, 8), dtype=ql.qbool)    # 64 qbools
board[3, 5]                                        # Access single qbool
board[3, :]                                        # Row slice -> qarray
board[:, 5]                                        # Column slice -> qarray
(board & other_board).any()                        # Element-wise AND, then OR-reduce
board != 0                                         # Element-wise comparison -> qbool array
```

### Avoid Nested with-blocks (from walk.py pattern)
```python
# Source: src/quantum_language/walk.py lines 216-277
# WRONG: nested with blocks
# with piece_present:
#     with not_friendly:  # <-- BAD: nesting breaks control state
#         result |= 1

# RIGHT: sequential with blocks, or precompute combined condition
combined = piece_present & not_friendly  # AND into single qbool
with combined:
    result |= 1
```

### Test Fixture Pattern (from conftest.py)
```python
# Source: tests/python/conftest.py
@pytest.fixture
def clean_circuit():
    circ = ql.circuit()
    yield circ
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| demo.py inline chess code | Standalone chess module | Phase 103 (now) | Reusable by Phases 104-106 |
| chess notation (a1-h8) | Square indices (0-63) | Phase 103 (now) | Consistent with qarray[rank, file] |
| Full board simulation | Circuit generation only | v6.1 decision | No Qiskit sim for full boards (>17 qubits) |

**Deprecated/outdated:**
- demo.py's `knight_moves()` uses chess notation internally with display-inverted ranks -- Phase 103 should use a cleaner 0-63 index scheme while maintaining the same attack logic.

## Open Questions

1. **Exact oracle API for Phase 104 compatibility**
   - What we know: Phase 104 needs to call the move oracle with a board position derived from branch register replay. The oracle returns a move count d(x) used for diffusion angles.
   - What's unclear: Should the oracle take qarrays as input (full position) or the branch register history? Does it need to return the actual move list or just the count?
   - Recommendation: Design oracle to accept a position dict (qarrays) and return both the move list and count. Phase 104 can call it after reconstructing position from branch registers. Keep the API flexible -- it's easier to constrain later.

2. **Discovery check detection**
   - What we know: Moving a knight might expose the own king to a check from the opponent (discovery check). In KNK endgame, the only opponent piece is the black king.
   - What's unclear: Can a knight block a king-to-king line? No -- kings can't be adjacent, and knights don't block lines.
   - Recommendation: For the simplified endgame (2 kings + knights), the only check scenario is the opponent king attacking a square. Discovery checks are not possible since the black king has no ranged attacks. Simplify accordingly.

3. **Number of white knights**
   - What we know: CONTEXT.md says "2 kings + white knights" (plural). REQUIREMENTS.md says "2 kings + white knights."
   - What's unclear: Is it always exactly 2 knights, or configurable? The branch register sizing (5-bit = max 32 moves) suggests 2 knights (max 16 knight moves + max 8 king moves = 24 < 32).
   - Recommendation: Support configurable number of knights (1-2), default to 2. The enumeration and branch register sizing naturally accommodate this.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | tests/python/conftest.py (clean_circuit fixture) |
| Quick run command | `pytest tests/python/test_chess.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHESS-01 | Board encoding as qarray with correct square-to-qubit mapping | unit | `pytest tests/python/test_chess.py::TestBoardEncoding -x` | Wave 0 |
| CHESS-02 | Knight attack pattern from any square, boundary-aware | unit | `pytest tests/python/test_chess.py::TestKnightMoves -x` | Wave 0 |
| CHESS-03 | King move generation, 8 directions, edge-aware | unit | `pytest tests/python/test_chess.py::TestKingMoves -x` | Wave 0 |
| CHESS-04 | Legal move filtering (friendly piece, opponent attacks) | unit | `pytest tests/python/test_chess.py::TestLegalMoveFiltering -x` | Wave 0 |
| CHESS-05 | Move oracle as @ql.compile function | unit + subcircuit | `pytest tests/python/test_chess.py::TestMoveOracle -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_chess.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_chess.py` -- all CHESS-01 through CHESS-05 tests
- No framework install needed (pytest already configured)
- No conftest changes needed (`clean_circuit` fixture already exists)

## Sources

### Primary (HIGH confidence)
- `src/demo.py` -- working example of chess-like quantum operations with knight_moves, attack(), qarray of qbools
- `src/quantum_language/qarray.pyx` -- full qarray API: initialization, indexing, slicing, element-wise operations, reductions
- `src/quantum_language/qbool.pyx` -- qbool is 1-bit qint with context manager protocol
- `src/quantum_language/compile.py` -- @ql.compile with inverse=True, ancilla tracking, gate capture/replay
- `src/quantum_language/walk.py` -- V-gate decomposition pattern for avoiding nested with-blocks
- `src/quantum_language/qint.pyx` -- context manager (__enter__/__exit__) showing nesting limitation
- `tests/python/conftest.py` -- clean_circuit fixture for unit tests
- `.planning/phases/103-chess-board-encoding-legal-moves/103-CONTEXT.md` -- locked decisions, discretion areas

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- requirement definitions CHESS-01 through CHESS-05
- `.planning/STATE.md` -- known limitations (with qbool nesting, 17-qubit budget)
- `.planning/MILESTONES.md` -- v6.0 context and known gaps

### Tertiary (LOW confidence)
- Knight/king move maximum counts (32 white / 8 black) -- from CONTEXT.md discussion, not independently verified against chess theory. However, 2 knights x 8 max moves = 16, plus king 8 max moves = 24 total, so 5-bit register (max 32) is correct.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- patterns directly from existing demo.py and walk.py code
- Pitfalls: HIGH -- identified from actual codebase examination (nesting limitation, qubit budget, indexing conventions)
- Move generation correctness: HIGH -- standard chess programming, verified against known knight/king move patterns
- Oracle design: MEDIUM -- the exact Phase 104 interface is not yet designed; Phase 103 should build a flexible API

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- no external dependencies changing)
