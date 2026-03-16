"""Conditional branching for quantum walk: Montanaro rotations based on count.

Given a count register holding the number of valid children at the current
node, this module creates a uniform superposition over valid move indices in
a branch register.  The superposition includes a parent/self component for
probability backflow, as required by the Montanaro walk operator.

Algorithm
---------
For each possible count value ``c`` in ``1 .. num_moves``, conditioned on
``count_reg == c``:

1. Apply Ry(phi(c)) to a dedicated parent-flag qubit, splitting amplitude
   between the parent component (cos(phi/2) = 1/sqrt(c+1)) and the
   children component (sin(phi/2) = sqrt(c)/sqrt(c+1)).

2. Apply cascade rotations to distribute the children amplitude uniformly
   among ``c`` branch register values.  The cascade uses balanced binary
   splitting with angles theta_k(c) = 2*arcsin(sqrt(right_count/total))
   at each split.

After the call, the parent-flag qubit and branch register together encode
the superposition: parent flag |0> gives the parent/self component, and
parent flag |1> combined with branch register values 0..c-1 gives the
children components.  Invalid moves (indices >= c) receive zero amplitude.

``unbranch`` reverses the entire operation.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374), Section 2.
"""

import math

from ._gates import emit_ry
from .diffusion import _flip_all
from .walk_core import WalkConfig, montanaro_phi
from .qbool import qbool as new_qbool


# ------------------------------------------------------------------
# Internal: qbool wrapper for existing physical qubits
# ------------------------------------------------------------------


def _make_qbool_wrapper(qubit_idx):
    """Create a qbool wrapping an existing physical qubit (no allocation).

    Builds a proper 64-element numpy qubit array with the qubit at index 63
    (right-aligned, as expected by the gate emission infrastructure).
    """
    import numpy as np
    from .qbool import qbool

    arr = np.zeros(64, dtype=np.uint32)
    arr[63] = qubit_idx
    return qbool(create_new=False, bit_list=arr)


# ------------------------------------------------------------------
# Cascade planning (balanced binary splitting)
# ------------------------------------------------------------------


def _plan_cascade_ops(d, w):
    """Pre-compute gate operations for a d-way equal superposition cascade.

    Returns a list of gate operations in execution order.  Each is a tuple:
        ('ry', bit_offset, angle)
        ('cry', bit_offset, angle, ctrl_bit_offset)
        ('x', bit_offset)
        ('cx', target_bit_offset, ctrl_bit_offset)

    Bit offsets are relative to the branch register (0 = MSB).

    Parameters
    ----------
    d : int
        Number of states to superpose equally (>= 1).
    w : int
        Width of the branch register in qubits.

    Returns
    -------
    list[tuple]
        Gate operations in execution order.
    """
    if d <= 1:
        return []
    ops = []
    _plan_cascade_recursive(d, w, 0, ops, control_stack=[])
    return ops


def _plan_cascade_recursive(d, w, bit_offset, ops, control_stack):
    """Recursively build cascade operations via balanced binary splitting."""
    if d <= 1 or bit_offset >= w:
        return

    left_count = (d + 1) // 2
    right_count = d - left_count

    if right_count == 0:
        _plan_cascade_recursive(d, w, bit_offset + 1, ops, control_stack)
        return

    # Ry angle: sin^2(theta/2) = right_count / d
    theta = 2.0 * math.asin(math.sqrt(right_count / d))

    if not control_stack:
        ops.append(("ry", bit_offset, theta))
    elif len(control_stack) == 1:
        ctrl_bit, ctrl_on_zero = control_stack[0]
        if ctrl_on_zero:
            ops.append(("x", ctrl_bit))
        ops.append(("cry", bit_offset, theta, ctrl_bit))
        if ctrl_on_zero:
            ops.append(("x", ctrl_bit))
    elif len(control_stack) == 2:
        c0_bit, c0_on_zero = control_stack[0]
        c1_bit, c1_on_zero = control_stack[1]
        if c0_on_zero:
            ops.append(("x", c0_bit))
        if c1_on_zero:
            ops.append(("x", c1_bit))
        ops.append(("cry", bit_offset, theta / 2, c1_bit))
        ops.append(("cx", c1_bit, c0_bit))
        ops.append(("cry", bit_offset, -theta / 2, c1_bit))
        ops.append(("cx", c1_bit, c0_bit))
        ops.append(("cry", bit_offset, theta / 2, c0_bit))
        if c1_on_zero:
            ops.append(("x", c1_bit))
        if c0_on_zero:
            ops.append(("x", c0_bit))
    else:
        raise NotImplementedError(
            f"Cascade with {len(control_stack)} nested controls not supported "
            f"(d={d} requires deeper decomposition). Reduce branching degree."
        )

    # Left subtree: controlled on current bit = |0>
    if left_count > 1 and bit_offset + 1 < w:
        _plan_cascade_recursive(
            left_count, w, bit_offset + 1, ops,
            control_stack + [(bit_offset, True)],
        )

    # Right subtree: controlled on current bit = |1>
    if right_count > 1 and bit_offset + 1 < w:
        _plan_cascade_recursive(
            right_count, w, bit_offset + 1, ops,
            control_stack + [(bit_offset, False)],
        )


