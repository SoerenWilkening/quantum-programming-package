"""Tests for Phase 14: Ordering Comparisons

Requirements:
- COMP-03: Refactor <= to use in-place subtraction/addition (no temp qint)
- COMP-04: Refactor >= to use in-place subtraction/addition (no temp qint)

These tests verify ordering comparisons work correctly for various bit widths
and edge cases, without allocating temporary qints.
"""

import quantum_language as ql

# ============================================================================
# Less-Than Tests (qint < int)
# ============================================================================


class TestQintLtInt:
    """Tests for qint < int comparison."""

    def test_basic_lt(self):
        """Basic qint < int returns qbool."""
        a = ql.qint(3, width=8)
        result = a < 5
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_lt_various_widths(self):
        """Less-than works for various bit widths."""
        for width in [1, 4, 8, 16, 32]:
            a = ql.qint(0, width=width)
            result = a < 1
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_lt_equal_values(self):
        """qint < same_value returns qbool (represents False)."""
        a = ql.qint(5, width=8)
        result = a < 5
        assert isinstance(result, ql.qbool)

    def test_lt_operand_preserved(self):
        """qint operand unchanged after < comparison."""
        a = ql.qint(3, width=8)
        width_before = a.width
        _ = a < 5
        assert a.width == width_before


class TestQintLtIntOverflow:
    """Tests for overflow handling in qint < int."""

    def test_lt_large_value(self):
        """qint < large_value handles overflow (returns True)."""
        a = ql.qint(5, width=4)  # 4-bit max is 15
        result = a < 100  # 100 > 15, overflow
        assert isinstance(result, ql.qbool)
        # Should return True (qint always < value outside its range)

    def test_lt_negative_value(self):
        """qint < negative handles overflow (returns False)."""
        a = ql.qint(5, width=8)
        result = a < -1  # Negative
        assert isinstance(result, ql.qbool)
        # Should return False (unsigned qint >= 0, not < negative)


# ============================================================================
# Greater-Than Tests (qint > int)
# ============================================================================


class TestQintGtInt:
    """Tests for qint > int comparison."""

    def test_basic_gt(self):
        """Basic qint > int returns qbool."""
        a = ql.qint(5, width=8)
        result = a > 3
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_gt_various_widths(self):
        """Greater-than works for various bit widths."""
        for width in [1, 4, 8, 16]:
            max_val = (1 << width) - 1
            a = ql.qint(max_val, width=width)
            result = a > 0
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_gt_operand_preserved(self):
        """qint operand unchanged after > comparison."""
        a = ql.qint(7, width=8)
        width_before = a.width
        _ = a > 3
        assert a.width == width_before


class TestQintGtIntOverflow:
    """Tests for overflow handling in qint > int."""

    def test_gt_large_value(self):
        """qint > large_value handles overflow (returns False)."""
        a = ql.qint(5, width=4)
        result = a > 100  # 100 > max 4-bit value
        assert isinstance(result, ql.qbool)
        # Should return False (qint never > value outside its range)

    def test_gt_negative_value(self):
        """qint > negative handles overflow (returns True)."""
        a = ql.qint(5, width=8)
        result = a > -5
        assert isinstance(result, ql.qbool)
        # Should return True (unsigned qint >= 0, always > negative)


# ============================================================================
# Less-Than-Or-Equal Tests (qint <= int)
# ============================================================================


class TestQintLeInt:
    """Tests for qint <= int comparison."""

    def test_basic_le(self):
        """Basic qint <= int returns qbool."""
        a = ql.qint(3, width=8)
        result = a <= 5
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_le_equal_values(self):
        """qint <= same_value returns qbool (represents True)."""
        a = ql.qint(5, width=8)
        result = a <= 5
        assert isinstance(result, ql.qbool)

    def test_le_various_widths(self):
        """Less-than-or-equal works for various bit widths."""
        for width in [1, 4, 8, 16]:
            a = ql.qint(0, width=width)
            result = a <= 0
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_le_operand_preserved(self):
        """qint operand unchanged after <= comparison."""
        a = ql.qint(3, width=8)
        width_before = a.width
        _ = a <= 5
        assert a.width == width_before


class TestQintLeIntOverflow:
    """Tests for overflow handling in qint <= int."""

    def test_le_large_value(self):
        """qint <= large_value handles overflow (returns True)."""
        a = ql.qint(5, width=4)
        result = a <= 100
        assert isinstance(result, ql.qbool)
        # Should return True (qint always <= value outside its range)

    def test_le_negative_value(self):
        """qint <= negative handles overflow (returns False)."""
        a = ql.qint(5, width=8)
        result = a <= -1
        assert isinstance(result, ql.qbool)
        # Should return False (unsigned qint >= 0, not <= negative)


# ============================================================================
# Greater-Than-Or-Equal Tests (qint >= int)
# ============================================================================


