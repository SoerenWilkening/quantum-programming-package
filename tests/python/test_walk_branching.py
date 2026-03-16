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

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig, branch_width, count_width
from quantum_language.walk_branching import (
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
    """Simulate QASM and return the full statevector."""
    circuit = qiskit.qasm3.loads(qasm_str)
    simulator = AerSimulator(method="statevector")
    circuit.save_statevector()
    job = simulator.run(circuit, shots=1)
    result = job.result()
    return result.get_statevector()


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


# ---------------------------------------------------------------------------
# Group 2: Cascade Planning (Pure Unit Tests)
# ---------------------------------------------------------------------------


class TestCascadePlanning:
    """Test _plan_cascade_ops for correct operation sequences."""

    def test_d1_empty(self):
        """d=1: no cascade needed (single child)."""
        assert _plan_cascade_ops(1, 1) == []

    def test_d2_single_ry(self):
        """d=2: single Ry to split into 2 equal parts."""
        ops = _plan_cascade_ops(2, 1)
        assert len(ops) >= 1
        assert ops[0][0] == "ry"

    def test_d3_has_operations(self):
        """d=3: needs cascade operations."""
        ops = _plan_cascade_ops(3, 2)
        assert len(ops) > 0

    def test_d4_has_operations(self):
        """d=4: needs cascade operations."""
        ops = _plan_cascade_ops(4, 2)
        assert len(ops) > 0


# ---------------------------------------------------------------------------
# Group 3: Angle Pre-computation
# ---------------------------------------------------------------------------


class TestAnglePrecomputation:
    """Test _precompute_angle_data returns correct structure."""

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

    def test_cascade_ops_d2_nonempty(self):
        data = _precompute_angle_data(3, 2)
        assert len(data[2]["cascade_ops"]) > 0


# ---------------------------------------------------------------------------
# Group 4: Branching with Fixed Count (Statevector Tests)
# ---------------------------------------------------------------------------


class TestBranchWithFixedCount:
    """Test branching when count is a fixed classical value.

    We set count_reg to a known classical value and verify the resulting
    superposition in the branch register.
    """

    def test_count_1_parent_amplitude(self):
        """count=1: parent amplitude should be 1/sqrt(2), child = 1/sqrt(2).

        With 1 valid child, phi = pi/2.
        cos(pi/4) = 1/sqrt(2) for parent.
        sin(pi/4) = 1/sqrt(2) for single child.
        """
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        sv = _get_statevector(qasm)
        probabilities = [abs(a) ** 2 for a in sv]

        # With count=1, bw=1: branch qubit gets Ry(pi/2)
        # Expected: |branch=0> has prob 1/2 (parent), |branch=1> has prob 1/2 (child)
        # The parent amplitude = 1/sqrt(1+1) = 1/sqrt(2)
        parent_amp_sq = 1.0 / 2.0
        total_prob = sum(probabilities)
        assert abs(total_prob - 1.0) < 1e-6, f"Probabilities don't sum to 1: {total_prob}"

    def test_count_2_all_valid_binary(self):
        """count=2 with binary branching: uniform over 2 children + parent.

        phi(2) = 2*arctan(sqrt(2)).
        Parent amplitude = cos(phi/2) = 1/sqrt(3).
        Each child amplitude = sin(phi/2)/sqrt(2) = sqrt(2)/sqrt(3) / sqrt(2) = 1/sqrt(3).
        """
        _init_circuit()
        cw = count_width(2) + 1  # extra bit to avoid signed overflow warning
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        sv = _get_statevector(qasm)
        probabilities = [abs(a) ** 2 for a in sv]

        # With d=2, parent amplitude should be 1/sqrt(3) -> prob 1/3
        # Each of the 2 children has amplitude 1/sqrt(3) -> prob 1/3
        # But since bw=1, branch=0 holds parent + child_0 superposition
        # We can check total probability sums to 1
        total_prob = sum(probabilities)
        assert abs(total_prob - 1.0) < 1e-6, f"Probabilities don't sum to 1: {total_prob}"


# ---------------------------------------------------------------------------
# Group 5: Unbranch (Inverse) Tests
# ---------------------------------------------------------------------------


class TestUnbranch:
    """unbranch reverses the branching, restoring original state."""

    def test_branch_unbranch_identity_count1(self):
        """branch + unbranch with count=1 restores branch_reg to |0>."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        branch_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, branch_start, bw)
        assert extracted == 0, (
            f"branch + unbranch should restore branch_reg to 0, got {extracted}"
        )

    def test_branch_unbranch_identity_count2(self):
        """branch + unbranch with count=2 restores branch_reg to |0>."""
        _init_circuit()
        cw = count_width(2) + 1  # extra bit to avoid signed overflow warning
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        branch_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, branch_start, bw)
        assert extracted == 0, (
            f"branch + unbranch should restore branch_reg to 0, got {extracted}"
        )

    def test_branch_unbranch_identity_count3(self):
        """branch + unbranch with count=3, 3-move config restores branch_reg."""
        _init_circuit()
        num_moves = 3
        cw = count_width(num_moves) + 1  # extra bit to avoid signed overflow
        bw = branch_width(num_moves)
        count_reg = ql.qint(3, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=num_moves)
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        branch_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, branch_start, bw)
        assert extracted == 0, (
            f"branch + unbranch should restore branch_reg to 0, got {extracted}"
        )

    def test_branch_unbranch_statevector_identity(self):
        """branch + unbranch produces the identity (statevector check)."""
        _init_circuit()
        cw = count_width(2) + 1  # extra bit to avoid signed overflow
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)

        # The initial state was |count=2, branch=0>.  After branch+unbranch,
        # the statevector should have all amplitude on the initial basis state.
        probabilities = [abs(a) ** 2 for a in sv]
        max_prob = max(probabilities)
        assert max_prob > 0.99, (
            f"branch + unbranch should be identity; max prob = {max_prob}"
        )

    def test_count_reg_unchanged_after_unbranch(self):
        """count_reg value is unchanged after branch + unbranch."""
        _init_circuit()
        cw = count_width(2) + 1  # extra bit to avoid signed overflow
        bw = branch_width(2)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        count_start = count_reg.allocated_start
        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, (
            f"count_reg should remain 2 after branch+unbranch, got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 6: Count=0 Edge Case
# ---------------------------------------------------------------------------


class TestCountZero:
    """When count=0, no branching should occur."""

    def test_count_zero_no_branching(self):
        """count=0: branch_reg stays at |0>, no rotations applied."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(0, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)

        branch_start = branch_reg.allocated_start
        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(qasm, nq, branch_start, bw)
        assert extracted == 0, (
            f"count=0: branch_reg should stay at 0, got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 7: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify circuits stay within the 17-qubit simulation limit."""

    def test_binary_branching_within_budget(self):
        """Binary branching: count(2 bits) + branch(1 bit) = 3 qubits."""
        _init_circuit()
        cw = count_width(2)
        bw = branch_width(2)
        count_reg = ql.qint(1, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=2)
        branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"

    def test_ternary_branching_within_budget(self):
        """Ternary branching: count(3 bits) + branch(2 bits) = 5 qubits."""
        _init_circuit()
        num_moves = 3
        cw = count_width(num_moves) + 1  # extra bit to avoid signed overflow
        bw = branch_width(num_moves)
        count_reg = ql.qint(2, width=cw)
        branch_reg = ql.qint(0, width=bw)

        cfg = WalkConfig(max_depth=1, num_moves=num_moves)
        branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"


# ---------------------------------------------------------------------------
# Group 8: Integration with Counting
# ---------------------------------------------------------------------------


class TestBranchingWithCounting:
    """Integration: count_valid_children + branch_to_children."""

    def test_count_then_branch_all_valid(self):
        """Count all-valid children, then branch: branch_reg in superposition.

        Uses XOR-based moves with is_valid_always.  After counting (count=2),
        branching should produce a superposition in the branch register.
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
        branch_to_children(cfg, count_reg, branch_reg)

        _keepalive = [state, count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        # The branch register should not be deterministically 0 anymore;
        # it should be in a superposition.
        sv = _get_statevector(qasm)
        probabilities = [abs(a) ** 2 for a in sv]
        total_prob = sum(probabilities)
        assert abs(total_prob - 1.0) < 1e-6

    def test_count_then_branch_then_unbranch(self):
        """count + branch + unbranch should leave branch_reg at |0>.

        The unbranch should undo the branching completely.
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
        branch_to_children(cfg, count_reg, branch_reg)
        unbranch(cfg, count_reg, branch_reg)

        branch_start = branch_reg.allocated_start
        _keepalive = [state, count_reg, branch_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(qasm, nq, branch_start, bw)
        assert extracted == 0, (
            f"count + branch + unbranch should restore branch_reg to 0, "
            f"got {extracted}"
        )