# ------------------------------------------------------------------
# Multi-controlled gate emission
# ------------------------------------------------------------------


def _emit_multi_controlled_ry(target_qubit, angle, ctrl_qubits):
    """Emit Ry(angle) on target controlled by multiple qubits.

    Handles 0, 1, 2+ controls via V-gate decomposition.
    """
    if abs(angle) < 1e-15:
        return

    if not ctrl_qubits:
        emit_ry(target_qubit, angle)
        return

    if len(ctrl_qubits) == 1:
        ctrl = _make_qbool_wrapper(ctrl_qubits[0])
        with ctrl:
            emit_ry(target_qubit, angle)
        return

    if len(ctrl_qubits) == 2:
        c0, c1 = ctrl_qubits
        c0_ctrl = _make_qbool_wrapper(c0)
        c1_ctrl = _make_qbool_wrapper(c1)
        with c1_ctrl:
            emit_ry(target_qubit, angle / 2)
        with c0_ctrl:
            _flip_all(c1_ctrl)
        with c1_ctrl:
            emit_ry(target_qubit, -angle / 2)
        with c0_ctrl:
            _flip_all(c1_ctrl)
        with c0_ctrl:
            emit_ry(target_qubit, angle / 2)
        return

    # 3+ controls: recursive V-gate decomposition
    primary = ctrl_qubits[-1]
    remaining = ctrl_qubits[:-1]
    p_ctrl = _make_qbool_wrapper(primary)
    with p_ctrl:
        emit_ry(target_qubit, angle / 2)
    _emit_multi_controlled_x(primary, remaining)
    with p_ctrl:
        emit_ry(target_qubit, -angle / 2)
    _emit_multi_controlled_x(primary, remaining)
    _emit_multi_controlled_ry(target_qubit, angle / 2, remaining)


def _emit_multi_controlled_x(target_qubit, ctrl_qubits):
    """Emit X on target controlled by multiple qubits."""
    target_wrapper = _make_qbool_wrapper(target_qubit)
    if not ctrl_qubits:
        _flip_all(target_wrapper)
        return
    if len(ctrl_qubits) == 1:
        ctrl = _make_qbool_wrapper(ctrl_qubits[0])
        with ctrl:
            _flip_all(target_wrapper)
        return
    from ._gates import emit_h, emit_mcz
    emit_h(target_qubit)
    emit_mcz(target_qubit, ctrl_qubits)
    emit_h(target_qubit)


# ------------------------------------------------------------------
# Cascade emission with multi-control
# ------------------------------------------------------------------


