"""Smoke tests for demo scripts (demo.py and chess_comparison.py)."""

import pytest

import chess_walk


@pytest.fixture(autouse=True)
def _reset_walk_cache():
    """Reset chess_walk module-level compiled function cache between tests."""
    chess_walk._walk_compiled_fn = None
    yield
    chess_walk._walk_compiled_fn = None


def test_demo_main():
    """demo.main() runs end-to-end and returns a stats dict with non-zero values."""
    from demo import main

    stats = main(visualize=False)

    assert isinstance(stats, dict), "main() must return a dict"
    for key in ("qubit_count", "gate_count", "depth"):
        assert key in stats, f"Missing key: {key}"
        assert stats[key] > 0, f"{key} must be > 0, got {stats[key]}"


@pytest.mark.skip(reason="chess_comparison.py not yet created")
def test_comparison_main():
    """chess_comparison.main() runs end-to-end and returns a results dict."""
    from chess_comparison import main

    results = main(visualize=False)
    assert isinstance(results, dict)
