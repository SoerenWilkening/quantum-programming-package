"""Tests for Cython-level Toffoli addition dispatch (toffoli_dispatch.pxi).

Replaces the deleted C-level test_hot_path_add.c tests. Exercises each
major dispatch path:
- Uncontrolled QQ and CQ addition/subtraction (Toffoli RCA)
- Controlled QQ and CQ addition/subtraction (Toffoli RCA)
- 1-bit edge case (special-case gate emission)
- Clifford+T hardcoded path (toffoli_decompose=True), including controlled
- CLA vs RCA dispatch (min_depth vs min_qubits tradeoff)
- QFT mode (fault_tolerant=False) as baseline comparison
- Zero-value and boundary-value edge cases
"""

import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

MAX_SIM_QUBITS = 17


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_num_qubits(qasm_str):
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _simulate(qasm_str, num_qubits, start, width):
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]
    msb = num_qubits - start - width
    lsb = num_qubits - 1 - start
    return int(bitstring[msb : lsb + 1], 2)


def _run_addition(a_val, b_val, width, invert=False, fault_tolerant=True,
                  tradeoff="auto", toffoli_decompose=False, controlled=False,
                  force_qq=False):
    """Build circuit, perform addition/subtraction, simulate, return result.

    When force_qq=True, b_val is used as the initial value for a second qint,
    forcing the QQ dispatch path even when b_val is a Python int.
    """
    ql.circuit()
    ql.option("fault_tolerant", fault_tolerant)
    if fault_tolerant:
        ql.option("tradeoff", tradeoff)
        if toffoli_decompose:
            ql.option("toffoli_decompose", True)

    a = ql.qint(a_val, width=width)

    if force_qq or not isinstance(b_val, int):
        # QQ path: create a second qint from b_val
        b = ql.qint(int(b_val), width=width)
        if controlled:
            ctrl = ql.qbool(True)
            with ctrl:
                if invert:
                    a -= b
                else:
                    a += b
        else:
            if invert:
                a -= b
            else:
                a += b
    else:
        # CQ path: use b_val as a classical integer
        if controlled:
            ctrl = ql.qbool(True)
            with ctrl:
                if invert:
                    a -= b_val
                else:
                    a += b_val
        else:
            if invert:
                a -= b_val
            else:
                a += b_val

    qasm_str = ql.to_openqasm()
    nq = _get_num_qubits(qasm_str)
    if nq > MAX_SIM_QUBITS:
        pytest.skip(f"Circuit needs {nq} qubits (max {MAX_SIM_QUBITS})")
    return _simulate(qasm_str, nq, 0, width)


def _run_gate_check(a_val, b_val, width, invert=False, fault_tolerant=True,
                    tradeoff="auto", toffoli_decompose=False, controlled=False,
                    force_qq=False):
    """Build circuit, return gate count (non-zero means gates were emitted)."""
    ql.circuit()
    ql.option("fault_tolerant", fault_tolerant)
    if fault_tolerant:
        ql.option("tradeoff", tradeoff)
        if toffoli_decompose:
            ql.option("toffoli_decompose", True)

    a = ql.qint(a_val, width=width)

    if force_qq or not isinstance(b_val, int):
        b = ql.qint(int(b_val), width=width)
        if controlled:
            ctrl = ql.qbool(True)
            with ctrl:
                if invert:
                    a -= b
                else:
                    a += b
        else:
            if invert:
                a -= b
            else:
                a += b
    else:
        if controlled:
            ctrl = ql.qbool(True)
            with ctrl:
                if invert:
                    a -= b_val
                else:
                    a += b_val
        else:
            if invert:
                a -= b_val
            else:
                a += b_val

    return ql.get_gate_count()


# ===========================================================================
# Toffoli RCA: Uncontrolled QQ addition/subtraction
# ===========================================================================


class TestToffoliQQUncontrolled:
    """Uncontrolled quantum-quantum addition via Toffoli RCA dispatch."""

    @pytest.mark.parametrize("width", [2, 4])
    def test_qq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 2, width, fault_tolerant=True, force_qq=True)
        assert result == (1 + 2) & mask

    @pytest.mark.parametrize("width", [2, 4])
    def test_qq_sub(self, width):
        mask = (1 << width) - 1
        result = _run_addition(5, 2, width, invert=True, fault_tolerant=True,
                               force_qq=True)
        assert result == (5 - 2) & mask

    def test_qq_add_produces_gates(self):
        gc = _run_gate_check(3, 2, 4, fault_tolerant=True, force_qq=True)
        assert gc > 0, "QQ Toffoli add should produce gates"

    def test_qq_sub_produces_gates(self):
        gc = _run_gate_check(5, 2, 4, invert=True, fault_tolerant=True,
                             force_qq=True)
        assert gc > 0, "QQ Toffoli sub should produce gates"


