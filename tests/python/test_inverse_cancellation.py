"""Tests for tail-only inverse cancellation in HistoryGraph.append().

Step 6.4: Tail-only inverse cancellation [Quantum_Assembly-4q7.4].

Validates that append() cancels inverse pairs at the tail when no active
blockers exist, and refuses to cancel when blockers are present or entries
are not at the tail.

Step 6.4 wiring [Quantum_Assembly-bd9]: Integration tests verify that
real qint in-place ops (__iadd__, __isub__, __ixor__) pass kind= to
history.append(), enabling the cancellation paths.
"""

import gc

import quantum_language as ql
from quantum_language.history_graph import HistoryGraph

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
# add_sub_cancel
# ---------------------------------------------------------------------------


class TestAddSubCancel:
    """add followed by sub with same seq_ptr and qubit_mapping cancels."""

    def test_add_sub_cancel(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1, 2), kind="add")
        assert len(hg) == 1
        hg.append(100, (0, 1, 2), kind="sub")
        assert len(hg) == 0

    def test_add_sub_cancel_entries_empty(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1, 2), kind="add")
        hg.append(100, (0, 1, 2), kind="sub")
        assert hg.entries == []


# ---------------------------------------------------------------------------
# sub_add_cancel
# ---------------------------------------------------------------------------


class TestSubAddCancel:
    """sub followed by add with same seq_ptr and qubit_mapping cancels."""

    def test_sub_add_cancel(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1, 2), kind="sub")
        assert len(hg) == 1
        hg.append(100, (0, 1, 2), kind="add")
        assert len(hg) == 0

    def test_sub_add_cancel_entries_empty(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1, 2), kind="sub")
        hg.append(100, (0, 1, 2), kind="add")
        assert hg.entries == []


# ---------------------------------------------------------------------------
# xor_self_cancel
# ---------------------------------------------------------------------------


class TestXorSelfCancel:
    """xor followed by xor with same seq_ptr and qubit_mapping cancels."""

    def test_xor_self_cancel(self):
        hg = HistoryGraph()
        hg.append(200, (3, 4), kind="xor")
        assert len(hg) == 1
        hg.append(200, (3, 4), kind="xor")
        assert len(hg) == 0

    def test_xor_self_cancel_entries_empty(self):
        hg = HistoryGraph()
        hg.append(200, (3, 4), kind="xor")
        hg.append(200, (3, 4), kind="xor")
        assert hg.entries == []


# ---------------------------------------------------------------------------
# no_cancel_different_values
# ---------------------------------------------------------------------------


