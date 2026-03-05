"""Smoke tests for demo scripts (demo.py and chess_comparison.py).

The walk step compilation is memory-intensive (~8GB+), so the smoke test
patches walk_step to avoid OOM in CI environments. The pre-walk sections
(position, legal moves, register construction, tree structure) run for real.
"""

from unittest.mock import patch

import pytest

import chess_walk


@pytest.fixture(autouse=True)
def _reset_walk_cache():
    """Reset chess_walk module-level compiled function cache between tests."""
    chess_walk._walk_compiled_fn = None
    yield
    chess_walk._walk_compiled_fn = None


def test_demo_main(clean_circuit):
    """demo.main() runs end-to-end and returns a stats dict with non-zero values.

    Patches walk_step to avoid memory-heavy compilation while still
    exercising all other demo sections (position, moves, registers, stats).
    The patched walk_step emits a few gates so circuit stats are non-zero.
    """
    from demo import main

    def _fake_walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, move_data, max_depth):
        """Lightweight stand-in: emit a handful of X gates to produce non-zero stats."""
        from quantum_language._gates import emit_x

        # Emit a few gates on walk qubits so circuit stats are non-zero
        w = max_depth + 1
        for i in range(w):
            emit_x(int(h_reg.qubits[64 - w + i]))

    with patch("demo.walk_step", side_effect=_fake_walk_step):
        stats = main(visualize=False)

    assert isinstance(stats, dict), "main() must return a dict"
    for key in ("qubit_count", "gate_count", "depth"):
        assert key in stats, f"Missing key: {key}"
        assert stats[key] > 0, f"{key} must be > 0, got {stats[key]}"


def test_comparison_main(clean_circuit):
    """chess_comparison.main() runs end-to-end and returns a results dict.

    Patches both manual walk_step (demo.py) and QWalkTree.walk_step to
    avoid memory-heavy compilation while still verifying the comparison
    script produces correct output structure.
    """
    from chess_comparison import main

    chess_walk._walk_compiled_fn = None

    def _fake_walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, move_data, max_depth):
        """Lightweight stand-in: emit a handful of X gates to produce non-zero stats."""
        from quantum_language._gates import emit_x

        w = max_depth + 1
        for i in range(w):
            emit_x(int(h_reg.qubits[64 - w + i]))

    def _fake_qwt_walk_step(self):
        """Lightweight stand-in for QWalkTree.walk_step: emit X gates on height register."""
        from quantum_language._gates import emit_x

        w = self.max_depth + 1
        for i in range(w):
            emit_x(int(self.height_register.qubits[64 - w + i]))

    with (
        patch("demo.walk_step", side_effect=_fake_walk_step),
        patch("quantum_language.walk.QWalkTree.walk_step", _fake_qwt_walk_step),
    ):
        results = main()

    assert isinstance(results, dict), "main() must return a dict"
    assert "manual" in results, "Missing key: manual"
    assert "api" in results, "Missing key: api"
    assert results["manual"]["qubit_count"] > 0, "manual qubit_count must be > 0"
    assert results["api"]["qubit_count"] > 0, "api qubit_count must be > 0"
