"""Walk core types and Montanaro angle computation.

Configuration dataclass, rotation angle formulas, and register width
helpers for the function-based quantum walk API.  All subsequent walk
modules (registers, counting, branching, diffusion, operators, search)
depend on this foundation.

Angle formulas follow Montanaro 2015, Section 2:

- Parent-children split:  phi(d) = 2 * arctan(sqrt(d))
- Cascade angles:         theta_k(d) = 2 * arctan(sqrt(1 / (d - 1 - k)))
                          for k = 0 .. d - 2
- Root special case:      phi_root(d, n) = 2 * arctan(sqrt(n * d))

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ------------------------------------------------------------------
# Register width helpers
# ------------------------------------------------------------------


def branch_width(num_moves):
    """Compute branch register width for a given number of moves.

    The branch register must hold values 0 .. num_moves - 1, so it
    needs ceil(log2(num_moves)) qubits, with a minimum of 1 qubit.

    Parameters
    ----------
    num_moves : int
        Maximum number of moves (children) at any node.

    Returns
    -------
    int
        Width in qubits.

    Raises
    ------
    TypeError
        If *num_moves* is not an int.
    ValueError
        If *num_moves* < 1.
    """
    if not isinstance(num_moves, int):
        raise TypeError(f"num_moves must be an int, got {type(num_moves).__name__}")
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")
    if num_moves == 1:
        return 1
    return max(1, math.ceil(math.log2(num_moves)))


def count_width(num_moves):
    """Compute count register width for a given number of moves.

    The count register stores values 0 .. num_moves (inclusive),
    so it needs ceil(log2(num_moves + 1)) qubits.

    Parameters
    ----------
    num_moves : int
        Maximum number of moves (children) at any node.

    Returns
    -------
    int
        Width in qubits.

    Raises
    ------
    TypeError
        If *num_moves* is not an int.
    ValueError
        If *num_moves* < 1.
    """
    if not isinstance(num_moves, int):
        raise TypeError(f"num_moves must be an int, got {type(num_moves).__name__}")
    if num_moves < 1:
        raise ValueError(f"num_moves must be >= 1, got {num_moves}")
    return math.ceil(math.log2(num_moves + 1))


# ------------------------------------------------------------------
# Montanaro angle formulas
# ------------------------------------------------------------------


def montanaro_phi(d):
    """Parent-children split angle for *d* valid children.

    phi(d) = 2 * arctan(sqrt(d))

    After applying Ry(phi) to the height qubit, the amplitude splits
    between the parent component (cos(phi/2)) and the children component
    (sin(phi/2)).

    Parameters
    ----------
    d : int
        Number of valid children (>= 1).

    Returns
    -------
    float
        Rotation angle in radians.

    Raises
    ------
    ValueError
        If *d* < 1.
    """
    if d < 1:
        raise ValueError(f"d must be >= 1, got {d}")
    return 2.0 * math.atan(math.sqrt(d))


def montanaro_cascade_angles(d):
    """Cascade angles distributing amplitude among *d* children.

    theta_k(d) = 2 * arctan(sqrt(1 / (d - 1 - k)))  for k = 0 .. d - 2

    These rotations, applied sequentially to the branch register qubits,
    produce a uniform superposition over *d* states.

    Parameters
    ----------
    d : int
        Number of valid children (>= 1).

    Returns
    -------
    list[float]
        Cascade angles (length d - 1).  Empty list when d == 1.

    Raises
    ------
    ValueError
        If *d* < 1.
    """
    if d < 1:
        raise ValueError(f"d must be >= 1, got {d}")
    angles = []
    for k in range(d - 1):
        remaining = d - 1 - k  # ranges from d-1 down to 1, always > 0
        angles.append(2.0 * math.atan(math.sqrt(1.0 / remaining)))
    return angles


def montanaro_angles(d):
    """All Montanaro rotation angles for *d* valid children.

    Returns both the parent-children split angle (phi) and the cascade
    angles (theta) as a dict.

    Parameters
    ----------
    d : int
        Number of valid children (>= 1).

    Returns
    -------
    dict
        ``{"phi": float, "cascade": list[float]}``
    """
    return {
        "phi": montanaro_phi(d),
        "cascade": montanaro_cascade_angles(d),
    }


def root_angle(d, n):
    """Root-level split angle (Montanaro special case).

    phi_root(d, n) = 2 * arctan(sqrt(n * d))

    At the root, the split angle accounts for the tree size *n*
    (max_depth) to ensure the correct overlap threshold for detection.

    Parameters
    ----------
    d : int
        Number of valid children at the root (>= 1).
    n : int
        Tree depth (max_depth, >= 1).

    Returns
    -------
    float
        Root rotation angle in radians.

    Raises
    ------
    ValueError
        If *d* < 1 or *n* < 1.
    """
    if d < 1:
        raise ValueError(f"d must be >= 1, got {d}")
    if n < 1:
        raise ValueError(f"n (max_depth) must be >= 1, got {n}")
    return 2.0 * math.atan(math.sqrt(n * d))


# ------------------------------------------------------------------
# WalkConfig dataclass
# ------------------------------------------------------------------


@dataclass
class WalkConfig:
    """Configuration for a quantum walk instance.

    Carries user-provided parameters (state register, callbacks, tree
    shape) and derived register widths.  Validates inputs at creation.

    Parameters
    ----------
    max_depth : int
        Maximum depth of the backtracking tree (>= 1).
    num_moves : int
        Maximum number of moves (branching factor) at any node (>= 1).
    make_move : callable, optional
        ``@ql.compile(inverse=True)`` function transforming state by a
        classical move index.
    undo_move : callable, optional
        Explicit inverse of ``make_move``.  If not provided, the counting
        module falls back to ``make_move.adjoint``.
    is_valid : callable, optional
        Quantum predicate returning ``qbool``.
    is_marked : callable, optional
        Quantum predicate returning ``qbool`` (only for full walk).
    state : object, optional
        Quantum register (qarray / qint) representing the problem state.

    Attributes
    ----------
    bw : int
        Branch register width (qubits per depth level).
    cw : int
        Count register width.
    hw : int
        Height register width (max_depth + 1, one-hot).
    """

    max_depth: int
    num_moves: int
    make_move: Optional[Callable] = None
    undo_move: Optional[Callable] = None
    is_valid: Optional[Callable] = None
    is_marked: Optional[Callable] = None
    state: Optional[Any] = None

    # Derived (computed in __post_init__)
    bw: int = field(init=False)
    cw: int = field(init=False)
    hw: int = field(init=False)

    def __post_init__(self):
        if not isinstance(self.max_depth, int):
            raise TypeError(
                f"max_depth must be an int, got {type(self.max_depth).__name__}"
            )
        if not isinstance(self.num_moves, int):
            raise TypeError(
                f"num_moves must be an int, got {type(self.num_moves).__name__}"
            )
        if self.max_depth < 1:
            raise ValueError(
                f"max_depth must be >= 1, got {self.max_depth}"
            )
        if self.num_moves < 1:
            raise ValueError(
                f"num_moves must be >= 1, got {self.num_moves}"
            )

        self.bw = branch_width(self.num_moves)
        self.cw = count_width(self.num_moves)
        self.hw = self.max_depth + 1

    def total_walk_qubits(self):
        """Total qubits used by framework-internal walk registers.

        height:  hw  =  max_depth + 1        (one-hot)
        branch:  bw * max_depth              (one register per depth)
        count:   cw                           (temporary)

        Does **not** include the user's state register.

        Returns
        -------
        int
            Total qubit count for walk machinery.
        """
        return self.hw + self.bw * self.max_depth + self.cw

    def root_phi(self):
        """Root-level split angle for this configuration.

        Uses the branching factor (num_moves) and tree depth (max_depth).

        Returns
        -------
        float
            Root rotation angle in radians.
        """
        return root_angle(self.num_moves, self.max_depth)

    def angles_for(self, d):
        """Montanaro angles for *d* valid children.

        Convenience wrapper around :func:`montanaro_angles`.

        Parameters
        ----------
        d : int
            Number of valid children.

        Returns
        -------
        dict
            ``{"phi": float, "cascade": list[float]}``
        """
        return montanaro_angles(d)
