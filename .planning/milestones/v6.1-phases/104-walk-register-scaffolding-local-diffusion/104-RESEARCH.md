# Phase 104: Walk Register Scaffolding & Local Diffusion - Research

**Researched:** 2026-03-03
**Domain:** Quantum walk register construction, Montanaro local diffusion, chess move replay
**Confidence:** HIGH

## Summary

Phase 104 implements the quantum walk register infrastructure (one-hot height register, per-level branch registers) and a single local diffusion operator D_x from raw primitives -- without using the existing QWalkTree class. The critical complexity is that D_x must derive board state at each tree node by sequentially replaying move oracles from the starting position through branch registers, then compute d(x) (branching factor) from the derived position to select correct Montanaro diffusion angles.

The project already has a complete reference implementation in `walk.py` (QWalkTree class with _variable_diffusion) and a working move oracle factory in `chess_encoding.py`. Phase 104 reuses walk.py internal helpers (_plan_cascade_ops, _emit_cascade_ops, _emit_multi_controlled_ry) and chess_encoding's compiled move oracle with .inverse support, composing them into a new purely functional module `src/chess_walk.py`.

**Primary recommendation:** Follow walk.py's _variable_diffusion pattern closely for the diffusion operator, adapting it to use chess-specific move replay for validity determination instead of the generic predicate interface. Keep the implementation compact and functional as specified.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sequential replay: apply move oracle level-by-level from starting position through branch registers 0..d-1
- Mux-style dispatch for move selection: build a multiplexer that reads the branch register value and applies the corresponding move (not one oracle per move with quantum conditionals)
- Inverse replay for uncomputation: use .inverse property of each compiled move oracle in reverse order (LIFO) to uncompute derived board state after diffusion
- Plain Python emitter (not a compiled function): a regular function that calls individual compiled oracles in sequence, giving transparency and easier debugging; manual inverse by calling in reverse
- Quantum d(x) computation: determine branching factor from the quantum board state at runtime, not precomputed classically
- Predicate-driven approach (walk.py _variable_diffusion style): evaluate each child's validity via validity qubits, then apply conditional Ry cascade rotations
- Purpose-built quantum predicate: write a new predicate that checks move legality directly from the board qarray state (does not call chess_encoding.legal_moves() classically)
- Exact Montanaro angles: phi = 2*arctan(sqrt(d)) for internal nodes, special root formula -- same formulas from Montanaro 2015 as implemented in walk.py
- Reuse walk.py internal helpers: import _plan_cascade_ops, _emit_cascade_ops, _emit_cascade_h_controlled directly -- "manual" means no QWalkTree class, not no helper reuse
- Keep helpers private: no API changes to walk.py (no renaming to public)
- Use public ql.diffusion() for S_0 reflection -- demonstrates framework usage
- Raw qint allocation for registers: directly call qint(0, width=...) for height and branch registers, no wrapper helpers
- New src/chess_walk.py module alongside chess_encoding.py
- Purely functional style (no class): functions like create_height_register(), create_branch_registers(), derive_board_state(), apply_diffusion()
- New tests/python/test_chess_walk.py for walk-specific tests
- Component testing only: test each function in isolation within 17-qubit budget (height register init, single move replay, single diffusion step) -- no tiny-board integration tests
- Keep quantum implementation as compact as possible for a better overview -- minimize boilerplate, favor concise circuit construction

### Claude's Discretion
- Mux dispatch implementation details (controlled-swap vs conditional oracle activation)
- Validity qubit allocation strategy for predicate evaluation
- Exact function signatures and parameter ordering
- Which walk.py helpers to import vs which to inline
- Test case selection for component verification

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WALK-01 | One-hot height register (max_depth+1 qubits) from raw qint with root initialization | Height register pattern from QWalkTree.__init__ (line 538-554 of walk.py): qint(0, width=max_depth+1) + emit_x on root qubit. Root qubit is qubits[63] (MSB, right-aligned). |
| WALK-02 | Per-level branch registers encoding chosen move index from legal move list | Branch register allocation from QWalkTree.__init__ (line 542-548): one qint per depth level, width = ceil(log2(d)). White max ~32 moves = 5-bit, black max 8 = 3-bit. chess_encoding.get_legal_moves_and_oracle() returns branch_width. |
| WALK-03 | Single local diffusion D_x with Montanaro angles (phi = 2*arctan(sqrt(d))) | Full reference in walk.py _variable_diffusion (lines 771-886): validity qubit allocation, child evaluation, conditional U_dagger * S_0 * U per d(x) value, uncomputation. Reusable helpers: _plan_cascade_ops, _emit_cascade_ops, _emit_multi_controlled_ry. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (ql) | internal | Circuit construction, qint/qbool/qarray types | Project's own framework -- all quantum operations go through this |
| chess_encoding | internal | Move generation, compiled move oracle factory | Phase 103 output -- provides get_legal_moves_and_oracle() |
| walk.py internals | internal | Cascade planning, multi-controlled Ry, height-controlled emission | Proven helpers from v6.0 -- reuse as-is via private imports |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >= 1.24 | Array manipulation for qubit index arrays | Used by _make_qbool_wrapper for 64-element qubit arrays |
| math | stdlib | arctan, sqrt, ceil, log2 for angle computation | Montanaro angle formulas |

### Import Map
```python
# From quantum_language
import quantum_language as ql
from quantum_language.qint import qint
from quantum_language.qbool import qbool
from quantum_language._gates import emit_ry, emit_x
from quantum_language.diffusion import diffusion  # Public S_0 reflection

# From walk.py (private helpers, no API change)
from quantum_language.walk import (
    _plan_cascade_ops,
    _emit_cascade_ops,
    _emit_cascade_multi_controlled,
    _emit_multi_controlled_ry,
    _make_qbool_wrapper,
)

# From chess_encoding (Phase 103)
from chess_encoding import (
    encode_position,
    get_legal_moves_and_oracle,
    legal_moves,
    legal_moves_white,
    legal_moves_black,
)
```

## Architecture Patterns

### Recommended Project Structure
```
src/
    chess_encoding.py    # Phase 103 -- move generation + oracle factory
    chess_walk.py        # Phase 104 -- NEW: walk registers + diffusion (purely functional)
    quantum_language/
        walk.py          # Existing QWalkTree + private helpers (unchanged)
        diffusion.py     # Public ql.diffusion() for S_0 reflection
tests/python/
    test_chess.py        # Phase 103 tests (existing)
    test_chess_walk.py   # Phase 104 tests -- NEW
    conftest.py          # Existing: clean_circuit fixture
```

### Pattern 1: Height Register Initialization
**What:** Create one-hot height register with root qubit set to |1>
**When to use:** At walk register construction time
**Example:**
```python
# Source: walk.py QWalkTree.__init__ lines 538-554
def create_height_register(max_depth):
    """Create one-hot height register with root initialized to |1>."""
    h = qint(0, width=max_depth + 1)
    # Root qubit is at qubits[63] (MSB, right-aligned in 64-element array)
    root_qubit = int(h.qubits[63])
    emit_x(root_qubit)
    return h
```

### Pattern 2: Branch Register Allocation
**What:** Create per-level branch registers with width derived from move count
**When to use:** After computing legal moves at each depth level
**Example:**
```python
# Source: walk.py QWalkTree.__init__ lines 542-548 + chess_encoding
def create_branch_registers(max_depth, move_data_per_level):
    """Create branch registers from precomputed move data per level."""
    registers = []
    for level_idx in range(max_depth):
        width = move_data_per_level[level_idx]["branch_width"]
        registers.append(qint(0, width=width))
    return registers
```

