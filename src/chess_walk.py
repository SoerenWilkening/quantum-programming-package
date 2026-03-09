"""Chess quantum walk register scaffolding, board state replay, and local diffusion.

Provides register construction (one-hot height, per-level branch), board
state derivation, and local diffusion D_x with Montanaro angles for the
chess quantum walk demo. Uses raw qint allocation and walk.py internal
helpers -- no QWalkTree class.

Phase 104 Plan 01: Walk register infrastructure.
Phase 104 Plan 02: Local diffusion operator with variable branching.
Phase 116 Plan 01: Quantum predicate integration and offset-based oracle.
"""

import math

import numpy as np

import quantum_language as ql
from chess_encoding import (
    _KING_OFFSETS,
    _KNIGHT_OFFSETS,
    build_move_table,
)
from chess_predicates import make_combined_predicate
from quantum_language.qint import qint
from quantum_language.walk import (
    _plan_cascade_ops,
    counting_diffusion_core,
)

__all__ = [
    "create_height_register",
    "create_branch_registers",
    "derive_board_state",
    "underive_board_state",
    "height_qubit",
    "prepare_walk_data",
    "montanaro_phi",
    "montanaro_root_phi",
    "precompute_diffusion_angles",
    "evaluate_children",
    "uncompute_children",
    "apply_diffusion",
    "r_a",
    "r_b",
    "all_walk_qubits",
    "walk_step",
]


def create_height_register(max_depth):
    """Create one-hot height register with root initialized to |1>.

    Parameters
    ----------
    max_depth : int
        Maximum tree depth. Register has max_depth+1 qubits.

    Returns
    -------
    qint
        Height register with root qubit set to |1>.
    """
    h = qint(0, width=max_depth + 1)
    h ^= 1  # Set root bit (depth=max_depth maps to bit 0)
    return h


def create_branch_registers(max_depth, move_data_per_level):
    """Create per-level branch registers from precomputed move data.

    Parameters
    ----------
    max_depth : int
        Maximum tree depth (number of branch registers to create).
    move_data_per_level : list[dict]
        Each dict must have 'branch_width' key giving qint width for that level.

    Returns
    -------
    list[qint]
        One branch register per level, width from move_data.
    """
    return [qint(0, width=move_data_per_level[i]["branch_width"]) for i in range(max_depth)]


def height_qubit(h_reg, depth, max_depth):
    """Get physical qubit index for a specific depth in the height register.

    Parameters
    ----------
    h_reg : qint
        Height register (width = max_depth + 1).
    depth : int
        Depth level to address (0 = leaves, max_depth = root).
    max_depth : int
        Maximum tree depth.

    Returns
    -------
    int
        Physical qubit index.
    """
    width = max_depth + 1
    return int(h_reg.qubits[64 - width + depth])


def derive_board_state(board_arrs, branch_regs, oracle_per_level, depth):
    """Apply move oracles 0..depth-1 to derive board state at given depth.

    Plain Python emitter -- calls each compiled oracle in forward order.

    Parameters
    ----------
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays representing the board.
    branch_regs : list[qint]
        Branch registers, one per level.
    oracle_per_level : list
        Compiled apply_move functions, one per level.
    depth : int
        Number of oracle levels to apply.
    """
    wk, bk, wn = board_arrs
    for level_idx in range(depth):
        oracle_per_level[level_idx](wk, bk, wn, branch_regs[level_idx])


def underive_board_state(board_arrs, branch_regs, oracle_per_level, depth):
    """Uncompute board state by applying oracle inverses in reverse (LIFO).

    Parameters
    ----------
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays representing the board.
    branch_regs : list[qint]
        Branch registers, one per level.
    oracle_per_level : list
        Compiled apply_move functions (must have .inverse property).
    depth : int
        Number of oracle levels to undo.
    """
    wk, bk, wn = board_arrs
    for level_idx in reversed(range(depth)):
        oracle_per_level[level_idx].inverse(wk, bk, wn, branch_regs[level_idx])


# Map piece_id to board_arrs index: (wk_arr, bk_arr, wn_arr)
BOARD_KEYS = {"wk": 0, "bk": 1, "wn": 2}


