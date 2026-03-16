"""Walk register management: allocate and manage quantum walk registers.

Provides the ``WalkRegisters`` class that allocates the framework-internal
registers used by the quantum walk algorithm:

- **height** register: one-hot qbool array (max_depth + 1 qubits), where
  ``height[k]`` being |1> means the walk is at depth k.
- **branch** registers: one qint per depth level (max_depth registers),
  each ``branch_width`` qubits wide, encoding the child index taken at
  that level.
- **count** register: a temporary qint (``count_width`` qubits) used
  during validity counting.

Register allocation matches :meth:`WalkConfig.total_walk_qubits`.

References
----------
    A. Montanaro, "Quantum speedup of backtracking algorithms",
    Theory of Computing, 2018 (arXiv:1509.02374).
"""

from .diffusion import _flip_all
from .walk_core import WalkConfig


class WalkRegisters:
    """Manages the quantum registers for a walk instance.

    Allocates height, branch, and count registers on construction.
    Provides helpers to initialize the root state, access branch
    registers by depth, and clean up.

    Parameters
    ----------
    config : WalkConfig
        Walk configuration with ``max_depth``, ``num_moves``, and
        derived register widths (``hw``, ``bw``, ``cw``).

    Attributes
    ----------
    config : WalkConfig
        The configuration used to create these registers.
    height : list[qbool]
        One-hot height register.  ``height[k]`` is |1> when the walk
        is at depth ``k``.  Length is ``max_depth + 1``.
    branches : list[qint]
        Per-depth branch registers.  ``branches[d]`` is the qint
        holding the child index at depth ``d`` (0-indexed from the
        leaves).  Length is ``max_depth``.
    count : qint
        Temporary count register for validity counting.

    Raises
    ------
    TypeError
        If *config* is not a ``WalkConfig``.
    """

    __slots__ = ("config", "height", "branches", "count", "_initialized",
                 "_cleaned_up")

    def __init__(self, config):
        if not isinstance(config, WalkConfig):
            raise TypeError(
                f"config must be a WalkConfig, got {type(config).__name__}"
            )

        import quantum_language as ql

        self.config = config
        self._initialized = False
        self._cleaned_up = False

        # Height register: one-hot qbool array (max_depth + 1 elements).
        # Each qbool is independently allocated and starts as |0>.
        self.height = [ql.qbool() for _ in range(config.hw)]

        # Branch registers: one qint per depth level, all start at 0.
        # branches[0] corresponds to depth 0 (leaf level),
        # branches[max_depth - 1] corresponds to depth max_depth - 1.
        self.branches = [
            ql.qint(0, width=config.bw)
            for _ in range(config.max_depth)
        ]

        # Count register: temporary qint for counting valid children.
        self.count = ql.qint(0, width=config.cw)

    def _check_cleaned_up(self):
        """Raise RuntimeError if cleanup() has been called."""
        if self._cleaned_up:
            raise RuntimeError("registers have been cleaned up")

    def init_root(self):
        """Set the height register to the root state.

        In the one-hot encoding, the root is at depth ``max_depth``.
        This sets ``height[max_depth]`` to |1> (via X gate) while all
        other height qubits and all branch registers remain at |0>.

        This method should be called exactly once after construction,
        before any walk operations.

        Raises
        ------
        RuntimeError
            If ``init_root`` has already been called, or if
            :meth:`cleanup` has been called.
        """
        self._check_cleaned_up()
        if self._initialized:
            raise RuntimeError("init_root() has already been called")

        root_idx = self.config.max_depth
        _flip_all(self.height[root_idx])
        self._initialized = True

    def branch_at(self, depth):
        """Return the branch register for a given depth.

        The branch register at depth ``d`` holds the child index taken
        when descending from depth ``d + 1`` to depth ``d``.

        Parameters
        ----------
        depth : int
            Depth level (0 = leaf level, max_depth - 1 = first branch
            below root).

        Returns
        -------
        qint
            Branch register for the given depth.

        Raises
        ------
        IndexError
            If *depth* is out of range ``[0, max_depth)``.
        TypeError
            If *depth* is not an int.
        RuntimeError
            If :meth:`cleanup` has been called.
        """
        self._check_cleaned_up()
        if not isinstance(depth, int):
            raise TypeError(
                f"depth must be an int, got {type(depth).__name__}"
            )
        if depth < 0 or depth >= self.config.max_depth:
            raise IndexError(
                f"depth must be in [0, {self.config.max_depth}), got {depth}"
            )
        return self.branches[depth]

    def height_qubit(self, depth):
        """Return the physical qubit index for the height bit at a given depth.

        Parameters
        ----------
        depth : int
            Depth level (0 .. max_depth inclusive).

        Returns
        -------
        int
            Physical qubit index for ``height[depth]``.

        Raises
        ------
        IndexError
            If *depth* is out of range ``[0, max_depth]``.
        TypeError
            If *depth* is not an int.
        RuntimeError
            If :meth:`cleanup` has been called.
        """
        self._check_cleaned_up()
        if not isinstance(depth, int):
            raise TypeError(
                f"depth must be an int, got {type(depth).__name__}"
            )
        if depth < 0 or depth > self.config.max_depth:
            raise IndexError(
                f"depth must be in [0, {self.config.max_depth}], got {depth}"
            )
        return int(self.height[depth].qubits[63])

    def current_depth(self):
        """Return the list of height qbools for use in controlled operations.

        In a quantum walk, the current depth is in superposition.  The
        caller uses ``with height[d]:`` to condition operations on being
        at depth ``d``.

        Returns
        -------
        list[qbool]
            The height register (one-hot qbool array).

        Raises
        ------
        RuntimeError
            If :meth:`cleanup` has been called.
        """
        self._check_cleaned_up()
        return self.height

    def total_qubits(self):
        """Compute the total number of qubits used by these registers.

        Returns
        -------
        int
            Sum of height, branch, and count register widths.

        Raises
        ------
        RuntimeError
            If :meth:`cleanup` has been called.
        """
        self._check_cleaned_up()
        h_qubits = len(self.height)
        b_qubits = sum(br.width for br in self.branches)
        c_qubits = self.count.width
        return h_qubits + b_qubits + c_qubits

    def cleanup(self):
        """Release references to all registers.

        After cleanup, the registers are no longer accessible.  This
        allows the framework's automatic uncomputation to reclaim
        qubits when the registers go out of scope.

        The method clears the internal lists and sets the count register
        to None.  Calling any other method after cleanup raises
        ``RuntimeError``.
        """
        self.height = []
        self.branches = []
        self.count = None
        self._cleaned_up = True
