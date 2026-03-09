# Phase 115: Check Detection & Combined Predicate - Research

**Researched:** 2026-03-09
**Domain:** Quantum check detection predicate + combined move legality predicate using ql constructs
**Confidence:** HIGH

## Summary

This phase adds two new predicate factories to `chess_predicates.py`: (1) a check detection predicate that verifies the king is not in check after a move by iterating over precomputed attack tables, and (2) a combined move legality predicate that composes piece-exists, no-friendly-capture, and check detection into a single qbool result.

Both predicates follow the established factory pattern from Phase 114: classical precomputation outside `@ql.compile(inverse=True)`, quantum operations inside using only standard ql constructs (`with`, `~`, `&` operator). The check detection predicate mirrors the no-friendly-capture flip-and-unflip pattern: optimistically flip result to |1> (safe), then conditionally un-flip when an enemy attacker is found at a square that attacks the king's position. The combined predicate calls all three sub-predicates sequentially and ANDs their results via chained `&` operator.

The key technical consideration is qubit budget for testing. Check detection alone on 2x2 boards fits comfortably (~11 qubits). The combined predicate requires careful test design because sharing board qarrays between sub-predicates is necessary to stay within the 17-qubit simulation limit. The recommended approach is: (a) test check detection independently with statevector verification on 2x2, (b) test combined predicate with minimal board setups where qarrays are shared (same object passed as both friendly and king), and (c) use circuit-only (no simulation) tests for 8x8 scaling verification.

**Primary recommendation:** Extend `chess_predicates.py` with two new factory functions following the exact flip-and-unflip pattern from `make_no_friendly_capture_predicate`. Use parameterized offset helpers (not the 8x8-hardcoded `knight_attacks`/`king_attacks`) for attack table construction.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Position-based check detection: classical loop over all possible king squares, `with king_qarray[r, f]:` to condition on king being there, then check if enemy pieces attack that square
- No discovered checks possible in KNK (no sliding pieces) -- moving a knight never exposes the king
- Parameterized by move: for king moves, check enemies attacking destination (r+dr, f+df); for knight moves, check enemies attacking king's current position (r, f)
- Side-specific factories: factory takes enemy_qarrays + enemy attack offsets specific to each side (white king safety: check black king adjacency only; black king safety: check white king adjacency + white knight L-shapes)
- Result polarity: |1> = king is safe (NOT in check) -- consistent with piece-exists and no-friendly-capture where |1> means "condition passed"
- Attack table structure: classical Python precomputation at circuit construction time, same pattern as Phase 114's valid_sources
- Merged attacker list: for each possible king square (r,f), precompute ALL (ar, af, enemy_qarray) triples that could attack it -- single loop in quantum body
- New parameterized helpers using _KNIGHT_OFFSETS/_KING_OFFSETS with (row, col) pairs and board_rows/board_cols bounds checking -- existing 8x8 helpers stay for classical move generation
- Mirror no-friendly-capture logic pattern: start by flipping result to |1> (optimistic: assume safe), then un-flip for each enemy found at an attacking square using `&` operator
- Combined predicate composition: sequential calls + AND -- call each sub-predicate separately, each writes to its own result qbool, then AND the three results into a final qbool
- Combined predicate is itself a @ql.compile(inverse=True) factory -- allocates three intermediate qbools, calls sub-predicates, ANDs into final result
- Factory builds all three sub-predicates internally from raw parameters -- single entry point for callers
- Three-way AND via chained `&` operator: `result = a & b`, then `final = result & c` -- two Toffoli gates, one intermediate ancilla
- Extend chess_predicates.py -- all predicate factories in one module
- Check detection: `make_check_detection_predicate(moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks)` where enemy_attacks is list of (offset_list, piece_type_str) tuples. Returns compiled func: `check_safe(king_qarray, *enemy_qarrays, result)`
- Combined: `make_combined_predicate(piece_type, dr, df, board_rows, board_cols, enemy_attacks)` returns compiled func: `is_legal(piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)`. Internally builds all three sub-predicates.

