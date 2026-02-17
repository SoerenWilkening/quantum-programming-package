"""Tests for CQ/cCQ classical-bit gate reduction (Phase 73).

Verifies:
1. Exhaustive correctness of CQ/cCQ addition and subtraction at widths 1-4
2. Gate count reduction for values with zero bits
3. T-count reduction for cCQ operations
4. BK CLA CQ/cCQ correctness (widths 2-4)
5. Gate purity: CQ addition uses only X/CX/CCX gates (no QFT gates)

Uses Qiskit AerSimulator for correctness verification (same pattern as
test_toffoli_hardcoded.py).
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ============================================================================
# Helper functions
# ============================================================================


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


def _verify_cq_add(a_val, value, width):
    """Verify CQ addition: a += value (classical), result in a-register.

    Returns (actual, expected) tuple.
    """
    gc.collect()
    ql.circuit()

    a = ql.qint(a_val, width=width)
    a += value

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # CQ +=: result is in a's qubits at [0..width-1]
    result_start = 0
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val + value) % (1 << width)
    return actual, expected


def _verify_ccq_add(a_val, value, width):
    """Verify controlled CQ addition: ctrl=|1>, a += value.

    Returns (actual, expected) tuple.
    """
    gc.collect()
    ql.circuit()

    ctrl = ql.qint(1, width=1)
    a = ql.qint(a_val, width=width)
    with ctrl:
        a += value

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # ctrl at [0], a at [1..width]
    result_start = 1
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val + value) % (1 << width)
    return actual, expected


def _verify_cq_sub(a_val, value, width):
    """Verify CQ subtraction: a -= value (classical), result in a-register.

    Returns (actual, expected) tuple.
    """
    gc.collect()
    ql.circuit()

    a = ql.qint(a_val, width=width)
    a -= value

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    result_start = 0
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val - value) % (1 << width)
    return actual, expected


def _verify_ccq_sub(a_val, value, width):
    """Verify controlled CQ subtraction: ctrl=|1>, a -= value.

    Returns (actual, expected) tuple.
    """
    gc.collect()
    ql.circuit()

    ctrl = ql.qint(1, width=1)
    a = ql.qint(a_val, width=width)
    with ctrl:
        a -= value

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits(qasm_str)

    # ctrl at [0], a at [1..width]
    result_start = 1
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    expected = (a_val - value) % (1 << width)
    return actual, expected


# ============================================================================
# Exhaustive CQ addition correctness tests (widths 1-4)
# ============================================================================


class TestCQAddExhaustive:
    """Exhaustive CQ addition correctness: all (a_val, value) pairs."""

    @pytest.mark.parametrize("width", [1, 2])
    def test_cq_add_exhaustive_small(self, width):
        """CQ addition: all pairs at widths 1-2."""
        max_val = 1 << width
        failures = []
        for a_val in range(max_val):
            for value in range(max_val):
                actual, expected = _verify_cq_add(a_val, value, width)
                if actual != expected:
                    failures.append(f"W{width}: {a_val} + {value} = {actual}, expected {expected}")
        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [3, 4])
    def test_cq_add_representative_medium(self, width):
        """CQ addition: representative values at widths 3-4."""
        max_val = (1 << width) - 1
        test_values = [0, 1, max_val, max_val >> 1, 2, 3, 5]
        test_values = [v for v in test_values if v <= max_val]

        failures = []
        for a_val in range(1 << width):
            for value in test_values:
                actual, expected = _verify_cq_add(a_val, value, width)
                if actual != expected:
                    failures.append(f"W{width}: {a_val} + {value} = {actual}, expected {expected}")
        assert not failures, "\n".join(failures)


# ============================================================================
# Exhaustive cCQ (controlled) addition correctness tests (widths 1-4)
# ============================================================================


class TestCCQAddExhaustive:
    """Exhaustive controlled CQ addition correctness."""

    @pytest.mark.parametrize("width", [1, 2])
    def test_ccq_add_exhaustive_small(self, width):
        """cCQ addition: all pairs at widths 1-2."""
        max_val = 1 << width
        failures = []
        for a_val in range(max_val):
            for value in range(max_val):
                actual, expected = _verify_ccq_add(a_val, value, width)
                if actual != expected:
                    failures.append(
                        f"cCQ W{width}: {a_val} + {value} = {actual}, expected {expected}"
                    )
        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [3, 4])
    def test_ccq_add_representative_medium(self, width):
        """cCQ addition: representative values at widths 3-4."""
        max_val = (1 << width) - 1
        test_values = [0, 1, max_val, max_val >> 1, 2, 3, 5]
        test_values = [v for v in test_values if v <= max_val]

        failures = []
        for a_val in range(1 << width):
            for value in test_values:
                actual, expected = _verify_ccq_add(a_val, value, width)
                if actual != expected:
                    failures.append(
                        f"cCQ W{width}: {a_val} + {value} = {actual}, expected {expected}"
                    )
        assert not failures, "\n".join(failures)


# ============================================================================
# Exhaustive CQ subtraction correctness tests (widths 1-4)
# ============================================================================


class TestCQSubExhaustive:
    """Exhaustive CQ subtraction correctness."""

    @pytest.mark.parametrize("width", [1, 2])
    def test_cq_sub_exhaustive_small(self, width):
        """CQ subtraction: all pairs at widths 1-2."""
        max_val = 1 << width
        failures = []
        for a_val in range(max_val):
            for value in range(max_val):
                actual, expected = _verify_cq_sub(a_val, value, width)
                if actual != expected:
                    failures.append(f"W{width}: {a_val} - {value} = {actual}, expected {expected}")
        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [3, 4])
    def test_cq_sub_representative_medium(self, width):
        """CQ subtraction: representative values at widths 3-4."""
        max_val = (1 << width) - 1
        test_values = [0, 1, max_val, max_val >> 1, 2, 3, 5]
        test_values = [v for v in test_values if v <= max_val]

        failures = []
        for a_val in range(1 << width):
            for value in test_values:
                actual, expected = _verify_cq_sub(a_val, value, width)
                if actual != expected:
                    failures.append(f"W{width}: {a_val} - {value} = {actual}, expected {expected}")
        assert not failures, "\n".join(failures)


# ============================================================================
# Exhaustive cCQ subtraction correctness tests (widths 1-4)
# ============================================================================


class TestCCQSubExhaustive:
    """Exhaustive controlled CQ subtraction correctness."""

    @pytest.mark.parametrize("width", [1, 2])
    def test_ccq_sub_exhaustive_small(self, width):
        """cCQ subtraction: all pairs at widths 1-2."""
        max_val = 1 << width
        failures = []
        for a_val in range(max_val):
            for value in range(max_val):
                actual, expected = _verify_ccq_sub(a_val, value, width)
                if actual != expected:
                    failures.append(
                        f"cCQ W{width}: {a_val} - {value} = {actual}, expected {expected}"
                    )
        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [3, 4])
    def test_ccq_sub_representative_medium(self, width):
        """cCQ subtraction: representative values at widths 3-4."""
        max_val = (1 << width) - 1
        test_values = [0, 1, max_val, max_val >> 1, 2, 3, 5]
        test_values = [v for v in test_values if v <= max_val]

        failures = []
        for a_val in range(1 << width):
            for value in test_values:
                actual, expected = _verify_ccq_sub(a_val, value, width)
                if actual != expected:
                    failures.append(
                        f"cCQ W{width}: {a_val} - {value} = {actual}, expected {expected}"
                    )
        assert not failures, "\n".join(failures)


# ============================================================================
# Gate count comparison tests
# ============================================================================


class TestGateCountReduction:
    """Verify gate count reduction for values with zero bits."""

    def test_cq_gate_count_even_vs_odd(self):
        """CQ add: even value (bit[0]=0) has fewer or equal CCX than odd at width 4."""
        gc.collect()
        # Even value: bit[0]=0 -> first MAJ eliminated
        c1 = ql.circuit()
        a1 = ql.qint(0, width=4)
        a1 += 2  # even
        counts_even = c1.gate_counts

        gc.collect()
        # Odd value: bit[0]=1 -> first MAJ not eliminated
        c2 = ql.circuit()
        a2 = ql.qint(0, width=4)
        a2 += 3  # odd
        counts_odd = c2.gate_counts

        # Even value should have fewer or equal CCX gates
        assert counts_even["CCX"] <= counts_odd["CCX"], (
            f"Even CCX={counts_even['CCX']} should be <= odd CCX={counts_odd['CCX']}"
        )

    def test_ccq_gate_reduction_zero_bits(self):
        """cCQ add: value with many zero bits has fewer CCX/MCX."""
        gc.collect()
        # Value 2 = 0b0010: 3 zero bits, 1 set bit
        c1 = ql.circuit()
        ctrl1 = ql.qint(1, width=1)
        a1 = ql.qint(0, width=4)
        with ctrl1:
            a1 += 2
        counts_sparse = c1.gate_counts

        gc.collect()
        # Value 15 = 0b1111: 0 zero bits, 4 set bits
        c2 = ql.circuit()
        ctrl2 = ql.qint(1, width=1)
        a2 = ql.qint(0, width=4)
        with ctrl2:
            a2 += 15
        counts_dense = c2.gate_counts

        # Sparse value should have fewer CCX gates
        ccx_sparse = counts_sparse.get("CCX", 0)
        ccx_dense = counts_dense.get("CCX", 0)
        assert ccx_sparse < ccx_dense, f"Sparse CCX={ccx_sparse} should be < dense CCX={ccx_dense}"

    def test_ccq_tcount_reduction(self):
        """cCQ: T-count for even value < T-count for odd value of same width."""
        gc.collect()
        # Even value
        c1 = ql.circuit()
        ctrl1 = ql.qint(1, width=1)
        a1 = ql.qint(0, width=4)
        with ctrl1:
            a1 += 2  # even
        t_even = c1.gate_counts["T"]

        gc.collect()
        # Odd value
        c2 = ql.circuit()
        ctrl2 = ql.qint(1, width=1)
        a2 = ql.qint(0, width=4)
        with ctrl2:
            a2 += 3  # odd
        t_odd = c2.gate_counts["T"]

        assert t_even < t_odd, f"Even T-count={t_even} should be < odd T-count={t_odd}"


# ============================================================================
# BK CLA CQ/cCQ tests (widths 2-4)
# ============================================================================


class TestBKCLACQ:
    """BK CLA CQ/cCQ addition correctness (requires qubit_saving=True)."""

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_bk_cq_add_correctness(self, width):
        """CQ BK CLA addition produces correct results."""
        max_val = (1 << width) - 1
        test_cases = [
            (0, 1),
            (1, 1),
            (max_val, 1),
            (0, max_val),
            (max_val, max_val),
            (3 % (1 << width), 2 % (1 << width)),
        ]

        failures = []
        for a_val, value in test_cases:
            gc.collect()
            ql.circuit()
            ql.option("qubit_saving", True)

            a = ql.qint(a_val, width=width)
            a += value

            qasm_str = ql.to_openqasm()
            num_qubits = _get_num_qubits(qasm_str)
            actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
            expected = (a_val + value) % (1 << width)

            if actual != expected:
                failures.append(
                    f"BK CQ W{width}: {a_val} + {value} = {actual}, expected {expected}"
                )

            ql.option("qubit_saving", False)

        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_bk_ccq_add_correctness(self, width):
        """cCQ BK CLA addition produces correct results."""
        max_val = (1 << width) - 1
        test_cases = [
            (0, 1),
            (1, 1),
            (max_val, 1),
            (0, max_val),
            (3 % (1 << width), 2 % (1 << width)),
        ]

        failures = []
        for a_val, value in test_cases:
            gc.collect()
            ql.circuit()
            ql.option("qubit_saving", True)

            ctrl = ql.qint(1, width=1)
            a = ql.qint(a_val, width=width)
            with ctrl:
                a += value

            qasm_str = ql.to_openqasm()
            num_qubits = _get_num_qubits(qasm_str)
            actual = _simulate_and_extract(qasm_str, num_qubits, 1, width)
            expected = (a_val + value) % (1 << width)

            if actual != expected:
                failures.append(
                    f"BK cCQ W{width}: {a_val} + {value} = {actual}, expected {expected}"
                )

            ql.option("qubit_saving", False)

        assert not failures, "\n".join(failures)


# ============================================================================
# Subtraction verification
# ============================================================================


class TestSubtraction:
    """CQ/cCQ subtraction (decrement) at widths 2-4."""

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_cq_sub_value1(self, width):
        """CQ subtraction (decrement) produces correct results."""
        max_val = (1 << width) - 1
        test_cases = [(0, 1), (1, 1), (max_val, 1), (3, 2)]

        failures = []
        for a_val, value in test_cases:
            actual, expected = _verify_cq_sub(a_val, value, width)
            if actual != expected:
                failures.append(
                    f"CQ sub W{width}: {a_val} - {value} = {actual}, expected {expected}"
                )
        assert not failures, "\n".join(failures)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_ccq_sub_value1(self, width):
        """cCQ subtraction (controlled decrement) produces correct results."""
        max_val = (1 << width) - 1
        test_cases = [(0, 1), (1, 1), (max_val, 1), (3, 2)]

        failures = []
        for a_val, value in test_cases:
            actual, expected = _verify_ccq_sub(a_val, value, width)
            if actual != expected:
                failures.append(
                    f"cCQ sub W{width}: {a_val} - {value} = {actual}, expected {expected}"
                )
        assert not failures, "\n".join(failures)


# ============================================================================
# Gate purity test
# ============================================================================


class TestGatePurity:
    """CQ addition emits only X/CX/CCX gates (no QFT gates)."""

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_cq_gate_purity(self, width):
        """CQ addition uses only Toffoli-family gates (X/CX/CCX/MCX)."""
        gc.collect()
        c = ql.circuit()
        a = ql.qint(0, width=width)
        a += 3 % (1 << width)
        counts = c.gate_counts

        assert counts.get("H", 0) == 0, f"Width {width}: H gates found in CQ add"
        assert counts.get("P", 0) == 0, f"Width {width}: P gates found in CQ add"

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_ccq_gate_purity(self, width):
        """cCQ addition uses only Toffoli-family gates."""
        gc.collect()
        c = ql.circuit()
        ctrl = ql.qint(1, width=1)
        a = ql.qint(0, width=width)
        with ctrl:
            a += 3 % (1 << width)
        counts = c.gate_counts

        assert counts.get("H", 0) == 0, f"Width {width}: H gates found in cCQ add"
        assert counts.get("P", 0) == 0, f"Width {width}: P gates found in cCQ add"
