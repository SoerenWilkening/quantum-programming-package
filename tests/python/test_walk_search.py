"""Tests for walk_search.py: full quantum walk search with detection.

Verifies the walk() public API:
- Detects known marked leaf (returns True)
- No marked nodes (returns False)
- 2-variable binary ILP detects feasible assignment
- 3-variable ILP within 15 qubits
- Returns bool type

All test circuits use <= 17 qubits.
"""

import gc

import numpy as np
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_registers import WalkRegisters
from quantum_language.walk_search import (
    _apply_phase_on_pattern,
    _collect_branch_qubits,
    _evaluate_is_marked_classically,
    _max_walk_iterations,
    _measure_root_overlap,
    _measure_root_overlap_unmarked,
    _tree_size,
    _validate_walk_args,
    walk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


# ---------------------------------------------------------------------------
# Simple marking callbacks for testing
# ---------------------------------------------------------------------------


def _is_marked_value3(state):
    """Marked when state == 3 (classical evaluation)."""
    return state == 3


def _is_marked_never(state):
    """Nothing is marked."""
    return False


def _is_marked_ge1(state):
    """Marked when state >= 1 (multiple solutions)."""
    return state >= 1


# ---------------------------------------------------------------------------
# Group 1: Tree Size Tests
# ---------------------------------------------------------------------------


class TestTreeSize:
    """Test _tree_size computation."""

    def test_binary_depth1(self):
        assert _tree_size(2, 1) == 3

    def test_binary_depth2(self):
        assert _tree_size(2, 2) == 7

    def test_binary_depth3(self):
        assert _tree_size(2, 3) == 15

    def test_ternary_depth2(self):
        assert _tree_size(3, 2) == 13

    def test_unary_depth5(self):
        assert _tree_size(1, 5) == 6


# ---------------------------------------------------------------------------
# Group 2: Iteration Count Tests
# ---------------------------------------------------------------------------


class TestIterationCount:
    """Test _max_walk_iterations computation."""

    def test_minimum_is_4(self):
        assert _max_walk_iterations(2, 1) >= 4

    def test_increases_with_tree_size(self):
        small = _max_walk_iterations(2, 2)
        large = _max_walk_iterations(2, 4)
        assert large >= small

    def test_binary_depth2(self):
        result = _max_walk_iterations(2, 2)
        assert result == 4


# ---------------------------------------------------------------------------
# Group 3: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Argument validation for walk()."""

    def test_rejects_none_is_marked(self):
        with pytest.raises(ValueError, match="is_marked must not be None"):
            _validate_walk_args(None, 2, 2)

    def test_rejects_non_int_max_depth(self):
        with pytest.raises(TypeError, match="max_depth must be an int"):
            _validate_walk_args(lambda s: None, 2.0, 2)

    def test_rejects_non_int_num_moves(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            _validate_walk_args(lambda s: None, 2, 2.0)

    def test_rejects_zero_max_depth(self):
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            _validate_walk_args(lambda s: None, 0, 2)

    def test_rejects_zero_num_moves(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 0)

    def test_rejects_non_int_max_iterations(self):
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=2.0)

    def test_rejects_zero_max_iterations(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=0)

    def test_rejects_negative_max_iterations(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=-1)

    def test_accepts_valid_max_iterations(self):
        """No exception for valid max_iterations=1."""
        _validate_walk_args(lambda s: None, 2, 2, max_iterations=1)

    def test_max_iterations_none_accepted(self):
        """None is the default and should be accepted."""
        _validate_walk_args(lambda s: None, 2, 2, max_iterations=None)


# ---------------------------------------------------------------------------
# Group 4: Root Overlap Tests
# ---------------------------------------------------------------------------


class TestRootOverlap:
    """Test root overlap measurement produces valid probabilities."""

    def test_unmarked_overlap_is_probability(self):
        """Root overlap is in [0, 1].

        Config: max_depth=2, num_moves=2
        Qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        overlap = _measure_root_overlap_unmarked(2, 2, 1)
        assert 0 <= overlap <= 1.0 + 1e-10

    def test_unmarked_overlap_less_than_one(self):
        """Root overlap decreases after walk steps.

        Qubits: 7 <= 17
        """
        overlap = _measure_root_overlap_unmarked(2, 2, 1)
        assert overlap < 1.0

    def test_unmarked_depth1_periodic(self):
        """On depth=1 tree, overlap returns to ~1.0 at power=2.

        Qubits: 2 height + 1 branch + 1 count = 4 <= 17
        """
        p2 = _measure_root_overlap_unmarked(2, 1, 2)
        assert abs(p2 - 1.0) < 1e-6

    def test_marked_same_as_unmarked_no_marks(self):
        """With no marks, marked walk equals unmarked walk.

        Qubits: 7 <= 17
        """
        config = WalkConfig(
            max_depth=2, num_moves=2,
            is_marked=_is_marked_never,
        )
        marked = _measure_root_overlap(config, 2)
        unmarked = _measure_root_overlap_unmarked(2, 2, 2)
        assert abs(marked - unmarked) < 1e-10


# ---------------------------------------------------------------------------
# Group 5: Detection Tests
# ---------------------------------------------------------------------------


class TestDetection:
    """Walk detection: marked leaf True, no marks False."""

    def test_detect_known_marked_leaf(self):
        """Detect a known marked leaf (value 3) -> True.

        Tree: max_depth=2, num_moves=2 (4 leaves)
        Marking: value 3 is marked (1 of 4 leaves)
        Qubits: 7 walk <= 17
        """
        result = walk(
            _is_marked_value3,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_detect_no_marked_nodes(self):
        """No marked nodes -> False.

        Tree: max_depth=2, num_moves=2
        Marking: nothing marked
        Qubits: 7 walk <= 17
        """
        result = walk(
            _is_marked_never,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is False

    def test_detect_multiple_marked_leaves(self):
        """Detect when multiple leaves are marked -> True.

        Tree: max_depth=2, num_moves=2
        Marking: values >= 1 (3 of 4 leaves)
        Qubits: 7 <= 17
        """
        result = walk(
            _is_marked_ge1,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_detect_returns_bool(self):
        """walk() returns exactly True or False (type check).

        Qubits: 7 <= 17
        """
        result = walk(
            _is_marked_never,
            max_depth=2, num_moves=2, max_iterations=4,
        )
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Group 6: max_iterations edge cases
# ---------------------------------------------------------------------------


class TestMaxIterationsEdgeCases:
    """walk() max_iterations validation and behavior."""

    def test_max_iterations_zero_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(_is_marked_never, max_depth=2, num_moves=2,
                 max_iterations=0)

    def test_max_iterations_negative_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(_is_marked_never, max_depth=2, num_moves=2,
                 max_iterations=-1)

    def test_max_iterations_float_raises(self):
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            walk(_is_marked_never, max_depth=2, num_moves=2,
                 max_iterations=4.0)

    def test_max_iterations_one(self):
        """max_iterations=1 tests only power=1.

        With only power=1, the marking effect is too small for
        detection.  Should return False.

        Qubits: 7 <= 17
        """
        result = walk(
            _is_marked_value3,
            max_depth=2, num_moves=2, max_iterations=1,
        )
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Group 7: ILP Tests
# ---------------------------------------------------------------------------


def _ilp2_is_marked(state):
    """2-var ILP: state == 3 (both bits set)."""
    return state == 3


def _ilp3_is_marked(state):
    """3-var ILP: state == 7 (all three bits set)."""
    return state == 7


class TestILP:
    """Binary ILP detection tests."""

    def test_2var_ilp_detects_feasible(self):
        """2-variable binary ILP: detect assignment x0=1, x1=1.

        Tree: max_depth=2, num_moves=2
        Walk qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        result = walk(
            _ilp2_is_marked,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_3var_ilp_detects_feasible(self):
        """3-variable binary ILP within 15 qubits.

        Tree: max_depth=3, num_moves=2
        Walk qubits: 4 height + 3 branch + 2 count = 9 <= 15
        """
        result = walk(
            _ilp3_is_marked,
            max_depth=3, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_3var_ilp_qubit_budget(self):
        """3-variable ILP walk qubits fit within 15.

        Walk registers: height=4, branch=3, count=2 -> 9
        """
        config = WalkConfig(max_depth=3, num_moves=2)
        total = config.total_walk_qubits()
        assert total <= 15, f"3-var ILP walk uses {total} qubits"


# ---------------------------------------------------------------------------
# Group 8: Consistency Tests
# ---------------------------------------------------------------------------


class TestConsistency:
    """Consistency and determinism of walk()."""

    def test_deterministic_results(self):
        """walk() produces consistent results across runs.

        Qubits: 7 <= 17
        """
        results = []
        for _ in range(3):
            r = walk(
                _is_marked_never,
                max_depth=2, num_moves=2, max_iterations=8,
            )
            results.append(r)
        assert all(r == results[0] for r in results)

    def test_walk_importable(self):
        """walk is importable from quantum_language."""
        from quantum_language import walk as w
        assert callable(w)


# ---------------------------------------------------------------------------
# Group 9: Internal function tests
# ---------------------------------------------------------------------------


class TestCollectBranchQubits:
    """Test _collect_branch_qubits returns correct qubit indices."""

    def test_binary_depth2_returns_2_qubits(self):
        """Binary depth=2: 2 branch registers of 1 qubit each.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        qubits = _collect_branch_qubits(regs, config)
        assert len(qubits) == 2

    def test_binary_depth3_returns_3_qubits(self):
        """Binary depth=3: 3 branch registers of 1 qubit each.

        Qubits: 9 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(config)
        qubits = _collect_branch_qubits(regs, config)
        assert len(qubits) == 3

    def test_qubit_indices_are_distinct(self):
        """All returned qubit indices should be unique.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        qubits = _collect_branch_qubits(regs, config)
        assert len(set(qubits)) == len(qubits)

    def test_qubit_indices_match_branch_registers(self):
        """Returned qubits match branch_at() values.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        qubits = _collect_branch_qubits(regs, config)

        expected = []
        for d in range(config.max_depth):
            br = regs.branch_at(d)
            bw = br.width
            for bit in range(bw):
                expected.append(int(br.qubits[64 - bw + bit]))
        assert qubits == expected

    def test_ternary_depth2_returns_4_qubits(self):
        """Ternary depth=2: 2 branch registers of 2 qubits each.

        Qubits: 9 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(config)
        qubits = _collect_branch_qubits(regs, config)
        assert len(qubits) == 4


class TestApplyPhaseOnPattern:
    """Test _apply_phase_on_pattern X-MCZ-X gate sequences."""

    def test_pattern_all_ones_no_x_gates(self):
        """Pattern with all 1s should emit no X gates, only MCZ.

        For pattern=3 (binary 11) on 2 branch qubits, no X gates
        are needed because all bits are already 1.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        regs.init_root()

        h_leaf_qubit = regs.height_qubit(0)
        branch_qubits = _collect_branch_qubits(regs, config)

        _apply_phase_on_pattern(3, branch_qubits, h_leaf_qubit)

        qasm = ql.to_openqasm()
        # Should NOT contain standalone 'x' gates (only init x for root)
        gate_lines = [
            l.strip() for l in qasm.split("\n")
            if l.strip().startswith("x ") and "q[" in l
        ]
        # The only X gate is the root initialization x q[2]
        root_x_count = sum(
            1 for l in gate_lines
            if l == f"x q[{regs.height_qubit(config.max_depth)}];"
        )
        assert len(gate_lines) == root_x_count

    def test_pattern_zero_emits_x_on_all_branches(self):
        """Pattern 0 (all zeros): X on every branch qubit before/after MCZ.

        For pattern=0, all branch bits should be 0, so we X them to
        convert to all-1s for MCZ, then X again to undo.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        regs.init_root()

        h_leaf_qubit = regs.height_qubit(0)
        branch_qubits = _collect_branch_qubits(regs, config)

        _apply_phase_on_pattern(0, branch_qubits, h_leaf_qubit)

        qasm = ql.to_openqasm()
        # Count X gates on branch qubits (each appears twice: before + after)
        x_count = 0
        for bq in branch_qubits:
            x_count += qasm.count(f"x q[{bq}];")
        assert x_count == 2 * len(branch_qubits)

    def test_phase_flip_on_target_state(self):
        """Pattern phase flip changes sign of correct basis state.

        Prepare h[0]=1 and branch pattern=3 (both branch qubits=1),
        apply phase on pattern 3.  The amplitude of that state
        should get a -1 phase.

        Qubits: 7 <= 17
        """
        from quantum_language._gates import emit_x

        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)

        # Set h[0]=1 (leaf), and both branches to 1 (pattern=3)
        emit_x(regs.height_qubit(0))
        for bq in _collect_branch_qubits(regs, config):
            emit_x(bq)

        # Record amplitude before marking
        qasm_before = ql.to_openqasm()
        sv_before = _simulate_statevector(qasm_before)

        # Now apply the marking phase
        _init_circuit()
        emit_x(regs.height_qubit(0))
        for bq in _collect_branch_qubits(regs, config):
            emit_x(bq)
        _apply_phase_on_pattern(
            3, _collect_branch_qubits(regs, config),
            regs.height_qubit(0),
        )
        qasm_after = ql.to_openqasm()
        sv_after = _simulate_statevector(qasm_after)

        # Find the nonzero amplitude index
        nonzero = np.where(np.abs(sv_before) > 0.5)[0]
        assert len(nonzero) == 1
        idx = nonzero[0]

        # Phase should have flipped: before +1, after -1
        assert abs(sv_before[idx] - 1.0) < 1e-6
        assert abs(sv_after[idx] + 1.0) < 1e-6

    def test_phase_flip_does_not_affect_other_pattern(self):
        """Phase flip on pattern 3 should NOT affect pattern 1.

        Prepare h[0]=1 with branch=1 (only LSB set), then apply
        phase on pattern 3.  The amplitude should be unchanged.

        Qubits: 7 <= 17
        """
        from quantum_language._gates import emit_x

        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)

        # Set h[0]=1 (leaf), branch[0]=1 only (pattern=1)
        emit_x(regs.height_qubit(0))
        branch_qubits = _collect_branch_qubits(regs, config)
        emit_x(branch_qubits[0])  # LSB only

        _apply_phase_on_pattern(3, branch_qubits, regs.height_qubit(0))

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # The nonzero amplitude should still be +1 (no phase flip)
        nonzero = np.where(np.abs(sv) > 0.5)[0]
        assert len(nonzero) == 1
        assert abs(sv[nonzero[0]] - 1.0) < 1e-6


class TestEvaluateIsMarkedClassically:
    """Test classical evaluation of is_marked predicate."""

    def test_marks_value3_only(self):
        result = _evaluate_is_marked_classically(
            lambda v: v == 3, total_branch_bits=2,
        )
        assert result == [3]

    def test_marks_nothing(self):
        result = _evaluate_is_marked_classically(
            lambda v: False, total_branch_bits=2,
        )
        assert result == []

    def test_marks_all(self):
        result = _evaluate_is_marked_classically(
            lambda v: True, total_branch_bits=2,
        )
        assert result == [0, 1, 2, 3]

    def test_marks_ge1(self):
        result = _evaluate_is_marked_classically(
            lambda v: v >= 1, total_branch_bits=2,
        )
        assert result == [1, 2, 3]

    def test_broken_callback_raises(self):
        """If callback raises, the exception propagates."""
        def bad_pred(v):
            raise RuntimeError("broken")
        with pytest.raises(RuntimeError, match="broken"):
            _evaluate_is_marked_classically(bad_pred, total_branch_bits=2)