### Pattern 3: Sequential Board State Replay (Mux Dispatch)
**What:** Derive board position at depth d by applying move oracles level-by-level from root
**When to use:** Before diffusion to determine d(x) at the current node
**Example:**
```python
# Source: chess_encoding _make_apply_move + CONTEXT.md mux-style dispatch decision
def derive_board_state(board, branch_registers, oracle_per_level, depth):
    """Apply move oracles 0..depth-1 to derive board state at depth."""
    for level_idx in range(depth):
        oracle = oracle_per_level[level_idx]
        oracle(board["white_king"], board["black_king"],
               board["white_knights"], branch_registers[level_idx])

def underive_board_state(board, branch_registers, oracle_per_level, depth):
    """Uncompute: apply oracle inverses in reverse (LIFO)."""
    for level_idx in reversed(range(depth)):
        oracle = oracle_per_level[level_idx]
        oracle.inverse(board["white_king"], board["black_king"],
                       board["white_knights"], branch_registers[level_idx])
```

### Pattern 4: Variable Diffusion with Validity Qubits
**What:** Evaluate move legality per child, then apply conditional Ry cascade based on d(x)
**When to use:** For the local diffusion D_x at a specific depth
**Example (structural pattern from walk.py _variable_diffusion):**
```python
# Source: walk.py _variable_diffusion lines 771-886
# Structure:
# 1. Allocate validity ancillae (one per potential child)
# 2. For each child i: navigate to child, evaluate validity, store, undo
# 3. Conditional U_dagger * S_0 * U for each possible d(x) value
# 4. Uncompute validity (reverse of step 2)

# The chess adaptation replaces the generic "predicate" with:
# - derive_board_state() to get position at current node
# - chess-specific validity check on derived board state
# - underive_board_state() to restore original state
```

### Pattern 5: Height Qubit Addressing
**What:** Extract physical qubit index for a specific depth from height register
**When to use:** For height-controlled gates in diffusion
**Example:**
```python
# Source: walk.py QWalkTree._height_qubit lines 704-721
def height_qubit(h_register, depth, max_depth):
    """Get physical qubit index for height register at given depth."""
    width = max_depth + 1
    return int(h_register.qubits[64 - width + depth])
```

### Anti-Patterns to Avoid
- **Using QWalkTree class:** The whole point is manual construction from raw primitives + helpers
- **Classical d(x) precomputation:** d(x) must be determined from quantum board state at runtime
- **Nested `with qbool:` contexts:** Framework limitation -- use V-gate decomposition via _emit_multi_controlled_ry instead
- **Calling chess_encoding.legal_moves() inside quantum context:** Classical function cannot be used at runtime; need quantum predicate for validity
- **Single-qubit conditional per move:** Use mux-style dispatch (branch == i pattern) not individual controlled gates

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cascade Ry for d-way superposition | Custom rotation tree | `_plan_cascade_ops(d, w)` + `_emit_cascade_ops()` | Balanced binary splitting with V-gate CCRy decomposition already handles arbitrary d and w |
| Multi-controlled Ry | Manual control decomposition | `_emit_multi_controlled_ry(target, angle, ctrls)` | V-gate recursive decomposition for 2+ controls already implemented |
| S_0 reflection (zero-state phase flip) | Custom X-MCZ-X pattern | `ql.diffusion(*registers)` | Public API, handles arbitrary register types, correct MCZ emission |
| qbool wrapping existing physical qubit | Manual numpy array construction | `_make_qbool_wrapper(qubit_idx)` | Correct 64-element array with right-alignment at index 63 |
| Height-controlled cascade | Nested with-blocks | `_emit_cascade_h_controlled(branch_reg, ops, h_qubit_idx, sign)` | Decomposes CCRy via V-gate pattern, avoids forbidden nested control |
| Multi-controlled cascade | Nested with-blocks | `_emit_cascade_multi_controlled(branch_reg, ops, ctrl_qubits, sign)` | Handles variable number of control qubits with correct decomposition |
| Compiled move oracle | Raw gate sequence | `chess_encoding.get_legal_moves_and_oracle()` | Returns @ql.compile(inverse=True) function with .inverse support |