### Claude's Discretion
- Exact ancilla management within compiled predicate bodies
- Internal structure of the attack table precomputation helpers
- How the combined predicate orders sub-predicate calls
- Classical helper functions for offset computation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRED-03 | Quantum check detection predicate verifies king is not in check after a move using pre-computed attack tables (knight L-shapes + king adjacency) evaluated via `with` conditionals on board qarray | Flip-and-unflip pattern from no-friendly-capture, classical attack table precomputation, parameterized offset helpers |
| PRED-04 | Combined move legality predicate composes piece-exists, no-friendly-capture, and check detection using standard `with qbool:` conditional nesting and boolean operators | Sequential sub-predicate calls + chained `&` operator for three-way AND, single @ql.compile factory |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | project-local | qarray, qbool, qint, @ql.compile, `with`, `&` operator | Project's core framework |
| numpy | installed | Board initialization arrays for qarray construction | Used throughout project |
| pytest | installed | Test framework with clean_circuit fixture | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit-aer | installed | AerSimulator statevector for 2x2 verification | Small-board tests within 17-qubit limit |

### Alternatives Considered
None -- all tooling is project-established. No new dependencies needed.

**Installation:**
No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/
  chess_predicates.py     # EXTEND: Add check detection + combined predicate factories
  chess_encoding.py       # Existing: _KNIGHT_OFFSETS, _KING_OFFSETS, legal_moves_*
  chess_walk.py           # Existing: Phase 116 integration point
tests/python/
  test_chess_predicates.py  # EXTEND: Add check detection + combined predicate tests
```

### Pattern 1: Flip-and-Unflip for Check Detection
**What:** Optimistically flip result to |1> (safe), then conditionally un-flip when an enemy attacker is found. Mirrors `make_no_friendly_capture_predicate`.
**When to use:** Check detection -- king is safe unless an enemy piece occupies an attacking square.
**Example:**
```python
# Source: Derived from chess_predicates.py:87 (no-friendly-capture pattern)
def make_check_detection_predicate(moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks):
    # Classical precomputation: for each possible king position,
    # compute all (attacker_row, attacker_file, enemy_qarray_index) triples
    attack_table = []  # list of (king_r, king_f, attackers)
    for kr in range(board_rows):
        for kf in range(board_cols):
            # Determine king square to check based on move type
            if moving_piece_type == "king":
                check_r, check_f = kr + dr, kf + df  # check destination
                if not (0 <= check_r < board_rows and 0 <= check_f < board_cols):
                    continue
            else:
                check_r, check_f = kr, kf  # check current position

            attackers = []
            for enemy_idx, (offsets, _piece_type_str) in enumerate(enemy_attacks):
                for adr, adf in offsets:
                    ar, af = check_r + adr, check_f + adf
                    if 0 <= ar < board_rows and 0 <= af < board_cols:
                        attackers.append((ar, af, enemy_idx))

            if moving_piece_type == "king":
                attack_table.append((kr, kf, attackers))
            else:
                attack_table.append((kr, kf, attackers))

    @ql.compile(inverse=True)
    def check_safe(king_qarray, *args):
        enemy_qarrays = args[:-1]
        result = args[-1]

        for kr, kf, attackers in attack_table:
            with king_qarray[kr, kf]:
                # Optimistic: flip to |1> (assume safe)
                ~result

            # For each attacker, un-flip if king here AND attacker present
            for ar, af, enemy_idx in attackers:
                enemy_flag = ql.qbool()
                with enemy_qarrays[enemy_idx][ar, af]:
                    ~enemy_flag

                cond = king_qarray[kr, kf] & enemy_flag
                with cond:
                    ~result  # un-flip: king in check

                # Uncompute enemy_flag
                with enemy_qarrays[enemy_idx][ar, af]:
                    ~enemy_flag

    return check_safe
```

### Pattern 2: Three-Way AND via Chained `&` Operator
**What:** Compose three qbool results into one using `a & b`, then `(a & b) & c`. Each `&` produces a Toffoli gate with an auto-uncomputed ancilla.
**When to use:** Combined predicate composition.
**Example:**
```python
# Source: Established in Phase 114 (qint_bitwise.pxi __and__)
# a, b, c are qbool results from sub-predicates
ab = a & b       # Toffoli: allocates ancilla, computes AND
final = ab & c   # Second Toffoli: AND of all three
with final:
    ~result       # Flip final result
