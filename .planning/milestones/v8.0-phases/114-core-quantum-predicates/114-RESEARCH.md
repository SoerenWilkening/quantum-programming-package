# Phase 114: Core Quantum Predicates - Research

**Researched:** 2026-03-08
**Domain:** Quantum predicate functions using ql constructs (with qbool, qarray, @ql.compile)
**Confidence:** HIGH

## Summary

This phase implements two quantum predicate functions -- piece-exists and no-friendly-capture -- as factory-produced `@ql.compile(inverse=True)` functions that evaluate chess move conditions in superposition. The predicates operate on board qarrays (2D qbool arrays) using the existing `with` conditional pattern for single-level controlled gates.

The core technical challenge is expressing multi-square conditions using only flat (non-nested) `with qbool:` blocks, since the framework raises `NotImplementedError` for nested `with qbool:` contexts. The classical-loop-over-squares pattern established in `_make_apply_move` (chess_encoding.py:390) provides the template: classical precomputation outside `@ql.compile`, quantum ops inside.

**Primary recommendation:** Follow the `_make_apply_move` factory pattern exactly -- classical loops enumerate squares, `with board[r, f]:` controls conditional flips on a result qbool. Each predicate is a separate factory function in a new `src/chess_predicates.py` module.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Separate `@ql.compile(inverse=True)` functions for piece-exists (PRED-01) and no-friendly-capture (PRED-02)
- Factory pattern: `make_piece_exists_predicate(piece_id, dr, df, board_rows, board_cols)` returns a compiled function, mirroring `_make_apply_move` in chess_encoding.py
- `@ql.compile(inverse=True)` wrapping is inside the factory -- caller gets a ready-to-use compiled function with `.inverse()` available
- New file: `src/chess_predicates.py` -- dedicated module alongside chess_encoding.py and chess_walk.py
- Classical loop over all possible source squares at circuit construction time
- For each (r, f): use `with board[r, f]:` to condition on piece being at that square, then check target condition at (r+dr, f+df)
- Generates O(board_size^2) controlled blocks using only standard ql constructs -- no quantum arithmetic on position registers
- Off-board moves: classical skip in the loop (no quantum gates for impossible moves)
- No-piece-exists: predicate result stays |0> naturally (no `with board[r,f]:` block fires)
- Side-specific friendly capture: white moves check white_king + white_knights, black check black_king only
- Factory takes `piece_qarray` (moving piece's board) and `friendly_qarrays` (list of same-color boards)
- Predicate writes to a passed-in result qbool (flips to |1> if condition holds)
- Caller owns the ancilla lifecycle -- matches existing validity[i] pattern
- Board size parameterized by `board_rows`, `board_cols` (2x2 for tests, 8x8 for production)

### Claude's Discretion
- Exact ancilla management within compiled predicate bodies
- How to structure the inner conditional logic (sequential `with` blocks vs accumulated condition)
- Classical helper functions for move validation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRED-01 | Quantum piece-exists predicate checks whether a specific piece type occupies a source square in superposition using `with` conditional and qarray element access | Factory pattern with classical loop over squares, `with board[r, f]:` conditional, result qbool flip |
| PRED-02 | Quantum no-friendly-capture predicate rejects moves where target square is occupied by same-color piece, using `with` conditional on board qarray elements | Second factory taking `friendly_qarrays`, loop over friendly boards checking target square |
| PRED-05 | All predicates use `@ql.compile(inverse=True)` for automatic ancilla uncomputation and compiled replay | `@ql.compile(inverse=True)` decorator inside factory, matching `_make_apply_move` pattern |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | project-local | Framework providing qarray, qbool, qint, @ql.compile | This project's core framework |
| numpy | installed | Board initialization arrays for qarray construction | Used throughout project for array ops |
| pytest | installed | Test framework | Project standard (conftest.py with clean_circuit fixture) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit-aer | installed | AerSimulator for statevector verification | Small-board tests (2x2, within 17 qubits) |

### Alternatives Considered
None -- all tooling is project-established. No new dependencies needed.

**Installation:**
No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/
  chess_predicates.py     # NEW: Predicate factory functions (this phase)
  chess_encoding.py       # Existing: Board encoding, move tables, apply_move oracle
  chess_walk.py           # Existing: Walk infrastructure, evaluate_children (Phase 116 integration)
tests/python/
  test_chess_predicates.py  # NEW: Predicate unit tests
```

### Pattern 1: Factory Pattern for Compiled Quantum Functions
**What:** Classical closure captures precomputed data; inner `@ql.compile(inverse=True)` function uses only quantum ops.
**When to use:** Any quantum function parameterized by classical data (board size, offsets, piece configs).
**Example (from chess_encoding.py:390-464):**
```python
def _make_apply_move(move_list, wk_sq, bk_sq, wn_squares, side_to_move):
    # Classical precomputation here (outside @ql.compile)
    flat_specs = []
    for piece_sq, dest_sq in move_list:
        # ... compute specs ...
        flat_specs.append((board_idx, src_rank, src_file, dst_rank, dst_file))

    @ql.compile(inverse=True)
    def apply_move(wk_arr, bk_arr, wn_arr, branch):
        # Only quantum operations here
        boards = [wk_arr, bk_arr, wn_arr]
        for i, (board_idx, sr, sf, dr, df) in enumerate(flat_specs):
            cond = branch == i
            with cond:
                ~boards[board_idx][sr, sf]
                ~boards[board_idx][dr, df]
    return apply_move
```

### Pattern 2: Single-Level `with` Conditional for Controlled Gates
**What:** `with qbool_or_qint:` creates controlled gate context. All quantum ops inside are controlled on that qubit.
**When to use:** Checking/setting values conditioned on a single qbool.
**Critical constraint:** Nested `with qbool:` raises `NotImplementedError`. Must use flat sequential blocks.
**Example:**
```python
# CORRECT: Sequential flat with blocks
with board[r1, f1]:
    ~result  # Flip result controlled on board[r1, f1]
with board[r2, f2]:
    ~result  # Flip result controlled on board[r2, f2]

# WRONG: Nested with blocks (raises NotImplementedError)
with board[r1, f1]:
    with board[r2, f2]:  # ERROR!
        ~result
```

### Pattern 3: qarray Element Access for Board Indexing
**What:** `board[rank, file]` returns a qbool element from a 2D qarray.
**When to use:** Accessing individual square states on the board.
**Details:** qarray supports NumPy-style multi-dimensional indexing (qarray.pyx:296-343). For a `(rows, cols)` shaped qarray of dtype=qbool, `board[r, f]` returns the qbool at that position. This qbool can be used as a `with` context manager for controlled operations.

### Pattern 4: Controlled NOT via `~element`
**What:** `~qbool_or_qint` applies X gates to all bits. Inside a `with` context, these become controlled-NOT (CNOT) gates.
**When to use:** Flipping a result bit conditioned on a board square value.
**Details:** `__invert__` on qint (qint_bitwise.pxi:534) emits X (uncontrolled) or controlled-X (when inside `with` block, via `_get_controlled()`).

### Anti-Patterns to Avoid
- **Nested `with qbool:` blocks:** Framework limitation. Use sequential `with` blocks or accumulate results via XOR/copy patterns instead.
- **Raw gate emission (`emit_x`, `emit_cnot`) in predicate logic:** Violates PRED-05 and WALK-05. Only standard ql constructs allowed for application logic.
- **Quantum arithmetic on position registers:** Not needed. Classical loop handles position enumeration at circuit construction time.
- **Using `encode_position` for small-board tests:** This function hardcodes 8x8 board shape. Tests must create small qarrays directly via `ql.qarray(np.zeros((rows, cols), dtype=int), dtype=ql.qbool)`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ancilla uncomputation | Manual inverse gate sequences | `@ql.compile(inverse=True)` | Framework handles forward/inverse lifecycle automatically |
| Board square indexing | Custom qubit offset calculations | `board[rank, file]` qarray indexing | qarray handles multi-dim indexing with bounds checking |
| Controlled operations | `emit_cnot` with manual qubit tracking | `with qbool:` + `~target` | Standard ql construct, respects control context stack |
| Move offset enumeration | Hardcoded offset lists per predicate | `_KNIGHT_OFFSETS` / `_KING_OFFSETS` from chess_encoding | Already defined and tested |

**Key insight:** The predicate bodies should look like natural Python code with `with`/`~` -- the framework compiles this to controlled gates. No qubit-level reasoning needed in application code.

## Common Pitfalls

### Pitfall 1: Nested `with qbool:` (Flat Toffoli-AND Limitation)
**What goes wrong:** Attempting `with board[r, f]: with friendly[r2, f2]: ~result` raises NotImplementedError.
**Why it happens:** Framework's control stack doesn't support multi-qubit AND conditions via nested context managers (line 813-817 in qint.pyx shows the TODO).
**How to avoid:** Use sequential `with` blocks. For piece-exists: single `with board[r, f]: ~result`. For no-friendly-capture: separate the conditions -- first check if piece exists (writes result), then check if friendly piece at target (writes to separate ancilla or XOR pattern).
**Warning signs:** Any code with two indented `with` blocks.

### Pitfall 2: Double-Flip on Result qbool (OR vs XOR Semantics)
**What goes wrong:** If multiple source squares have the piece (superposition), each `with board[r, f]: ~result` flips the result. Two flips cancel out (XOR, not OR).
**Why it happens:** `~result` is X gate, and X^2 = I.
**How to avoid:** For piece-exists, this is actually correct behavior in the KNK endgame: each piece type has exactly one instance per board, so only one `with board[r, f]:` block fires. For boards with multiple pieces of same type (e.g., 2 knights on same qarray), need careful design -- but this phase's predicates are parameterized per-piece-type, not per-piece.
**Warning signs:** Predicate operating on a qarray where multiple elements could be |1> simultaneously.

### Pitfall 3: 17-Qubit Simulation Budget
**What goes wrong:** Test circuits exceed 17 qubits, causing Qiskit simulation to hang/OOM.
**Why it happens:** 3 piece boards x NxN = 3N^2 qubits. 3x3 = 27 qubits already exceeds limit.
**How to avoid:** Use 2x2 boards (12 qubits for 3 pieces + 1 result + ancillae = ~14-15 qubits). For no-friendly-capture with fewer boards, 2 pieces on 2x2 = 8 + result = 9 qubits leaves room. Always limit `max_parallel_threads=4` in AerSimulator.
**Warning signs:** Board dimensions > 2x2 in simulation tests.

### Pitfall 4: Forgetting Off-Board Skip in Classical Loop
**What goes wrong:** Accessing `board[r+dr, f+df]` where (r+dr, f+df) is out of bounds causes IndexError.
**Why it happens:** Not all (r, f) + (dr, df) combinations land on valid squares.
**How to avoid:** Classical `if 0 <= r+dr < board_rows and 0 <= f+df < board_cols:` guard before emitting any quantum ops for that iteration.
**Warning signs:** IndexError during circuit construction (not simulation).

### Pitfall 5: Confusing `with board[r, f]:` Direction
**What goes wrong:** Piece-exists should check source squares, not target squares. Getting the loop logic reversed.
**Why it happens:** Predicate has two concerns: (1) piece at source, (2) condition at target.
**How to avoid:** For piece-exists: loop (r, f) over all squares, compute (r+dr, f+df) as the move destination. `with piece_qarray[r, f]:` means "if piece is here", then flip result to indicate this move is geometrically possible from this source.

## Code Examples

### Piece-Exists Predicate Factory
```python
# Source: Derived from _make_apply_move pattern (chess_encoding.py:390)
def make_piece_exists_predicate(piece_id, dr, df, board_rows, board_cols):
    """Create a compiled predicate that checks if a piece can make move (dr, df).

    Returns @ql.compile(inverse=True) function that flips result qbool to |1>
    if piece_qarray has a piece at any square (r, f) such that (r+dr, f+df)
    is within bounds.
    """
    # Classical precomputation: which (r, f) have valid destinations
    valid_sources = []
    for r in range(board_rows):
        for f in range(board_cols):
            tr, tf = r + dr, f + df
            if 0 <= tr < board_rows and 0 <= tf < board_cols:
                valid_sources.append((r, f))

    @ql.compile(inverse=True)
    def piece_exists(piece_qarray, result):
        for r, f in valid_sources:
            with piece_qarray[r, f]:
                ~result

    return piece_exists
```

### No-Friendly-Capture Predicate Factory
```python
# Source: Derived from context decisions + _make_apply_move pattern
def make_no_friendly_capture_predicate(dr, df, board_rows, board_cols,
                                        num_friendly_boards):
    """Create a compiled predicate checking no friendly piece at target.

    For each source (r, f) with valid target (r+dr, f+df), checks that
    no friendly board has a piece at the target square.
    Result qbool is flipped to |1> if target is NOT occupied by friendly.
    """
    valid_sources = []
    for r in range(board_rows):
        for f in range(board_cols):
            tr, tf = r + dr, f + df
            if 0 <= tr < board_rows and 0 <= tf < board_cols:
                valid_sources.append((r, f, tr, tf))

    @ql.compile(inverse=True)
    def no_friendly_capture(piece_qarray, friendly_qarrays_flat, result):
        # friendly_qarrays_flat: list of qarrays for same-color pieces
        # For each valid source, check if target is friendly-occupied
        for r, f, tr, tf in valid_sources:
            with piece_qarray[r, f]:
                # Piece is here -- now check target for each friendly board
                # NOTE: Cannot nest with blocks. Need ancilla or sequential approach.
                # Since each board has at most one piece, can check each friendly
                # board separately and accumulate.
                pass  # Implementation requires careful flat design

    return no_friendly_capture
```

### Small-Board Test Setup (2x2)
```python
# Source: Derived from encode_position pattern + qarray dim constructor
import numpy as np
import quantum_language as ql

def make_small_board(rows, cols, occupied_squares):
    """Create a small board qarray with specified pieces."""
    data = np.zeros((rows, cols), dtype=int)
    for r, f in occupied_squares:
        data[r, f] = 1
    return ql.qarray(data, dtype=ql.qbool)

# Example 2x2 test
ql.circuit()
piece_board = make_small_board(2, 2, [(0, 0)])  # Piece at (0,0)
result = ql.qbool()
# Test: can piece move (dr=1, df=0) from (0,0) to (1,0)?
predicate = make_piece_exists_predicate("test", 1, 0, 2, 2)
predicate(piece_board, result)
```

### Statevector Verification Pattern
```python
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# Build circuit, export to QASM, run statevector simulation
# Compare result qbool amplitudes against classical expectation
sim = AerSimulator(method='statevector', max_parallel_threads=4)
# ... standard Qiskit statevector extraction ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Classical pre-filtering (legal_moves_white) | Quantum predicate in superposition | v8.0 (this phase) | Predicates evaluate legality at circuit level, not classically |
| Trivial always-valid predicate (chess_walk.py:297-310) | Real piece-exists + no-friendly-capture | v8.0 (this phase) | evaluate_children gets actual validity (Phase 116 wiring) |
| Raw gate emission for custom logic | Standard ql constructs only | v8.0 design decision | All application logic uses with/operators/@ql.compile |

**Deprecated/outdated:**
- `legal_moves_white`/`legal_moves_black` classical filtering: Still exists for reference but quantum predicates replace this for the walk.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, configured in conftest.py) |
| Config file | tests/python/conftest.py (clean_circuit fixture) |
| Quick run command | `pytest tests/python/test_chess_predicates.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRED-01 | piece-exists predicate returns correct qbool for piece at source | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestPieceExists -x` | No - Wave 0 |
| PRED-02 | no-friendly-capture rejects moves to friendly-occupied targets | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestNoFriendlyCapture -x` | No - Wave 0 |
| PRED-05 | predicates use @ql.compile(inverse=True) with working .inverse() | unit (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestCompileInverse -x` | No - Wave 0 |
| PRED-01/02 | classical equivalence on 2x2 board | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestClassicalEquivalence -x` | No - Wave 0 |
| PRED-01/02 | 8x8 circuit builds without error (no simulation) | smoke (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestScaling -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_chess_predicates.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_chess_predicates.py` -- covers PRED-01, PRED-02, PRED-05
- [ ] No new conftest fixtures needed (clean_circuit already exists)
- [ ] No new framework installs needed