def _emit_cascade_multi_controlled(branch_reg, ops, ctrl_qubits, sign=1):
    """Execute pre-planned cascade ops with additional control qubits.

    Parameters
    ----------
    branch_reg : qint
        Branch register to operate on.
    ops : list[tuple]
        Gate operations from ``_plan_cascade_ops``.
    ctrl_qubits : list[int]
        Physical qubit indices for additional controls.
    sign : int
        +1 for forward cascade, -1 for inverse (negates angles).
    """
    w = branch_reg.width
    if sign == -1:
        ops = list(reversed(ops))

    for op in ops:
        if op[0] == "ry":
            _, bit_off, angle = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            _emit_multi_controlled_ry(qubit, sign * angle, ctrl_qubits)
        elif op[0] == "cry":
            _, bit_off, angle, ctrl_bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            cascade_ctrl = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            _emit_multi_controlled_ry(
                qubit, sign * angle, ctrl_qubits + [cascade_ctrl]
            )
        elif op[0] == "x":
            _, bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            _emit_multi_controlled_x(qubit, ctrl_qubits)
        elif op[0] == "cx":
            _, target_bit_off, ctrl_bit_off = op
            target_q = int(branch_reg.qubits[64 - w + target_bit_off])
            cascade_ctrl = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            _emit_multi_controlled_x(
                target_q, ctrl_qubits + [cascade_ctrl]
            )


# ------------------------------------------------------------------
# BranchState: holds branching ancillae for correct inversion
# ------------------------------------------------------------------


class BranchState:
    """Holds the quantum ancillae created during branching.

    The multi-controlled rotations in the branching step create
    entanglement via V-gate decomposition involving the comparison
    qubits.  For the inverse (unbranch) to undo this exactly, it
    must reuse the *same* physical comparison qubits.  This object
    carries them from ``branch_to_children`` to ``unbranch``.

    Attributes
    ----------
    parent_flag : qbool
        Dedicated parent-flag qubit.
    cond_map : dict
        Maps count value c -> qbool comparison result (count_reg == c).
    """

    __slots__ = ("parent_flag", "cond_map")

    def __init__(self, parent_flag, cond_map):
        self.parent_flag = parent_flag
        self.cond_map = cond_map


# ------------------------------------------------------------------
# Public API: branch_to_children / unbranch
# ------------------------------------------------------------------


def branch_to_children(config, count_reg, branch_reg, parent_flag=None):
    """Create uniform superposition over valid move indices in branch register.

    Given ``count_reg`` holding the number of valid children (computed by
    :func:`~walk_counting.count_valid_children`), this function applies
    conditional Montanaro rotations to produce:

    - For each count value ``c`` (1 .. num_moves), conditioned on
      ``count_reg == c``:

      1. Ry(phi(c)) on a dedicated parent-flag qubit, splitting
         amplitude 1/sqrt(c+1) to parent and sqrt(c)/sqrt(c+1) to children.

      2. Cascade rotations on the branch register to distribute the children
         amplitude uniformly among values 0 .. c-1.

    After the call, the parent-flag qubit encodes whether we stay at the
    parent (|0>) or descend to a child (|1>), and the branch register
    holds the child index.  For d valid children, the parent component
    has amplitude 1/sqrt(d+1).

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``num_moves``.
    count_reg : qint
        Count register holding the number of valid children.
    branch_reg : qint
        Branch register (initially |0>) to receive the superposition.
    parent_flag : qbool, optional
        Dedicated parent-flag qubit.  If None, one is allocated
        automatically.

    Returns
    -------
    BranchState
        Object holding the parent-flag qubit and comparison ancillae.
        Must be passed to :func:`unbranch` for correct inversion.

    Raises
    ------
    TypeError
        If ``config`` is not a ``WalkConfig``.
    ValueError
        If ``count_reg`` or ``branch_reg`` is None.
    """
    _validate_branching_args(config, count_reg, branch_reg)

    num_moves = config.num_moves
    bw = branch_reg.width

    # Allocate parent-flag qubit if not provided
    if parent_flag is None:
        parent_flag = new_qbool()

    # Pre-compute angles and cascade ops for each possible count value
    angle_data = _precompute_angle_data(num_moves, bw)

    # Compute all count comparisons up front AND keep the qbool objects
    # alive.  The framework's automatic uncomputation reverses comparison
    # gates when a qbool goes out of scope, so we must retain references
    # to all comparison results until after the controlled rotations.
    # The comparison qbools are also returned in the BranchState so that
    # unbranch can reuse the same physical qubits.
    cond_map = {}
    for c in range(1, num_moves + 1):
        cond_map[c] = (count_reg == c)

    parent_qubit = int(parent_flag.qubits[63])

    for c in range(1, num_moves + 1):
        cond_qubit = int(cond_map[c].qubits[63])
        ctrl_qubits = [cond_qubit]
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]

        # Step 1: Parent-children split via Ry(phi) on parent-flag qubit.
        # The parent flag is a SEPARATE qubit from the branch register.
        # After Ry(phi), amplitude splits as:
        #   cos(phi/2) on |0> = 1/sqrt(c+1)  (parent)
        #   sin(phi/2) on |1> = sqrt(c)/sqrt(c+1)  (children)
        _emit_multi_controlled_ry(parent_qubit, phi, ctrl_qubits)

        # Step 2: Cascade to distribute amplitude uniformly among branch
        # register values 0..c-1.  The cascade is controlled only on the
        # count comparison (not on parent_flag).  Both the parent and
        # children components share the same branch register encoding;
        # the parent/child distinction lives on the parent_flag qubit.
        # This matches Montanaro's formulation where the cascade and
        # its inverse bracket the S_0 reflection.
        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=1,
            )

    return BranchState(parent_flag, cond_map)


