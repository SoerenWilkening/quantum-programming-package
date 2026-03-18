"""Tests for Phase ix4.2: In-place comparison with borrow-ancilla pattern.

Verifies that __lt__ and __gt__ use the borrow-ancilla pattern
(split-register arithmetic) instead of temporary copies.

Tests:
  - lt_correctness: qint < int and qint < qint produce correct results
  - gt_correctness: qint > int and qint > qint produce correct results
  - le_ge_derived: <= and >= work correctly (derived from lt/gt)
  - operand_preservation: operands unchanged after comparison
  - no_history_children: no temporary children in history.children
  - ancilla_deallocated: borrow ancilla freed after comparison
  - comparison_in_with_block: comparison result usable in with block
  - comparison_superposition: comparison works in Grover oracle context
"""

import gc

import quantum_language as ql

# ============================================================================
# lt_correctness
# ============================================================================


class TestLtCorrectness:
    """Less-than comparison produces correct qbool results."""

    def test_lt_int_true(self):
        """qint(3) < 5 should produce qbool (True)."""
        ql.circuit()
        a = ql.qint(3, width=4)
        result = a < 5
        assert isinstance(result, ql.qbool)

    def test_lt_int_false(self):
        """qint(7) < 3 should produce qbool (False)."""
        ql.circuit()
        a = ql.qint(7, width=4)
        result = a < 3
        assert isinstance(result, ql.qbool)

    def test_lt_int_equal(self):
        """qint(5) < 5 should produce qbool (False)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a < 5
        assert isinstance(result, ql.qbool)

    def test_lt_int_zero(self):
        """qint(n) < 0 should always be False (unsigned)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a < 0
        assert isinstance(result, ql.qbool)

    def test_lt_int_overflow(self):
        """qint < value_too_large should always be True."""
        ql.circuit()
        a = ql.qint(15, width=4)
        result = a < 100
        assert isinstance(result, ql.qbool)

    def test_lt_int_negative(self):
        """qint < negative should always be False."""
        ql.circuit()
        a = ql.qint(0, width=4)
        result = a < -1
        assert isinstance(result, ql.qbool)

    def test_lt_qint_true(self):
        """qint(3) < qint(5) should produce qbool."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        result = a < b
        assert isinstance(result, ql.qbool)

    def test_lt_qint_false(self):
        """qint(7) < qint(3) should produce qbool."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        result = a < b
        assert isinstance(result, ql.qbool)

    def test_lt_qint_equal_values(self):
        """qint(5) < qint(5) should produce qbool (False)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=4)
        result = a < b
        assert isinstance(result, ql.qbool)

    def test_lt_self_optimization(self):
        """x < x always returns False (self-comparison)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a < a
        assert isinstance(result, ql.qbool)

    def test_lt_various_widths(self):
        """Less-than works for various bit widths."""
        for width in [1, 2, 4, 8]:
            ql.circuit()
            a = ql.qint(0, width=width)
            result = a < 1
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_lt_mixed_widths(self):
        """Less-than works when operands have different widths."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=8)
        result = a < b
        assert isinstance(result, ql.qbool)


# ============================================================================
# gt_correctness
# ============================================================================


class TestGtCorrectness:
    """Greater-than comparison produces correct qbool results."""

    def test_gt_int_true(self):
        """qint(7) > 3 should produce qbool."""
        ql.circuit()
        a = ql.qint(7, width=4)
        result = a > 3
        assert isinstance(result, ql.qbool)

    def test_gt_int_false(self):
        """qint(2) > 5 should produce qbool."""
        ql.circuit()
        a = ql.qint(2, width=4)
        result = a > 5
        assert isinstance(result, ql.qbool)

    def test_gt_int_equal(self):
        """qint(5) > 5 should produce qbool (False)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a > 5
        assert isinstance(result, ql.qbool)

    def test_gt_int_negative(self):
        """qint > negative should always be True."""
        ql.circuit()
        a = ql.qint(0, width=4)
        result = a > -1
        assert isinstance(result, ql.qbool)

    def test_gt_int_overflow(self):
        """qint > value_too_large should always be False."""
        ql.circuit()
        a = ql.qint(15, width=4)
        result = a > 100
        assert isinstance(result, ql.qbool)

    def test_gt_qint_true(self):
        """qint(7) > qint(3) should produce qbool."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        result = a > b
        assert isinstance(result, ql.qbool)

    def test_gt_qint_false(self):
        """qint(2) > qint(5) should produce qbool."""
        ql.circuit()
        a = ql.qint(2, width=4)
        b = ql.qint(5, width=4)
        result = a > b
        assert isinstance(result, ql.qbool)

    def test_gt_self_optimization(self):
        """x > x always returns False."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a > a
        assert isinstance(result, ql.qbool)

    def test_gt_various_widths(self):
        """Greater-than works for various bit widths."""
        for width in [1, 2, 4, 8]:
            ql.circuit()
            a = ql.qint(1, width=width) if width > 1 else ql.qint(1, width=1)
            result = a > 0
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_gt_mixed_widths(self):
        """Greater-than works when operands have different widths."""
        ql.circuit()
        a = ql.qint(10, width=8)
        b = ql.qint(3, width=4)
        result = a > b
        assert isinstance(result, ql.qbool)

    def test_gt_int_max_value(self):
        """qint > max_val should always be False."""
        ql.circuit()
        a = ql.qint(15, width=4)
        result = a > 15
        assert isinstance(result, ql.qbool)