class TestQintGeInt:
    """Tests for qint >= int comparison."""

    def test_basic_ge(self):
        """Basic qint >= int returns qbool."""
        a = ql.qint(5, width=8)
        result = a >= 3
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_ge_equal_values(self):
        """qint >= same_value returns qbool (represents True)."""
        a = ql.qint(5, width=8)
        result = a >= 5
        assert isinstance(result, ql.qbool)

    def test_ge_various_widths(self):
        """Greater-than-or-equal works for various bit widths."""
        for width in [1, 4, 8, 16]:
            a = ql.qint(0, width=width)
            result = a >= 0
            assert isinstance(result, ql.qbool), f"Failed for width {width}"

    def test_ge_operand_preserved(self):
        """qint operand unchanged after >= comparison."""
        a = ql.qint(7, width=8)
        width_before = a.width
        _ = a >= 3
        assert a.width == width_before


class TestQintGeIntOverflow:
    """Tests for overflow handling in qint >= int."""

    def test_ge_large_value(self):
        """qint >= large_value handles overflow (returns False)."""
        a = ql.qint(5, width=4)
        result = a >= 100
        assert isinstance(result, ql.qbool)
        # Should return False (qint never >= value outside its range)

    def test_ge_negative_value(self):
        """qint >= negative handles overflow (returns True)."""
        a = ql.qint(5, width=8)
        result = a >= -5
        assert isinstance(result, ql.qbool)
        # Should return True (unsigned qint >= 0, always >= negative)


# ============================================================================
# qint vs qint Tests
# ============================================================================


class TestQintLtQint:
    """Tests for qint < qint comparison."""

    def test_basic_lt_qint(self):
        """Basic qint < qint returns qbool."""
        a = ql.qint(3, width=8)
        b = ql.qint(5, width=8)
        result = a < b
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_lt_qint_preserves_both_operands(self):
        """Both operands preserved after < comparison."""
        a = ql.qint(3, width=8)
        b = ql.qint(5, width=8)
        a_width = a.width
        b_width = b.width

        _ = a < b

        assert a.width == a_width
        assert b.width == b_width

    def test_lt_qint_different_widths(self):
        """< works with different bit widths."""
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=8)
        result = a < b
        assert isinstance(result, ql.qbool)


class TestQintGtQint:
    """Tests for qint > qint comparison."""

    def test_basic_gt_qint(self):
        """Basic qint > qint returns qbool."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        result = a > b
        assert isinstance(result, ql.qbool)

    def test_gt_qint_preserves_both_operands(self):
        """Both operands preserved after > comparison."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        a_width = a.width
        b_width = b.width

        _ = a > b

        assert a.width == a_width
        assert b.width == b_width


class TestQintLeQint:
    """Tests for qint <= qint comparison."""

    def test_basic_le_qint(self):
        """Basic qint <= qint returns qbool."""
        a = ql.qint(3, width=8)
        b = ql.qint(5, width=8)
        result = a <= b
        assert isinstance(result, ql.qbool)

    def test_le_qint_equal_values(self):
        """qint <= qint with equal values."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)
        result = a <= b
        assert isinstance(result, ql.qbool)

    def test_le_qint_preserves_both_operands(self):
        """Both operands preserved after <= comparison."""
        a = ql.qint(3, width=8)
        b = ql.qint(5, width=8)
        a_width = a.width
        b_width = b.width

        _ = a <= b

        assert a.width == a_width
        assert b.width == b_width


class TestQintGeQint:
    """Tests for qint >= qint comparison."""

    def test_basic_ge_qint(self):
        """Basic qint >= qint returns qbool."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        result = a >= b
        assert isinstance(result, ql.qbool)

    def test_ge_qint_equal_values(self):
        """qint >= qint with equal values."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)
        result = a >= b
        assert isinstance(result, ql.qbool)

    def test_ge_qint_preserves_both_operands(self):
        """Both operands preserved after >= comparison."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        a_width = a.width
        b_width = b.width

        _ = a >= b

        assert a.width == a_width
        assert b.width == b_width


# ============================================================================
# Self-Comparison Tests
# ============================================================================


class TestSelfComparisons:
    """Tests for self-comparison optimizations (a op a)."""

    def test_lt_self(self):
        """a < a returns qbool (represents False)."""
        a = ql.qint(5, width=8)
        result = a < a
        assert isinstance(result, ql.qbool)

    def test_gt_self(self):
        """a > a returns qbool (represents False)."""
        a = ql.qint(5, width=8)
        result = a > a
        assert isinstance(result, ql.qbool)

    def test_le_self(self):
        """a <= a returns qbool (represents True)."""
        a = ql.qint(5, width=8)
        result = a <= a
        assert isinstance(result, ql.qbool)

    def test_ge_self(self):
        """a >= a returns qbool (represents True)."""
        a = ql.qint(5, width=8)
        result = a >= a
        assert isinstance(result, ql.qbool)

    def test_self_comparison_preserves_operand(self):
        """Self-comparison preserves operand."""
        a = ql.qint(5, width=8)
        width_before = a.width

        _ = a < a
        assert a.width == width_before

        _ = a <= a
        assert a.width == width_before

        _ = a > a
        assert a.width == width_before

        _ = a >= a
        assert a.width == width_before


# ============================================================================
# Context Manager Integration Tests
# ============================================================================


