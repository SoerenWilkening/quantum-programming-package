"""Tests for circuit reset behavior via ql.circuit().

Verifies that ql.circuit() properly resets all circuit state:
- No gate leakage from prior operations
- Qubit allocation starts fresh (from index 0)
- Simulation results are independent across resets
- Multiple consecutive resets work correctly
- Reset after conditional operations produces clean state

Important: Always call gc.collect() before ql.circuit() to prevent
GC-induced gate injection from previous test's qint destructors.

Requirement: TEST-04 (circuit state isolation)
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


class TestCircuitReset:
    """Tests for circuit state isolation via ql.circuit()."""

    def test_reset_no_gate_leakage(self):
        """After reset, QASM contains only new circuit operations.

        Build circuit 1 with addition, reset, build circuit 2 with only init.
        Circuit 2 QASM should not contain addition gates from circuit 1.
        """
        # Circuit 1: a + 1
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        b = a + 1
        qasm1 = ql.to_openqasm()
        _keepalive1 = [a, b]

        # Verify circuit 1 has substance
        assert len(qasm1) > 100, "Circuit 1 too small"

        # Release refs and reset
        del _keepalive1, a, b
        gc.collect()
        ql.circuit()

        # Circuit 2: just init a value
        c = ql.qint(5, width=3)
        qasm2 = ql.to_openqasm()
        _keepalive2 = [c]

        # Circuit 2 should be much smaller (no addition gates)
        # Check that circuit 2 doesn't contain as many gates
        gate_count_1 = qasm1.count("cx ") + qasm1.count("ccx ")
        gate_count_2 = qasm2.count("cx ") + qasm2.count("ccx ")
        assert gate_count_2 < gate_count_1, (
            f"Circuit 2 has {gate_count_2} gates, expected fewer than circuit 1's {gate_count_1}"
        )

    def test_reset_qubit_allocation_fresh(self):
        """After reset, qubit allocation starts from index 0.

        Allocate 8-qubit register (uses indices 0-7), reset,
        then allocate 3-qubit register -- should start at index 0.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=8)
        assert a.allocated_start == 0, f"First alloc should start at 0, got {a.allocated_start}"

        # Release and reset
        del a
        gc.collect()
        ql.circuit()

        b = ql.qint(0, width=3)
        assert b.allocated_start == 0, (
            f"After reset, allocation should start at 0, got {b.allocated_start}"
        )

    def test_reset_simulation_independence(self):
        """Simulation results are independent across circuit resets.

        Build complex circuit, reset, build simple one.
        Simple circuit simulation should not be contaminated.
        """
        # Build complex circuit (don't simulate, just create)
        gc.collect()
        ql.circuit()
        x = ql.qint(7, width=4)
        y = x + 1
        _keepalive = [x, y]
        del _keepalive, x, y

        # Reset and build simple circuit
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        b = a + 1

        result_start = b.allocated_start
        result_width = b.width
        qasm = ql.to_openqasm()
        _keepalive = [a, b]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (max 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 4, f"Expected 4 (3+1), got {actual}"

    def test_multiple_resets(self):
        """Multiple consecutive resets each produce clean state.

        Do 3 cycles of: gc.collect(), ql.circuit(), allocate qint.
        After each reset, allocation should start at 0 and QASM should
        contain only the current circuit.
        """
        for cycle in range(3):
            gc.collect()
            ql.circuit()
            a = ql.qint(cycle, width=3)
            assert a.allocated_start == 0, (
                f"Cycle {cycle}: allocation should start at 0, got {a.allocated_start}"
            )

            qasm = ql.to_openqasm()
            _keepalive = [a]

            # QASM should be relatively small (just initialization)
            num_qubits = _get_num_qubits(qasm)
            assert num_qubits <= 4, f"Cycle {cycle}: expected <= 4 qubits, got {num_qubits}"

            del _keepalive, a

    def test_reset_after_conditional(self):
        """Reset after conditional clears all control state.

        Build circuit with conditional, reset, build simple circuit.
        Simple circuit should have no conditional gates.
        """
        # Build conditional circuit
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        result = ql.qint(0, width=3)
        with cond:
            result += 1
        _keepalive = [a, cond, result]
        qasm_cond = ql.to_openqasm()
        del _keepalive, a, cond, result

        # Reset and build simple circuit
        gc.collect()
        ql.circuit()
        b = ql.qint(5, width=3)
        qasm_simple = ql.to_openqasm()
        _keepalive = [b]

        # Simple circuit should not contain comparison/control gates
        # The conditional circuit is much larger
        assert len(qasm_simple) < len(qasm_cond), (
            f"Simple circuit ({len(qasm_simple)} chars) should be smaller than "
            f"conditional circuit ({len(qasm_cond)} chars)"
        )

        # Verify simple circuit has minimal gate count
        gate_count = qasm_simple.count("cx ") + qasm_simple.count("ccx ")
        assert gate_count < 10, f"Simple init should have few gates, got {gate_count}"
