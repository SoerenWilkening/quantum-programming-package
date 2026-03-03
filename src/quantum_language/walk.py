"""Quantum backtracking tree encoding (Montanaro 2015).

Provides QWalkTree for encoding backtracking search trees into quantum registers.
The tree uses a one-hot height register (max_depth+1 qubits) and per-level branch
registers. Local diffusion operators, walk operators, and detection are built on
top of this encoding in later modules.

Variable branching (Phase 100) extends the diffusion to support trees where
different nodes have different numbers of valid children, determined dynamically
by predicate evaluation at each node.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

import itertools
import math

import numpy as np

from ._gates import emit_ry, emit_x
from .qint import qint


def _make_qbool_wrapper(qubit_idx):
    """Create a qbool wrapping an existing physical qubit (no allocation).

    Builds a proper 64-element numpy qubit array with the qubit at index 63
    (right-aligned, as expected by the gate emission infrastructure).

    Parameters
    ----------
    qubit_idx : int
        Physical qubit index to wrap.

    Returns
    -------
    qbool
        A qbool backed by the existing qubit.
    """
    from .qbool import qbool

    arr = np.zeros(64, dtype=np.uint32)
    arr[63] = qubit_idx
    return qbool(create_new=False, bit_list=arr)


def _plan_cascade_ops(d, w):
    """Pre-compute the gate operations for a d-way equal superposition cascade.

    Returns a list of gate operations in execution order. Each operation is
    a tuple of one of:
        ('ry', bit_offset, angle)         -- unconditional Ry
        ('cry', bit_offset, angle, ctrl_bit_offset)  -- singly-controlled Ry
        ('x', bit_offset)                 -- unconditional X

    The operations use bit offsets (0=MSB) relative to the branch register.
    They are designed to be executed sequentially with at most one level of
    ``with qbool:`` control (no nesting).

    Parameters
    ----------
    d : int
        Number of states to superpose equally.
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
    _plan_cascade_ops_recursive(d, w, 0, ops, control_stack=[])
    return ops


def _plan_cascade_ops_recursive(d, w, bit_offset, ops, control_stack):
    """Recursively build gate operation list for cascade.

    Uses balanced binary splitting. For each split, emits the rotation
    and schedules child operations with the appropriate control context.

    Multi-qubit controls (depth > 1) are decomposed into sequences of
    singly-controlled and unconditional gates using V-gate decomposition.
    """
    if d <= 1 or bit_offset >= w:
        return

    left_count = (d + 1) // 2
    right_count = d - left_count

    if right_count == 0:
        _plan_cascade_ops_recursive(d, w, bit_offset + 1, ops, control_stack)
        return

    # Ry angle: sin^2(theta/2) = right_count/d
    theta = 2.0 * math.asin(math.sqrt(right_count / d))

    if not control_stack:
        # No control: simple Ry
        ops.append(("ry", bit_offset, theta))
    elif len(control_stack) == 1:
        # Single control: CRy
        ctrl_bit, ctrl_on_zero = control_stack[0]
        if ctrl_on_zero:
            ops.append(("x", ctrl_bit))
        ops.append(("cry", bit_offset, theta, ctrl_bit))
        if ctrl_on_zero:
            ops.append(("x", ctrl_bit))
    else:
        # Multi-control: decompose CCRy into CRy + CNOT sequence
        # For 2 controls: CCRy(theta) = CRy(theta/2, c1) CNOT(c0,c1) CRy(-theta/2, c1) CNOT(c0,c1) CRy(theta/2, c0)
        # For simplicity, handle up to 2 controls; beyond that, raise error
        if len(control_stack) == 2:
            c0_bit, c0_on_zero = control_stack[0]
            c1_bit, c1_on_zero = control_stack[1]

            # Prepare controls (flip for on-zero conditions)
            if c0_on_zero:
                ops.append(("x", c0_bit))
            if c1_on_zero:
                ops.append(("x", c1_bit))

            # Decompose CCRy(theta) using the V-gate pattern:
            # CRy(theta/2, c1, target), CNOT(c0, c1), CRy(-theta/2, c1, target),
            # CNOT(c0, c1), CRy(theta/2, c0, target)
            ops.append(("cry", bit_offset, theta / 2, c1_bit))
            ops.append(("cx", c1_bit, c0_bit))  # CNOT(c0 -> c1)
            ops.append(("cry", bit_offset, -theta / 2, c1_bit))
            ops.append(("cx", c1_bit, c0_bit))  # CNOT(c0 -> c1)
            ops.append(("cry", bit_offset, theta / 2, c0_bit))

            # Undo control flips
            if c1_on_zero:
                ops.append(("x", c1_bit))
            if c0_on_zero:
                ops.append(("x", c0_bit))
        else:
            # For 3+ controls, use recursive decomposition or raise
            raise NotImplementedError(
                f"Cascade with {len(control_stack)} nested controls not supported "
                f"(d={d} requires deeper decomposition). Reduce branching degree."
            )

    # Recurse on left subtree (controlled on current bit = |0>)
    if left_count > 1 and bit_offset + 1 < w:
        _plan_cascade_ops_recursive(
            left_count,
            w,
            bit_offset + 1,
            ops,
            control_stack + [(bit_offset, True)],  # True = control on |0>
        )

    # Recurse on right subtree (controlled on current bit = |1>)
    if right_count > 1 and bit_offset + 1 < w:
        _plan_cascade_ops_recursive(
            right_count,
            w,
            bit_offset + 1,
            ops,
            control_stack + [(bit_offset, False)],  # False = control on |1>
        )


def _emit_cascade_ops(branch_reg, ops, sign=1):
    """Execute pre-planned cascade gate operations on a branch register.

    Parameters
    ----------
    branch_reg : qint
        Branch register to operate on.
    ops : list[tuple]
        Gate operations from ``_plan_cascade_ops``.
    sign : int
        +1 for forward cascade, -1 for inverse (negates Ry angles).
    """
    w = branch_reg.width

    if sign == -1:
        # Inverse: reverse operation order and negate angles
        ops = list(reversed(ops))

    for op in ops:
        if op[0] == "ry":
            _, bit_off, angle = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            emit_ry(qubit, sign * angle)
        elif op[0] == "cry":
            _, bit_off, angle, ctrl_bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            ctrl_qubit = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            ctrl = _make_qbool_wrapper(ctrl_qubit)
            with ctrl:
                emit_ry(qubit, sign * angle)
        elif op[0] == "x":
            _, bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            emit_x(qubit)
        elif op[0] == "cx":
            # CNOT: target, control
            _, target_bit_off, ctrl_bit_off = op
            target_qubit = int(branch_reg.qubits[64 - w + target_bit_off])
            ctrl_qubit = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            ctrl = _make_qbool_wrapper(ctrl_qubit)
            with ctrl:
                emit_x(target_qubit)


