"""Local diffusion operator for quantum walk.

D_x = U * S_0 * U_dagger, where U = Montanaro rotations on
parent_flag + branch register, S_0 = phase flip on |0...0>.

Fixed-branching path: d known classically, direct rotations, D^2 = I exact.
Variable-branching path: evaluates validity, counts, conditional rotations.
Root node uses phi_root = 2 * arctan(sqrt(n * d)).

Reference: Montanaro, "Quantum speedup of backtracking algorithms", 2018.
"""

from ._gates import emit_mcz, emit_ry, emit_x, emit_z
from .diffusion import _collect_qubits
from .walk_branching import (
    _emit_cascade_multi_controlled,
    _emit_multi_controlled_ry,
    _plan_cascade_ops,
)
from .walk_core import (
    WalkConfig,
    branch_width,
    count_width,
    montanaro_phi,
    root_angle,
)


# ------------------------------------------------------------------
# S_0 reflection on parent_flag + branch register
# ------------------------------------------------------------------


def _s0_reflection(parent_flag, branch_reg):
    """Phase flip on |0...0> of parent_flag + branch_reg (X-MCZ-X)."""
    s0_qubits = _collect_qubits(parent_flag, branch_reg)

    if not s0_qubits:
        return

    # X on all qubits (map |0...0> -> |1...1>)
    for q in s0_qubits:
        emit_x(q)

    # MCZ: phase flip on |1...1>
    if len(s0_qubits) == 1:
        emit_z(s0_qubits[0])
    else:
        emit_mcz(s0_qubits[-1], s0_qubits[:-1])

    # X on all qubits (undo the mapping)
    for q in s0_qubits:
        emit_x(q)


# ------------------------------------------------------------------
# Pre-compute angles and cascade ops
# ------------------------------------------------------------------


def _precompute_angles(num_moves, bw, is_root=False, max_depth=1):
    """Montanaro angles and cascade ops for c = 1 .. num_moves."""
    data = {}
    for c in range(1, num_moves + 1):
        if is_root:
            phi = root_angle(c, max_depth)
        else:
            phi = montanaro_phi(c)
        cascade_ops = _plan_cascade_ops(c, bw)
        data[c] = {"phi": phi, "cascade_ops": cascade_ops}
    return data


# ------------------------------------------------------------------
# Fixed-branching diffusion (no predicates, D^2 = I exact)
# ------------------------------------------------------------------


def _fixed_diffusion(d, parent_flag, branch_reg, angle_data):
    """Fixed-branching D_x = U S_0 U_dagger.  No ancilla, D^2 = I exact."""
    if d < 1:
        return  # No valid children -> identity

    phi = angle_data[d]["phi"]
    cascade_ops = angle_data[d]["cascade_ops"]
    parent_qubit = int(parent_flag.qubits[63])

    # Step A: U_dagger (inverse state preparation)
    # First undo cascade, then undo phi rotation
    if d > 1 and cascade_ops:
        _emit_cascade_multi_controlled(
            branch_reg, cascade_ops, [], sign=-1,
        )
    emit_ry(parent_qubit, -phi)

    # Step B: S_0 reflection
    _s0_reflection(parent_flag, branch_reg)

    # Step C: U forward (state preparation)
    # First phi rotation, then cascade
    emit_ry(parent_qubit, phi)
    if d > 1 and cascade_ops:
        _emit_cascade_multi_controlled(
            branch_reg, cascade_ops, [], sign=1,
        )


# ------------------------------------------------------------------
# Variable-branching diffusion (with predicates)
# ------------------------------------------------------------------


def _evaluate_validity(config):
    """Apply-check-undo loop: return list of validity qbools per move."""
    state = config.state
    make_move = config.make_move
    is_valid = config.is_valid
    num_moves = config.num_moves

    undo = config.undo_move
    if undo is None:
        undo = config.make_move.adjoint

    validity = []
    for i in range(num_moves):
        make_move(state, i)
        v = is_valid(state)
        validity.append(v)
        undo(state, i)

    return validity


