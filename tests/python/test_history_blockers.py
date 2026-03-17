"""Tests for Blocker data structure in HistoryGraph.

Validates that blockers track dependent qint liveness via weakrefs
and that add_blocker / active_blockers_after work correctly.

Step 6.1: Blocker data structure [Quantum_Assembly-4q7.1].
"""

import gc

import quantum_language as ql
from quantum_language.history_graph import Blocker, HistoryGraph

# ---------------------------------------------------------------------------
# Helper: weakref-able dummy with qubits_allocated property
# ---------------------------------------------------------------------------


class _Dummy:
    """Weakref-able placeholder simulating a qint with qubits_allocated."""

    def __init__(self, allocated=True):
        self._allocated = allocated

    @property
    def qubits_allocated(self):
        return self._allocated

    @qubits_allocated.setter
    def qubits_allocated(self, value):
        self._allocated = value


# ---------------------------------------------------------------------------
# blocker_active_while_allocated
# ---------------------------------------------------------------------------


class TestBlockerActiveWhileAllocated:
    """Blocker reports active when dependent's qubits are still allocated."""

    def test_blocker_active_while_allocated(self):
        dep = _Dummy(allocated=True)
        blocker = Blocker(dep, index=0)
        assert blocker.is_active is True

    def test_blocker_dependent_accessible(self):
        dep = _Dummy(allocated=True)
        blocker = Blocker(dep, index=0)
        assert blocker.dependent is dep

    def test_blocker_index_stored(self):
        dep = _Dummy(allocated=True)
        blocker = Blocker(dep, index=5)
        assert blocker.index == 5


# ---------------------------------------------------------------------------
# blocker_inactive_after_deallocation
# ---------------------------------------------------------------------------


class TestBlockerInactiveAfterDeallocation:
    """Blocker reports inactive after dependent is deallocated or GC'd."""

    def test_blocker_inactive_after_flag_cleared(self):
        dep = _Dummy(allocated=True)
        blocker = Blocker(dep, index=0)
        assert blocker.is_active is True

        dep.qubits_allocated = False
        assert blocker.is_active is False

    def test_blocker_inactive_after_gc(self):
        dep = _Dummy(allocated=True)
        blocker = Blocker(dep, index=0)
        assert blocker.is_active is True

        del dep
        gc.collect()
        assert blocker.is_active is False
        assert blocker.dependent is None


# ---------------------------------------------------------------------------
# add_blocker
# ---------------------------------------------------------------------------


class TestAddBlocker:
    """HistoryGraph.add_blocker creates and stores a Blocker."""

    def test_add_blocker_returns_blocker(self):
        hg = HistoryGraph()
        dep = _Dummy()
        blocker = hg.add_blocker(dep)
        assert isinstance(blocker, Blocker)

    def test_add_blocker_stored_in_list(self):
        hg = HistoryGraph()
        dep = _Dummy()
        blocker = hg.add_blocker(dep)
        assert blocker in hg.blockers

    def test_add_blocker_index_matches_entry_count(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1))
        hg.append(200, (2, 3))
        dep = _Dummy()
        blocker = hg.add_blocker(dep)
        assert blocker.index == 2

    def test_add_blocker_empty_entries(self):
        hg = HistoryGraph()
        dep = _Dummy()
        blocker = hg.add_blocker(dep)
        assert blocker.index == 0

    def test_add_blocker_is_active(self):
        hg = HistoryGraph()
        dep = _Dummy(allocated=True)
        blocker = hg.add_blocker(dep)
        assert blocker.is_active is True


# ---------------------------------------------------------------------------
# active_blockers_after
# ---------------------------------------------------------------------------


