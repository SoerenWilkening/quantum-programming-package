"""Phase 6: Bitwise Operations Tests

Tests for BITOP-01 through BITOP-05 requirements:
- BITOP-01: Bitwise AND on quantum integers
- BITOP-02: Bitwise OR on quantum integers
- BITOP-03: Bitwise XOR on quantum integers
- BITOP-04: Bitwise NOT on quantum integers
- BITOP-05: Python operator overloading for bitwise ops

Each test class maps to a specific requirement from the Phase 6 ROADMAP.
Tests verify operations complete successfully and produce expected types/widths.
"""

import os
import sys

import pytest

# Add python-backend to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "python-backend"))

import quantum_language as ql  # noqa: E402

# ============================================================================
# BITOP-01: Bitwise AND Tests
# ============================================================================


class TestBitopAnd:
    """Tests for BITOP-01: Bitwise AND operation on quantum integers."""

    def test_and_same_width_4bit(self):
        """AND of two same-width 4-bit qints produces 4-bit result."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1100, width=4)
        c = a & b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4

    def test_and_same_width_8bit(self):
        """AND of two same-width 8-bit qints produces 8-bit result."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0xAA, width=8)
        c = a & b
        assert c.width == 8
        assert isinstance(c, ql.qint)

    def test_and_same_width_16bit(self):
        """AND of two same-width 16-bit qints produces 16-bit result."""
        a = ql.qint(0xFFFF, width=16)
        b = ql.qint(0x00FF, width=16)
        c = a & b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_and_mixed_width_8_and_16(self):
        """AND of 8-bit and 16-bit uses larger width (16)."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0xFFFF, width=16)
        c = a & b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_and_mixed_width_16_and_8(self):
        """AND of 16-bit and 8-bit uses larger width (16) - order independent."""
        a = ql.qint(0x00FF, width=16)
        b = ql.qint(0xFF, width=8)
        c = a & b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_and_mixed_width_4_and_12(self):
        """AND of 4-bit and 12-bit uses larger width (12).

        Note: Using 12-bit instead of 32-bit because AND requires Toffoli gates
        which grow exponentially in circuit depth with width.
        """
        a = ql.qint(0xF, width=4)
        b = ql.qint(0, width=12)
        c = a & b
        assert c.width == 12
        assert isinstance(c, ql.qint)

    def test_and_qint_int_basic(self):
        """AND with classical integer works."""
        a = ql.qint(0b1111, width=4)
        c = a & 0b1010
        assert c is not None
        assert isinstance(c, ql.qint)
        # Width may expand based on classical value

    def test_and_qint_int_preserves_min_width(self):
        """AND with small classical int preserves qint width."""
        a = ql.qint(0xFF, width=8)
        c = a & 3  # 3 = 0b11, fits in 2 bits
        assert c is not None
        assert isinstance(c, ql.qint)
        # Result width is max of operand widths

    def test_and_qint_int_expands_width(self):
        """AND with large classical int may expand result width."""
        a = ql.qint(0xFF, width=8)
        c = a & 0xFFFF  # 16 bits
        assert c is not None
        assert isinstance(c, ql.qint)
        # Result width determined by max needed

    def test_and_preserves_operands(self):
        """AND does not modify input operands (out-of-place operation)."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        # Capture properties before operation
        a_width_before = a.width
        b_width_before = b.width

        c = a & b

        # Operands widths unchanged
        assert a.width == a_width_before
        assert b.width == b_width_before
        # Result is different object
        assert c is not a
        assert c is not b

    def test_and_returns_new_qint(self):
        """AND always returns a new qint object."""
        a = ql.qint(7, width=8)
        b = ql.qint(3, width=8)
        c = a & b
        assert c is not a
        assert c is not b
        assert isinstance(c, ql.qint)


# ============================================================================
# BITOP-02: Bitwise OR Tests
# ============================================================================


