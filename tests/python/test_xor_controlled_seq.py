"""Tests for XOR controlled sequence wiring (Step 11.2).

Covers issue Quantum_Assembly-bl0.2: XOR and in-place XOR compile-mode IR
entries now pass controlled_seq (cQ_xor, cQ_not) to _record_instruction.

Acceptance criteria:
- XOR IR entry has non-zero controlled_seq
- In-place XOR IR entries (ixor_cq, ixor_qq) have non-zero controlled_seq
- Compiled function with XOR called in controlled context produces correct gate count
- DAG report shows non-zero U and C for XOR nodes
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


class TestXorIRControlledSeq:
    """XOR IR entries have non-zero controlled_seq."""

    def test_xor_qq_has_controlled_seq(self):
        """xor IR entry has non-zero controlled_seq."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a ^ b

        entries = [r for r in block._instruction_ir if r.name == "xor"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_ixor_cq_has_controlled_seq(self):
        """ixor_cq IR entry has non-zero controlled_seq."""
        ql.circuit()
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a ^= 5

        entries = [r for r in block._instruction_ir if r.name == "ixor_cq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_ixor_qq_has_controlled_seq(self):
        """ixor_qq IR entry has non-zero controlled_seq."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a ^= b

        entries = [r for r in block._instruction_ir if r.name == "ixor_qq"]
        assert len(entries) == 1
        assert entries[0].uncontrolled_seq != 0
        assert entries[0].controlled_seq != 0

    def test_xor_controlled_seq_differs_from_uncontrolled(self):
        """XOR controlled_seq pointer differs from uncontrolled_seq."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a ^ b

        entry = [r for r in block._instruction_ir if r.name == "xor"][0]
        assert entry.uncontrolled_seq != entry.controlled_seq, (
            "XOR: uncontrolled and controlled seq pointers should differ"
        )

    def test_ixor_qq_controlled_seq_differs_from_uncontrolled(self):
        """ixor_qq controlled_seq pointer differs from uncontrolled_seq."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a ^= b

        entry = [r for r in block._instruction_ir if r.name == "ixor_qq"][0]
        assert entry.uncontrolled_seq != entry.controlled_seq, (
            "ixor_qq: uncontrolled and controlled seq pointers should differ"
        )


# ---------------------------------------------------------------------------
# DAG report shows non-zero U and C for XOR nodes
# ---------------------------------------------------------------------------


class TestDagXorGateCounts:
    """DAG report shows non-zero U and C for XOR nodes."""

    def test_dag_xor_qq_has_both_gate_counts(self):
        """XOR QQ: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a ^ b

        entry = [r for r in block._instruction_ir if r.name == "xor"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"XOR QQ uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"XOR QQ controlled gate count should be > 0, got {cc_gc}"

    def test_dag_ixor_cq_has_both_gate_counts(self):
        """ixor_cq: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a ^= 5

        entry = [r for r in block._instruction_ir if r.name == "ixor_cq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"ixor_cq uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"ixor_cq controlled gate count should be > 0, got {cc_gc}"

    def test_dag_ixor_qq_has_both_gate_counts(self):
        """ixor_qq: _resolve_gate_count returns > 0 for both sequences."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a ^= b

        entry = [r for r in block._instruction_ir if r.name == "ixor_qq"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert uc_gc > 0, f"ixor_qq uncontrolled gate count should be > 0, got {uc_gc}"
        assert cc_gc > 0, f"ixor_qq controlled gate count should be > 0, got {cc_gc}"

    def test_dag_xor_controlled_count_ge_uncontrolled(self):
        """XOR controlled gate count >= uncontrolled (CNOT -> Toffoli)."""
        from quantum_language.call_graph import _resolve_gate_count

        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a ^ b

        entry = [r for r in block._instruction_ir if r.name == "xor"][0]
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        cc_gc = _resolve_gate_count(entry.controlled_seq)
        assert cc_gc >= uc_gc, (
            f"XOR controlled gate count ({cc_gc}) should be >= uncontrolled ({uc_gc})"
        )