```

### Pattern 3: Combined Predicate as Outer Factory
**What:** A factory that internally creates all three sub-predicates and composes them within a single `@ql.compile(inverse=True)` body.
**When to use:** The `make_combined_predicate` function.
**Key consideration:** Sub-predicates CANNOT be called as compiled functions inside another `@ql.compile` body. Instead, the combined predicate must inline the logic of each sub-predicate (or call them as regular functions if the framework supports nested compiled calls). Based on Phase 114's established pattern, each sub-predicate's logic should be inlined directly.

### Anti-Patterns to Avoid
- **Nested `with qbool:` blocks:** Framework raises NotImplementedError. Use `&` operator for AND conditions.
- **Using 8x8-hardcoded `knight_attacks()`/`king_attacks()`:** These return square indices for 8x8 boards. Use `_KNIGHT_OFFSETS`/`_KING_OFFSETS` with parameterized bounds checking instead.
- **Calling compiled sub-predicates inside compiled combined predicate:** Nested `@ql.compile` calls may not work correctly. Inline the sub-predicate logic or use the sub-predicate factories to get the logic pattern, then replicate it in the combined body.
- **Double-flip without unflip:** If the same result qbool could be flipped by multiple king positions (superposition), the XOR=OR property relies on exactly one king per board. This holds for KNK.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ancilla uncomputation | Manual inverse gate sequences | `@ql.compile(inverse=True)` | Framework handles forward/inverse lifecycle |
| Board square indexing | Custom qubit offset math | `board[rank, file]` qarray indexing | qarray handles multi-dim indexing |
| AND of two qbools | Manual Toffoli gate emission | `a & b` operator | Allocates ancilla, emits Toffoli, handles lifecycle |
| Attack offset enumeration | Hardcoded per-predicate lists | `_KNIGHT_OFFSETS` / `_KING_OFFSETS` from chess_encoding | Already defined, tested, canonical |
| Classical legal move verification | New verification logic | `legal_moves_white()` / `legal_moves_black()` | Existing classical equivalents for test oracles |

**Key insight:** The check detection predicate is structurally identical to no-friendly-capture -- both use the flip-and-unflip pattern with per-position ancilla. The only difference is WHAT is being checked (enemy attackers vs friendly pieces at target).

## Common Pitfalls

### Pitfall 1: King Position in Superposition
**What goes wrong:** Treating king position as classically known (single square) instead of iterating over all possible positions with `with king_qarray[r, f]:`.
**Why it happens:** In classical chess, king position is known. In quantum walk, the king is in superposition.
**How to avoid:** Always loop over ALL board squares with `with king_qarray[r, f]:` conditioning. The quantum `with` ensures only the basis states where the king IS at (r, f) are affected.
**Warning signs:** Code that hardcodes a king square in the check detection predicate body.

### Pitfall 2: King Move vs Knight Move Check Direction
**What goes wrong:** Checking the wrong square for attacks. For king moves, need to check if enemies attack the DESTINATION. For knight moves, need to check if enemies attack the king's CURRENT position (since knight can't discover check in KNK).
**Why it happens:** Both are "check detection" but the relevant square differs.
**How to avoid:** The `moving_piece_type` parameter controls which square to check: king moves use (kr+dr, kf+df), knight moves use (kr, kf).
**Warning signs:** King moving into check not detected, or knight moves incorrectly flagged.

### Pitfall 3: Qubit Budget for Combined Predicate Testing
**What goes wrong:** Combined predicate simulation test exceeds 17-qubit limit.
**Why it happens:** Full KNK on 2x2 needs: piece_qarray(4) + friendly_qarrays(4-8) + king_qarray(4, shared) + enemy_qarrays(4-8) + intermediate qbools(3) + final result(1) + ancillas. Can exceed 17 easily.
**How to avoid:**
  - Share board qarrays: king_qarray can be the SAME Python object as one of the friendly_qarrays (no extra qubits)
  - Test check detection independently (fewer boards needed)
  - Test combined with minimal configuration: e.g., white knight move needs piece=wn(4), friendly=wk(4), king=wk(same 4), enemy=bk(4) = 12 data + 4 results + ancillas = ~18. May need to simplify further or use 1x2 boards.
  - Use circuit-only (no simulation) tests for 8x8 combined predicate
**Warning signs:** AerSimulator hanging or OOM during combined predicate tests.

### Pitfall 4: `&` Operator Ancilla in Loops
**What goes wrong:** The `&` operator allocates an ancilla qbool each time. In loops, accumulated ancillas consume qubits.
**Why it happens:** Each `cond = king_qarray[kr, kf] & enemy_flag` allocates a fresh ancilla.
**How to avoid:** Phase 114 solved this with per-source ancilla allocation and explicit uncomputation. Follow the same pattern: allocate enemy_flag per attacker iteration, uncompute after use. The `&` operator's ancilla is auto-managed.
**Warning signs:** Qubit count growing linearly with number of attackers in the attack table.

### Pitfall 5: Nested Compiled Function Calls
**What goes wrong:** Calling a `@ql.compile(inverse=True)` function inside another `@ql.compile` body may not compose correctly.
**Why it happens:** The compile decorator records gate sequences for replay. Nesting may interfere with the recording mechanism.
**How to avoid:** The combined predicate should inline the sub-predicate logic directly rather than calling the compiled sub-predicate functions. Alternatively, test whether compiled function calls within compiled bodies work in the framework -- if they do, this simplifies the implementation significantly.
**Warning signs:** Incorrect gate sequences, missing gates in the inverse, or runtime errors during compilation.

### Pitfall 6: Forgetting to Uncompute Ancillas in Check Detection
**What goes wrong:** `enemy_flag` ancillas left in non-|0> state prevent correct `@ql.compile(inverse=True)` behavior.
**Why it happens:** The flip-and-unflip pattern requires explicit uncomputation of intermediate ancillas.
**How to avoid:** Mirror the accumulation exactly: for each `with enemy_qarray[ar, af]: ~enemy_flag`, add corresponding uncomputation after the `&`-controlled result flip. Follow the no-friendly-capture pattern line-for-line.
**Warning signs:** Statevector tests showing unexpected amplitudes; ancilla qubits not returning to |0>.

## Code Examples

### Check Detection Factory (Full Pattern)
```python
# Source: Derived from chess_predicates.py:87-189 (no-friendly-capture)
from chess_encoding import _KNIGHT_OFFSETS, _KING_OFFSETS

