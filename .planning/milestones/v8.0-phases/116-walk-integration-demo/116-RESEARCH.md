# Phase 116: Walk Integration & Demo - Research

**Researched:** 2026-03-09
**Domain:** Quantum chess walk integration -- predicate wiring, move table oracle, demo rewrite
**Confidence:** HIGH

## Summary

Phase 116 integrates three prior phases into a complete quantum chess walk: Phase 113's `build_move_table` for all-moves enumeration, Phase 114-115's quantum predicates for legality evaluation, and Phase 113's `counting_diffusion_core` for variable-branching diffusion. The core work is rewriting `chess_walk.py` (primarily `prepare_walk_data` and `evaluate_children`) and `demo.py`.

The existing code is well-structured with clear integration points. The main complexity lies in: (1) building a new offset-based oracle factory that works with `build_move_table` entries `(piece_id, dr, df)` instead of the current `(piece_sq, dest_sq)` pairs, (2) wiring combined predicates with correct side-aware argument packing, and (3) replacing the `walk_step` closure pattern with explicit-arg `@ql.compile`.

**Primary recommendation:** Implement in three waves -- oracle/data-layer rewrite first, evaluate_children predicate wiring second, demo/cleanup third.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Pre-build all combined predicates at prepare_walk_data time, one per move entry in the table
- Store compiled predicates alongside move data in the per-level dict
- evaluate_children indexes predicate[i] and calls it with board qarrays + validity[i]
- Side-aware arg packing: prepare_walk_data determines which qarrays are friendly/enemy based on side-to-move, packs args per combined predicate signature (piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)
- Predicate call happens AFTER oracle applies the move (evaluate on child board state): encode child index -> flip height -> apply oracle -> evaluate predicate on resulting board -> undo
- Replace only the trivial reject+flip block in evaluate_children (steps d-e), keep steps (a)-(c) and (f)-(h) identical to preserve proven navigate-evaluate-undo pattern
- Replace get_legal_moves_and_oracle entirely in prepare_walk_data -- call build_move_table instead
- Oracle still transforms board state (apply_move); needed for derive/underive pattern
- Predicate evaluates legality of the resulting board independently
- Independent tables per side with independent branch widths: white levels d_max=24, branch_width=5; black levels d_max=8, branch_width=3
- Off-board moves: oracle emits identity (no-op), predicate naturally returns |0> (piece-exists fails)
- White moves: enemy_attacks = [(king_offsets, 'bk')]
- Black moves: enemy_attacks = [(king_offsets, 'wk'), (knight_offsets, 'wn')]
- Explicit qarray mapping stored in move_data per level: piece_qarray_key, friendly_keys, king_key, enemy_keys
- Update existing demo.py (replace old approach entirely)
- KNK position: white king e4, white knight c3, black king e8
- Walk depth 2 (white move + black response)
- Minimal stats output: qubit count, gate count, circuit depth, build time
- Circuit-build-only (no Qiskit simulation -- exceeds 17-qubit limit)
- Drop the complex _walk_ctx closure/mutable-dict pattern from walk_step
- Keep @ql.compile on walk_step with explicit args (no closure tricks)
- Keep all_walk_qubits mega-register but simplify and add clear docstring
- Simple key function based on qubit count instead of opaque lambda
- Remove get_legal_moves_and_oracle from chess_encoding.py
- Keep legal_moves_white/black as test-only helpers
- Remove old test_demo.py tests entirely, write new tests for rewritten demo
- Tests are circuit-build-only (no simulation) -- verify circuit construction succeeds, check stat assertions

