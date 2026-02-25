"""Phase 69/91: Toffoli Division/Modulo Verification Tests.

Tests division and modulo operations via C-level restoring division (Phase 91).
The C-level implementation in ToffoliDivision.c uses CDKM adders directly,
replacing the old Python-level division that leaked ancillae.

Tests cover:
1. Classical divisor floor division (widths 2-4) -- all pass after Phase 91
2. Classical divisor modulo (widths 2-3) -- all pass after Phase 91
3. Quantum divisor floor division (width 2) -- partial failures (ancilla leak in QQ path)
4. Quantum divisor modulo (width 2) -- partial failures (ancilla leak in QQ path)
5. Controlled division (xfail -- _divmod_c does not check controlled context)
6. Gate purity (no QFT gates)

Simulator: Toffoli circuits contain MCX (multi-controlled X) gates that are not
supported by the MPS simulator directly. We transpile circuits to decompose MCX
into basis gates {cx, ccx, u1, u2, u3, x, h} before simulation.

Result extraction: Uses allocated_start from the Python qint object to determine
physical qubit positions.
"""

import gc
import random
import re
import warnings

import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# Phase 91: CQ division and modulo are now fully fixed (BUG-DIV-02, BUG-MOD-REDUCE resolved).
# No KNOWN_TOFFOLI_DIV_FAILURES or KNOWN_TOFFOLI_MOD_FAILURES sets needed.
#
# QQ (quantum divisor) division still has failures due to comparison ancilla
# leak in the repeated-subtraction path. The C-level toffoli_divmod_qq cannot
# uncompute comparison ancillae within the iteration loop, causing entangled
# garbage qubits to corrupt conditional operations. All cases where a >= b
# (quotient >= 1) fail because the quotient register stays |0>.
# ---------------------------------------------------------------------------
KNOWN_TOFFOLI_QDIV_FAILURES = {
    (2, 1, 1),
    (2, 2, 1),
    (2, 2, 2),
    (2, 3, 1),
    (2, 3, 2),
    (2, 3, 3),
}

