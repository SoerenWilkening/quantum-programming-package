"""BUG-03: Multiplication segfault fix verification tests.

Tests multiplication operations across bit widths 1-4 to ensure:
1. No segfaults occur (memory allocation fixed)
2. Correct results for basic multiplication cases
3. Width-dependent behavior is stable

These tests verify the fix for BUG-03 where multiplication would segfault
at certain bit widths due to insufficient per-layer gate allocation.
"""

from verify_helpers import format_failure_message

import quantum_language as ql


def test_mul_2x3_4bit(verify_circuit):
    """Test BUG-03: 2*3=6 on 4-bit integers (basic multiplication)."""

    def circuit_builder():
        a = ql.qint(2, width=4)
        b = ql.qint(3, width=4)
        a * b  # noqa: B018 - expression result intentionally unused (circuit construction)
        return 6

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("mul", [2, 3], 4, expected, actual)


def test_mul_1x1_2bit(verify_circuit):
    """Test BUG-03: 1*1=1 on 2-bit integers (minimal width)."""

    def circuit_builder():
        a = ql.qint(1, width=2)
        b = ql.qint(1, width=2)
        a * b  # noqa: B018 - expression result intentionally unused (circuit construction)
        return 1

    actual, expected = verify_circuit(circuit_builder, width=2)
    assert actual == expected, format_failure_message("mul", [1, 1], 2, expected, actual)


def test_mul_3x3_4bit(verify_circuit):
    """Test BUG-03: 3*3=9 on 4-bit integers (squared value)."""

    def circuit_builder():
        a = ql.qint(3, width=4)
        b = ql.qint(3, width=4)
        a * b  # noqa: B018 - expression result intentionally unused (circuit construction)
        return 9

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("mul", [3, 3], 4, expected, actual)


def test_mul_0x5_4bit(verify_circuit):
    """Test BUG-03: 0*5=0 on 4-bit integers (zero operand)."""

    def circuit_builder():
        a = ql.qint(0, width=4)
        b = ql.qint(5, width=4)
        a * b  # noqa: B018 - expression result intentionally unused (circuit construction)
        return 0

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("mul", [0, 5], 4, expected, actual)


def test_mul_2x2_3bit(verify_circuit):
    """Test BUG-03: 2*2=4 on 3-bit integers (3-bit width, segfault-prone)."""

    def circuit_builder():
        a = ql.qint(2, width=3)
        b = ql.qint(2, width=3)
        a * b  # noqa: B018 - expression result intentionally unused (circuit construction)
        return 4

    actual, expected = verify_circuit(circuit_builder, width=3)
    assert actual == expected, format_failure_message("mul", [2, 2], 3, expected, actual)
