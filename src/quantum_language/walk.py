"""Quantum backtracking tree encoding (Montanaro 2015).

Provides QWalkTree for encoding backtracking search trees into quantum registers.
The tree uses a one-hot height register (max_depth+1 qubits) and per-level branch
registers. Local diffusion operators, walk operators, and detection are built on
top of this encoding in later modules.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

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

    def local_diffusion(self, depth):
        """Apply local diffusion operator D_x at the given depth.

        D_x is the reflection 2|psi_x><psi_x| - I on the local subspace
        of a node at depth ``depth``. Implemented as U * S_0 * U_dagger
        where U prepares |psi_x> from |0...0>.

        All gates are controlled on the height qubit h[depth], so calling
        at a depth where h[depth] != |1> is a no-op (safe for walk operator
        loops over all depths).

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