def _compute_attack_table(moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks):
    """Precompute attack table: for each king position, list all attacker squares.

    Returns list of (king_r, king_f, [(attacker_r, attacker_f, enemy_idx), ...])
    """
    table = []
    for kr in range(board_rows):
        for kf in range(board_cols):
            # Which square are we checking for attacks?
            if moving_piece_type == "king":
                check_r, check_f = kr + dr, kf + df
                if not (0 <= check_r < board_rows and 0 <= check_f < board_cols):
                    continue  # king destination off-board -> skip
            else:
                check_r, check_f = kr, kf  # knight move -> check king's current pos

            attackers = []
            for enemy_idx, (offsets, _label) in enumerate(enemy_attacks):
                for adr, adf in offsets:
                    ar, af = check_r + adr, check_f + adf
                    if 0 <= ar < board_rows and 0 <= af < board_cols:
                        attackers.append((ar, af, enemy_idx))

            table.append((kr, kf, attackers))
    return table


def make_check_detection_predicate(moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks):
    attack_table = _compute_attack_table(
        moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks
    )

    @ql.compile(inverse=True)
    def check_safe(king_qarray, *args):
        enemy_qarrays = args[:-1]
        result = args[-1]

        for kr, kf, attackers in attack_table:
            # Optimistic flip: if king is at (kr, kf), assume safe
            with king_qarray[kr, kf]:
                ~result

            # Un-flip for each attacker found
            for ar, af, enemy_idx in attackers:
                enemy_flag = ql.qbool()
                with enemy_qarrays[enemy_idx][ar, af]:
                    ~enemy_flag

                cond = king_qarray[kr, kf] & enemy_flag
                with cond:
                    ~result

                # Uncompute enemy_flag
                with enemy_qarrays[enemy_idx][ar, af]:
                    ~enemy_flag

    return check_safe
```

### Combined Predicate Factory (Sketch)
```python
def make_combined_predicate(piece_type, dr, df, board_rows, board_cols, enemy_attacks):
    # Build sub-predicates at construction time
    pe_pred = make_piece_exists_predicate(piece_type, dr, df, board_rows, board_cols)
    nfc_pred = make_no_friendly_capture_predicate(dr, df, board_rows, board_cols)
    cd_pred = make_check_detection_predicate(
        piece_type, dr, df, board_rows, board_cols, enemy_attacks
    )

    @ql.compile(inverse=True)
    def is_legal(piece_qarray, *args):
        # Parse variadic args: *friendly_qarrays, king_qarray, *enemy_qarrays, result
        # Exact parsing depends on signature convention
        result = args[-1]

        # Allocate intermediate qbools
        pe_result = ql.qbool()
        nfc_result = ql.qbool()
        cd_result = ql.qbool()

        # Call sub-predicates (or inline their logic)
        pe_pred(piece_qarray, pe_result)
        nfc_pred(piece_qarray, *friendly_qarrays_slice, nfc_result)
        cd_pred(king_qarray_ref, *enemy_qarrays_slice, cd_result)

        # Three-way AND
        ab = pe_result & nfc_result
        abc = ab & cd_result
        with abc:
            ~result

        # Uncompute sub-predicate results (adjoint calls)
        cd_pred.adjoint(king_qarray_ref, *enemy_qarrays_slice, cd_result)
        nfc_pred.adjoint(piece_qarray, *friendly_qarrays_slice, nfc_result)
        pe_pred.adjoint(piece_qarray, pe_result)

    return is_legal
