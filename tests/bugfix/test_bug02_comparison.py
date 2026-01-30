"""BUG-02: Less-or-equal comparison verification tests.

Tests the fix for qint(5) <= qint(5) returning 0 (should return 1).

The bug is in __le__ which combines is_negative and is_zero checks.
For equal values, the zero check should return True (1), making <= return True.
"""

from verify_helpers import format_failure_message

import quantum_language as ql


def test_le_5_le_5(verify_circuit):
    """Test BUG-02 case: qint(5) <= qint(5) should return 1 (True)."""

    def circuit_builder(a=5, b=5, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 5 <= 5 is True (1)
        return 1

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [5, 5], 4, expected, actual)


def test_le_3_le_7(verify_circuit):
    """Test less-than case: qint(3) <= qint(7) should return 1 (True)."""

    def circuit_builder(a=3, b=7, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 3 <= 7 is True (1)
        return 1

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [3, 7], 4, expected, actual)


def test_le_7_le_3(verify_circuit):
    """Test greater-than case: qint(7) <= qint(3) should return 0 (False)."""

    def circuit_builder(a=7, b=3, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 7 <= 3 is False (0)
        return 0

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [7, 3], 4, expected, actual)


def test_le_0_le_0(verify_circuit):
    """Test zero equality: qint(0) <= qint(0) should return 1 (True)."""

    def circuit_builder(a=0, b=0, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 0 <= 0 is True (1)
        return 1

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [0, 0], 4, expected, actual)


def test_le_0_le_15(verify_circuit):
    """Test zero vs max: qint(0) <= qint(15) should return 1 (True)."""

    def circuit_builder(a=0, b=15, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 0 <= 15 is True (1)
        return 1

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [0, 15], 4, expected, actual)


def test_le_15_le_0(verify_circuit):
    """Test max vs zero: qint(15) <= qint(0) should return 0 (False)."""

    def circuit_builder(a=15, b=0, w=4):
        x = ql.qint(a, width=w)
        y = ql.qint(b, width=w)
        _result = x <= y  # noqa: F841 - result needed for circuit generation
        # Expected: 15 <= 0 is False (0)
        return 0

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, format_failure_message("le", [15, 0], 4, expected, actual)
