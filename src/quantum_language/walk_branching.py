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

from .diffusion import _flip_all, _qubit_index
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


def _wrap_qbool(q):
    """Create a non-owning qbool wrapper for an existing qbool.

    Extracts the physical qubit index and creates a lightweight wrapper
    so that operations on the wrapper do not trigger uncomputation of
    the original qbool.

    Parameters
    ----------
    q : qbool
        Source qbool to wrap.

    Returns
    -------
    qbool
        Non-owning wrapper backed by the same physical qubit.
    """
    return _make_qbool_wrapper(_qubit_index(q))


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
# Multi-controlled gate helpers
# ------------------------------------------------------------------


def _multi_controlled_ry(target, angle, ctrls):
    """Apply Ry(angle) on target controlled by multiple qubits.

    Uses branch() for the rotation and & chains for multi-control.
    Negative angles (for inverse) are handled via X-Ry-X decomposition.

    Parameters
    ----------
    target : qbool
        Target qubit (qbool object).
    angle : float
        Ry rotation angle in radians.
    ctrls : list[qbool]
        Control qubits (qbool objects).
    """
    if abs(angle) < 1e-15:
        return

    prob = math.sin(angle / 2) ** 2
    inverse = angle < 0

    # Create a lightweight non-owning wrapper so branch() does not
    # trigger uncomputation of the caller's qbool.
    target_w = _wrap_qbool(target)

    if not ctrls:
        if inverse:
            _flip_all(target_w)
            target_w.branch(prob)
            _flip_all(target_w)
        else:
            target_w.branch(prob)
        return

    # Wrap controls as lightweight qbool views to avoid cascade
    # uncomputation of the caller's qbool objects.
    ctrl_wrappers = [_wrap_qbool(c) for c in ctrls]

    # Build combined control via & chain
    combined = ctrl_wrappers[0]
    for cw in ctrl_wrappers[1:]:
        combined = combined & cw

    with combined:
        if inverse:
            _flip_all(target_w)
            target_w.branch(prob)
            _flip_all(target_w)
        else:
            target_w.branch(prob)


def _multi_controlled_x(target, ctrls):
    """Apply X on target controlled by multiple qubits.

    Parameters
    ----------
    target : qbool
        Target qubit (qbool object).
    ctrls : list[qbool]
        Control qubits (qbool objects).
    """
    target_wrapper = _wrap_qbool(target)
    if not ctrls:
        _flip_all(target_wrapper)
        return
    ctrl_wrappers = [_wrap_qbool(c) for c in ctrls]
    if len(ctrl_wrappers) == 1:
        with ctrl_wrappers[0]:
            _flip_all(target_wrapper)
        return
    # Build combined qbool via & chain of all control qubits
    combined = ctrl_wrappers[0]
    for cw in ctrl_wrappers[1:]:
        combined = combined & cw
    with combined:
        _flip_all(target_wrapper)


# ------------------------------------------------------------------
# Cascade with multi-control
# ------------------------------------------------------------------


def _cascade_multi_controlled(branch_reg, ops, ctrls, sign=1):
    """Execute pre-planned cascade ops with additional control qubits.

    Uses qint bitwise indexing (branch_reg[i]) for cascade bit access.

    Parameters
    ----------
    branch_reg : qint
        Branch register to operate on.
    ops : list[tuple]
        Gate operations from ``_plan_cascade_ops``.
    ctrls : list[qbool]
        Control qubits (qbool objects).
    sign : int
        +1 for forward cascade, -1 for inverse (negates angles).
    """
    w = branch_reg.width
    if sign == -1:
        ops = list(reversed(ops))

    # Convert MSB-first bit_offset to LSB-first qint index.
    # Cascade uses 0=MSB, qint[i] uses 0=LSB.
    def _bit_qbool(bit_off):
        return branch_reg[w - 1 - bit_off]

    for op in ops:
        if op[0] == "ry":
            _, bit_off, angle = op
            target = _bit_qbool(bit_off)
            _multi_controlled_ry(target, sign * angle, ctrls)
        elif op[0] == "cry":
            _, bit_off, angle, ctrl_bit_off = op
            target = _bit_qbool(bit_off)
            cascade_ctrl = _bit_qbool(ctrl_bit_off)
            _multi_controlled_ry(
                target, sign * angle, ctrls + [cascade_ctrl]
            )
        elif op[0] == "x":
            _, bit_off = op
            target = _bit_qbool(bit_off)
            _multi_controlled_x(target, ctrls)
        elif op[0] == "cx":
            _, target_bit_off, ctrl_bit_off = op
            target = _bit_qbool(target_bit_off)
            cascade_ctrl = _bit_qbool(ctrl_bit_off)
            _multi_controlled_x(target, ctrls + [cascade_ctrl])


# ------------------------------------------------------------------
# BranchState: holds branching ancillae for correct inversion
# ------------------------------------------------------------------


class BranchState:
    """Holds the quantum ancillae created during branching.

    The multi-controlled rotations in the branching step create
    entanglement involving the comparison qubits.  For the inverse
    (unbranch) to undo this exactly, it must reuse the *same*
    physical comparison qubits.  This object carries them from
    ``branch_to_children`` to ``unbranch``.

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

    for c in range(1, num_moves + 1):
        ctrl_qbools = [cond_map[c]]
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]

        # Step 1: Parent-children split via Ry(phi) on parent-flag qubit.
        # The parent flag is a SEPARATE qubit from the branch register.
        # After Ry(phi), amplitude splits as:
        #   cos(phi/2) on |0> = 1/sqrt(c+1)  (parent)
        #   sin(phi/2) on |1> = sqrt(c)/sqrt(c+1)  (children)
        _multi_controlled_ry(parent_flag, phi, ctrl_qbools)

        # Step 2: Cascade to distribute amplitude uniformly among branch
        # register values 0..c-1.  The cascade is controlled only on the
        # count comparison (not on parent_flag).  Both the parent and
        # children components share the same branch register encoding;
        # the parent/child distinction lives on the parent_flag qubit.
        # This matches Montanaro's formulation where the cascade and
        # its inverse bracket the S_0 reflection.
        if c > 1 and cascade_ops:
            _cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qbools, sign=1,
            )

    return BranchState(parent_flag, cond_map)


def unbranch(config, count_reg, branch_reg, branch_state=None):
    """Inverse of :func:`branch_to_children`.

    Reverses the branching rotations, restoring the branch register to
    |0> and the parent-flag qubit to |0>.  Applied in reverse order of
    count values, with inverted rotation angles.

    The ``branch_state`` carries the comparison qbools and parent-flag
    from the forward pass.  The inverse **must** use the same physical
    comparison qubits because the multi-controlled rotations create
    entanglement involving those qubits.

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

    # Reverse order of count values for inverse
    for c in reversed(range(1, num_moves + 1)):
        ctrl_qbools = [cond_map[c]]
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]

        # Inverse cascade first (reverse of forward order),
        # controlled only on count comparison (matching forward pass).
        if c > 1 and cascade_ops:
            _cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qbools, sign=-1,
            )

        # Inverse phi rotation on parent-flag qubit
        _multi_controlled_ry(parent_flag, -phi, ctrl_qbools)


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