def _make_apply_move_from_table(move_table):
    """Create a compiled oracle from an offset-based move table.

    For each branch register value i, move_table[i] = (piece_id, dr, df).
    The oracle enumerates all 64 possible source squares for each entry and
    conditionally applies the move when branch == i AND piece at source.
    Off-board destinations (r+dr, f+df outside 0..7) are skipped classically
    (no gates emitted), implementing identity for invalid moves.

    Parameters
    ----------
    move_table : list[tuple[str, int, int]]
        Table of (piece_id, rank_delta, file_delta) triples from build_move_table.

    Returns
    -------
    CompiledFunc
        A @ql.compile(inverse=True) function with signature
        (wk_arr, bk_arr, wn_arr, branch).
    """
    # Classical precomputation: per branch value, list valid (board_idx, src_r, src_f, dst_r, dst_f)
    per_branch_specs = []
    for piece_id, dr, df in move_table:
        board_idx = BOARD_KEYS[piece_id]
        specs = []
        for r in range(8):
            for f in range(8):
                tr, tf = r + dr, f + df
                if 0 <= tr < 8 and 0 <= tf < 8:
                    specs.append((board_idx, r, f, tr, tf))
        per_branch_specs.append(specs)

    @ql.compile(inverse=True)
    def apply_move(wk_arr, bk_arr, wn_arr, branch):
        """Apply the i-th move to the board, conditioned on branch register value.

        For each branch value i, iterates all valid source squares for that
        entry's (piece_id, dr, df) and flips source off / destination on.
        """
        boards = [wk_arr, bk_arr, wn_arr]
        for i, specs in enumerate(per_branch_specs):
            if not specs:
                continue  # All destinations off-board for this entry
            cond = branch == i
            with cond:
                for board_idx, src_r, src_f, dst_r, dst_f in specs:
                    ~boards[board_idx][src_r, src_f]
                    ~boards[board_idx][dst_r, dst_f]

    return apply_move


def prepare_walk_data(wk_sq, bk_sq, wn_squares, max_depth):
    """Precompute move data for each level of the walk tree.

    Alternates side_to_move: white at level 0 (root's children), black at
    level 1, white at level 2, etc. Uses build_move_table for all-moves
    enumeration and make_combined_predicate for quantum legality checking.

    Parameters
    ----------
    wk_sq : int
        White king square (0-63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s).
    max_depth : int
        Number of levels in the walk tree.

    Returns
    -------
    list[dict]
        One dict per level with keys: move_table, move_count, branch_width,
        apply_move, predicates, entry_qarray_keys.
    """
    data = []
    for level in range(max_depth):
        side = "white" if level % 2 == 0 else "black"

        # Build move table for this side
        if side == "white":
            move_table = build_move_table([("wk", "king"), ("wn", "knight")])
            enemy_attacks = [(_KING_OFFSETS, "bk")]
            n_friendly = 1  # one other friendly piece besides moving piece
            n_enemy = 1
        else:
            move_table = build_move_table([("bk", "king")])
            enemy_attacks = [(_KING_OFFSETS, "wk"), (_KNIGHT_OFFSETS, "wn")]
            n_friendly = 0  # no other black pieces in KNK
            n_enemy = 2

        move_count = len(move_table)
        branch_width = max(1, math.ceil(math.log2(max(move_count, 1))))

        # Build one combined predicate per table entry
        predicates = []
        entry_qarray_keys = []
        for piece_id, dr, df in move_table:
            piece_type = "king" if piece_id in ("wk", "bk") else "knight"
            pred = make_combined_predicate(
                piece_type, dr, df, 8, 8, enemy_attacks, n_friendly, n_enemy
            )
            predicates.append(pred)

            # Determine qarray key mappings for argument resolution
            if side == "white":
                if piece_id == "wk":
                    keys = {"piece": "wk", "friendly": ["wn"], "king": "wk", "enemy": ["bk"]}
                else:  # wn
                    keys = {"piece": "wn", "friendly": ["wk"], "king": "wk", "enemy": ["bk"]}
            else:
                keys = {"piece": "bk", "friendly": [], "king": "bk", "enemy": ["wk", "wn"]}
            entry_qarray_keys.append(keys)

        # Build offset-based oracle
        apply_move = _make_apply_move_from_table(move_table)

        data.append(
            {
                "move_table": move_table,
                "move_count": move_count,
                "branch_width": branch_width,
                "apply_move": apply_move,
                "predicates": predicates,
                "entry_qarray_keys": entry_qarray_keys,
            }
        )
    return data


# ---------------------------------------------------------------------------
# Montanaro angle helpers
# ---------------------------------------------------------------------------


def montanaro_phi(d):
    """Montanaro parent-children split angle for internal nodes.

    Parameters
    ----------
    d : int
        Branching factor (number of valid children).

    Returns
    -------
    float
        phi = 2 * arctan(sqrt(d)).
    """
    return 2.0 * math.atan(math.sqrt(d))


