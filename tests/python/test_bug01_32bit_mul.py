"""Regression tests for BUG-01: 32-bit multiplication segfault.

MAXLAYERINSEQUENCE was 10,000 but 32-bit QQ_mul needs 36,494 layers,
causing a buffer overflow segfault. Fixed by increasing to 300,000.

Tests verify:
- 32-bit multiplication generates a valid circuit (no segfault)
- 4-bit multiplication produces correct results via Qiskit simulation
- Small widths (1-16 bit) continue to work correctly
"""

import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM and extract integer from result register."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _get_num_qubits(qasm_str):
    """Extract number of qubits from OpenQASM string."""
    import re

    matches = re.findall(r"qubit\[(\d+)\]", qasm_str)
    if matches:
        return max(int(m) for m in matches)
    return 0


class TestBug01_32BitMulSegfault:
    """Regression tests for BUG-01: MAXLAYERINSEQUENCE overflow."""

    def test_32bit_mul_no_segfault(self):
        """32-bit QQ_mul generates a circuit without segfault.

        This was the original crash: 32-bit multiplication needs 36,494 layers
        but the old MAXLAYERINSEQUENCE=10,000 caused buffer overflow.
        No simulation (32*3=96 qubits, exceeds 17-qubit limit).
        """
        ql.circuit()
        a = ql.qint(3, width=32)
        b = ql.qint(2, width=32)
        _c = a * b  # noqa: F841 - side effect: circuit generation
        qasm = ql.to_openqasm()
        assert len(qasm) > 100, "Circuit should be non-trivial"

    def test_16bit_mul_no_segfault(self):
        """16-bit QQ_mul generates without crash (generation-only).

        16-bit needs ~4,862 layers. Tests headroom at intermediate width.
        """
        ql.circuit()
        a = ql.qint(5, width=16)
        b = ql.qint(3, width=16)
        _c = a * b  # noqa: F841 - side effect: circuit generation
        qasm = ql.to_openqasm()
        assert len(qasm) > 100, "Circuit should be non-trivial"

    def test_8bit_mul_no_segfault(self):
        """8-bit QQ_mul generates without crash (generation-only)."""
        ql.circuit()
        a = ql.qint(7, width=8)
        b = ql.qint(3, width=8)
        _c = a * b  # noqa: F841 - side effect: circuit generation
        qasm = ql.to_openqasm()
        assert len(qasm) > 100, "Circuit should be non-trivial"

    def test_4bit_mul_simulation_correctness(self):
        """4-bit multiplication produces correct result via Qiskit simulation.

        4-bit QQ_mul uses 4*3=12 qubits, within 17-qubit simulation limit.
        Tests that 3 * 2 = 6.
        """
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a * b
        result_start = c.allocated_start
        result_width = c.width

        qasm = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm)
        result = _simulate_and_extract(qasm, num_qubits, result_start, result_width)

        # 3 * 2 = 6
        assert result == 6, f"Expected 6, got {result}"

    def test_4bit_mul_different_values(self):
        """4-bit multiplication with different values.

        Tests 5 * 2 = 10.
        """
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(2, width=4)
        c = a * b
        result_start = c.allocated_start
        result_width = c.width

        qasm = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm)
        result = _simulate_and_extract(qasm, num_qubits, result_start, result_width)

        # 5 * 2 = 10
        assert result == 10, f"Expected 10, got {result}"

    @pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6, 7, 8])
    def test_small_widths_generation(self, width):
        """Small-width multiplications generate without crash (regression).

        Verifies no regression at widths 1-8.
        """
        ql.circuit()
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        _c = a * b  # noqa: F841 - side effect: circuit generation
        qasm = ql.to_openqasm()
        assert len(qasm) > 0, f"Width {width} should produce non-empty circuit"
