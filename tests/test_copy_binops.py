"""Verification tests for copy-aware binary operations.

Tests that qint __add__, __radd__, and __sub__ use quantum copy (CNOT gates)
rather than classical reinitialization, producing correct results through the
full pipeline: Python API -> C backend circuit -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All value pairs for widths 2-3 for add, sub, radd
- Operand preservation: Original qints unmodified after binary ops
- Width mismatch: Mixed-width addition produces correct result
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_pairs,
    generate_exhaustive_values,
)

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

# ====================================================================
# PARAMETRIZE DATA
# ====================================================================


def _binop_pair_cases():
    """Generate (width, val_a, val_b) for exhaustive binary op testing (widths 2-3)."""
    cases = []
    for width in [2, 3]:
        for val_a, val_b in generate_exhaustive_pairs(width):
            cases.append((width, val_a, val_b))
    return cases


def _radd_cases():
    """Generate (width, classical_val, quantum_val) for radd testing."""
    cases = []
    for width in [2, 3]:
        values = generate_exhaustive_values(width)
        for classical_val in values:
            for quantum_val in values:
                cases.append((width, classical_val, quantum_val))
    return cases


BINOP_PAIR_CASES = _binop_pair_cases()
RADD_CASES = _radd_cases()


# ====================================================================
# ADDITION TESTS
# ====================================================================


@pytest.mark.parametrize("width,val_a,val_b", BINOP_PAIR_CASES)
def test_add_qint_qint_exhaustive(verify_circuit, width, val_a, val_b):
    """Test qint + qint produces correct value for all pairs, widths 2-3.

    Verifies through Qiskit simulation that addition with quantum copy
    yields (val_a + val_b) % (2**width).
    """
    expected_val = (val_a + val_b) % (2**width)

    def circuit_builder(a_val=val_a, b_val=val_b, w=width):
        a = ql.qint(a_val, width=w)
        b = ql.qint(b_val, width=w)
        c = a + b
        return (expected_val, [a, b, c])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message(
        "add_qq", [val_a, val_b], width, expected, actual
    )


@pytest.mark.parametrize("width,val_a,val_b", BINOP_PAIR_CASES)
def test_add_qint_int_exhaustive(verify_circuit, width, val_a, val_b):
    """Test qint + int produces correct value for all pairs, widths 2-3."""
    expected_val = (val_a + val_b) % (2**width)

    def circuit_builder(a_val=val_a, b_val=val_b, w=width):
        a = ql.qint(a_val, width=w)
        c = a + b_val
        return (expected_val, [a, c])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message(
        "add_qi", [val_a, val_b], width, expected, actual
    )


# ====================================================================
# SUBTRACTION TESTS
# ====================================================================


@pytest.mark.parametrize("width,val_a,val_b", BINOP_PAIR_CASES)
def test_sub_qint_qint_exhaustive(verify_circuit, width, val_a, val_b):
    """Test qint - qint produces correct value for all pairs, widths 2-3.

    Verifies through Qiskit simulation that subtraction with quantum copy
    yields (val_a - val_b) % (2**width).
    """
    expected_val = (val_a - val_b) % (2**width)

    def circuit_builder(a_val=val_a, b_val=val_b, w=width):
        a = ql.qint(a_val, width=w)
        b = ql.qint(b_val, width=w)
        c = a - b
        return (expected_val, [a, b, c])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message(
        "sub_qq", [val_a, val_b], width, expected, actual
    )


@pytest.mark.parametrize("width,val_a,val_b", BINOP_PAIR_CASES)
def test_sub_qint_int_exhaustive(verify_circuit, width, val_a, val_b):
    """Test qint - int produces correct value for all pairs, widths 2-3."""
    expected_val = (val_a - val_b) % (2**width)

    def circuit_builder(a_val=val_a, b_val=val_b, w=width):
        a = ql.qint(a_val, width=w)
        c = a - b_val
        return (expected_val, [a, c])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message(
        "sub_qi", [val_a, val_b], width, expected, actual
    )


# ====================================================================
# RADD TESTS
# ====================================================================


@pytest.mark.parametrize("width,classical_val,quantum_val", RADD_CASES)
def test_radd_exhaustive(verify_circuit, width, classical_val, quantum_val):
    """Test int + qint (radd) produces correct value for all pairs, widths 2-3.

    Verifies through Qiskit simulation that reverse addition with quantum copy
    yields (classical_val + quantum_val) % (2**width).
    """
    expected_val = (classical_val + quantum_val) % (2**width)

    def circuit_builder(c_val=classical_val, q_val=quantum_val, w=width):
        a = ql.qint(q_val, width=w)
        c = c_val + a
        return (expected_val, [a, c])

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message(
        "radd", [classical_val, quantum_val], width, expected, actual
    )


# ====================================================================
# OPERAND PRESERVATION TESTS
# ====================================================================


@pytest.mark.parametrize("width", [2, 3])
def test_add_preserves_operands(width):
    """Test that a + b leaves both a and b with their original values.

    After c = a + b, measuring a and b should yield their original values.
    This verifies that quantum copy does not corrupt the source operands.
    """
    gc.collect()
    ql.circuit()

    val_a = 1
    val_b = 2
    a = ql.qint(val_a, width=width)
    b = ql.qint(val_b, width=width)
    c = a + b

    qasm_str = ql.to_openqasm()
    del a, b, c

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    # Layout: [c (result)][b][a] -- last allocated is leftmost in bitstring
    # a is rightmost (first allocated), b is next, c is leftmost
    a_bits = bitstring[-width:]
    b_bits = bitstring[-(2 * width) : -width]

    actual_a = int(a_bits, 2)
    actual_b = int(b_bits, 2)

    assert actual_a == val_a, f"Operand a corrupted after add: expected {val_a}, got {actual_a}"
    assert actual_b == val_b, f"Operand b corrupted after add: expected {val_b}, got {actual_b}"


@pytest.mark.parametrize("width", [2, 3])
def test_sub_preserves_operands(width):
    """Test that a - b leaves both a and b with their original values.

    After c = a - b, measuring a and b should yield their original values.
    """
    gc.collect()
    ql.circuit()

    val_a = 3
    val_b = 1
    a = ql.qint(val_a, width=width)
    b = ql.qint(val_b, width=width)
    c = a - b

    qasm_str = ql.to_openqasm()
    del a, b, c

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    a_bits = bitstring[-width:]
    b_bits = bitstring[-(2 * width) : -width]

    actual_a = int(a_bits, 2)
    actual_b = int(b_bits, 2)

    assert actual_a == val_a, f"Operand a corrupted after sub: expected {val_a}, got {actual_a}"
    assert actual_b == val_b, f"Operand b corrupted after sub: expected {val_b}, got {actual_b}"


# ====================================================================
# WIDTH MISMATCH TESTS
# ====================================================================


@pytest.mark.xfail(reason="Pre-existing bug: mixed-width QFT addition off-by-one", strict=True)
def test_add_width_mismatch(verify_circuit):
    """Test that adding qints of different widths produces correct result.

    When a (3-bit) + b (5-bit), result should be 5-bit wide and hold
    the correct sum value.

    NOTE: Currently xfail due to pre-existing QFT addition bug with
    mixed-width operands (off-by-one). Not caused by copy-aware changes.
    """
    val_a = 5  # 3-bit
    val_b = 10  # 5-bit
    result_width = 5
    expected_val = (val_a + val_b) % (2**result_width)

    def circuit_builder():
        a = ql.qint(val_a, width=3)
        b = ql.qint(val_b, width=5)
        c = a + b
        return (expected_val, [a, b, c])

    actual, expected = verify_circuit(circuit_builder, result_width)
    assert actual == expected, format_failure_message(
        "add_mismatch", [val_a, val_b], result_width, expected, actual
    )


@pytest.mark.xfail(reason="Pre-existing bug: mixed-width QFT subtraction off-by-one", strict=True)
def test_sub_width_mismatch(verify_circuit):
    """Test that subtracting qints of different widths produces correct result.

    NOTE: Currently xfail due to pre-existing QFT subtraction bug with
    mixed-width operands (off-by-one). Not caused by copy-aware changes.
    """
    val_a = 5  # 3-bit
    val_b = 10  # 5-bit
    result_width = 5
    expected_val = (val_a - val_b) % (2**result_width)

    def circuit_builder():
        a = ql.qint(val_a, width=3)
        b = ql.qint(val_b, width=5)
        c = a - b
        return (expected_val, [a, b, c])

    actual, expected = verify_circuit(circuit_builder, result_width)
    assert actual == expected, format_failure_message(
        "sub_mismatch", [val_a, val_b], result_width, expected, actual
    )