# ===========================================================================
# Toffoli RCA: Uncontrolled CQ addition/subtraction
# ===========================================================================


class TestToffoliCQUncontrolled:
    """Uncontrolled classical-quantum addition via Toffoli RCA dispatch."""

    @pytest.mark.parametrize("width", [2, 4])
    def test_cq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 3, width, fault_tolerant=True)
        assert result == (1 + 3) & mask

    @pytest.mark.parametrize("width", [2, 4])
    def test_cq_sub(self, width):
        mask = (1 << width) - 1
        result = _run_addition(7, 2, width, invert=True, fault_tolerant=True)
        assert result == (7 - 2) & mask

    def test_cq_add_produces_gates(self):
        gc = _run_gate_check(3, 5, 4, fault_tolerant=True)
        assert gc > 0, "CQ Toffoli add should produce gates"

    def test_cq_add_zero_value(self):
        """CQ add with classical value 0 should still produce a valid result."""
        result = _run_addition(5, 0, 4, fault_tolerant=True)
        assert result == 5


# ===========================================================================
# Toffoli RCA: Controlled QQ and CQ
# ===========================================================================


class TestToffoliControlled:
    """Controlled addition via Toffoli dispatch (cQQ and cCQ paths)."""

    def test_controlled_qq_add(self):
        result = _run_addition(2, 3, 4, controlled=True, fault_tolerant=True,
                               force_qq=True)
        assert result == 5, "Controlled QQ add with ctrl=True should add"

    def test_controlled_qq_sub(self):
        result = _run_addition(5, 2, 4, invert=True, controlled=True,
                               fault_tolerant=True, force_qq=True)
        assert result == 3, "Controlled QQ sub with ctrl=True should subtract"

    def test_controlled_cq_add(self):
        result = _run_addition(4, 7, 4, controlled=True, fault_tolerant=True)
        assert result == 11, "Controlled CQ add with ctrl=True should add"

    def test_controlled_cq_sub(self):
        result = _run_addition(9, 4, 4, invert=True, controlled=True,
                               fault_tolerant=True)
        assert result == 5, "Controlled CQ sub with ctrl=True should subtract"

    def test_controlled_qq_produces_gates(self):
        gc = _run_gate_check(2, 3, 4, controlled=True, fault_tolerant=True,
                             force_qq=True)
        assert gc > 0, "Controlled QQ Toffoli add should produce gates"

    def test_controlled_cq_produces_gates(self):
        gc = _run_gate_check(2, 5, 4, controlled=True, fault_tolerant=True)
        assert gc > 0, "Controlled CQ Toffoli add should produce gates"


# ===========================================================================
# 1-bit edge case
# ===========================================================================


class TestOneBitEdgeCase:
    """1-bit addition uses direct gate emission (special case in dispatch)."""

    def test_1bit_qq_add(self):
        result = _run_addition(1, 1, 1, fault_tolerant=True, force_qq=True)
        assert result == 0, "1 + 1 mod 2 = 0"

    def test_1bit_cq_add(self):
        result = _run_addition(0, 1, 1, fault_tolerant=True)
        assert result == 1, "0 + 1 = 1"

    def test_1bit_qq_sub(self):
        result = _run_addition(1, 1, 1, invert=True, fault_tolerant=True,
                               force_qq=True)
        assert result == 0, "1 - 1 = 0"

    def test_1bit_cq_sub(self):
        result = _run_addition(1, 1, 1, invert=True, fault_tolerant=True)
        assert result == 0, "1 - 1 = 0"

    def test_1bit_qq_produces_gates(self):
        gc = _run_gate_check(1, 1, 1, fault_tolerant=True, force_qq=True)
        assert gc > 0, "1-bit QQ Toffoli add should produce gates"

    def test_1bit_cq_produces_gates(self):
        gc = _run_gate_check(0, 1, 1, fault_tolerant=True)
        assert gc > 0, "1-bit CQ Toffoli add should produce gates"


# ===========================================================================
# Clifford+T path (toffoli_decompose=True)
# ===========================================================================