```

### Parameterized Attack Offset Helper
```python
# Source: chess_encoding.py:42-63 (_KNIGHT_OFFSETS, _KING_OFFSETS)
def attacks_for_piece_type(piece_type_str, board_rows, board_cols):
    """Return (offset_list, label) for a piece type, parameterized by board size.

    Unlike knight_attacks()/king_attacks() which are hardcoded to 8x8,
    this returns raw offsets that callers filter with board bounds.
    """
    from chess_encoding import _KNIGHT_OFFSETS, _KING_OFFSETS
    if piece_type_str == "knight":
        return (_KNIGHT_OFFSETS, "knight")
    elif piece_type_str == "king":
        return (_KING_OFFSETS, "king")
    else:
        raise ValueError(f"Unknown piece type: {piece_type_str}")
```

### Test Pattern: Classical Equivalence for Check Detection
```python
def _classical_check_safe(king_pos, enemy_positions, enemy_attacks, moving_piece_type, dr, df, board_rows, board_cols):
    """Classical: is king safe after move (dr, df)?

    For king moves: check if destination (kr+dr, kf+df) is attacked.
    For knight moves: check if king's current position is attacked.
    """
    kr, kf = king_pos
    if moving_piece_type == "king":
        check_r, check_f = kr + dr, kf + df
        if not (0 <= check_r < board_rows and 0 <= check_f < board_cols):
            return False  # destination off-board
    else:
        check_r, check_f = kr, kf

    for enemy_idx, (offsets, _label) in enumerate(enemy_attacks):
        for adr, adf in offsets:
            ar, af = check_r + adr, check_f + adf
            if 0 <= ar < board_rows and 0 <= af < board_cols:
                if (ar, af) in enemy_positions[enemy_idx]:
                    return False  # attacked!
    return True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Classical check detection (legal_moves_white/black) | Quantum check predicate in superposition | v8.0 Phase 115 | King safety evaluated at circuit level for all basis states simultaneously |
| Separate legality conditions tested independently | Combined predicate with single qbool output | v8.0 Phase 115 | Walk integration (Phase 116) gets single validity flag per move |

**Deprecated/outdated:**
- `knight_attacks(sq)` / `king_attacks(sq)`: Still used for classical move generation but NOT for quantum predicates (hardcoded to 8x8). Use `_KNIGHT_OFFSETS`/`_KING_OFFSETS` with parameterized bounds instead.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in tests/python/conftest.py) |
| Config file | tests/python/conftest.py (clean_circuit fixture) |
| Quick run command | `pytest tests/python/test_chess_predicates.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRED-03 | Check detection returns safe/unsafe for king positions with enemy attackers | unit (statevector 2x2) | `pytest tests/python/test_chess_predicates.py::TestCheckDetection -x` | Exists (extend) |
| PRED-03 | Check detection classical equivalence on 2x2 board | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestCheckDetectionClassical -x` | Extend |
| PRED-04 | Combined predicate returns correct legality flag | unit (statevector 2x2) | `pytest tests/python/test_chess_predicates.py::TestCombinedPredicate -x` | Extend |
| PRED-04 | Combined predicate classical equivalence on 2x2 | integration (statevector) | `pytest tests/python/test_chess_predicates.py::TestCombinedClassical -x` | Extend |
| PRED-03/04 | 8x8 circuits build without error (no simulation) | smoke (circuit gen) | `pytest tests/python/test_chess_predicates.py::TestScalingPhase115 -x` | Extend |
| PRED-03 | Check detection adjoint roundtrip | unit (statevector) | `pytest tests/python/test_chess_predicates.py::TestCheckDetection::test_adjoint_roundtrip -x` | Extend |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_chess_predicates.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Add TestCheckDetection class to `tests/python/test_chess_predicates.py`
- [ ] Add TestCombinedPredicate class to `tests/python/test_chess_predicates.py`
- [ ] Add TestScalingPhase115 class for 8x8 circuit-only tests
- [ ] Classical equivalence helpers for check detection

