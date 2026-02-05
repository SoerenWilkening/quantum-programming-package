"""BUG-01: Subtraction underflow verification tests.

Tests the fix for qint(3) - qint(7) on 4-bit integers returning 12 (not 7).

The bug was in __sub__ which copied self.value (initialization value) instead
of the quantum state when creating the result qint for out-of-place subtraction.
"""

from verify_helpers import format_failure_message

import quantum_language as ql


def test_sub_3_minus_7(verify_circuit):
    """Test BUG-01 case: qint(3) - qint(7) on 4-bit should return 12."""

    def circuit_builder(a=3, b=7, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x - y  # noqa: F841 - result needed for circuit generation
        # Expected: (3 - 7) mod 16 = -4 mod 16 = 12
        return 12

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("sub", [3, 7], 4, expected, actual)


def test_sub_7_minus_3(verify_circuit):
    """Test normal subtraction: qint(7) - qint(3) should return 4."""

    def circuit_builder(a=7, b=3, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x - y  # noqa: F841 - result needed for circuit generation
        # Expected: 7 - 3 = 4
        return 4

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("sub", [7, 3], 4, expected, actual)


def test_sub_0_minus_1(verify_circuit):
    """Test underflow at zero: qint(0) - qint(1) should return 15."""

    def circuit_builder(a=0, b=1, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x - y  # noqa: F841 - result needed for circuit generation
        # Expected: (0 - 1) mod 16 = -1 mod 16 = 15
        return 15

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("sub", [0, 1], 4, expected, actual)


def test_sub_5_minus_5(verify_circuit):
    """Test equal values: qint(5) - qint(5) should return 0."""

    def circuit_builder(a=5, b=5, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x - y  # noqa: F841 - result needed for circuit generation
        # Expected: 5 - 5 = 0
        return 0

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("sub", [5, 5], 4, expected, actual)


def test_sub_15_minus_0(verify_circuit):
    """Test subtracting zero: qint(15) - qint(0) should return 15."""

    def circuit_builder(a=15, b=0, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x - y  # noqa: F841 - result needed for circuit generation
        # Expected: 15 - 0 = 15
        return 15

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("sub", [15, 0], 4, expected, actual)