class TestCliffordTPath:
    """Clifford+T decomposition path (hardcoded sequences for widths 1-8)."""

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_clifft_qq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 2, width, fault_tolerant=True,
                               toffoli_decompose=True, force_qq=True)
        assert result == (1 + 2) & mask

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_clifft_cq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 3, width, fault_tolerant=True,
                               toffoli_decompose=True)
        assert result == (1 + 3) & mask

    def test_clifft_qq_sub(self):
        result = _run_addition(5, 2, 4, invert=True, fault_tolerant=True,
                               toffoli_decompose=True, force_qq=True)
        assert result == 3

    def test_clifft_cq_sub(self):
        result = _run_addition(6, 2, 4, invert=True, fault_tolerant=True,
                               toffoli_decompose=True)
        assert result == 4

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_clifft_controlled_qq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 2, width, fault_tolerant=True,
                               toffoli_decompose=True, controlled=True,
                               force_qq=True)
        assert result == (1 + 2) & mask

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_clifft_controlled_cq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(2, 3, width, fault_tolerant=True,
                               toffoli_decompose=True, controlled=True)
        assert result == (2 + 3) & mask

    def test_clifft_controlled_qq_sub(self):
        result = _run_addition(7, 3, 4, invert=True, fault_tolerant=True,
                               toffoli_decompose=True, controlled=True,
                               force_qq=True)
        assert result == 4

    def test_clifft_controlled_cq_sub(self):
        result = _run_addition(8, 3, 4, invert=True, fault_tolerant=True,
                               toffoli_decompose=True, controlled=True)
        assert result == 5

    def test_clifft_produces_gates(self):
        gc = _run_gate_check(1, 2, 4, fault_tolerant=True,
                             toffoli_decompose=True, force_qq=True)
        assert gc > 0, "Clifford+T QQ path should produce gates"


# ===========================================================================
# CLA vs RCA dispatch
# ===========================================================================


class TestCLAvsRCA:
    """CLA (min_depth) vs RCA (min_qubits) dispatch paths."""

    @pytest.mark.parametrize("width", [3, 4])
    def test_min_depth_qq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 2, width, fault_tolerant=True,
                               tradeoff="min_depth", force_qq=True)
        assert result == (1 + 2) & mask

    @pytest.mark.parametrize("width", [3, 4])
    def test_min_qubits_qq_add(self, width):
        mask = (1 << width) - 1
        result = _run_addition(1, 2, width, fault_tolerant=True,
                               tradeoff="min_qubits", force_qq=True)
        assert result == (1 + 2) & mask

    def test_min_depth_cq_add(self):
        result = _run_addition(1, 5, 4, fault_tolerant=True,
                               tradeoff="min_depth")
        assert result == 6

    def test_min_depth_qq_sub(self):
        result = _run_addition(7, 3, 4, invert=True, fault_tolerant=True,
                               tradeoff="min_depth", force_qq=True)
        assert result == 4

    def test_min_depth_cq_sub(self):
        result = _run_addition(9, 4, 4, invert=True, fault_tolerant=True,
                               tradeoff="min_depth")
        assert result == 5

    def test_both_modes_agree(self):
        """min_depth and min_qubits should produce the same arithmetic result."""
        r1 = _run_addition(5, 3, 4, fault_tolerant=True, tradeoff="min_depth",
                           force_qq=True)
        r2 = _run_addition(5, 3, 4, fault_tolerant=True, tradeoff="min_qubits",
                           force_qq=True)
        assert r1 == r2 == 8


# ===========================================================================
# QFT baseline (non-Toffoli)
# ===========================================================================


class TestQFTBaseline:
    """QFT-mode addition (fault_tolerant=False) for comparison."""

    def test_qft_qq_add(self):
        result = _run_addition(3, 2, 4, fault_tolerant=False, force_qq=True)
        assert result == 5

    def test_qft_cq_add(self):
        result = _run_addition(3, 4, 4, fault_tolerant=False)
        assert result == 7

    def test_qft_qq_sub(self):
        result = _run_addition(5, 2, 4, invert=True, fault_tolerant=False,
                               force_qq=True)
        assert result == 3

    def test_qft_cq_sub(self):
        result = _run_addition(7, 3, 4, invert=True, fault_tolerant=False)
        assert result == 4

    def test_qft_matches_toffoli(self):
        """QFT and Toffoli modes should produce identical results for QQ."""
        r_qft = _run_addition(5, 3, 4, fault_tolerant=False, force_qq=True)
        r_tof = _run_addition(5, 3, 4, fault_tolerant=True, force_qq=True)
        assert r_qft == r_tof


# ===========================================================================
# Zero and boundary values
# ===========================================================================


class TestEdgeCases:
    """Zero-value and boundary edge cases."""

    def test_add_zero_qq(self):
        result = _run_addition(5, 0, 4, fault_tolerant=True, force_qq=True)
        assert result == 5

    def test_add_zero_cq(self):
        result = _run_addition(5, 0, 4, fault_tolerant=True)
        assert result == 5

    def test_overflow_wraps(self):
        """Addition that overflows should wrap (modular arithmetic)."""
        result = _run_addition(15, 1, 4, fault_tolerant=True, force_qq=True)
        assert result == 0, "15 + 1 mod 16 = 0"

    def test_subtract_to_zero(self):
        result = _run_addition(5, 5, 4, invert=True, fault_tolerant=True,
                               force_qq=True)
        assert result == 0

    def test_underflow_wraps(self):
        """Subtraction that underflows should wrap (modular arithmetic)."""
        result = _run_addition(0, 1, 4, invert=True, fault_tolerant=True,
                               force_qq=True)
        assert result == 15, "0 - 1 mod 16 = 15"
