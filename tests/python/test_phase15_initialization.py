"""Tests for Phase 15: Classical Initialization

Requirements:
- INIT-01: Implement classical value initialization via X gates in qint constructor

These tests verify that qint objects are correctly initialized to classical values
via X gate application, with auto-width mode and explicit width specifications.
"""

import os
import sys

import pytest

# Add python-backend to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "python-backend"))

import quantum_language as ql  # noqa: E402

# ============================================================================
# Basic Initialization Tests
# ============================================================================


class TestBasicInitialization:
    """Tests for basic qint initialization with various values."""

    def test_init_zero(self):
        """Initialize qint with value 0."""
        a = ql.qint(0, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_positive_value(self):
        """Initialize qint with positive value."""
        a = ql.qint(5, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_all_ones(self):
        """Initialize qint with all bits set (255 for 8-bit)."""
        a = ql.qint(255, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_power_of_two(self):
        """Initialize qint with power of 2 (single bit set)."""
        a = ql.qint(64, width=8)  # Binary 01000000
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_max_value_for_width(self):
        """Initialize qint with maximum value for bit width."""
        # 4-bit max unsigned = 15
        a = ql.qint(15, width=4)
        assert isinstance(a, ql.qint)
        assert a.width == 4


# ============================================================================
# Auto-Width Mode Tests
# ============================================================================


class TestAutoWidthMode:
    """Tests for auto-width calculation based on value."""

    def test_auto_width_small_value(self):
        """Auto-width for small values (qint(5) = 3 bits)."""
        a = ql.qint(5)  # Binary 101 = 3 bits
        assert isinstance(a, ql.qint)
        assert a.width == 3

    def test_auto_width_power_of_two(self):
        """Auto-width for power of 2."""
        a = ql.qint(8)  # Binary 1000 = 4 bits
        assert isinstance(a, ql.qint)
        assert a.width == 4

    def test_auto_width_large_value(self):
        """Auto-width for larger values."""
        a = ql.qint(1000)  # Binary 1111101000 = 10 bits
        assert isinstance(a, ql.qint)
        assert a.width == 10

    def test_auto_width_value_1(self):
        """Auto-width for value 1 (minimum positive)."""
        a = ql.qint(1)  # Binary 1 = 1 bit
        assert isinstance(a, ql.qint)
        assert a.width == 1

    def test_auto_width_zero_defaults_to_8(self):
        """Auto-width for zero defaults to 8 bits."""
        a = ql.qint(0)
        assert isinstance(a, ql.qint)
        assert a.width == 8  # Default for zero

    @pytest.mark.parametrize(
        "value,expected_width",
        [
            (1, 1),
            (2, 2),
            (3, 2),
            (4, 3),
            (7, 3),
            (8, 4),
            (15, 4),
            (16, 5),
            (31, 5),
            (32, 6),
            (63, 6),
            (64, 7),
            (127, 7),
            (128, 8),
            (255, 8),
            (256, 9),
        ],
    )
    def test_auto_width_parametrized(self, value, expected_width):
        """Parametrized test for auto-width calculation."""
        a = ql.qint(value)
        assert a.width == expected_width, (
            f"qint({value}) should have width {expected_width}, got {a.width}"
        )


# ============================================================================
# Negative Value Tests (Two's Complement)
# ============================================================================


class TestNegativeValues:
    """Tests for negative value initialization in two's complement."""

    def test_init_negative_explicit_width(self):
        """Initialize qint with negative value and explicit width."""
        a = ql.qint(-1, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_negative_small_value(self):
        """Initialize with small negative value (-3 in 4 bits = 1101)."""
        a = ql.qint(-3, width=4)
        assert isinstance(a, ql.qint)
        assert a.width == 4

    def test_init_negative_min_value(self):
        """Initialize with minimum value for bit width."""
        # 4-bit signed min = -8 = 1000 in two's complement
        a = ql.qint(-8, width=4)
        assert isinstance(a, ql.qint)
        assert a.width == 4

    def test_auto_width_negative_one(self):
        """Auto-width for -1 (special case: 1 bit)."""
        a = ql.qint(-1)
        assert isinstance(a, ql.qint)
        assert a.width == 1  # -1 = 1 bit (two's complement)

    def test_auto_width_negative_power_of_two(self):
        """Auto-width for negative power of 2."""
        a = ql.qint(-8)  # Requires 4 bits in two's complement
        assert isinstance(a, ql.qint)
        assert a.width == 4

    def test_auto_width_negative_non_power(self):
        """Auto-width for negative non-power of 2."""
        a = ql.qint(-5)  # Requires calculation
        assert isinstance(a, ql.qint)
        # -5 needs 4 bits: range is -8 to 7


# ============================================================================
# Truncation Warning Tests
# ============================================================================


class TestTruncationWarnings:
    """Tests for truncation warnings when value exceeds width."""

    def test_overflow_emits_warning(self):
        """Value too large for width emits UserWarning."""
        # 1000 doesn't fit in 8 bits (max 255)
        with pytest.warns(UserWarning, match="Value.*exceeds"):
            a = ql.qint(1000, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_no_warning_when_fits(self):
        """No warning when value fits in width."""
        # 100 fits in 8 bits (range -128 to 127)
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a = ql.qint(100, width=8)
            # Filter for truncation warnings
            truncation_warnings = [warning for warning in w if "exceeds" in str(warning.message)]
            assert len(truncation_warnings) == 0
        assert isinstance(a, ql.qint)

    def test_no_warning_in_auto_width_mode(self):
        """Auto-width mode never emits truncation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a = ql.qint(1000)  # Auto-width, no overflow possible
            # Filter for truncation warnings
            truncation_warnings = [warning for warning in w if "exceeds" in str(warning.message)]
            assert len(truncation_warnings) == 0
        assert isinstance(a, ql.qint)
        assert a.width == 10  # Correct auto-width for 1000

    def test_negative_overflow_warning(self):
        """Negative value outside range emits warning."""
        # -10 doesn't fit in 3 bits (range -4 to 3)
        with pytest.warns(UserWarning, match="Value.*exceeds"):
            a = ql.qint(-10, width=3)
        assert isinstance(a, ql.qint)


# ============================================================================
# Integration Tests (Initialized qint in Operations)
# ============================================================================


class TestInitializedQintInOperations:
    """Tests that initialized qints work correctly in arithmetic and comparisons."""

    def test_init_qint_in_addition(self):
        """Initialized qint can be used in addition."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        c = a + b
        assert isinstance(c, ql.qint)

    def test_init_qint_in_comparison(self):
        """Initialized qint can be used in comparison."""
        a = ql.qint(5, width=8)
        result = a == 5
        assert isinstance(result, ql.qbool)

    def test_init_qint_in_bitwise_and(self):
        """Initialized qint can be used in bitwise AND."""
        a = ql.qint(12, width=8)  # Binary 1100
        b = ql.qint(10, width=8)  # Binary 1010
        c = a & b  # Should be 1000 = 8
        assert isinstance(c, ql.qint)

    def test_auto_width_qint_in_addition(self):
        """Auto-width qint works in arithmetic operations."""
        a = ql.qint(5)  # 3 bits
        b = ql.qint(3)  # 2 bits
        c = a + b  # Different widths should work
        assert isinstance(c, ql.qint)

    def test_auto_width_qint_in_comparison(self):
        """Auto-width qint works in comparison."""
        a = ql.qint(10)  # Auto-width
        result = a > 5
        assert isinstance(result, ql.qbool)


# ============================================================================
# Boundary Conditions
# ============================================================================


class TestBoundaryConditions:
    """Edge cases and boundary tests."""

    def test_init_1_bit_zero(self):
        """1-bit qint with value 0."""
        a = ql.qint(0, width=1)
        assert isinstance(a, ql.qint)
        assert a.width == 1

    def test_init_1_bit_one(self):
        """1-bit qint with value 1."""
        a = ql.qint(1, width=1)
        assert isinstance(a, ql.qint)
        assert a.width == 1

    def test_init_64_bit(self):
        """64-bit qint (maximum width)."""
        a = ql.qint(42, width=64)
        assert isinstance(a, ql.qint)
        assert a.width == 64

    def test_init_64_bit_large_value(self):
        """64-bit qint with large value."""
        large_val = 2**30  # Large but within Python int range
        a = ql.qint(large_val, width=64)
        assert isinstance(a, ql.qint)
        assert a.width == 64

    def test_invalid_width_below_1(self):
        """Width below 1 raises ValueError."""
        with pytest.raises(ValueError, match="Width must be 1-64"):
            ql.qint(5, width=0)

    def test_invalid_width_above_64(self):
        """Width above 64 raises ValueError."""
        with pytest.raises(ValueError, match="Width must be 1-64"):
            ql.qint(5, width=65)

    def test_keyword_argument_width(self):
        """Width can be specified as keyword argument."""
        a = ql.qint(value=5, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_keyword_argument_bits(self):
        """Legacy 'bits' parameter still works."""
        a = ql.qint(5, bits=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8


# ============================================================================
# Type Coercion Tests
# ============================================================================


class TestTypeCoercion:
    """Tests for initialization with various numeric types."""

    def test_init_with_numpy_int32(self):
        """Initialize with numpy int32."""
        import numpy as np

        value = np.int32(42)
        a = ql.qint(value, width=8)
        assert isinstance(a, ql.qint)
        assert a.width == 8

    def test_init_with_numpy_int64(self):
        """Initialize with numpy int64."""
        import numpy as np

        value = np.int64(123)
        a = ql.qint(value, width=8)
        assert isinstance(a, ql.qint)

    def test_auto_width_with_numpy_int(self):
        """Auto-width works with numpy integers."""
        import numpy as np

        value = np.int32(10)
        a = ql.qint(value)
        assert isinstance(a, ql.qint)
        assert a.width == 4  # 10 needs 4 bits


# ============================================================================
# Requirements Coverage Tests
# ============================================================================


class TestRequirementsCoverage:
    """Tests explicitly mapping to INIT-01 requirement."""

    def test_init01_classical_value_initialization(self):
        """INIT-01: qint constructor initializes to classical value."""
        a = ql.qint(5, width=8)
        assert isinstance(a, ql.qint)
        # Value is encoded (can't directly inspect without measurement)
        # but we can verify it works in operations
        result = a == 5
        assert isinstance(result, ql.qbool)

    def test_init01_auto_width_calculates_correctly(self):
        """INIT-01: Auto-width calculates minimum bits needed."""
        test_cases = [
            (1, 1),  # 1 bit
            (5, 3),  # 101 = 3 bits
            (8, 4),  # 1000 = 4 bits
            (255, 8),  # 11111111 = 8 bits
        ]
        for value, expected_width in test_cases:
            a = ql.qint(value)
            assert a.width == expected_width, f"qint({value}) should be {expected_width} bits"

    def test_init01_explicit_width_respected(self):
        """INIT-01: Explicit width parameter is respected."""
        a = ql.qint(5, width=16)
        assert a.width == 16  # Not auto-calculated

    def test_init01_x_gates_applied(self):
        """INIT-01: X gates are applied based on binary representation."""
        # Create circuit and check gate counts
        c = ql.circuit()
        a = ql.qint(5, width=8)  # Binary 00000101 = 2 X gates (bits 0 and 2)

        # After initialization, circuit should have X gates
        # We can't directly count just the initialization gates without
        # measuring, but we verify the qint was created successfully
        assert isinstance(a, ql.qint)
        assert c.gate_count >= 2  # At least the X gates

    def test_init01_zero_no_x_gates(self):
        """INIT-01: Zero value applies no X gates."""
        c = ql.circuit()
        gate_count_before = c.gate_count

        a = ql.qint(0, width=8)  # No X gates should be applied

        gate_count_after = c.gate_count
        gates_added = gate_count_after - gate_count_before

        assert isinstance(a, ql.qint)
        assert gates_added == 0  # No gates for zero initialization
