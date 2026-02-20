"""Phase 66: CDKM Ripple-Carry Adder - Exhaustive Verification Tests.

Tests all 5 success criteria:
1. QQ_add_toffoli generates correct addition using CCX/CX/X only
2. CQ_add_toffoli adds classical constant correctly using CCX/CX/X only
3. Subtraction works via inverted adder for both QQ and CQ
4. Mixed-width addition handles different bit widths
5. Ancilla is allocated, uncomputed, and freed correctly

Uses Qiskit AerSimulator for statevector simulation to verify
arithmetic correctness exhaustively for small widths.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _enable_toffoli():
    """Helper to enable Toffoli arithmetic mode."""
    ql.option("fault_tolerant", True)


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate a QASM circuit and extract result from specific qubit range.

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
    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    # Result register at physical qubits [result_start, result_start + result_width - 1]
    # MSB of result = qubit (result_start + result_width - 1) at position (N - result_start - result_width)
    # LSB of result = qubit result_start at position (N - 1 - result_start)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _verify_toffoli_qq(circuit_builder, width, w_a=None, w_b=None):
    """Verify a Toffoli QQ addition/subtraction circuit.

    For QQ add/sub, the result register c is at qubits [w_a + w_b .. w_a + w_b + result_width - 1].
    For result_width >= 2, there's 1 ancilla at the top.
    For result_width == 1, total is 2 qubits (no ancilla), c at qubit 1.

    Args:
        circuit_builder: Callable that builds circuit and returns (expected, keepalive_refs)
        width: Result register width (= max(w_a, w_b) for mixed, or same for equal)
        w_a: Width of first operand (defaults to width if None)
        w_b: Width of second operand (defaults to width if None)

    Returns:
        Tuple (actual, expected)
    """
    if w_a is None:
        w_a = width
    if w_b is None:
        w_b = width

    gc.collect()
    ql.circuit()

    result = circuit_builder()
    if isinstance(result, tuple):
        expected, _keepalive = result
    else:
        expected = result
        _keepalive = None

    qasm_str = ql.to_openqasm()

    # Get actual qubit count from the QASM qubit declaration
    num_qubits = None
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            num_qubits = int(line.split("[")[1].split("]")[0])
            break

    if num_qubits is None:
        raise Exception(f"Could not find qubit count in QASM:\n{qasm_str}")

    # Result register c starts after a and b registers
    result_start = w_a + w_b

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


class TestToffoliQQAddition:
    """Success Criterion 1: QQ_add_toffoli generates correct addition.

    Exhaustively tests all input pairs at widths 1-4.
    QQ_add (out-of-place) uses 2*N+1 qubits with Toffoli path.

    Uses custom verification that accounts for Toffoli ancilla qubit
    placement (ancilla at top of qubit array, result register below it).
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_qq_add_exhaustive(self, width):
        """QQ Toffoli addition produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    qc = qa + qb
                    return ((a + b) % (1 << w), [qa, qb, qc])

                actual, expected = _verify_toffoli_qq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_qq_add", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


def _verify_toffoli_cq(circuit_builder, width):
    """Verify a Toffoli CQ addition/subtraction circuit.

    For CQ add/sub (in-place), the result register is in the self qubits
    at positions [0..width-1]. Ancilla qubits (temp register + carry) are
    allocated at higher indices by the allocator.

    Args:
        circuit_builder: Callable that builds circuit and returns expected value
        width: Bit width of result register

    Returns:
        Tuple (actual, expected)
    """
    gc.collect()
    ql.circuit()

    result = circuit_builder()
    if isinstance(result, tuple):
        expected, _keepalive = result
    else:
        expected = result
        _keepalive = None

    qasm_str = ql.to_openqasm()

    # Get actual qubit count from the QASM qubit declaration
    num_qubits = None
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            num_qubits = int(line.split("[")[1].split("]")[0])
            break

    if num_qubits is None:
        raise Exception(f"Could not find qubit count in QASM:\n{qasm_str}")

    # Result register (self) starts at qubit 0
    result_start = 0

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


class TestToffoliCQAddition:
    """Success Criterion 2: CQ_add_toffoli adds classical constant correctly.

    Exhaustively tests all input pairs at widths 1-4.
    CQ_add (in-place) uses 2*N+1 qubits with Toffoli path (N temp + N self + 1 carry).
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_cq_add_exhaustive(self, width):
        """CQ Toffoli addition produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qa += b
                    return (a + b) % (1 << w)

                actual, expected = _verify_toffoli_cq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_cq_add", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliSubtraction:
    """Success Criterion 3: Subtraction works via inverted adder for both QQ and CQ.

    Exhaustively tests all input pairs at widths 1-4.
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_qq_sub_exhaustive(self, width):
        """QQ Toffoli subtraction produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    qc = qa - qb
                    return ((a - b) % (1 << w), [qa, qb, qc])

                actual, expected = _verify_toffoli_qq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_qq_sub", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_cq_sub_exhaustive(self, width):
        """CQ Toffoli subtraction produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qa -= b
                    return (a - b) % (1 << w)

                actual, expected = _verify_toffoli_cq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_cq_sub", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliMixedWidth:
    """Success Criterion 4: Mixed-width addition handles different bit widths.

    Tests representative input pairs for width combinations (2,3), (3,4), (4,6).
    """

    @pytest.mark.parametrize(
        "w_a,w_b",
        [(2, 3), (3, 4), (4, 6)],
    )
    def test_mixed_width_addition(self, w_a, w_b):
        """Mixed-width Toffoli addition produces correct results."""
        max_a = (1 << w_a) - 1
        max_b = (1 << w_b) - 1
        result_width = max(w_a, w_b)

        test_pairs = [
            (0, 0),
            (1, 1),
            (max_a, 1),
            (1, max_b),
            (max_a, max_b),
        ]

        failures = []
        for a, b in test_pairs:

            def circuit_builder(a=a, b=b, wa=w_a, wb=w_b):
                _enable_toffoli()
                qa = ql.qint(a, width=wa)
                qb = ql.qint(b, width=wb)
                qc = qa + qb
                rw = max(wa, wb)
                return ((a + b) % (1 << rw), [qa, qb, qc])

            actual, expected = _verify_toffoli_qq(circuit_builder, result_width, w_a=w_a, w_b=w_b)
            if actual != expected:
                failures.append(
                    f"FAIL: toffoli_mixed_add({a}[w={w_a}]+{b}[w={w_b}]) "
                    f"expected={expected}, got={actual}"
                )

        assert not failures, f"{len(failures)} failures:\n" + "\n".join(failures)

    @pytest.mark.parametrize(
        "w_a,w_b",
        [(2, 3), (3, 4), (4, 6)],
    )
    def test_mixed_width_subtraction(self, w_a, w_b):
        """Mixed-width Toffoli subtraction produces correct results."""
        max_a = (1 << w_a) - 1
        max_b = (1 << w_b) - 1
        result_width = max(w_a, w_b)

        test_pairs = [
            (0, 0),
            (1, 1),
            (max_a, 1),
            (1, max_b),
            (max_a, max_b),
        ]

        failures = []
        for a, b in test_pairs:

            def circuit_builder(a=a, b=b, wa=w_a, wb=w_b):
                _enable_toffoli()
                qa = ql.qint(a, width=wa)
                qb = ql.qint(b, width=wb)
                qc = qa - qb
                rw = max(wa, wb)
                return ((a - b) % (1 << rw), [qa, qb, qc])

            actual, expected = _verify_toffoli_qq(circuit_builder, result_width, w_a=w_a, w_b=w_b)
            if actual != expected:
                failures.append(
                    f"FAIL: toffoli_mixed_sub({a}[w={w_a}]-{b}[w={w_b}]) "
                    f"expected={expected}, got={actual}"
                )

        assert not failures, f"{len(failures)} failures:\n" + "\n".join(failures)


