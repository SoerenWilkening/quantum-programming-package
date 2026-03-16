"""Tests for walk_branching: branch_to_children and unbranch.

Verifies that conditional Montanaro rotations based on count value
produce the correct superposition over valid move indices, with the
correct parent amplitude.  All tests stay within the 17-qubit limit.

Requirements from acceptance criteria:
- Uniform superposition over valid moves
- Parent amplitude = 1/sqrt(d+1)
- Invalid moves get zero amplitude
- unbranch restores original state
"""

import gc
import math

import numpy as np
import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig, branch_width, count_width
from quantum_language.walk_branching import (
    BranchState,
    branch_to_children,
    unbranch,
    _plan_cascade_ops,
    _precompute_angle_data,
)


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _get_statevector(qasm_str):
    """Simulate QASM and return the full statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    simulator = AerSimulator(method="statevector")
    circuit.save_statevector()
    job = simulator.run(circuit, shots=1)
    result = job.result()
    sv = result.get_statevector()
    return np.asarray(sv)


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
    result_bits = bitstring[msb_pos: lsb_pos + 1]
    return int(result_bits, 2)


def _extract_register_probs(sv, num_qubits, reg_start, reg_width):
    """Sum statevector probabilities by register value.

    Returns a dict mapping register value -> probability.
    """
    probs = {}
    for idx, amp in enumerate(sv):
        p = abs(amp) ** 2
        if p < 1e-15:
            continue
        val = (idx >> reg_start) & ((1 << reg_width) - 1)
        probs[val] = probs.get(val, 0.0) + p
    return probs


def _extract_joint_probs(sv, num_qubits, reg1_start, reg1_width,
                         reg2_start, reg2_width):
    """Sum statevector probabilities by joint register values.

    Returns a dict mapping (reg1_val, reg2_val) -> probability.
    """
    probs = {}
    for idx, amp in enumerate(sv):
        p = abs(amp) ** 2
        if p < 1e-15:
            continue
        val1 = (idx >> reg1_start) & ((1 << reg1_width) - 1)
        val2 = (idx >> reg2_start) & ((1 << reg2_width) - 1)
        key = (val1, val2)
        probs[key] = probs.get(key, 0.0) + p
    return probs


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()
    ql.option('simulate', True)


# ---------------------------------------------------------------------------
# Group 1: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Argument validation for branch_to_children and unbranch."""

    def test_rejects_non_walkconfig(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            branch_to_children("not a config", None, None)

    def test_rejects_none_count_reg(self):
        cfg = WalkConfig(max_depth=1, num_moves=2)
        with pytest.raises(ValueError, match="count_reg must not be None"):
            branch_to_children(cfg, None, "dummy")

    def test_rejects_none_branch_reg(self):
        cfg = WalkConfig(max_depth=1, num_moves=2)
        with pytest.raises(ValueError, match="branch_reg must not be None"):
            branch_to_children(cfg, "dummy", None)

    def test_unbranch_rejects_non_walkconfig(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            unbranch(42, None, None)

    def test_unbranch_rejects_none_count_reg(self):
        cfg = WalkConfig(max_depth=1, num_moves=2)
        with pytest.raises(ValueError, match="count_reg must not be None"):
            unbranch(cfg, None, "dummy")

    def test_unbranch_rejects_none_branch_reg(self):
        cfg = WalkConfig(max_depth=1, num_moves=2)
        with pytest.raises(ValueError, match="branch_reg must not be None"):
            unbranch(cfg, "dummy", None)

    def test_unbranch_rejects_none_branch_state(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=1, num_moves=2)
        count_reg = ql.qint(1, width=count_width(2))
        branch_reg = ql.qint(0, width=branch_width(2))
        with pytest.raises(ValueError, match="branch_state must not be None"):
            unbranch(cfg, count_reg, branch_reg, branch_state=None)


# ---------------------------------------------------------------------------
# Group 2: Cascade Planning (Pure Unit Tests)
# ---------------------------------------------------------------------------


class TestCascadePlanning:
    """Test _plan_cascade_ops for correct operation sequences and angles."""

    def test_d1_empty(self):
        """d=1: no cascade needed (single child)."""
        assert _plan_cascade_ops(1, 1) == []

    def test_d2_single_ry_correct_angle(self):
        """d=2: single Ry with theta = pi/2 (equal split of 2 states)."""
        ops = _plan_cascade_ops(2, 1)
        assert len(ops) == 1
        assert ops[0][0] == "ry"
        assert ops[0][1] == 0  # bit_offset = 0
        # sin^2(theta/2) = 1/2, so theta = 2*arcsin(sqrt(1/2)) = pi/2
        expected_angle = math.pi / 2
        assert math.isclose(ops[0][2], expected_angle, rel_tol=1e-12), (
            f"d=2 cascade angle: expected {expected_angle}, got {ops[0][2]}"
        )

    def test_d3_correct_first_angle(self):
        """d=3 with w=2: first op is Ry with theta = 2*arcsin(sqrt(1/3))."""
        ops = _plan_cascade_ops(3, 2)
        assert len(ops) > 0
        assert ops[0][0] == "ry"
        # d=3: left=2, right=1. theta = 2*arcsin(sqrt(1/3))
        expected_angle = 2.0 * math.asin(math.sqrt(1.0 / 3.0))
        assert math.isclose(ops[0][2], expected_angle, rel_tol=1e-12), (
            f"d=3 first cascade angle: expected {expected_angle}, got {ops[0][2]}"
        )

    def test_d4_correct_first_angle(self):
        """d=4 with w=2: first op is Ry splitting into 2+2."""
        ops = _plan_cascade_ops(4, 2)
        assert len(ops) > 0
        assert ops[0][0] == "ry"
        # d=4: left=2, right=2. theta = 2*arcsin(sqrt(2/4)) = pi/2
        expected_angle = math.pi / 2
        assert math.isclose(ops[0][2], expected_angle, rel_tol=1e-12), (
            f"d=4 first cascade angle: expected {expected_angle}, got {ops[0][2]}"
        )

    def test_d2_w2_has_ry_on_bit0(self):
        """d=2 with w=2: Ry on bit 0 (MSB), splits into 1 left + 1 right."""
        ops = _plan_cascade_ops(2, 2)
        assert ops[0][0] == "ry"
        assert ops[0][1] == 0
        assert math.isclose(ops[0][2], math.pi / 2, rel_tol=1e-12)

    def test_d3_has_four_operations(self):
        """d=3 with w=2: Ry, X, CRy, X sequence."""
        ops = _plan_cascade_ops(3, 2)
        assert len(ops) == 4
        assert ops[0][0] == "ry"   # initial split
        assert ops[1][0] == "x"    # flip for control-on-zero
        assert ops[2][0] == "cry"  # CRy for left subtree split
        assert ops[3][0] == "x"    # undo flip


# ---------------------------------------------------------------------------
# Group 3: Angle Pre-computation
# ---------------------------------------------------------------------------


class TestAnglePrecomputation:
    """Test _precompute_angle_data returns correct structure and values."""

    def test_returns_all_count_values(self):
        data = _precompute_angle_data(3, 2)
        assert 1 in data
        assert 2 in data
        assert 3 in data
        assert 0 not in data

    def test_phi_values_correct(self):
        data = _precompute_angle_data(2, 1)
        # phi(1) = 2*arctan(1) = pi/2
        assert math.isclose(data[1]["phi"], math.pi / 2, rel_tol=1e-12)
        # phi(2) = 2*arctan(sqrt(2))
        expected = 2.0 * math.atan(math.sqrt(2))
        assert math.isclose(data[2]["phi"], expected, rel_tol=1e-12)

    def test_cascade_ops_d1_empty(self):
        data = _precompute_angle_data(3, 2)
        assert data[1]["cascade_ops"] == []

    def test_cascade_ops_d2_has_correct_angle(self):
        data = _precompute_angle_data(3, 2)
        ops = data[2]["cascade_ops"]
        assert len(ops) >= 1
        assert ops[0][0] == "ry"
        assert math.isclose(ops[0][2], math.pi / 2, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# Group 4: Branching with Fixed Count -- Amplitude Verification
# ---------------------------------------------------------------------------


class TestBranchAmplitudes:
    """Verify exact amplitudes after branching with a fixed count value.

    For count=c, the Montanaro phi rotation produces:
      parent amplitude = cos(phi(c)/2) = 1/sqrt(c+1)
      children amplitude (total) = sin(phi(c)/2) = sqrt(c)/sqrt(c+1)
    The cascade then distributes children amplitude uniformly, giving
    each of c children amplitude = 1/sqrt(c+1).
    """

    def test_count1_amplitudes(self):
        """count=1: parent prob = 1/2, single child prob = 1/2.

        phi(1) = pi/2.  cos(pi/4)^2 = 1/2.  sin(pi/4)^2 = 1/2.
        Parent on parent_flag=0, child on parent_flag=1.
        Branch register stays 0 (no cascade for single child).
        """
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        parent_prob = pf_probs.get(0, 0.0)
        child_prob = pf_probs.get(1, 0.0)

        assert abs(parent_prob - 0.5) < 1e-6, (
            f"count=1: parent prob should be 0.5, got {parent_prob}"
        )
        assert abs(child_prob - 0.5) < 1e-6, (
            f"count=1: child prob should be 0.5, got {child_prob}"
        )

    def test_count2_amplitudes_binary(self):
        """count=2, binary branching: each of 3 components has prob 1/3.

        phi(2) = 2*arctan(sqrt(2)).
        cos^2(phi/2) = 1/3 (parent).
        sin^2(phi/2) = 2/3 (children total), split equally -> 1/3 each.
        """
        _init_circuit()
        cw = count_width(2) + 1  # extra bit to avoid signed overflow
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        br_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _get_statevector(qasm)

        # Parent amplitude: parent_flag=0 (regardless of branch)
        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        parent_prob = pf_probs.get(0, 0.0)
        assert abs(parent_prob - 1.0 / 3.0) < 1e-6, (
            f"count=2: parent prob should be 1/3, got {parent_prob}"
        )

        # Children: parent_flag=1, each branch value (0 and 1) gets 1/3
        joint = _extract_joint_probs(
            sv, nq, pf_start, 1, br_start, bw
        )
        child0_prob = joint.get((1, 0), 0.0)
        child1_prob = joint.get((1, 1), 0.0)
        assert abs(child0_prob - 1.0 / 3.0) < 1e-6, (
            f"count=2: child 0 prob should be 1/3, got {child0_prob}"
        )
        assert abs(child1_prob - 1.0 / 3.0) < 1e-6, (
            f"count=2: child 1 prob should be 1/3, got {child1_prob}"
        )

    def test_count3_amplitudes_ternary(self):
        """count=3, ternary branching: parent + 3 children each get 1/4.

        phi(3) = 2*arctan(sqrt(3)).
        cos^2(phi/2) = 1/4 (parent).
        sin^2(phi/2) = 3/4 (children), split equally -> 1/4 each.
        """
        _init_circuit()
        num_moves = 3
        cw = count_width(num_moves) + 1
        bw = branch_width(num_moves)
        count_reg = ql.qint(3, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=num_moves)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        br_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        parent_prob = pf_probs.get(0, 0.0)
        assert abs(parent_prob - 0.25) < 1e-6, (
            f"count=3: parent prob should be 1/4, got {parent_prob}"
        )

        joint = _extract_joint_probs(sv, nq, pf_start, 1, br_start, bw)
        for i in range(3):
            child_prob = joint.get((1, i), 0.0)
            assert abs(child_prob - 0.25) < 1e-6, (
                f"count=3: child {i} prob should be 1/4, got {child_prob}"
            )

        # Invalid move index 3 should have zero amplitude
        invalid_prob = joint.get((1, 3), 0.0)
        assert invalid_prob < 1e-6, (
            f"count=3: invalid branch=3 should have zero prob, got {invalid_prob}"
        )

    def test_count1_parent_amplitude_matches_formula(self):
        """Verify parent amplitude = 1/sqrt(d+1) for d=1."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        parent_prob = pf_probs.get(0, 0.0)
        expected = 1.0 / (1 + 1)  # 1/sqrt(d+1)^2 = 1/(d+1) for d=1
        assert abs(parent_prob - expected) < 1e-6, (
            f"Parent prob should be {expected}, got {parent_prob}"
        )

    def test_count0_no_branching(self):
        """count=0: no rotations, parent_flag stays |0>, branch stays |0>."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(0, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        br_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        assert abs(pf_probs.get(0, 0.0) - 1.0) < 1e-6, (
            "count=0: all amplitude should be on parent_flag=0"
        )

        br_probs = _extract_register_probs(sv, nq, br_start, bw)
        assert abs(br_probs.get(0, 0.0) - 1.0) < 1e-6, (
            "count=0: all amplitude should be on branch=0"
        )

    def test_invalid_moves_zero_amplitude(self):
        """count=1 with bw=1: only move 0 is valid, move 1 gets zero.

        With c=1, the cascade is empty, so all children amplitude
        goes to branch=0.  Joint (parent_flag=1, branch=1) = 0.
        """
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        br_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        joint = _extract_joint_probs(sv, nq, pf_start, 1, br_start, bw)
        invalid_prob = joint.get((1, 1), 0.0)
        assert invalid_prob < 1e-6, (
            f"count=1: invalid move (pf=1, branch=1) should have zero "
            f"amplitude, got prob {invalid_prob}"
        )

        valid_child_prob = joint.get((1, 0), 0.0)
        assert abs(valid_child_prob - 0.5) < 1e-6, (
            f"count=1: valid child (pf=1, branch=0) should have prob 0.5, "
            f"got {valid_child_prob}"
        )


# ---------------------------------------------------------------------------
# Group 5: Unbranch (Inverse) Tests -- Non-Trivial Verification
# ---------------------------------------------------------------------------


class TestUnbranch:
    """unbranch reverses the branching, restoring original state.

    Tests first verify branch produces a non-trivial superposition,
    then verify unbranch restores the initial state.
    """

    def test_branch_produces_superposition_then_unbranch_restores(self):
        """Two-phase: (1) branch is non-trivial, (2) branch+unbranch = I."""
        # Phase 1: branch alone
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        assert pf_probs.get(0, 0.0) > 0.1, (
            "branch should produce non-trivial parent component"
        )
        assert pf_probs.get(1, 0.0) > 0.1, (
            "branch should produce non-trivial child component"
        )

        # Phase 2: branch + unbranch
        _init_circuit()
        count_reg2 = ql.qint(1, width=cw)
        branch_reg2 = ql.qint(0, width=bw)
        cfg2 = WalkConfig(max_depth=1, num_moves=2)
        bs2 = branch_to_children(cfg2, count_reg2, branch_reg2)
        unbranch(cfg2, count_reg2, branch_reg2, branch_state=bs2)

        _keepalive2 = [count_reg2, branch_reg2, bs2]
        qasm2 = ql.to_openqasm()
        sv2 = _get_statevector(qasm2)

        max_prob = max(abs(a) ** 2 for a in sv2)
        assert max_prob > 0.99, (
            f"branch+unbranch should be identity; max prob = {max_prob}"
        )

    def test_unbranch_restores_count2(self):
        """branch + unbranch with count=2 restores all registers."""
        _init_circuit()
        cw = count_width(2) + 1
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg, branch_state=bs)

        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)

        max_prob = max(abs(a) ** 2 for a in sv)
        assert max_prob > 0.99, (
            f"branch+unbranch count=2 should be identity; max prob = {max_prob}"
        )

    def test_unbranch_restores_count3(self):
        """branch + unbranch with count=3 restores all registers."""
        _init_circuit()
        num_moves = 3
        cw = count_width(num_moves) + 1
        bw = branch_width(num_moves)
        count_reg = ql.qint(3, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=num_moves)
        bs = branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg, branch_state=bs)

        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)

        max_prob = max(abs(a) ** 2 for a in sv)
        assert max_prob > 0.99, (
            f"branch+unbranch count=3 should be identity; max prob = {max_prob}"
        )

    def test_branch_reg_zero_after_unbranch(self):
        """Measurement confirms branch_reg is |0> after unbranch."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg, branch_state=bs)

        br_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)

        extracted = _simulate_and_extract(qasm, nq, br_start, bw)
        assert extracted == 0, (
            f"branch+unbranch should restore branch_reg to 0, got {extracted}"
        )

    def test_count_reg_unchanged_after_unbranch(self):
        """count_reg value is unchanged after branch + unbranch."""
        _init_circuit()
        cw = count_width(2) + 1
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg, branch_state=bs)

        count_start = count_reg.allocated_start
        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, (
            f"count_reg should remain 2 after branch+unbranch, got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 6: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify circuits stay within the 17-qubit simulation limit."""

    def test_binary_branching_within_budget(self):
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"

    def test_ternary_branching_within_budget(self):
        _init_circuit()
        num_moves = 3
        cw = count_width(num_moves) + 1
        bw = branch_width(num_moves)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=num_moves)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"