### Claude's Discretion
- Exact structure of the per-level move_data dict (keys and values)
- How to thread qarray references through the predicate call signature
- Test assertions: specific gate count / qubit count ranges vs just "builds without error"
- Whether to keep or simplify precompute_diffusion_angles helper

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WALK-02 | Rewritten evaluate_children calls quantum legality predicate per move candidate instead of trivial always-valid check | Predicate wiring pattern documented; existing evaluate_children steps (a)-(c) and (f)-(h) preserved, only (d)-(e) replaced with combined_predicate call |
| WALK-04 | Rewritten chess_walk.py integrates quantum predicates, all-moves enumeration, and redesigned diffusion into complete walk step U = R_B * R_A | prepare_walk_data rewrite, new offset-based oracle, walk_step simplification all documented |
| WALK-05 | Demo serves as showcase -- all quantum logic via standard ql constructs, no raw gate emission | Demo design with KNK position, depth-2 walk, circuit-build-only stats documented |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (ql) | project-internal | Circuit construction, qint/qbool/qarray, @ql.compile | Framework being demonstrated |
| chess_encoding | project-internal | Board encoding, move tables, oracle factories | Existing Phase 104/113 infrastructure |
| chess_predicates | project-internal | Legality predicates (piece-exists, no-friendly, check-safe, combined) | Phase 114-115 predicates |
| walk.py | project-internal | counting_diffusion_core, _plan_cascade_ops | Phase 113 shared diffusion |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (existing) | qarray creation, qubit array manipulation | Board encoding, mega-register construction |
| math | stdlib | Angle computation (atan, sqrt, log2, ceil) | Montanaro angles, branch width |

## Architecture Patterns

### Recommended Project Structure
```
src/
  chess_walk.py       # Rewritten: prepare_walk_data, evaluate_children, walk_step
  chess_encoding.py   # Modified: remove get_legal_moves_and_oracle, keep build_move_table
  chess_predicates.py # Unchanged: used as-is from Phase 114-115
  demo.py             # Rewritten: KNK walk showcase
tests/python/
  test_demo.py        # Rewritten: circuit-build-only tests
  test_chess_walk.py  # Existing tests may need updates
```

### Pattern 1: Offset-Based Oracle Factory
**What:** New `_make_apply_move_from_table` factory that creates a compiled oracle from `build_move_table` entries `(piece_id, dr, df)` instead of fixed `(piece_sq, dest_sq)` pairs.
**When to use:** Called once per level in `prepare_walk_data`.
**Key insight:** For each table entry `(piece_id, dr, df)`, the oracle must iterate all 64 source squares and conditionally apply the move when `branch == i AND piece at (r,f)`. Off-board destinations `(r+dr, f+df)` are skipped classically (no gates emitted), implementing identity for invalid moves.

```python
# Pseudocode for offset-based oracle
def _make_apply_move_from_table(move_table, piece_key_to_board_idx):
    """Build compiled oracle from (piece_id, dr, df) table entries."""
    # Classical precomputation: for each entry, enumerate all valid (src, dst)
    flat_specs = []
    for piece_id, dr, df in move_table:
        board_idx = piece_key_to_board_idx[piece_id]
        for r in range(8):
            for f in range(8):
                tr, tf = r + dr, f + df
                if 0 <= tr < 8 and 0 <= tf < 8:
                    flat_specs.append((board_idx, r, f, tr, tf))
                # Off-board: no entry -> identity (no gates)

    @ql.compile(inverse=True)
    def apply_move(wk_arr, bk_arr, wn_arr, branch):
        boards = [wk_arr, bk_arr, wn_arr]
        for i, (board_idx, sr, sf, dr_, df_) in enumerate(flat_specs):
            cond = branch == i
            with cond:
                ~boards[board_idx][sr, sf]
                ~boards[board_idx][dr_, df_]
    return apply_move
```

**CRITICAL NOTE:** The above pseudocode has a flaw -- `flat_specs` has variable number of entries per move (valid source squares), but `branch == i` indexes into the move_table (one per branch value). The oracle must be indexed by branch register value (0..d_max-1), with each branch value mapping to exactly one move_table entry. The oracle iterates source squares WITHIN a branch condition, applying move only where piece exists. This mirrors the existing `_make_apply_move` pattern but with offset-based source enumeration.

Corrected approach:
```python
# For each branch value i -> move_table[i] = (piece_id, dr, df)
# For that entry, enumerate all valid (src_r, src_f) -> (dst_r, dst_f)
# Inside branch == i condition, swap src/dst for each valid source
```

### Pattern 2: Side-Aware Predicate Argument Packing
**What:** `prepare_walk_data` determines friendly/enemy qarrays based on side-to-move and stores qarray key mappings in move_data.
**When to use:** Each level in the walk tree alternates sides.

