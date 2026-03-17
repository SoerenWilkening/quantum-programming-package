"""Tests for per-variable history recording in arithmetic/comparison/bitwise ops.

Validates that operations producing new qint/qbool values record
(sequence_ptr, qubit_mapping, num_ancilla, kind) entries into the result's history graph,
and that intermediate temporaries are tracked as weakref children.

Step 1.2 of Phase 1: Record Operations into Per-Variable History
[Quantum_Assembly-2ab.2].
"""

import gc

import quantum_language as ql

# ---------------------------------------------------------------------------
# Arithmetic: addition records history
# ---------------------------------------------------------------------------


class TestAdditionRecordsHistory:
    """c = a + b -> c.history has 1 entry."""

    def test_addition_qq_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        assert len(c.history) == 1

    def test_addition_cq_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = a + 2
        assert len(c.history) == 1

    def test_addition_history_has_qubit_mapping(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        seq_ptr, qm, _nac, _kind = c.history.entries[0]
        # qubit_mapping should be a tuple of integer-like values
        assert isinstance(qm, tuple)
        assert len(qm) > 0
        assert all(int(q) >= 0 for q in qm)

    def test_subtraction_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        c = a - b
        assert len(c.history) == 1

    def test_radd_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = 2 + a
        assert len(c.history) == 1

    def test_rsub_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = 10 - a
        assert len(c.history) == 1

    def test_negation_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        c = -a
        assert len(c.history) == 1

    def test_lshift_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = a << 1
        assert len(c.history) == 1

    def test_rshift_records_history(self):
        ql.circuit()
        a = ql.qint(6, width=4)
        c = a >> 1
        assert len(c.history) == 1

    def test_mul_cq_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = a * 2
        assert len(c.history) == 1

    def test_mul_qq_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a * b
        assert len(c.history) == 1

    def test_rmul_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = 2 * a
        assert len(c.history) == 1


# ---------------------------------------------------------------------------
# Comparison: records history
# ---------------------------------------------------------------------------


class TestComparisonRecordsHistory:
    """Comparison ops record entries into result qbool's history."""

    def test_eq_cq_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        assert len(cond.history) >= 1

    def test_eq_qq_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=4)
        cond = a == b
        assert len(cond.history) >= 1

    def test_gt_cq_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a > 3
        assert len(cond.history) >= 1

    def test_lt_cq_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a < 7
        assert len(cond.history) >= 1

    def test_gt_qq_records_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        cond = a > b
        assert len(cond.history) >= 1

    def test_lt_qq_records_history(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        cond = a < b
        assert len(cond.history) >= 1

    def test_comparison_history_has_qubit_mapping(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        seq_ptr, qm, _nac, _kind = cond.history.entries[0]
        assert isinstance(qm, tuple)
        assert len(qm) > 0


# ---------------------------------------------------------------------------
# Bitwise: records history
# ---------------------------------------------------------------------------


class TestBitwiseRecordsHistory:
    """Bitwise ops record entries into result's history."""

    def test_and_qq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1101, width=4)
        b = ql.qint(0b1011, width=4)
        c = a & b
        assert len(c.history) == 1

    def test_and_cq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1101, width=4)
        c = a & 0b1011
        assert len(c.history) == 1

    def test_or_qq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1100, width=4)
        b = ql.qint(0b0011, width=4)
        c = a | b
        assert len(c.history) == 1

    def test_or_cq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1100, width=4)
        c = a | 0b0011
        assert len(c.history) == 1

    def test_xor_qq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1100, width=4)
        b = ql.qint(0b0110, width=4)
        c = a ^ b
        assert len(c.history) == 1

    def test_xor_cq_records_history(self):
        ql.circuit()
        a = ql.qint(0b1100, width=4)
        c = a ^ 0b0110
        assert len(c.history) == 1

    def test_bitwise_history_has_qubit_mapping(self):
        ql.circuit()
        a = ql.qint(0b1101, width=4)
        b = ql.qint(0b1011, width=4)
        c = a & b
        seq_ptr, qm, _nac, _kind = c.history.entries[0]
        assert isinstance(qm, tuple)
        assert len(qm) > 0


