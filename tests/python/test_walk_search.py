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

import pytest

import quantum_language as ql
from quantum_language.walk_search import (
    _max_walk_iterations,
    _measure_root_overlap,
    _measure_root_overlap_unmarked,
    _tree_size,
    _validate_walk_args,
    walk,
)
from quantum_language.walk_core import WalkConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()


# ---------------------------------------------------------------------------
# Simple move/validity/marking callbacks for testing
# ---------------------------------------------------------------------------


def _make_move_xor(state, move_idx):
    """Apply move by XORing state with (move_idx + 1)."""
    state ^= (move_idx + 1)


def _undo_move_xor(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= (move_idx + 1)


def _is_valid_always(state):
    """All moves are valid."""
    return state == state  # Always True qbool


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

    def test_rejects_none_state(self):
        with pytest.raises(ValueError, match="state must not be None"):
            _validate_walk_args(None, lambda s, i: None, lambda s: None,
                                lambda s: None, 2, 2)

    def test_rejects_none_make_move(self):
        with pytest.raises(ValueError, match="make_move must not be None"):
            _validate_walk_args("state", None, lambda s: None,
                                lambda s: None, 2, 2)

    def test_rejects_none_is_valid(self):
        with pytest.raises(ValueError, match="is_valid must not be None"):
            _validate_walk_args("state", lambda s, i: None, None,
                                lambda s: None, 2, 2)

    def test_rejects_none_is_marked(self):
        with pytest.raises(ValueError, match="is_marked must not be None"):
            _validate_walk_args("state", lambda s, i: None, lambda s: None,
                                None, 2, 2)

    def test_rejects_non_int_max_depth(self):
        with pytest.raises(TypeError, match="max_depth must be an int"):
            _validate_walk_args("s", lambda s, i: None, lambda s: None,
                                lambda s: None, 2.0, 2)

    def test_rejects_non_int_num_moves(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            _validate_walk_args("s", lambda s, i: None, lambda s: None,
                                lambda s: None, 2, 2.0)

    def test_rejects_zero_max_depth(self):
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            _validate_walk_args("s", lambda s, i: None, lambda s: None,
                                lambda s: None, 0, 2)

    def test_rejects_zero_num_moves(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            _validate_walk_args("s", lambda s, i: None, lambda s: None,
                                lambda s: None, 2, 0)


# ---------------------------------------------------------------------------
# Group 4: Root Overlap Tests
# ---------------------------------------------------------------------------


class TestRootOverlap:
    """Test root overlap measurement produces valid probabilities."""

    def test_unmarked_overlap_is_probability(self):
        """Root overlap is in [0, 1].

        Config: max_depth=2, num_moves=2
        Qubits: 3 height + 2 branch + 1 count = 6 <= 17
        """
        overlap = _measure_root_overlap_unmarked(2, 2, 1)
        assert 0 <= overlap <= 1.0 + 1e-10

    def test_unmarked_overlap_less_than_one(self):
        """Root overlap decreases after walk steps.

        Qubits: 6 <= 17
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

        Qubits: 6 <= 17
        """
        _init_circuit()
        s = ql.qint(0, width=2)
        config = WalkConfig(
            max_depth=2, num_moves=2,
            is_marked=_is_marked_never, state=s,
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
        _init_circuit()
        s = ql.qint(0, width=2)
        result = walk(
            s, _make_move_xor, _is_valid_always, _is_marked_value3,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_detect_no_marked_nodes(self):
        """No marked nodes -> False.

        Tree: max_depth=2, num_moves=2
        Marking: nothing marked
        Qubits: 7 walk <= 17
        """
        _init_circuit()
        s = ql.qint(0, width=2)
        result = walk(
            s, _make_move_xor, _is_valid_always, _is_marked_never,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is False

    def test_detect_multiple_marked_leaves(self):
        """Detect when multiple leaves are marked -> True.

        Tree: max_depth=2, num_moves=2
        Marking: values >= 1 (3 of 4 leaves)
        Qubits: 7 <= 17
        """
        _init_circuit()
        s = ql.qint(0, width=2)
        result = walk(
            s, _make_move_xor, _is_valid_always, _is_marked_ge1,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_detect_returns_bool(self):
        """walk() returns exactly True or False (type check).

        Qubits: 7 <= 17
        """
        _init_circuit()
        s = ql.qint(0, width=2)
        result = walk(
            s, _make_move_xor, _is_valid_always, _is_marked_never,
            max_depth=2, num_moves=2, max_iterations=4,
        )
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Group 6: ILP Tests
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
        State: 2-bit (branch registers encode variables)
        Walk qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        _init_circuit()
        s = ql.qint(0, width=2)
        result = walk(
            s, _make_move_xor, _is_valid_always, _ilp2_is_marked,
            max_depth=2, num_moves=2, max_iterations=16,
        )
        assert result is True

    def test_3var_ilp_detects_feasible(self):
        """3-variable binary ILP within 15 qubits.

        Tree: max_depth=3, num_moves=2
        Walk qubits: 4 height + 3 branch + 2 count = 9 <= 15
        """
        _init_circuit()
        s = ql.qint(0, width=3)
        result = walk(
            s, _make_move_xor, _is_valid_always, _ilp3_is_marked,
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
# Group 7: Consistency Tests
# ---------------------------------------------------------------------------


class TestConsistency:
    """Consistency and determinism of walk()."""

    def test_deterministic_results(self):
        """walk() produces consistent results across runs.

        Qubits: 7 <= 17
        """
        results = []
        for _ in range(3):
            _init_circuit()
            s = ql.qint(0, width=2)
            r = walk(
                s, _make_move_xor, _is_valid_always, _is_marked_never,
                max_depth=2, num_moves=2, max_iterations=8,
            )
            results.append(r)
        assert all(r == results[0] for r in results)

    def test_walk_importable(self):
        """walk is importable from quantum_language."""
        from quantum_language import walk as w
        assert callable(w)