def _emit_cascade_h_controlled(branch_reg, ops, h_qubit_idx, sign=1):
    """Execute cascade ops with height-qubit control, avoiding nested contexts.

    All gates are emitted controlled on ``h_qubit_idx``. For operations
    that already have a cascade control (cry, cx), the height control is
    added via V-gate decomposition (CCRy -> CRy + CNOT sequence) rather
    than nested ``with qbool:`` blocks.

    Parameters
    ----------
    branch_reg : qint
        Branch register to operate on.
    ops : list[tuple]
        Gate operations from ``_plan_cascade_ops``.
    h_qubit_idx : int
        Physical qubit index for the height control qubit.
    sign : int
        +1 for forward cascade, -1 for inverse (negates Ry angles).
    """
    w = branch_reg.width
    h_ctrl = _make_qbool_wrapper(h_qubit_idx)

    if sign == -1:
        ops = list(reversed(ops))

    for op in ops:
        if op[0] == "ry":
            # Single-qubit Ry -> CRy controlled on h
            _, bit_off, angle = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            with h_ctrl:
                emit_ry(qubit, sign * angle)
        elif op[0] == "cry":
            # CRy(theta, ctrl_q, target_q) -> CCRy(theta, h, ctrl_q, target_q)
            # Decompose via V-gate: CCRy(t) =
            #   CRy(t/2, c2, tgt) CNOT(c1, c2) CRy(-t/2, c2, tgt)
            #   CNOT(c1, c2) CRy(t/2, c1, tgt)
            # where c1=h_qubit, c2=cascade_ctrl
            _, bit_off, angle, ctrl_bit_off = op
            target_q = int(branch_reg.qubits[64 - w + bit_off])
            cascade_ctrl_q = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            theta = sign * angle
            cascade_ctrl = _make_qbool_wrapper(cascade_ctrl_q)

            # V-gate decomposition for CCRy
            with cascade_ctrl:
                emit_ry(target_q, theta / 2)
            with h_ctrl:
                emit_x(cascade_ctrl_q)
            with cascade_ctrl:
                emit_ry(target_q, -theta / 2)
            with h_ctrl:
                emit_x(cascade_ctrl_q)
            with h_ctrl:
                emit_ry(target_q, theta / 2)
        elif op[0] == "x":
            # X -> CX controlled on h
            _, bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            with h_ctrl:
                emit_x(qubit)
        elif op[0] == "cx":
            # CX(target, ctrl) -> CCX(h, ctrl, target)
            # Decompose as Toffoli via H-CCZ-H:
            #   H(target) MCZ(target, [h, ctrl]) H(target)
            _, target_bit_off, ctrl_bit_off = op
            target_q = int(branch_reg.qubits[64 - w + target_bit_off])
            cascade_ctrl_q = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            from ._gates import emit_h, emit_mcz

            emit_h(target_q)
            emit_mcz(target_q, [h_qubit_idx, cascade_ctrl_q])
            emit_h(target_q)


def _emit_multi_controlled_ry(target_qubit, angle, ctrl_qubits):
    """Emit Ry(angle) on target controlled by multiple qubits.

    For zero controls, emits unconditional Ry. For one control, uses
    CRy via qbool wrapper. For two or more controls, uses recursive
    V-gate decomposition.

    Parameters
    ----------
    target_qubit : int
        Physical qubit index for the Ry target.
    angle : float
        Rotation angle.
    ctrl_qubits : list[int]
        Physical qubit indices for controls.
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
        # V-gate decomposition: CCRy(theta) =
        #   CRy(theta/2, c1) CNOT(c0,c1) CRy(-theta/2, c1) CNOT(c0,c1) CRy(theta/2, c0)
        c0, c1 = ctrl_qubits
        c0_ctrl = _make_qbool_wrapper(c0)
        c1_ctrl = _make_qbool_wrapper(c1)
        with c1_ctrl:
            emit_ry(target_qubit, angle / 2)
        with c0_ctrl:
            emit_x(c1)
        with c1_ctrl:
            emit_ry(target_qubit, -angle / 2)
        with c0_ctrl:
            emit_x(c1)
        with c0_ctrl:
            emit_ry(target_qubit, angle / 2)
        return

    # 3+ controls: peel off last control, recurse
    primary = ctrl_qubits[-1]
    remaining = ctrl_qubits[:-1]
    p_ctrl = _make_qbool_wrapper(primary)
    with p_ctrl:
        emit_ry(target_qubit, angle / 2)
    for r in remaining:
        r_ctrl = _make_qbool_wrapper(r)
        with r_ctrl:
            emit_x(primary)
    with p_ctrl:
        emit_ry(target_qubit, -angle / 2)
    for r in remaining:
        r_ctrl = _make_qbool_wrapper(r)
        with r_ctrl:
            emit_x(primary)
    _emit_multi_controlled_ry(target_qubit, angle / 2, remaining)


def _emit_multi_controlled_x(target_qubit, ctrl_qubits):
    """Emit X on target controlled by multiple qubits.

    For zero controls: unconditional X. One control: CX. Two+ controls:
    H-MCZ-H decomposition.

    Parameters
    ----------
    target_qubit : int
        Physical qubit index for the X target.
    ctrl_qubits : list[int]
        Physical qubit indices for controls.
    """
    if not ctrl_qubits:
        emit_x(target_qubit)
        return
    if len(ctrl_qubits) == 1:
        ctrl = _make_qbool_wrapper(ctrl_qubits[0])
        with ctrl:
            emit_x(target_qubit)
        return
    from ._gates import emit_h, emit_mcz

    emit_h(target_qubit)
    emit_mcz(target_qubit, ctrl_qubits)
    emit_h(target_qubit)


def _emit_cascade_multi_controlled(branch_reg, ops, ctrl_qubits, sign=1):
    """Execute cascade ops with multiple control qubits.

    Each cascade gate operation is additionally controlled by all qubits
    in ctrl_qubits. Uses V-gate decomposition for multi-controlled gates.

    Parameters
    ----------
    branch_reg : qint
        Branch register to operate on.
    ops : list[tuple]
        Gate operations from ``_plan_cascade_ops``.
    ctrl_qubits : list[int]
        Physical qubit indices for additional controls.
    sign : int
        +1 for forward cascade, -1 for inverse (negates Ry angles).
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
            _emit_multi_controlled_ry(qubit, sign * angle, ctrl_qubits + [cascade_ctrl])
        elif op[0] == "x":
            _, bit_off = op
            qubit = int(branch_reg.qubits[64 - w + bit_off])
            _emit_multi_controlled_x(qubit, ctrl_qubits)
        elif op[0] == "cx":
            _, target_bit_off, ctrl_bit_off = op
            target_q = int(branch_reg.qubits[64 - w + target_bit_off])
            cascade_ctrl = int(branch_reg.qubits[64 - w + ctrl_bit_off])
            _emit_multi_controlled_x(target_q, ctrl_qubits + [cascade_ctrl])