**Key insight:** walk.py's internal helpers are battle-tested through v6.0's QWalkTree. Reusing them eliminates bugs in the complex multi-controlled rotation decomposition, which is notoriously easy to get wrong when hand-rolled.

## Common Pitfalls

### Pitfall 1: Qubit Array Right-Alignment
**What goes wrong:** Accessing wrong physical qubit from qint register
**Why it happens:** qint stores qubits in a 64-element numpy array, right-aligned. A 5-bit register uses indices 59-63, not 0-4. MSB is at `qubits[64 - width]`, LSB at `qubits[63]`.
**How to avoid:** Always use `int(reg.qubits[64 - width + bit_offset])` pattern from walk.py
**Warning signs:** Gate operates on qubit 0 when it should be on a higher-numbered qubit

### Pitfall 2: Root Qubit is MSB (qubits[63])
**What goes wrong:** Initializing wrong qubit as root
**Why it happens:** One-hot height register uses MSB (bit position max_depth, stored at qubits[63]) for root, not LSB
**How to avoid:** Follow walk.py convention: `emit_x(int(h.qubits[63]))` for root initialization
**Warning signs:** Walk starts at leaf instead of root

### Pitfall 3: Depth vs Level Index Confusion
**What goes wrong:** Using wrong angle or wrong branch register for a depth
**Why it happens:** walk.py uses `level_idx = max_depth - depth`. Root is at depth=max_depth, level_idx=0. Leaves are at depth=0, level_idx=max_depth.
**How to avoid:** Document the mapping clearly. Root = depth max_depth = level_idx 0. Branch register `[level_idx]` corresponds to `depth = max_depth - level_idx`.
**Warning signs:** Angles computed for wrong branching degree

### Pitfall 4: Oracle .inverse Requires Prior Forward Call
**What goes wrong:** Calling `.inverse` without a matching forward call
**Why it happens:** The _AncillaInverseProxy tracks which forward call to undo. Without a forward call, the inverse has nothing to match.
**How to avoid:** Always call forward oracle before calling `.inverse`. The derive/underive pattern ensures this: derive calls forward, underive calls inverse in reverse order.
**Warning signs:** Runtime error from compile infrastructure about missing forward call

### Pitfall 5: Nested `with qbool:` Context Forbidden
**What goes wrong:** Trying to nest two quantum-conditional blocks
**Why it happens:** Framework limitation: `with qbool:` cannot nest (quantum-quantum AND not supported)
**How to avoid:** Use V-gate decomposition via _emit_multi_controlled_ry for multi-controlled gates. Never write `with cond1: with cond2:`.
**Warning signs:** Framework error about unsupported nested control

### Pitfall 6: 17-Qubit Simulation Budget
**What goes wrong:** Creating test circuits that exceed simulation capacity
**Why it happens:** Full chess board is 192+ qubits (3 * 64 qbools). Even a height register + one branch register + partial board exceeds 17 qubits quickly.
**How to avoid:** Component testing only -- test height register init (4-5 qubits), single move replay (tiny board), single diffusion step (tiny). No end-to-end walk simulation.
**Warning signs:** Tests hang or crash with memory errors

### Pitfall 7: Side-to-Move Alternation
**What goes wrong:** Using same player's moves at every depth level
**Why it happens:** Forgetting that chess alternates: white at even depths, black at odd depths (or vice versa depending on who moves first)
**How to avoid:** Move oracle per level must alternate between white and black move sets. Branch register widths differ: white max ~5 bits, black max ~3 bits.
**Warning signs:** Branch register width uniform across all levels when it should alternate