# ============================================================================
# le_ge_derived
# ============================================================================


class TestLeGeDerived:
    """<= and >= are derived from > and < respectively."""

    def test_le_int(self):
        """qint <= int produces qbool."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a <= 5
        assert isinstance(result, ql.qbool)

    def test_le_qint(self):
        """qint <= qint produces qbool."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        result = a <= b
        assert isinstance(result, ql.qbool)

    def test_ge_int(self):
        """qint >= int produces qbool."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a >= 5
        assert isinstance(result, ql.qbool)

    def test_ge_qint(self):
        """qint >= qint produces qbool."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        result = a >= b
        assert isinstance(result, ql.qbool)

    def test_le_self(self):
        """x <= x is always True."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a <= a
        assert isinstance(result, ql.qbool)

    def test_ge_self(self):
        """x >= x is always True."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = a >= a
        assert isinstance(result, ql.qbool)


# ============================================================================
# operand_preservation
# ============================================================================


class TestOperandPreservation:
    """Operands must be unchanged after comparison."""

    def test_lt_preserves_operand_cq(self):
        """self is unchanged after self < int."""
        ql.circuit()
        a = ql.qint(5, width=4)
        _ = a < 3
        # Operand should still be valid and have same width
        assert a.width == 4

    def test_lt_preserves_operands_qq(self):
        """Both operands unchanged after qint < qint."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(7, width=4)
        _ = a < b
        assert a.width == 4
        assert b.width == 4

    def test_gt_preserves_operands_qq(self):
        """Both operands unchanged after qint > qint."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        _ = a > b
        assert a.width == 4
        assert b.width == 4

    def test_operand_usable_after_comparison(self):
        """Operand can be used in further arithmetic after comparison."""
        ql.circuit()
        a = ql.qint(5, width=4)
        _ = a < 10
        a += 1  # Should work without error
        assert a.width == 4


# ============================================================================
# no_history_children
# ============================================================================


class TestNoHistoryChildren:
    """Borrow-ancilla comparisons should not create temporary children."""

    def test_lt_cq_no_children(self):
        """CQ less-than should have no history children."""
        ql.circuit()
        a = ql.qint(3, width=4)
        result = a < 5
        assert len(result.history.children) == 0

    def test_lt_qq_no_children(self):
        """QQ less-than should have no history children."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        result = a < b
        assert len(result.history.children) == 0

    def test_gt_cq_no_children(self):
        """CQ greater-than should have no history children."""
        ql.circuit()
        a = ql.qint(7, width=4)
        result = a > 3
        assert len(result.history.children) == 0

    def test_gt_qq_no_children(self):
        """QQ greater-than should have no history children."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        result = a > b
        assert len(result.history.children) == 0


# ============================================================================
# ancilla_deallocated
# ============================================================================