# ---------------------------------------------------------------------------
# Group 7: Integration with Counting
# ---------------------------------------------------------------------------


class TestBranchingWithCounting:
    """Integration: count_valid_children + branch_to_children."""

    def test_count_then_branch_produces_superposition(self):
        """Count all-valid children (count=2), then branch.

        The parent_flag should be in superposition and the branch
        register should show non-trivial amplitude distribution.
        """
        from quantum_language.walk_counting import count_valid_children

        _init_circuit()
        state = ql.qint(0, width=2)
        num_moves = 2
        cw = count_width(num_moves)
        bw = branch_width(num_moves)
        count_reg = ql.qint(0, width=cw)
        branch_reg = ql.qint(0, width=bw)

        def make_move(s, i):
            s ^= (i + 1)

        def undo_move(s, i):
            s ^= (i + 1)

        def is_valid_always(s):
            return s == s

        cfg = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=make_move,
            undo_move=undo_move,
            is_valid=is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        pf_start = bs.parent_flag.allocated_start
        _keepalive = [state, count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _get_statevector(qasm)

        pf_probs = _extract_register_probs(sv, nq, pf_start, 1)
        assert pf_probs.get(0, 0.0) > 0.1, (
            "After count+branch, parent component should have non-trivial prob"
        )
        assert pf_probs.get(1, 0.0) > 0.1, (
            "After count+branch, children component should have non-trivial prob"
        )

    def test_count_then_branch_then_unbranch_restores(self):
        """count + branch + unbranch should leave branch_reg at |0>."""
        from quantum_language.walk_counting import count_valid_children

        _init_circuit()
        state = ql.qint(0, width=2)
        num_moves = 2
        cw = count_width(num_moves)
        bw = branch_width(num_moves)
        count_reg = ql.qint(0, width=cw)
        branch_reg = ql.qint(0, width=bw)

        def make_move(s, i):
            s ^= (i + 1)

        def undo_move(s, i):
            s ^= (i + 1)

        def is_valid_always(s):
            return s == s

        cfg = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=make_move,
            undo_move=undo_move,
            is_valid=is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)
        bs = branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg, branch_state=bs)

        br_start = branch_reg.allocated_start
        _keepalive = [state, count_reg, branch_reg, bs]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(qasm, nq, br_start, bw)
        assert extracted == 0, (
            f"count+branch+unbranch should restore branch_reg to 0, "
            f"got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 8: BranchState return type
# ---------------------------------------------------------------------------


class TestBranchStateReturn:
    """branch_to_children returns a BranchState object."""

    def test_returns_branch_state(self):
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)
        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg, bs]
        assert isinstance(bs, BranchState)
        assert bs.parent_flag is not None
        assert hasattr(bs.parent_flag, 'qubits')
        assert bs.parent_flag.width == 1
        assert len(bs.cond_map) == 2  # num_moves=2 -> conds for c=1,2

    def test_accepts_external_parent_flag(self):
        """Can pass in a pre-allocated parent_flag qubit."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)
        my_pf = ql.qbool()

        cfg = WalkConfig(max_depth=1, num_moves=2)
        bs = branch_to_children(
            cfg, count_reg, branch_reg, parent_flag=my_pf
        )

        _keepalive = [count_reg, branch_reg, bs]
        assert bs.parent_flag is my_pf
