"""Quantum walk search: build marked walk configuration (Montanaro 2015).

Public API: ``walk(is_marked, max_depth, num_moves, state, make_move, is_valid, *, max_iterations=None)``

Builds a :class:`WalkConfig` with the ``is_marked`` predicate set and
allocates walk registers ready for use with :func:`walk_step`.  The
marking predicate is evaluated **quantumly** via the infrastructure in
``walk_operators._apply_local_diffusion``: marked nodes receive identity
(D_x = I), unmarked nodes receive the standard diffusion operator.

.. todo::

    Detection via quantum phase estimation is a future milestone.
    The current ``walk()`` returns ``(config, registers)`` for use
    with ``walk_step``; a future version will wrap this in a phase
    estimation routine to detect whether any marked node exists
    (Montanaro 2015, Theorem 1).

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

import math

from .walk_core import WalkConfig
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
# Validation
# ------------------------------------------------------------------


def _validate_walk_args(
    is_marked, max_depth, num_moves, state, make_move, is_valid, max_iterations=None
):
    """Validate arguments for the walk() public API."""
    if is_marked is None:
        raise ValueError("is_marked must not be None")
    if not isinstance(max_depth, int):
        raise TypeError(f"max_depth must be an int, got {type(max_depth).__name__}")
    if not isinstance(num_moves, int):
        raise TypeError(f"num_moves must be an int, got {type(num_moves).__name__}")
    if max_depth < 1:
        raise ValueError(f"max_depth must be >= 1, got {max_depth}")
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")
    if state is None:
        raise ValueError("state must not be None")
    if make_move is None:
        raise ValueError("make_move must not be None")
    if is_valid is None:
        raise ValueError("is_valid must not be None")
    if max_iterations is not None:
        if not isinstance(max_iterations, int):
            raise TypeError(f"max_iterations must be an int, got {type(max_iterations).__name__}")
        if max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1, got {max_iterations}")


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def walk(
    is_marked,
    max_depth,
    num_moves,
    state,
    make_move,
    is_valid,
    *,
    undo_move=None,
    max_iterations=None,
):
    """Build a marked quantum walk configuration with allocated registers.

    Creates a :class:`WalkConfig` with ``is_marked`` set and allocates
    :class:`WalkRegisters` initialized at the root state.  The returned
    pair ``(config, registers)`` is ready for use with :func:`walk_step`.

    The ``is_marked`` predicate is evaluated **quantumly** during
    ``walk_step``: for each node, ``is_marked(state)`` returns a
    ``qbool``, and marked nodes receive identity (D_x = I) while
    unmarked nodes receive the standard diffusion operator (per
    Montanaro 2015).

    .. todo::

        Detection via quantum phase estimation is a future milestone.
        Currently this function returns ``(config, registers)`` for
        manual walk step iteration.  A future version will wrap the
        walk in a phase estimation routine to detect whether any
        marked node exists (Montanaro 2015, Theorem 1).

    Parameters
    ----------
    is_marked : callable
        Quantum predicate ``is_marked(state)`` returning ``qbool``.
        Evaluated quantumly during walk steps to distinguish marked
        nodes (identity) from unmarked nodes (diffusion).
    max_depth : int
        Maximum depth of the backtracking tree (>= 1).
    num_moves : int
        Maximum branching factor at any node (>= 1).
    state : qint or qarray
        Quantum register representing the problem state.
    make_move : callable
        Function ``make_move(state, move_index)`` that transforms
        state by applying a move.
    is_valid : callable
        Quantum predicate ``is_valid(state)`` returning ``qbool``.
    undo_move : callable, optional
        Explicit inverse of ``make_move``.  If not provided, the
        diffusion falls back to ``make_move.inverse``.
    max_iterations : int, optional
        Maximum walk step iterations (>= 1).  Auto-computed from
        tree size as ``ceil(sqrt(T / n))`` if not provided.

    Returns
    -------
    tuple[WalkConfig, WalkRegisters]
        A ``(config, registers)`` pair.  The config has ``is_marked``
        set and registers are initialized at the root.  Use with
        :func:`walk_step` to apply walk iterations.

    Raises
    ------
    ValueError
        If ``is_marked``, ``state``, ``make_move``, or ``is_valid``
        is None, or depth/moves < 1, or ``max_iterations`` < 1.
    TypeError
        If ``max_depth``, ``num_moves``, or ``max_iterations`` are
        not int.
    """
    _validate_walk_args(
        is_marked, max_depth, num_moves, state, make_move, is_valid, max_iterations=max_iterations
    )

    if max_iterations is None:
        max_iterations = _max_walk_iterations(num_moves, max_depth)

    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        is_marked=is_marked,
        state=state,
        make_move=make_move,
        undo_move=undo_move,
        is_valid=is_valid,
    )

    registers = WalkRegisters(config)
    registers.init_root()

    return config, registers
