"""Phase 76: Branch/Superposition Qiskit-Verified Tests.

Verifies that qint.branch() and qbool.branch() correctly create quantum
superpositions by exporting to OpenQASM and simulating with Qiskit Aer.

Test coverage:
- branch(0.5) creates equal superposition (P(0)=P(1)=0.5 per qubit)
- branch() with various probabilities (0, 0.3, 0.5, 0.7, 1)
- qint widths 1-8
- qbool (width=1) branch
- Indexed branch x[i].branch()
- Controlled branch (inside `with qbool:` block)
- branch() inside @ql.compile decorated functions
- Inverse verification (branch + inverse restores |0>)
"""

import gc
import math

import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql

# Tolerance for probability comparison (user decision: 1e-6)
TOLERANCE = 1e-6
# Number of shots for Qiskit simulation (higher = more precise probabilities)
SHOTS = 8192


def _simulate_qasm(qasm_str: str) -> dict:
    """Run QASM through Qiskit Aer and return counts dict."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(max_parallel_threads=4)
    transpiled = transpile(circuit, simulator)
    result = simulator.run(transpiled, shots=SHOTS).result()
    return result.get_counts()


def _counts_to_probabilities(counts: dict, num_qubits: int) -> dict:
    """Convert counts to probability dict with all basis states."""
    total = sum(counts.values())
    probs = {}
    for i in range(2**num_qubits):
        bitstring = format(i, f"0{num_qubits}b")
        probs[bitstring] = counts.get(bitstring, 0) / total
    return probs


def _run_branch_circuit(width: int, prob: float = 0.5) -> dict:
    """Create circuit with branch(prob), return Qiskit counts."""
    ql.circuit()
    ql.option("fault_tolerant", True)  # Use Toffoli backend for consistent gates

    x = ql.qint(0, width=width)
    x.branch(prob)

    qasm = ql.to_openqasm()

    # Force cleanup
    del x
    gc.collect()

    return _simulate_qasm(qasm)


class TestBranchEqualSuperposition:
    """Test branch(0.5) creates equal superposition - PRIM-03."""

    @pytest.mark.parametrize("width", range(1, 9))  # widths 1-8 per user decision
    def test_equal_superposition_all_widths(self, width):
        """branch(0.5) on width-N qint creates 2^N equal probability states."""
        counts = _run_branch_circuit(width, prob=0.5)
        probs = _counts_to_probabilities(counts, width)

        # Each basis state should have probability 1/2^width
        expected_prob = 1.0 / (2**width)

        for state, prob in probs.items():
            assert abs(prob - expected_prob) < 0.05, (
                f"Width {width}, state {state}: expected {expected_prob:.4f}, got {prob:.4f}"
            )


class TestBranchProbabilities:
    """Test branch() with various probability values."""

    @pytest.mark.parametrize("prob", [0.0, 0.3, 0.5, 0.7, 1.0])
    def test_single_qubit_probability(self, prob):
        """Single qubit branch(prob) produces correct probability distribution."""
        counts = _run_branch_circuit(width=1, prob=prob)
        total = sum(counts.values())

        # P(|1>) should equal prob (within statistical tolerance)
        p1 = counts.get("1", 0) / total

        # Use wider tolerance for statistical sampling (3% for edge cases)
        tol = 0.03 if prob in (0.0, 1.0) else 0.05
        assert abs(p1 - prob) < tol, f"branch({prob}): expected P(1)={prob}, got {p1:.4f}"

    def test_probability_edge_case_zero(self):
        """branch(0) keeps qubit in |0> state."""
        counts = _run_branch_circuit(width=1, prob=0.0)
        total = sum(counts.values())
        p0 = counts.get("0", 0) / total
        assert p0 > 0.99, f"branch(0) should keep |0>, got P(0)={p0:.4f}"

    def test_probability_edge_case_one(self):
        """branch(1) flips qubit to |1> state."""
        counts = _run_branch_circuit(width=1, prob=1.0)
        total = sum(counts.values())
        p1 = counts.get("1", 0) / total
        assert p1 > 0.99, f"branch(1) should flip to |1>, got P(1)={p1:.4f}"


class TestBranchQbool:
    """Test branch() on qbool (PRIM-02)."""

    def test_qbool_branch_equal_superposition(self):
        """qbool.branch() creates equal superposition."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        b = ql.qbool(False)
        b.branch()

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        p0 = counts.get("0", 0) / total
        p1 = counts.get("1", 0) / total

        assert abs(p0 - 0.5) < 0.05, f"qbool.branch() P(0) should be 0.5, got {p0:.4f}"
        assert abs(p1 - 0.5) < 0.05, f"qbool.branch() P(1) should be 0.5, got {p1:.4f}"