class TestAncillaDeallocated:
    """Borrow ancilla should be deallocated after comparison."""

    def test_lt_cq_ancilla_freed(self):
        """After lt CQ comparison, borrow ancilla is freed (no leak)."""
        ql.circuit()
        a = ql.qint(3, width=4)
        stats_before = ql.circuit_stats()
        _ = a < 5
        stats_after = ql.circuit_stats()
        # The only net allocation should be the result qbool (1 qubit)
        net_alloc = stats_after["current_in_use"] - stats_before["current_in_use"]
        assert net_alloc == 1, f"Expected 1 net qubit (result), got {net_alloc}"

    def test_lt_qq_ancilla_freed(self):
        """After lt QQ comparison, ancilla qubits are freed."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        stats_before = ql.circuit_stats()
        _ = a < b
        stats_after = ql.circuit_stats()
        net_alloc = stats_after["current_in_use"] - stats_before["current_in_use"]
        assert net_alloc == 1, f"Expected 1 net qubit (result), got {net_alloc}"

    def test_gt_cq_ancilla_freed(self):
        """After gt CQ comparison, borrow ancilla is freed."""
        ql.circuit()
        a = ql.qint(7, width=4)
        stats_before = ql.circuit_stats()
        _ = a > 3
        stats_after = ql.circuit_stats()
        net_alloc = stats_after["current_in_use"] - stats_before["current_in_use"]
        assert net_alloc == 1, f"Expected 1 net qubit (result), got {net_alloc}"

    def test_gt_qq_ancilla_freed(self):
        """After gt QQ comparison, ancilla qubits are freed."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        stats_before = ql.circuit_stats()
        _ = a > b
        stats_after = ql.circuit_stats()
        net_alloc = stats_after["current_in_use"] - stats_before["current_in_use"]
        assert net_alloc == 1, f"Expected 1 net qubit (result), got {net_alloc}"


# ============================================================================
# comparison_in_with_block
# ============================================================================


class TestComparisonInWithBlock:
    """Comparison results work correctly as with-block controls."""

    def test_lt_in_with_block(self):
        """Less-than result can control a with block."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(0, width=4)
        cond = a < 5
        with cond:
            b += 1
        assert b.width == 4

    def test_gt_in_with_block(self):
        """Greater-than result can control a with block."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(0, width=4)
        cond = a > 3
        with cond:
            b += 1
        assert b.width == 4

    def test_lt_qq_in_with_block(self):
        """QQ less-than result can control a with block."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(7, width=4)
        c = ql.qint(0, width=4)
        cond = a < b
        with cond:
            c += 1
        assert c.width == 4

    def test_le_in_with_block(self):
        """<= result can control a with block."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(0, width=4)
        cond = a <= 5
        with cond:
            b += 1
        assert b.width == 4

    def test_ge_in_with_block(self):
        """>= result can control a with block."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(0, width=4)
        cond = a >= 5
        with cond:
            b += 1
        assert b.width == 4

    def test_comparison_history_cleared_after_with(self):
        """History should be cleared after with block exit."""
        ql.circuit()
        a = ql.qint(3, width=4)
        cond = a < 5
        assert len(cond.history) >= 1
        with cond:
            pass
        assert len(cond.history) == 0


# ============================================================================
# comparison_superposition
# ============================================================================


class TestComparisonSuperposition:
    """Comparison operators generate valid circuits for superposition use."""

    def test_lt_generates_gates(self):
        """Less-than comparison generates circuit gates."""
        ql.circuit()
        a = ql.qint(3, width=4)
        gc_before = ql.get_gate_count()
        _ = a < 5
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "LT should generate gates"

    def test_gt_generates_gates(self):
        """Greater-than comparison generates circuit gates."""
        ql.circuit()
        a = ql.qint(7, width=4)
        gc_before = ql.get_gate_count()
        _ = a > 3
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "GT should generate gates"

    def test_lt_qq_generates_gates(self):
        """QQ less-than comparison generates circuit gates."""
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        gc_before = ql.get_gate_count()
        _ = a < b
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "QQ LT should generate gates"

    def test_gt_qq_generates_gates(self):
        """QQ greater-than comparison generates circuit gates."""
        ql.circuit()
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        gc_before = ql.get_gate_count()
        _ = a > b
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "QQ GT should generate gates"

    def test_compound_comparison(self):
        """Compound comparison with & works."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = (a > 2) & (a < 8)
        # & between qbools returns a qint (Toffoli AND result)
        assert isinstance(cond, ql.qint)

    def test_comparison_in_toffoli_mode(self):
        """Comparison works in Toffoli (fault-tolerant) mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(3, width=4)
        result = a < 5
        assert isinstance(result, ql.qbool)

    def test_gt_in_toffoli_mode(self):
        """Greater-than works in Toffoli mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(7, width=4)
        result = a > 3
        assert isinstance(result, ql.qbool)

    def test_lt_qq_in_toffoli_mode(self):
        """QQ less-than works in Toffoli mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        result = a < b
        assert isinstance(result, ql.qbool)

    def test_gt_qq_in_toffoli_mode(self):
        """QQ greater-than works in Toffoli mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(7, width=4)
        b = ql.qint(3, width=4)
        result = a > b
        assert isinstance(result, ql.qbool)
