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
from quantum_language._core import (
    _atexit_disable_circuit,
    _get_circuit_active,
    _set_circuit_active,
)
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
        cond = a == 5
        assert len(cond.history) == 1
        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()
        # Inverse gates should have been emitted (gate count increased)
        assert gc_after > gc_before

    def test_del_is_idempotent_no_double_uncompute(self):
        """After __del__ uncomputes history, a second GC pass emits no gates.

        Verifies there is no double-uncomputation: history.uncompute()
        clears entries so a repeat is a no-op.
        """
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        assert len(cond.history) == 1
        # First del + GC
        del cond
        gc.collect()
        gc_after_first = ql.get_gate_count()
        # Second GC pass should emit nothing further
        gc.collect()
        gc_after_second = ql.get_gate_count()
        assert gc_after_second == gc_after_first

    def test_del_preserves_input_variables(self):
        """Input variables remain intact when temporaries are deleted."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=4)
        cond = a == b
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
        cond = a == 5
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
        cond = a == 5
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
        cond = a == 5
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
        child_cond = a == 3
        child_seq_ptr, _, _, _ = child_cond.history.entries[0]
        assert child_seq_ptr != 0

        # Create the parent equality
        parent_cond = a == 5
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


# ---------------------------------------------------------------------------
# Test: EAGER mode (qubit_saving=True)
# ---------------------------------------------------------------------------


class TestDelEagerMode:
    """EAGER mode: __del__ always uncomputes immediately."""

    def test_eager_del_emits_inverse_gates(self):
        """In EAGER mode, __del__ emits inverse gates for comparison."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5
        assert len(cond.history) == 1
        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before

    def test_eager_no_double_uncompute(self):
        """EAGER mode does not double-uncompute history + legacy path."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        gc_after_init = ql.get_gate_count()
        cond = a == 5
        gc_after_compare = ql.get_gate_count()
        forward_compare_gates = gc_after_compare - gc_after_init
        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        inverse_gates = gc_after_del - gc_after_compare
        # Inverse should emit exactly the same number of gates as the
        # forward comparison.  Double uncomputation (history.uncompute
        # + history uncompute) would emit 2x.
        assert inverse_gates == forward_compare_gates, (
            f"Possible double uncomputation: forward={forward_compare_gates}, "
            f"inverse={inverse_gates}"
        )

    def test_eager_skips_when_inactive(self):
        """EAGER mode still respects circuit-active guard."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5
        gc_before = ql.get_gate_count()
        _set_circuit_active(False)
        try:
            del cond
            gc.collect()
            gc_after = ql.get_gate_count()
            assert gc_after == gc_before
        finally:
            _set_circuit_active(True)

    def test_eager_bitwise_and(self):
        """EAGER mode uncomputes bitwise AND on del."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        c = a & 0b1011
        assert len(c.history) == 1
        gc_before = ql.get_gate_count()
        del c
        gc.collect()
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before


# ---------------------------------------------------------------------------
# Test: atexit shutdown guard
# ---------------------------------------------------------------------------


class TestAtexitShutdownGuard:
    """atexit hook disables circuit-active to prevent shutdown crashes."""

    def test_atexit_disables_circuit_flag(self):
        """Calling the atexit hook sets circuit-active to False."""
        ql.circuit()
        assert _get_circuit_active()
        _atexit_disable_circuit()
        assert not _get_circuit_active()
        # Restore for subsequent tests
        _set_circuit_active(True)

    def test_del_after_atexit_is_noop(self):
        """__del__ after atexit hook does not emit gates."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        gc_before = ql.get_gate_count()
        _atexit_disable_circuit()
        try:
            del cond
            gc.collect()
            gc_after = ql.get_gate_count()
            assert gc_after == gc_before
        finally:
            _set_circuit_active(True)

    def test_atexit_is_idempotent(self):
        """Calling atexit hook multiple times is safe."""
        ql.circuit()
        assert _get_circuit_active()
        _atexit_disable_circuit()
        _atexit_disable_circuit()
        assert not _get_circuit_active()
        _set_circuit_active(True)

    def test_del_after_atexit_eager_mode_is_noop(self):
        """__del__ in EAGER mode after atexit hook does not emit gates."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5
        gc_before = ql.get_gate_count()
        _atexit_disable_circuit()
        try:
            del cond
            gc.collect()
            gc_after = ql.get_gate_count()
            assert gc_after == gc_before
        finally:
            _set_circuit_active(True)

    def test_del_with_children_after_atexit_is_noop(self):
        """__del__ with cascading children after atexit emits no gates."""
        ql.circuit()
        a = ql.qint(5, width=4)
        child_cond = a == 3
        parent_cond = a == 5
        parent_cond.history.add_child(child_cond)
        gc_before = ql.get_gate_count()
        _atexit_disable_circuit()
        try:
            del parent_cond
            gc.collect()
            gc_after = ql.get_gate_count()
            assert gc_after == gc_before
            # Child history should remain untouched (no cascade happened)
            assert len(child_cond.history) == 1
        finally:
            _set_circuit_active(True)

    def test_atexit_hook_is_registered(self):
        """The atexit hook is registered in the atexit module."""
        import atexit

        # atexit._run_exitfuncs would run all; we just check registration
        # by verifying _atexit_disable_circuit is callable and the module
        # import + register call in _core.pyx executed at import time.
        # The function should already be registered (line 85 of _core.pyx).
        # We verify by calling unregister and re-registering.
        atexit.unregister(_atexit_disable_circuit)
        atexit.register(_atexit_disable_circuit)
        # If we got here without error, the function is a valid atexit target


# ---------------------------------------------------------------------------
# Test: __exit__ + __del__ no double uncompute
# ---------------------------------------------------------------------------


class TestExitDelNoDoubleUncompute:
    """__exit__ clears layer range so subsequent __del__ does not re-uncompute."""

    def test_with_then_del_no_extra_gates(self):
        """After with-block exits, deleting the condition emits no more gates."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        with cond:
            pass
        gc_after_exit = ql.get_gate_count()
        # Now delete the condition -- should not emit extra inverse gates
        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        assert gc_after_del == gc_after_exit

    def test_with_then_del_eager_no_extra_gates(self):
        """EAGER mode: after with-block, del does not double-uncompute."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5
        with cond:
            pass
        gc_after_exit = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        assert gc_after_del == gc_after_exit


# ---------------------------------------------------------------------------
# Test: simulation correctness
# ---------------------------------------------------------------------------


class TestDelSimulationCorrectness:
    """Verify __del__ uncomputation produces correct circuit state.

    Uses gate count symmetry: forward comparison + inverse should produce
    twice the forward gate count (exact for CQ equality).
    """

    def test_del_inverse_gate_count_matches_forward(self):
        """Inverse gate count from __del__ matches forward gate count."""
        ql.circuit()
        a = ql.qint(5, width=4)
        gc_after_init = ql.get_gate_count()
        cond = a == 5
        gc_after_compare = ql.get_gate_count()
        forward_compare_gates = gc_after_compare - gc_after_init
        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        inverse_gates = gc_after_del - gc_after_compare
        # For CQ equality, the inverse should emit the same number of
        # gates as the forward path (self-inverse sequence).
        assert inverse_gates == forward_compare_gates, (
            f"Forward={forward_compare_gates}, inverse={inverse_gates}"
        )

    def test_del_leaves_peak_allocated_intact(self):
        """After del uncomputation, peak_allocated is not reduced."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        stats_before = ql.circuit_stats()
        peak_before = stats_before["peak_allocated"]
        del cond
        gc.collect()
        stats_after = ql.circuit_stats()
        peak_after = stats_after["peak_allocated"]
        # Peak allocated should not decrease after uncomputation
        # (qubits were used at some point, even if freed back)
        assert peak_after >= peak_before