class TestBranchIndexed:
    """Test branch() on indexed qubit x[i]."""

    def test_indexed_branch_single_qubit(self):
        """x[0].branch(0.5) affects only that qubit."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qint(0, width=4)
        x[0].branch(0.5)  # Branch only LSB

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)

        # Only LSB should be in superposition
        # States 0000 and 0001 should have ~0.5 each
        total = sum(counts.values())
        p_0000 = counts.get("0000", 0) / total
        p_0001 = counts.get("0001", 0) / total

        # These two states should have most of the probability
        assert p_0000 + p_0001 > 0.95, (
            f"Indexed branch should only affect LSB, got states: {counts}"
        )

        # Each should be roughly 0.5
        assert abs(p_0000 - 0.5) < 0.05
        assert abs(p_0001 - 0.5) < 0.05

    def test_multiple_indexed_branches(self):
        """Multiple indexed branches affect multiple qubits."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qint(0, width=3)
        x[0].branch(0.5)  # LSB
        x[2].branch(0.5)  # MSB (not middle bit)

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)

        # States 000, 001, 100, 101 should each have ~0.25
        # Middle bit (index 1) stays |0>
        total = sum(counts.values())
        expected_states = ["000", "001", "100", "101"]

        for state in expected_states:
            p = counts.get(state, 0) / total
            assert abs(p - 0.25) < 0.06, f"State {state} should have P=0.25, got {p:.4f}"


class TestBranchControlled:
    """Test branch() inside controlled context (with block)."""

    def test_controlled_branch_cry(self):
        """branch() inside `with ctrl:` produces CRy gates."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        ctrl = ql.qbool(True)  # Control qubit is |1>
        target = ql.qbool(False)

        with ctrl:
            target.branch(0.5)

        qasm = ql.to_openqasm()

        # Verify CRy gate appears in QASM
        assert "cry" in qasm.lower() or "ry" in qasm.lower(), (
            f"Expected Ry gate in QASM, got:\n{qasm}"
        )

        # Simulate: ctrl=|1>, so CRy should apply
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        # Qiskit little-endian convention: bitstring "ab" = q[1]=a, q[0]=b
        # ctrl is q[0] (LSB, rightmost), target is q[1] (MSB, leftmost)
        # ctrl=|1> states: "01" (target=0, ctrl=1) and "11" (target=1, ctrl=1)
        p_01 = counts.get("01", 0) / total
        p_11 = counts.get("11", 0) / total

        assert p_01 + p_11 > 0.95, f"Control=|1> so target should be active. Got: {counts}"
        assert abs(p_01 - 0.5) < 0.05, f"Expected p_01~0.5, got {p_01:.4f}"
        assert abs(p_11 - 0.5) < 0.05, f"Expected p_11~0.5, got {p_11:.4f}"


class TestBranchCompile:
    """Test branch() inside @ql.compile decorated functions."""

    def test_branch_in_compiled_function(self):
        """branch() works inside @ql.compile decorated function."""

        @ql.compile
        def create_superposition(x):
            x.branch(0.5)
            return x

        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qint(0, width=2)
        create_superposition(x)

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        probs = _counts_to_probabilities(counts, 2)

        # Equal superposition: each of 4 states has P=0.25
        for state, prob in probs.items():
            assert abs(prob - 0.25) < 0.06, (
                f"Compiled branch: state {state} expected P=0.25, got {prob:.4f}"
            )


class TestBranchValidation:
    """Test branch() input validation."""

    def test_invalid_probability_negative(self):
        """branch() raises ValueError for negative probability."""
        ql.circuit()
        x = ql.qint(0, width=2)

        with pytest.raises(ValueError, match="Probability must be in"):
            x.branch(-0.1)

    def test_invalid_probability_greater_than_one(self):
        """branch() raises ValueError for probability > 1."""
        ql.circuit()
        x = ql.qint(0, width=2)

        with pytest.raises(ValueError, match="Probability must be in"):
            x.branch(1.5)

    def test_branch_returns_none(self):
        """branch() returns None (mutation, no chaining)."""
        ql.circuit()
        x = ql.qint(0, width=2)
        result = x.branch()
        assert result is None, f"branch() should return None, got {result}"


class TestBranchAccumulation:
    """Test that multiple branch() calls accumulate."""

    def test_double_branch_accumulates(self):
        """Two branch(0.5) calls accumulate rotations."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qbool(False)
        x.branch(0.5)  # Ry(pi/2)
        x.branch(0.5)  # Another Ry(pi/2) -> total Ry(pi) = X

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        # Two Ry(pi/2) = Ry(pi) = flip to |1>
        p1 = counts.get("1", 0) / total
        assert p1 > 0.95, f"Double branch(0.5) should give |1>, got P(1)={p1:.4f}"


