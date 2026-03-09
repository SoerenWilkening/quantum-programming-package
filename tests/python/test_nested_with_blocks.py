"""Tests for nested quantum conditionals (2-level with-blocks).

Verifies behavior of nested `with qbool:` blocks:
- Inner block should execute only when BOTH outer and inner conditions are True
- Outer-only operations should execute when outer is True regardless of inner
- When outer is False, nothing should execute (including inner block)

Phase 117 status: Nested with-blocks push stack entries (no longer raise
NotImplementedError), but lack AND composition -- only the inner control
qubit gates inner operations. Phase 118 will add AND-ancilla composition.
All nested tests are marked xfail (strict=False) to document this.

Single-level conditional tests (which DO work) are included as regression
baselines to ensure the non-nested path remains functional.

Uses direct simulation via Qiskit AerSimulator to verify results.
All tests use small QInts to stay under 17-qubit limit.

Requirement: TEST-03 (nested with-block coverage)
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
    """Baseline: single-level with-blocks work correctly.

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
    """Tests for 2-level nested quantum conditionals.

    Phase 117 status: Nested with-blocks now push two stack entries
    (no longer raise NotImplementedError), but only the inner control
    qubit is used for gating (no AND composition yet). This means inner
    operations are controlled on the inner condition only, not both.

    Phase 118 will add AND-ancilla composition so inner operations are
    controlled on (outer AND inner). Until then, tests may produce wrong
    results and are marked xfail with strict=False.
    """

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_both_true(self):
        """Both outer and inner conditions True.

        outer: a=3 > 1 (True), inner: b=3 > 1 (True)
        In outer: result += 1; In inner: result += 2
        Expected: 3 (1 + 2)
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        outer_cond = a > 1
        b = ql.qint(3, width=3)
        inner_cond = b > 1
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 3, f"Expected 3 (1+2), got {actual}"

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_outer_true_inner_false(self):
        """Outer True, inner False: only outer-gated ops execute.

        outer: a=3 > 1 (True), inner: b=0 > 1 (False)
        In outer: result += 1; In inner: result += 2
        Expected: 1 (only outer op)
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        outer_cond = a > 1
        b = ql.qint(0, width=3)
        inner_cond = b > 1
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (outer only), got {actual}"

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_outer_false_inner_true(self):
        """Outer False blocks everything including inner block.

        outer: a=0 > 1 (False), inner: b=3 > 1 (True)
        In outer: result += 1; In inner: result += 2
        Expected: 0 (outer blocks all)
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        outer_cond = a > 1
        b = ql.qint(3, width=3)
        inner_cond = b > 1
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (outer blocks all), got {actual}"

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_both_false(self):
        """Both conditions False: no operations execute.

        outer: a=0 > 1 (False), inner: b=0 > 1 (False)
        In outer: result += 1; In inner: result += 2
        Expected: 0
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        outer_cond = a > 1
        b = ql.qint(0, width=3)
        inner_cond = b > 1
        result = ql.qint(0, width=3)
        with outer_cond:
            result += 1
            with inner_cond:
                result += 2

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (both false), got {actual}"

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_subtraction(self):
        """Nested conditional subtraction: both True.

        outer: a=3 > 1 (True), inner: b=3 > 1 (True)
        result starts at 3; In outer: result -= 1; In inner: result -= 1
        Expected: 1 (3 - 1 - 1)
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        outer_cond = a > 1
        b = ql.qint(3, width=3)
        inner_cond = b > 1
        result = ql.qint(3, width=3)
        with outer_cond:
            result -= 1
            with inner_cond:
                result -= 1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (3-1-1), got {actual}"

    @pytest.mark.xfail(
        reason="Phase 117: nested with-blocks push stack entries but lack AND composition (Phase 118)",
        strict=False,
    )
    def test_nested_assignment_in_inner_only(self):
        """Arithmetic only in inner block: both True.

        outer: a=3 > 1 (True), inner: b=3 > 1 (True)
        Only inside inner: result += 3
        Expected: 3
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(3, width=3)
        outer_cond = a > 1
        b = ql.qint(3, width=3)
        inner_cond = b > 1
        result = ql.qint(0, width=3)
        with outer_cond:
            with inner_cond:
                result += 3

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [a, outer_cond, b, inner_cond, result]

        num_qubits = _get_num_qubits(qasm)
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 3, f"Expected 3 (inner only), got {actual}"
