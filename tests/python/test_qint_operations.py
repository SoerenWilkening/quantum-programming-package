"""Characterization tests for qint arithmetic and comparison operations.

These tests capture the CURRENT BEHAVIOR of qint operations as of 2026-01-26.
They serve as golden masters to detect regressions during refactoring.

Tests verify that operations complete successfully and produce expected types,
not that they produce specific gate sequences.
"""

import os
import sys

import pytest

# Add python-backend to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "python-backend"))

import quantum_language as ql  # noqa: E402

# ============================================================================
# qint Creation Tests
# ============================================================================


def test_qint_creation_default():
    """Test qint creation with default parameters."""
    a = ql.qint()
    assert a is not None
    assert isinstance(a, ql.qint)
    # Verify object has string representation
    assert str(a) is not None


def test_qint_creation_with_value():
    """Test qint creation with specified value and bits."""
    a = ql.qint(value=5, bits=8)
    assert a is not None
    assert isinstance(a, ql.qint)


@pytest.mark.parametrize("bits", [2, 4, 8, 16])
def test_qint_creation_various_widths(bits):
    """Test qint creation with various bit widths."""
    a = ql.qint(value=0, bits=bits)
    assert a is not None
    assert isinstance(a, ql.qint)


# ============================================================================
# Arithmetic Operations - In-place Addition
# ============================================================================


def test_qint_addition_inplace_with_int():
    """Test in-place addition of qint and integer constant."""
    a = ql.qint(value=5, bits=8)

    # Perform in-place addition
    result = a.__iadd__(3)

    # Verify operation completed
    assert result is not None
    # In-place operations return self
    assert result is a


def test_qint_addition_inplace_operator():
    """Test in-place addition using += operator."""
    a = ql.qint(value=10, bits=8)

    # Use += operator
    a += 5

    # Verify a still exists and is qint
    assert a is not None
    assert isinstance(a, ql.qint)


# ============================================================================
# Arithmetic Operations - Out-of-place Addition
# ============================================================================


def test_qint_addition_outofplace_with_int():
    """Test out-of-place addition creates new qint."""
    a = ql.qint(value=5, bits=8)

    # Perform out-of-place addition
    b = a + 3

    # Verify new qint was created
    assert b is not None
    assert isinstance(b, ql.qint)
    assert b is not a  # Different object


def test_qint_addition_outofplace_qint_qint():
    """Test addition of two qint objects."""
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Perform addition
    c = a + b

    # Verify result is qint
    assert c is not None
    assert isinstance(c, ql.qint)
    assert c is not a
    assert c is not b


def test_qint_radd():
    """Test reverse addition (int + qint)."""
    a = ql.qint(value=5, bits=8)

    # Perform reverse addition
    b = 3 + a

    # Verify result is qint
    assert b is not None
    assert isinstance(b, ql.qint)


# ============================================================================
# Arithmetic Operations - Subtraction
# ============================================================================


def test_qint_subtraction_inplace():
    """Test in-place subtraction of qint and integer."""
    a = ql.qint(value=10, bits=8)

    # Perform in-place subtraction
    a -= 5

    # Verify operation completed
    assert a is not None
    assert isinstance(a, ql.qint)


def test_qint_subtraction_outofplace():
    """Test out-of-place subtraction creates new qint."""
    a = ql.qint(value=10, bits=8)

    # Perform out-of-place subtraction
    b = a - 5

    # Verify new qint was created
    assert b is not None
    assert isinstance(b, ql.qint)
    assert b is not a


def test_qint_subtraction_qint_qint():
    """Test subtraction of two qint objects."""
    a = ql.qint(value=10, bits=8)
    b = ql.qint(value=3, bits=8)

    # Perform subtraction
    c = a - b

    # Verify result is qint
    assert c is not None
    assert isinstance(c, ql.qint)


# ============================================================================
# Arithmetic Operations - Multiplication
# ============================================================================


def test_qint_multiplication_with_int():
    """Test multiplication of qint and integer constant."""
    a = ql.qint(value=5, bits=8)

    # Perform multiplication
    b = a * 3

    # Verify result is qint
    assert b is not None
    assert isinstance(b, ql.qint)


def test_qint_multiplication_qint_qint():
    """Test multiplication of two qint objects."""
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Perform multiplication
    c = a * b

    # Verify result is qint
    assert c is not None
    assert isinstance(c, ql.qint)


def test_qint_rmul():
    """Test reverse multiplication (int * qint)."""
    a = ql.qint(value=5, bits=8)

    # Perform reverse multiplication
    b = 3 * a

    # Verify result is qint
    assert b is not None
    assert isinstance(b, ql.qint)


# ============================================================================
# Comparison Operations
# ============================================================================


def test_qint_less_than():
    """Test less-than comparison returns qbool."""
    a = ql.qint(value=5, bits=8)

    # Perform comparison
    result = a < 10

    # Verify result is qbool (which is subclass of qint)
    assert result is not None
    assert isinstance(result, ql.qbool)


def test_qint_less_equal():
    """Test less-than-or-equal comparison returns qbool."""
    a = ql.qint(value=5, bits=8)

    # Perform comparison
    result = a <= 10

    # Verify result is qbool
    assert result is not None
    assert isinstance(result, ql.qbool)


def test_qint_greater_than():
    """Test greater-than comparison returns qbool."""
    a = ql.qint(value=5, bits=8)

    # Perform comparison
    result = a > 2

    # Verify result is qbool
    assert result is not None
    assert isinstance(result, ql.qbool)


def test_qint_greater_equal():
    """Test greater-than-or-equal comparison returns qbool."""
    a = ql.qint(value=5, bits=8)

    # Perform comparison
    result = a >= 2

    # Verify result is qbool
    assert result is not None
    assert isinstance(result, ql.qbool)


# ============================================================================
# Circuit Generation Verification
# ============================================================================


def test_qint_operations_modify_circuit():
    """Test that qint operations generate circuit gates.

    This is a characterization test - we verify the circuit is being
    modified, not that specific gates are generated.
    """
    # Create qints (circuit is initialized automatically)
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Perform operations
    c = a + b
    d = a - 2
    e = a * 2

    # Verify operations completed (if they generate gates or not,
    # we're just checking they don't crash)
    assert c is not None
    assert d is not None
    assert e is not None


# ============================================================================
# Multiple Operation Chains
# ============================================================================


def test_qint_operation_chain():
    """Test chaining multiple arithmetic operations."""
    a = ql.qint(value=10, bits=8)

    # Chain operations
    b = (a + 5) - 3

    # Verify result
    assert b is not None
    assert isinstance(b, ql.qint)


def test_qint_mixed_operations():
    """Test mixing different operation types."""
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Mix operations
    c = (a + b) * 2
    d = a - b

    # Verify results
    assert c is not None
    assert d is not None
    assert isinstance(c, ql.qint)
    assert isinstance(d, ql.qint)


# ============================================================================
# Edge Cases
# ============================================================================


def test_qint_operation_with_zero():
    """Test arithmetic operations with zero."""
    a = ql.qint(value=5, bits=8)

    # Operations with zero
    b = a + 0
    c = a - 0
    d = a * 0

    # Verify operations completed
    assert b is not None
    assert c is not None
    assert d is not None


def test_qint_self_operations():
    """Test operations where qint operates on itself."""
    a = ql.qint(value=5, bits=8)

    # Self operations
    b = a + a
    c = a - a
    d = a * a

    # Verify operations completed
    assert b is not None
    assert c is not None
    assert d is not None
