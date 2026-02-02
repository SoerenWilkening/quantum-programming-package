"""Verification tests for quantum copy operations.

Tests that qint.copy(), qint.copy_onto(), and qbool.copy() correctly
copy quantum state through the full pipeline:
Python API -> C backend circuit -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All values for widths 1-4 bits for copy() and copy_onto()
- Type preservation: qbool.copy() returns qbool
- Error handling: width mismatch raises ValueError
- Qubit distinctness: copy produces fresh qubits
"""

import pytest
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_values,
)

import quantum_language as ql

# ====================================================================
# PARAMETRIZE DATA
# ====================================================================


def _copy_cases():
    """Generate (width, value) tuples for exhaustive copy testing (widths 1-4)."""
    cases = []
    for width in [1, 2, 3, 4]:
        for value in generate_exhaustive_values(width):
            cases.append((width, value))
    return cases


COPY_CASES = _copy_cases()


# ====================================================================
# qint.copy() TESTS
# ====================================================================


@pytest.mark.parametrize("width,value", COPY_CASES)
def test_copy_value_exhaustive(verify_circuit, width, value):
    """Test qint.copy() produces correct value for all widths 1-4 exhaustively.

    Verifies that the copy measures to the same value as the source
    through the full Qiskit simulation pipeline.
    """

    def circuit_builder(val=value, w=width):
        a = ql.qint(val, width=w)
        b = a.copy()
        return (val, [a, b])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("copy", [value], width, expected, actual)


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_copy_preserves_width(clean_circuit, width):
    """Test that copy() preserves bit width."""
    a = ql.qint(1, width=width)
    b = a.copy()
    assert b.width == a.width, f"Expected width {a.width}, got {b.width}"


def test_copy_distinct_qubits(clean_circuit):
    """Test that copy() produces distinct qubits from source.

    The copy must use fresh qubit allocations, not share references
    with the source.
    """
    a = ql.qint(5, width=4)
    b = a.copy()
    # Access qubits through the string representation to verify they differ
    assert str(a) != str(b), "Copy must have distinct qubits from source"


# ====================================================================
# qint.copy_onto() TESTS
# ====================================================================


@pytest.mark.parametrize("width,value", COPY_CASES)
def test_copy_onto_value(verify_circuit, width, value):
    """Test qint.copy_onto() produces correct value for all widths 1-4 exhaustively.

    Verifies that copy_onto with a zero target measures to the same value
    as the source through the full Qiskit simulation pipeline.
    """

    def circuit_builder(val=value, w=width):
        a = ql.qint(val, width=w)
        b = ql.qint(width=w)
        a.copy_onto(b)
        return (val, [a, b])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("copy_onto", [value], width, expected, actual)


def test_copy_onto_width_mismatch(clean_circuit):
    """Test that copy_onto raises ValueError on width mismatch."""
    a = ql.qint(5, width=4)
    b = ql.qint(width=3)
    with pytest.raises(ValueError, match="Width mismatch"):
        a.copy_onto(b)


# ====================================================================
# qbool.copy() TESTS
# ====================================================================


def test_qbool_copy_type_preservation(clean_circuit):
    """Test that qbool.copy() returns a qbool, not a qint."""
    b = ql.qbool(True)
    c = b.copy()
    assert type(c).__name__ == "qbool", f"Expected qbool, got {type(c).__name__}"


@pytest.mark.parametrize("value", [True, False])
def test_qbool_copy_value(verify_circuit, value):
    """Test qbool.copy() produces correct value through Qiskit simulation."""

    def circuit_builder(val=value):
        b = ql.qbool(val)
        c = b.copy()
        return (int(val), [b, c])

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, f"qbool.copy({value}): expected {expected}, got {actual}"
