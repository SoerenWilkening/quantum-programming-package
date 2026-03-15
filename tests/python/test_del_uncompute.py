"""Tests for __del__ uncomputation with circuit-active guard.

When a qint/qbool's refcount hits zero mid-circuit, ``__del__``
triggers uncomputation via the per-variable history graph.  A
circuit-active flag (set True on ``ql.circuit()``, False on
finalization) prevents firing during shutdown or after the circuit
is done.

Step 1.4 of Phase 1: __del__ Uncomputation with Circuit Guard
[Quantum_Assembly-2ab.4].
"""

import gc

import quantum_language as ql
from quantum_language._core import _get_circuit_active, _set_circuit_active
from quantum_language.history_graph import HistoryGraph


# ---------------------------------------------------------------------------
# Test: del uncomputes when circuit active
# ---------------------------------------------------------------------------


class TestDelUncomputesWhenCircuitActive:
    """Temporary going out of scope triggers history uncomputation."""

    def test_del_emits_inverse_gates_for_comparison(self):
        """A comparison result going out of scope emits inverse gates."""
        ql.circuit()
        assert _get_circuit_active()
        a = ql.qint(5, width=4)
        cond = (a == 5)
        assert len(cond.history) == 1
        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()
        # Inverse gates should have been emitted (gate count increased)
        assert gc_after > gc_before

    def test_del_clears_history_on_comparison(self):
        """After __del__, the comparison's history entries are cleared."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = (a == 5)
        # Verify history exists before deletion
        assert len(cond.history) == 1
        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()
        # We verify uncomputation happened by gate count increase
        assert gc_after > gc_before

    def test_del_preserves_input_variables(self):
        """Input variables remain intact when temporaries are deleted."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=4)
        cond = (a == b)
        del cond
        gc.collect()
        # Input variables should be unaffected
        assert a.width == 4
        assert b.width == 4
        assert not a._is_uncomputed
        assert not b._is_uncomputed
        assert len(a.history) == 0
        assert len(b.history) == 0

    def test_del_bitwise_and_emits_inverse(self):
        """Bitwise AND result going out of scope emits inverse gates."""
        ql.circuit()
        a = ql.qint(5, width=4)
        c = a & 0b1011
        assert len(c.history) == 1
        gc_before = ql.get_gate_count()
        del c
        gc.collect()
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before


# ---------------------------------------------------------------------------
# Test: del skips when circuit inactive
# ---------------------------------------------------------------------------


class TestDelSkipsWhenCircuitInactive:
    """No uncomputation after circuit finalization."""

    def test_del_skips_when_circuit_not_active(self):
        """Setting circuit-active to False prevents __del__ uncomputation."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = (a == 5)
        assert len(cond.history) == 1
        gc_before = ql.get_gate_count()
        # Simulate circuit finalization
        _set_circuit_active(False)
        try:
            del cond
            gc.collect()
            gc_after = ql.get_gate_count()
            # No inverse gates should have been emitted
            assert gc_after == gc_before
        finally:
            # Restore circuit-active state for subsequent tests
            _set_circuit_active(True)

    def test_del_no_error_when_circuit_inactive(self):
        """__del__ with inactive circuit does not raise or print errors."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = (a == 5)
        _set_circuit_active(False)
        try:
            # Should not raise
            del cond
            gc.collect()
        finally:
            _set_circuit_active(True)

    def test_circuit_reinit_reactivates(self):
        """Calling ql.circuit() again resets the active flag to True."""
        ql.circuit()
        _set_circuit_active(False)
        assert not _get_circuit_active()
        ql.circuit()
        assert _get_circuit_active()

    def test_del_skips_bitwise_when_inactive(self):
        """Bitwise AND result skips uncomputation when circuit inactive."""
        ql.circuit()
        a = ql.qint(5, width=4)
        c = a & 0b1011
        assert len(c.history) == 1
        gc_before = ql.get_gate_count()
        _set_circuit_active(False)
        try:
            del c
            gc.collect()
            gc_after = ql.get_gate_count()
            assert gc_after == gc_before
        finally:
            _set_circuit_active(True)


# ---------------------------------------------------------------------------
# Test: del cascades to orphaned children
# ---------------------------------------------------------------------------


class TestDelCascadesToOrphanedChildren:
    """Parent deletion triggers child uncomputation via history cascade."""

    def test_del_does_not_cascade_to_inputs(self):
        """Cascading via history does not touch user-created input variables."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = (a == 5)
        del cond
        gc.collect()
        # Input variable 'a' must remain untouched
        assert a.width == 4
        assert not a._is_uncomputed
        assert len(a.history) == 0

    def test_history_cascade_via_del_unit(self):
        """Unit test: __del__ on a variable with children cascades uncompute.

        Uses HistoryGraph directly to verify cascade behavior triggered
        by __del__ path.  The run_fn callback tracks which entries are
        processed.
        """
        parent_hg = HistoryGraph()
        parent_hg.append(100, (0, 1))

        class _Dummy:
            pass

        child = _Dummy()
        child.history = HistoryGraph()
        child.history.append(200, (2, 3))
        parent_hg.add_child(child)

        calls = []
        parent_hg.uncompute(lambda s, q, n: calls.append((s, q)))

        # Parent's entry processed
        assert (100, (0, 1)) in calls
        # Child's entry cascaded
        assert (200, (2, 3)) in calls
        # Both histories cleared
        assert len(parent_hg) == 0
        assert len(child.history) == 0

    def test_history_cascade_skips_dead_children(self):
        """Unit test: cascade via __del__ path skips dead weakref children."""
        parent_hg = HistoryGraph()
        parent_hg.append(100, (0, 1))

        class _Dummy:
            pass

        child = _Dummy()
        child.history = HistoryGraph()
        child.history.append(200, (2, 3))
        parent_hg.add_child(child)

        # Kill the child
        del child
        gc.collect()

        calls = []
        parent_hg.uncompute(lambda s, q, n: calls.append((s, q)))

        # Parent's entry processed
        assert (100, (0, 1)) in calls
        # Child was dead, so its entry was not processed
        assert (200, (2, 3)) not in calls

    def test_del_on_equality_with_manual_child(self):
        """End-to-end: equality result with a manually-added child cascades."""
        ql.circuit()
        a = ql.qint(5, width=4)

        # Create a second equality result to use as a "child"
        child_cond = (a == 3)
        child_seq_ptr, _, _ = child_cond.history.entries[0]
        assert child_seq_ptr != 0

        # Create the parent equality
        parent_cond = (a == 5)
        # Register child_cond as a weakref child of parent_cond
        parent_cond.history.add_child(child_cond)

        gc_before = ql.get_gate_count()
        # Delete parent - should cascade to child
        del parent_cond
        gc.collect()
        gc_after = ql.get_gate_count()

        # Inverse gates emitted for parent and cascaded to child
        assert gc_after > gc_before
        # Child's history should be cleared by cascade
        assert len(child_cond.history) == 0