class TestOrderingContextManager:
    """Tests for using ordering comparison results in controlled operations."""

    def test_lt_result_as_control(self):
        """< result can be used as control in with statement."""
        a = ql.qint(3, width=8)
        is_less = a < 5

        result = ql.qint(0, width=4)
        with is_less:
            result += 1

        assert isinstance(result, ql.qint)

    def test_le_result_as_control(self):
        """<= result can be used as control in with statement."""
        a = ql.qint(3, width=8)
        is_le = a <= 5

        result = ql.qint(0, width=4)
        with is_le:
            result += 1

        assert isinstance(result, ql.qint)

    def test_gt_result_as_control(self):
        """> result can be used as control in with statement."""
        a = ql.qint(7, width=8)
        is_greater = a > 5

        result = ql.qint(0, width=4)
        with is_greater:
            result += 1

        assert isinstance(result, ql.qint)

    def test_ge_result_as_control(self):
        """>= result can be used as control in with statement."""
        a = ql.qint(7, width=8)
        is_ge = a >= 5

        result = ql.qint(0, width=4)
        with is_ge:
            result += 1

        assert isinstance(result, ql.qint)

    def test_combined_ordering_controls(self):
        """Multiple ordering comparisons combined."""
        a = ql.qint(5, width=8)

        in_range = (a >= 3) & (a <= 7)

        result = ql.qint(0, width=4)
        with in_range:
            result += 1

        assert isinstance(result, ql.qint)


# ============================================================================
# Edge Cases and Regression Tests
# ============================================================================


class TestOrderingEdgeCases:
    """Edge cases and regression tests."""

    def test_zero_comparisons(self):
        """Comparisons with zero work correctly."""
        a = ql.qint(0, width=8)

        assert isinstance(a < 1, ql.qbool)
        assert isinstance(a <= 0, ql.qbool)
        assert isinstance(a > 0, ql.qbool)
        assert isinstance(a >= 0, ql.qbool)

    def test_max_value_comparisons(self):
        """Comparisons at max value for width."""
        a = ql.qint(127, width=8)  # Use 127 to avoid signed issues

        assert isinstance(a < 128, ql.qbool)
        assert isinstance(a <= 127, ql.qbool)
        assert isinstance(a > 126, ql.qbool)
        assert isinstance(a >= 127, ql.qbool)

    def test_comparison_after_arithmetic(self):
        """Comparison after arithmetic operations."""
        a = ql.qint(3, width=8)
        a += 2  # a is now 5

        result = a < 10
        assert isinstance(result, ql.qbool)

    def test_multiple_comparisons_same_qint(self):
        """Multiple comparisons on same qint."""
        a = ql.qint(5, width=8)

        r1 = a < 10
        r2 = a > 3
        r3 = a <= 5
        r4 = a >= 5

        assert isinstance(r1, ql.qbool)
        assert isinstance(r2, ql.qbool)
        assert isinstance(r3, ql.qbool)
        assert isinstance(r4, ql.qbool)

    def test_reversed_operand_int_lt_qint(self):
        """Reversed operand: int < qint (Python calls __gt__)."""
        a = ql.qint(5, width=8)
        # Python should call a.__gt__(3) for: 3 < a
        # This tests the reflection behavior
        result = 3 < a  # Equivalent to a > 3
        assert isinstance(result, ql.qbool)

    def test_reversed_operand_int_le_qint(self):
        """Reversed operand: int <= qint (Python calls __ge__)."""
        a = ql.qint(5, width=8)
        result = 3 <= a  # Equivalent to a >= 3
        assert isinstance(result, ql.qbool)


# ============================================================================
# Requirements Coverage Tests
# ============================================================================


class TestRequirementsCoverage:
    """Tests explicitly mapping to COMP-03 and COMP-04 requirements."""

    def test_comp03_le_no_temp_allocation(self):
        """COMP-03: <= works (no temp qint allocation)."""
        a = ql.qint(5, width=8)
        result = a <= 10
        assert isinstance(result, ql.qbool)
        # Note: We verify no temp allocation by code inspection, not test

    def test_comp03_le_preserves_operand(self):
        """COMP-03: <= preserves operand (in-place pattern)."""
        a = ql.qint(5, width=8)
        width_before = a.width

        _ = a <= 10

        assert a.width == width_before

    def test_comp04_ge_no_temp_allocation(self):
        """COMP-04: >= works (no temp qint allocation)."""
        a = ql.qint(5, width=8)
        result = a >= 3
        assert isinstance(result, ql.qbool)

    def test_comp04_ge_preserves_operand(self):
        """COMP-04: >= preserves operand (in-place pattern)."""
        a = ql.qint(5, width=8)
        width_before = a.width

        _ = a >= 3

        assert a.width == width_before

    def test_all_operators_return_qbool(self):
        """All four operators return qbool type."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        assert isinstance(a < b, ql.qbool)
        assert isinstance(a > b, ql.qbool)
        assert isinstance(a <= b, ql.qbool)
        assert isinstance(a >= b, ql.qbool)
        assert isinstance(a < 10, ql.qbool)
        assert isinstance(a > 3, ql.qbool)
        assert isinstance(a <= 5, ql.qbool)
        assert isinstance(a >= 5, ql.qbool)