class TreeNode:
    """Wraps tree registers for predicate evaluation.

    A lightweight state object passed to predicate callables. Provides
    access to the node's depth (via one-hot height register) and the
    branch values at each level.

    Parameters
    ----------
    height_register : qint
        One-hot height register (max_depth+1 qubits).
    branch_registers : list[qint]
        Per-level branch registers.
    max_depth : int
        Maximum tree depth.
    """

    __slots__ = ("_height_register", "_branch_registers", "_max_depth")

    def __init__(self, height_register, branch_registers, max_depth):
        self._height_register = height_register
        self._branch_registers = branch_registers
        self._max_depth = max_depth

    @property
    def depth(self):
        """One-hot height register as qint (max_depth+1 qubits).

        The qubit at position h[k] is |1> when the node is at depth k.
        """
        return self._height_register

    @property
    def branch_values(self):
        """List of qint branch registers, one per depth level."""
        return list(self._branch_registers)


class QWalkTree:
    """Quantum backtracking tree with one-hot height encoding.

    Encodes a backtracking search tree into quantum registers following
    Montanaro's scheme: a one-hot height register indicates which depth
    level the current node occupies, and per-level branch registers
    store which child was taken at each level.

    Parameters
    ----------
    max_depth : int
        Maximum depth of the tree (inclusive). A tree with max_depth=d
        has d+1 levels (0 through d).
    branching : int or list[int]
        Branching degree. If int, uniform branching at all levels.
        If list, per-level branching (length must equal max_depth).
    predicate : callable, optional
        Accept/reject predicate function. Receives a TreeNode and must
        return (is_accept, is_reject) as a tuple of two qbools.
        Validated at construction if provided.
    max_qubits : int, optional
        Maximum qubit budget for simulation (default 17). The tree can
        be constructed regardless of size; the budget is checked only
        when simulation is requested.

    Attributes
    ----------
    height_register : qint
        One-hot height register (max_depth+1 qubits).
    branch_registers : list[qint]
        Per-level branch registers.
    max_depth : int
        Maximum tree depth.
    branching : list[int]
        Normalized branching degrees (one per level).
    max_qubits : int
        Simulation qubit budget.
    node : TreeNode
        TreeNode accessor for predicate evaluation.
    total_qubits : int
        Total qubits used by the tree encoding.

    Examples
    --------
    >>> import quantum_language as ql
    >>> c = ql.circuit()
    >>> tree = ql.QWalkTree(max_depth=2, branching=2)
    >>> tree.total_qubits
    5
    >>> tree.height_register.width
    3
    """

    def __init__(self, max_depth, branching, predicate=None, *, max_qubits=17):
        self.max_depth = max_depth
        self.max_qubits = max_qubits
        self._predicate = predicate
        self._predicate_is_compiled = False

        # Normalize branching to per-level list
        if isinstance(branching, int):
            self.branching = [branching] * max_depth
        elif isinstance(branching, list | tuple):
            if len(branching) != max_depth:
                raise ValueError(
                    f"branching list length ({len(branching)}) must equal max_depth ({max_depth})"
                )
            self.branching = list(branching)
        else:
            raise ValueError(f"branching must be int or list, got {type(branching).__name__}")

        # Register allocation (eager, at construction)
        # Height register: one-hot encoding, max_depth+1 qubits
        self.height_register = qint(0, width=max_depth + 1)

        # Branch registers: one qint per depth level
        # Width = ceil(log2(branching[i])), minimum 1 qubit
        self.branch_registers = []
        for i in range(max_depth):
            b = self.branching[i]
            if b < 1:
                raise ValueError(f"branching degree must be >= 1, got {b} at level {i}")
            width = max(1, math.ceil(math.log2(b))) if b > 1 else 1
            self.branch_registers.append(qint(0, width=width))

        # Root state preparation: set height qubit for max_depth to |1>
        # In one-hot encoding, root is at depth max_depth (top of tree)
        # The MSB of the height register (qubits[63]) corresponds to bit max_depth
        root_qubit = self.height_register.qubits[63]
        emit_x(root_qubit)

        # Precompute diffusion angles for all depth levels
        self._setup_diffusion()

        # Lazy compilation for walk_step (compiled on first call)
        self._walk_compiled = None

        # Disjointness validation (fail fast)
        disjointness = self.verify_disjointness()
        if not disjointness["disjoint"]:
            raise ValueError(
                f"R_A and R_B height controls are not disjoint. "
                f"Overlapping qubit indices: {disjointness['overlap']}. "
                f"This indicates a bug in the parity assignment logic."
            )

        # Predicate validation (if provided) -- called at scope depth 0
        # to avoid LIFO scope interference with returned qbools
        if self._predicate is not None:
            self._validate_predicate()

    @property
    def total_qubits(self):
        """Total qubits used by the tree encoding.

        Computed as height register width + sum of branch register widths.
        """
        height_qubits = self.max_depth + 1
        branch_qubits = sum(max(1, math.ceil(math.log2(b))) if b > 1 else 1 for b in self.branching)
        return height_qubits + branch_qubits

    @property
    def node(self):
        """TreeNode accessor for predicate evaluation."""
        return TreeNode(self.height_register, self.branch_registers, self.max_depth)

    def _check_qubit_budget(self):
        """Check if total qubits exceed the simulation budget.

        Raises
        ------
        ValueError
            If total_qubits exceeds max_qubits.
        """
        total = self.total_qubits
        if total > self.max_qubits:
            raise ValueError(
                f"Tree requires {total} qubits but simulation budget is "
                f"{self.max_qubits} qubits. Reduce tree size or increase "
                f"max_qubits parameter."
            )

    def _setup_diffusion(self):
        """Precompute diffusion rotation angles and cascade ops for all levels.

        Stores per-level angle data in ``self._diffusion_data`` (list indexed
        by level_idx 0..max_depth-1) and the special root angle in
        ``self._root_phi``.

        Also pre-plans cascade gate operations for each unique (d, w) pair
        so that the cascade can be emitted as a flat sequence of gates
        (avoiding nested control contexts).

        Angles follow Montanaro 2015 Section 2:
        - Parent-children split: phi = 2*arctan(sqrt(d))
        - Cascade angles: theta_k = 2*arctan(sqrt(1/(d-1-k))) for k=0..d-2
        - Root special case: phi_root = 2*arctan(sqrt(n*d_root))
        """
        from .compile import compile as ql_compile

        self._diffusion_data = []
        self._cascade_ops = {}  # (d, w) -> list of gate ops
        self._cascade_compiled = {}  # (d, w) -> (fwd_compiled, inv_compiled)

        for level_idx in range(self.max_depth):
            d = self.branching[level_idx]
            depth = self.max_depth - level_idx

            # Parent-children split: phi = 2*arctan(sqrt(d))
            phi = 2.0 * math.atan(math.sqrt(d))

            # Child cascade angles: theta_k = 2*arctan(sqrt(1/(d-1-k)))
            cascade_angles = []
            for k in range(max(0, d - 1)):
                remaining = d - 1 - k
                if remaining > 0:
                    theta = 2.0 * math.atan(math.sqrt(1.0 / remaining))
                else:
                    theta = 0.0
                cascade_angles.append(theta)

            self._diffusion_data.append(
                {
                    "phi": phi,
                    "cascade": cascade_angles,
                    "d": d,
                    "depth": depth,
                    "level_idx": level_idx,
                }
            )

            # Pre-plan cascade gate operations for this (d, w)
            branch_reg = self.branch_registers[level_idx]
            w = branch_reg.width
            key = (d, w)
            if key not in self._cascade_ops and d > 1:
                ops = _plan_cascade_ops(d, w)
                self._cascade_ops[key] = ops

                # Build compiled forward/inverse cascade for height-controlled use
                _ops_capture = ops

                def _fwd_body(reg, _ops=_ops_capture):
                    _emit_cascade_ops(reg, _ops, sign=1)

                def _inv_body(reg, _ops=_ops_capture):
                    _emit_cascade_ops(reg, _ops, sign=-1)

                fwd_compiled = ql_compile(key=lambda r: r.width)(_fwd_body)
                inv_compiled = ql_compile(key=lambda r: r.width)(_inv_body)
                self._cascade_compiled[key] = (fwd_compiled, inv_compiled)

        # Root angle: phi_root = 2*arctan(sqrt(n*d_root))
        d_root = self.branching[0]  # root is at level_idx=0
        n = self.max_depth
        self._root_phi = 2.0 * math.atan(math.sqrt(n * d_root))

        # Variable branching: precompute angles for all possible child counts
        # d=1..d_max at each level. Used when predicate prunes some children.
        self._variable_angles = {}  # d_val -> {'phi': float, 'cascade_ops': list}
        for level_idx in range(self.max_depth):
            d_max_level = self.branching[level_idx]
            branch_reg = self.branch_registers[level_idx]
            w = branch_reg.width
            for d_val in range(1, d_max_level + 1):
                if d_val not in self._variable_angles:
                    phi_d = 2.0 * math.atan(math.sqrt(d_val))
                    ops_d = _plan_cascade_ops(d_val, w) if d_val > 1 else []
                    self._variable_angles[d_val] = {
                        "phi": phi_d,
                        "cascade_ops": ops_d,
                    }

        # Root angles for variable branching: phi_root(d) = 2*arctan(sqrt(n*d))
        self._variable_root_angles = {}
        d_root_max = self.branching[0]
        for d_val in range(1, d_root_max + 1):
            self._variable_root_angles[d_val] = 2.0 * math.atan(math.sqrt(n * d_val))

    def _height_qubit(self, depth):
        """Get physical qubit index for height register bit at given depth.

        In one-hot encoding, h[depth] = |1> means the node is at depth
        ``depth``.  Root is at depth=max_depth, leaves at depth=0.

        Parameters
        ----------
        depth : int
            Depth level (0..max_depth).

        Returns
        -------
        int
            Physical qubit index for h[depth].
        """
        width = self.max_depth + 1
        return int(self.height_register.qubits[64 - width + depth])

    def diffusion_info(self, depth):
        """Return diffusion angle data for inspection at a given depth.

        Parameters
        ----------
        depth : int
            Depth level (0..max_depth).

        Returns
        -------
        dict
            Angle data including 'phi', 'cascade_angles', 'd', 'depth',
            'is_root', and optionally 'phi_root' or 'is_leaf'.

        Raises
        ------
        ValueError
            If depth is out of range.
        """
        if depth < 0 or depth > self.max_depth:
            raise ValueError(f"depth must be 0..{self.max_depth}, got {depth}")

        # Leaf: no children, no diffusion
        if depth == 0:
            return {"depth": 0, "d": 0, "is_leaf": True}

        level_idx = self.max_depth - depth
        data = self._diffusion_data[level_idx]
        info = {
            "phi": data["phi"],
            "cascade_angles": list(data["cascade"]),
            "d": data["d"],
            "depth": depth,
        }

        if depth == self.max_depth:
            info["is_root"] = True
            info["phi_root"] = self._root_phi
        else:
            info["is_root"] = False

        return info

    @property
    def _use_variable_branching(self):
        """True if variable branching is active (predicate provided)."""
        return self._predicate is not None

    def _variable_diffusion(self, depth):
        """Apply variable-branching local diffusion D_x at the given depth.

        Evaluates the predicate on each potential child to determine which
        are valid, then applies angle-conditional rotations based on the
        count of valid children d(x). When d(x) = 0 (all rejected), the
        diffusion is skipped entirely (the conditional rotation blocks
        produce identity for the all-zeros validity pattern).

        The structure is:
        1. Allocate validity ancillae (one per potential child)
        2. Evaluate predicate on each child (navigate, evaluate, store, undo)
        3. Conditional U_dagger * S_0 * U for each possible d(x) value
        4. Uncompute validity ancillae (reverse of step 2)

        Parameters
        ----------
        depth : int
            Depth level (1..max_depth). Must not be called for depth=0.
        """
        from .qbool import qbool

        level_idx = self.max_depth - depth
        d_max = self.branching[level_idx]
        branch_reg = self.branch_registers[level_idx]
        h_qubit_idx = self._height_qubit(depth)
        h_control = _make_qbool_wrapper(h_qubit_idx)
        is_root = depth == self.max_depth

        # --- Step 1: Allocate validity ancillae ---
        # validity[i] = |1> means child i is VALID (not rejected).
        validity = [qbool() for _ in range(d_max)]

        # --- Step 2: Evaluate predicate on each child ---
        self._evaluate_children(depth, level_idx, d_max, validity)

        # --- Step 3: Conditional D_x = U * S_0 * U_dagger for each d(x) ---
        # For each possible d value (1..d_max), for each bit pattern with
        # exactly d ones among d_max validity ancillae, emit the conditional
        # rotation block.

        validity_qubits = [int(validity[j].qubits[63]) for j in range(d_max)]

        # Step 3a: U_dagger (inverse state preparation) conditional on d(x)
        for d_val in range(1, d_max + 1):
            angle_data = self._variable_angles.get(d_val)
            if angle_data is None:
                continue
            phi_d = angle_data["phi"]
            if is_root:
                phi_d = self._variable_root_angles.get(d_val, phi_d)
            cascade_ops_d = angle_data["cascade_ops"]

            for pattern in itertools.combinations(range(d_max), d_val):
                # Flip zeros so all validity qubits are |1> when pattern matches
                zeros = [j for j in range(d_max) if j not in pattern]
                for z in zeros:
                    emit_x(validity_qubits[z])

                ctrl_qubits = [h_qubit_idx] + validity_qubits

                # U_dagger: inverse cascade then inverse parent-child split
                if d_val > 1 and cascade_ops_d:
                    _emit_cascade_multi_controlled(branch_reg, cascade_ops_d, ctrl_qubits, sign=-1)
                _emit_multi_controlled_ry(self._height_qubit(depth - 1), -phi_d, ctrl_qubits)

                # Undo X flips
                for z in zeros:
                    emit_x(validity_qubits[z])

        # Step 3b: S_0 reflection (independent of d(x))
        # Same as uniform: X-MCZ-X on local subspace, controlled on h[depth]
        from ._gates import emit_mcz, emit_z
        from .diffusion import _collect_qubits

        h_child = _make_qbool_wrapper(self._height_qubit(depth - 1))
        s0_qubits = _collect_qubits(h_child, branch_reg)
        with h_control:
            for q in s0_qubits:
                emit_x(q)
        all_s0_with_h = [h_qubit_idx] + s0_qubits
        if len(all_s0_with_h) == 1:
            emit_z(all_s0_with_h[0])
        else:
            emit_mcz(all_s0_with_h[-1], all_s0_with_h[:-1])
        with h_control:
            for q in s0_qubits:
                emit_x(q)

        # Step 3c: U forward conditional on d(x)
        for d_val in range(1, d_max + 1):
            angle_data = self._variable_angles.get(d_val)
            if angle_data is None:
                continue
            phi_d = angle_data["phi"]
            if is_root:
                phi_d = self._variable_root_angles.get(d_val, phi_d)
            cascade_ops_d = angle_data["cascade_ops"]

            for pattern in itertools.combinations(range(d_max), d_val):
                zeros = [j for j in range(d_max) if j not in pattern]
                for z in zeros:
                    emit_x(validity_qubits[z])

                ctrl_qubits = [h_qubit_idx] + validity_qubits

                # U forward: parent-child Ry then cascade
                _emit_multi_controlled_ry(self._height_qubit(depth - 1), phi_d, ctrl_qubits)
                if d_val > 1 and cascade_ops_d:
                    _emit_cascade_multi_controlled(branch_reg, cascade_ops_d, ctrl_qubits, sign=1)

                for z in zeros:
                    emit_x(validity_qubits[z])

        # --- Step 4: Uncompute validity ancillae (reverse of step 2) ---
        self._uncompute_children(depth, level_idx, d_max, validity)

    def _evaluate_children(self, depth, level_idx, d_max, validity):
        """Evaluate predicate on each child and store validity results.

        For each child i (0..d_max-1):
        1. Navigate to child state (set branch register, flip height)
        2. Evaluate predicate
        3. Store validity: validity[i] = NOT reject (|1> = valid)
        4. Uncompute predicate and undo navigation

        Parameters
        ----------
        depth : int
            Current depth level.
        level_idx : int
            Level index (max_depth - depth).
        d_max : int
            Maximum branching degree at this level.
        validity : list[qbool]
            Validity ancillae to store results.
        """
        br = self.branch_registers[level_idx]
        bw = br.width

        for i in range(d_max):
            # Navigate to child i: encode child index in branch register
            for bit in range(bw):
                if (i >> (bw - 1 - bit)) & 1:
                    emit_x(int(br.qubits[64 - bw + bit]))

            # Flip height: move from depth to depth-1 (child's depth)
            emit_x(self._height_qubit(depth))
            emit_x(self._height_qubit(depth - 1))

            # Evaluate predicate
            node = self.node
            _accept_q, reject_q = self._predicate(node)

            # Store validity: validity[i] = NOT reject
            # CNOT from reject to validity, then X to invert
            reject_qubit = int(reject_q.qubits[63])
            validity_qubit = int(validity[i].qubits[63])
            reject_ctrl = _make_qbool_wrapper(reject_qubit)
            with reject_ctrl:
                emit_x(validity_qubit)
            emit_x(validity_qubit)  # Flip: validity=|1> means valid

            # Uncompute predicate
            if self._predicate_is_compiled:
                self._predicate.adjoint(node)

            # Undo height flip
            emit_x(self._height_qubit(depth - 1))
            emit_x(self._height_qubit(depth))

            # Undo branch register encoding
            for bit in range(bw):
                if (i >> (bw - 1 - bit)) & 1:
                    emit_x(int(br.qubits[64 - bw + bit]))

    def _uncompute_children(self, depth, level_idx, d_max, validity):
        """Uncompute validity ancillae (reverse of _evaluate_children).

        Must be called after the conditional diffusion blocks to disentangle
        the validity ancillae from the tree state.

        Parameters
        ----------
        depth : int
            Current depth level.
        level_idx : int
            Level index (max_depth - depth).
        d_max : int
            Maximum branching degree at this level.
        validity : list[qbool]
            Validity ancillae to uncompute.
        """
        br = self.branch_registers[level_idx]
        bw = br.width

        for i in reversed(range(d_max)):
            # Navigate to child i (same as forward)
            for bit in range(bw):
                if (i >> (bw - 1 - bit)) & 1:
                    emit_x(int(br.qubits[64 - bw + bit]))

            emit_x(self._height_qubit(depth))
            emit_x(self._height_qubit(depth - 1))

            # Re-evaluate predicate
            node = self.node
            _accept_q, reject_q = self._predicate(node)

            # Undo validity store (reverse: X then CNOT)
            reject_qubit = int(reject_q.qubits[63])
            validity_qubit = int(validity[i].qubits[63])
            emit_x(validity_qubit)
            reject_ctrl = _make_qbool_wrapper(reject_qubit)
            with reject_ctrl:
                emit_x(validity_qubit)

            # Uncompute predicate
            if self._predicate_is_compiled:
                self._predicate.adjoint(node)

            # Undo navigation
            emit_x(self._height_qubit(depth - 1))
            emit_x(self._height_qubit(depth))

            for bit in range(bw):
                if (i >> (bw - 1 - bit)) & 1:
                    emit_x(int(br.qubits[64 - bw + bit]))

    def local_diffusion(self, depth):
        """Apply local diffusion operator D_x at the given depth.

        D_x is the reflection 2|psi_x><psi_x| - I on the local subspace
        of a node at depth ``depth``. Implemented as U * S_0 * U_dagger
        where U prepares |psi_x> from |0...0>.

        All gates are controlled on the height qubit h[depth], so calling
        at a depth where h[depth] != |1> is a no-op (safe for walk operator
        loops over all depths).

        When a predicate is provided, dispatches to _variable_diffusion()
        which evaluates the predicate on each potential child and applies
        conditional rotations based on the count of valid children d(x).

        Parameters
        ----------
        depth : int
            Depth level (0..max_depth). Leaf (depth=0) is a no-op.

        Raises
        ------
        ValueError
            If depth is out of range.
        """
        if depth < 0 or depth > self.max_depth:
            raise ValueError(f"depth must be 0..{self.max_depth}, got {depth}")

        # Leaf skip: leaves have no children, no diffusion
        if depth == 0:
            return

        # Variable branching dispatch: predicate provided -> evaluate per-child
        if self._use_variable_branching:
            self._variable_diffusion(depth)
            return

        # Get level data
        level_idx = self.max_depth - depth
        data = self._diffusion_data[level_idx]
        d = data["d"]
        branch_reg = self.branch_registers[level_idx]
        w = branch_reg.width

        # Height-controlled dispatch: all gates controlled on h[depth]
        h_qubit_idx = self._height_qubit(depth)
        h_control = _make_qbool_wrapper(h_qubit_idx)

        is_root = depth == self.max_depth

        # Get pre-planned cascade ops
        cascade_key = (d, w)
        cascade_ops = self._cascade_ops.get(cascade_key, [])

        # D_x = U * S_0 * U_dagger (reflection about |psi_x>)
        # All gates height-controlled on h[depth].  The cascade uses
        # _emit_cascade_h_controlled which decomposes doubly-controlled
        # gates (CCRy) via V-gate pattern, avoiding nested 'with' blocks.

        # Step A: U_dagger (inverse state preparation)
        # First undo cascade, then undo parent-child split
        if d > 1 and cascade_ops:
            _emit_cascade_h_controlled(branch_reg, cascade_ops, h_qubit_idx, sign=-1)
        with h_control:
            if is_root:
                emit_ry(self._height_qubit(depth - 1), -self._root_phi)
            else:
                emit_ry(self._height_qubit(depth - 1), -data["phi"])

        # Step B: S_0 reflection on the local subspace
        # Emit raw X-MCZ-X pattern controlled on h[depth].
        from ._gates import emit_mcz, emit_z
        from .diffusion import _collect_qubits

        h_child = _make_qbool_wrapper(self._height_qubit(depth - 1))
        s0_qubits = _collect_qubits(h_child, branch_reg)
        with h_control:
            for q in s0_qubits:
                emit_x(q)
        # MCZ: add h_qubit to the control list for the S_0 reflection
        all_s0_with_h = [h_qubit_idx] + s0_qubits
        if len(all_s0_with_h) == 1:
            emit_z(all_s0_with_h[0])
        else:
            emit_mcz(all_s0_with_h[-1], all_s0_with_h[:-1])
        with h_control:
            for q in s0_qubits:
                emit_x(q)

        # Step C: U (forward state preparation)
        # First parent-child split, then cascade
        with h_control:
            if is_root:
                emit_ry(self._height_qubit(depth - 1), self._root_phi)
            else:
                emit_ry(self._height_qubit(depth - 1), data["phi"])
        if d > 1 and cascade_ops:
            _emit_cascade_h_controlled(branch_reg, cascade_ops, h_qubit_idx, sign=1)

    def R_A(self):
        """Apply R_A: reflections at even-depth nodes.

        R_A is the product of local diffusions D_x for all nodes at even
        depths (0, 2, 4, ...), excluding the root which always belongs
        to R_B per the Montanaro convention. Leaf (depth=0) is a no-op
        but included for completeness.

        Each local_diffusion(depth) is height-controlled (only activates
        when h[depth] = |1>), so applying all even depths is safe.
        """
        for depth in range(0, self.max_depth + 1, 2):
            if depth == self.max_depth:
                continue  # Root always belongs to R_B
            self.local_diffusion(depth)

    def R_B(self):
        """Apply R_B: reflections at odd-depth nodes plus root.

        R_B is the product of local diffusions D_x for all nodes at odd
        depths (1, 3, 5, ...) plus the root node (at max_depth).
        Root is always in R_B regardless of whether max_depth is even
        or odd (Montanaro convention).

        If max_depth is odd, the root is already covered by the odd-depth
        loop. If max_depth is even, root is added explicitly.
        """
        for depth in range(1, self.max_depth + 1, 2):
            self.local_diffusion(depth)
        # Root always in R_B; add if not already covered (even max_depth)
        if self.max_depth % 2 == 0:
            self.local_diffusion(self.max_depth)

    def verify_disjointness(self):
        """Verify R_A and R_B height controls are disjoint.

        Checks that the height qubits serving as primary controls for
        R_A (even depths, excluding root) and R_B (odd depths + root)
        have no overlap. This is the structural correctness condition
        for the product-of-reflections walk step.

        The check operates on physical qubit indices from the height
        register -- no circuit execution required.

        Returns
        -------
        dict
            Keys: 'R_A_qubits' (set), 'R_B_qubits' (set),
            'overlap' (set), 'disjoint' (bool).

        Examples
        --------
        >>> import quantum_language as ql
        >>> ql.circuit()
        >>> tree = ql.QWalkTree(max_depth=2, branching=2)
        >>> result = tree.verify_disjointness()
        >>> result['disjoint']
        True
        """
        r_a_depths = set()
        r_b_depths = set()

        # R_A: even depths, excluding root
        for depth in range(0, self.max_depth + 1, 2):
            if depth != self.max_depth:
                r_a_depths.add(depth)

        # R_B: odd depths + root
        for depth in range(1, self.max_depth + 1, 2):
            r_b_depths.add(depth)
        if self.max_depth % 2 == 0:
            r_b_depths.add(self.max_depth)

        # Map to physical qubit indices
        r_a_qubits = {self._height_qubit(d) for d in r_a_depths}
        r_b_qubits = {self._height_qubit(d) for d in r_b_depths}

        overlap = r_a_qubits & r_b_qubits
        return {
            "R_A_qubits": r_a_qubits,
            "R_B_qubits": r_b_qubits,
            "overlap": overlap,
            "disjoint": len(overlap) == 0,
        }

    def _all_qubits_register(self):
        """Create a qint wrapping all tree qubits (no allocation).

        Used as the argument to the compiled walk step so that all tree
        qubits are treated as parameter qubits (not internal ancillas).
        This prevents the forward-call tracking from blocking repeated
        walk_step() invocations.

        Returns
        -------
        qint
            A qint backed by all tree qubits (height + branch registers).
        """
        all_indices = []
        w = self.max_depth + 1
        for i in range(w):
            all_indices.append(int(self.height_register.qubits[64 - w + i]))
        for br in self.branch_registers:
            bw = br.width
            for i in range(bw):
                all_indices.append(int(br.qubits[64 - bw + i]))

        arr = np.zeros(64, dtype=np.uint32)
        total = len(all_indices)
        for i, idx in enumerate(all_indices):
            arr[64 - total + i] = idx
        return qint(0, create_new=False, bit_list=arr, width=total)

    def walk_step(self):
        """Apply walk step U = R_B * R_A.

        The walk step is the fundamental operation of the quantum walk.
        It composes R_A (even-depth reflections) and R_B (odd-depth +
        root reflections) into a single operation.

        On first call, the gate sequence is captured and compiled via
        @ql.compile for caching and automatic controlled variant
        derivation. Subsequent calls replay the cached sequence.

        The controlled variant is accessible via standard ``with qbool:``
        pattern -- no separate method needed.

        Examples
        --------
        >>> import quantum_language as ql
        >>> ql.circuit()
        >>> tree = ql.QWalkTree(max_depth=2, branching=2)
        >>> tree.walk_step()  # First call compiles
        >>> tree.walk_step()  # Replays cached gates
        """
        if self._walk_compiled is None:
            from .compile import compile as ql_compile

            # Capture tree reference for the closure
            tree_ref = self

            def _walk_body(all_qubits_reg):
                tree_ref.R_A()
                tree_ref.R_B()

            # Key by total_qubits per CONTEXT.md locked decision.
            # Pass all tree qubits as the argument so none are treated
            # as internal ancillas by the compile infrastructure.
            self._walk_compiled = ql_compile(key=lambda r: tree_ref.total_qubits)(_walk_body)

        self._walk_compiled(self._all_qubits_register())

    def _tree_size(self):
        """Compute total number of nodes in the tree.

        For uniform branching d at each level with max_depth n:
        T = 1 + d + d^2 + ... + d^n = (d^(n+1) - 1) / (d - 1)

        For variable branching, uses the maximum branching degree
        at each level (conservative upper bound for iteration count).

        Returns
        -------
        int
            Total node count.
        """
        total = 1  # root
        level_count = 1
        for level_idx in range(self.max_depth):
            level_count *= self.branching[level_idx]
            total += level_count
        return total

    def _measure_root_overlap(self, num_steps):
        """Build a fresh circuit with num_steps walk steps and measure root overlap.

        Constructs a new circuit and QWalkTree with identical parameters
        (but no predicate, to keep qubit count minimal), applies walk_step
        the specified number of times, then computes |<r|psi>|^2 where
        |r> is the root state.

        Parameters
        ----------
        num_steps : int
            Number of walk steps to apply.

        Returns
        -------
        float
            Probability of measuring the root state (|<r|psi>|^2).
        """
        import qiskit.qasm3
        from qiskit import transpile
        from qiskit_aer import AerSimulator

        import quantum_language as ql

        ql.circuit()
        inner_tree = QWalkTree(
            max_depth=self.max_depth,
            branching=list(self.branching),
            predicate=None,  # No predicate for clean measurement
            max_qubits=self.max_qubits,
        )

        for _ in range(num_steps):
            inner_tree.walk_step()

        qasm_str = ql.to_openqasm()

        # Statevector simulation
        circuit = qiskit.qasm3.loads(qasm_str)
        circuit.save_statevector()
        sim = AerSimulator(method="statevector", max_parallel_threads=4)
        result = sim.run(transpile(circuit, sim)).result()
        sv = np.asarray(result.get_statevector())

        # Root state index: h[max_depth]=|1>, all others |0>
        # Qiskit little-endian: qubit k set = bit k of statevector index
        h_root = inner_tree._height_qubit(inner_tree.max_depth)
        root_idx = 1 << h_root
        return float(abs(sv[root_idx]) ** 2)

    def _measure_marked_overlap(self, num_steps, marked_leaves):
        """Measure total probability of marked leaf states after walk steps.

        Constructs a fresh circuit, applies walk_step num_steps times,
        then sums the probabilities of all statevector components
        corresponding to the marked leaf assignments.

        This implements the marked vertex detection: if the walk step
        distributes significant amplitude to the marked leaves, a
        solution is detected.

        Parameters
        ----------
        num_steps : int
            Number of walk steps to apply.
        marked_leaves : list[dict]
            List of marked leaf states. Each dict maps depth level (int)
            to branch value (int), e.g. [{0: 0, 1: 1}] for leaf with
            branch[0]=0, branch[1]=1 at depth 0 (leaf level).

        Returns
        -------
        float
            Total probability of measuring any marked leaf state.
        """
        import qiskit.qasm3
        from qiskit import transpile
        from qiskit_aer import AerSimulator

        import quantum_language as ql

        ql.circuit()
        inner_tree = QWalkTree(
            max_depth=self.max_depth,
            branching=list(self.branching),
            predicate=None,
            max_qubits=self.max_qubits,
        )

        for _ in range(num_steps):
            inner_tree.walk_step()

        qasm_str = ql.to_openqasm()

        circuit = qiskit.qasm3.loads(qasm_str)
        circuit.save_statevector()
        sim = AerSimulator(method="statevector", max_parallel_threads=4)
        result = sim.run(transpile(circuit, sim)).result()
        sv = np.asarray(result.get_statevector())

        # Compute statevector indices for marked leaf states
        total_prob = 0.0
        for leaf in marked_leaves:
            idx = 0
            # Height qubit: leaf is at depth 0, so h[0] = |1>
            idx |= 1 << inner_tree._height_qubit(0)
            # Branch register values
            for level_idx, branch_val in leaf.items():
                br = inner_tree.branch_registers[level_idx]
                bw = br.width
                for bit in range(bw):
                    if (branch_val >> (bw - 1 - bit)) & 1:
                        idx |= 1 << int(br.qubits[64 - bw + bit])
            total_prob += float(abs(sv[idx]) ** 2)

        return total_prob

    def detect(self, max_iterations=None):
        """Detect whether a solution exists in the backtracking tree.

        Implements Montanaro's Algorithm 1 (adapted): iterative power-method
        detection. Applies the walk step U raised to increasing powers
        (1, 2, 4, 8, ...), measuring root state overlap after each power
        level. If the root overlap probability drops below the 3/8
        threshold at any power level, a solution is detected.

        Each power level is a separate circuit execution using statevector
        simulation.

        .. warning::

            This method resets the global circuit state. Save any existing
            circuit (via ``ql.to_openqasm()``) before calling.

        Parameters
        ----------
        max_iterations : int, optional
            Maximum number of walk steps in the largest power level.
            Auto-computed from tree size as ``ceil(sqrt(T / n))`` if not
            provided, where T is total node count and n is max_depth.

        Returns
        -------
        bool
            True if a solution is detected, False otherwise.
        """
        if max_iterations is None:
            T = self._tree_size()
            n = self.max_depth
            max_iterations = max(4, int(math.ceil(math.sqrt(T / n))))

        threshold = 3.0 / 8.0  # Montanaro detection threshold

        power = 1
        while power <= max_iterations:
            root_prob = self._measure_root_overlap(power)
            if root_prob < threshold:
                return True  # Solution detected
            power *= 2

        return False  # No solution detected

    def _validate_predicate(self):
        """Validate predicate mutual exclusion on root state.

        Calls the predicate on the current (root) state and checks that
        both is_accept and is_reject are not simultaneously True.

        Raises
        ------
        ValueError
            If mutual exclusion is violated (both accept and reject are True).
        TypeError
            If predicate returns wrong type or format.
        """
        from .compile import CompiledFunc

        node = TreeNode(self.height_register, self.branch_registers, self.max_depth)
        result = self._predicate(node)

        if not isinstance(result, tuple | list) or len(result) != 2:
            raise TypeError(
                "Predicate must return (is_accept, is_reject) tuple of two qbools, "
                f"got {type(result).__name__}"
                + (f" of length {len(result)}" if isinstance(result, tuple | list) else "")
            )

        is_accept, is_reject = result

        # Store accept/reject qbools for later use by walk operators
        self._accept = is_accept
        self._reject = is_reject

        # Check if predicate is a compiled function
        if isinstance(self._predicate, CompiledFunc):
            self._predicate_is_compiled = True

        # Mutual exclusion check -- at construction, root is computational
        # basis state so qbool values are deterministic. Use .measure()
        # to access the classical initialization value (cdef field).
        accept_val = is_accept.measure()
        reject_val = is_reject.measure()
        if accept_val and reject_val:
            raise ValueError(
                "Predicate mutual exclusion violated: both accept and reject "
                "returned True for the root state. A node cannot be "
                "simultaneously accepted and rejected."
            )

    def uncompute_predicate(self):
        """Uncompute predicate qbools.

        For @ql.compile predicates, calls .adjoint() to replay the inverse
        gate sequence. For raw callables, this is a no-op (user manages
        cleanup).

        Note: Uses adjoint (standalone inverse replay) rather than inverse
        (which requires matching forward-call qubit tracking). The predicate
        receives a TreeNode wrapper, not raw qint arguments, so the
        inverse proxy cannot match inputs.
        """
        if self._predicate is None:
            return
        if self._predicate_is_compiled:
            node = TreeNode(self.height_register, self.branch_registers, self.max_depth)
            self._predicate.adjoint(node)
