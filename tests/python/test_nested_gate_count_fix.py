"""Tests for nested compiled function gate count fix.

Issue: Quantum_Assembly-i81
Spec: R20.5

Tests that ql.get_gate_count() matches between compiled and uncompiled
execution, and between first call (capture) and replay.
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language._core import get_gate_count, reset_gate_count


class TestNestedGateCountConsistency:
    """get_gate_count() is consistent between capture and replay for nested functions."""

    def test_nested_compiled_replay_matches_capture(self):
        """Replay gate count matches capture gate count for nested compiled functions."""
        ql.circuit()

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x = inner(x)
            x += 2
            return x

        a = qint(0, width=4)

        # First call (capture)
        reset_gate_count()
        outer(a)
        capture_gc = get_gate_count()

        # Second call (replay)
        reset_gate_count()
        outer(a)
        replay_gc = get_gate_count()

        assert replay_gc == capture_gc, (
            f"Replay gate count {replay_gc} != capture gate count {capture_gc}"
        )

    def test_nested_compiled_matches_uncompiled(self):
        """Compiled nested gate count matches uncompiled equivalent."""
        ql.circuit()

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x = inner(x)
            x += 2
            return x

        a = qint(0, width=4)
        reset_gate_count()
        outer(a)
        compiled_gc = get_gate_count()

        # Uncompiled equivalent
        ql.circuit()
        b = qint(0, width=4)
        reset_gate_count()
        b += 1
        b += 2
        uncompiled_gc = get_gate_count()

        assert compiled_gc == uncompiled_gc, (
            f"Compiled gate count {compiled_gc} != uncompiled {uncompiled_gc}"
        )

    def test_single_compiled_replay_matches_capture(self):
        """Single (non-nested) compiled function: replay matches capture."""
        ql.circuit()

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = qint(0, width=4)

        reset_gate_count()
        inc(a)
        capture_gc = get_gate_count()

        reset_gate_count()
        inc(a)
        replay_gc = get_gate_count()

        assert replay_gc == capture_gc, f"Replay {replay_gc} != capture {capture_gc}"

    def test_deeply_nested_replay_matches_capture(self):
        """Three levels of nesting: replay matches capture."""
        ql.circuit()

        @ql.compile
        def level3(x):
            x += 1
            return x

        @ql.compile
        def level2(x):
            x = level3(x)
            x += 2
            return x

        @ql.compile
        def level1(x):
            x = level2(x)
            x += 3
            return x

        a = qint(0, width=4)

        reset_gate_count()
        level1(a)
        capture_gc = get_gate_count()

        reset_gate_count()
        level1(a)
        replay_gc = get_gate_count()

        assert replay_gc == capture_gc, f"Deep nested: replay {replay_gc} != capture {capture_gc}"

    def test_hierarchical_gate_count_matches_get_gate_count(self):
        """hierarchical_gate_count().total matches get_gate_count() on replay."""
        ql.circuit()

        @ql.compile
        def inner2(x):
            x += 1
            return x

        @ql.compile
        def outer2(x):
            x = inner2(x)
            x += 2
            return x

        a = qint(0, width=4)
        outer2(a)  # capture

        reset_gate_count()
        outer2(a)  # replay
        replay_gc = get_gate_count()

        hier = outer2._hierarchical_gate_count()
        assert hier["total"] == replay_gc, (
            f"hierarchical total {hier['total']} != replay {replay_gc}"
        )
