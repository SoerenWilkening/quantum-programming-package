"""Validation tests for hardcoded addition sequences.

These tests verify that hardcoded (pre-computed) sequences for widths 1-16
produce correct arithmetic results - functional equivalence to dynamic generation.

NOTE: We test ARITHMETIC CORRECTNESS, not gate-by-gate structure comparison.
The internal gate sequence is an implementation detail. What matters is that
addition operations produce mathematically correct results.

Simulation constraints (qubit budget, ~8 GB available):
- QQ_add out-of-place (3*N qubits): feasible for widths 1-9 (27 qubits max)
- CQ_add in-place (N qubits): feasible for ALL widths 1-16
- cCQ_add / controlled CQ_add (N+1 qubits): feasible for ALL widths 1-16

Per CONTEXT.md, this is one-time verification (not in regular CI).
Mark with @pytest.mark.hardcoded_validation to allow filtering.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

# Suppress cosmetic warnings for values >= 2^(width-1) in unsigned interpretation
warnings.filterwarnings("ignore", message="Value .* exceeds")


@pytest.mark.hardcoded_validation
class TestHardcodedSequenceValidation:
    """Verify hardcoded sequences produce correct arithmetic results."""

    @pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6, 7, 8, 9])
    def test_qq_add_produces_correct_results(self, verify_circuit, width):
        """QQ_add hardcoded produces correct arithmetic results.

        Out-of-place QQ_add uses 3*N qubits, so feasible up to width 9 (27 qubits).
        Width 10+ exceeds available memory for statevector simulation.
        """
        # Test representative values including edge cases
        test_cases = [(0, 0), (1, 1)]
        max_val = (1 << width) - 1

        # Add more test cases that fit within the width
        if width >= 2:
            test_cases.append((2, 3) if max_val >= 3 else (max_val, 1))

        # Boundary cases
        test_cases.extend([(max_val, 1), (max_val, max_val)])

        for a, b in test_cases:
            if a >= (1 << width) or b >= (1 << width):
                continue

            def circuit_builder(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                _r = qa + qb
                return (a + b) % (1 << w)

            actual, expected = verify_circuit(circuit_builder, width)
            assert actual == expected, format_failure_message(
                "qq_add_hardcoded", [a, b], width, expected, actual
            )

    @pytest.mark.parametrize("width", range(1, 17))
    def test_cq_add_produces_correct_results(self, verify_circuit, width):
        """CQ_add (classical-quantum) produces correct arithmetic results.

        In-place CQ_add uses N qubits, feasible for all widths 1-16.
        """
        # Test representative values
        test_cases = [(0, 0), (1, 1)]
        max_val = (1 << width) - 1

        if width >= 2:
            test_cases.append((2, 3) if max_val >= 3 else (max_val, 1))

        test_cases.extend([(max_val, 1), (1, max_val)])

        # For large widths, cap classical values to keep them reasonable
        if width > 8:
            capped_max = min(max_val, 255)
            test_cases = [(0, 0), (1, 1), (1, capped_max), (capped_max, 1)]

        for a, b in test_cases:
            if a >= (1 << width) or b >= (1 << width):
                continue

            def circuit_builder(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qa += b  # In-place classical addition
                return (a + b) % (1 << w)

            actual, expected = verify_circuit(circuit_builder, width)
            assert actual == expected, format_failure_message(
                "cq_add_hardcoded", [a, b], width, expected, actual
            )

    @pytest.mark.parametrize("width", [11, 12, 13, 14, 15, 16])
    def test_cq_add_large_widths_correctness(self, verify_circuit, width):
        """CQ_add for large widths (11-16) with multiple test values.

        These widths are too large for out-of-place QQ_add simulation (3*N qubits),
        but CQ_add (N qubits) is feasible. Tests boundary and representative values.
        """
        max_val = (1 << width) - 1
        test_cases = [
            (0, 0),  # identity
            (1, 1),  # simple
            (1, max_val),  # 1 + max wraps to 0
            (max_val, 1),  # max + 1 wraps to 0
            (100, 200),  # medium values
        ]

        for a, b in test_cases:
            if a >= (1 << width) or b >= (1 << width):
                continue

            def circuit_builder(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qa += b
                return (a + b) % (1 << w)

            actual, expected = verify_circuit(circuit_builder, width)
            assert actual == expected, format_failure_message(
                "cq_add_large", [a, b], width, expected, actual
            )

    def test_dynamic_fallback_widths(self, verify_circuit):
        """Width 17 uses dynamic generation and produces correct results.

        Width 17 is the first width beyond the hardcoded range (1-16).
        Uses CQ_add (in-place, 17 qubits) to avoid memory issues.
        """
        width = 17

        def circuit_builder(w=width):
            qa = ql.qint(1, width=w)
            qa += 255  # In-place classical addition
            return (1 + 255) % (1 << w)

        actual, expected = verify_circuit(circuit_builder, width)
        assert actual == expected, format_failure_message(
            "cq_add_dynamic", [1, 255], width, expected, actual
        )

    @pytest.mark.parametrize("width", [17, 18])
    def test_cq_dynamic_fallback_widths(self, verify_circuit, width):
        """CQ addition with widths > 16 uses dynamic generation correctly."""
        max_val = min((1 << width) - 1, 255)

        def circuit_builder(w=width, mv=max_val):
            qa = ql.qint(1, width=w)
            qa += mv
            return (1 + mv) % (1 << w)

        actual, expected = verify_circuit(circuit_builder, width)
        assert actual == expected, format_failure_message(
            "cq_add_dynamic", [1, max_val], width, expected, actual
        )


@pytest.mark.hardcoded_validation
class TestHardcodedSequenceExecution:
    """Verify hardcoded sequences execute without errors.

    These tests build circuits without full simulation -- just verify that
    the hardcoded gate sequences can be loaded and applied without crashing.
    """

    @pytest.mark.parametrize("width", range(1, 17))
    def test_qq_add_circuit_executes(self, width):
        """QQ_add hardcoded executes without error and produces non-trivial circuit."""
        circ = ql.circuit()
        qa = ql.qint(0, width=width)
        qb = ql.qint(0, width=width)
        _r = qa + qb

        assert circ.depth >= 1, f"Circuit should have non-zero depth for width {width}"

    @pytest.mark.parametrize("width", range(1, 17))
    def test_controlled_cq_add_circuit_executes(self, width):
        """Controlled CQ_add executes without error.

        NOTE: Controlled QQ addition (qa + qb inside `with ctrl:`) raises
        NotImplementedError at user level. However, controlled CQ addition
        (qa += b inside `with ctrl:`) works and uses the cQQ_add sequences
        internally via CQ_add's controlled path.
        """
        circ = ql.circuit()
        qa = ql.qint(1, width=width)

        # Controlled CQ addition via context manager
        ctrl = ql.qint(1, width=1)
        with ctrl:
            qa += 1  # Controlled in-place classical addition

        assert circ.depth >= 1, f"Controlled circuit should have depth for width {width}"

    @pytest.mark.parametrize("width", range(1, 17))
    def test_cq_add_circuit_executes(self, width):
        """CQ_add (classical-quantum) executes without error."""
        circ = ql.circuit()
        qa = ql.qint(0, width=width)
        qa += 1  # In-place classical addition

        assert circ.depth >= 1, f"CQ circuit should have non-zero depth for width {width}"


@pytest.mark.hardcoded_validation
class TestHardcodedBoundaryConditions:
    """Test boundary conditions for hardcoded sequence widths."""

    def test_width_8_boundary(self, verify_circuit):
        """Width 8 is the middle of the hardcoded range - verify it works correctly."""
        max_val = 255  # 2^8 - 1

        def circuit_builder():
            qa = ql.qint(max_val, width=8)
            qb = ql.qint(1, width=8)
            _r = qa + qb
            return 0  # 255 + 1 = 256 mod 256 = 0

        actual, expected = verify_circuit(circuit_builder, 8)
        assert actual == expected, f"Width 8 overflow: expected {expected}, got {actual}"

    def test_width_16_boundary(self, verify_circuit):
        """Width 16 is the last hardcoded width - verify CQ_add with boundary values."""
        width = 16
        max_val = (1 << width) - 1  # 65535

        # Test 0 + 0 = 0
        def circuit_zero(w=width):
            qa = ql.qint(0, width=w)
            qa += 0
            return 0

        actual, expected = verify_circuit(circuit_zero, width)
        assert actual == expected, f"Width 16 zero: expected {expected}, got {actual}"

        # Test 1 + 1 = 2
        def circuit_one(w=width):
            qa = ql.qint(1, width=w)
            qa += 1
            return 2

        actual, expected = verify_circuit(circuit_one, width)
        assert actual == expected, f"Width 16 add: expected {expected}, got {actual}"

        # Test max + 1 = 0 (overflow wrapping)
        def circuit_overflow(w=width, mv=max_val):
            qa = ql.qint(mv, width=w)
            qa += 1
            return 0  # 65535 + 1 = 65536 mod 65536 = 0

        actual, expected = verify_circuit(circuit_overflow, width)
        assert actual == expected, f"Width 16 overflow: expected {expected}, got {actual}"

    def test_width_17_uses_dynamic(self, verify_circuit):
        """Width 17 should fall back to dynamic generation."""

        def circuit_builder():
            qa = ql.qint(1, width=17)
            qa += 1  # CQ_add in-place to avoid 3*17=51 qubit issue
            return 2

        actual, expected = verify_circuit(circuit_builder, 17)
        assert actual == expected, f"Width 17 dynamic: expected {expected}, got {actual}"

    @pytest.mark.parametrize("width", range(1, 17))
    def test_zero_plus_zero(self, verify_circuit, width):
        """Addition identity: 0 + 0 = 0 for all hardcoded widths.

        Uses CQ_add (in-place) for widths 10-16 to stay within qubit budget.
        """
        if width <= 9:
            # Out-of-place QQ_add feasible (3*9=27 qubits)
            def circuit_builder(w=width):
                qa = ql.qint(0, width=w)
                qb = ql.qint(0, width=w)
                _r = qa + qb
                return 0

            actual, expected = verify_circuit(circuit_builder, width)
        else:
            # In-place CQ_add for large widths
            def circuit_builder(w=width):
                qa = ql.qint(0, width=w)
                qa += 0
                return 0

            actual, expected = verify_circuit(circuit_builder, width)

        assert actual == expected, f"Width {width} identity: expected {expected}, got {actual}"

    @pytest.mark.parametrize("width", range(1, 17))
    def test_overflow_wrapping(self, verify_circuit, width):
        """Max value + 1 wraps to 0 for all hardcoded widths.

        Uses CQ_add (in-place) for widths 10-16 to stay within qubit budget.
        """
        max_val = (1 << width) - 1

        if width <= 9:
            # Out-of-place QQ_add feasible (3*9=27 qubits)
            def circuit_builder(w=width, mv=max_val):
                qa = ql.qint(mv, width=w)
                qb = ql.qint(1, width=w)
                _r = qa + qb
                return 0  # max + 1 wraps to 0

            actual, expected = verify_circuit(circuit_builder, width)
        else:
            # In-place CQ_add for large widths
            def circuit_builder(w=width, mv=max_val):
                qa = ql.qint(mv, width=w)
                qa += 1
                return 0  # max + 1 wraps to 0

            actual, expected = verify_circuit(circuit_builder, width)

        assert actual == expected, f"Width {width} overflow: expected {expected}, got {actual}"


def _simulate_controlled_cq_add(width, init_val, add_val, ctrl_val):
    """Simulate controlled CQ_add and extract qa register value.

    The controlled CQ_add circuit has N+1 qubits: q[0..N-1] for qa, q[N] for ctrl.
    In Qiskit's big-endian bitstring, the first char is the highest qubit (ctrl),
    followed by qa bits. We skip the control bit to extract only the qa value.

    Returns:
        Tuple of (qa_actual, ctrl_actual) as integers.
    """
    gc.collect()
    ql.circuit()
    qa = ql.qint(init_val, width=width)
    ctrl = ql.qint(ctrl_val, width=1)
    with ctrl:
        qa += add_val
    qasm_str = ql.to_openqasm()

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector")
    job = simulator.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    # First char = ctrl qubit (highest index), remaining = qa register
    ctrl_actual = int(bitstring[0], 2)
    qa_actual = int(bitstring[1:], 2)
    return qa_actual, ctrl_actual


@pytest.mark.hardcoded_validation
class TestHardcodedControlledVariants:
    """Test controlled addition variants (cCQ_add path).

    Controlled CQ addition (qa += b inside `with ctrl:`) internally uses
    the cQQ_add-style circuit. Testing this for all widths 1-16 indirectly
    validates the cQQ_add hardcoded sequences.

    Uses N+1 qubits (N for target + 1 for control), feasible for all widths 1-16.

    NOTE: These tests use custom simulation instead of verify_circuit because
    the control qubit changes the bitstring layout (ctrl bit is at highest index,
    which is the first char in Qiskit's big-endian bitstring format).
    """

    @pytest.mark.parametrize("width", range(1, 17))
    def test_controlled_cq_add_correctness_control_on(self, width):
        """Controlled CQ_add with control=|1> performs addition."""
        expected = 2 % (1 << width)
        qa_actual, ctrl_actual = _simulate_controlled_cq_add(width, 1, 1, 1)
        assert ctrl_actual == 1, f"Control qubit should remain |1>, got {ctrl_actual}"
        assert qa_actual == expected, format_failure_message(
            "controlled_cq_add_on", [1, 1], width, expected, qa_actual
        )

    @pytest.mark.parametrize("width", range(1, 17))
    def test_controlled_cq_add_correctness_control_off(self, width):
        """Controlled CQ_add with control=|0> does NOT perform addition."""
        expected = 1  # Unchanged
        qa_actual, ctrl_actual = _simulate_controlled_cq_add(width, 1, 1, 0)
        assert ctrl_actual == 0, f"Control qubit should remain |0>, got {ctrl_actual}"
        assert qa_actual == expected, format_failure_message(
            "controlled_cq_add_off", [1, 1], width, expected, qa_actual
        )

    @pytest.mark.parametrize("width", range(1, 17))
    def test_controlled_cq_add_boundary_values(self, width):
        """Controlled CQ_add with boundary values (overflow wrapping)."""
        max_val = (1 << width) - 1
        expected = 0  # max + 1 wraps to 0
        qa_actual, ctrl_actual = _simulate_controlled_cq_add(width, max_val, 1, 1)
        assert ctrl_actual == 1, f"Control qubit should remain |1>, got {ctrl_actual}"
        assert qa_actual == expected, format_failure_message(
            "controlled_cq_add_overflow", [max_val, 1], width, expected, qa_actual
        )