def _variable_diffusion(config, parent_flag, branch_reg, angle_data,
                        is_root=False):
    """Variable-branching diffusion: count -> conditional rotations -> S_0."""
    import quantum_language as ql

    num_moves = config.num_moves

    # Step 1: Evaluate validity for all children
    validity = _evaluate_validity(config)

    # Step 2: Sum validity bits into count register.
    # Use controlled increment (``with v: count += 1``) instead of
    # ``count += v`` to avoid a framework bug where ``__iadd__`` /
    # ``__isub__`` with comparison-derived qbools produces garbage
    # qubit indices.
    cw = count_width(num_moves)
    count = ql.qint(0, width=cw)
    for v in validity:
        with v:
            count += 1

    # Step 3: Compute count comparisons and extract raw qubit indices.
    # Store only the physical qubit index (int), not the live qbool,
    # matching the pattern in the old counting_diffusion_core.
    cond_qubits_map = {}
    for c in range(1, num_moves + 1):
        if c in angle_data:
            cond = (count == c)
            cond_qubits_map[c] = int(cond.qubits[63])

    parent_qubit = int(parent_flag.qubits[63])

    # Step 4: U_dagger (inverse state preparation)
    for c in range(1, num_moves + 1):
        if c not in angle_data:
            continue
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]
        ctrl_qubits = [cond_qubits_map[c]]

        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=-1,
            )
        _emit_multi_controlled_ry(parent_qubit, -phi, ctrl_qubits)

    # Step 5: S_0 reflection
    _s0_reflection(parent_flag, branch_reg)

    # Step 6: U forward (state preparation)
    for c in range(1, num_moves + 1):
        if c not in angle_data:
            continue
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]
        ctrl_qubits = [cond_qubits_map[c]]

        _emit_multi_controlled_ry(parent_qubit, phi, ctrl_qubits)
        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=1,
            )

    # Step 7: Uncompute count register (reverse controlled decrement)
    for v in reversed(validity):
        with v:
            count -= 1


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def walk_diffusion(state, make_move, is_valid, num_moves,
                   undo_move=None, max_depth=1, is_root=False):
    """Local diffusion operator at the current depth.

    Combines counting and branching into a single reflection operator
    that satisfies D^2 = I.  This is the public building block for
    constructing walk operators (R_A, R_B) or custom quantum walks.

    The diffusion operates on the user's ``state`` register using the
    provided ``make_move`` and ``is_valid`` callbacks.  Framework-
    internal registers (parent_flag, branch) are allocated automatically.

    Parameters
    ----------
    state : qint or qarray
        Quantum register representing the problem state.
    make_move : callable
        Function ``make_move(state, move_index)`` that transforms the
        state by applying a classical move index.  Should be decorated
        with ``@ql.compile(inverse=True)`` if no explicit ``undo_move``
        is provided.
    is_valid : callable
        Quantum predicate ``is_valid(state)`` returning ``qbool``.
    num_moves : int
        Maximum number of moves (branching factor) at any node.
    undo_move : callable, optional
        Explicit inverse of ``make_move``.  If not provided, the
        counting module falls back to ``make_move.adjoint``.
    max_depth : int, optional
        Tree depth (used for root angle computation).  Default is 1.
    is_root : bool, optional
        If True, use the root angle formula for the parent-children
        split.  Default is False.

    Raises
    ------
    TypeError
        If ``num_moves`` is not an int.
    ValueError
        If ``num_moves`` < 1, or if required callbacks are None.
    """
    _validate_args(state, make_move, is_valid, num_moves)

    import quantum_language as ql
    from .qbool import qbool as new_qbool

    # Build WalkConfig
    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        make_move=make_move,
        undo_move=undo_move,
        is_valid=is_valid,
        state=state,
    )

    # Allocate framework-internal registers
    bw = branch_width(num_moves)
    parent_flag = new_qbool()
    branch_reg = ql.qint(0, width=bw)

    # Pre-compute angles
    angles = _precompute_angles(
        num_moves, bw,
        is_root=is_root,
        max_depth=max_depth,
    )

    # Apply the variable-branching diffusion
    _variable_diffusion(config, parent_flag, branch_reg, angles,
                        is_root=is_root)


def walk_diffusion_fixed(parent_flag, branch_reg, num_moves,
                         max_depth=1, is_root=False):
    """Fixed-branching diffusion (no predicates, D^2 = I exact).

    Applies the Montanaro diffusion assuming all ``num_moves`` children
    are valid.  Uses direct rotations on the parent_flag and branch
    register with no ancilla allocation.  Satisfies D^2 = I at full
    statevector level.

    This is the building block used by walk operators (R_A, R_B) at
    nodes where the branching factor is fixed.

    Parameters
    ----------
    parent_flag : qbool
        Parent-flag qubit.
    branch_reg : qint
        Branch register.
    num_moves : int
        Number of valid children (branching factor).
    max_depth : int, optional
        Tree depth (for root angle formula).  Default is 1.
    is_root : bool, optional
        If True, use root angle formula.  Default is False.
    """
    if not isinstance(num_moves, int):
        raise TypeError(
            f"num_moves must be an int, got {type(num_moves).__name__}"
        )
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")

    bw = branch_reg.width
    angles = _precompute_angles(
        num_moves, bw,
        is_root=is_root,
        max_depth=max_depth,
    )
    _fixed_diffusion(num_moves, parent_flag, branch_reg, angles)


# ------------------------------------------------------------------
# Low-level API: diffusion with pre-allocated registers
# ------------------------------------------------------------------


def walk_diffusion_with_regs(config, parent_flag, branch_reg, is_root=False):
    """Local diffusion using pre-allocated registers.

    Like :func:`walk_diffusion` but takes a ``WalkConfig`` and
    pre-allocated parent_flag/branch registers.  Uses variable-
    branching diffusion with validity evaluation.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with state, make_move, is_valid, num_moves.
    parent_flag : qbool
        Pre-allocated parent-flag qubit.
    branch_reg : qint
        Pre-allocated branch register (initially zero).
    is_root : bool
        If True, use root angle formula.
    """
    _validate_config(config)

    num_moves = config.num_moves
    bw = branch_reg.width

    angles = _precompute_angles(
        num_moves, bw,
        is_root=is_root,
        max_depth=config.max_depth,
    )

    _variable_diffusion(config, parent_flag, branch_reg, angles,
                        is_root=is_root)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def _validate_args(state, make_move, is_valid, num_moves):
    """Validate arguments for walk_diffusion."""
    if state is None:
        raise ValueError("state must not be None")
    if make_move is None:
        raise ValueError("make_move must not be None")
    if is_valid is None:
        raise ValueError("is_valid must not be None")
    if not isinstance(num_moves, int):
        raise TypeError(
            f"num_moves must be an int, got {type(num_moves).__name__}"
        )
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")


def _validate_config(config):
    """Validate a WalkConfig for diffusion."""
    if not isinstance(config, WalkConfig):
        raise TypeError(
            f"config must be a WalkConfig, got {type(config).__name__}"
        )
    if config.state is None:
        raise ValueError("config.state must not be None")
    if config.make_move is None:
        raise ValueError("config.make_move must not be None")
    if config.is_valid is None:
        raise ValueError("config.is_valid must not be None")