```python
# White's turn (level 0, 2, ...):
#   piece moving: wk or wn (from move_table piece_id)
#   friendly qarrays: [wk_arr, wn_arr] (minus the moving piece)
#   king for check: wk_arr (white king must not be in check)
#   enemy qarrays: [bk_arr] (only enemy attacks relevant)
#   enemy_attacks: [(_KING_OFFSETS, 'bk')]

# Black's turn (level 1, 3, ...):
#   piece moving: bk (only black king in KNK)
#   friendly qarrays: [] (no other black pieces)
#   king for check: bk_arr (black king must not be in check)
#   enemy qarrays: [wk_arr, wn_arr] (both can attack)
#   enemy_attacks: [(_KING_OFFSETS, 'wk'), (_KNIGHT_OFFSETS, 'wn')]
```

### Pattern 3: Simplified walk_step with Explicit Args
**What:** Replace the `_walk_ctx` closure/mutable-dict pattern with a straightforward `@ql.compile` that takes explicit arguments.
**When to use:** The walk_step function.

```python
def walk_step(h_reg, branch_regs, board_arrs, oracle_per_level,
              move_data_per_level, max_depth):
    from quantum_language.compile import compile as ql_compile

    mega_reg = all_walk_qubits(h_reg, branch_regs, max_depth)

    @ql_compile(key=lambda *args: mega_reg.width + sum(len(a) for a in board_arrs))
    def _walk_body(walk_qubits_reg, wk_arr, bk_arr, wn_arr):
        _board = (wk_arr, bk_arr, wn_arr)
        r_a(h_reg, branch_regs, _board, oracle_per_level, move_data_per_level, max_depth)
        r_b(h_reg, branch_regs, _board, oracle_per_level, move_data_per_level, max_depth)

    wk, bk, wn = board_arrs
    _walk_body(mega_reg, wk, bk, wn)
```

### Pattern 4: Per-Level Move Data Dict Structure
**What:** Recommended structure for the per-level dict returned by `prepare_walk_data`.

```python
{
    'move_table': [(piece_id, dr, df), ...],  # from build_move_table
    'move_count': int,          # len(move_table) = d_max for this level
    'branch_width': int,        # ceil(log2(move_count))
    'apply_move': CompiledFunc, # offset-based oracle
    'predicates': [CompiledFunc, ...],  # one combined predicate per entry
    'piece_qarray_key': str,    # key for each entry's piece qarray
    'friendly_keys': [str, ...],  # keys for friendly qarrays
    'king_key': str,            # key for king qarray (for check detection)
    'enemy_keys': [str, ...],   # keys for enemy qarrays
}
```

