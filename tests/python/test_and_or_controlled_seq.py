"""Tests for AND/OR controlled sequence wiring (Step 11.4).

Covers issue Quantum_Assembly-bl0.4: AND and OR compile-mode IR entries
now pass controlled_seq (cCQ_and, cQ_and, cCQ_or, cQ_or) to
_record_instruction.

Note: IR recording for bitwise ops only happens in QFT mode
(fault_tolerant=False). In Toffoli mode (default), bitwise ops bypass IR
recording and emit gates directly.

Acceptance criteria:
- AND IR entry has non-zero controlled_seq
- OR IR entry has non-zero controlled_seq
- Compiled function with AND in controlled context: gate count matches uncompiled
- DAG report shows non-zero U and C for AND/OR nodes
"""

import warnings

import quantum_language as ql
from quantum_language.compile import CompiledBlock

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


# ---------------------------------------------------------------------------
# IR entries have non-zero controlled_seq
# ---------------------------------------------------------------------------


class TestAndOrIRControlledSeq:
    """AND and OR IR entries have non-zero controlled_seq."""

    def test_and_qq_has_controlled_seq(self):
        """and_qq IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & b

        entries = [r for r in block._instruction_ir if r.name == "and_qq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_and_cq_has_controlled_seq(self):
        """and_cq IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & 5

        entries = [r for r in block._instruction_ir if r.name == "and_cq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_or_qq_has_controlled_seq(self):
        """or_qq IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | b

        entries = [r for r in block._instruction_ir if r.name == "or_qq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_or_cq_has_controlled_seq(self):
        """or_cq IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | 5

        entries = [r for r in block._instruction_ir if r.name == "or_cq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_and_controlled_seq_differs_from_uncontrolled(self):
        """AND controlled_seq pointer differs from uncontrolled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & b

        entry = [r for r in block._instruction_ir if r.name == "and_qq"][0]
        assert entry.uncontrolled_seq != entry.controlled_seq, (
            "AND: uncontrolled and controlled seq pointers should differ"
        )

    def test_or_controlled_seq_differs_from_uncontrolled(self):
        """OR controlled_seq pointer differs from uncontrolled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | b

        entry = [r for r in block._instruction_ir if r.name == "or_qq"][0]
        assert entry.uncontrolled_seq != entry.controlled_seq, (
            "OR: uncontrolled and controlled seq pointers should differ"
        )


# ---------------------------------------------------------------------------
# DAG report shows non-zero U and C for AND/OR nodes
# ---------------------------------------------------------------------------


class TestDagAndOrGateCounts:
    """DAG report shows non-zero U and C for AND/OR nodes."""

    def test_dag_and_qq_has_both_gate_counts(self):
        """AND QQ: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & b

        entry = [r for r in block._instruction_ir if r.name == "and_qq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"AND QQ uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"AND QQ controlled gate count should be > 0, got {cc_gc}"

    def test_dag_or_qq_has_both_gate_counts(self):
        """OR QQ: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | b

        entry = [r for r in block._instruction_ir if r.name == "or_qq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"OR QQ uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"OR QQ controlled gate count should be > 0, got {cc_gc}"

    def test_dag_and_cq_has_both_gate_counts(self):
        """AND CQ: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & 5

        entry = [r for r in block._instruction_ir if r.name == "and_cq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"AND CQ uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"AND CQ controlled gate count should be > 0, got {cc_gc}"

    def test_dag_or_cq_has_both_gate_counts(self):
        """OR CQ: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | 5

        entry = [r for r in block._instruction_ir if r.name == "or_cq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"OR CQ uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"OR CQ controlled gate count should be > 0, got {cc_gc}"


# ---------------------------------------------------------------------------
# Zero-value edge cases
# ---------------------------------------------------------------------------


class TestZeroValueEdgeCases:
    """AND/OR with classical zero produce valid (non-garbage) gate counts."""

    def test_and_cq_zero_has_valid_gate_count(self):
        """a & 0 in compile mode: gate counts are 0, not garbage."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a & 0

        entries = [r for r in block._instruction_ir if r.name == "and_cq"]
        assert len(entries) == 1
        uc_gc = _resolve_gate_count(entries[0].uncontrolled_seq)
        cc_gc = _resolve_gate_count(entries[0].controlled_seq)
        assert uc_gc == 0, f"AND CQ zero uncontrolled gate count should be 0, got {uc_gc}"
        assert cc_gc == 0, f"AND CQ zero controlled gate count should be 0, got {cc_gc}"

    def test_or_cq_zero_has_valid_gate_count(self):
        """a | 0 in compile mode: gate counts are valid."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for bitwise IR recording
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a | 0

        entries = [r for r in block._instruction_ir if r.name == "or_cq"]
        assert len(entries) == 1
        uc_gc = _resolve_gate_count(entries[0].uncontrolled_seq)
        cc_gc = _resolve_gate_count(entries[0].controlled_seq)
        assert uc_gc >= 0, f"OR CQ zero uncontrolled gate count should be >= 0, got {uc_gc}"
        assert cc_gc >= 0, f"OR CQ zero controlled gate count should be >= 0, got {cc_gc}"
