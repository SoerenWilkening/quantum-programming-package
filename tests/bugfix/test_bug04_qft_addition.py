"""BUG-04: QFT addition with nonzero operands fix verification tests.

Tests QFT-based addition to ensure it works correctly with both nonzero operands.
Previous bug: addition worked for 0+N and N+0 but failed for M+N where both M,N != 0.

These tests verify the fix for BUG-04 where QFT addition failed with two nonzero
operands (e.g., 3+5 returned incorrect result instead of 8).
"""

from verify_helpers import format_failure_message

import quantum_language as ql


def test_add_0_plus_0(verify_circuit):
    """Test BUG-04: 0+0=0 (baseline, both zero)."""

    def circuit_builder():
        a = ql.qint(0, width=4)
        a += 0
        return 0

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [0, 0], 4, expected, actual)


def test_add_0_plus_1(verify_circuit):
    """Test BUG-04: 0+1=1 (one zero operand)."""

    def circuit_builder():
        a = ql.qint(0, width=4)
        a += 1
        return 1

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [0, 1], 4, expected, actual)


def test_add_1_plus_0(verify_circuit):
    """Test BUG-04: 1+0=1 (other zero operand)."""

    def circuit_builder():
        a = ql.qint(1, width=4)
        a += 0
        return 1

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [1, 0], 4, expected, actual)


def test_add_1_plus_1(verify_circuit):
    """Test BUG-04: 1+1=2 (simplest nonzero+nonzero case)."""

    def circuit_builder():
        a = ql.qint(1, width=4)
        a += 1
        return 2

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [1, 1], 4, expected, actual)


def test_add_3_plus_5(verify_circuit):
    """Test BUG-04: 3+5=8 (reported bug case, both nonzero)."""

    def circuit_builder():
        a = ql.qint(3, width=4)
        a += 5
        return 8

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [3, 5], 4, expected, actual)


def test_add_7_plus_8(verify_circuit):
    """Test BUG-04: 7+8=15 (large values, 4-bit max)."""

    def circuit_builder():
        a = ql.qint(7, width=4)
        a += 8
        return 15

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [7, 8], 4, expected, actual)


def test_add_8_plus_8_overflow(verify_circuit):
    """Test BUG-04: 8+8=0 (overflow wrapping, 8+8=16 mod 16=0)."""

    def circuit_builder():
        a = ql.qint(8, width=4)
        a += 8
        return 0  # 16 mod 16 = 0

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [8, 8], 4, expected, actual)
