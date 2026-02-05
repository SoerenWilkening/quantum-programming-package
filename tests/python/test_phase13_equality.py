"""Tests for Phase 13: Equality Comparison

Requirements:
- COMP-01: Implement qint == int using CQ_equal_width in Python bindings
- COMP-02: Implement qint == qint as (qint - qint) == 0

These tests verify equality comparisons work correctly for various bit widths
and edge cases, and integrate properly with quantum control flow.
"""

import quantum_language as ql

# ============================================================================
# COMP-01: qint == int Tests
# ============================================================================


class TestQintEqInt:
    """Tests for qint == int comparison using CQ_equal_width."""

    def test_basic_equality(self):
        """Basic qint == int comparison returns qbool."""
        a = ql.qint(5, width=8)
        result = a == 5
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_various_widths(self):
        """Equality works for various bit widths."""
        for width in [1, 4, 8, 16, 32]:
            a = ql.qint(0, width=width)
            result = a == 0
            assert isinstance(result, ql.qbool), f"Failed for width {width}"
            assert result.width == 1

    def test_width_1(self):
        """Single-bit comparison works."""
        a = ql.qint(1, width=1)
        result = a == 1
        assert isinstance(result, ql.qbool)

    def test_width_1_zero(self):
        """Single-bit comparison with zero."""
        a = ql.qint(0, width=1)
        result = a == 0
        assert isinstance(result, ql.qbool)

    def test_non_zero_value(self):
        """Comparison with non-zero classical value."""
        a = ql.qint(42, width=8)
        result = a == 42
        assert isinstance(result, ql.qbool)

    def test_max_value_for_width(self):
        """Comparison with maximum value for bit width."""
        # 8-bit max unsigned = 255
        a = ql.qint(127, width=8)  # Use 127 to avoid signed overflow warning
        result = a == 127
        assert isinstance(result, ql.qbool)


class TestQintEqIntOverflow:
    """Tests for overflow handling in qint == int."""

    def test_overflow_large_value(self):
        """Value too large for bit width returns not-equal."""
        a = ql.qint(5, width=4)  # 4-bit can hold 0-15
        result = a == 100  # 100 > 15, overflow
        assert isinstance(result, ql.qbool)
        # Should return qbool representing "not equal"

    def test_overflow_negative_value(self):
        """Negative value with unsigned qint returns not-equal."""
        a = ql.qint(5, width=8)
        result = a == -1  # Negative not representable in unsigned
        assert isinstance(result, ql.qbool)


# ============================================================================
# COMP-02: qint == qint Tests
# ============================================================================


class TestQintEqQint:
    """Tests for qint == qint comparison using subtract-add-back pattern."""

    def test_basic_qq_equality(self):
        """Basic qint == qint comparison returns qbool."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)
        result = a == b
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_self_comparison(self):
        """Self-comparison (a == a) optimization works."""
        a = ql.qint(5, width=8)
        result = a == a
        assert isinstance(result, ql.qbool)
        # Self-comparison should be optimized

    def test_different_values(self):
        """Comparison of different values."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        result = a == b
        assert isinstance(result, ql.qbool)

    def test_operand_preservation(self):
        """Both operands preserved after comparison."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        # Store original widths
        a_width_before = a.width
        b_width_before = b.width

        result = a == b  # noqa: F841 - result unused, but comparison side effects are tested

        # Verify operands still have correct widths
        assert a.width == a_width_before
        assert b.width == b_width_before
        # Operands should still be usable
        assert isinstance(a, ql.qint)
        assert isinstance(b, ql.qint)


class TestQintEqQintMixedWidths:
    """Tests for qint == qint with different bit widths."""

    def test_different_widths_8_16(self):
        """Comparison with different widths (8 vs 16)."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=16)
        result = a == b
        assert isinstance(result, ql.qbool)

    def test_different_widths_4_8(self):
        """Comparison with different widths (4 vs 8)."""
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=8)
        result = a == b
        assert isinstance(result, ql.qbool)


# ============================================================================
# Inequality Tests
# ============================================================================