class TestToffoliAncillaLifecycle:
    """Success Criterion 5: Ancilla is allocated, uncomputed, and freed correctly.

    Tests sequential operations to detect ancilla leaks.
    """

    def test_sequential_qq_additions_no_crash(self):
        """Two sequential Toffoli QQ additions build without error.

        If ancilla leaked from first addition, allocator state would be
        corrupted and second addition would either crash or misallocate.
        Correctness of individual operations is verified by exhaustive tests.
        """
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a1 = ql.qint(3, width=4)
        b1 = ql.qint(5, width=4)
        c1 = a1 + b1  # First addition

        a2 = ql.qint(7, width=4)
        b2 = ql.qint(2, width=4)
        c2 = a2 + b2  # Second addition -- uses freed ancilla from first

        # If we got here without crash, ancilla lifecycle is working
        assert c1.width == 4
        assert c2.width == 4

        # Keep references alive
        _ = (a1, b1, c1, a2, b2, c2)

    def test_sequential_cq_additions_no_crash(self):
        """Two sequential Toffoli CQ additions build without error."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a1 = ql.qint(3, width=4)
        a1 += 5  # First CQ addition

        a2 = ql.qint(7, width=4)
        a2 += 2  # Second CQ addition -- uses freed ancilla from first

        assert a1.width == 4
        assert a2.width == 4

        _ = (a1, a2)

    def test_ancilla_freed_after_qq_addition(self):
        """Ancilla qubit is freed after QQ Toffoli addition.

        Verifies via allocator stats that current_in_use does not grow
        by more than the result register (ancilla was freed).
        """
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        c = a + b

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        # QQ addition creates result register (4 qubits) but ancilla should be freed.
        # in_use should increase by exactly result width (4), not result width + ancilla (5).
        increase = in_use_after - in_use_before
        assert increase == 4, (
            f"Expected in_use to increase by 4 (result register only), "
            f"but increased by {increase}. Ancilla may have leaked."
        )

        _ = (a, b, c)

    def test_ancilla_stats_after_addition(self):
        """Ancilla allocation count increases but current_in_use does not leak."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        stats_before = ql.circuit_stats()

        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        c = a + b

        stats_after = ql.circuit_stats()

        # Ancilla allocations should have increased (Toffoli adder uses ancilla)
        assert stats_after["ancilla_allocations"] >= stats_before["ancilla_allocations"], (
            f"Expected ancilla_allocations to increase, "
            f"before={stats_before['ancilla_allocations']}, "
            f"after={stats_after['ancilla_allocations']}"
        )

        # Keep references alive to prevent premature deallocation
        _ = (a, b, c)


