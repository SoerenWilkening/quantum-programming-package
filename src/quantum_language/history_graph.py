"""Per-variable history graph for automatic uncomputation.

Each qint/qbool carries a HistoryGraph that records the operations
(sequence_ptr, qubit_mapping) that produced it.  Children (intermediate
temporaries consumed during creation) are tracked via weakrefs so they
can be garbage-collected independently when no longer referenced
elsewhere.

The graph supports reverse iteration (for uncomputing in LIFO order)
and a discard() method (for measurement, where inverse gates are
meaningless because qubits have collapsed).
"""

import weakref


class Blocker:
    """A blocker prevents uncomputation while a dependent qint is alive.

    Holds a weakref to the dependent qint and the entry index at which
    it was inserted.  A blocker is "active" when the dependent qint
    still has allocated qubits; once the qint is deallocated (or
    garbage-collected), the blocker becomes inactive.

    Attributes
    ----------
    _ref : weakref.ref
        Weakref to the dependent qint.
    index : int
        Entry index at time of insertion (len(entries) when added).
    """

    __slots__ = ("_ref", "index")

    def __init__(self, dependent, index):
        self._ref = weakref.ref(dependent)
        self.index = index

    @property
    def is_active(self):
        """Return True if the dependent qint's qubits are still allocated."""
        obj = self._ref()
        if obj is None:
            return False
        return getattr(obj, "allocated_qubits", False)

    @property
    def dependent(self):
        """Return the dependent object, or None if garbage-collected."""
        return self._ref()


class HistoryGraph:
    """Lightweight history of operations that produced a quantum variable.

    Attributes
    ----------
    entries : list[tuple]
        List of (sequence_ptr, qubit_mapping) tuples in insertion order.
    children : list[weakref.ref]
        Weakrefs to child variables consumed during creation.
    """

    __slots__ = ("entries", "children", "blockers")

    def __init__(self):
        self.entries = []
        self.children = []
        self.blockers = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def append(self, sequence_ptr, qubit_mapping, num_ancilla=0):
        """Record an operation entry.

        Parameters
        ----------
        sequence_ptr : int
            Pointer (as Python int) to the C ``sequence_t`` that was
            executed.
        qubit_mapping : tuple[int, ...]
            Qubit indices passed to ``run_instruction``.
        num_ancilla : int, optional
            Number of temporary ancilla qubits that must be allocated
            at the end of *qubit_mapping* when replaying the inverse.
            Default 0 (no ancilla needed).
        """
        self.entries.append((sequence_ptr, qubit_mapping, num_ancilla))

    def add_child(self, child):
        """Register *child* as a weakref dependency.

        Parameters
        ----------
        child : object
            A qint/qbool whose lifetime is tracked via weakref.
        """
        self.children.append(weakref.ref(child))

    def add_blocker(self, dependent):
        """Register a blocker for *dependent*.

        The blocker records the current entry count as its index and
        remains active as long as *dependent*'s qubits are allocated.

        Parameters
        ----------
        dependent : object
            A qint/qbool whose liveness gates uncomputation.

        Returns
        -------
        Blocker
            The newly created blocker.
        """
        blocker = Blocker(dependent, len(self.entries))
        self.blockers.append(blocker)
        return blocker

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def reversed_entries(self):
        """Yield entries in reverse (LIFO) order.

        Yields
        ------
        tuple
            (sequence_ptr, qubit_mapping) from newest to oldest.
        """
        return reversed(self.entries)

    # ------------------------------------------------------------------
    # Child access
    # ------------------------------------------------------------------

    def live_children(self):
        """Return list of children that are still alive.

        Returns
        -------
        list
            Dereferenced child objects (dead weakrefs are skipped).
        """
        alive = []
        for ref in self.children:
            obj = ref()
            if obj is not None:
                alive.append(obj)
        return alive

    # ------------------------------------------------------------------
    # Uncomputation
    # ------------------------------------------------------------------

    def uncompute(self, run_fn):
        """Uncompute all entries in reverse order, then cascade to children.

        Iterates entries newest-to-oldest, calling *run_fn* for each entry
        that has a real sequence pointer (non-zero).  After all entries are
        processed, cascades to orphaned children (alive weakrefs whose
        referent has a history with entries).

        Parameters
        ----------
        run_fn : callable(sequence_ptr, qubit_mapping, num_ancilla)
            Callback that executes ``run_instruction(seq, mapping,
            invert=True)`` on the active circuit, allocating fresh
            ancilla if *num_ancilla* > 0.  Provided by the Cython
            caller.
        """
        # 1. Reverse-iterate entries and invoke inverted run_instruction
        for seq_ptr, qubit_mapping, num_ancilla in self.reversed_entries():
            if seq_ptr != 0:
                run_fn(seq_ptr, qubit_mapping, num_ancilla)

        # 2. Clear own entries (idempotent: prevents double-uncompute)
        self.entries.clear()

        # 3. Cascade to orphaned children via weakrefs
        for ref in self.children:
            child = ref()
            if child is None:
                continue
            child_history = getattr(child, "history", None)
            if child_history is not None and child_history:
                child_history.uncompute(run_fn)

        # 4. Clear children list
        self.children.clear()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def discard(self):
        """Clear all entries, children, and blockers.

        Called on measurement — qubits have collapsed so inverse gates
        are physically meaningless.
        """
        self.entries.clear()
        self.children.clear()
        self.blockers.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active_blockers_after(self, index):
        """Return blockers inserted at or after *index* that are still active.

        Parameters
        ----------
        index : int
            Entry index threshold.  Only blockers whose ``index`` is
            >= this value are considered.

        Returns
        -------
        list[Blocker]
            Active blockers with ``blocker.index >= index``.
        """
        return [b for b in self.blockers if b.index >= index and b.is_active]

    def __len__(self):
        return len(self.entries)

    def __bool__(self):
        return len(self.entries) > 0