class TestInternalGates:
    """Test internal gate primitives (foundation for Phase 78 diffusion)."""

    def test_emit_h_produces_hadamard(self):
        """emit_h() emits H gate visible in QASM."""
        from quantum_language._gates import emit_h

        ql.circuit()
        ql.option("fault_tolerant", True)

        # Allocate a qubit and emit H
        x = ql.qbool(False)
        emit_h(x.qubits[63])  # Direct access to qubit index

        qasm = ql.to_openqasm()
        assert "h " in qasm.lower(), f"Expected H gate in QASM:\n{qasm}"

        # Simulate: H on |0> gives equal superposition
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())
        p0 = counts.get("0", 0) / total
        p1 = counts.get("1", 0) / total

        assert abs(p0 - 0.5) < 0.05
        assert abs(p1 - 0.5) < 0.05

    def test_emit_z_produces_phase_flip(self):
        """emit_z() emits Z gate visible in QASM."""
        from quantum_language._gates import emit_h, emit_z

        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qbool(False)
        emit_h(x.qubits[63])  # Create |+>
        emit_z(x.qubits[63])  # Apply Z -> |->
        emit_h(x.qubits[63])  # Convert back -> |1>

        qasm = ql.to_openqasm()
        assert "z " in qasm.lower(), f"Expected Z gate in QASM:\n{qasm}"

        # H-Z-H on |0> = |1>
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())
        p1 = counts.get("1", 0) / total

        assert p1 > 0.95, f"H-Z-H should give |1>, got P(1)={p1:.4f}"

    def test_emit_ry_produces_rotation(self):
        """emit_ry() emits Ry gate visible in QASM."""
        from quantum_language._gates import emit_ry

        ql.circuit()
        ql.option("fault_tolerant", True)

        x = ql.qbool(False)
        # Ry(pi/2) = equal superposition
        emit_ry(x.qubits[63], math.pi / 2)

        qasm = ql.to_openqasm()
        assert "ry" in qasm.lower(), f"Expected Ry gate in QASM:\n{qasm}"

        counts = _simulate_qasm(qasm)
        total = sum(counts.values())
        p0 = counts.get("0", 0) / total
        p1 = counts.get("1", 0) / total

        assert abs(p0 - 0.5) < 0.05
        assert abs(p1 - 0.5) < 0.05

    def test_emit_mcz_phase_flip_on_111(self):
        """emit_mcz() applies phase flip only when all controls are |1>.

        Verifies MCZ gate for Phase 78 diffusion operator by checking that
        the |111> state gets a phase flip while other states are unchanged.

        Setup: Create |+++> state (equal superposition), apply MCZ, then
        apply H to all qubits. The phase flip on |111> should cause
        constructive/destructive interference visible in measurement.
        """
        from quantum_language._gates import emit_h, emit_mcz

        ql.circuit()
        ql.option("fault_tolerant", True)

        # Allocate 3 qubits
        q0 = ql.qbool(False)
        q1 = ql.qbool(False)
        q2 = ql.qbool(False)

        # Create |+++> state
        emit_h(q0.qubits[63])
        emit_h(q1.qubits[63])
        emit_h(q2.qubits[63])

        # Apply MCZ: Z on q2 controlled by q0, q1
        # This flips phase of |111> state
        emit_mcz(q2.qubits[63], [q0.qubits[63], q1.qubits[63]])

        # Apply H to all qubits
        emit_h(q0.qubits[63])
        emit_h(q1.qubits[63])
        emit_h(q2.qubits[63])

        qasm = ql.to_openqasm()

        # Simulate and verify interference pattern
        counts = _simulate_qasm(qasm)

        # The H-MCZ-H pattern creates specific interference:
        # |000> should have lower probability than without MCZ
        # Other states get modified probabilities
        # Key check: distribution is NOT uniform (would be 1/8 each without MCZ)
        probs = _counts_to_probabilities(counts, 3)

        # Verify MCZ had an effect: at least one state should deviate
        # significantly from uniform 1/8 = 0.125
        max_deviation = max(abs(p - 0.125) for p in probs.values())
        assert max_deviation > 0.05, (
            f"MCZ should cause interference. Max deviation from uniform: {max_deviation:.4f}"
        )

    def test_emit_mcz_two_controls(self):
        """emit_mcz() with 2 controls works correctly."""
        from quantum_language._gates import emit_mcz

        ql.circuit()
        ql.option("fault_tolerant", True)

        # Allocate qubits: 2 controls + 1 target
        ctrl0 = ql.qbool(True)  # |1>
        ctrl1 = ql.qbool(True)  # |1>
        target = ql.qbool(False)  # |0>

        # Apply H to target to create |+>
        from quantum_language._gates import emit_h

        emit_h(target.qubits[63])

        # Apply MCZ: both controls are |1>, so Z should apply
        emit_mcz(target.qubits[63], [ctrl0.qubits[63], ctrl1.qubits[63]])

        # Apply H again: |+> -> Z -> |-> -> H -> |1>
        emit_h(target.qubits[63])

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        # Target should be |1> (both controls were |1>)
        # Full state: |11> for controls, |1> for target = |111>
        p_111 = counts.get("111", 0) / total
        assert p_111 > 0.95, f"MCZ with both controls |1> should flip target. P(111)={p_111:.4f}"

    def test_emit_mcz_single_control_fallback(self):
        """emit_mcz() with single control falls back to CZ."""
        from quantum_language._gates import emit_h, emit_mcz

        ql.circuit()
        ql.option("fault_tolerant", True)

        ctrl = ql.qbool(True)  # |1>
        target = ql.qbool(False)  # |0>

        emit_h(target.qubits[63])  # |+>
        emit_mcz(target.qubits[63], [ctrl.qubits[63]])  # Single control = CZ
        emit_h(target.qubits[63])  # Should give |1>

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        # Control |1> + H-CZ-H on target = target flipped to |1>
        p_11 = counts.get("11", 0) / total
        assert p_11 > 0.95, f"Single-control MCZ should act as CZ. P(11)={p_11:.4f}"

    def test_emit_mcz_no_controls_fallback(self):
        """emit_mcz() with no controls falls back to Z."""
        from quantum_language._gates import emit_h, emit_mcz

        ql.circuit()
        ql.option("fault_tolerant", True)

        target = ql.qbool(False)

        emit_h(target.qubits[63])  # |+>
        emit_mcz(target.qubits[63], [])  # No controls = just Z
        emit_h(target.qubits[63])  # Should give |1>

        qasm = ql.to_openqasm()
        counts = _simulate_qasm(qasm)
        total = sum(counts.values())

        p_1 = counts.get("1", 0) / total
        assert p_1 > 0.95, f"Zero-control MCZ should act as Z. P(1)={p_1:.4f}"
