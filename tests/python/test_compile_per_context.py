"""Tests for per-context compiled function cache key (Quantum_Assembly-1yb, Quantum_Assembly-czb, Quantum_Assembly-e80).

Verifies that control_count is included in the compiled function cache key
so controlled and uncontrolled calls produce separate cache entries with
independent, correct original_gate_count values from actual Toffoli dispatch.

Tests:
- test_separate_cache_entries — both contexts present after mixed calls
- test_uncontrolled_gate_count — uncontrolled call credits correct cost
- test_controlled_gate_count — controlled call credits correct cost
- test_order_independent — call order does not affect per-call gate counts
- test_nested_controlled_gate_count — outer calling inner inside with:
  total matches uncompiled equivalent
- test_no_controlled_block_attr — cached blocks have no controlled_block
- test_cache_miss_controlled — controlled call after uncontrolled is a cache miss
- test_replay_credits_correct_context — controlled replay credits controlled cost,
  uncontrolled replay credits uncontrolled cost
- test_nested_replay_total_matches_uncompiled — outer(inner_uc + own_ops + inner_ctrl)
  total equals manual equivalent
"""

import gc
import warnings

import quantum_language as ql
from quantum_language._core import get_gate_count

warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestSeparateCacheEntries:
    """Controlled and uncontrolled calls create separate cache entries."""

    def test_separate_cache_entries(self):
        """After calling foo both uncontrolled and controlled, _cache has 2 entries."""

        @ql.compile
        def foo(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = foo(a)
        assert len(foo._cache) == 1

        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c:
            _ = foo(b)
        assert len(foo._cache) == 2

    def test_controlled_only_one_entry(self):
        """Calling only in controlled context creates exactly one entry."""

        @ql.compile
        def bar(x):
            x += 2
            return x

        gc.collect()
        ql.circuit()
        c = ql.qbool(True)
        a = ql.qint(0, width=3)
        with c:
            _ = bar(a)
        assert len(bar._cache) == 1

    def test_two_uncontrolled_calls_one_entry(self):
        """Two uncontrolled calls with same widths share one cache entry."""

        @ql.compile
        def baz(x):
            x += 3
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = baz(a)
        b = ql.qint(0, width=3)
        _ = baz(b)
        assert len(baz._cache) == 1

    def test_two_controlled_calls_one_entry(self):
        """Two controlled calls with same widths share one cache entry."""

        @ql.compile
        def qux(x):
            x += 4
            return x

        gc.collect()
        ql.circuit()
        c1 = ql.qbool(True)
        a = ql.qint(0, width=3)
        with c1:
            _ = qux(a)

        c2 = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c2:
            _ = qux(b)
        assert len(qux._cache) == 1


class TestUncontrolledGateCount:
    """Uncontrolled call credits correct uncontrolled cost."""

    def test_uncontrolled_gate_count(self):
        """Uncontrolled call's original_gate_count reflects uncontrolled Toffoli dispatch."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Measure standalone uncontrolled cost
        gc_before = get_gate_count()
        a_raw = ql.qint(0, width=3)
        a_raw += 1
        standalone_cost = get_gate_count() - gc_before

        # Now use compiled version
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = inc(a)

        # Find the uncontrolled cache entry (control_count=0)
        uc_block = None
        for _key, block in inc._cache.items():
            # control_count is in the key; find the uncontrolled one
            if block.original_gate_count > 0:
                # Check if this is the uncontrolled entry by looking at key
                uc_block = block
                break

        assert uc_block is not None
        assert uc_block.original_gate_count == standalone_cost


class TestControlledGateCount:
    """Controlled call credits correct controlled cost."""

    def test_controlled_gate_count(self):
        """Controlled call's original_gate_count reflects controlled Toffoli dispatch."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Measure standalone controlled cost
        ctrl = ql.qbool(True)
        gc_before = get_gate_count()
        a_raw = ql.qint(0, width=3)
        with ctrl:
            a_raw += 1
        standalone_ctrl_cost = get_gate_count() - gc_before

        # Now use compiled version in controlled context
        ql.circuit()
        c = ql.qbool(True)
        a = ql.qint(0, width=3)
        with c:
            _ = inc(a)

        # Find the controlled cache entry
        blocks = list(inc._cache.values())
        assert len(blocks) == 1  # Only controlled call was made
        ctrl_block = blocks[0]
        assert ctrl_block.original_gate_count == standalone_ctrl_cost


class TestOrderIndependent:
    """Call order does not affect per-call gate counts."""

    def test_order_independent(self):
        """Uncontrolled-first and controlled-first produce same per-call gate counts."""

        # --- Order 1: uncontrolled first ---
        @ql.compile
        def inc_a(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        a = ql.qint(0, width=3)
        gc_before = get_gate_count()
        _ = inc_a(a)
        uc_cost_order1 = get_gate_count() - gc_before

        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        gc_before = get_gate_count()
        with c:
            _ = inc_a(b)
        ctrl_cost_order1 = get_gate_count() - gc_before

        # --- Order 2: controlled first ---
        @ql.compile
        def inc_b(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        c2 = ql.qbool(True)
        d = ql.qint(0, width=3)
        gc_before = get_gate_count()
        with c2:
            _ = inc_b(d)
        ctrl_cost_order2 = get_gate_count() - gc_before

        e = ql.qint(0, width=3)
        gc_before = get_gate_count()
        _ = inc_b(e)
        uc_cost_order2 = get_gate_count() - gc_before

        # Gate counts should match regardless of order
        assert uc_cost_order1 == uc_cost_order2
        assert ctrl_cost_order1 == ctrl_cost_order2

        # Controlled should cost more than uncontrolled
        assert ctrl_cost_order1 > uc_cost_order1


class TestNestedControlledGateCount:
    """Outer calling inner inside with: inner gets a controlled cache entry."""

    def test_nested_controlled_gate_count(self):
        """Inner function called inside with: from outer gets a controlled cache entry
        whose original_gate_count matches standalone controlled cost."""

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            c = x > 2
            with c:
                x = inner(x)
            return x

        gc.collect()
        ql.circuit()

        # Measure standalone controlled cost for inner's operation
        ctrl = ql.qbool(True)
        gc_before = get_gate_count()
        a_raw = ql.qint(0, width=4)
        with ctrl:
            a_raw += 1
        standalone_ctrl_cost = get_gate_count() - gc_before

        # Run compiled outer (which calls inner inside with:)
        ql.circuit()
        a = ql.qint(0, width=4)
        _ = outer(a)

        # Inner should have exactly one cache entry (controlled, since
        # outer calls it inside a with: block)
        assert len(inner._cache) == 1
        inner_block = list(inner._cache.values())[0]
        assert inner_block.original_gate_count == standalone_ctrl_cost

    def test_nested_both_contexts(self):
        """Inner called both controlled (from outer) and uncontrolled produces 2 entries."""

        @ql.compile
        def inner2(x):
            x += 1
            return x

        @ql.compile
        def outer2(x):
            c = x > 2
            with c:
                x = inner2(x)
            return x

        gc.collect()
        ql.circuit()

        # Call inner uncontrolled first
        a = ql.qint(0, width=4)
        _ = inner2(a)
        assert len(inner2._cache) == 1

        # Call outer which calls inner controlled
        b = ql.qint(0, width=4)
        _ = outer2(b)
        assert len(inner2._cache) == 2


class TestNoControlledBlockAttr:
    """Cached blocks have no controlled_block attribute (Quantum_Assembly-czb)."""

    def test_no_controlled_block_attr(self):
        """After capture, cached blocks do not have a controlled_block attribute."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Uncontrolled call
        a = ql.qint(0, width=3)
        _ = inc(a)

        # Controlled call
        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c:
            _ = inc(b)

        # Both cache entries should not have controlled_block
        for _key, block in inc._cache.items():
            assert not hasattr(block, "controlled_block")


class TestCacheMissControlled:
    """Controlled call after uncontrolled is a cache miss (separate key)."""

    def test_cache_miss_controlled(self):
        """A controlled call after an uncontrolled call is a cache miss,
        not a replay of the uncontrolled block's controlled variant."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Uncontrolled call (cache miss -> capture)
        a = ql.qint(0, width=3)
        _ = inc(a)
        assert len(inc._cache) == 1

        # Controlled call should be a separate cache miss
        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c:
            _ = inc(b)

        # Should now have 2 entries (separate keys)
        assert len(inc._cache) == 2

        # The two cache entries should be different blocks
        blocks = list(inc._cache.values())
        assert blocks[0] is not blocks[1]


class TestReplayCreditsCorrectContext:
    """Replay credits the correct per-context gate cost (Quantum_Assembly-e80)."""

    def test_replay_credits_correct_context(self):
        """Controlled replay credits controlled cost, uncontrolled replay
        credits uncontrolled cost."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Measure standalone costs
        x_raw = ql.qint(0, width=3)
        gc_before = get_gate_count()
        x_raw += 1
        uc_standalone = get_gate_count() - gc_before

        ql.circuit()
        ctrl = ql.qbool(True)
        x_raw2 = ql.qint(0, width=3)
        gc_before = get_gate_count()
        with ctrl:
            x_raw2 += 1
        ctrl_standalone = get_gate_count() - gc_before

        # Capture both contexts
        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = inc(a)

        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c:
            _ = inc(b)

        # Replay uncontrolled
        d = ql.qint(0, width=3)
        gc_before = get_gate_count()
        _ = inc(d)
        uc_replay = get_gate_count() - gc_before

        # Replay controlled
        c2 = ql.qbool(True)
        e = ql.qint(0, width=3)
        gc_before = get_gate_count()
        with c2:
            _ = inc(e)
        ctrl_replay = get_gate_count() - gc_before

        assert uc_replay == uc_standalone, (
            f"Uncontrolled replay {uc_replay} != standalone {uc_standalone}"
        )
        assert ctrl_replay == ctrl_standalone, (
            f"Controlled replay {ctrl_replay} != standalone {ctrl_standalone}"
        )


class TestNestedReplayTotalMatchesUncompiled:
    """Nested replay total matches uncompiled equivalent (Quantum_Assembly-e80)."""

    def test_nested_replay_total_matches_uncompiled(self):
        """outer(inner_uc + own_ops + inner_ctrl) total equals manual
        equivalent on both capture and replay."""

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x = inner(x)  # uncontrolled inner call
            x += 2  # outer's own operation
            c = ql.qbool(True)
            with c:
                x = inner(x)  # controlled inner call
            return x

        gc.collect()
        ql.circuit()

        # Uncompiled baseline
        x = ql.qint(0, width=4)
        gc_before = get_gate_count()
        x += 1
        x += 2
        c = ql.qbool(True)
        with c:
            x += 1
        uncompiled_total = get_gate_count() - gc_before

        # Compiled capture
        gc.collect()
        ql.circuit()
        y = ql.qint(0, width=4)
        gc_before = get_gate_count()
        _ = outer(y)
        capture_total = get_gate_count() - gc_before

        # Compiled replay
        z = ql.qint(0, width=4)
        gc_before = get_gate_count()
        _ = outer(z)
        replay_total = get_gate_count() - gc_before

        assert capture_total == uncompiled_total, (
            f"Capture {capture_total} != uncompiled {uncompiled_total}"
        )
        assert replay_total == uncompiled_total, (
            f"Replay {replay_total} != uncompiled {uncompiled_total}"
        )
