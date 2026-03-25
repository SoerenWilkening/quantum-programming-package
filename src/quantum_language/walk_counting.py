"""Move counting for quantum walk: count valid children at the current node.

Implements the apply-check-undo loop that counts how many of the possible
moves (children) at a node are valid.  The count is accumulated into a
quantum register so that each basis state of the problem state gets its
own count value in superposition.

Algorithm
---------
For each move index i in 0 .. num_moves - 1:
    1. Apply make_move(state, i) -- transform state to the i-th child
    2. Evaluate is_valid(state) -- returns a qbool
    3. Controlled on the validity flag: count += 1
    4. Uncompute is_valid (automatic via history graph or adjoint)
    5. Undo the move via undo_move(state, i) or make_move.inverse(state, i)

After the loop, ``count_reg`` holds the number of valid children for
each basis state of ``state``.  The state register is restored to its
original value.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374), Section 3.
"""

from .walk_core import WalkConfig


def _get_undo_fn(config):
    """Determine the undo function for make_move.

    Uses ``config.undo_move`` if set, otherwise falls back to
    ``config.make_move.inverse``.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration.

    Returns
    -------
    callable
        Function ``f(state, move_idx)`` that undoes the move.

    Raises
    ------
    AttributeError
        If neither ``undo_move`` nor ``make_move.inverse`` is available.
    """
    undo = getattr(config, "undo_move", None)
    if undo is not None:
        return undo
    return config.make_move.inverse


def count_valid_children(config, count_reg):
    """Count how many children of the current node are valid.

    For each move index ``i`` in ``range(config.num_moves)``, applies the
    move, checks validity, conditionally increments ``count_reg``, then
    undoes the move.  After the call, ``count_reg`` contains the number
    of valid children and ``config.state`` is unchanged.

    The undo is performed by ``config.undo_move(state, i)`` if available,
    otherwise by ``config.make_move.inverse(state, i)``.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration carrying ``state``, ``make_move``, ``is_valid``,
        and ``num_moves``.  Optionally carries ``undo_move``.
    count_reg : qint
        Quantum integer register (initially zero) that receives the count.
        Must be wide enough to hold values 0 .. num_moves (see
        :func:`~walk_core.count_width`).

    Raises
    ------
    ValueError
        If ``config.make_move`` or ``config.is_valid`` is None.
    TypeError
        If ``config`` is not a ``WalkConfig``.
    """
    _validate_config(config)

    state = config.state
    make_move = config.make_move
    is_valid = config.is_valid
    num_moves = config.num_moves
    undo_move = _get_undo_fn(config)

    for i in range(num_moves):
        # 1. Apply move i to the state
        make_move(state, i)

        # 2. Evaluate validity predicate
        valid = is_valid(state)

        # 3. Conditionally increment count
        with valid:
            count_reg += 1

        # 4. valid is uncomputed automatically when its refcount drops
        #    (Phase 1 history-graph uncomputation handles this)

        # 5. Undo the move to restore state
        undo_move(state, i)


def uncount_valid_children(config, count_reg):
    """Inverse of :func:`count_valid_children`.

    Applies the counting loop in reverse order (move indices from
    ``num_moves - 1`` down to 0) with decrements instead of increments.
    After the call, ``count_reg`` is restored to zero and ``config.state``
    is unchanged.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration (same as for :func:`count_valid_children`).
    count_reg : qint
        Quantum integer register containing the count to be undone.
    """
    _validate_config(config)

    state = config.state
    make_move = config.make_move
    is_valid = config.is_valid
    num_moves = config.num_moves
    undo_move = _get_undo_fn(config)

    for i in reversed(range(num_moves)):
        # Undo in reverse order: move, check, decrement, undo move
        make_move(state, i)

        valid = is_valid(state)

        with valid:
            count_reg -= 1

        undo_move(state, i)


def _validate_config(config):
    """Validate that the config has the required callbacks and state.

    Parameters
    ----------
    config : WalkConfig
        Configuration to validate.

    Raises
    ------
    TypeError
        If *config* is not a ``WalkConfig``.
    ValueError
        If ``make_move``, ``is_valid``, or ``state`` is None.
    """
    if not isinstance(config, WalkConfig):
        raise TypeError(f"config must be a WalkConfig, got {type(config).__name__}")
    if config.make_move is None:
        raise ValueError("config.make_move must not be None")
    if config.is_valid is None:
        raise ValueError("config.is_valid must not be None")
    if config.state is None:
        raise ValueError("config.state must not be None")