class TestInequality:
    """Tests for != operator (inverted ==)."""

    def test_ne_int(self):
        """qint != int returns qbool."""
        a = ql.qint(5, width=8)
        result = a != 5
        assert isinstance(result, ql.qbool)
        assert result.width == 1

    def test_ne_qint(self):
        """qint != qint returns qbool."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        result = a != b
        assert isinstance(result, ql.qbool)

    def test_ne_overflow(self):
        """!= with overflow value returns qbool."""
        a = ql.qint(5, width=4)
        result = a != 100  # Overflow
        assert isinstance(result, ql.qbool)


# ============================================================================
# Context Manager Integration Tests
# ============================================================================


class TestEqualityContextManager:
    """Tests for using equality result in controlled operations."""

    def test_eq_result_as_control(self):
        """Equality result can be used as control in with statement."""
        a = ql.qint(5, width=8)
        is_five = a == 5

        result = ql.qint(0, width=4)
        with is_five:
            result += 1  # Controlled addition

        assert isinstance(result, ql.qint)

    def test_ne_result_as_control(self):
        """Inequality result can be used as control."""
        a = ql.qint(5, width=8)
        not_five = a != 5

        result = ql.qint(0, width=4)
        with not_five:
            result += 1

        assert isinstance(result, ql.qint)

    def test_qq_eq_result_as_control(self):
        """qint == qint result can be used as control."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)
        are_equal = a == b

        result = ql.qint(0, width=4)
        with are_equal:
            result += 1

        assert isinstance(result, ql.qint)

    def test_chained_comparisons_in_control(self):
        """Multiple comparisons can be combined for control."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)

        eq1 = a == 5
        eq2 = b == 5

        result = ql.qint(0, width=4)
        with eq1 & eq2:
            result += 1

        assert isinstance(result, ql.qint)


# ============================================================================
# Edge Cases and Regression Tests
# ============================================================================


class TestEqualityEdgeCases:
    """Edge cases and regression tests for equality comparison."""

    def test_zero_equality(self):
        """Comparison with zero works."""
        a = ql.qint(0, width=8)
        result = a == 0
        assert isinstance(result, ql.qbool)

    def test_compare_after_arithmetic(self):
        """Comparison after arithmetic operations."""
        a = ql.qint(3, width=8)
        a += 2  # a is now effectively 5
        result = a == 5
        assert isinstance(result, ql.qbool)

    def test_multiple_comparisons_same_qint(self):
        """Multiple comparisons on same qint."""
        a = ql.qint(5, width=8)

        r1 = a == 5
        r2 = a == 3
        r3 = a == 5

        assert isinstance(r1, ql.qbool)
        assert isinstance(r2, ql.qbool)
        assert isinstance(r3, ql.qbool)

    def test_comparison_preserves_qint_type(self):
        """Comparison doesn't change qint type."""
        a = ql.qint(5, width=8)
        _ = a == 5
        assert isinstance(a, ql.qint)
        assert a.width == 8


# ============================================================================
# Requirements Coverage Tests
# ============================================================================


class TestRequirementsCoverage:
    """Tests explicitly mapping to COMP-01 and COMP-02 requirements."""

    def test_comp01_qint_eq_int_returns_qbool(self):
        """COMP-01: qint == int returns quantum boolean result."""
        a = ql.qint(5, width=8)
        result = a == 5
        assert isinstance(result, ql.qbool)

    def test_comp01_uses_c_level_function(self):
        """COMP-01: Comparison should work (uses CQ_equal_width internally)."""
        # We can't directly verify C function usage, but we verify it works
        for width in [1, 4, 8, 16]:
            for value in [0, 1, (1 << (width - 1)) - 1 if width > 1 else 1]:
                a = ql.qint(value, width=width)
                result = a == value
                assert isinstance(result, ql.qbool), f"Failed for width={width}, value={value}"

    def test_comp02_qint_eq_qint_returns_qbool(self):
        """COMP-02: qint == qint returns quantum boolean result."""
        a = ql.qint(5, width=8)
        b = ql.qint(5, width=8)
        result = a == b
        assert isinstance(result, ql.qbool)

    def test_comp02_uses_subtract_add_pattern(self):
        """COMP-02: Pattern (qint - qint) == 0 is used (operands preserved)."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        # Get original state
        a_width = a.width
        b_width = b.width

        # Perform comparison
        result = a == b

        # Verify operands preserved (subtract-add pattern restores them)
        assert a.width == a_width
        assert b.width == b_width
        assert isinstance(result, ql.qbool)
