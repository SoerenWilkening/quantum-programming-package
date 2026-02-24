"""Phase 68/69: Toffoli Schoolbook Multiplication - Exhaustive Verification Tests.

Tests all success criteria for uncontrolled and controlled Toffoli multiplication:

Phase 68 (uncontrolled):
1. QQ Toffoli multiplication produces correct product for all input pairs at widths 1-3
2. CQ Toffoli multiplication produces correct product for all input pairs at widths 1-3
3. Toffoli multiplication circuits contain only CCX/CX/X gates (no CP/H gates)
4. a * b and a *= b operators dispatch to Toffoli multiplication in default mode

Phase 69 (controlled):
5. cQQ Toffoli multiplication correct for all input pairs at widths 1-3 with control=|1>
6. cQQ Toffoli multiplication is a no-op for all input pairs at widths 1-2 with control=|0>
7. cCQ Toffoli multiplication correct for all input pairs at widths 1-3 with control=|1>
8. cCQ Toffoli multiplication is a no-op for all input pairs at widths 1-2 with control=|0>
9. Controlled Toffoli multiplication circuits contain only CCX/CX/X gates

Uses Qiskit AerSimulator for statevector simulation to verify
arithmetic correctness exhaustively for small widths.

NOTE: Controlled multiplication tests use a scope-depth workaround for
BUG-COND-MUL-01 (out-of-place multiplication results created inside
`with ctrl:` blocks get auto-uncomputed by scope cleanup). The C backend
generates correct circuits; the Python scope management incorrectly
reverses the gates. The workaround temporarily sets scope_depth=0 during
the multiplication so the result qint does not register in the scope frame.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

# BUG-COND-MUL-01 workaround removed: scope depth bypass now in production __mul__/__rmul__

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


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM string."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise Exception(f"Could not find qubit count in QASM:\n{qasm_str}")


def _verify_toffoli_mul_qq(circuit_builder, width):
    """Verify a Toffoli QQ multiplication circuit.

    For QQ mul (c = a * b), the allocation order is:
      a (self) at [0..width-1]
      b (other) at [width..2*width-1]
      c (result) at [2*width..3*width-1]
    Ancilla qubits (from CDKM adder loop) are above that.

    Args:
        circuit_builder: Callable that builds circuit and returns (expected, keepalive_refs)
        width: Result register width

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
    num_qubits = _get_num_qubits(qasm_str)

    # Result register c starts after a and b registers
    result_start = 2 * width

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


