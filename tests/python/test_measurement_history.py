"""Tests for measurement trigger: discard history on measurement.

When a qint/qbool is measured, its history graph is discarded because
qubits have collapsed and uncomputation is physically meaningless.

Step 1.5 of Phase 1: Measurement Trigger [Quantum_Assembly-2ab.5].
"""

import gc

import quantum_language as ql


# ---------------------------------------------------------------------------
# Test: measurement clears history
# ---------------------------------------------------------------------------


class TestMeasurementClearsHistory:
    """After measurement, the variable's history graph is empty."""

    def test_measurement_clears_history_qint(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        # Manually populate history to verify discard
        a.history.append(100, (0, 1))
        a.history.append(200, (2, 3))
        assert len(a.history) == 2

        a.measure()
        assert len(a.history) == 0
        assert not a.history

    def test_measurement_clears_history_qbool(self):
        ql.circuit()
        b = ql.qbool(True)
        b.history.append(300, (0,))
        assert len(b.history) == 1

        b.measure()
        assert len(b.history) == 0

    def test_measurement_returns_value(self):
        """measure() still returns the correct value after adding discard."""
        ql.circuit()
        a = ql.qint(7, width=4)
        result = a.measure()
        assert result == 7

    def test_measurement_on_empty_history(self):
        """Measuring a freshly created qint (no history) does not raise."""
        ql.circuit()
        a = ql.qint(0, width=4)
        assert len(a.history) == 0
        result = a.measure()
        assert result == 0
        assert len(a.history) == 0


# ---------------------------------------------------------------------------
# Test: measured variable no __del__ uncompute
# ---------------------------------------------------------------------------


class TestMeasuredVariableNoDelUncompute:
    """After measurement, __del__ uncomputation is a no-op because history
    is empty (no entries to reverse)."""

    def test_measured_variable_no_del_uncompute(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        # Populate history as if operations produced this variable
        a.history.append(100, (0, 1))
        a.history.append(200, (2, 3))

        a.measure()

        # History is now empty -- __del__ has nothing to uncompute
        assert len(a.history) == 0
        assert not a.history

    def test_measured_qbool_no_del_uncompute(self):
        ql.circuit()
        b = ql.qbool(True)
        b.history.append(400, (0,))

        b.measure()
        assert len(b.history) == 0
        assert not b.history


# ---------------------------------------------------------------------------
# Test: measurement orphans children
# ---------------------------------------------------------------------------


class _Dummy:
    """Weakref-able placeholder for testing child weakrefs."""
    pass


class TestMeasurementOrphansChildren:
    """Children of a measured variable are detached and can be cleaned up
    independently (weakrefs in children list are cleared by discard)."""

    def test_measurement_orphans_children(self):
        ql.circuit()
        a = ql.qint(5, width=4)

        # Add child weakrefs
        child1 = _Dummy()
        child2 = _Dummy()
        a.history.add_child(child1)
        a.history.add_child(child2)
        assert len(a.history.live_children()) == 2

        a.measure()

        # Children list is cleared by discard
        assert len(a.history.children) == 0
        assert a.history.live_children() == []

        # But the child objects themselves are still alive (not destroyed)
        assert child1 is not None
        assert child2 is not None

    def test_orphaned_children_can_be_gc_independently(self):
        """After measurement, children are no longer referenced by the
        history graph and can be garbage collected on their own."""
        ql.circuit()
        a = ql.qint(5, width=4)

        child = _Dummy()
        a.history.add_child(child)

        a.measure()
        # History no longer holds a weakref to child
        assert len(a.history.children) == 0

        # Child can be deleted independently
        del child
        gc.collect()
        # No errors -- child was cleaned up without interference
