"""Tests for demo.py -- circuit-build-only tests for KNK depth-2 walk.

These tests verify that the demo constructs a valid quantum circuit
and that supporting data structures are correct. No simulation is
performed.
"""

import pytest

from chess_encoding import build_move_table


def test_demo_move_tables():
    """Verify build_move_table produces correct entry counts for KNK position."""
    white_table = build_move_table([("wk", "king"), ("wn", "knight")])
    assert len(white_table) == 16, f"White table should have 16 entries, got {len(white_table)}"

    black_table = build_move_table([("bk", "king")])
    assert len(black_table) == 8, f"Black table should have 8 entries, got {len(black_table)}"


def test_demo_prepare_walk_data_structure(clean_circuit):
    """Verify prepare_walk_data returns proper structure for KNK depth-2."""
    from chess_walk import prepare_walk_data

    data = prepare_walk_data(28, 60, [18], 2)

    assert isinstance(data, list), "prepare_walk_data must return a list"
    assert len(data) == 2, f"Expected 2 levels, got {len(data)}"

    # Check required keys in each dict
    required_keys = {
        "move_table",
        "move_count",
        "branch_width",
        "apply_move",
        "predicates",
        "entry_qarray_keys",
    }
    for level_idx, level_data in enumerate(data):
        assert isinstance(level_data, dict), f"Level {level_idx} must be a dict"
        for key in required_keys:
            assert key in level_data, f"Level {level_idx} missing key: {key}"

    # Level 0 (white): 16 moves, 4 branch bits
    assert data[0]["move_count"] == 16
    assert data[0]["branch_width"] == 4
    assert len(data[0]["predicates"]) == 16

    # Level 1 (black): 8 moves, 3 branch bits
    assert data[1]["move_count"] == 8
    assert data[1]["branch_width"] == 3
    assert len(data[1]["predicates"]) == 8


@pytest.mark.slow
def test_demo_circuit_builds(clean_circuit):
    """demo.main() builds a valid circuit and returns stats.

    This test runs the full circuit build (no simulation). It may take
    significant time (10-60s) and memory. Marked as slow -- skip with
    ``pytest -m 'not slow'``.
    """
    from demo import main

    stats = main(visualize=False)

    assert isinstance(stats, dict), "main() must return a dict"
    for key in ("qubit_count", "gate_count", "depth", "build_time"):
        assert key in stats, f"Missing key: {key}"
    assert stats["qubit_count"] > 0
    assert stats["gate_count"] > 0
    assert stats["depth"] > 0
    assert stats["build_time"] >= 0
    assert "gate_counts" in stats