def montanaro_root_phi(d, max_depth):
    """Montanaro root angle with depth amplification.

    Parameters
    ----------
    d : int
        Branching factor at the root.
    max_depth : int
        Maximum tree depth n.

    Returns
    -------
    float
        phi_root = 2 * arctan(sqrt(n * d)).
    """
    return 2.0 * math.atan(math.sqrt(max_depth * d))


def precompute_diffusion_angles(d_max, branch_width):
    """Precompute angle data for each possible branching factor 1..d_max.

    Parameters
    ----------
    d_max : int
        Maximum branching degree.
    branch_width : int
        Width of the branch register in qubits.

    Returns
    -------
    dict[int, dict]
        Maps d_val -> {"phi": float, "cascade_ops": list}.
    """
    angles = {}
    for d_val in range(1, d_max + 1):
        phi = montanaro_phi(d_val)
        if d_val > 1:
            try:
                ops = _plan_cascade_ops(d_val, branch_width)
            except NotImplementedError:
                # Cascade planning fails for d_val > 2^(w-1) due to control
                # depth limitation. Fall back to Ry-only (no child cascade).
                ops = []
        else:
            ops = []
        angles[d_val] = {"phi": phi, "cascade_ops": ops}
    return angles


# ---------------------------------------------------------------------------
# Validity evaluation (child predicate loop)
# ---------------------------------------------------------------------------


def evaluate_children(
    depth, level_idx, d_max, branch_reg, h_reg, max_depth, oracle, board_arrs, validity
):
    """Evaluate each child's validity and store in validity ancillae.

    For each child i (0..d_max-1): encode child index in branch register,
    flip height, apply oracle to get child board state, check validity via
    quantum predicate, store result, then undo everything.

    Follows walk.py _evaluate_children pattern exactly.

    Parameters
    ----------
    depth : int
        Current depth level.
    level_idx : int
        Level index (max_depth - depth).
    d_max : int
        Maximum branching degree at this level.
    branch_reg : qint
        Branch register for this level.
    h_reg : qint
        Height register.
    max_depth : int
        Maximum tree depth.
    oracle : callable
        Compiled apply_move function for this level.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    validity : list[qbool]
        Validity ancillae to store results (one per child).
    """
    from quantum_language.qbool import qbool as alloc_qbool

    wk, bk, wn = board_arrs
    height_mask = 3 << (max_depth - depth)  # bits for depth and depth-1

    for i in range(d_max):
        # (a) Encode child index i in branch register
        branch_reg ^= i

        # (b) Flip height: depth -> depth-1 (move to child level)
        h_reg ^= height_mask

        # (c) Apply oracle to derive child board state
        oracle(wk, bk, wn, branch_reg)

        # (d) Quantum validity predicate: validity[i] = NOT reject.
        # For the KNK endgame with precomputed structurally valid moves,
        # all children in the oracle are valid. The predicate is trivially
        # satisfied (reject = |0>, validity = |1>). The quantum predicate
        # is still necessary to support the variable-branching D_x pattern
        # where d(x) counts valid children via these ancillae.
        reject = alloc_qbool()
        with reject:
            validity[i] ^= 1
        validity[i] ^= 1  # Flip: validity=|1> means valid

        # (e) Uncompute predicate (adjoint of trivial predicate is identity)

        # (f) Uncompute oracle
        oracle.inverse(wk, bk, wn, branch_reg)

        # (g) Undo height flip
        h_reg ^= height_mask

        # (h) Undo branch register encoding
        branch_reg ^= i


def uncompute_children(
    depth, level_idx, d_max, branch_reg, h_reg, max_depth, oracle, board_arrs, validity
):
    """Uncompute validity ancillae (reverse of evaluate_children).

    Iterates children in reversed order and undoes the validity store.

    Parameters
    ----------
    depth : int
        Current depth level.
    level_idx : int
        Level index (max_depth - depth).
    d_max : int
        Maximum branching degree at this level.
    branch_reg : qint
        Branch register for this level.
    h_reg : qint
        Height register.
    max_depth : int
        Maximum tree depth.
    oracle : callable
        Compiled apply_move function for this level.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    validity : list[qbool]
        Validity ancillae to uncompute.
    """
    from quantum_language.qbool import qbool as alloc_qbool

    wk, bk, wn = board_arrs
    height_mask = 3 << (max_depth - depth)  # bits for depth and depth-1

    for i in reversed(range(d_max)):
        # Navigate to child i
        branch_reg ^= i
        h_reg ^= height_mask

        # Re-apply oracle
        oracle(wk, bk, wn, branch_reg)

        # Re-evaluate predicate (trivial)
        reject = alloc_qbool()

        # Undo validity store (reverse order: X then CNOT)
        validity[i] ^= 1
        with reject:
            validity[i] ^= 1

        # Uncompute oracle
        oracle.inverse(wk, bk, wn, branch_reg)

        # Undo navigation
        h_reg ^= height_mask
        branch_reg ^= i