KNOWN_TOFFOLI_QMOD_FAILURES = {
    (2, 1, 1),
    (2, 2, 1),
    (2, 2, 2),
    (2, 3, 1),
    (2, 3, 2),
    (2, 3, 3),
}


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------
def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM string."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise Exception(f"Could not find qubit count in QASM:\n{qasm_str[:200]}")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate a QASM circuit with MPS (after transpiling MCX) and extract result.

    Toffoli circuits contain MCX gates that MPS doesn't support directly.
    We transpile to decompose them into basis gates first.

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

    # Transpile to decompose MCX gates for MPS compatibility
    basis_gates = ["cx", "u1", "u2", "u3", "x", "h", "ccx", "id"]
    transpiled = transpile(circuit, basis_gates=basis_gates, optimization_level=0)

    simulator = AerSimulator(method="matrix_product_state", max_parallel_threads=4)
    job = simulator.run(transpiled, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _enable_toffoli():
    """Helper to enable Toffoli arithmetic mode."""
    ql.option("fault_tolerant", True)


# ---------------------------------------------------------------------------
# xfail marking helpers (QQ only -- CQ is fully fixed)
# ---------------------------------------------------------------------------
def _mark_qdiv_failures(cases):
    """Wrap known quantum division failure cases with xfail markers."""
    marked = []
    for triple in cases:
        if triple in KNOWN_TOFFOLI_QDIV_FAILURES:
            marked.append(
                pytest.param(
                    *triple,
                    marks=pytest.mark.xfail(
                        reason="QQ division: comparison ancilla leak in repeated-subtraction path",
                        strict=True,
                    ),
                )
            )
        else:
            marked.append(triple)
    return marked


def _mark_qmod_failures(cases):
    """Wrap known quantum modulo failure cases with xfail markers."""
    marked = []
    for triple in cases:
        if triple in KNOWN_TOFFOLI_QMOD_FAILURES:
            marked.append(
                pytest.param(
                    *triple,
                    marks=pytest.mark.xfail(
                        reason="QQ modulo: comparison ancilla leak in repeated-subtraction path",
                        strict=True,
                    ),
                )
            )
        else:
            marked.append(triple)
    return marked


# ---------------------------------------------------------------------------
# Test data generation
# ---------------------------------------------------------------------------
def _exhaustive_div_cases(widths):
    """Generate (width, a, divisor) for given widths, divisor in [1, 2^width)."""
    cases = []
    for width in widths:
        for a_val in range(1 << width):
            for divisor in range(1, 1 << width):
                cases.append((width, a_val, divisor))
    return cases


def _sampled_div_cases_w4():
    """Generate ~30 (width, a, divisor) for width 4 with deterministic seed."""
    width = 4
    max_val = (1 << width) - 1
    pairs = set()
    for a_val in [0, 1, max_val - 1, max_val]:
        for divisor in [1, 2, max_val - 1, max_val]:
            pairs.add((a_val, divisor))
    rng = random.Random(42)
    while len(pairs) < 30:
        a_val = rng.randint(0, max_val)
        divisor = rng.randint(1, max_val)
        pairs.add((a_val, divisor))
    return [(width, a, d) for a, d in sorted(pairs)]


def _exhaustive_qdiv_cases(widths):
    """Generate (width, a, b) for quantum division at given widths, b in [1, 2^width)."""
    cases = []
    for width in widths:
        for a_val in range(1 << width):
            for b_val in range(1, 1 << width):
                cases.append((width, a_val, b_val))
    return cases


EXHAUSTIVE_DIV_W2W3 = _exhaustive_div_cases([2, 3])
SAMPLED_DIV_W4 = _sampled_div_cases_w4()
EXHAUSTIVE_MOD_W2W3 = _exhaustive_div_cases([2, 3])
EXHAUSTIVE_QDIV_W2 = _exhaustive_qdiv_cases([2])
EXHAUSTIVE_QMOD_W2 = _exhaustive_qdiv_cases([2])


# ===========================================================================
# Test Class 1: Classical Divisor Division
# ===========================================================================
class TestToffoliClassicalDivision:
    """Verify a // divisor (classical) produces correct quotient in Toffoli mode.

    Exhaustive at widths 2-3, sampled at width 4.
    Width 1 is skipped (only divisor=1, always returns a).
    Phase 91: All xfail markers removed -- C-level CQ divmod is correct.
    """

    def _run_toffoli_div(self, width, a_val, divisor):
        """Run Toffoli division through pipeline, return actual quotient."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        a = ql.qint(a_val, width=width)
        q = a // divisor
        result_start = q.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        return _simulate_and_extract(qasm_str, num_qubits, result_start, width)

    @pytest.mark.parametrize(
        "width,a,divisor",
        EXHAUSTIVE_DIV_W2W3,
        ids=lambda *args: None,
    )
    def test_div_exhaustive(self, width, a, divisor):
        """Floor division: qint(a) // divisor at widths 2-3 (exhaustive, Toffoli mode)."""
        expected = a // divisor
        actual = self._run_toffoli_div(width, a, divisor)
        assert actual == expected, format_failure_message(
            "toffoli_div", [a, divisor], width, expected, actual
        )

    @pytest.mark.parametrize(
        "width,a,divisor",
        SAMPLED_DIV_W4,
        ids=lambda *args: None,
    )
    def test_div_sampled_width4(self, width, a, divisor):
        """Floor division: qint(a) // divisor at width 4 (sampled, Toffoli mode)."""
        expected = a // divisor
        actual = self._run_toffoli_div(width, a, divisor)
        assert actual == expected, format_failure_message(
            "toffoli_div", [a, divisor], width, expected, actual
        )


# ===========================================================================
# Test Class 2: Classical Divisor Modulo
# ===========================================================================
class TestToffoliClassicalModulo:
    """Verify a % divisor (classical) produces correct remainder in Toffoli mode.

    Exhaustive at widths 2-3. Phase 91: C-level CQ divmod fixes all cases
    (BUG-MOD-REDUCE resolved). No xfail markers needed.
    """

    def _run_toffoli_mod(self, width, a_val, divisor):
        """Run Toffoli modulo through pipeline, return actual remainder."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        a = ql.qint(a_val, width=width)
        r = a % divisor
        result_start = r.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        return _simulate_and_extract(qasm_str, num_qubits, result_start, width)

    @pytest.mark.parametrize(
        "width,a,divisor",
        EXHAUSTIVE_MOD_W2W3,
        ids=lambda *args: None,
    )
    def test_mod_exhaustive(self, width, a, divisor):
        """Modulo: qint(a) % divisor at widths 2-3 (exhaustive, Toffoli mode)."""
        expected = a % divisor
        actual = self._run_toffoli_mod(width, a, divisor)
        assert actual == expected, format_failure_message(
            "toffoli_mod", [a, divisor], width, expected, actual
        )


# ===========================================================================
# Test Class 3: Quantum Divisor Division
# ===========================================================================
class TestToffoliQuantumDivision:
    """Verify a // b (quantum divisor) produces correct quotient in Toffoli mode.

    Exhaustive at width 2 (37 qubits per circuit -- feasible with MPS after
    transpiling MCX gates). Width 3 requires 82 qubits -- too slow for testing.
    """

    def _run_toffoli_qdiv(self, width, a_val, b_val):
        """Run Toffoli quantum division through pipeline, return actual quotient."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        a = ql.qint(a_val, width=width)
        b = ql.qint(b_val, width=width)
        q = a // b
        result_start = q.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        return _simulate_and_extract(qasm_str, num_qubits, result_start, width)

    @pytest.mark.parametrize(
        "width,a,b",
        _mark_qdiv_failures(EXHAUSTIVE_QDIV_W2),
        ids=lambda *args: None,
    )
    def test_qdiv_exhaustive_w2(self, width, a, b):
        """Quantum floor division: qint(a) // qint(b) at width 2 (Toffoli mode)."""
        expected = a // b
        actual = self._run_toffoli_qdiv(width, a, b)
        assert actual == expected, format_failure_message(
            "toffoli_qdiv", [a, b], width, expected, actual
        )


# ===========================================================================
# Test Class 4: Quantum Divisor Modulo
# ===========================================================================
class TestToffoliQuantumModulo:
    """Verify a % b (quantum divisor) produces correct remainder in Toffoli mode.

    Exhaustive at width 2 (32 qubits per circuit).
    """

    def _run_toffoli_qmod(self, width, a_val, b_val):
        """Run Toffoli quantum modulo through pipeline, return actual remainder."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        a = ql.qint(a_val, width=width)
        b = ql.qint(b_val, width=width)
        r = a % b
        result_start = r.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        return _simulate_and_extract(qasm_str, num_qubits, result_start, width)

    @pytest.mark.parametrize(
        "width,a,b",
        _mark_qmod_failures(EXHAUSTIVE_QMOD_W2),
        ids=lambda *args: None,
    )
    def test_qmod_exhaustive_w2(self, width, a, b):
        """Quantum modulo: qint(a) % qint(b) at width 2 (Toffoli mode)."""
        expected = a % b
        actual = self._run_toffoli_qmod(width, a, b)
        assert actual == expected, format_failure_message(
            "toffoli_qmod", [a, b], width, expected, actual
        )


# ===========================================================================
# Test Class 5: Controlled Division
# ===========================================================================
class TestToffoliDivisionControlled:
    """Verify division inside `with ctrl:` block.

    Currently xfail because _divmod_c does not check the controlled context
    (_get_controlled). The C-level division always runs the uncontrolled
    variant regardless of whether a `with ctrl:` block is active. This means
    controlled division silently produces incorrect results (the division
    runs unconditionally instead of being gated on the control qubit).

    Phase 91: Updated reason from "controlled XOR not supported" to
    "_divmod_c ignores controlled context".
    """

    @pytest.mark.xfail(
        reason="Phase 91: _divmod_c ignores controlled context (always uncontrolled)",
        strict=True,
    )
    def test_controlled_div_active(self):
        """Controlled division with ctrl=|1> should produce correct quotient."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        ctrl = ql.qint(1, width=1)
        a = ql.qint(3, width=2)
        with ctrl:
            q = a // 2
        # Division runs unconditionally, but result should still be 1 if ctrl=1
        result_start = q.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, 2)
        assert actual == 1, f"Expected 3//2=1, got {actual}"

    def test_controlled_div_inactive(self):
        """Controlled division with ctrl=|0> should be no-op (quotient=0).

        Phase 91: This test passes because when ctrl=|0>, the controlled
        gates inside the division are no-ops, producing quotient=0. The
        active test (ctrl=|1>) still fails because the C-level division
        generates 0 instead of the expected quotient value.
        """
        gc.collect()
        ql.circuit()
        _enable_toffoli()
        ctrl = ql.qint(0, width=1)
        a = ql.qint(3, width=2)
        with ctrl:
            q = a // 2
        result_start = q.allocated_start
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits(qasm_str)
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, 2)
        assert actual == 0, f"Expected no-op quotient=0, got {actual}"


