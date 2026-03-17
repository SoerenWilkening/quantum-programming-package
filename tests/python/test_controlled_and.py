"""Tests for controlled AND (& operator inside with-blocks).

Verifies that the & operator on qbools/qints works correctly inside
quantum conditional contexts (with-blocks), including:
- No regression for uncontrolled AND
- Single-level controlled AND (with ctrl: c = a & b)
- Double-controlled AND (nested with-blocks)
- Chained AND inside with-blocks
- Statevector verification of correct amplitudes

Step 3.2: Controlled-AND support [Quantum_Assembly-8ct]

Uses direct simulation via Qiskit AerSimulator to verify results.
All tests stay under 17-qubit limit.
"""

import gc
import re
import warnings

import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _fresh_circuit():
    """Create a fresh circuit with simulation enabled."""
    ql.circuit()
    ql.option("simulate", True)


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


def _get_statevector(qasm_str):
    """Get statevector from QASM circuit."""
    from qiskit.quantum_info import Statevector

    circuit = qiskit.qasm3.loads(qasm_str)
    sv = Statevector.from_instruction(circuit)
    return sv


def _get_num_qubits(qasm_str):
    """Extract number of qubits from OpenQASM string."""
    matches = re.findall(r"qubit\[(\d+)\]", qasm_str)
    if matches:
        return max(int(m) for m in matches)
    return 0


class TestAndOutsideWith:
    """Regression: & operator works as before outside with-blocks."""

    def test_qbool_and_qbool_basic(self):
        """qbool & qbool outside with-block produces correct result."""
        gc.collect()
        _fresh_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = a & b
        assert isinstance(c, ql.qint)
        assert c.width == 1

    def test_qbool_and_false(self):
        """qbool(True) & qbool(False) = False outside with-block."""
        gc.collect()
        _fresh_circuit()
        a = ql.qbool(True)
        b = ql.qbool(False)
        c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"True & False should be 0, got {actual}"

    def test_qbool_and_true(self):
        """qbool(True) & qbool(True) = True outside with-block."""
        gc.collect()
        _fresh_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"True & True should be 1, got {actual}"

    def test_qint_and_qint_outside(self):
        """Multi-bit AND outside with-block still works."""
        gc.collect()
        _fresh_circuit()
        a = ql.qint(0b11, width=2)
        b = ql.qint(0b10, width=2)
        c = a & b
        assert c.width == 2

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0b10, f"0b11 & 0b10 should be 0b10, got {bin(actual)}"


class TestAndInsideWith:
    """& operator works inside a single with-block (controlled AND)."""

    def test_and_inside_with_true(self):
        """with ctrl(True): c = a & b should execute AND normally.

        ctrl=True, a=True, b=True -> c should be True (1).
        Qubits: 3 inputs + 1 result + 1 ancilla = 5
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (ctrl=T, T&T=T), got {actual}"

    def test_and_inside_with_false_ctrl(self):
        """with ctrl(False): c = a & b should NOT execute AND.

        ctrl=False, a=True, b=True -> c should be 0 (AND not executed).
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(False)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (ctrl=F, AND not executed), got {actual}"

    def test_and_inside_with_false_operand(self):
        """with ctrl(True): c = a & b where b=False -> c=0.

        ctrl=True, a=True, b=False -> c should be 0 (T&F=F).
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(False)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (ctrl=T, T&F=F), got {actual}"

    def test_and_2bit_inside_with(self):
        """with ctrl(True): c = a & b on 2-bit values.

        ctrl=True, a=0b11, b=0b10 -> c should be 0b10.
        Qubits: 1 ctrl + 2+2 inputs + 2 result + 1 ancilla = 8
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qint(0b11, width=2)
        b = ql.qint(0b10, width=2)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        result_width = c.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0b10, f"Expected 0b10, got {bin(actual)}"