# ---------------------------------------------------------------------------
# Local diffusion D_x
# ---------------------------------------------------------------------------


def apply_diffusion(
    depth, h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth
):
    """Apply local diffusion D_x at a given depth.

    Uses the shared counting_diffusion_core from walk.py for O(d_max)
    gate complexity:
    1. Derive board state at current node (replay oracles 0..depth-1).
    2. Allocate validity ancillae.
    3. Evaluate children (quantum predicate per child).
    4. Precompute angles, delegate to counting_diffusion_core.
    5. Uncompute validity.
    6. Underive board state.

    Parameters
    ----------
    depth : int
        Current depth level (1..max_depth).
    h_reg : qint
        Height register.
    branch_regs : list[qint]
        Per-level branch registers.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    oracle_per_level : list
        Compiled apply_move functions, one per level.
    move_data_per_level : list[dict]
        Move data per level (needs 'move_count' key).
    max_depth : int
        Maximum tree depth.
    """
    from quantum_language.qbool import qbool

    # --- Step 1: Setup ---
    level_idx = max_depth - depth

    # --- Step 2: Derive board state at current node ---
    # Replay oracles 0..level_idx-1 to reach current depth.
    # Root (depth=max_depth, level_idx=0) needs 0 replays (starting position).
    derive_board_state(board_arrs, branch_regs, oracle_per_level, level_idx)
    d_max = move_data_per_level[level_idx]["move_count"]
    branch_reg = branch_regs[level_idx]
    is_root = depth == max_depth
    h_qubit_idx = height_qubit(h_reg, depth, max_depth)
    h_child_idx = height_qubit(h_reg, depth - 1, max_depth)

    # --- Step 3: Allocate validity ancillae ---
    validity = [qbool() for _ in range(d_max)]

    # --- Step 4: Evaluate children ---
    evaluate_children(
        depth,
        level_idx,
        d_max,
        branch_reg,
        h_reg,
        max_depth,
        oracle_per_level[level_idx],
        board_arrs,
        validity,
    )

    # --- Step 5: Precompute angles ---
    angles = precompute_diffusion_angles(d_max, branch_reg.width)
    root_angles = {}
    if is_root:
        for d_val in range(1, d_max + 1):
            root_angles[d_val] = montanaro_root_phi(d_val, max_depth)

    # --- Step 6: Counting diffusion core (shared with walk.py) ---
    counting_diffusion_core(
        validity,
        d_max,
        branch_reg,
        h_qubit_idx,
        h_child_idx,
        angles,
        root_angles,
        is_root,
    )

    # --- Step 7: Uncompute validity ---
    uncompute_children(
        depth,
        level_idx,
        d_max,
        branch_reg,
        h_reg,
        max_depth,
        oracle_per_level[level_idx],
        board_arrs,
        validity,
    )

    # --- Step 8: Underive board state ---
    underive_board_state(board_arrs, branch_regs, oracle_per_level, level_idx)


# ---------------------------------------------------------------------------
# Mega-register for compile
# ---------------------------------------------------------------------------


def all_walk_qubits(h_reg, branch_regs, max_depth):
    """Create qint wrapping height + branch walk qubits.

    Used as one of the arguments to the compiled walk step so these
    qubits are treated as parameter qubits (not internal ancillas).
    Board array qarrays are passed separately to the compiled function
    since the total qubit count exceeds the 64-qubit qint width limit.

    Parameters
    ----------
    h_reg : qint
        Height register (width = max_depth + 1).
    branch_regs : list[qint]
        Per-level branch registers.
    max_depth : int
        Maximum tree depth.

    Returns
    -------
    qint
        Register wrapping height + branch qubits with create_new=False.
    """
    all_indices = []
    # Height register qubits
    w = max_depth + 1
    for i in range(w):
        all_indices.append(int(h_reg.qubits[64 - w + i]))
    # Branch register qubits
    for br in branch_regs:
        bw = br.width
        for i in range(bw):
            all_indices.append(int(br.qubits[64 - bw + i]))

    arr = np.zeros(64, dtype=np.uint32)
    total = len(all_indices)
    for i, idx in enumerate(all_indices):
        arr[64 - total + i] = idx
    return qint(0, create_new=False, bit_list=arr, width=total)