class TestNoCancelDifferentValues:
    """No cancellation when seq_ptr or qubit_mapping differs."""

    def test_no_cancel_different_seq_ptr(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (0, 1), kind="sub")
        assert len(hg) == 2

    def test_no_cancel_different_qubit_mapping(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(100, (0, 2), kind="sub")
        assert len(hg) == 2

    def test_no_cancel_same_kind_add(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(100, (0, 1), kind="add")
        assert len(hg) == 2

    def test_no_cancel_same_kind_sub(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="sub")
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 2

    def test_no_cancel_xor_different_qubit_mapping(self):
        hg = HistoryGraph()
        hg.append(200, (3, 4), kind="xor")
        hg.append(200, (3, 5), kind="xor")
        assert len(hg) == 2

    def test_no_cancel_xor_different_seq_ptr(self):
        hg = HistoryGraph()
        hg.append(200, (3, 4), kind="xor")
        hg.append(300, (3, 4), kind="xor")
        assert len(hg) == 2

    def test_no_cancel_without_kind(self):
        """Entries without kind never cancel."""
        hg = HistoryGraph()
        hg.append(100, (0, 1))
        hg.append(100, (0, 1))
        assert len(hg) == 2

    def test_no_cancel_kind_none_vs_add(self):
        """Tail without kind does not cancel with new entry that has kind."""
        hg = HistoryGraph()
        hg.append(100, (0, 1))
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 2


# ---------------------------------------------------------------------------
# no_cancel_with_blocker
# ---------------------------------------------------------------------------


class TestNoCancelWithBlocker:
    """No cancellation when an active blocker exists after the tail."""

    def test_no_cancel_with_active_blocker(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 2

    def test_no_cancel_with_blocker_at_tail(self):
        """Blocker at exactly the tail index prevents cancellation."""
        hg = HistoryGraph()
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)  # index=0
        hg.append(100, (0, 1), kind="add")  # entry index 0
        dep2 = _Dummy(allocated=True)
        hg.add_blocker(dep2)  # index=1
        hg.append(100, (0, 1), kind="sub")
        # Blocker at index 1 (== tail index) should prevent cancellation
        assert len(hg) == 2


# ---------------------------------------------------------------------------
# cancel_after_blocker_cleared
# ---------------------------------------------------------------------------


class TestCancelAfterBlockerCleared:
    """Cancellation proceeds once a blocker becomes inactive."""

    def test_cancel_after_deallocation(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        # Blocker active — no cancellation
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 2
        # Now clear the entries and try again with inactive blocker
        hg.entries.clear()
        dep.qubits_allocated = False
        hg.append(100, (0, 1), kind="add")
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 0

    def test_cancel_after_gc(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        del dep
        gc.collect()
        # Blocker now inactive — cancellation should proceed
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 0


# ---------------------------------------------------------------------------
# no_cancel_non_tail
# ---------------------------------------------------------------------------


class TestNoCancelNonTail:
    """Cancellation only applies to the tail entry, not earlier entries."""

    def test_no_cancel_non_tail(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (2, 3), kind="xor")
        # The sub matches the first entry (add), not the tail (xor)
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 3

    def test_no_cancel_middle_entry(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (2, 3), kind="add")
        hg.append(300, (4, 5), kind="xor")
        # Try to cancel the middle entry — should not work
        hg.append(200, (2, 3), kind="sub")
        assert len(hg) == 4


# ---------------------------------------------------------------------------
# chain_cancellation
# ---------------------------------------------------------------------------


class TestChainCancellation:
    """Successive cancellations peel entries from the tail one at a time."""

    def test_chain_cancellation(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 2

        # Cancel the xor tail
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 1

        # Now the add is the tail — cancel it
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 0

    def test_chain_cancellation_three_entries(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (2, 3), kind="xor")
        hg.append(300, (4, 5), kind="sub")
        assert len(hg) == 3

        # Cancel sub with add
        hg.append(300, (4, 5), kind="add")
        assert len(hg) == 2

        # Cancel xor with xor
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 1

        # Cancel add with sub
        hg.append(100, (0, 1), kind="sub")
        assert len(hg) == 0


# ---------------------------------------------------------------------------
# gate_count_reduction
# ---------------------------------------------------------------------------


class TestGateCountReduction:
    """Cancellation reduces the number of history entries — a proxy for
    gate count reduction in the real circuit."""

    def test_gate_count_baseline(self):
        """Without cancellation, entries accumulate."""
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(200, (2, 3), kind="xor")
        hg.append(300, (4, 5), kind="sub")
        assert len(hg) == 3

    def test_gate_count_with_cancellation(self):
        """With cancellation, inverse pairs are removed."""
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(100, (0, 1), kind="sub")  # cancels
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 1

    def test_gate_count_multiple_cancellations(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        hg.append(100, (0, 1), kind="sub")  # cancels add
        hg.append(200, (2, 3), kind="xor")
        hg.append(200, (2, 3), kind="xor")  # cancels xor
        assert len(hg) == 0

    def test_gate_count_with_blocker_prevents_reduction(self):
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="add")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        hg.append(100, (0, 1), kind="sub")  # blocked — no cancellation
        assert len(hg) == 2

    def test_num_ancilla_preserved(self):
        """num_ancilla is preserved in entries that are not cancelled."""
        hg = HistoryGraph()
        hg.append(100, (0, 1), 3, kind="add")
        assert len(hg) == 1
        assert hg.entries[0][2] == 3

    def test_kind_preserved_in_entry(self):
        """kind is stored as the 4th element of the entry tuple."""
        hg = HistoryGraph()
        hg.append(100, (0, 1), kind="xor")
        assert hg.entries[0][3] == "xor"


# ---------------------------------------------------------------------------
# compiled_fn_cancel
# ---------------------------------------------------------------------------


class TestCompiledFnCancel:
    """compiled_fn followed by compiled_fn_inv with same seq_ptr and
    qubit_mapping cancels (Step 6.5)."""

    def test_compiled_fn_cancel(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn")
        assert len(hg) == 1
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn_inv")
        assert len(hg) == 0

    def test_compiled_fn_cancel_entries_empty(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn")
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn_inv")
        assert hg.entries == []

    def test_compiled_fn_inv_then_fn_cancel(self):
        """compiled_fn_inv followed by compiled_fn also cancels."""
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn_inv")
        hg.append(500, (0, 1, 2, 3), kind="compiled_fn")
        assert len(hg) == 0

    def test_compiled_fn_chain_cancel(self):
        """Chain cancellation: fn + other + cancel_other + cancel_fn."""
        hg = HistoryGraph()
        hg.append(500, (0, 1), kind="compiled_fn")
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 2
        # Cancel xor
        hg.append(200, (2, 3), kind="xor")
        assert len(hg) == 1
        # Cancel compiled_fn
        hg.append(500, (0, 1), kind="compiled_fn_inv")
        assert len(hg) == 0


# ---------------------------------------------------------------------------
# compiled_fn_no_cancel_different_args
# ---------------------------------------------------------------------------


class TestCompiledFnNoCancelDifferentArgs:
    """No cancellation when seq_ptr or qubit_mapping differs for compiled fns."""

    def test_no_cancel_different_seq_ptr(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1), kind="compiled_fn")
        hg.append(600, (0, 1), kind="compiled_fn_inv")
        assert len(hg) == 2

    def test_no_cancel_different_qubit_mapping(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1), kind="compiled_fn")
        hg.append(500, (0, 2), kind="compiled_fn_inv")
        assert len(hg) == 2

    def test_no_cancel_same_kind(self):
        """Two compiled_fn entries with same args do NOT cancel."""
        hg = HistoryGraph()
        hg.append(500, (0, 1), kind="compiled_fn")
        hg.append(500, (0, 1), kind="compiled_fn")
        assert len(hg) == 2

    def test_no_cancel_same_kind_inv(self):
        """Two compiled_fn_inv entries with same args do NOT cancel."""
        hg = HistoryGraph()
        hg.append(500, (0, 1), kind="compiled_fn_inv")
        hg.append(500, (0, 1), kind="compiled_fn_inv")
        assert len(hg) == 2


# ---------------------------------------------------------------------------
# compiled_fn_blocker
# ---------------------------------------------------------------------------


class TestCompiledFnBlocker:
    """No cancellation for compiled fns when an active blocker exists."""

    def test_no_cancel_with_active_blocker(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2), kind="compiled_fn")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        hg.append(500, (0, 1, 2), kind="compiled_fn_inv")
        assert len(hg) == 2

    def test_cancel_after_blocker_inactive(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2), kind="compiled_fn")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        dep.qubits_allocated = False
        # Blocker now inactive — cancellation should proceed
        hg.append(500, (0, 1, 2), kind="compiled_fn_inv")
        assert len(hg) == 0

    def test_cancel_after_blocker_gc(self):
        hg = HistoryGraph()
        hg.append(500, (0, 1, 2), kind="compiled_fn")
        dep = _Dummy(allocated=True)
        hg.add_blocker(dep)
        del dep
        gc.collect()
        # Blocker GC'd — cancellation should proceed
        hg.append(500, (0, 1, 2), kind="compiled_fn_inv")
        assert len(hg) == 0


# ---------------------------------------------------------------------------
# Integration: real qint in-place ops wire kind= to history.append
# [Quantum_Assembly-bd9]
# ---------------------------------------------------------------------------


class TestIaddIsubCancelReal:
    """a += N; a -= N on a real qint produces empty history."""

    def test_iadd_isub_cancel_classical(self):
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a += 5
        a -= 5
        assert len(a.history) == 0

    def test_isub_iadd_cancel_classical(self):
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a -= 3
        a += 3
        assert len(a.history) == 0

    def test_iadd_isub_no_cancel_different_values(self):
        """a += 5; a -= 3 must NOT cancel (different classical values)."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a += 5
        a -= 3
        assert len(a.history) == 2

    def test_iadd_records_kind_add(self):
        """__iadd__ records an entry with kind='add'."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a += 7
        assert len(a.history) == 1
        assert a.history.entries[0][3] == "add"

    def test_isub_records_kind_sub(self):
        """__isub__ records an entry with kind='sub'."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a -= 2
        assert len(a.history) == 1
        assert a.history.entries[0][3] == "sub"


class TestIxorCancelReal:
    """a ^= N; a ^= N on a real qint produces empty history (XOR is self-inverse)."""

    def test_ixor_self_cancel_classical(self):
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a ^= 5
        a ^= 5
        assert len(a.history) == 0

    def test_ixor_no_cancel_different_values(self):
        """a ^= 5; a ^= 3 must NOT cancel (different classical values)."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a ^= 5
        a ^= 3
        assert len(a.history) == 2

    def test_ixor_records_kind_xor(self):
        """__ixor__ records an entry with kind='xor'."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a ^= 9
        assert len(a.history) == 1
        assert a.history.entries[0][3] == "xor"

    def test_ixor_qq_self_cancel(self):
        """a ^= b; a ^= b on quantum operands produces empty history."""
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        b = ql.qint(3, width=4)
        a ^= b
        a ^= b
        assert len(a.history) == 0


class TestChainCancelReal:
    """Multiple in-place ops can chain-cancel on real qints."""

    def test_add_xor_cancel_chain(self):
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a += 5
        a ^= 3
        assert len(a.history) == 2
        # Cancel xor first (tail)
        a ^= 3
        assert len(a.history) == 1
        # Cancel add (now tail)
        a -= 5
        assert len(a.history) == 0

    def test_triple_add_sub_partial_cancel(self):
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        a += 1
        a += 2
        a -= 2  # cancels the += 2
        assert len(a.history) == 1
        assert a.history.entries[0][3] == "add"