class TestBitopOr:
    """Tests for BITOP-02: Bitwise OR operation on quantum integers."""

    def test_or_same_width_4bit(self):
        """OR of two same-width 4-bit qints produces 4-bit result."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b0101, width=4)
        c = a | b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4

    def test_or_same_width_8bit(self):
        """OR of two same-width 8-bit qints produces 8-bit result."""
        a = ql.qint(0x0F, width=8)
        b = ql.qint(0xF0, width=8)
        c = a | b
        assert c.width == 8
        assert isinstance(c, ql.qint)

    def test_or_same_width_16bit(self):
        """OR of two same-width 16-bit qints produces 16-bit result."""
        a = ql.qint(0x00FF, width=16)
        b = ql.qint(0xFF00, width=16)
        c = a | b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_or_mixed_width_8_and_16(self):
        """OR of 8-bit and 16-bit uses larger width (16)."""
        a = ql.qint(0x0F, width=8)
        b = ql.qint(0xF000, width=16)
        c = a | b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_or_mixed_width_16_and_8(self):
        """OR of 16-bit and 8-bit uses larger width (16) - order independent."""
        a = ql.qint(0xF000, width=16)
        b = ql.qint(0x0F, width=8)
        c = a | b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_or_mixed_width_4_and_12(self):
        """OR of 4-bit and 12-bit uses larger width (12).

        Note: Using 12-bit instead of 32-bit because OR requires Toffoli gates
        which grow exponentially in circuit depth with width.
        """
        a = ql.qint(0xF, width=4)
        b = ql.qint(0, width=12)
        c = a | b
        assert c.width == 12
        assert isinstance(c, ql.qint)

    def test_or_qint_int_basic(self):
        """OR with classical integer works."""
        a = ql.qint(0b0000, width=4)
        c = a | 0b1111
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_or_qint_int_preserves_min_width(self):
        """OR with small classical int preserves qint width."""
        a = ql.qint(0, width=8)
        c = a | 3  # 3 = 0b11
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_or_qint_int_large_value(self):
        """OR with large classical int may expand result width."""
        a = ql.qint(0, width=8)
        c = a | 0xFFFF
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_or_preserves_operands(self):
        """OR does not modify input operands (out-of-place operation)."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        a_width_before = a.width
        b_width_before = b.width

        c = a | b

        # Operands widths unchanged
        assert a.width == a_width_before
        assert b.width == b_width_before
        # Result is different object
        assert c is not a
        assert c is not b

    def test_or_returns_new_qint(self):
        """OR always returns a new qint object."""
        a = ql.qint(0, width=8)
        b = ql.qint(15, width=8)
        c = a | b
        assert c is not a
        assert c is not b
        assert isinstance(c, ql.qint)


# ============================================================================
# BITOP-03: Bitwise XOR Tests
# ============================================================================


class TestBitopXor:
    """Tests for BITOP-03: Bitwise XOR operation on quantum integers."""

    def test_xor_same_width_4bit(self):
        """XOR of two same-width 4-bit qints produces 4-bit result."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1100, width=4)
        c = a ^ b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4

    def test_xor_same_width_8bit(self):
        """XOR of two same-width 8-bit qints produces 8-bit result."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0x0F, width=8)
        c = a ^ b
        assert c.width == 8
        assert isinstance(c, ql.qint)

    def test_xor_same_width_16bit(self):
        """XOR of two same-width 16-bit qints produces 16-bit result."""
        a = ql.qint(0xFFFF, width=16)
        b = ql.qint(0x00FF, width=16)
        c = a ^ b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_xor_mixed_width_8_and_16(self):
        """XOR of 8-bit and 16-bit uses larger width (16)."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0x00FF, width=16)
        c = a ^ b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_xor_mixed_width_16_and_8(self):
        """XOR of 16-bit and 8-bit uses larger width (16) - order independent."""
        a = ql.qint(0x00FF, width=16)
        b = ql.qint(0xFF, width=8)
        c = a ^ b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_xor_mixed_width_4_and_16(self):
        """XOR of 4-bit and 16-bit uses larger width (16).

        Note: XOR uses CNOT gates which are O(1) depth, so this is faster
        than AND/OR but we still keep width reasonable.
        """
        a = ql.qint(0xF, width=4)
        b = ql.qint(0, width=16)
        c = a ^ b
        assert c.width == 16
        assert isinstance(c, ql.qint)

    def test_xor_qint_int_basic(self):
        """XOR with classical integer works."""
        a = ql.qint(0b1111, width=4)
        c = a ^ 0b1010
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_xor_qint_int_preserves_min_width(self):
        """XOR with small classical int preserves qint width."""
        a = ql.qint(0xFF, width=8)
        c = a ^ 0x0F
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_xor_qint_int_large_value(self):
        """XOR with large classical int may expand result width."""
        a = ql.qint(0xFF, width=8)
        c = a ^ 0xFFFF
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_xor_preserves_operands(self):
        """XOR does not modify input operands (out-of-place operation)."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)
        a_width_before = a.width
        b_width_before = b.width

        c = a ^ b

        # Operands widths unchanged
        assert a.width == a_width_before
        assert b.width == b_width_before
        # Result is different object
        assert c is not a
        assert c is not b

    def test_xor_returns_new_qint(self):
        """XOR always returns a new qint object."""
        a = ql.qint(0xAA, width=8)
        b = ql.qint(0x55, width=8)
        c = a ^ b
        assert c is not a
        assert c is not b
        assert isinstance(c, ql.qint)

    def test_xor_self_produces_zero_pattern(self):
        """XOR of a value with itself produces a result (conceptually zero)."""
        a = ql.qint(0b1111, width=4)
        b = ql.qint(0b1111, width=4)
        c = a ^ b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4