**Note:** `piece_qarray_key` may vary per entry (wk vs wn for white's turn). Consider storing per-entry metadata or a list of per-entry key tuples.

### Anti-Patterns to Avoid
- **Closure capture for @ql.compile args:** The existing `_walk_ctx` dict pattern is fragile and unreadable. Use explicit arguments instead.
- **Nested with qbool:** Raises NotImplementedError. Always use `&` operator for Toffoli AND.
- **Raw gate emission in demo code:** Defeats WALK-05. All application logic must use `with`, operators, `@ql.compile`, `ql.array`.
- **Running simulation on chess circuits:** Exceeds 17-qubit limit. Circuit-build-only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Piece-exists check | Custom gate sequence | `make_piece_exists_predicate` | Phase 114 handles all edge cases |
| Friendly capture check | Custom gate sequence | `make_no_friendly_capture_predicate` | Phase 114 handles ancilla management |
| Check detection | Custom gate sequence | `make_check_detection_predicate` | Phase 115 handles attack tables |
| Combined legality | Manual AND of sub-predicates | `make_combined_predicate` | Phase 115 handles 3-way AND + uncomputation |
| Variable-branching diffusion | Custom diffusion operator | `counting_diffusion_core` | Phase 113 handles O(d_max) counting circuit |
| Move enumeration | Manual offset loops | `build_move_table` | Phase 113 handles piece type dispatch |

## Common Pitfalls

### Pitfall 1: Oracle Must Use Branch Index, Not Source Square Index
**What goes wrong:** Building an oracle where each branch value maps to a (source, destination) pair requires knowing all valid source squares at construction time. With offset-based moves, each branch value i maps to one (piece_id, dr, df) entry, but the actual source square depends on the quantum board state.
**Why it happens:** The existing `_make_apply_move` knows exact source squares from classical pre-filtering.
**How to avoid:** The new oracle must enumerate ALL 64 possible source squares for each branch value and apply the move conditionally on `branch == i` AND piece at source. Off-board destinations are filtered classically (no gates emitted).
**Warning signs:** Oracle produces different gate counts than expected; off-board moves produce gates instead of identity.

### Pitfall 2: Side-Aware Argument Order for Combined Predicate
**What goes wrong:** The combined predicate signature is `(piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)`. Getting the order wrong produces incorrect legality evaluation.
**Why it happens:** White and black levels have different piece/friendly/enemy configurations.
**How to avoid:** Store explicit qarray key lists in move_data per level. At evaluate_children time, look up actual qarrays from board_arrs tuple using stored keys.
**Warning signs:** Predicates pass for illegal moves or reject legal ones.

### Pitfall 3: Per-Entry Piece Type Varies Within a Level
**What goes wrong:** For white's turn, move_table entries alternate between 'wk' (king moves) and 'wn' (knight moves). Each entry's combined predicate uses a different `piece_type` parameter and different `piece_qarray`.
**Why it happens:** `build_move_table` with `[('wk', 'king'), ('wn', 'knight')]` produces 16 entries: 8 king + 8 knight.
**How to avoid:** Build one combined predicate per entry (not per level). Each predicate is parameterized by its entry's `(piece_type, dr, df)`. Store the predicate AND qarray key mapping per entry, or use per-entry metadata lists.
**Warning signs:** All entries use the same piece type or wrong piece qarray.

### Pitfall 4: Memory/Gate Count for Depth-2 Walk
**What goes wrong:** Each combined predicate uses ~34 qubits (from Phase 115 research). With d_max=24 for white and d_max=8 for black, the circuit may be very large.
**Why it happens:** Each evaluate_children call allocates validity ancillae and predicate ancillae for d_max children.
**How to avoid:** Circuit-build-only (no simulation). Accept large circuits for the demo. The test should verify construction succeeds, not gate counts within a narrow range.
**Warning signs:** OOM during circuit construction.

### Pitfall 5: Predicate Evaluation Timing (After Oracle)
**What goes wrong:** Evaluating the predicate on the root board state instead of the child board state.
**Why it happens:** The predicate must evaluate legality of the move's RESULT, not the starting position.
**How to avoid:** Follow the locked decision: encode child index -> flip height -> apply oracle -> evaluate predicate on resulting board -> undo. Steps (a)-(c) navigate to child state, (d) evaluates predicate, (e) uncomputes predicate, (f)-(h) undo navigation.
**Warning signs:** All moves appear legal (predicate evaluates starting position where king isn't in check).

### Pitfall 6: Uncompute Order in evaluate_children
**What goes wrong:** `uncompute_children` must mirror `evaluate_children` in exact reverse.
**Why it happens:** Quantum uncomputation requires exact reversal of gate sequence.
**How to avoid:** `uncompute_children` iterates in reversed range, calls predicate.adjoint() instead of predicate(), reverses validity store operations.
**Warning signs:** Ancilla qubits not returned to |0>, circuit verification fails.

## Code Examples

### evaluate_children with Combined Predicate (Steps d-e Replacement)

```python
def evaluate_children(
    depth, level_idx, d_max, branch_reg, h_reg, max_depth,
    oracle, board_arrs, validity, predicates, qarray_args_per_entry
):
    wk, bk, wn = board_arrs
    height_mask = 3 << (max_depth - depth)

    for i in range(d_max):
        # (a) Encode child index
        branch_reg ^= i
        # (b) Flip height
        h_reg ^= height_mask
        # (c) Apply oracle
        oracle(wk, bk, wn, branch_reg)

        # (d) Evaluate combined predicate on child board state
        pred = predicates[i]
        pred_args = qarray_args_per_entry[i]  # resolved qarray references
        pred(*pred_args, validity[i])

        # (e) Uncompute predicate (adjoint)
        # Not needed here -- predicate result stays in validity[i]
        # Adjoint is called in uncompute_children

        # (f) Uncompute oracle
        oracle.inverse(wk, bk, wn, branch_reg)
        # (g) Undo height flip
        h_reg ^= height_mask
        # (h) Undo branch encoding
        branch_reg ^= i
```

### Board Array Key Resolution

```python
# Board arrays indexed by key
BOARD_KEYS = {'wk': 0, 'bk': 1, 'wn': 2}

def resolve_qarray_args(board_arrs, entry_piece_id, friendly_keys, king_key, enemy_keys):
    """Resolve qarray references for a single predicate call."""
    piece_arr = board_arrs[BOARD_KEYS[entry_piece_id]]
    friendly_arrs = [board_arrs[BOARD_KEYS[k]] for k in friendly_keys]
    king_arr = board_arrs[BOARD_KEYS[king_key]]
    enemy_arrs = [board_arrs[BOARD_KEYS[k]] for k in enemy_keys]
    return (piece_arr, *friendly_arrs, king_arr, *enemy_arrs)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `get_legal_moves_and_oracle` (classical pre-filter) | `build_move_table` + quantum predicates | Phase 113-115 (v8.0) | All moves enumerated, legality checked in superposition |
| Trivial validity predicate (always |1>) | `make_combined_predicate` (3-condition check) | Phase 114-115 (v8.0) | Real legality evaluation: piece-exists AND no-friendly AND not-in-check |
| O(2^d_max) itertools diffusion | `counting_diffusion_core` O(d_max) | Phase 113 (v8.0) | Scalable to large branching factors |
| Closure-based `_walk_ctx` pattern | Explicit-arg `@ql.compile` | Phase 116 (this phase) | Readable, debuggable walk_step |

## Open Questions

1. **Per-entry vs per-level oracle**
   - What we know: Each level has one `apply_move` oracle that handles all branch values. The move_table entries define what each branch value does.
   - What's unclear: Should there be one oracle per level (iterating all entries with `branch == i` conditions) or should the oracle pattern change?
   - Recommendation: One oracle per level is correct -- matches existing pattern. The factory just changes from position-specific moves to offset-enumerated moves.

2. **Walk_step @ql.compile caching**
   - What we know: The existing code uses a module-level `_walk_compiled_fn` for caching. The user wants to remove the closure pattern.
   - What's unclear: Whether `@ql.compile` decorator can be applied inline (per-call) without the module-level cache.
   - Recommendation: Create the compiled function once at module level or use a local `@ql_compile(key=...)` decorator inside `walk_step`. The key function should be simple (total qubit count).

3. **Friendly qarrays for white king moves**
   - What we know: When white king moves, friendly qarrays = [wn_arr] (white knights). When white knight moves, friendly qarrays = [wk_arr, wn_arr]? Or [wk_arr]?
   - What's unclear: Should the moving piece's qarray be excluded from friendlies?
   - Recommendation: The moving piece IS checked by piece-exists. The no-friendly-capture checks the TARGET square. The moving piece's own qarray should be in friendly_qarrays because it checks the destination, not the source. However, the moving piece itself will be at the source (not target) in the child state, so including it is correct -- it prevents self-capture scenarios.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/python/conftest.py |
| Quick run command | `pytest tests/python/test_demo.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WALK-02 | evaluate_children calls quantum predicate | unit | `pytest tests/python/test_chess_walk.py -x -v -k evaluate` | Needs update |
| WALK-04 | Integrated walk step builds circuit | integration | `pytest tests/python/test_demo.py -x -v` | Needs rewrite |
| WALK-05 | Demo uses only ql constructs | integration | `pytest tests/python/test_demo.py -x -v` | Needs rewrite |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_demo.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/python/test_demo.py` -- needs complete rewrite (old tests depend on patched walk_step, new tests should be circuit-build-only)
- [ ] test_chess_walk.py may need updates for new evaluate_children signature

## Sources

### Primary (HIGH confidence)
- `src/chess_walk.py` -- current implementation, all integration points identified
- `src/chess_encoding.py` -- build_move_table, _make_apply_move, get_legal_moves_and_oracle
- `src/chess_predicates.py` -- make_combined_predicate signature and internals
- `src/quantum_language/walk.py` -- counting_diffusion_core signature
- `src/demo.py` -- current demo structure
- `.planning/phases/116-walk-integration-demo/116-CONTEXT.md` -- locked decisions

### Secondary (MEDIUM confidence)
- Phase 115 STATE.md notes on combined predicate qubit count (34 qubits for 2x2)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries are project-internal, code read directly
- Architecture: HIGH - existing patterns well-understood, integration points clear
- Pitfalls: HIGH - based on direct code analysis of current implementation gaps

**Research date:** 2026-03-09
**Valid until:** 2026-03-16 (project-internal, stable)