### Qubit Budget Analysis for Tests

| Test Scenario | Boards | Data Qubits | Ancillas (est.) | Total (est.) | Feasible? |
|---------------|--------|-------------|-----------------|-------------|-----------|
| Check detection alone (2x2) | king(4) + 1 enemy(4) + result(1) | 9 | ~3 | ~12 | Yes |
| Check detection (2x2, 2 enemies) | king(4) + 2 enemies(8) + result(1) | 13 | ~4 | ~17 | Tight but yes |
| Combined (2x2, minimal) | piece(4) + king=friendly(4, shared) + enemy(4) + 4 results | 16 | ~4 | ~20 | Over budget |
| Combined (2x2, reduced) | 2 distinct boards(8) + 4 results | 12 | ~4 | ~16 | Feasible with care |

**Recommendation for combined predicate testing:** Use the absolute minimum board count. For a white knight move test: piece_qarray=wn(4), friendly+king=wk(4, one board serving both roles), enemy=bk(4). Total data = 12 + 4 results + ancillas. If ancillas exceed 1, consider testing the combined predicate's logic by verifying each sub-predicate independently (which are already tested) and testing only the AND composition with a small circuit.

## Open Questions

1. **Nested Compiled Function Calls**
   - What we know: The combined predicate needs to call sub-predicates within a `@ql.compile` body. Phase 114's sub-predicates are themselves `@ql.compile(inverse=True)` functions.
   - What's unclear: Whether calling a compiled function inside another compiled function's body works correctly in the framework (gate recording, inverse lifecycle).
   - Recommendation: Test this early. If it works, the combined predicate is straightforward. If not, inline the sub-predicate logic (copy the loop structures) into the combined body. The CONTEXT.md decision says the factory "internally builds all three sub-predicates" -- this is compatible with either approach.

2. **Variadic Argument Parsing in Combined Predicate**
   - What we know: Signature is `is_legal(piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)`. But Python doesn't support multiple `*args` groups.
   - What's unclear: Exact convention for separating friendly qarrays from king qarray from enemy qarrays in a single `*args`.
   - Recommendation: Use a count-based convention (factory knows how many friendly boards and how many enemy boards at construction time) or use the convention `(piece_qarray, *args)` where args layout is `[friendly_0, ..., friendly_n, king, enemy_0, ..., enemy_m, result]` with counts captured in the factory closure.

3. **Combined Predicate Qubit Budget for Simulation Tests**
   - What we know: Full combined predicate on 2x2 likely exceeds 17 qubits.
   - What's unclear: Exact ancilla count for the three-way AND + sub-predicate ancillas.
   - Recommendation: Test combined predicate with circuit-only builds for correctness of construction, and use the most minimal board setup possible for statevector verification. If needed, verify the AND composition separately from the sub-predicate calls.

## Sources

### Primary (HIGH confidence)
- `src/chess_predicates.py` - Existing predicate factories (piece-exists, no-friendly-capture) -- exact pattern to follow
- `src/chess_encoding.py` - `_KNIGHT_OFFSETS`, `_KING_OFFSETS`, `legal_moves_white()`, `legal_moves_black()` -- attack computation reference
- `tests/python/test_chess_predicates.py` - Existing test patterns, `make_small_board`, `_get_result_probability` helpers
- `src/quantum_language/qint_bitwise.pxi` - `__and__` operator implementation (Toffoli AND)
- `.planning/phases/115-check-detection-combined-predicate/115-CONTEXT.md` - Locked decisions

### Secondary (MEDIUM confidence)
- `.planning/phases/114-core-quantum-predicates/114-RESEARCH.md` - Prior phase research, established patterns
- `tests/python/conftest.py` - `clean_circuit` fixture

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All project-internal, no new dependencies
- Architecture: HIGH - Check detection mirrors proven no-friendly-capture pattern exactly
- Pitfalls: HIGH - Nested-with limitation confirmed in Phase 114, qubit budget arithmetic verified
- Combined predicate composition: MEDIUM - Nested compiled function calls need empirical validation

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable -- project-internal framework)