class TestAndNestedWith:
    """& operator inside double-nested with-blocks (double-controlled AND)."""

    def test_and_nested_both_true(self):
        """with c1: with c2: d = a & b, both controls True.

        c1=True, c2=True, a=True, b=True -> d=1.
        Qubits: 2 ctrls + 2 inputs + 1 result + 1 AND-compose-ancilla + 1 CCX-ancilla = 7
        """
        gc.collect()
        _fresh_circuit()
        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with c1:
            with c2:
                d = a & b

        result_start = d.allocated_start
        result_width = d.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, a, b, d]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (both ctrls True, T&T), got {actual}"

    def test_and_nested_outer_false(self):
        """with c1(False): with c2(True): d = a & b -> d=0.

        Outer control blocks everything.
        """
        gc.collect()
        _fresh_circuit()
        c1 = ql.qbool(False)
        c2 = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with c1:
            with c2:
                d = a & b

        result_start = d.allocated_start
        result_width = d.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, a, b, d]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (outer False), got {actual}"

    def test_and_nested_inner_false(self):
        """with c1(True): with c2(False): d = a & b -> d=0.

        Inner control blocks AND.
        """
        gc.collect()
        _fresh_circuit()
        c1 = ql.qbool(True)
        c2 = ql.qbool(False)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with c1:
            with c2:
                d = a & b

        result_start = d.allocated_start
        result_width = d.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, a, b, d]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (inner False), got {actual}"


class TestAndChainInsideWith:
    """Chained AND (a & b & c) inside a with-block."""

    def test_chain_inside_with_all_true(self):
        """with ctrl: combined = a & b & c, all True.

        ctrl=True, a=True, b=True, c=True -> combined=True.
        a & b produces intermediate, intermediate & c produces combined.
        Qubits: 1 ctrl + 3 inputs + 1 intermediate + 1 result + 2 ancillas ~ 8
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = ql.qbool(True)
        with ctrl:
            combined = a & b & c

        result_start = combined.allocated_start
        result_width = combined.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c, combined]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (all True), got {actual}"

    def test_chain_inside_with_one_false(self):
        """with ctrl: combined = a & b & c, b=False.

        ctrl=True, a=True, b=False, c=True -> combined=False (0).
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(False)
        c = ql.qbool(True)
        with ctrl:
            combined = a & b & c

        result_start = combined.allocated_start
        result_width = combined.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c, combined]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (b=False breaks chain), got {actual}"

    def test_chain_inside_with_ctrl_false(self):
        """with ctrl(False): combined = a & b & c -> all 0.

        ctrl=False blocks all AND operations.
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(False)
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = ql.qbool(True)
        with ctrl:
            combined = a & b & c

        result_start = combined.allocated_start
        result_width = combined.width
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c, combined]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (ctrl=False), got {actual}"


class TestControlledAndStatevector:
    """Verify correct amplitudes via statevector simulation."""

    def test_statevector_ctrl_true_and_true_true(self):
        """Statevector: ctrl=True, a & b where a=True, b=True.

        The result qubit should be |1> with probability 1.0.
        All qubits are in computational basis (no superposition).
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        # The statevector should have exactly one non-zero amplitude
        probs = sv.probabilities()
        nonzero = [(i, p) for i, p in enumerate(probs) if p > 1e-10]
        assert len(nonzero) == 1, f"Expected 1 basis state, got {len(nonzero)}"

        # Extract the result bit from the basis state index
        basis_idx = nonzero[0][0]
        bitstring = format(basis_idx, f"0{num_qubits}b")
        result_bit = int(bitstring[num_qubits - 1 - result_start])
        assert result_bit == 1, f"Result qubit should be 1, got {result_bit}"

    def test_statevector_ctrl_false_and_true_true(self):
        """Statevector: ctrl=False, a & b where a=True, b=True.

        The result qubit should be |0> (AND not executed).
        """
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(False)
        a = ql.qbool(True)
        b = ql.qbool(True)
        with ctrl:
            c = a & b

        result_start = c.allocated_start
        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        num_qubits = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        probs = sv.probabilities()
        nonzero = [(i, p) for i, p in enumerate(probs) if p > 1e-10]
        assert len(nonzero) == 1, f"Expected 1 basis state, got {len(nonzero)}"

        basis_idx = nonzero[0][0]
        bitstring = format(basis_idx, f"0{num_qubits}b")
        result_bit = int(bitstring[num_qubits - 1 - result_start])
        assert result_bit == 0, f"Result qubit should be 0, got {result_bit}"

    def test_statevector_deterministic_no_spurious_amplitudes(self):
        """All inputs are computational basis: statevector has exactly 1 nonzero amplitude."""
        gc.collect()
        _fresh_circuit()
        ctrl = ql.qbool(True)
        a = ql.qbool(True)
        b = ql.qbool(False)
        with ctrl:
            c = a & b

        qasm = ql.to_openqasm()
        _keepalive = [ctrl, a, b, c]

        sv = _get_statevector(qasm)
        probs = sv.probabilities()
        nonzero_count = sum(1 for p in probs if p > 1e-10)
        assert nonzero_count == 1, (
            f"Expected exactly 1 nonzero amplitude for deterministic inputs, got {nonzero_count}"
        )