### Pitfall 8: Validity Qubit Combinatorial Explosion
**What goes wrong:** O(2^d_max) pattern combinations in conditional diffusion
**Why it happens:** _variable_diffusion iterates over all `C(d_max, d_val)` combinations. For d_max = 32 (white's max moves), this is astronomically expensive.
**How to avoid:** This is a real architectural concern. For the chess demo, the circuit is only generated (not simulated). The gate count will be enormous but that's acceptable for circuit-generation-only mode. For testing, use positions with very few legal moves (2-4).
**Warning signs:** Circuit generation takes minutes or hangs for realistic positions

## Code Examples

### Height Register Creation (Verified from walk.py)
```python
# Source: walk.py QWalkTree.__init__ lines 538-554
from quantum_language.qint import qint
from quantum_language._gates import emit_x

def create_height_register(max_depth):
    h = qint(0, width=max_depth + 1)
    root_qubit = int(h.qubits[63])  # MSB = root
    emit_x(root_qubit)
    return h
```

### Montanaro Angle Computation (Verified from walk.py _setup_diffusion)
```python
# Source: walk.py _setup_diffusion lines 607-680
import math

def montanaro_phi(d):
    """Parent-children split angle: phi = 2*arctan(sqrt(d))."""
    return 2.0 * math.atan(math.sqrt(d))

def montanaro_root_phi(d_root, max_depth):
    """Root angle: phi_root = 2*arctan(sqrt(n*d_root))."""
    return 2.0 * math.atan(math.sqrt(max_depth * d_root))

# For variable branching, precompute for each possible d value (1..d_max):
# variable_angles[d] = {"phi": montanaro_phi(d), "cascade_ops": _plan_cascade_ops(d, w)}
```

### Variable Diffusion D_x Structure (Verified from walk.py _variable_diffusion)
```python
# Source: walk.py _variable_diffusion lines 771-886
# Adapted pseudocode for chess_walk:

def apply_diffusion(depth, h_reg, branch_regs, board, oracle_per_level,
                    d_max, max_depth):
    """Apply local diffusion D_x at given depth.

    Steps:
    1. Derive board state at current node (replay oracles 0..depth-1)
    2. Allocate validity ancillae
    3. Evaluate each child's legality from derived board state
    4. Conditional U_dagger * S_0 * U per d(x) value
    5. Uncompute validity
    6. Underive board state (inverse replay)
    """
    # Step 1: derive board state
    derive_board_state(board, branch_regs, oracle_per_level, depth)

    # Step 2: allocate validity qubits
    validity = [qbool() for _ in range(d_max)]

    # Step 3: evaluate children
    # For each child i (0..d_max-1):
    #   - Set branch_regs[level_idx] to i (X gates on appropriate bits)
    #   - Apply oracle at current level to get child's board state
    #   - Check validity (is the move legal from derived board?)
    #   - Store in validity[i]
    #   - Uncompute oracle at current level
    #   - Reset branch register
    evaluate_children(depth, d_max, validity, ...)

    # Step 4: conditional diffusion (follows walk.py exactly)
    # For each d_val in 1..d_max:
    #   For each C(d_max, d_val) bit pattern:
    #     - Flip zero validity qubits
    #     - Multi-controlled U_dagger (inverse cascade + inverse parent Ry)
    #     - Undo X flips
    # S_0 reflection (ql.diffusion on local subspace)
    # Repeat for U forward

    # Step 5: uncompute validity
    uncompute_children(depth, d_max, validity, ...)

    # Step 6: underive board state
    underive_board_state(board, branch_regs, oracle_per_level, depth)
```

### Move Oracle Mux Dispatch (Verified from chess_encoding)
```python
# Source: chess_encoding.py _make_apply_move lines 358-432
# The compiled oracle already performs mux-style dispatch internally:
# For each move index i, condition on (branch == i), flip source/dest qubits.
# No additional mux needed -- just call the oracle with the branch register.

# derive_board_state simply calls each level's oracle in sequence:
def derive_board_state(board, branch_regs, oracle_per_level, depth):
    for level_idx in range(depth):
        oracle = oracle_per_level[level_idx]
        oracle(board["white_king"], board["black_king"],
               board["white_knights"], branch_regs[level_idx])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Uniform branching (fixed d) | Variable branching (_variable_diffusion) | Phase 100 (v6.0) | Angles depend on runtime d(x), not compile-time d |
| Generic predicate callback | Chess-specific board state validity | Phase 104 (now) | Predicate evaluates from derived quantum board state |
| QWalkTree class | Raw functional primitives | Phase 104 (now) | Educational demo, no class encapsulation |

**Deprecated/outdated:**
- QWalkTree's local_diffusion() is the high-level API; Phase 104 builds the same logic from lower-level pieces

## Open Questions

1. **Validity predicate design**
   - What we know: Must check move legality from quantum board state (qarray). Cannot call classical legal_moves().
   - What's unclear: The exact quantum predicate implementation -- checking if a destination square is occupied by a friendly piece or attacked by the opponent requires reading qarray state.
   - Recommendation: For KNK endgame, the validity check can be simpler: check that the destination square is not occupied by a friendly piece. Since the move list is precomputed classically, only moves to non-attacked squares are included. The quantum predicate just needs to verify the specific destination square in the qarray is available. This can use a simple `with board[rank, file]:` conditional to flip a validity qubit.

2. **Board state for validity at depth d**
   - What we know: Board state at depth d is derived by replaying d oracles. After deriving, we can inspect qarrays.
   - What's unclear: Since oracle applications are quantum (conditioned on branch register superposition), the board state at depth d is in superposition. The validity predicate must operate on this superposition.
   - Recommendation: The validity check IS the predicate evaluation from _variable_diffusion. Each child is evaluated by: (a) set branch to child index classically (X gates), (b) apply oracle to get deterministic child state, (c) check validity, (d) store, (e) undo. This makes each evaluation classical-like (specific branch value, not superposition) during the evaluation loop.

3. **Test circuit sizing**
   - What we know: 17-qubit max, full board = 192+ qubits, component testing only.
   - What's unclear: What's the most useful component test within budget?
   - Recommendation: (a) Height register init: 4 qubits (max_depth=3), can simulate. (b) Branch register allocation: trivially testable. (c) Single oracle call: needs tiny board -- impractical with qarrays (64 qbools per board). Focus on circuit-generation tests (no simulation) for larger components, simulation only for tiny register tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/python/conftest.py (clean_circuit fixture) |
| Quick run command | `pytest tests/python/test_chess_walk.py -v -x` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WALK-01 | Height register creation with root init | unit | `pytest tests/python/test_chess_walk.py::TestHeightRegister -x` | Wave 0 |
| WALK-02 | Branch register allocation per level | unit | `pytest tests/python/test_chess_walk.py::TestBranchRegisters -x` | Wave 0 |
| WALK-03 | Local diffusion D_x with correct angles | unit (circuit gen) | `pytest tests/python/test_chess_walk.py::TestDiffusion -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_chess_walk.py -v -x`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/python/test_chess_walk.py` -- covers WALK-01, WALK-02, WALK-03
- [ ] No new conftest fixtures needed -- `clean_circuit` from existing conftest.py suffices

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/walk.py` -- QWalkTree, _plan_cascade_ops, _emit_cascade_ops, _variable_diffusion, _evaluate_children, _uncompute_children (complete reference implementation)
- `src/chess_encoding.py` -- encode_position, get_legal_moves_and_oracle, _make_apply_move (Phase 103 oracle)
- `src/quantum_language/diffusion.py` -- ql.diffusion() S_0 reflection implementation
- `src/quantum_language/__init__.py` -- public API surface
- `src/quantum_language/_gates.pxd` -- available gate primitives (h, z, ry, ch, cz, cry, mcz, p, cp)

### Secondary (MEDIUM confidence)
- `tests/python/test_chess.py` -- test patterns, clean_circuit fixture usage
- `tests/python/conftest.py` -- fixture definitions

### Tertiary (LOW confidence)
- None -- all findings verified from codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries and helpers verified in existing codebase
- Architecture: HIGH -- follows proven _variable_diffusion pattern from walk.py with chess-specific adaptations
- Pitfalls: HIGH -- identified from actual codebase patterns (qubit addressing, nesting, budget)

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable internal codebase, no external dependency changes)