def unbranch(config, count_reg, branch_reg, branch_state=None):
    """Inverse of :func:`branch_to_children`.

    Reverses the branching rotations, restoring the branch register to
    |0> and the parent-flag qubit to |0>.  Applied in reverse order of
    count values, with inverted rotation angles.

    The ``branch_state`` carries the comparison qbools and parent-flag
    from the forward pass.  The inverse **must** use the same physical
    comparison qubits because the multi-controlled V-gate decomposition
    creates entanglement involving those qubits.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``num_moves``.
    count_reg : qint
        Count register holding the number of valid children.
    branch_reg : qint
        Branch register to restore to |0>.
    branch_state : BranchState
        State returned by :func:`branch_to_children`, carrying the
        parent-flag qubit and comparison ancillae.

    Raises
    ------
    ValueError
        If ``branch_state`` is None.
    """
    _validate_branching_args(config, count_reg, branch_reg)
    if branch_state is None:
        raise ValueError("branch_state must not be None for unbranch")

    parent_flag = branch_state.parent_flag
    cond_map = branch_state.cond_map

    num_moves = config.num_moves
    bw = branch_reg.width

    angle_data = _precompute_angle_data(num_moves, bw)

    parent_qubit = int(parent_flag.qubits[63])

    # Reverse order of count values for inverse
    for c in reversed(range(1, num_moves + 1)):
        cond_qubit = int(cond_map[c].qubits[63])
        ctrl_qubits = [cond_qubit]
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]

        # Inverse cascade first (reverse of forward order),
        # controlled only on count comparison (matching forward pass).
        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=-1,
            )

        # Inverse phi rotation on parent-flag qubit
        _emit_multi_controlled_ry(parent_qubit, -phi, ctrl_qubits)


# ------------------------------------------------------------------
# Pre-computation helpers
# ------------------------------------------------------------------


def _precompute_angle_data(num_moves, bw):
    """Pre-compute Montanaro angles and cascade ops for all count values.

    Parameters
    ----------
    num_moves : int
        Maximum number of moves.
    bw : int
        Branch register width in qubits.

    Returns
    -------
    dict
        Maps count value c -> {"phi": float, "cascade_ops": list}.
    """
    data = {}
    for c in range(1, num_moves + 1):
        phi = montanaro_phi(c)
        cascade_ops = _plan_cascade_ops(c, bw)
        data[c] = {"phi": phi, "cascade_ops": cascade_ops}
    return data


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def _validate_branching_args(config, count_reg, branch_reg):
    """Validate arguments for branch_to_children / unbranch.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.
    count_reg : qint
        Count register.
    branch_reg : qint
        Branch register.

    Raises
    ------
    TypeError
        If ``config`` is not a ``WalkConfig``.
    ValueError
        If ``count_reg`` or ``branch_reg`` is None.
    """
    if not isinstance(config, WalkConfig):
        raise TypeError(
            f"config must be a WalkConfig, got {type(config).__name__}"
        )
    if count_reg is None:
        raise ValueError("count_reg must not be None")
    if branch_reg is None:
        raise ValueError("branch_reg must not be None")
