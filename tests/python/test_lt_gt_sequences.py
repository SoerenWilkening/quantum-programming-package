"""Tests for lt/gt comparison sequence pointers (Phase 11.5).

Covers issue Quantum_Assembly-bl0.5: lt and gt comparisons in compile mode
now have non-zero uncontrolled_seq and controlled_seq, allowing IR replay
to execute comparisons in compiled functions.

All IR tests use QFT mode (fault_tolerant=False) because IR recording
for arithmetic/comparison operations is specific to QFT mode. In Toffoli
mode (default), operations emit gates directly via Toffoli dispatch.
"""

import quantum_language as ql
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


# ---------------------------------------------------------------------------
# Acceptance: lt IR entry has non-zero uncontrolled_seq and controlled_seq
# ---------------------------------------------------------------------------


class TestLtSequencePointers:
    """lt IR entries have valid sequence pointers."""

    def test_lt_cq_has_uncontrolled_seq(self):
        """CQ lt IR entry has non-zero uncontrolled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a < 5

        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].uncontrolled_seq != 0

    def test_lt_cq_has_controlled_seq(self):
        """CQ lt IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a < 5

        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].controlled_seq != 0

    def test_lt_qq_has_uncontrolled_seq(self):
        """QQ lt IR entry has non-zero uncontrolled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a < b

        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].uncontrolled_seq != 0

    def test_lt_qq_has_controlled_seq(self):
        """QQ lt IR entry has non-zero controlled_seq."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a < b

        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].controlled_seq != 0


# ---------------------------------------------------------------------------
# Acceptance: gt IR entry has non-zero sequences
# ---------------------------------------------------------------------------


class TestGtSequencePointers:
    """gt IR entries have valid sequence pointers."""

    def test_gt_cq_has_sequences(self):
        """CQ gt IR entry has non-zero uncontrolled and controlled sequences."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a > 2

        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 1
        assert gt_entries[0].uncontrolled_seq != 0
        assert gt_entries[0].controlled_seq != 0

    def test_gt_qq_has_sequences(self):
        """QQ gt IR entry has non-zero uncontrolled and controlled sequences."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            _ = a > b

        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 1
        assert gt_entries[0].uncontrolled_seq != 0
        assert gt_entries[0].controlled_seq != 0


# ---------------------------------------------------------------------------
# Acceptance: Compiled function with a < b produces correct qbool result
# ---------------------------------------------------------------------------


class TestCompiledLtCorrectness:
    """Compiled lt produces correct results (not silently skipped)."""

    def test_compiled_lt_cq_produces_gates(self):
        """Compiled function with CQ lt produces non-zero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", True)

        @ql.compile
        def check_lt(x):
            r = x < 5
            return r

        a = ql.qint(3, width=4)
        gc_before = ql.get_gate_count()
        check_lt(a)
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "Compiled lt must produce gates"

    def test_compiled_lt_qq_produces_gates(self):
        """Compiled function with QQ lt produces non-zero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", True)

        @ql.compile
        def check_lt(x, y):
            r = x < y
            return r

        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        gc_before = ql.get_gate_count()
        check_lt(a, b)
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "Compiled QQ lt must produce gates"


# ---------------------------------------------------------------------------
# Acceptance: Gate count of compiled lt matches uncompiled
# ---------------------------------------------------------------------------


class TestCompiledLtGateCount:
    """Compiled lt gate count matches uncompiled."""

    def test_lt_cq_gate_count_match(self):
        """Gate count from compiled CQ lt matches uncompiled path."""
        # Uncompiled
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", True)
        a1 = ql.qint(3, width=4)
        gc_before = ql.get_gate_count()
        _ = a1 < 5
        gc_uncompiled = ql.get_gate_count() - gc_before

        # Compiled
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", True)

        @ql.compile
        def check_lt(x):
            r = x < 5
            return r

        a2 = ql.qint(3, width=4)
        gc_before = ql.get_gate_count()
        _ = check_lt(a2)
        gc_compiled = ql.get_gate_count() - gc_before

        assert gc_compiled == gc_uncompiled, (
            f"Compiled CQ lt gate count ({gc_compiled}) must match uncompiled ({gc_uncompiled})"
        )
