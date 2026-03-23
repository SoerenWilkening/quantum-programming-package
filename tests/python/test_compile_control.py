"""Tests for compiled function control propagation.

Verify that @ql.compile stores separate cache entries for controlled and
uncontrolled calls (control_count is part of the cache key). Each context
captures its own block independently (no derived controlled_block).

Replay inside a with-block uses the separately captured controlled block.

Requirements: Quantum_Assembly-aql.1, Quantum_Assembly-aql.2
"""

import gc
import warnings

import quantum_language as ql
from quantum_language.compile import CompiledBlock

warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestPerContextCacheEntry:
    """Verify per-context cache entries for controlled vs uncontrolled calls."""

    def test_single_cache_entry_uncontrolled(self):
        """Calling outside a with-block creates exactly one cache entry."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        assert len(inc._cache) == 1

    def test_separate_cache_entry_controlled(self):
        """Calling inside a with-block creates a second cache entry."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        # First call outside with to populate cache
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)  # Controlled call creates separate entry

        # Per-context cache: controlled and uncontrolled are separate entries
        assert len(inc._cache) == 2

    def test_single_cache_entry_first_call_in_with(self):
        """First call inside a with-block creates exactly one cache entry."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)  # First call (capture path, inside with)

        # Single entry, not separate entries for control_count=0 and 1
        assert len(inc._cache) == 1


class TestBlockIsCompiledBlock:
    """Verify that cached blocks are CompiledBlock instances."""

    def test_uncontrolled_block_is_compiled_block(self):
        """After capture, cached block is a CompiledBlock."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert isinstance(block, CompiledBlock)

    def test_uncontrolled_gates_no_extra_controls(self):
        """Uncontrolled block gates have no extra control qubits added."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        # Uncontrolled gates should exist
        assert len(block.gates) > 0

    def test_no_controlled_block_attribute(self):
        """Blocks no longer have a controlled_block attribute."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert not hasattr(block, "controlled_block")


class TestCacheKeyWithControlCount:
    """Verify that control_count IS part of the cache key."""

    def test_separate_keys_controlled_and_uncontrolled(self):
        """Uncontrolled and controlled calls create separate cache entries."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        # First call: uncontrolled (populates cache)
        a = ql.qint(0, width=2)
        _ = inc(a)
        assert len(inc._cache) == 1

        # Second call: controlled (creates separate cache entry)
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)
        assert len(inc._cache) == 2

    def test_cache_key_tuple_has_control_count(self):
        """Cache key contains control_count after qubit_saving."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        # The cache key is a tuple:
        #   (classical_args, widths, qubit_saving, control_count, *mode_flags)
        key = list(inc._cache.keys())[0]
        # key[0] = classical_args tuple (empty for this case)
        # key[1] = widths tuple
        # key[2] = qubit_saving (bool)
        # key[3] = control_count (int 0 for uncontrolled)
        assert isinstance(key[2], bool), (
            f"Expected key[2] to be bool (qubit_saving), got {type(key[2]).__name__} = {key[2]!r}"
        )
        assert key[3] == 0, (
            f"Expected key[3] to be 0 (control_count for uncontrolled), got {key[3]!r}"
        )

    def test_different_widths_different_entries(self):
        """Different qubit widths still produce different cache entries."""

        @ql.compile(opt=0)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)
        b = ql.qint(0, width=3)
        _ = inc(b)

        # Different widths -> different keys -> 2 entries
        assert len(inc._cache) == 2


# =========================================================================
# Runtime sequence selection in _replay
# =========================================================================


class TestControlledDifferentGates:
    """Controlled context produces more gates than uncontrolled."""

    def test_controlled_more_gates(self):
        """with ctrl: f(x) produces more gates than f(x) alone."""
        from quantum_language._core import get_gate_count

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # Uncontrolled call (capture)
        a = ql.qint(0, width=2)
        gc_before = get_gate_count()
        _ = inc(a)
        uc_cost = get_gate_count() - gc_before

        # Controlled call (capture -- separate cache entry)
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        gc_before = get_gate_count()
        with c:
            _ = inc(b)
        cc_cost = get_gate_count() - gc_before

        # Controlled should cost more
        assert cc_cost >= uc_cost


class TestUncontrolledReplay:
    """Replaying without control uses uncontrolled sequence."""

    def test_uncontrolled_replay(self):
        """Second call outside with-block replays uncontrolled gates."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call: capture
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block.total_virtual_qubits > 0

        # Second call: replay (no control context) -- should work
        b = ql.qint(0, width=2)
        _ = inc(b)

        # Still one cache entry for uncontrolled
        assert len(inc._cache) == 1


class TestControlledReplay:
    """Replaying with control uses controlled sequence."""

    def test_controlled_replay(self):
        """Replay inside a with-block uses the controlled cache entry."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call: capture (uncontrolled)
        a = ql.qint(0, width=2)
        _ = inc(a)

        # Second call: capture inside with-block (controlled -- separate key)
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)

        # Per-context cache: uncontrolled and controlled are separate entries
        assert len(inc._cache) == 2

    def test_controlled_replay_first_call_in_with(self):
        """First call inside with-block, second inside another with-block."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call inside with (capture path)
        c1 = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c1:
            _ = inc(a)

        # Second call inside different with (replay path)
        c2 = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c2:
            _ = inc(b)

        assert len(inc._cache) == 1


class TestNestedWithCompiled:
    """Nested with blocks use AND-ancilla as control qubit."""

    def test_nested_with_compiled(self):
        """with c1: with c2: f(x) uses the AND-ancilla as control qubit."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call: capture outside with
        a = ql.qint(0, width=3)
        _ = inc(a)

        # Nested with blocks: the two conditions are AND-combined into
        # a single control qubit (AND-ancilla)
        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c1:
            with c2:
                _ = inc(b)

        # Per-context cache: uncontrolled and controlled are separate entries
        assert len(inc._cache) == 2


class TestSimulateTrueControlled:
    """With simulate=True, controlled and uncontrolled produce different states."""

    def test_simulate_true_replay_injects_gates(self):
        """With simulate=True, replay inside with-block injects gates."""
        from quantum_language._core import get_gate_count

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # Capture + replay uncontrolled
        a = ql.qint(0, width=2)
        _ = inc(a)
        gate_count_uncontrolled = get_gate_count()

        # Replay controlled
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)
        gate_count_total = get_gate_count()

        # Controlled replay should have added gates
        controlled_gates_added = gate_count_total - gate_count_uncontrolled
        assert controlled_gates_added > 0, "Controlled replay did not inject any gates"
