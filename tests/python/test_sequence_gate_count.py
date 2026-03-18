"""Tests for _sequence_gate_count Cython helper.

Issue: Quantum_Assembly-vdn
Spec: R16.11

Tests:
1. Function exists and is importable from _core.
2. Returns 0 for null (0) pointer.
3. Returns correct gate count for valid sequence pointers (via compile IR).
4. Integration with _resolve_gate_count in call_graph.
"""

import quantum_language as ql
from quantum_language._core import _sequence_gate_count
from quantum_language.compile import CompiledBlock


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


class TestSequenceGateCountNull:
    """_sequence_gate_count returns 0 for null pointer."""

    def test_null_returns_zero(self):
        """Passing 0 (null) returns 0."""
        assert _sequence_gate_count(0) == 0


class TestSequenceGateCountValid:
    """_sequence_gate_count returns correct count for valid sequence pointers."""

    def test_cq_add_sequence_has_positive_count(self):
        """CQ_add sequence pointer has a positive gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode records sequence_t ptrs
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        assert len(block._instruction_ir) == 1
        rec = block._instruction_ir[0]
        assert rec.uncontrolled_seq != 0
        count = _sequence_gate_count(rec.uncontrolled_seq)
        assert count > 0, f"Expected positive gate count, got {count}"

    def test_controlled_sequence_has_positive_count(self):
        """Controlled CQ_add sequence also has a positive gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        rec = block._instruction_ir[0]
        if rec.controlled_seq != 0:
            count = _sequence_gate_count(rec.controlled_seq)
            assert count > 0, f"Expected positive controlled gate count, got {count}"

    def test_different_widths_different_counts(self):
        """Wider addition sequences produce more gates."""
        counts = {}
        for width in (4, 8):
            ql.circuit()
            ql.option("fault_tolerant", False)
            a = ql.qint(0, width=width)

            @ql.compile
            def dummy(x):
                return x

            block = _make_block()
            with dummy.compile_mode(block):
                a += 1

            rec = block._instruction_ir[0]
            assert rec.uncontrolled_seq != 0
            counts[width] = _sequence_gate_count(rec.uncontrolled_seq)

        assert counts[8] > counts[4], (
            f"8-bit ({counts[8]}) should have more gates than 4-bit ({counts[4]})"
        )

    def test_qq_add_sequence_has_positive_count(self):
        """QQ_add sequence pointer has a positive gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += b

        qq_entries = [r for r in block._instruction_ir if r.name == "add_qq"]
        assert len(qq_entries) == 1
        rec = qq_entries[0]
        assert rec.uncontrolled_seq != 0
        count = _sequence_gate_count(rec.uncontrolled_seq)
        assert count > 0, f"Expected positive QQ gate count, got {count}"


class TestSequenceGateCountIntegration:
    """_sequence_gate_count integrates with _resolve_gate_count."""

    def test_resolve_uses_cython_helper(self):
        """_resolve_gate_count delegates to _sequence_gate_count for valid ptrs."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        rec = block._instruction_ir[0]
        assert rec.uncontrolled_seq != 0

        result = _resolve_gate_count(rec.uncontrolled_seq)
        expected = _sequence_gate_count(rec.uncontrolled_seq)
        assert result == expected
        assert result > 0

    def test_resolve_returns_zero_for_null(self):
        """_resolve_gate_count returns 0 for null pointer."""
        from quantum_language.call_graph import _resolve_gate_count

        assert _resolve_gate_count(0) == 0
