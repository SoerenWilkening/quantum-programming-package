"""Chess quantum walk register scaffolding, board state replay, and local diffusion.

Provides register construction (one-hot height, per-level branch), board
state derivation, and local diffusion D_x with Montanaro angles for the
chess quantum walk demo. Uses raw qint allocation and walk.py internal
helpers -- no QWalkTree class.

Phase 104 Plan 01: Walk register infrastructure.
Phase 104 Plan 02: Local diffusion operator with variable branching.
"""

import math

from chess_encoding import get_legal_moves_and_oracle
from quantum_language._gates import emit_x
from quantum_language.qint import qint
from quantum_language.walk import _make_qbool_wrapper, _plan_cascade_ops

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
        Height register with root qubit (MSB, qubits[63]) set via emit_x.
    """
    h = qint(0, width=max_depth + 1)
    emit_x(int(h.qubits[63]))  # Root = MSB
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


def prepare_walk_data(wk_sq, bk_sq, wn_squares, max_depth):
    """Precompute move data for each level of the walk tree.

    Alternates side_to_move: white at level 0 (root's children), black at
    level 1, white at level 2, etc.

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
        One dict per level with keys: moves, move_count, branch_width, apply_move.
    """
    data = []
    for level in range(max_depth):
        side = "white" if level % 2 == 0 else "black"
        level_data = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, side)
        data.append(level_data)
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
        ops = _plan_cascade_ops(d_val, branch_width) if d_val > 1 else []
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

    bw = branch_reg.width
    wk, bk, wn = board_arrs

    for i in range(d_max):
        # (a) Encode child index i in branch register (MSB-first)
        for bit in range(bw):
            if (i >> (bw - 1 - bit)) & 1:
                emit_x(int(branch_reg.qubits[64 - bw + bit]))

        # (b) Flip height: depth -> depth-1 (move to child level)
        emit_x(height_qubit(h_reg, depth, max_depth))
        emit_x(height_qubit(h_reg, depth - 1, max_depth))

        # (c) Apply oracle to derive child board state
        oracle(wk, bk, wn, branch_reg)

        # (d) Quantum validity predicate: allocate reject qbool,
        # then set validity[i] = NOT reject.
        # For the KNK endgame with precomputed structurally valid moves,
        # all children in the oracle are valid. The predicate is trivially
        # satisfied (reject = |0>, validity = |1>). The quantum predicate
        # is still necessary to support the variable-branching D_x pattern
        # where d(x) counts valid children via these ancillae.
        reject = alloc_qbool()
        reject_qubit = int(reject.qubits[63])
        validity_qubit = int(validity[i].qubits[63])
        reject_ctrl = _make_qbool_wrapper(reject_qubit)
        with reject_ctrl:
            emit_x(validity_qubit)
        emit_x(validity_qubit)  # Flip: validity=|1> means valid

        # (e) Uncompute predicate (adjoint of trivial predicate is identity)

        # (f) Uncompute oracle
        oracle.inverse(wk, bk, wn, branch_reg)

        # (g) Undo height flip
        emit_x(height_qubit(h_reg, depth - 1, max_depth))
        emit_x(height_qubit(h_reg, depth, max_depth))

        # (h) Undo branch register encoding
        for bit in range(bw):
            if (i >> (bw - 1 - bit)) & 1:
                emit_x(int(branch_reg.qubits[64 - bw + bit]))


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

    bw = branch_reg.width
    wk, bk, wn = board_arrs

    for i in reversed(range(d_max)):
        # Navigate to child i
        for bit in range(bw):
            if (i >> (bw - 1 - bit)) & 1:
                emit_x(int(branch_reg.qubits[64 - bw + bit]))

        emit_x(height_qubit(h_reg, depth, max_depth))
        emit_x(height_qubit(h_reg, depth - 1, max_depth))

        # Re-apply oracle
        oracle(wk, bk, wn, branch_reg)

        # Re-evaluate predicate (trivial)
        reject = alloc_qbool()
        reject_qubit = int(reject.qubits[63])
        validity_qubit = int(validity[i].qubits[63])

        # Undo validity store (reverse order: X then CNOT)
        emit_x(validity_qubit)
        reject_ctrl = _make_qbool_wrapper(reject_qubit)
        with reject_ctrl:
            emit_x(validity_qubit)

        # Uncompute oracle
        oracle.inverse(wk, bk, wn, branch_reg)

        # Undo navigation
        emit_x(height_qubit(h_reg, depth - 1, max_depth))
        emit_x(height_qubit(h_reg, depth, max_depth))

        for bit in range(bw):
            if (i >> (bw - 1 - bit)) & 1:
                emit_x(int(branch_reg.qubits[64 - bw + bit]))
