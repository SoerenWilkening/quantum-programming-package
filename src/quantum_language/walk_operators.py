"""Walk operators: R_A, R_B, walk_step for quantum backtracking.

Provides the height-controlled walk operators that compose local diffusion
operators at alternating depths to form the walk step U = R_B * R_A.

R_A: local diffusion at even depths (excluding root).
R_B: local diffusion at odd depths plus root.

The walk step is compiled with ``@ql.compile`` for gate caching so that
repeated applications replay the cached gate sequence.

Height controls are disjoint by construction: even-depth height qubits
(minus root) for R_A, odd-depth height qubits plus root for R_B.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

from ._gates import emit_mcz, emit_ry, emit_x, emit_z
from .walk_branching import (
    _emit_cascade_multi_controlled,
    _make_qbool_wrapper,
    _plan_cascade_ops,
)
from .walk_core import (
    WalkConfig,
    branch_width,
    montanaro_phi,
    root_angle,
)
from .walk_diffusion import _s0_reflection
from .walk_registers import WalkRegisters


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def _validate_operator_args(config, registers):
    """Validate arguments for walk operator functions.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.
    registers : WalkRegisters
        Walk registers.

    Raises
    ------
    TypeError
        If arguments are wrong type.
    """
    if not isinstance(config, WalkConfig):
        raise TypeError(
            f"config must be a WalkConfig, got {type(config).__name__}"
        )
    if not isinstance(registers, WalkRegisters):
        raise TypeError(
            f"registers must be a WalkRegisters, got "
            f"{type(registers).__name__}"
        )


# ------------------------------------------------------------------
# Angle precomputation
# ------------------------------------------------------------------


def _precompute_diffusion_angles(num_moves, bw, is_root=False,
                                  max_depth=1):
    """Pre-compute Montanaro angles and cascade ops for c = 1 .. num_moves.

    Parameters
    ----------
    num_moves : int
        Maximum branching factor.
    bw : int
        Branch register width.
    is_root : bool
        If True, use root angle formula.
    max_depth : int
        Tree depth (for root angle formula).

    Returns
    -------
    dict
        Maps child count c -> {"phi": float, "cascade_ops": list}.
    """
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
# Height-controlled local diffusion (fixed branching)
# ------------------------------------------------------------------


def _height_controlled_diffusion(h_qubit_idx, h_child_idx, branch_reg,
                                  num_moves, angle_data):
    """Apply local diffusion D_x controlled on height qubit.

    All gates are controlled on h[depth] (the height qubit at the
    current depth).  The diffusion acts on the h[depth-1] qubit
    (child height bit) and the branch register at this level.

    Implements D_x = U * S_0 * U_dagger where:
    - U = Ry(phi) on h_child + cascade on branch_reg
    - S_0 = phase flip on |0...0> of h_child + branch_reg

    Parameters
    ----------
    h_qubit_idx : int
        Physical qubit index for h[depth] (control).
    h_child_idx : int
        Physical qubit index for h[depth-1] (target of Ry).
    branch_reg : qint
        Branch register at this depth level.
    num_moves : int
        Branching factor (number of valid children).
    angle_data : dict
        Pre-computed angles from ``_precompute_diffusion_angles``.
    """
    if num_moves < 1:
        return  # No children -> identity

    phi = angle_data[num_moves]["phi"]
    cascade_ops = angle_data[num_moves]["cascade_ops"]
    h_control = _make_qbool_wrapper(h_qubit_idx)

    # Step A: U_dagger (inverse state preparation)
    # Undo cascade, then undo parent-child split rotation.
    if num_moves > 1 and cascade_ops:
        _emit_cascade_multi_controlled(
            branch_reg, cascade_ops, [h_qubit_idx], sign=-1,
        )
    with h_control:
        emit_ry(h_child_idx, -phi)

    # Step B: S_0 reflection on h_child + branch_reg subspace,
    # controlled on h[depth].
    #
    # The S_0 reflection flips phase on |0...0> of (h_child, branch_reg).
    # We need: X on all qubits, MCZ on all, X on all -- all controlled
    # on h[depth].
    from .diffusion import _collect_qubits

    h_child_qbool = _make_qbool_wrapper(h_child_idx)
    s0_qubits = _collect_qubits(h_child_qbool, branch_reg)

    # X on all s0_qubits, controlled on h[depth]
    with h_control:
        for q in s0_qubits:
            emit_x(q)

    # MCZ: add h_qubit_idx to the control list
    all_s0_with_h = [h_qubit_idx] + s0_qubits
    if len(all_s0_with_h) == 1:
        emit_z(all_s0_with_h[0])
    else:
        emit_mcz(all_s0_with_h[-1], all_s0_with_h[:-1])

    # X on all s0_qubits, controlled on h[depth]
    with h_control:
        for q in s0_qubits:
            emit_x(q)

    # Step C: U (forward state preparation)
    # Parent-child split rotation, then cascade.
    with h_control:
        emit_ry(h_child_idx, phi)
    if num_moves > 1 and cascade_ops:
        _emit_cascade_multi_controlled(
            branch_reg, cascade_ops, [h_qubit_idx], sign=1,
        )


def _height_controlled_variable_diffusion(config, registers, depth,
                                           is_root=False):
    """Apply variable-branching local diffusion controlled on height qubit.

    Uses the counting-based approach: evaluate validity for each child,
    count valid children, apply conditional Montanaro rotations, S_0
    reflection, and uncompute.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with state, make_move, is_valid, num_moves.
    registers : WalkRegisters
        Walk registers.
    depth : int
        Depth level (1..max_depth).
    is_root : bool
        If True, use root angle formula.
    """
    import quantum_language as ql

    num_moves = config.num_moves
    bw = config.bw
    h_qubit_idx = registers.height_qubit(depth)
    h_child_idx = registers.height_qubit(depth - 1)
    branch_reg = registers.branch_at(depth - 1)
    h_control = _make_qbool_wrapper(h_qubit_idx)

    # Pre-compute angles for all possible count values
    angle_data = _precompute_diffusion_angles(
        num_moves, bw, is_root=is_root, max_depth=config.max_depth,
    )

    # Step 1: Evaluate validity for all children
    state = config.state
    make_move = config.make_move
    is_valid = config.is_valid
    undo = config.undo_move
    if undo is None:
        undo = config.make_move.adjoint

    validity = []
    for i in range(num_moves):
        make_move(state, i)
        v = is_valid(state)
        validity.append(v)
        undo(state, i)

    # Step 2: Sum validity bits into count register
    from .walk_core import count_width
    cw = count_width(num_moves)
    count = ql.qint(0, width=cw)
    for v in validity:
        with v:
            count += 1

    # Step 3: Compute count comparisons
    cond_qubits_map = {}
    for c in range(1, num_moves + 1):
        if c in angle_data:
            cond = (count == c)
            cond_qubits_map[c] = int(cond.qubits[63])

    # Step 4: U_dagger (inverse state preparation)
    for c in range(1, num_moves + 1):
        if c not in angle_data:
            continue
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]
        ctrl_qubits = [h_qubit_idx, cond_qubits_map[c]]

        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=-1,
            )
        from .walk_branching import _emit_multi_controlled_ry
        _emit_multi_controlled_ry(h_child_idx, -phi, ctrl_qubits)

    # Step 5: S_0 reflection controlled on h[depth]
    from .diffusion import _collect_qubits

    h_child_qbool = _make_qbool_wrapper(h_child_idx)
    s0_qubits = _collect_qubits(h_child_qbool, branch_reg)

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

    # Step 6: U forward (state preparation)
    for c in range(1, num_moves + 1):
        if c not in angle_data:
            continue
        phi = angle_data[c]["phi"]
        cascade_ops = angle_data[c]["cascade_ops"]
        ctrl_qubits = [h_qubit_idx, cond_qubits_map[c]]

        _emit_multi_controlled_ry(h_child_idx, phi, ctrl_qubits)
        if c > 1 and cascade_ops:
            _emit_cascade_multi_controlled(
                branch_reg, cascade_ops, ctrl_qubits, sign=1,
            )

    # Step 7: Uncompute count register
    for v in reversed(validity):
        with v:
            count -= 1


# ------------------------------------------------------------------
# Local diffusion dispatch
# ------------------------------------------------------------------


def _apply_local_diffusion(config, registers, depth):
    """Apply local diffusion at the given depth, controlled on height.

    Dispatches between fixed-branching (no predicates) and variable-
    branching (with is_valid predicate) depending on whether config
    has callbacks set.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.
    registers : WalkRegisters
        Walk registers.
    depth : int
        Depth level (0..max_depth). Depth 0 is leaf (no-op).
    """
    if depth == 0:
        return  # Leaf: no children, no diffusion

    is_root = (depth == config.max_depth)

    # Determine whether to use variable or fixed branching
    use_variable = (config.make_move is not None
                    and config.is_valid is not None
                    and config.state is not None)

    if use_variable:
        _height_controlled_variable_diffusion(
            config, registers, depth, is_root=is_root,
        )
    else:
        # Fixed branching: direct Montanaro rotations
        num_moves = config.num_moves
        bw = config.bw
        h_qubit_idx = registers.height_qubit(depth)
        h_child_idx = registers.height_qubit(depth - 1)

        # The branch register at depth d is used for branches going
        # from depth d down to depth d-1.  In WalkRegisters, branches
        # are indexed 0..max_depth-1 where index 0 is the deepest
        # (leaf level).  The branch at "depth d" (tree depth) maps to
        # branches[max_depth - depth] in the register layout.  But
        # WalkRegisters.branch_at(depth) handles this mapping using
        # the direct index, where branch_at(d) returns branches[d].
        # For the walk operators, the branch register at tree depth d
        # is branch_at(depth - 1), matching how the tree descends from
        # depth d to depth d-1.
        branch_reg = registers.branch_at(depth - 1)

        angle_data = _precompute_diffusion_angles(
            num_moves, bw, is_root=is_root,
            max_depth=config.max_depth,
        )

        _height_controlled_diffusion(
            h_qubit_idx, h_child_idx, branch_reg,
            num_moves, angle_data,
        )


# ------------------------------------------------------------------
# R_A: even-depth reflections (excluding root)
# ------------------------------------------------------------------


def build_R_A(config, registers):
    """Apply R_A: local diffusion at even-depth nodes (excluding root).

    R_A is the product of local diffusion operators D_x for nodes at
    even depths (0, 2, 4, ...), excluding the root which always belongs
    to R_B per the Montanaro convention.

    Each diffusion at depth ``d`` is controlled on the height qubit
    ``height[d]``, so it only activates when the walk is at that depth.
    Depth 0 (leaf) is a no-op.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``max_depth``, ``num_moves``.
    registers : WalkRegisters
        Walk registers with height and branch registers.

    Raises
    ------
    TypeError
        If arguments are wrong type.
    """
    _validate_operator_args(config, registers)

    for depth in range(0, config.max_depth + 1, 2):
        if depth == config.max_depth:
            continue  # Root always belongs to R_B
        _apply_local_diffusion(config, registers, depth)


# ------------------------------------------------------------------
# R_B: odd-depth reflections plus root
# ------------------------------------------------------------------


def build_R_B(config, registers):
    """Apply R_B: local diffusion at odd-depth nodes plus root.

    R_B is the product of local diffusion operators D_x for nodes at
    odd depths (1, 3, 5, ...) plus the root node (at max_depth).
    Root is always in R_B regardless of whether max_depth is even or
    odd (Montanaro convention).

    Each diffusion at depth ``d`` is controlled on the height qubit
    ``height[d]``.  If max_depth is odd, the root is already covered
    by the odd-depth loop.  If max_depth is even, root is added
    explicitly.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``max_depth``, ``num_moves``.
    registers : WalkRegisters
        Walk registers with height and branch registers.

    Raises
    ------
    TypeError
        If arguments are wrong type.
    """
    _validate_operator_args(config, registers)

    for depth in range(1, config.max_depth + 1, 2):
        _apply_local_diffusion(config, registers, depth)

    # Root always in R_B; add if not already covered (even max_depth)
    if config.max_depth % 2 == 0:
        _apply_local_diffusion(config, registers, config.max_depth)


# ------------------------------------------------------------------
# Disjointness verification
# ------------------------------------------------------------------


def verify_disjointness(config, registers):
    """Verify R_A and R_B height controls are disjoint.

    Checks that the height qubits serving as primary controls for
    R_A (even depths, excluding root) and R_B (odd depths + root)
    have no overlap.  This is the structural correctness condition
    for the product-of-reflections walk step.

    The check operates on physical qubit indices from the height
    register -- no circuit execution required.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``max_depth``.
    registers : WalkRegisters
        Walk registers with height register.

    Returns
    -------
    dict
        Keys: ``R_A_qubits`` (set), ``R_B_qubits`` (set),
        ``overlap`` (set), ``disjoint`` (bool).

    Raises
    ------
    TypeError
        If arguments are wrong type.
    """
    _validate_operator_args(config, registers)

    r_a_depths = set()
    r_b_depths = set()

    # R_A: even depths, excluding root
    for depth in range(0, config.max_depth + 1, 2):
        if depth != config.max_depth:
            r_a_depths.add(depth)

    # R_B: odd depths + root
    for depth in range(1, config.max_depth + 1, 2):
        r_b_depths.add(depth)
    if config.max_depth % 2 == 0:
        r_b_depths.add(config.max_depth)

    # Map to physical qubit indices
    r_a_qubits = {registers.height_qubit(d) for d in r_a_depths}
    r_b_qubits = {registers.height_qubit(d) for d in r_b_depths}

    overlap = r_a_qubits & r_b_qubits
    return {
        "R_A_qubits": r_a_qubits,
        "R_B_qubits": r_b_qubits,
        "overlap": overlap,
        "disjoint": len(overlap) == 0,
    }


# ------------------------------------------------------------------
# walk_step: R_B * R_A composed and compiled
# ------------------------------------------------------------------


def walk_step(config, registers):
    """Apply one walk step U = R_B * R_A.

    Composes R_A (even-depth reflections) and R_B (odd-depth + root
    reflections) into a single unitary.  The walk step is the
    fundamental iteration of the quantum backtracking algorithm.

    The operation preserves the norm of the statevector (unitarity).

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.
    registers : WalkRegisters
        Walk registers.

    Raises
    ------
    TypeError
        If arguments are wrong type.
    """
    _validate_operator_args(config, registers)
    build_R_A(config, registers)
    build_R_B(config, registers)


class WalkOperatorState:
    """Holds compiled walk step for repeated application.

    Wraps ``walk_step`` in ``@ql.compile`` for gate caching.  The
    first call captures the gate sequence; subsequent calls replay it.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.
    registers : WalkRegisters
        Walk registers.

    Attributes
    ----------
    config : WalkConfig
        Walk configuration.
    registers : WalkRegisters
        Walk registers.
    """

    __slots__ = ("config", "registers", "_compiled_fn", "_all_qubits_reg")

    def __init__(self, config, registers):
        _validate_operator_args(config, registers)
        self.config = config
        self.registers = registers
        self._compiled_fn = None
        self._all_qubits_reg = None

    def _build_all_qubits_register(self):
        """Create a qint wrapping all walk register qubits.

        Used as the argument to the compiled walk step so that all
        register qubits are treated as parameter qubits (not internal
        ancillas).

        Returns
        -------
        qint
            A qint backed by all walk register qubits.
        """
        import numpy as np
        from .qint import qint

        all_indices = []

        # Height register qubits
        for h in self.registers.height:
            all_indices.append(int(h.qubits[63]))

        # Branch register qubits
        for br in self.registers.branches:
            bw = br.width
            for i in range(bw):
                all_indices.append(int(br.qubits[64 - bw + i]))

        # Count register qubits
        cw = self.registers.count.width
        for i in range(cw):
            all_indices.append(
                int(self.registers.count.qubits[64 - cw + i])
            )

        arr = np.zeros(64, dtype=np.uint32)
        total = len(all_indices)
        for i, idx in enumerate(all_indices):
            arr[64 - total + i] = idx
        return qint(0, create_new=False, bit_list=arr, width=total)

    def step(self):
        """Apply one compiled walk step.

        On first call, captures the gate sequence via ``@ql.compile``.
        Subsequent calls replay the cached sequence.
        """
        if self._compiled_fn is None:
            from .compile import compile as ql_compile

            cfg_ref = self.config
            regs_ref = self.registers

            def _walk_body(all_qubits_reg):
                build_R_A(cfg_ref, regs_ref)
                build_R_B(cfg_ref, regs_ref)

            self._compiled_fn = ql_compile(
                key=lambda r: regs_ref.total_qubits()
            )(_walk_body)

            self._all_qubits_reg = self._build_all_qubits_register()

        self._compiled_fn(self._all_qubits_reg)

    @property
    def is_compiled(self):
        """True if the walk step has been compiled (first call done)."""
        return self._compiled_fn is not None