## Open Questions

1. **No-Friendly-Capture: Flat Multi-Condition Pattern**
   - What we know: Cannot nest `with piece_qarray[r, f]:` inside `with friendly_board[tr, tf]:`. Need flat approach.
   - What's unclear: Best pattern for "piece exists at (r,f) AND friendly at (r+dr,f+df)" without nesting.
   - Recommendation: Use intermediate ancilla qbool. First `with piece_qarray[r, f]: ~ancilla` to flag piece presence, then `with ancilla: with friendly[tr, tf]:` -- wait, this is still nested. Alternative: use the qbool copy or `&=` operator to combine conditions into a single control. The `__enter__` code (qint.pyx:815-816) shows `_control_bool &= self` for the nested case, suggesting `&=` may work for AND. Need to verify whether the `&=` path actually works or is the TODO branch. **This is the key technical risk -- recommend testing the `&=` path early or using sequential XOR accumulation.**

2. **Double-Flip Correctness for Multi-Piece qarrays**
   - What we know: White knights qarray can have multiple |1> entries (2 knights). Piece-exists loops all squares with `~result` -- if 2 squares are |1>, result flips twice = |0>.
   - What's unclear: Whether the predicate design needs to handle this or whether the factory is always called with single-piece qarrays.
   - Recommendation: Context says factory is per-piece-type. For knights, the qarray represents ALL knights. If the question is "does ANY knight exist at a source for move (dr, df)", multiple knights at valid sources would cause double-flip. Either (a) ensure the predicate is called per-individual-piece (not per-type), or (b) use an ancilla accumulation pattern that implements OR rather than XOR. **Clarify with CONTEXT.md -- the factory takes `piece_qarray` which is the board for one piece type. For the KNK endgame with 1-2 knights, this matters.**

## Sources

### Primary (HIGH confidence)
- chess_encoding.py (src/) - Factory pattern, move tables, board encoding
- chess_walk.py (src/) - evaluate_children, validity pattern, _make_qbool_wrapper
- qint.pyx - `__enter__`/`__exit__` context manager (with conditional), `__invert__` (controlled NOT)
- qarray.pyx - Multi-dimensional indexing, element access, qbool element retrieval
- qbool.pyx - 1-bit qint subclass, context manager usage
- compile.py - @ql.compile decorator, inverse support
- 114-CONTEXT.md - User decisions constraining implementation

### Secondary (MEDIUM confidence)
- qint_bitwise.pxi - `__invert__` implementation (X/controlled-X emission)
- walk.py - counting_diffusion_core, _make_qbool_wrapper helper

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are project-internal, versions pinned
- Architecture: HIGH - Factory pattern proven in _make_apply_move, with/~ pattern established
- Pitfalls: HIGH - Nested with limitation confirmed in source code (qint.pyx TODO at line 814)
- No-friendly-capture flat design: MEDIUM - The AND-condition pattern needs empirical validation of `&=` path

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- project-internal framework, no external API changes)
