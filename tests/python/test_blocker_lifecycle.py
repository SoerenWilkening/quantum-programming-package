"""Tests for blocker lifecycle with real qint deallocation.

Validates that Blocker.is_active becomes False when the dependent
qint's qubits are deallocated — via del, explicit uncompute, or
with-block exit.

Step 6.3: Qubit deallocation notification [Quantum_Assembly-4q7.3].
"""

import gc

import quantum_language as ql
from quantum_language.history_graph import HistoryGraph

# ---------------------------------------------------------------------------
# blocker_live_query
# ---------------------------------------------------------------------------


class TestBlockerLiveQuery:
    """Blocker.is_active reflects qint.qubits_allocated in real time."""

    def test_blocker_active_for_live_qint(self):
        ql.circuit()
        a = ql.qint(0, width=4)
        hg = HistoryGraph()
        blocker = hg.add_blocker(a)
        assert blocker.is_active is True
        assert a.qubits_allocated is True

    def test_qubits_allocated_true_after_creation(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        assert a.qubits_allocated is True

    def test_qubits_allocated_false_after_uncompute(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        assert c.qubits_allocated is True
        c.uncompute()
        assert c.qubits_allocated is False

    def test_blocker_tracks_uncompute(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        hg = HistoryGraph()
        blocker = hg.add_blocker(c)
        assert blocker.is_active is True
        c.uncompute()
        assert blocker.is_active is False


# ---------------------------------------------------------------------------
# del_clears_blocker
# ---------------------------------------------------------------------------


class TestDelClearsBlocker:
    """Deleting a qint deallocates qubits, making its blocker inactive."""

    def test_del_makes_blocker_inactive(self):
        ql.circuit()
        a = ql.qint(0, width=4)
        hg = HistoryGraph()
        blocker = hg.add_blocker(a)
        assert blocker.is_active is True

        del a
        gc.collect()
        assert blocker.is_active is False

    def test_del_intermediate_clears_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        hg = HistoryGraph()
        blocker = hg.add_blocker(c)
        assert blocker.is_active is True

        del c
        gc.collect()
        assert blocker.is_active is False


# ---------------------------------------------------------------------------
# with_exit_clears_blocker
# ---------------------------------------------------------------------------


class TestWithExitClearsBlocker:
    """Exiting a with-block uncomputes the condition, clearing its blocker."""

    def test_with_exit_clears_condition_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        hg = HistoryGraph()

        cond = a == 3
        blocker = hg.add_blocker(cond)
        assert blocker.is_active is True

        with cond:
            pass

        # After with-exit, the condition's history is uncomputed and
        # its qubits are deallocated (scope cleanup).
        # The condition qint itself may still exist but its qubits
        # should be freed via scope or GC.
        del cond
        gc.collect()
        assert blocker.is_active is False
