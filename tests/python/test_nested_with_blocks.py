"""Tests for nested quantum conditionals (multi-level with-blocks).

Verifies behavior of nested `with qbool:` blocks:
- Inner block should execute only when BOTH outer and inner conditions are True
- Outer-only operations should execute when outer is True regardless of inner
- When outer is False, nothing should execute (including inner block)
- ~qbool inside with-blocks produces controlled NOT operations
- Multi-bit qint as with-block condition raises TypeError

Phase 118 implements AND-composition in __enter__/__exit__ so that nested
with-blocks produce doubly-controlled (and higher) operations. The inner
control qubit is AND-composed with the outer control via Toffoli gate,
producing an AND-ancilla that becomes the active control for inner operations.

Single-level conditional tests are included as regression baselines to ensure
the non-nested path remains functional (CTRL-05).

Uses direct simulation via Qiskit AerSimulator to verify results.
All tests use qbool(True/False) conditions to stay under 17-qubit limit.

Requirements: CTRL-01, CTRL-04, CTRL-05
"""

import gc
import re
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
    matches = re.findall(r"qubit\[(\d+)\]", qasm_str)
    if matches:
        return max(int(m) for m in matches)
    return 0


class TestSingleLevelConditional:
    """Baseline: single-level with-blocks work correctly (CTRL-05).

    These tests verify the non-nested path remains functional
    as a regression baseline for the nested tests.
    """

    def test_single_cond_true_add(self):
        """Single with-block, condition True: result += 1 executes.

        a=3 > 1 is True, result starts at 0, expected: 1.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        result = ql.qint(0, width=3)
        with cond:
            result += 1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1, got {actual}"

    def test_single_cond_false_add(self):
        """Single with-block, condition False: result += 1 is skipped.

        a=0 > 1 is False, result starts at 0, expected: 0.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        cond = a > 1
        result = ql.qint(0, width=3)
        with cond:
            result += 1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0, got {actual}"

    def test_single_cond_true_sub(self):
        """Single with-block, condition True: result -= 1 executes.

        a=3 > 1 is True, result starts at 3, expected: 2.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        cond = a > 1
        result = ql.qint(3, width=3)
        with cond:
            result -= 1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 2, f"Expected 2, got {actual}"


class TestNestedWithBlocks:
    """Tests for 2-level nested quantum conditionals (CTRL-01).

    Phase 118 implements AND-composition: at nesting depth >= 1, __enter__
    calls _toffoli_and() to compose the outer and inner control qubits,
    producing an AND-ancilla that becomes the active control. This ensures
    inner operations are controlled on (outer AND inner).

    All tests use direct qbool(True/False) values to stay under 17-qubit
    simulation limit (~5-6 qubits per test).
    """

    def test_nested_both_true(self):
        """Both outer and inner conditions True.

        outer: qbool(True), inner: qbool(True)
        In outer: result += 1; In inner: result += 2
        Expected: 3 (1 + 2)
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(True)
        inner_cond = ql.qbool(True)
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 3, f"Expected 3 (1+2), got {actual}"

    def test_nested_outer_true_inner_false(self):
        """Outer True, inner False: only outer-gated ops execute.

        outer: qbool(True), inner: qbool(False)
        In outer: result += 1; In inner: result += 2
        Expected: 1 (only outer op)
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(True)
        inner_cond = ql.qbool(False)
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (outer only), got {actual}"

    def test_nested_outer_false_inner_true(self):
        """Outer False blocks everything including inner block.

        outer: qbool(False), inner: qbool(True)
        In outer: result += 1; In inner: result += 2
        Expected: 0 (outer blocks all)
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(False)
        inner_cond = ql.qbool(True)
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (outer blocks all), got {actual}"

    def test_nested_both_false(self):
        """Both conditions False: no operations execute.

        outer: qbool(False), inner: qbool(False)
        In outer: result += 1; In inner: result += 2
        Expected: 0
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(False)
        inner_cond = ql.qbool(False)
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (both false), got {actual}"

    def test_nested_subtraction(self):
        """Nested conditional subtraction: both True.

        outer: qbool(True), inner: qbool(True)
        result starts at 3; In outer: result -= 1; In inner: result -= 1
        Expected: 1 (3 - 1 - 1)
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(True)
        inner_cond = ql.qbool(True)
        result = ql.qint(3, width=3)
        with outer_cond:
            result -= 1
            with inner_cond:
                result -= 1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (3-1-1), got {actual}"

    def test_nested_assignment_in_inner_only(self):
        """Arithmetic only in inner block: both True.

        outer: qbool(True), inner: qbool(True)
        Only inside inner: result += 3
        Expected: 3
        """
        gc.collect()
        ql.circuit()
        outer_cond = ql.qbool(True)
        inner_cond = ql.qbool(True)
        result = ql.qint(0, width=3)
        with outer_cond:
            with inner_cond:
                result += 3

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [outer_cond, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 3, f"Expected 3 (inner only), got {actual}"

    def test_invert_inside_with(self):
        """~qbool inside with-block produces controlled NOT (CTRL-04)."""
        gc.collect()
        ql.circuit()
        cond = ql.qbool(True)
        target = ql.qbool(False)
        with cond:
            _ = ~target  # Should flip target (controlled NOT)
        # target should be True (1)
        result_start = target.allocated_start
        result_width = target.width
        qasm = ql.to_openqasm()
        _keepalive = [cond, target]
        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (~False = True), got {actual}"

    def test_invert_inside_nested_with(self):
        """~qbool inside nested with-block produces doubly-controlled NOT (CTRL-04)."""
        gc.collect()
        ql.circuit()
        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        target = ql.qbool(False)
        with c1:
            with c2:
                _ = ~target
        result_start = target.allocated_start
        result_width = target.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, target]
        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (doubly-controlled ~False), got {actual}"

    def test_width_validation_rejects_multibit(self):
        """Multi-bit qint as with-block condition raises TypeError."""
        gc.collect()
        ql.circuit()
        x = ql.qint(5, width=4)
        with pytest.raises(TypeError, match="qbool.*1-bit"):
            with x:
                pass