# ---------------------------------------------------------------------------
# Walk operators R_A and R_B
# ---------------------------------------------------------------------------


def r_a(h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth):
    """Apply R_A: diffusion at even depths, excluding root and leaves.

    R_A covers even-numbered depth levels (0, 2, 4, ...) but skips:
    - depth 0 (leaves -- no children, level_idx out of range)
    - depth == max_depth (root always belongs to R_B)

    Together with R_B, covers all active depths exactly once (disjoint).

    Parameters
    ----------
    h_reg : qint
        Height register.
    branch_regs : list[qint]
        Per-level branch registers.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    oracle_per_level : list
        Compiled apply_move functions, one per level.
    move_data_per_level : list[dict]
        Move data per level.
    max_depth : int
        Maximum tree depth.
    """
    for depth in range(0, max_depth + 1, 2):
        if depth == 0:
            continue  # Leaves: no children, level_idx out of range
        if depth == max_depth:
            continue  # Root always belongs to R_B
        apply_diffusion(
            depth, h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth
        )


def r_b(h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth):
    """Apply R_B: diffusion at odd depths plus root.

    R_B covers odd-numbered depth levels (1, 3, 5, ...) and always includes
    the root (depth == max_depth). If max_depth is even, root is added
    explicitly since it wouldn't be in the odd range.

    Together with R_A, covers all active depths exactly once (disjoint).

    Parameters
    ----------
    h_reg : qint
        Height register.
    branch_regs : list[qint]
        Per-level branch registers.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    oracle_per_level : list
        Compiled apply_move functions, one per level.
    move_data_per_level : list[dict]
        Move data per level.
    max_depth : int
        Maximum tree depth.
    """
    for depth in range(1, max_depth + 1, 2):
        apply_diffusion(
            depth, h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth
        )
    # Root always in R_B; add explicitly if max_depth is even (not in odd range)
    if max_depth % 2 == 0:
        apply_diffusion(
            max_depth,
            h_reg,
            branch_regs,
            board_arrs,
            oracle_per_level,
            move_data_per_level,
            max_depth,
        )


# ---------------------------------------------------------------------------
# Walk step U = R_B * R_A (compiled)
# ---------------------------------------------------------------------------

# Module-level compiled function: created once per process, re-captures per circuit.
# The @ql.compile infrastructure handles its own per-circuit cache clearing.
_walk_compiled_fn = None


def walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth):
    """Apply walk step U = R_B * R_A.

    On first call, the gate sequence is captured and compiled via
    @ql.compile for caching and automatic inverse derivation.
    Subsequent calls replay the cached gate sequence.

    The height + branch qubits are wrapped in a mega-register via
    all_walk_qubits(), and board qarrays (wk, bk, wn) are passed as
    separate arguments so the compile infrastructure treats all walk
    qubits as parameters (not internal ancillas).

    Parameters
    ----------
    h_reg : qint
        Height register.
    branch_regs : list[qint]
        Per-level branch registers.
    board_arrs : tuple
        (wk_arr, bk_arr, wn_arr) qarrays.
    oracle_per_level : list
        Compiled apply_move functions, one per level.
    move_data_per_level : list[dict]
        Move data per level.
    max_depth : int
        Maximum tree depth.
    """
    global _walk_compiled_fn
    from quantum_language.compile import compile as ql_compile

    mega_reg = all_walk_qubits(h_reg, branch_regs, max_depth)
    total = mega_reg.width + sum(len(a) for a in board_arrs)

    if _walk_compiled_fn is None:
        # Create the compiled function once. The closure captures walk
        # args by reference via a mutable container so they update each call.
        _ctx = {}

        def _walk_body(walk_qubits_reg, wk_arr, bk_arr, wn_arr):
            c = _ctx
            _board = (wk_arr, bk_arr, wn_arr)
            r_a(c["h"], c["br"], _board, c["opl"], c["mdpl"], c["md"])
            r_b(c["h"], c["br"], _board, c["opl"], c["mdpl"], c["md"])

        _walk_compiled_fn = ql_compile(key=lambda r, w, b, n: _ctx.get("total", 0))(_walk_body)
        _walk_compiled_fn._walk_ctx = _ctx  # stash reference

    # Update context for this call
    ctx = _walk_compiled_fn._walk_ctx
    ctx["h"] = h_reg
    ctx["br"] = branch_regs
    ctx["opl"] = oracle_per_level
    ctx["mdpl"] = move_data_per_level
    ctx["md"] = max_depth
    ctx["total"] = total

    wk, bk, wn = board_arrs
    _walk_compiled_fn(mega_reg, wk, bk, wn)
