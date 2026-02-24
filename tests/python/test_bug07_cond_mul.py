"""Regression tests for BUG-07: controlled multiplication scope uncomputation corruption.

BUG-COND-MUL-01: When `result *= 2` runs inside a `with cond:` block, __mul__
creates a new qint that gets registered in the scope frame. When __exit__ runs,
it uncomputes ALL scope-registered qints including the multiplication result.

Fixed by temporarily setting current_scope_depth to 0 during result qint
creation in __mul__/__rmul__, preventing scope registration.

Tests verify:
- Controlled in-place multiplication (condition True) produces correct result
- Controlled out-of-place multiplication works inside with block
- Non-controlled multiplication still works (no regression)
- Conditional addition/subtraction still works (no regression)
"""

import gc
import re
import warnings

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
    matches = re.findall(r"qubit\[(\d+)\]", qasm_str)
    if matches:
        return max(int(m) for m in matches)
    return 0


class TestBug07_CondMul:
    """Regression tests for BUG-07/BUG-COND-MUL-01."""

    def test_controlled_imul_true(self):
        """Controlled in-place multiplication (condition True).

        a=3 > 1 is True, result=1, result *= 2 -> result should be 2.
        Uses ~15 qubits (3-bit comparison + 3-bit result + intermediates).
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1  # True
        result = ql.qint(1, width=3)
        with cond:
            result *= 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 2, f"Expected 2, got {actual}"

    def test_controlled_outofplace_mul_true(self):
        """Controlled out-of-place multiplication (condition True).

        a=2, b=3, cond=a>1 (True), c = a * b inside with cond:.
        Expected c = 6.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(2, width=3)
        cond = a > 1  # True
        with cond:
            c = a * ql.qint(3, width=3)

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 6, f"Expected 6, got {actual}"

    def test_noncontrolled_mul_regression(self):
        """Non-controlled multiplication still works after fix.

        a=3 * 2 = 6. Uses 4*3=12 qubits.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=4)
        b = a * 2
        result_start = b.allocated_start
        result_width = b.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 6, f"Expected 6, got {actual}"

    def test_noncontrolled_rmul_regression(self):
        """Non-controlled reverse multiplication still works.

        2 * a (where a=3) = 6.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=4)
        b = 2 * a  # __rmul__
        result_start = b.allocated_start
        result_width = b.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 6, f"Expected 6, got {actual}"

    def test_controlled_add_regression(self):
        """Conditional addition still works (no regression from mul fix).

        a=3 > 1 is True, result=5, result += 2 -> result should be 7.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        result = ql.qint(5, width=4)
        with cond:
            result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 7, f"Expected 7, got {actual}"

    def test_controlled_sub_regression(self):
        """Conditional subtraction still works (no regression from mul fix).

        a=3 > 1 is True, result=5, result -= 2 -> result should be 3.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        result = ql.qint(5, width=4)
        with cond:
            result -= 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 3, f"Expected 3, got {actual}"

    def test_circuit_generation_no_crash(self):
        """Controlled multiplication generates circuit without crash."""
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        r = ql.qint(2, width=3)
        with cond:
            r *= 2
        qasm = ql.to_openqasm()
        assert len(qasm) > 100, "Circuit too small"