class TestActiveBlockersAfter:
    """active_blockers_after returns active blockers at or after index."""

    def test_all_blockers_after_zero(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        d2 = _Dummy(allocated=True)
        hg.add_blocker(d1)
        hg.append(100, (0,))
        hg.add_blocker(d2)

        active = hg.active_blockers_after(0)
        assert len(active) == 2

    def test_filter_by_index(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        hg.add_blocker(d1)  # index=0
        hg.append(100, (0,))
        hg.append(200, (1,))
        d2 = _Dummy(allocated=True)
        hg.add_blocker(d2)  # index=2

        active = hg.active_blockers_after(1)
        assert len(active) == 1
        assert active[0].dependent is d2

    def test_filter_inactive(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        d2 = _Dummy(allocated=False)
        hg.add_blocker(d1)
        hg.add_blocker(d2)

        active = hg.active_blockers_after(0)
        assert len(active) == 1
        assert active[0].dependent is d1

    def test_empty_when_no_blockers(self):
        hg = HistoryGraph()
        hg.append(100, (0,))
        assert hg.active_blockers_after(0) == []

    def test_empty_when_all_deallocated(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        hg.add_blocker(d1)
        d1.qubits_allocated = False
        assert hg.active_blockers_after(0) == []

    def test_index_boundary_inclusive(self):
        hg = HistoryGraph()
        dep = _Dummy(allocated=True)
        hg.append(100, (0,))
        hg.add_blocker(dep)  # index=1
        # Exactly at the boundary
        active = hg.active_blockers_after(1)
        assert len(active) == 1
        # Just past the boundary
        active = hg.active_blockers_after(2)
        assert len(active) == 0


# ---------------------------------------------------------------------------
# multiple_blockers
# ---------------------------------------------------------------------------


class TestMultipleBlockers:
    """Multiple blockers can coexist and be independently active/inactive."""

    def test_multiple_blockers_all_active(self):
        hg = HistoryGraph()
        deps = [_Dummy(allocated=True) for _ in range(3)]
        for d in deps:
            hg.add_blocker(d)
        assert len(hg.active_blockers_after(0)) == 3

    def test_multiple_blockers_partial_deallocation(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        d2 = _Dummy(allocated=True)
        d3 = _Dummy(allocated=True)
        hg.add_blocker(d1)
        hg.add_blocker(d2)
        hg.add_blocker(d3)

        d2.qubits_allocated = False
        active = hg.active_blockers_after(0)
        assert len(active) == 2
        dependents = [b.dependent for b in active]
        assert d1 in dependents
        assert d3 in dependents
        assert d2 not in dependents

    def test_multiple_blockers_all_deallocated(self):
        hg = HistoryGraph()
        deps = [_Dummy(allocated=True) for _ in range(3)]
        for d in deps:
            hg.add_blocker(d)
        for d in deps:
            d.qubits_allocated = False
        assert hg.active_blockers_after(0) == []

    def test_multiple_blockers_at_different_indices(self):
        hg = HistoryGraph()
        d1 = _Dummy(allocated=True)
        hg.add_blocker(d1)  # index=0
        hg.append(100, (0,))
        d2 = _Dummy(allocated=True)
        hg.add_blocker(d2)  # index=1
        hg.append(200, (1,))
        d3 = _Dummy(allocated=True)
        hg.add_blocker(d3)  # index=2

        assert len(hg.active_blockers_after(0)) == 3
        assert len(hg.active_blockers_after(1)) == 2
        assert len(hg.active_blockers_after(2)) == 1
        assert len(hg.active_blockers_after(3)) == 0

    def test_discard_clears_blockers(self):
        hg = HistoryGraph()
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        assert len(hg.blockers) == 1
        hg.discard()
        assert len(hg.blockers) == 0


# ---------------------------------------------------------------------------
# Integration: blocker with real qint
# ---------------------------------------------------------------------------


class TestBlockerWithQint:
    """Blocker tracks a real qint's allocation status."""

    def test_blocker_active_with_real_qint(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        hg = HistoryGraph()
        blocker = hg.add_blocker(a)
        assert blocker.is_active is True

    def test_blocker_inactive_after_qint_uncompute(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        hg = HistoryGraph()
        blocker = hg.add_blocker(c)
        assert blocker.is_active is True

        c.uncompute()
        assert blocker.is_active is False
