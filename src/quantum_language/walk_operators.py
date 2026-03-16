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

import warnings

from .diffusion import _flip_all
from .walk_core import WalkConfig
from .walk_diffusion import walk_diffusion_fixed, walk_diffusion_with_regs
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
# Local diffusion dispatch
# ------------------------------------------------------------------


def _apply_fixed_diffusion(config, registers, depth, is_root):
    """Apply fixed-branching diffusion at *depth*, controlled on height."""
    from .walk_branching import _make_qbool_wrapper

    h_qubit_idx = registers.height_qubit(depth)
    h_child_idx = registers.height_qubit(depth - 1)
    branch_reg = registers.branch_at(depth - 1)
    parent_flag = _make_qbool_wrapper(h_child_idx)

    walk_diffusion_fixed(
        parent_flag, branch_reg, config.num_moves,
        max_depth=config.max_depth, is_root=is_root,
        control_qubit=h_qubit_idx,
    )


def _apply_local_diffusion(config, registers, depth):
    """Apply local diffusion at the given depth, controlled on height.

    Dispatches between fixed-branching (no predicates) and variable-
    branching (with is_valid predicate) depending on whether config
    has callbacks set.

    Per Montanaro 2015, if ``config.is_marked`` is set along with
    ``config.state``, the marking predicate is evaluated quantumly.
    Marked nodes receive identity (D_x = I) while unmarked nodes
    receive the standard diffusion operator.

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
        # Variable branching: marking is not yet integrated into the
        # variable-branching path because make_move uses DSL operations
        # (XOR) that do not support controlled execution.  The variable
        # diffusion runs unconditionally here; marking integration for
        # variable branching is deferred to walk_search rewrite
        # (Quantum_Assembly-8sp).
        if config.is_marked is not None:
            warnings.warn(
                "is_marked is ignored in the variable-branching path; "
                "marking integration for variable branching is deferred "
                "to the walk_search rewrite (Quantum_Assembly-8sp)",
                stacklevel=2,
            )
        from .walk_branching import _make_qbool_wrapper

        h_qubit_idx = registers.height_qubit(depth)
        h_child_idx = registers.height_qubit(depth - 1)
        branch_reg = registers.branch_at(depth - 1)
        parent_flag = _make_qbool_wrapper(h_child_idx)

        walk_diffusion_with_regs(
            config, parent_flag, branch_reg,
            is_root=is_root, control_qubit=h_qubit_idx,
        )
    elif config.is_marked is not None and config.state is not None:
        # Quantum marking (fixed branching):
        # D_x = I for marked, standard diffusion for unmarked.
        # Evaluate is_marked(state) quantumly to get a qbool,
        # negate it so that ``with marked:`` runs on UNMARKED nodes.
        #
        # Note: this code path is infrastructure for the walk_search
        # rewrite (Quantum_Assembly-8sp).  The current walk() public
        # API in walk_search.py does not set config.state, so it does
        # not reach this branch yet.
        marked = config.is_marked(config.state)
        _flip_all(marked)
        with marked:
            _apply_fixed_diffusion(config, registers, depth, is_root)
        _flip_all(marked)
    else:
        _apply_fixed_diffusion(config, registers, depth, is_root)


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