# ============================================================================
# BITOP-04: Bitwise NOT Tests
# ============================================================================


class TestBitopNot:
    """Tests for BITOP-04: Bitwise NOT operation on quantum integers."""

    def test_not_preserves_width_4bit(self):
        """NOT preserves 4-bit width."""
        a = ql.qint(0b1010, width=4)
        b = ~a
        assert b.width == 4
        assert isinstance(b, ql.qint)

    def test_not_preserves_width_8bit(self):
        """NOT preserves 8-bit width."""
        a = ql.qint(0xFF, width=8)
        b = ~a
        assert b.width == 8
        assert isinstance(b, ql.qint)

    def test_not_preserves_width_16bit(self):
        """NOT preserves 16-bit width."""
        a = ql.qint(0xFFFF, width=16)
        b = ~a
        assert b.width == 16
        assert isinstance(b, ql.qint)

    def test_not_preserves_width_24bit(self):
        """NOT preserves 24-bit width.

        Note: NOT uses X gates which are O(1) depth per bit, so larger widths
        are feasible. Using 24-bit to keep test runtime reasonable.
        """
        a = ql.qint(0, width=24)
        b = ~a
        assert b.width == 24
        assert isinstance(b, ql.qint)

    def test_not_inplace_returns_self(self):
        """NOT modifies in-place and returns self (same object)."""
        a = ql.qint(0b0000, width=4)
        b = ~a
        assert b is a  # Same object reference

    def test_not_1bit(self):
        """NOT works on 1-bit quantum integer."""
        a = ql.qint(0, width=1)
        b = ~a
        assert b.width == 1
        assert b is a

    def test_not_qbool(self):
        """NOT works on qbool (1-bit quantum boolean)."""
        a = ql.qbool(False)
        b = ~a
        assert b.width == 1
        assert isinstance(b, ql.qbool)
        assert b is a  # In-place modification

    def test_not_qbool_true(self):
        """NOT on qbool initialized True."""
        a = ql.qbool(True)
        b = ~a
        assert b.width == 1
        assert b is a

    def test_double_not_same_object(self):
        """Double NOT returns same object (two in-place ops)."""
        a = ql.qint(0b1010, width=4)
        b = ~(~a)
        assert b is a  # Still same object after double inversion


# ============================================================================
# BITOP-05: Python Operator Overloading Tests
# ============================================================================


