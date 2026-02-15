"""Phase 71: CLA Adder - Smoke Tests.

Tests Brent-Kung CLA QQ addition at widths >= CLA_THRESHOLD (4).
Uses Qiskit AerSimulator for exhaustive statevector verification.

Also tests the CLA option override and below-threshold fallback to RCA.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _enable_toffoli_cla():
    """Enable Toffoli mode with CLA enabled (default)."""
    ql.option("fault_tolerant", True)
    ql.option("cla", True)  # Ensure CLA is not overridden


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate a QASM circuit and extract result from specific qubit range."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector")
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _get_num_qubits_from_qasm(qasm_str):
    """Extract qubit count from OpenQASM qubit declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _run_inplace_add(a_val, b_val, width):
    """Run in-place addition and extract result from qa register.

    qa += qb where qa is at physical qubits [0..width-1].
    """
    gc.collect()
    ql.circuit()
    _enable_toffoli_cla()
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa += qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    # qa is first allocated, starts at qubit 0
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb)
    return actual


def _run_inplace_sub(a_val, b_val, width):
    """Run in-place subtraction and extract result from qa register.

    qa -= qb where qa is at physical qubits [0..width-1].
    """
    gc.collect()
    ql.circuit()
    _enable_toffoli_cla()
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa -= qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb)
    return actual


class TestBKQQAddition:
    """Test Brent-Kung QQ addition at CLA-eligible widths."""

    @pytest.mark.parametrize("width", [4, 5, 6])
    def test_bk_qq_add_exhaustive(self, width):
        """Exhaustive test: a + b mod 2^width for all input pairs."""
        modulus = 1 << width
        failures = []

        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val + b_val) % modulus
                actual = _run_inplace_add(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("bk_qq_add", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, (
            f"BK QQ add width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("width", [4, 5])
    def test_bk_qq_sub_exhaustive(self, width):
        """Exhaustive test: a - b mod 2^width for all input pairs."""
        modulus = 1 << width
        failures = []

        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val - b_val) % modulus
                actual = _run_inplace_sub(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("bk_qq_sub", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, (
            f"BK QQ sub width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


class TestCLAOption:
    """Test CLA option override."""

    def test_cla_option_default_true(self):
        """CLA is enabled by default."""
        gc.collect()
        ql.circuit()
        assert ql.option("cla") is True

    def test_cla_option_disable(self):
        """ql.option('cla', False) disables CLA."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        assert ql.option("cla") is False

    def test_cla_option_re_enable(self):
        """CLA can be re-enabled."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        ql.option("cla", True)
        assert ql.option("cla") is True

    def test_cla_option_rejects_non_bool(self):
        """CLA option rejects non-bool values."""
        gc.collect()
        ql.circuit()
        with pytest.raises(ValueError, match="cla option requires bool"):
            ql.option("cla", 1)

    def test_cla_option_reset_on_new_circuit(self):
        """Creating a new circuit resets CLA to default (enabled)."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        assert ql.option("cla") is False
        ql.circuit()
        assert ql.option("cla") is True

    def test_cla_override_forces_rca(self):
        """With CLA disabled, width >= 4 still uses RCA (produces correct results)."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("cla", False)
        qa = ql.qint(5, width=4)
        qb = ql.qint(3, width=4)
        qa += qb
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits_from_qasm(qasm_str)
        actual = _simulate_and_extract(qasm_str, num_qubits, 0, 4)
        assert actual == 8, f"Expected 8, got {actual}"
        _ = (qa, qb)


class TestCLABelowThreshold:
    """Verify widths below threshold still use RCA correctly."""

    @pytest.mark.parametrize("width", [2, 3])
    def test_below_threshold_still_works(self, width):
        """Widths below CLA threshold use RCA (existing behavior preserved)."""
        modulus = 1 << width
        failures = []
        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val + b_val) % modulus
                actual = _run_inplace_add(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "below_threshold", [a_val, b_val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"Below-threshold width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )
