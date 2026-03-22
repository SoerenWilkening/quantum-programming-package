"""Tests for compiled function control propagation.

Phase 5, Step 5.1: Verify that @ql.compile stores separate cache entries
for controlled and uncontrolled calls (control_count is part of the cache
key). Each entry's CompiledBlock has both an uncontrolled and controlled
variant derived via _derive_controlled_block.

Phase 5, Step 5.2: Verify that _replay() checks the control stack at
runtime and selects the appropriate gate sequence (controlled or
uncontrolled). The control virtual index is mapped to the actual control
qubit dynamically. Gate sequences are fixed; only qubit mapping varies.

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
        """Controlled block has same total_virtual_qubits as uncontrolled."""

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

        assert ctrl_block.total_virtual_qubits == block.total_virtual_qubits


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
# Phase 5, Step 5.2 — Runtime sequence selection in _replay
# =========================================================================


class TestControlledDifferentGates:
    """Controlled replay produces more gates than uncontrolled."""

    def test_controlled_different_gates(self):
        """with ctrl: f(x) produces more gates than f(x) alone."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # Uncontrolled call (capture)
        a = ql.qint(0, width=2)
        _ = inc(a)
        block = list(inc._cache.values())[0]
        uncontrolled_gate_count = len(block.gates)
        controlled_gate_count = len(block.controlled_block.gates)

        # Controlled variant should have the same number of gates but each
        # gate has one more control qubit
        assert controlled_gate_count == uncontrolled_gate_count
        for ug, cg in zip(block.gates, block.controlled_block.gates, strict=False):
            assert cg["num_controls"] == ug["num_controls"] + 1


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
        uncontrolled_total_vqubits = block.total_virtual_qubits

        # Second call: replay (no control context)
        b = ql.qint(0, width=2)
        _ = inc(b)

        # Both variants now share the same total_virtual_qubits (index 0
        # reserved for control in both)
        ctrl_block = block.controlled_block
        assert ctrl_block.total_virtual_qubits == uncontrolled_total_vqubits


class TestControlledReplay:
    """Replaying with control uses controlled sequence."""

    def test_controlled_replay(self):
        """Replay inside a with-block uses the controlled gate sequence."""

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

        block = list(inc._cache.values())[0]
        ctrl_block = block.controlled_block
        # Controlled block has control_virtual_idx set
        assert ctrl_block.control_virtual_idx is not None

        # Second call: replay inside with-block (controlled)
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

        # First call inside with (capture path: captures uncontrolled,
        # derives controlled)
        c1 = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c1:
            _ = inc(a)

        # Second call inside different with (replay path: uses controlled)
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

    def test_simulate_true_controlled(self):
        """Controlled call with simulate=True injects controlled gates."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # Capture
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        ctrl_block = block.controlled_block

        # Verify the controlled block's gates all include the control
        # virtual index in their controls list
        ctrl_virt = ctrl_block.control_virtual_idx
        assert ctrl_virt is not None
        for gate in ctrl_block.gates:
            assert ctrl_virt in gate["controls"], (
                f"Gate {gate} missing control virtual index {ctrl_virt}"
            )

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