def _verify_toffoli_mul_cq(circuit_builder, width):
    """Verify a Toffoli CQ multiplication circuit.

    For CQ imul (qa *= val), __imul__ calls __mul__ which allocates:
      qa_orig (self) at [0..width-1]
      result at [width..2*width-1]
    Then __imul__ swaps qa's Python qubit refs to point to result qubits.
    Ancilla qubits (from CDKM adder loop) are above that.

    The product is computed into the result register at [width..2*width-1].

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
    num_qubits = _get_num_qubits(qasm_str)

    # Result register starts after original self qubits
    result_start = width

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


class TestToffoliQQMultiplication:
    """Success Criterion 1: QQ Toffoli multiplication produces correct product.

    Exhaustively tests all input pairs at widths 1-3.
    QQ mul (out-of-place) allocates 3*width qubits + ancilla.
    """

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_qq_mul_exhaustive(self, width):
        """QQ Toffoli multiplication produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    qc = qa * qb
                    return ((a * b) % (1 << w), [qa, qb, qc])

                actual, expected = _verify_toffoli_mul_qq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_qq_mul", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliCQMultiplication:
    """Success Criterion 2: CQ Toffoli multiplication produces correct product.

    Exhaustively tests all input pairs at widths 1-3.
    CQ imul allocates 2*width qubits + ancilla.
    """

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_cq_mul_exhaustive(self, width):
        """CQ Toffoli multiplication produces correct results for all input pairs."""
        failures = []

        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qa *= b
                    return (a * b) % (1 << w)

                actual, expected = _verify_toffoli_mul_cq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("toffoli_cq_mul", [a, b], width, expected, actual)
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliMultiplicationGatePurity:
    """Success Criterion 3: Toffoli multiplication circuits contain only CCX/CX/X gates.

    Verifies via both gate_counts API and OpenQASM export that no QFT-style
    rotation gates (H, P, CP, Rz) appear in the multiplication circuits.
    """

    def test_qq_mul_no_qft_gates(self):
        """QQ Toffoli multiplication uses only CCX/CX/X gates (width 2)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(2, width=2)
        b = ql.qint(3, width=2)
        c = a * b

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

        assert not violations, "Found QFT-style gates in Toffoli QQ mul circuit:\n" + "\n".join(
            violations[:10]
        )

        # Keep references alive
        _ = (a, b, c)

    def test_cq_mul_no_qft_gates(self):
        """CQ Toffoli multiplication uses only CCX/CX/X gates (width 2)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(2, width=2)
        a *= 3

        qasm_str = ql.to_openqasm()

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

        assert not violations, "Found QFT-style gates in Toffoli CQ mul circuit:\n" + "\n".join(
            violations[:10]
        )

    def test_operator_dispatch_mul(self):
        """Default mode (Toffoli) dispatches a * b and a *= b without QFT gates.

        Verifies success criterion 4: operators use Toffoli path in default mode
        without needing explicit ql.option('fault_tolerant', True).
        """
        # Test a * b (QQ) in default mode
        gc.collect()
        ql.circuit()
        # Do NOT call _enable_toffoli() -- Toffoli is already the default
        a = ql.qint(2, width=3)
        b = ql.qint(3, width=3)
        c = a * b
        qasm_qq = ql.to_openqasm()

        forbidden_gates = {"h ", "p(", "cp("}
        gate_lines_qq = [
            line.strip().lower()
            for line in qasm_qq.split("\n")
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

        qq_violations = [
            gl for gl in gate_lines_qq if any(gl.startswith(fg) for fg in forbidden_gates)
        ]
        assert not qq_violations, "QQ mul in default mode uses QFT gates:\n" + "\n".join(
            qq_violations[:5]
        )

        # Test a *= b (CQ) in default mode
        gc.collect()
        ql.circuit()
        a2 = ql.qint(2, width=3)
        a2 *= 3
        qasm_cq = ql.to_openqasm()

        gate_lines_cq = [
            line.strip().lower()
            for line in qasm_cq.split("\n")
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

        cq_violations = [
            gl for gl in gate_lines_cq if any(gl.startswith(fg) for fg in forbidden_gates)
        ]
        assert not cq_violations, "CQ imul in default mode uses QFT gates:\n" + "\n".join(
            cq_violations[:5]
        )

        _ = (a, b, c, a2)


# ============================================================================
# Phase 69: Controlled Toffoli Multiplication Verification
# ============================================================================


def _verify_toffoli_cmul_qq(circuit_builder, width):
    """Verify a controlled Toffoli QQ multiplication circuit.

    For controlled QQ mul (with ctrl: c = a * b), the allocation order is:
      a (self) at [0..width-1]
      b (other) at [width..2*width-1]
      ctrl at [2*width] (1-bit control qubit)
      c (result) at [2*width+1..3*width]
    Ancilla qubits (carry, AND ancilla from CDKM adder loop) are above that.

    Uses allocated_start from the result qint for robust result extraction.

    WORKAROUND (BUG-COND-MUL-01): Temporarily sets scope_depth=0 during the
    multiplication inside `with ctrl:` to prevent the result qint from being
    registered in the scope frame and auto-uncomputed at scope exit. The C
    backend generates correct circuits; only Python scope cleanup is broken.

    Args:
        circuit_builder: Callable that builds circuit and returns (expected, keepalive_refs).
                         Must use the scope-depth workaround internally.
        width: Result register width

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
    num_qubits = _get_num_qubits(qasm_str)

    # Use allocated_start from the result qint for robust extraction
    # The circuit_builder returns keepalive refs; the result qint (qc) is in there
    if isinstance(_keepalive, list) and len(_keepalive) >= 4:
        qc = _keepalive[3]  # [qa, qb, ctrl, qc]
        result_start = qc.allocated_start
    else:
        # Fallback: ctrl at 2*width, result at 2*width+1
        result_start = 2 * width + 1

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


def _verify_toffoli_cmul_cq(circuit_builder, width):
    """Verify a controlled Toffoli CQ multiplication circuit.

    For controlled CQ imul (with ctrl: a *= val), __imul__ calls __mul__ which:
      - Allocates a_orig (self) at [0..width-1]
      - ctrl at [width] (allocated before result because `with ctrl:` entered first)
      - result at [width+1..2*width]
    Then __imul__ swaps qa's Python qubit refs to point to result qubits.

    Uses allocated_start from the qa qint (which now points to result register).

    WORKAROUND (BUG-COND-MUL-01): Same scope-depth workaround as cQQ.

    Args:
        circuit_builder: Callable that builds circuit and returns (expected, keepalive_refs)
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
    num_qubits = _get_num_qubits(qasm_str)

    # Use allocated_start from qa (which points to result register after *=)
    if isinstance(_keepalive, list) and len(_keepalive) >= 1:
        qa = _keepalive[0]  # [qa, ctrl]
        result_start = qa.allocated_start
    else:
        # Fallback: ctrl at width, result at width+1
        result_start = width + 1

    _keepalive = None

    try:
        actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
        return (actual, expected)
    except Exception as e:
        raise Exception(f"Simulation failed: {e}\n\nQASM:\n{qasm_str}") from e


class TestToffoliControlledQQMultiplication:
    """Controlled QQ Toffoli multiplication (cQQ) verification.

    Tests with control=|1> (multiplication happens) and control=|0> (no-op).
    Uses scope-depth workaround for BUG-COND-MUL-01.
    """

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_cqq_mul_control_active(self, width):
        """cQQ mul with control=|1> produces correct product for all input pairs."""
        failures = []
        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(1, width=1)  # control = |1>
                    with ctrl:
                        qc = qa * qb
                    return ((a * b) % (1 << w), [qa, qb, ctrl, qc])

                actual, expected = _verify_toffoli_cmul_qq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_cqq_mul_active", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2])
    def test_cqq_mul_control_inactive(self, width):
        """cQQ mul with control=|0> is a no-op (result stays 0)."""
        failures = []
        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(0, width=1)  # control = |0>
                    with ctrl:
                        qc = qa * qb
                    return (0, [qa, qb, ctrl, qc])  # expect 0 (no mul)

                actual, expected = _verify_toffoli_cmul_qq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_cqq_mul_inactive", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliControlledCQMultiplication:
    """Controlled CQ Toffoli multiplication (cCQ) verification.

    Tests with control=|1> (multiplication happens) and control=|0> (no-op).
    Uses scope-depth workaround for BUG-COND-MUL-01.
    """

    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_ccq_mul_control_active(self, width):
        """cCQ mul with control=|1> produces correct product for all input pairs."""
        failures = []
        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(1, width=1)
                    with ctrl:
                        qa *= b
                    return ((a * b) % (1 << w), [qa, ctrl])

                actual, expected = _verify_toffoli_cmul_cq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_ccq_mul_active", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )

    @pytest.mark.parametrize("width", [1, 2])
    def test_ccq_mul_control_inactive(self, width):
        """cCQ mul with control=|0> is a no-op (result register stays 0).

        When ctrl=|0>, the multiplication is skipped. __imul__ creates a new
        result register initialized to |0> and swaps Python refs. With ctrl=|0>,
        the Toffoli multiplication gates are all gated off, so the result
        register stays at |0>. The Python variable 'qa' now points to the
        result register (which is |0>).
        """
        failures = []
        for a in range(1 << width):
            for b in range(1 << width):

                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(0, width=1)
                    with ctrl:
                        qa *= b
                    return (0, [qa, ctrl])  # result register stays 0

                actual, expected = _verify_toffoli_cmul_cq(circuit_builder, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "toffoli_ccq_mul_inactive", [a, b], width, expected, actual
                        )
                    )

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(
            failures[:10]
        )


class TestToffoliControlledMultiplicationGatePurity:
    """Controlled Toffoli multiplication gate purity verification.

    Verifies that controlled multiplication circuits contain only
    CCX/CX/X/MCX gates (no QFT-style rotation gates).
    """

    def test_cqq_mul_no_qft_gates(self):
        """Controlled QQ Toffoli multiplication uses only CCX/CX/X gates (width 2)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(2, width=2)
        b = ql.qint(3, width=2)
        ctrl = ql.qint(1, width=1)
        with ctrl:
            c = a * b

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
            "Found QFT-style gates in controlled Toffoli QQ mul circuit:\n"
            + "\n".join(violations[:10])
        )

        # Verify that some gates were actually generated (not empty circuit)
        non_x_gates = [g for g in gate_lines if not g.startswith("x ")]
        assert len(non_x_gates) > 0, "Controlled QQ mul circuit has no non-init gates"

        _ = (a, b, ctrl, c)

    def test_ccq_mul_no_qft_gates(self):
        """Controlled CQ Toffoli multiplication uses only CCX/CX/X gates (width 2)."""
        gc.collect()
        ql.circuit()
        _enable_toffoli()

        a = ql.qint(2, width=2)
        ctrl = ql.qint(1, width=1)
        with ctrl:
            a *= 3

        qasm_str = ql.to_openqasm()

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
            "Found QFT-style gates in controlled Toffoli CQ mul circuit:\n"
            + "\n".join(violations[:10])
        )

        # Verify that some gates were actually generated
        non_x_gates = [g for g in gate_lines if not g.startswith("x ")]
        assert len(non_x_gates) > 0, "Controlled CQ mul circuit has no non-init gates"

        _ = (a, ctrl)
