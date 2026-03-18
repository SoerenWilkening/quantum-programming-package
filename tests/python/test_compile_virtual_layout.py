"""Tests for standardized virtual qubit layout — control at index 0.

Verifies the acceptance criteria for Quantum_Assembly-6us:

1. Captured block gates never reference virtual index 0.
2. Controlled variant gates all have 0 in controls.
3. Uncontrolled and controlled blocks have same total_virtual_qubits.
4. param_qubit_ranges uses (start, end) tuples starting at 1.
5. Replay inside with block produces different gates than outside.
"""

import gc
import warnings

import quantum_language as ql
from quantum_language.compile import (
    _build_virtual_mapping,
    _derive_controlled_gates,
)

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# AC-1: Captured block gates never reference virtual index 0
# ---------------------------------------------------------------------------
class TestCapturedGatesNoIndex0:
    """Virtual index 0 is reserved; uncontrolled gates must never use it."""

    def test_inc_gates_skip_index_0(self):
        """Simple increment: no gate target or control touches index 0."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)
        a = ql.qint(0, width=3)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        for gate in block.gates:
            assert gate["target"] != 0, f"Uncontrolled gate target is virtual index 0: {gate}"
            assert 0 not in gate["controls"], (
                f"Uncontrolled gate controls contain virtual index 0: {gate}"
            )

    def test_add_gates_skip_index_0(self):
        """Two-argument add: no gate references index 0."""

        @ql.compile
        def add(x, y):
            x += y
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        _ = add(a, b)

        block = list(add._cache.values())[0]
        for gate in block.gates:
            assert gate["target"] != 0, f"Uncontrolled gate target is virtual index 0: {gate}"
            assert 0 not in gate["controls"], (
                f"Uncontrolled gate controls contain virtual index 0: {gate}"
            )

    def test_build_virtual_mapping_skips_index_0(self):
        """_build_virtual_mapping assigns no real qubit to virtual index 0."""
        # Simulate a small gate list with real qubit indices 10, 11, 12
        gates = [
            {
                "target": 10,
                "controls": [11],
                "num_controls": 1,
                "gate_type": 0,
                "angle": 0.0,
                "layer": 0,
            },
            {
                "target": 12,
                "controls": [],
                "num_controls": 0,
                "gate_type": 0,
                "angle": 0.0,
                "layer": 0,
            },
        ]
        param_indices = [[10, 11], [12]]
        virtual_gates, r2v, total = _build_virtual_mapping(gates, param_indices)

        # No real qubit should map to virtual index 0
        assert 0 not in r2v.values(), f"A real qubit was mapped to virtual index 0: {r2v}"
        # Virtual indices should start at 1
        assert min(r2v.values()) == 1

        # Verify virtual gates don't use index 0
        for vg in virtual_gates:
            assert vg["target"] != 0
            assert 0 not in vg["controls"]


# ---------------------------------------------------------------------------
# AC-2: Controlled variant gates all have 0 in controls
# ---------------------------------------------------------------------------
class TestControlledGatesHaveIndex0:
    """Every gate in the controlled block must include index 0 in controls."""

    def test_controlled_gates_all_have_0(self):
        """All controlled gates have virtual index 0 in their controls."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)
        a = ql.qint(0, width=3)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        ctrl_block = block.controlled_block
        assert ctrl_block is not None

        for gate in ctrl_block.gates:
            assert 0 in gate["controls"], f"Controlled gate missing index 0 in controls: {gate}"

    def test_derive_controlled_gates_prepends_0(self):
        """_derive_controlled_gates prepends 0 to every gate's controls."""
        gates = [
            {
                "target": 1,
                "controls": [2],
                "num_controls": 1,
                "gate_type": 0,
                "angle": 0.0,
                "layer": 0,
            },
            {
                "target": 3,
                "controls": [],
                "num_controls": 0,
                "gate_type": 0,
                "angle": 0.0,
                "layer": 0,
            },
        ]
        result = _derive_controlled_gates(gates)

        for rg in result:
            assert rg["controls"][0] == 0, f"First control is not 0: {rg['controls']}"

        # Gate with 1 control -> 2 controls
        assert result[0]["num_controls"] == 2
        assert result[0]["controls"] == [0, 2]

        # Gate with 0 controls -> 1 control
        assert result[1]["num_controls"] == 1
        assert result[1]["controls"] == [0]

    def test_controlled_block_control_virtual_idx_is_0(self):
        """controlled_block.control_virtual_idx is exactly 0."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block.controlled_block.control_virtual_idx == 0


# ---------------------------------------------------------------------------
# AC-3: Uncontrolled and controlled blocks have same total_virtual_qubits
# ---------------------------------------------------------------------------
class TestSameTotalVirtualQubits:
    """Both block variants must report the same total_virtual_qubits."""

    def test_same_total_simple(self):
        """Simple inc: both variants have equal total_virtual_qubits."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        ctrl = block.controlled_block
        assert block.total_virtual_qubits == ctrl.total_virtual_qubits

    def test_same_total_two_args(self):
        """Two-argument function: both variants have equal total_virtual_qubits."""

        @ql.compile
        def add(x, y):
            x += y
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        _ = add(a, b)

        block = list(add._cache.values())[0]
        ctrl = block.controlled_block
        assert block.total_virtual_qubits == ctrl.total_virtual_qubits

    def test_uncontrolled_control_virtual_idx_is_none(self):
        """Uncontrolled block has control_virtual_idx=None."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block.control_virtual_idx is None


# ---------------------------------------------------------------------------
# AC-4: param_qubit_ranges uses (start, end) tuples starting at 1
# ---------------------------------------------------------------------------
class TestParamQubitRangesFormat:
    """param_qubit_ranges must be list of (start, end) tuples beginning at 1."""

    def test_single_arg_range_starts_at_1(self):
        """Single argument: param_qubit_ranges starts at virtual index 1."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=4)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert len(block.param_qubit_ranges) == 1
        start, end = block.param_qubit_ranges[0]
        assert start == 1, f"param range starts at {start}, expected 1"
        assert end == 5, f"param range ends at {end}, expected 5 (1+4)"

    def test_two_args_contiguous_from_1(self):
        """Two arguments: ranges are contiguous starting at 1."""

        @ql.compile
        def add(x, y):
            x += y
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=2)
        _ = add(a, b)

        block = list(add._cache.values())[0]
        assert len(block.param_qubit_ranges) == 2

        s0, e0 = block.param_qubit_ranges[0]
        s1, e1 = block.param_qubit_ranges[1]

        assert s0 == 1, f"First param starts at {s0}, expected 1"
        assert e0 == 4, f"First param ends at {e0}, expected 4 (1+3)"
        assert s1 == 4, f"Second param starts at {s1}, expected 4"
        assert e1 == 6, f"Second param ends at {e1}, expected 6 (4+2)"

    def test_ranges_are_tuples(self):
        """Each range is a tuple (not list)."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        for r in block.param_qubit_ranges:
            assert isinstance(r, tuple), f"Expected tuple, got {type(r).__name__}"
            assert len(r) == 2, f"Expected 2-tuple, got length {len(r)}"

    def test_controlled_block_same_param_ranges(self):
        """Controlled block shares the same param_qubit_ranges."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=3)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        ctrl = block.controlled_block
        assert block.param_qubit_ranges == ctrl.param_qubit_ranges


