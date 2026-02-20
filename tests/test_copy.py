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

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_values,
)

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

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


# ====================================================================
# UNCOMPUTATION TESTS
# ====================================================================


def test_copy_uncomputation():
    """Test that copy() participates in scope-based automatic uncomputation.

    Creates a copy inside a with-block with EAGER mode enabled.
    After scope exit, the copy's ancilla qubits should be uncomputed (|0>).
    """
    gc.collect()
    ql.circuit()
    ql.option("qubit_saving", True)

    width = 3
    value = 5

    a = ql.qint(value, width=width)
    with ql.qbool(True):
        b = a.copy()

    # After with-block, b should be uncomputed
    qasm_str = ql.to_openqasm()
    ql.option("qubit_saving", False)

    # Keep references alive until after QASM export
    del a, b

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    n = len(bitstring)

    # Layout: [copy_bits (uncomputed)][condition_bit][input_a_bits]
    # input_a is rightmost (first allocated), width=3
    # condition bit is next (1 bit for qbool)
    # copy bits should be uncomputed (all 0)
    input_a_bits = bitstring[n - width :]
    actual_a = int(input_a_bits, 2)
    assert actual_a == value, f"Input a corrupted: expected {value}, got {actual_a}"

    # Everything left of input_a and condition should be 0 (uncomputed)
    # The copy qubits and any intermediates should be cleaned up
    ancilla_region = bitstring[: n - width - 1]  # exclude input_a and condition bit
    assert all(bit == "0" for bit in ancilla_region), (
        f"Ancilla not clean after uncomputation: {ancilla_region} (full: {bitstring})"
    )
