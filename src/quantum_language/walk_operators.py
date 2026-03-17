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

from .diffusion import _qubit_index, _register_indices, _xor_with_simulate
from .walk_core import WalkConfig
from .walk_diffusion import _evaluate_validity, walk_diffusion_with_regs
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
        raise TypeError(f"config must be a WalkConfig, got {type(config).__name__}")
    if not isinstance(registers, WalkRegisters):
        raise TypeError(f"registers must be a WalkRegisters, got {type(registers).__name__}")


# ------------------------------------------------------------------
# Local diffusion dispatch
# ------------------------------------------------------------------


def _apply_local_diffusion(config, registers, depth):
    """Apply local diffusion at the given depth, controlled on height.

    Always uses variable-branching diffusion (with is_valid predicate).
    If ``config.is_marked`` is set, the marking predicate is evaluated
    quantumly: marked nodes receive identity (D_x = I) while unmarked
    nodes receive the standard diffusion operator.

    Height control uses the qbool from ``registers.height_qubit(depth)``.
    The child height qbool is passed directly as the parent flag.

    When marking is active, the structure at this level is:

    1. Evaluate validity unconditionally (no marking control).
    2. Evaluate ``is_marked(state)`` to obtain a ``marked`` qbool.
    3. Negate ``marked`` so it is |1> for UNMARKED nodes.
    4. Pass ``marked`` as ``marking_qbool`` into the diffusion so that
       only the rotation / S_0 steps are conditioned on it.
    5. Undo the negation.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with state, make_move, is_valid.
    registers : WalkRegisters
        Walk registers.
    depth : int
        Depth level (0..max_depth). Depth 0 is leaf (no-op).
    """
    if depth == 0:
        return  # Leaf: no children, no diffusion

    is_root = depth == config.max_depth

    h_qbool = registers.height_qubit(depth)
    h_child_qbool = registers.height_qubit(depth - 1)
    branch_reg = registers.branch_at(depth - 1)

    if config.is_marked is not None and config.state is not None:
        # Quantum marking with variable branching:
        # D_x = I for marked, standard diffusion for unmarked.

        # Step 1: Evaluate validity unconditionally (outside marking).
        validity = _evaluate_validity(config)

        # Step 2-3: Evaluate is_marked(state) quantumly, negate so
        # that the marking qbool is |1> for UNMARKED nodes.
        marked = config.is_marked(config.state)
        _xor_with_simulate(marked, 1)

        # Step 4: Pass marked qbool into diffusion -- only the
        # rotation / S_0 steps are controlled on it.  Validity
        # is pre-evaluated and passed in so it runs unconditionally.
        walk_diffusion_with_regs(
            config,
            h_child_qbool,
            branch_reg,
            is_root=is_root,
            control_qbool=h_qbool,
            marking_qbool=marked,
            validity=validity,
        )

        # Step 5: Undo the negation.
        _xor_with_simulate(marked, 1)
    else:
        walk_diffusion_with_regs(
            config,
            h_child_qbool,
            branch_reg,
            is_root=is_root,
            control_qbool=h_qbool,
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

    # Map to physical qubit indices via _qubit_index helper
    r_a_qubits = {_qubit_index(registers.height_qubit(d)) for d in r_a_depths}
    r_b_qubits = {_qubit_index(registers.height_qubit(d)) for d in r_b_depths}

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
            all_indices.append(_qubit_index(h))

        # Branch register qubits
        for br in self.registers.branches:
            all_indices.extend(_register_indices(br))

        # Count register qubits
        all_indices.extend(_register_indices(self.registers.count))

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

            self._compiled_fn = ql_compile(key=lambda r: regs_ref.total_qubits())(_walk_body)

            self._all_qubits_reg = self._build_all_qubits_register()

        self._compiled_fn(self._all_qubits_reg)

    @property
    def is_compiled(self):
        """True if the walk step has been compiled (first call done)."""
        return self._compiled_fn is not None