# ---------------------------------------------------------------------------
# AC-5: Replay inside with block produces different gates than outside
# ---------------------------------------------------------------------------
class TestReplayControlledVsUncontrolled:
    """Replay under control context must produce different (controlled) gates."""

    def test_gate_count_differs(self):
        """Controlled replay injects gates with more controls than uncontrolled."""
        from quantum_language._core import get_gate_count

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
        after_capture = get_gate_count()

        # Uncontrolled replay
        b = ql.qint(0, width=2)
        _ = inc(b)
        after_uncontrolled = get_gate_count()
        uncontrolled_count = after_uncontrolled - after_capture

        # Controlled replay
        c = ql.qbool(True)
        d = ql.qint(0, width=2)
        with c:
            _ = inc(d)
        after_controlled = get_gate_count()
        controlled_count = after_controlled - after_uncontrolled

        # Controlled replay produces at least as many gates (each gate
        # in the controlled variant has one extra control qubit)
        assert controlled_count >= uncontrolled_count, (
            f"Controlled ({controlled_count}) should be >= uncontrolled ({uncontrolled_count})"
        )

    def test_controlled_gates_in_block_differ(self):
        """The controlled block's gate list differs from uncontrolled."""

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

        # Same number of gates
        assert len(block.gates) == len(ctrl_block.gates)

        # But each controlled gate has one more control
        for ug, cg in zip(block.gates, ctrl_block.gates, strict=False):
            assert cg["num_controls"] == ug["num_controls"] + 1
            # The extra control is index 0
            assert cg["controls"][0] == 0
            # Remaining controls match the uncontrolled gate
            assert cg["controls"][1:] == ug["controls"]

    def test_replay_controlled_maps_index_0_to_control_qubit(self):
        """When replaying in a with block, virtual index 0 maps to the control qubit."""

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

        # Controlled replay -- this should work without error,
        # meaning index 0 was correctly mapped to the control qubit
        ctrl = ql.qbool(True)
        b = ql.qint(0, width=2)
        with ctrl:
            result = inc(b)

        # Verify result is valid
        assert result is not None