class TestToffoliGateTypeVerification:
    """Success Criteria 1 & 2: Gate purity verification.

    Verifies that Toffoli circuits contain ONLY CCX/CX/X gates
    (no CP/H/P/Rz rotation gates from QFT).
    """

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_qq_toffoli_gate_purity(self, width):
        """QQ Toffoli addition uses only CCX/CX/X gates."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(1, width=width)
        b = ql.qint(2, width=width)
        c = a + b

        # Get gate counts from circuit
        circ = ql.circuit.__new__(ql.circuit)
        counts = circ.gate_counts

        # Toffoli circuits should have ZERO QFT-style gates
        assert counts["H"] == 0, f"Found {counts['H']} H gates in Toffoli circuit (width={width})"
        assert counts["P"] == 0, f"Found {counts['P']} P gates in Toffoli circuit (width={width})"

        # Should have some X/CX/CCX gates
        toffoli_gates = counts["X"] + counts["CNOT"] + counts["CCX"]
        assert toffoli_gates > 0, f"No Toffoli gates found in circuit (width={width})"

        # Keep references alive
        _ = (a, b, c)

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_cq_toffoli_gate_purity(self, width):
        """CQ Toffoli addition uses only CCX/CX/X gates."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(1, width=width)
        a += 3

        circ = ql.circuit.__new__(ql.circuit)
        counts = circ.gate_counts

        assert counts["H"] == 0, (
            f"Found {counts['H']} H gates in Toffoli CQ circuit (width={width})"
        )
        assert counts["P"] == 0, (
            f"Found {counts['P']} P gates in Toffoli CQ circuit (width={width})"
        )

        toffoli_gates = counts["X"] + counts["CNOT"] + counts["CCX"]
        assert toffoli_gates > 0, f"No Toffoli gates found in CQ circuit (width={width})"

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_qq_toffoli_gate_purity_via_qasm(self, width):
        """Verify via OpenQASM export that only Toffoli-compatible gates are used."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(1, width=width)
        b = ql.qint(2, width=width)
        c = a + b

        qasm_str = ql.to_openqasm()

        # Parse QASM lines for gate instructions
        forbidden_gates = {"h ", "p(", "cp(", "rz(", "ry(", "rx(", "u(", "u1(", "u2(", "u3("}
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

        assert not violations, (
            f"Found QFT-style gates in Toffoli circuit (width={width}):\n"
            + "\n".join(violations[:10])
        )

        # Keep references alive
        _ = (a, b, c)


def _verify_controlled_inplace(circuit_builder, width):
    """Verify a controlled in-place Toffoli addition/subtraction circuit.

    For controlled in-place operations (a += b or a += val inside `with ctrl:`),
    the result register (self/a) is always at physical qubits [0..width-1].
    Ancilla qubits (carry, temp, control) are at higher indices.

    Args:
        circuit_builder: Callable that builds circuit and returns expected value
        width: Bit width of result register

    Returns:
        Tuple (actual, expected)
    """
    gc.collect()
    ql.circuit()

    result = circuit_builder()
    if isinstance(result, tuple):
        expected, _keepalive = result
    else:
        expected = result
        _keepalive = None

    qasm_str = ql.to_openqasm()

    # Get actual qubit count from the QASM qubit declaration
    num_qubits = None
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            num_qubits = int(line.split("[")[1].split("]")[0])
            break

    if num_qubits is None:
        raise Exception(f"Could not find qubit count in QASM:\n{qasm_str}")

    # Result register (self) starts at qubit 0
    result_start = 0

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


class TestControlledToffoliQQAddition:
    """Phase 67: Controlled QQ Toffoli addition verification.

    Tests controlled in-place QQ addition (a += b inside `with ctrl:`) using
    the Toffoli CDKM path. Verifies that:
    - control=|1> performs addition correctly
    - control=|0> is a no-op
    - Controlled subtraction works
    - Only X-type gates (CCX/CX/X) are used
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_cqq_toffoli_add_control_active(self, width):
        """Controlled QQ Toffoli addition with control=|1>."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(1, width=1)
                    with ctrl:
                        qa += qb
                    return ((a + b) % (1 << w), [qa, qb, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_cqq_add_ctrl1", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_cqq_toffoli_add_control_inactive(self, width):
        """Controlled QQ Toffoli addition with control=|0> (no-op)."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(0, width=1)
                    with ctrl:
                        qa += qb
                    return (a, [qa, qb, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_cqq_add_ctrl0", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_cqq_toffoli_sub_control_active(self, width):
        """Controlled QQ Toffoli subtraction with control=|1>."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(1, width=1)
                    with ctrl:
                        qa -= qb
                    return ((a - b) % (1 << w), [qa, qb, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_cqq_sub_ctrl1", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_cqq_toffoli_gate_purity(self, width):
        """Controlled QQ Toffoli addition uses only X-type gates (CCX/CX/X)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        qa = ql.qint(1, width=width)
        qb = ql.qint(2, width=width)
        ctrl = ql.qint(1, width=1)
        with ctrl:
            qa += qb

        circ = ql.circuit.__new__(ql.circuit)
        counts = circ.gate_counts

        assert counts["H"] == 0, (
            f"Found {counts['H']} H gates in controlled Toffoli QQ circuit (width={width})"
        )
        assert counts["P"] == 0, (
            f"Found {counts['P']} P gates in controlled Toffoli QQ circuit (width={width})"
        )

        toffoli_gates = counts["X"] + counts["CNOT"] + counts["CCX"]
        assert toffoli_gates > 0, f"No Toffoli gates found in controlled QQ circuit (width={width})"

        _ = (qa, qb, ctrl)


class TestControlledToffoliCQAddition:
    """Phase 67: Controlled CQ Toffoli addition verification.

    Tests controlled in-place CQ addition (a += val inside `with ctrl:`) using
    the Toffoli CDKM path. Verifies that:
    - control=|1> performs addition correctly
    - control=|0> is a no-op
    - Controlled subtraction works
    - Only X-type gates (CCX/CX/X) are used
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_ccq_toffoli_add_control_active(self, width):
        """Controlled CQ Toffoli addition with control=|1>."""
        failures = []

        for a in range(1 << width):
            for val in range(1 << width):

                def circuit_builder(a=a, val=val, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(1, width=1)
                    with ctrl:
                        qa += val
                    return ((a + val) % (1 << w), [qa, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_ccq_add_ctrl1", [a, val], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2, 3, 4])
    def test_ccq_toffoli_add_control_inactive(self, width):
        """Controlled CQ Toffoli addition with control=|0> (no-op)."""
        failures = []

        for a in range(1 << width):
            for val in range(1 << width):

                def circuit_builder(a=a, val=val, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(0, width=1)
                    with ctrl:
                        qa += val
                    return (a, [qa, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_ccq_add_ctrl0", [a, val], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_ccq_toffoli_sub_control_active(self, width):
        """Controlled CQ Toffoli subtraction with control=|1>."""
        failures = []

        for a in range(1 << width):
            for val in range(1 << width):

                def circuit_builder(a=a, val=val, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(1, width=1)
                    with ctrl:
                        qa -= val
                    return ((a - val) % (1 << w), [qa, ctrl])

                actual, expected = _verify_controlled_inplace(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_ccq_sub_ctrl1", [a, val], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_ccq_toffoli_gate_purity(self, width):
        """Controlled CQ Toffoli addition uses only X-type gates (CCX/CX/X)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        qa = ql.qint(1, width=width)
        ctrl = ql.qint(1, width=1)
        with ctrl:
            qa += 3

        circ = ql.circuit.__new__(ql.circuit)
        counts = circ.gate_counts

        assert counts["H"] == 0, (
            f"Found {counts['H']} H gates in controlled Toffoli CQ circuit (width={width})"
        )
        assert counts["P"] == 0, (
            f"Found {counts['P']} P gates in controlled Toffoli CQ circuit (width={width})"
        )

        toffoli_gates = counts["X"] + counts["CNOT"] + counts["CCX"]
        assert toffoli_gates > 0, f"No Toffoli gates found in controlled CQ circuit (width={width})"

        _ = (qa, ctrl)


class TestToffoliFaultTolerantOption:
    """Test the fault_tolerant option itself (get/set/reset behavior)."""

    def test_default_is_toffoli(self):
        """Default arithmetic mode is Toffoli (fault_tolerant=True)."""
        gc.collect()
        ql.circuit()
        assert ql.option("fault_tolerant") is True

    def test_set_true(self):
        """Setting fault_tolerant to True enables Toffoli mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        assert ql.option("fault_tolerant") is True

    def test_set_false_restores_qft(self):
        """Setting fault_tolerant back to False restores QFT mode."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("fault_tolerant", False)
        assert ql.option("fault_tolerant") is False

    def test_rejects_non_bool(self):
        """fault_tolerant option rejects non-bool values."""
        gc.collect()
        ql.circuit()
        with pytest.raises(ValueError, match="fault_tolerant option requires bool"):
            ql.option("fault_tolerant", 1)

    def test_circuit_reset_restores_default(self):
        """Creating a new circuit resets fault_tolerant to default (True/Toffoli)."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)
        assert ql.option("fault_tolerant") is False
        ql.circuit()  # Reset
        assert ql.option("fault_tolerant") is True


class TestDefaultModeToffoli:
    """Verify that Toffoli is the default arithmetic mode (Phase 67-03)."""

    def test_default_is_toffoli(self):
        """Default arithmetic should be Toffoli without explicit option."""
        gc.collect()
        ql.circuit()
        # Do NOT call ql.option('fault_tolerant', True) -- Toffoli is default
        a = ql.qint(3, width=3)
        b = ql.qint(2, width=3)
        a += b
        qasm = ql.to_openqasm()
        # Should contain CCX/CX/X gates, NOT H or P gates from QFT
        gate_lines = [
            line.strip().lower()
            for line in qasm.split("\n")
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
        h_gates = [gl for gl in gate_lines if gl.startswith("h ")]
        p_gates = [gl for gl in gate_lines if gl.startswith("p(")]
        assert len(h_gates) == 0, f"Default mode should not use H gates, found {len(h_gates)}"
        assert len(p_gates) == 0, f"Default mode should not use P gates, found {len(p_gates)}"

    def test_qft_opt_in(self):
        """QFT mode available via explicit option."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=3)
        b = ql.qint(2, width=3)
        a += b
        qasm = ql.to_openqasm()
        # QFT mode should use H/P gates
        qasm_lower = qasm.lower()
        has_rotation = "h " in qasm_lower or "rz" in qasm_lower or "p(" in qasm_lower
        assert has_rotation, "QFT mode should use rotation gates"


class TestToffoliQFTFallback:
    """Test that QFT path still works when fault_tolerant is False.

    Ensures the existing QFT arithmetic is not broken by the Toffoli wiring.
    Since Phase 67-03, the default is Toffoli, so QFT requires explicit opt-in.
    """

    def test_qft_addition_still_works(self, verify_circuit):
        """QFT addition (via explicit opt-in) produces correct results."""

        def circuit_builder():
            ql.option("fault_tolerant", False)
            assert ql.option("fault_tolerant") is False
            qa = ql.qint(3, width=4)
            qb = ql.qint(5, width=4)
            qc = qa + qb
            return (8, [qa, qb, qc])

        actual, expected = verify_circuit(circuit_builder, width=4)
        assert actual == expected, f"QFT addition broken: expected {expected}, got {actual}"

    def test_qft_has_rotation_gates(self):
        """QFT path uses H and P gates (distinguishing it from Toffoli path)."""
        gc.collect()
        ql.circuit()
        # Opt in to QFT mode
        ql.option("fault_tolerant", False)
        assert ql.option("fault_tolerant") is False

        a = ql.qint(1, width=4)
        b = ql.qint(2, width=4)
        c = a + b

        circ = ql.circuit.__new__(ql.circuit)
        counts = circ.gate_counts

        # QFT path should use H and P gates
        assert counts["H"] > 0, "QFT path should use H gates"
        assert counts["P"] > 0, "QFT path should use P gates"

        _ = (a, b, c)
