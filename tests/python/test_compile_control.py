"""Tests for unified cache entry with both uncontrolled and controlled sequences.

Phase 5, Step 5.1: Verify that @ql.compile stores a single cache entry
containing both uncontrolled and controlled gate sequences, with no
control_count in the cache key. The controlled variant is derived via
_derive_controlled_block and attached to the same CompiledBlock.

Requirements: Quantum_Assembly-aql.1
"""

import gc
import warnings

import quantum_language as ql
from quantum_language.compile import CompiledBlock

warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestSingleCacheEntry:
    """Verify that one cache entry is created regardless of controlled context."""

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

    def test_single_cache_entry_controlled(self):
        """Calling inside a with-block still creates exactly one cache entry."""

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
            _ = inc(b)  # Replay path (controlled)

        # Still only one cache entry (not two)
        assert len(inc._cache) == 1

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


class TestBothSequencesStored:
    """Verify that both uncontrolled and controlled gate sequences are stored."""

    def test_controlled_block_attached(self):
        """After capture, block.controlled_block is a CompiledBlock."""

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
        assert block.controlled_block is not None
        assert isinstance(block.controlled_block, CompiledBlock)

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
        # control_virtual_idx should be None for uncontrolled block
        assert block.control_virtual_idx is None

    def test_controlled_gates_have_extra_control(self):
        """Controlled block gates each have one additional control qubit."""

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
        ctrl_block = block.controlled_block

        # Controlled block should have gates
        assert len(ctrl_block.gates) > 0
        # control_virtual_idx should be set
        assert ctrl_block.control_virtual_idx is not None
        # Each controlled gate has one more control than the corresponding uncontrolled gate
        for ug, cg in zip(block.gates, ctrl_block.gates, strict=False):
            assert cg["num_controls"] == ug["num_controls"] + 1

    def test_controlled_block_total_virtual_qubits(self):
        """Controlled block has one more virtual qubit than uncontrolled."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        ctrl_block = block.controlled_block

        assert ctrl_block.total_virtual_qubits == block.total_virtual_qubits + 1


class TestCacheKeyNoControlCount:
    """Verify that control_count is not part of the cache key."""

    def test_same_key_controlled_and_uncontrolled(self):
        """Uncontrolled and controlled calls hit the same cache entry."""

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

        # Second call: controlled (should hit same cache entry, not create new)
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)
        assert len(inc._cache) == 1

    def test_cache_key_tuple_has_no_control_count(self):
        """Cache key does not contain a 0 or 1 for control_count."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        # The cache key is a tuple. In the old code it was:
        #   (classical_args, widths, control_count, qubit_saving, *mode_flags)
        # In the new code it should be:
        #   (classical_args, widths, qubit_saving, *mode_flags)
        # So key[2] should NOT be 0 or 1 (control_count).
        key = list(inc._cache.keys())[0]
        # key[0] = classical_args tuple (empty for this case)
        # key[1] = widths tuple
        # key[2] = qubit_saving (bool), NOT control_count (int 0 or 1)
        # The old control_count would be at index 2 with value 0 or 1 (int).
        # qubit_saving is a bool (True/False).
        assert isinstance(key[2], bool), (
            f"Expected key[2] to be bool (qubit_saving), "
            f"got {type(key[2]).__name__} = {key[2]!r} (likely control_count)"
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
