"""Full quantum walk search with detection (Montanaro 2015).

Public API: ``walk(is_marked, max_depth, num_moves, *, state=None, make_move=None, is_valid=None, max_iterations=None)``

Algorithm
---------
The detection algorithm modifies the walk step U = R_B * R_A by
incorporating a marking oracle phase flip at the leaf level (depth 0).
Standard R_A skips depth 0 (leaves have no children); for detection,
R_A' applies a phase flip on marked leaf patterns before R_A.

The marking oracle is evaluated classically to determine which branch
patterns correspond to marked leaves, then phase flips are applied
via multi-controlled-Z gates on the branch register qubits.

Detection uses iterative power-method: for increasing powers
1, 2, 4, 8, ..., compare root overlap of the marked walk to the
unmarked baseline.  If the marked walk's overlap diverges from the
baseline beyond a detection threshold, a marked node is detected.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

import math

import numpy as np

from ._gates import emit_mcz, emit_x, emit_z
from .walk_core import WalkConfig
from .walk_operators import build_R_A, build_R_B, walk_step
from .walk_registers import WalkRegisters


# ------------------------------------------------------------------
# Tree size computation
# ------------------------------------------------------------------


def _tree_size(num_moves, max_depth):
    """Total nodes: (d^(n+1) - 1) / (d - 1)."""
    if num_moves == 1:
        return max_depth + 1
    return (num_moves ** (max_depth + 1) - 1) // (num_moves - 1)


# ------------------------------------------------------------------
# Iteration count
# ------------------------------------------------------------------


def _max_walk_iterations(num_moves, max_depth):
    """O(sqrt(T/n)) iterations, minimum 4."""
    T = _tree_size(num_moves, max_depth)
    return max(4, int(math.ceil(math.sqrt(T / max_depth))))


# ------------------------------------------------------------------
# Marking oracle at leaf level
# ------------------------------------------------------------------


def _collect_branch_qubits(registers, config):
    """Flat list of branch register qubit indices, leaf to root."""
    qubits = []
    for d in range(config.max_depth):
        br = registers.branch_at(d)
        bw = br.width
        for bit in range(bw):
            qubits.append(int(br.qubits[64 - bw + bit]))
    return qubits


def _evaluate_is_marked_classically(is_marked, total_branch_bits):
    """Return list of integer patterns where is_marked returns True."""
    marked_values = []
    for val in range(1 << total_branch_bits):
        result = is_marked(val)
        if result is True or result == 1:
            marked_values.append(val)
    return marked_values


def _apply_phase_on_pattern(pattern, branch_qubits, h_leaf_qubit):
    """Phase flip on a specific branch pattern via X-MCZ-X."""
    total_bits = len(branch_qubits)

    # X on branch qubits that should be |0> in the pattern
    for bit_idx in range(total_bits):
        if not ((pattern >> bit_idx) & 1):
            emit_x(branch_qubits[bit_idx])

    # MCZ on h[0] + all branch qubits: phase flip when all are |1>
    all_qubits = [h_leaf_qubit] + branch_qubits
    if len(all_qubits) == 1:
        emit_z(all_qubits[0])
    else:
        emit_mcz(all_qubits[-1], all_qubits[:-1])

    # Undo X
    for bit_idx in range(total_bits):
        if not ((pattern >> bit_idx) & 1):
            emit_x(branch_qubits[bit_idx])


def _apply_marking_phase(config, registers):
    """Phase flip marked leaf patterns, controlled on h[0]=|1>."""
    h_leaf_qubit = registers.height_qubit(0)
    branch_qubits = _collect_branch_qubits(registers, config)
    total_bits = len(branch_qubits)

    marked_values = _evaluate_is_marked_classically(
        config.is_marked, total_bits,
    )

    for val in marked_values:
        _apply_phase_on_pattern(val, branch_qubits, h_leaf_qubit)


# ------------------------------------------------------------------
# Marked walk step
# ------------------------------------------------------------------


def _marked_walk_step(config, registers):
    """Walk step U' = R_B * R_A' with marking phase at depth 0."""
    fixed_config = WalkConfig(
        max_depth=config.max_depth,
        num_moves=config.num_moves,
    )

    # R_A' = marking phase + standard R_A
    _apply_marking_phase(config, registers)
    build_R_A(fixed_config, registers)

    # R_B as usual
    build_R_B(fixed_config, registers)


# ------------------------------------------------------------------
# Statevector simulation
# ------------------------------------------------------------------


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
    import qiskit.qasm3
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


# ------------------------------------------------------------------
# Root overlap measurement
# ------------------------------------------------------------------


def _measure_root_overlap(config, num_steps):
    """Root state probability after num_steps marked walk steps."""
    import quantum_language as ql

    ql.circuit()

    walk_config = WalkConfig(
        max_depth=config.max_depth,
        num_moves=config.num_moves,
        is_marked=config.is_marked,
    )

    regs = WalkRegisters(walk_config)
    regs.init_root()

    for _ in range(num_steps):
        _marked_walk_step(walk_config, regs)

    qasm_str = ql.to_openqasm()
    sv = _simulate_statevector(qasm_str)

    h_root_qubit = regs.height_qubit(config.max_depth)
    root_idx = 1 << h_root_qubit
    return float(abs(sv[root_idx]) ** 2)


def _measure_root_overlap_unmarked(num_moves, max_depth, num_steps):
    """Root state probability after num_steps unmarked walk steps."""
    import quantum_language as ql

    ql.circuit()

    fixed_config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
    )
    regs = WalkRegisters(fixed_config)
    regs.init_root()

    for _ in range(num_steps):
        walk_step(fixed_config, regs)

    qasm_str = ql.to_openqasm()
    sv = _simulate_statevector(qasm_str)

    h_root_qubit = regs.height_qubit(max_depth)
    root_idx = 1 << h_root_qubit
    return float(abs(sv[root_idx]) ** 2)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def _validate_walk_args(is_marked, max_depth, num_moves,
                        max_iterations=None):
    """Validate arguments for the walk() public API."""
    if is_marked is None:
        raise ValueError("is_marked must not be None")
    if not isinstance(max_depth, int):
        raise TypeError(
            f"max_depth must be an int, got {type(max_depth).__name__}"
        )
    if not isinstance(num_moves, int):
        raise TypeError(
            f"num_moves must be an int, got {type(num_moves).__name__}"
        )
    if max_depth < 1:
        raise ValueError(f"max_depth must be >= 1, got {max_depth}")
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")
    if max_iterations is not None:
        if not isinstance(max_iterations, int):
            raise TypeError(
                f"max_iterations must be an int, got "
                f"{type(max_iterations).__name__}"
            )
        if max_iterations < 1:
            raise ValueError(
                f"max_iterations must be >= 1, got {max_iterations}"
            )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def walk(is_marked, max_depth, num_moves, *, state=None,
         make_move=None, is_valid=None, max_iterations=None):
    """Quantum walk search: detect whether a marked node exists.

    Implements a quantum walk-based detection algorithm for marked
    nodes in a backtracking tree.  The marking oracle is evaluated
    classically on branch register patterns, and a phase flip is
    applied at the leaf level of the walk step.

    The algorithm compares root overlap of the marked walk to the
    unmarked baseline across multiple power levels.  If the marking
    causes the root overlap to diverge from the baseline, a marked
    node is detected.

    .. note::

        This module currently uses fixed-branching walk operators.
        The ``state``, ``make_move``, and ``is_valid`` parameters
        are accepted for API compatibility with future variable-
        branching support but are not used in the current
        implementation.

    Parameters
    ----------
    is_marked : callable
        Predicate ``is_marked(value)`` returning bool.  Called with
        integer values representing branch register patterns at the
        leaf level.
    max_depth : int
        Maximum depth of the backtracking tree (>= 1).
    num_moves : int
        Maximum branching factor at any node (>= 1).
    state : qint or qarray, optional
        Quantum register representing the problem state.  Reserved
        for future variable-branching support; not used currently.
    make_move : callable, optional
        Function ``make_move(state, move_index)`` that transforms
        state by applying a move.  Reserved for future variable-
        branching support; not used currently.
    is_valid : callable, optional
        Quantum predicate ``is_valid(state)`` returning ``qbool``.
        Reserved for future variable-branching support; not used
        currently.
    max_iterations : int, optional
        Maximum walk step iterations (>= 1).  Auto-computed from
        tree size as ``ceil(sqrt(T / n))`` if not provided.

    Returns
    -------
    bool
        True if a marked node is detected, False otherwise.

    Raises
    ------
    ValueError
        If ``is_marked`` is None, or depth/moves < 1, or
        ``max_iterations`` < 1.
    TypeError
        If ``max_depth``, ``num_moves``, or ``max_iterations`` are
        not int.
    """
    _validate_walk_args(is_marked, max_depth, num_moves,
                        max_iterations=max_iterations)

    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        is_marked=is_marked,
    )

    if max_iterations is None:
        max_iterations = _max_walk_iterations(num_moves, max_depth)

    # Detection threshold: if overlap difference exceeds this,
    # the marking has a detectable effect on the walk dynamics.
    detection_threshold = 1e-4

    # Iterative power-method detection
    power = 1
    while power <= max_iterations:
        marked_overlap = _measure_root_overlap(config, power)
        baseline_overlap = _measure_root_overlap_unmarked(
            num_moves, max_depth, power,
        )
        diff = abs(marked_overlap - baseline_overlap)
        if diff > detection_threshold:
            return True  # Marking changed walk dynamics
        power *= 2

    return False  # No detectable effect from marking