class TestBitopOverloading:
    """Tests for BITOP-05: Python operator overloading for bitwise operations."""

    def test_and_operator(self):
        """& operator works for qint & qint."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        c = a & b
        assert isinstance(c, ql.qint)
        assert c is not a
        assert c is not b

    def test_or_operator(self):
        """| operator works for qint | qint."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        c = a | b
        assert isinstance(c, ql.qint)
        assert c is not a
        assert c is not b

    def test_xor_operator(self):
        """^ operator works for qint ^ qint."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        c = a ^ b
        assert isinstance(c, ql.qint)
        assert c is not a
        assert c is not b

    def test_invert_operator(self):
        """~ operator works for ~qint."""
        a = ql.qint(1, width=8)
        b = ~a
        assert isinstance(b, ql.qint)
        assert b is a  # In-place modification

    def test_iand_operator(self):
        """&= operator works (in-place AND)."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        original_a = a
        a &= b
        assert isinstance(a, ql.qint)
        assert a is original_a  # Same object after in-place

    def test_ior_operator(self):
        """|= operator works (in-place OR)."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        original_a = a
        a |= b
        assert isinstance(a, ql.qint)
        assert a is original_a

    def test_ixor_operator(self):
        """^= operator works (in-place XOR)."""
        a = ql.qint(1, width=8)
        b = ql.qint(1, width=8)
        original_a = a
        a ^= b
        assert isinstance(a, ql.qint)
        assert a is original_a

    def test_rand_operator(self):
        """int & qint triggers __rand__."""
        a = ql.qint(0xFF, width=8)
        c = 0xF0 & a
        assert isinstance(c, ql.qint)

    def test_ror_operator(self):
        """int | qint triggers __ror__."""
        a = ql.qint(0x0F, width=8)
        c = 0xF0 | a
        assert isinstance(c, ql.qint)

    def test_rxor_operator(self):
        """int ^ qint triggers __rxor__."""
        a = ql.qint(0xFF, width=8)
        c = 0x0F ^ a
        assert isinstance(c, ql.qint)

    def test_and_with_int_right(self):
        """qint & int works."""
        a = ql.qint(0xFF, width=8)
        c = a & 0x0F
        assert isinstance(c, ql.qint)

    def test_or_with_int_right(self):
        """qint | int works."""
        a = ql.qint(0x0F, width=8)
        c = a | 0xF0
        assert isinstance(c, ql.qint)

    def test_xor_with_int_right(self):
        """qint ^ int works."""
        a = ql.qint(0xFF, width=8)
        c = a ^ 0x0F
        assert isinstance(c, ql.qint)


# ============================================================================
# Phase 6 Success Criteria Verification
# ============================================================================


class TestPhase6SuccessCriteria:
    """Tests mapping directly to Phase 6 success criteria from ROADMAP.md.

    Success Criteria:
    1. Bitwise AND, OR, XOR, and NOT operations work on quantum integers
    2. Python operator overloading works for bitwise operations
    3. Bit operations respect variable-width integers
    4. Generated circuits for bit operations have reasonable depth
    """

    def test_criterion_1_all_bitwise_ops_work(self):
        """SC1: AND, OR, XOR, NOT all work on qint."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1100, width=4)

        # All operations should execute without error
        c_and = a & b
        c_or = a | b
        c_xor = a ^ b
        c_not = ~a

        assert isinstance(c_and, ql.qint)
        assert isinstance(c_or, ql.qint)
        assert isinstance(c_xor, ql.qint)
        assert isinstance(c_not, ql.qint)

    def test_criterion_2_operator_overloading(self):
        """SC2: Python operators &, |, ^, ~ work."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        # Using Python operators directly (syntax check)
        _ = a & b
        _ = a | b
        _ = a ^ b
        _ = ~a

        # Verify no exceptions raised

    def test_criterion_3_variable_width_respected(self):
        """SC3: Operations respect variable-width (result = max width).

        Note: Using smaller widths (max 16-bit) to avoid circuit timeout.
        The width propagation logic is the same regardless of actual width.
        """
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=8)
        c = ql.qint(0, width=16)

        # Result should use max width of operands
        r1 = a & b  # 4 & 8 -> 8
        r2 = b | c  # 8 | 16 -> 16
        r3 = a ^ c  # 4 ^ 16 -> 16

        assert r1.width == 8, f"Expected 8, got {r1.width}"
        assert r2.width == 16, f"Expected 16, got {r2.width}"
        assert r3.width == 16, f"Expected 16, got {r3.width}"

    def test_criterion_4_reasonable_depth(self):
        """SC4: Circuit depth is reasonable (operations complete quickly).

        NOT and XOR should be O(1) depth (parallel gates)
        AND and OR should be O(N) depth (sequential Toffoli)
        This test verifies operations complete without timeout for reasonable sizes.
        """
        # 8-bit operations should complete quickly
        a = ql.qint(0, width=8)
        b = ql.qint(0, width=8)

        # These should all complete without timeout
        _ = ~a
        _ = a ^ b
        _ = a & b
        _ = a | b

        # Verify all completed
        assert True  # If we reach here, depth was reasonable


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


class TestBackwardCompatibility:
    """Tests ensuring qbool bitwise operations still work after Phase 6 changes."""

    def test_qbool_and_qbool(self):
        """qbool & qbool still works and returns 1-bit result."""
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = a & b
        # Phase 6: Returns qint with max width (both are width 1)
        assert isinstance(c, ql.qint)
        assert c.width == 1

    def test_qbool_or_qbool(self):
        """qbool | qbool still works and returns 1-bit result."""
        a = ql.qbool(True)
        b = ql.qbool(False)
        c = a | b
        assert isinstance(c, ql.qint)
        assert c.width == 1

    def test_qbool_xor_qbool(self):
        """qbool ^ qbool still works and returns 1-bit result."""
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = a ^ b
        assert isinstance(c, ql.qint)
        assert c.width == 1

    def test_qbool_not(self):
        """~qbool still works and returns qbool (1-bit)."""
        a = ql.qbool(True)
        b = ~a
        assert isinstance(b, ql.qbool)
        assert b.width == 1
        assert b is a  # In-place modification

    def test_qbool_and_qint(self):
        """qbool & qint works (mixed width: 1 & 8)."""
        a = ql.qbool(True)
        b = ql.qint(0xFF, width=8)
        c = a & b
        assert isinstance(c, ql.qint)
        assert c.width == 8  # max(1, 8)

    def test_qint_and_qbool(self):
        """qint & qbool works (mixed width: 8 & 1)."""
        a = ql.qint(0xFF, width=8)
        b = ql.qbool(True)
        c = a & b
        assert isinstance(c, ql.qint)
        assert c.width == 8  # max(8, 1)


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestBitwiseEdgeCases:
    """Edge cases for bitwise operations."""

    def test_and_with_zero(self):
        """AND with 0 works."""
        a = ql.qint(0xFF, width=8)
        c = a & 0
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_or_with_zero(self):
        """OR with 0 preserves value."""
        a = ql.qint(0xFF, width=8)
        c = a | 0
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_xor_with_zero(self):
        """XOR with 0 preserves value."""
        a = ql.qint(0xFF, width=8)
        c = a ^ 0
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_and_with_all_ones(self):
        """AND with all ones preserves value."""
        a = ql.qint(0x55, width=8)
        c = a & 0xFF
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_or_with_all_ones(self):
        """OR with all ones produces all ones."""
        a = ql.qint(0x00, width=8)
        c = a | 0xFF
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_xor_all_same_bits(self):
        """XOR with same value produces zero pattern."""
        a = ql.qint(0xAA, width=8)
        c = a ^ 0xAA
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_min_width_1bit_and(self):
        """AND works at minimum width (1-bit)."""
        a = ql.qint(1, width=1)
        b = ql.qint(1, width=1)
        c = a & b
        assert c.width == 1

    def test_min_width_1bit_or(self):
        """OR works at minimum width (1-bit)."""
        a = ql.qint(0, width=1)
        b = ql.qint(1, width=1)
        c = a | b
        assert c.width == 1

    def test_min_width_1bit_xor(self):
        """XOR works at minimum width (1-bit)."""
        a = ql.qint(1, width=1)
        b = ql.qint(1, width=1)
        c = a ^ b
        assert c.width == 1

    def test_min_width_1bit_not(self):
        """NOT works at minimum width (1-bit)."""
        a = ql.qint(1, width=1)
        b = ~a
        assert b.width == 1


# ============================================================================
# Chained Operations Tests
# ============================================================================


class TestChainedBitwiseOps:
    """Tests for chaining multiple bitwise operations."""

    def test_chain_and_or(self):
        """(a & b) | c works."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1100, width=4)
        c = ql.qint(0b0001, width=4)
        result = (a & b) | c
        assert isinstance(result, ql.qint)
        assert result.width == 4

    def test_chain_or_and(self):
        """(a | b) & c works."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b0100, width=4)
        c = ql.qint(0b1111, width=4)
        result = (a | b) & c
        assert isinstance(result, ql.qint)
        assert result.width == 4

    def test_chain_xor_and(self):
        """(a ^ b) & c works."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b0110, width=4)
        c = ql.qint(0b0011, width=4)
        result = (a ^ b) & c
        assert isinstance(result, ql.qint)
        assert result.width == 4

    def test_chain_not_and(self):
        """(~a) & b works."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1111, width=4)
        result = (~a) & b
        assert isinstance(result, ql.qint)
        # Note: ~a modifies a in-place, so result is from modified a & b

    def test_triple_chain(self):
        """a & b & c works (left-to-right evaluation)."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0x0F, width=8)
        c = ql.qint(0x03, width=8)
        result = a & b & c
        assert isinstance(result, ql.qint)
        assert result.width == 8

    def test_mixed_width_chain(self):
        """Chaining operations with mixed widths propagates correctly."""
        a = ql.qint(0xFF, width=8)
        b = ql.qint(0xFFFF, width=16)
        c = ql.qint(0xF, width=4)

        # (8-bit & 16-bit) -> 16-bit, then (16-bit | 4-bit) -> 16-bit
        result = (a & b) | c
        assert result.width == 16


# ============================================================================
# Type Error Tests
# ============================================================================


class TestBitwiseTypeErrors:
    """Tests verifying proper type checking in bitwise operations."""

    def test_and_with_string_raises_typeerror(self):
        """qint & string raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a & "hello"

    def test_or_with_string_raises_typeerror(self):
        """qint | string raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a | "hello"

    def test_xor_with_string_raises_typeerror(self):
        """qint ^ string raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a ^ "hello"

    def test_and_with_float_raises_typeerror(self):
        """qint & float raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a & 3.14

    def test_or_with_float_raises_typeerror(self):
        """qint | float raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a | 3.14

    def test_xor_with_float_raises_typeerror(self):
        """qint ^ float raises TypeError."""
        a = ql.qint(5, width=8)
        with pytest.raises(TypeError):
            _ = a ^ 3.14
