"""Tests for HistoryGraph data structure.

Validates append/reverse ordering, weakref alive/dead semantics,
empty history on fresh qint, and discard behavior.

Step 1.1 of Phase 1: Per-Variable History Graph [Quantum_Assembly-2ab.1].
"""

import gc

import quantum_language as ql
from quantum_language.history_graph import HistoryGraph


# ---------------------------------------------------------------------------
# Pure data-structure tests (no circuit required)
# ---------------------------------------------------------------------------


class TestAppendAndReverse:
    """Entries come back in reverse insertion order."""

    def test_append_and_reverse(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1, 2))
        hg.append(200, (3, 4))
        hg.append(300, (5,))

        reversed_list = list(hg.reversed_entries())
        assert reversed_list == [
            (300, (5,)),
            (200, (3, 4)),
            (100, (0, 1, 2)),
        ]

    def test_single_entry_reverse(self):
        hg = HistoryGraph()
        hg.append(42, (7, 8))
        reversed_list = list(hg.reversed_entries())
        assert reversed_list == [(42, (7, 8))]

    def test_entries_preserve_insertion_order(self):
        hg = HistoryGraph()
        for i in range(5):
            hg.append(i * 10, (i,))
        assert hg.entries == [(i * 10, (i,)) for i in range(5)]


class TestLen:
    """__len__ reports number of entries."""

    def test_empty(self):
        hg = HistoryGraph()
        assert len(hg) == 0

    def test_after_appends(self):
        hg = HistoryGraph()
        hg.append(1, (0,))
        hg.append(2, (1,))
        assert len(hg) == 2


class TestBool:
    """__bool__ is False for empty, True otherwise."""

    def test_empty_is_falsy(self):
        hg = HistoryGraph()
        assert not hg

    def test_nonempty_is_truthy(self):
        hg = HistoryGraph()
        hg.append(1, (0,))
        assert hg


# ---------------------------------------------------------------------------
# Weakref child tracking
# ---------------------------------------------------------------------------


class _Dummy:
    """Weakref-able placeholder used instead of real qint in pure tests."""
    pass


class TestChildWeakrefAlive:
    """Weakref resolves when child is still alive."""

    def test_child_weakref_alive(self):
        hg = HistoryGraph()
        child = _Dummy()
        hg.add_child(child)

        alive = hg.live_children()
        assert len(alive) == 1
        assert alive[0] is child

    def test_multiple_children_alive(self):
        hg = HistoryGraph()
        c1 = _Dummy()
        c2 = _Dummy()
        hg.add_child(c1)
        hg.add_child(c2)

        alive = hg.live_children()
        assert len(alive) == 2


class TestChildWeakrefDead:
    """Weakref returns None after child is deleted."""

    def test_child_weakref_dead(self):
        hg = HistoryGraph()
        child = _Dummy()
        hg.add_child(child)

        del child
        gc.collect()

        alive = hg.live_children()
        assert len(alive) == 0

    def test_mixed_alive_and_dead(self):
        hg = HistoryGraph()
        c1 = _Dummy()
        c2 = _Dummy()
        hg.add_child(c1)
        hg.add_child(c2)

        del c1
        gc.collect()

        alive = hg.live_children()
        assert len(alive) == 1
        assert alive[0] is c2


# ---------------------------------------------------------------------------
# Discard (measurement trigger)
# ---------------------------------------------------------------------------


class TestDiscard:
    """discard() clears entries and children."""

    def test_discard_clears_entries(self):
        hg = HistoryGraph()
        hg.append(1, (0,))
        hg.append(2, (1,))
        hg.discard()
        assert len(hg) == 0
        assert list(hg.reversed_entries()) == []

    def test_discard_clears_children(self):
        hg = HistoryGraph()
        child = _Dummy()
        hg.add_child(child)
        hg.discard()
        assert hg.live_children() == []
        assert len(hg.children) == 0

    def test_discard_on_empty(self):
        hg = HistoryGraph()
        hg.discard()  # should not raise
        assert len(hg) == 0


# ---------------------------------------------------------------------------
# Integration: qint/qbool carry history attribute
# ---------------------------------------------------------------------------


class TestQintEmptyHistory:
    """New qint has an empty HistoryGraph."""

    def test_empty_history(self):
        ql.circuit()
        a = ql.qint(0, width=4)
        assert isinstance(a.history, HistoryGraph)
        assert len(a.history) == 0
        assert not a.history

    def test_qbool_empty_history(self):
        ql.circuit()
        b = ql.qbool(False)
        assert isinstance(b.history, HistoryGraph)
        assert len(b.history) == 0

    def test_qint_with_value_empty_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        # Initialization X gates are not recorded in the history graph.
        # Only arithmetic/comparison/bitwise operations will record.
        assert len(a.history) == 0

    def test_qint_bitlist_empty_history(self):
        """qint created via bit_list also has empty history."""
        ql.circuit()
        import numpy as np
        bl = np.zeros(64, dtype=np.uint32)
        a = ql.qint(0, width=4, create_new=False, bit_list=bl)
        assert isinstance(a.history, HistoryGraph)
        assert len(a.history) == 0
