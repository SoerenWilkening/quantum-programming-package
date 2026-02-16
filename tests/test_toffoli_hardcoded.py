"""Tests for hardcoded Toffoli sequences and T-count reporting (Phase 72).

Verifies:
1. T-count appears in gate_counts dict and equals 7 * (CCX + MCX)
2. Hardcoded Toffoli QQ/cQQ sequences produce correct addition results
3. Gate purity: Toffoli arithmetic uses only X/CX/CCX gates (no QFT gates)
4. Subtraction still works after hardcoded integration

Uses Qiskit AerSimulator for correctness verification (same pattern as
test_toffoli_addition.py). Gate-count-only tests do not require simulation.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM circuit and extract result from specific qubit range.

    Args:
        qasm_str: OpenQASM 3.0 string
        num_qubits: Total number of qubits in circuit
        result_start: Starting physical qubit index of result register (LSB)
        result_width: Number of qubits in result register

    Returns:
        Integer value of result register
    """
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector")
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _get_num_qubits(qasm_str):
    """Extract qubit count from QASM string."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _verify_qq_add(a_val, b_val, width):
    """Verify in-place QQ addition: a += b, result in a-register.

    For in-place +=, the result is stored in qa's qubits at positions [0..width-1].
    """
    gc.collect()
    ql.circuit()

    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa += qb

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # In-place +=: result is in qa's qubits at [0..width-1]
    result_start = 0
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val + b_val) % (1 << width)
    return actual, expected


def _verify_cqq_add(a_val, b_val, width):
    """Verify controlled in-place QQ addition: ctrl=|1>, a += b."""
    gc.collect()
    ql.circuit()

    ctrl = ql.qint(1, width=1)
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    with ctrl:
        qa += qb

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # ctrl at [0], qa at [1..width], result in qa
    result_start = 1
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val + b_val) % (1 << width)
    return actual, expected


def _verify_qq_sub(a_val, b_val, width):
    """Verify in-place QQ subtraction: a -= b, result in a-register."""
    gc.collect()
    ql.circuit()

    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa -= qb

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # In-place -=: result is in qa's qubits at [0..width-1]
    result_start = 0
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val - b_val) % (1 << width)
    return actual, expected


# ============================================================================
# T-count reporting tests (INF-04) -- no simulation needed
# ============================================================================


class TestTCount:
    """Verify T-count appears in gate_counts and equals 7 * (CCX + MCX)."""

    def test_t_count_in_gate_counts(self):
        """gate_counts dict has 'T' key."""
        c = ql.circuit()
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        counts = c.gate_counts
        assert "T" in counts, "gate_counts missing 'T' key"

    def test_t_count_equals_7_times_ccx_plus_mcx(self):
        """T = 7 * (CCX + MCX) for Toffoli arithmetic."""
        c = ql.circuit()
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        counts = c.gate_counts
        assert counts["T"] == 7 * (counts["CCX"] + counts["MCX"]), (
            f"T={counts['T']} != 7*(CCX+MCX)={7 * (counts['CCX'] + counts['MCX'])}"
        )

    def test_t_count_zero_for_qft(self):
        """T = 0 for QFT arithmetic (no CCX/MCX gates)."""
        c = ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        counts = c.gate_counts
        assert counts["CCX"] == 0, "QFT should have no CCX gates"
        assert counts["T"] == 0, "QFT should have T=0"
        ql.option("fault_tolerant", True)  # restore default

    def test_t_count_scales_with_width(self):
        """Wider additions have more CCX -> more T gates."""
        t_counts = []
        for width in [2, 4, 8]:
            c = ql.circuit()
            a = ql.qint(0, width=width)
            b = ql.qint(0, width=width)
            a += b
            t_counts.append(c.gate_counts["T"])
        assert t_counts[0] < t_counts[1] < t_counts[2], (
            f"T-count should increase with width: {t_counts}"
        )


# ============================================================================
# Hardcoded Toffoli sequence correctness tests (INF-03)
# ============================================================================


class TestHardcodedToffoliSequences:
    """Verify hardcoded sequences produce correct results via Qiskit simulation."""

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_qq_add_hardcoded_correctness(self, width):
        """QQ addition with hardcoded sequences matches expected results.

        Tests representative input pairs. Widths 1-4 are feasible for
        statevector simulation (max ~9 qubits for width 4).
        """
        max_val = (1 << width) - 1
        test_pairs = [(0, 0), (1, 0), (0, 1), (1, 1)]
        if width >= 2:
            test_pairs.extend([(max_val, 1), (max_val, max_val)])

        failures = []
        for a_val, b_val in test_pairs:
            actual, expected = _verify_qq_add(a_val, b_val, width)
            if actual != expected:
                failures.append(f"Width {width}: {a_val} + {b_val} = {actual}, expected {expected}")

        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_qq_add_gate_purity(self, width):
        """Hardcoded QQ Toffoli addition uses only X/CX/CCX gates."""
        c = ql.circuit()
        a = ql.qint(0, width=width)
        b = ql.qint(1, width=width)
        a += b
        counts = c.gate_counts
        assert counts["H"] == 0, f"Width {width}: H gates found in Toffoli add"
        assert counts["P"] == 0, f"Width {width}: P gates found in Toffoli add"

    @pytest.mark.parametrize("width", [2, 4])
    def test_cqq_add_hardcoded_correctness(self, width):
        """Controlled QQ addition with hardcoded sequences works correctly."""
        actual, expected = _verify_cqq_add(3 % (1 << width), 2, width)
        assert actual == expected, (
            f"Controlled add width {width}: 3 + 2 = {actual}, expected {expected}"
        )

    def test_hardcoded_no_regression_basic(self):
        """Sanity check: basic Toffoli add still works after hardcoded integration."""
        actual, expected = _verify_qq_add(7, 5, 4)
        assert actual == expected, f"4-bit: 7 + 5 = {actual}, expected 12"

    @pytest.mark.parametrize("width", [2, 4])
    def test_subtraction_still_works(self, width):
        """Subtraction (inverted adder) works with hardcoded sequences."""
        a_val = 5 % (1 << width)
        b_val = 3 % (1 << width)
        actual, expected = _verify_qq_sub(a_val, b_val, width)
        assert actual == expected, (
            f"Width {width}: {a_val} - {b_val} = {actual}, expected {expected}"
        )
