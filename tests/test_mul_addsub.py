"""Phase 72, Plan 03 (MUL-05): AND-ancilla MCX decomposition for QQ multiplication.

Verifies that the optimized QQ multiplication (AND-ancilla MCX decomposition)
produces identical results to the previous implementation and uses zero MCX
gates with 3+ controls. The optimization replaces each MCX(3-control) gate
in the controlled CDKM adder with 3 CCX gates via AND-ancilla pattern.

Test categories:
  1. Exhaustive correctness at widths 1-3 (all input pairs)
  2. Spot-check correctness at width 4
  3. Gate count validation: zero MCX(3+), reasonable CCX, pure Toffoli gates
  4. Non-regression: controlled multiplication and CQ multiplication unaffected
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql
from quantum_language._core import current_scope_depth

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _enable_toffoli():
    """Helper to enable Toffoli arithmetic mode."""
    ql.option("fault_tolerant", True)


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate a QASM circuit and extract result from specific qubit range."""
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
    """Extract qubit count from OpenQASM string."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise Exception(f"Could not find qubit count in QASM:\n{qasm_str}")


def _verify_qq_mul(a_val, b_val, width):
    """Build and simulate QQ multiplication, return (actual, expected)."""
    gc.collect()
    ql.circuit()
    _enable_toffoli()
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qc = qa * qb
    expected = (a_val * b_val) % (1 << width)

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)
    result_start = 2 * width  # Result register starts after a and b

    # Keep references alive during simulation
    _refs = (qa, qb, qc)
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    return actual, expected


class TestOptimizedMulCorrectness:
    """Verify optimized QQ multiplication produces correct results."""

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_qq_mul_exhaustive(self, width):
        """Exhaustive QQ multiplication at small widths."""
        max_val = 1 << width
        failures = []

        for a_val in range(max_val):
            for b_val in range(max_val):
                actual, expected = _verify_qq_mul(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "optimized_qq_mul", [a_val, b_val], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [4])
    def test_qq_mul_spot_check_width4(self, width):
        """Spot check QQ multiplication at width 4."""
        test_pairs = [
            (0, 0),
            (1, 1),
            (2, 3),
            (3, 5),
            (7, 7),
            (15, 1),
            (1, 15),
            (15, 15),
            (8, 2),
            (6, 9),
        ]
        failures = []

        for a_val, b_val in test_pairs:
            actual, expected = _verify_qq_mul(a_val, b_val, width)
            if actual != expected:
                failures.append(
                    format_failure_message(
                        "optimized_qq_mul_w4", [a_val, b_val], width, expected, actual
                    )
                )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestOptimizedMulGateCounts:
    """Verify gate count improvements from optimization."""

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_no_mcx_3plus_in_qq_mul(self, width):
        """Optimized QQ multiplication should have no MCX gates with 3+ controls.

        MCX gates (3+ controls) are now counted under 'other' in gate_counts.
        After AND-ancilla decomposition, there should be zero of them.
        """
        gc.collect()
        c = ql.circuit()
        _enable_toffoli()
        a = ql.qint(1, width=width)
        b = ql.qint(2 % (1 << width), width=width)
        result = a * b
        counts = c.gate_counts

        # MCX (3+ controls) now counted under 'other'; should be zero
        # after AND-ancilla decomposition
        assert counts["other"] == 0, (
            f"Width {width}: found {counts['other']} other gates "
            f"(expected 0 after AND-ancilla decomposition)"
        )

        _ = (a, b, result)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_ccx_count_reasonable(self, width):
        """CCX count should be reasonable for the optimized version.

        With decomposed MCX: each controlled addition of w bits uses
        10*w CCX (5 per cMAJ, 5 per cUMA). For n iterations with
        decreasing width, total ~ 10 * sum(1..n) = 5*n*(n+1) CCX plus
        width-1 CCX for the 1-bit iterations.
        """
        gc.collect()
        c = ql.circuit()
        _enable_toffoli()
        a = ql.qint(1, width=width)
        b = ql.qint(2 % (1 << width), width=width)
        result = a * b
        counts = c.gate_counts

        # Upper bound: 10 * sum(2..n) + (n-1) for width-1 iterations
        # sum(2..n) = n*(n+1)/2 - 1, so max ~ 5*n*(n+1) + n
        max_ccx = 5 * width * (width + 1) + width
        assert counts["CCX"] <= max_ccx, (
            f"Width {width}: {counts['CCX']} CCX exceeds expected max {max_ccx}"
        )
        assert counts["CCX"] > 0, f"Width {width}: no CCX gates in Toffoli mul?"

        _ = (a, b, result)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_t_count_equals_7_times_ccx(self, width):
        """T-count = 7 * CCX for Toffoli multiplication.

        After AND-ancilla optimization, no MCX gates remain, so T = 7 * CCX.
        """
        gc.collect()
        c = ql.circuit()
        _enable_toffoli()
        a = ql.qint(1, width=width)
        b = ql.qint(2 % (1 << width), width=width)
        result = a * b
        counts = c.gate_counts

        expected_t = 7 * counts["CCX"]
        assert counts["T"] == expected_t, (
            f"Width {width}: T={counts['T']} != 7*CCX={expected_t} (CCX={counts['CCX']})"
        )

        _ = (a, b, result)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_gate_purity_no_qft(self, width):
        """Optimized Toffoli multiplication uses only X/CX/CCX gates (no QFT)."""
        gc.collect()
        c = ql.circuit()
        _enable_toffoli()
        a = ql.qint(1, width=width)
        b = ql.qint(2 % (1 << width), width=width)
        result = a * b
        counts = c.gate_counts

        assert counts["H"] == 0, f"Width {width}: {counts['H']} H gates in Toffoli multiplication"
        assert counts["P"] == 0, f"Width {width}: {counts['P']} P gates in Toffoli multiplication"
        assert counts["other"] == 0, (
            f"Width {width}: {counts['other']} 'other' gates in Toffoli multiplication"
        )

        _ = (a, b, result)


class TestControlledMulStillWorks:
    """Verify controlled multiplication is not broken by optimization."""

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_controlled_qq_mul(self, width):
        """Controlled QQ multiplication still produces correct results."""
        failures = []
        max_val = 1 << width

        # Test a selection of input pairs with control=|1>
        test_pairs = [(a, b) for a in range(max_val) for b in range(max_val)]

        for a_val, b_val in test_pairs:
            gc.collect()
            ql.circuit()
            _enable_toffoli()
            qa = ql.qint(a_val, width=width)
            qb = ql.qint(b_val, width=width)
            ctrl = ql.qint(1, width=1)
            with ctrl:
                saved = current_scope_depth.get()
                current_scope_depth.set(0)
                qc = qa * qb
                current_scope_depth.set(saved)

            expected = (a_val * b_val) % max_val
            qasm_str = ql.to_openqasm()
            num_qubits = _get_num_qubits(qasm_str)

            # Result at qc.allocated_start
            result_start = qc.allocated_start
            _refs = (qa, qb, ctrl, qc)
            actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)

            if actual != expected:
                failures.append(
                    format_failure_message(
                        "controlled_qq_mul", [a_val, b_val], width, expected, actual
                    )
                )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    def test_cq_mul_unaffected(self):
        """CQ multiplication should be unaffected by QQ optimization."""
        failures = []

        for width in [2, 3, 4]:
            max_val = 1 << width
            test_pairs = [
                (1, 1),
                (2, 3),
                (3, 5),
                (max_val - 1, 1),
                (1, max_val - 1),
            ]

            for a_val, b_val in test_pairs:
                gc.collect()
                ql.circuit()
                _enable_toffoli()
                qa = ql.qint(a_val, width=width)
                qa *= b_val

                expected = (a_val * b_val) % max_val
                qasm_str = ql.to_openqasm()
                num_qubits = _get_num_qubits(qasm_str)

                result_start = width  # CQ result at [width..2*width-1]
                actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)

                if actual != expected:
                    failures.append(
                        format_failure_message("cq_mul", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} CQ mul failures:\n" + "\n".join(failures[:10])