# ===========================================================================
# Test Class 6: Gate Purity
# ===========================================================================
class TestToffoliDivisionGatePurity:
    """Verify that division circuits in Toffoli mode contain no QFT gates.

    Division composes +=, -=, >=, and `with` blocks. In Toffoli mode, all
    arithmetic dispatches through CDKM adders (CCX/CX/X + MCX for controlled).
    No H, P, or CP gates should appear.
    """

    def test_div_no_qft_gates(self):
        """Classical division in Toffoli mode uses only Toffoli-compatible gates."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(3, width=2)
        q = a // 2

        qasm_str = ql.to_openqasm()

        forbidden_gates = {
            "h ",
            "p(",
            "cp(",
            "rz(",
            "ry(",
            "rx(",
            "u(",
            "u1(",
            "u2(",
            "u3(",
        }
        gate_lines = [
            line.strip()
            for line in qasm_str.split("\n")
            if line.strip()
            and not line.strip().startswith("//")
            and not line.strip().startswith("OPENQASM")
            and not line.strip().startswith("include")
            and not line.strip().startswith("qubit")
            and not line.strip().startswith("bit")
            and not line.strip().startswith("measure")
            and not line.strip().startswith("{")
            and not line.strip().startswith("}")
        ]

        violations = []
        for line in gate_lines:
            for fg in forbidden_gates:
                if line.lower().startswith(fg):
                    violations.append(line)

        assert not violations, "Found QFT-style gates in Toffoli division circuit:\n" + "\n".join(
            violations[:10]
        )

        # Verify only Toffoli-compatible gate types
        gate_types = set()
        for line in gate_lines:
            match = re.match(r"([a-z]+)", line.lower())
            if match:
                gate_types.add(match.group(1))

        # Expected: x, cx, ccx, ctrl (MCX), possibly barrier
        allowed = {"x", "cx", "ccx", "ctrl", "barrier", "mcx"}
        unexpected = gate_types - allowed
        assert not unexpected, f"Unexpected gate types in Toffoli division: {unexpected}"

        _ = (a, q)

    def test_mod_no_qft_gates(self):
        """Classical modulo in Toffoli mode uses only Toffoli-compatible gates."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(3, width=2)
        r = a % 2

        qasm_str = ql.to_openqasm()

        forbidden_gates = {
            "h ",
            "p(",
            "cp(",
            "rz(",
            "ry(",
            "rx(",
            "u(",
            "u1(",
            "u2(",
            "u3(",
        }
        gate_lines = [
            line.strip()
            for line in qasm_str.split("\n")
            if line.strip()
            and not line.strip().startswith("//")
            and not line.strip().startswith("OPENQASM")
            and not line.strip().startswith("include")
            and not line.strip().startswith("qubit")
            and not line.strip().startswith("bit")
            and not line.strip().startswith("measure")
            and not line.strip().startswith("{")
            and not line.strip().startswith("}")
        ]

        violations = []
        for line in gate_lines:
            for fg in forbidden_gates:
                if line.lower().startswith(fg):
                    violations.append(line)

        assert not violations, "Found QFT-style gates in Toffoli modulo circuit:\n" + "\n".join(
            violations[:10]
        )

        _ = (a, r)

    def test_default_dispatch_div(self):
        """Default mode (Toffoli) dispatches division without QFT gates.

        Verifies that a // b dispatches to Toffoli path without needing
        explicit ql.option('fault_tolerant', True).
        """
        gc.collect()
        ql.circuit()
        # Do NOT call _enable_toffoli() -- Toffoli is already the default
        a = ql.qint(3, width=2)
        q = a // 2
        qasm_str = ql.to_openqasm()

        forbidden_gates = {"h ", "p(", "cp("}
        gate_lines = [
            line.strip().lower()
            for line in qasm_str.split("\n")
            if line.strip()
            and not line.strip().startswith("//")
            and not line.strip().startswith("OPENQASM")
            and not line.strip().startswith("include")
            and not line.strip().startswith("qubit")
            and not line.strip().startswith("bit")
            and not line.strip().startswith("measure")
            and not line.strip().startswith("{")
            and not line.strip().startswith("}")
        ]

        violations = [gl for gl in gate_lines if any(gl.startswith(fg) for fg in forbidden_gates)]
        assert not violations, "Division in default mode uses QFT gates:\n" + "\n".join(
            violations[:5]
        )

        _ = (a, q)