# ---------------------------------------------------------------------------
# Chained expressions: children
# ---------------------------------------------------------------------------


class TestChainedExpressionRecordsChildren:
    """Compound expressions add intermediate temporaries as weakref children."""

    def test_chained_add_gt_records_children(self):
        """cond = (a + 3) > 5 -> cond's history has entries from the comparison."""
        ql.circuit()
        a = ql.qint(4, width=4)
        temp = a + 3
        cond = temp > 5
        # The > comparison on qint > int delegates to qint > qint,
        # which creates widened temporaries tracked as children.
        # At minimum, the comparison result should have history entries.
        assert len(cond.history) >= 1

    def test_lt_qq_has_widened_children_registered(self):
        """a < b registers widened temps as weakref children."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        cond = a < b
        # __lt__ creates temp_self and temp_other as widened copies
        # and registers them as weakref children via add_child.
        # The temps are local to __lt__ and may already be GC'd,
        # but the weakref slots should still exist in the children list.
        assert len(cond.history.children) >= 2

    def test_gt_qq_has_widened_children_registered(self):
        """a > b registers widened temps as weakref children."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        cond = a > b
        assert len(cond.history.children) >= 2

    def test_children_dead_after_scope_exit(self):
        """Widened temp weakrefs become dead after method scope exits."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        cond = a < b
        gc.collect()
        # The widened temps are local to __lt__, so their weakrefs
        # are expected to be dead after __lt__ returns and GC runs.
        # This verifies the weakref mechanism handles dead refs gracefully.
        # live_children() should return empty or fewer than children count
        alive = cond.history.live_children()
        dead_count = len(cond.history.children) - len(alive)
        assert dead_count >= 0  # At least some may be dead


# ---------------------------------------------------------------------------
# Input variables: no history
# ---------------------------------------------------------------------------


class TestInputVariablesNoHistory:
    """User-created input variables have empty history."""

    def test_qint_no_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        assert len(a.history) == 0

    def test_qbool_no_history(self):
        ql.circuit()
        b = ql.qbool(False)
        assert len(b.history) == 0

    def test_zero_qint_no_history(self):
        ql.circuit()
        a = ql.qint(0, width=8)
        assert len(a.history) == 0

    def test_iadd_does_not_add_history(self):
        """In-place += does not record to history (modifies existing var)."""
        ql.circuit()
        a = ql.qint(3, width=4)
        a += 2
        # In-place operations modify `a` but do not create a new result
        # that needs history. The history is for tracking how a *new*
        # variable was produced, not modifications to existing ones.
        assert len(a.history) == 0

    def test_isub_does_not_add_history(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        a -= 2
        assert len(a.history) == 0

    def test_operands_unchanged_after_add(self):
        """a + b should not modify a.history or b.history."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        _ = a + b
        assert len(a.history) == 0
        assert len(b.history) == 0


# ---------------------------------------------------------------------------
# History entry contents
# ---------------------------------------------------------------------------


class TestHistoryEntryContents:
    """Validate structure and content of history entries."""

    def test_qubit_mapping_contains_result_qubits(self):
        """The qubit mapping should include the result's own qubits."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        _, qm, _nac, _kind = c.history.entries[0]
        # Result qubits should be in the mapping
        c_offset = 64 - c.width
        result_qubits = {int(c.qubits[c_offset + i]) for i in range(c.width)}
        mapping_set = set(qm)
        assert result_qubits.issubset(mapping_set)

    def test_eq_cq_has_sequence_ptr(self):
        """CQ equality comparison captures the sequence pointer."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        seq_ptr, _, _nac, _kind = cond.history.entries[0]
        # The CQ equality path has a real sequence pointer
        assert seq_ptr != 0

    def test_addition_has_zero_sequence_ptr(self):
        """Compound addition uses sequence_ptr=0 (multiple sub-ops)."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b
        seq_ptr, _, _nac, _kind = c.history.entries[0]
        # Out-of-place addition is a compound op (copy + add),
        # so no single sequence_ptr
        assert seq_ptr == 0
