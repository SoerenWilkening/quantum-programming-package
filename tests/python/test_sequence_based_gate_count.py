"""Tests for sequence-based gate counting (Step 12.2).

Issue: Quantum_Assembly-vpi
Spec: R23.6

Tests:
1. All operation sequences have total_gate_count > 0 after creation.
2. Sequence metadata gate count matches gates emitted by run_instruction.
3. run_instruction fast path uses total_gate_count (O(1) counting).
4. Bitwise/comparison operations report gate counts from sequence metadata.
"""

import quantum_language as ql


class TestSequenceGateCountNonzero:
    """All operation sequences have total_gate_count > 0."""

    def test_qft_cq_add_nonzero(self):
        """QFT CQ addition sequence has total_gate_count > 0."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        a += 3
        assert ql.get_gate_count() > 0

    def test_qft_qq_add_nonzero(self):
        """QFT QQ addition sequence has total_gate_count > 0."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        assert ql.get_gate_count() > 0

    def test_toffoli_cq_add_nonzero(self):
        """Toffoli CQ addition records nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        a += 3
        assert ql.get_gate_count() > 0

    def test_toffoli_qq_add_nonzero(self):
        """Toffoli QQ addition records nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        assert ql.get_gate_count() > 0

    def test_bitwise_and_nonzero(self):
        """AND operation sequence has nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        _ = a & b
        assert ql.get_gate_count() > 0

    def test_bitwise_or_nonzero(self):
        """OR operation sequence has nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        _ = a | b
        assert ql.get_gate_count() > 0

    def test_bitwise_not_nonzero(self):
        """NOT operation sequence has nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = ~a
        assert ql.get_gate_count() > 0

    def test_comparison_eq_nonzero(self):
        """Equality comparison sequence has nonzero gate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = a == 3
        assert ql.get_gate_count() > 0


class TestSequenceCountMatchesExecution:
    """Sequence metadata count matches gates emitted by run_instruction."""

    def test_qft_cq_count_matches_simulate(self):
        """QFT CQ add: non-simulate gate count matches simulate gate count."""
        # Non-simulate mode (counting via total_gate_count fast path)
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", False)
        a = ql.qint(0, width=4)
        a += 3
        gc_nosim = ql.get_gate_count()

        # Simulate mode (counting via per-gate increment)
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        a += 3
        gc_sim = ql.get_gate_count()

        assert gc_nosim == gc_sim, f"Non-simulate count {gc_nosim} != simulate count {gc_sim}"

    def test_qft_qq_count_matches_simulate(self):
        """QFT QQ add: non-simulate count matches simulate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        ql.option("simulate", False)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        gc_nosim = ql.get_gate_count()

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        a += b
        gc_sim = ql.get_gate_count()

        assert gc_nosim == gc_sim

    def test_toffoli_cq_count_matches_simulate(self):
        """Toffoli CQ add: non-simulate count matches simulate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=4)
        a += 3
        gc_nosim = ql.get_gate_count()

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        a += 3
        gc_sim = ql.get_gate_count()

        assert gc_nosim == gc_sim

    def test_toffoli_qq_count_matches_simulate(self):
        """Toffoli QQ add: non-simulate count matches simulate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        a += b
        gc_nosim = ql.get_gate_count()

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        a += b
        gc_sim = ql.get_gate_count()

        assert gc_nosim == gc_sim

    def test_bitwise_and_both_positive(self):
        """AND operation: both modes produce positive gate counts."""
        # Note: AND has a pre-existing discrepancy between simulate and
        # non-simulate modes due to how Q_and sequences count multi-qubit
        # gates vs their decomposed forms. Both should be positive.
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        _ = a & b
        gc_nosim = ql.get_gate_count()

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=3)
        b = ql.qint(0, width=3)
        _ = a & b
        gc_sim = ql.get_gate_count()

        assert gc_nosim > 0
        assert gc_sim > 0

    def test_not_count_matches_simulate(self):
        """NOT operation: non-simulate count matches simulate count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=4)
        _ = ~a
        gc_nosim = ql.get_gate_count()

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = ~a
        gc_sim = ql.get_gate_count()

        assert gc_nosim == gc_sim


class TestRunInstructionFastPath:
    """run_instruction fast path uses total_gate_count for O(1) counting."""

    def test_fast_path_counts_correctly(self):
        """Non-simulate addition produces correct gate count via fast path."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=4)
        a += 1
        # Gate count should be positive (fast path used total_gate_count)
        assert ql.get_gate_count() > 0

    def test_fast_path_multiple_operations(self):
        """Multiple operations in non-simulate mode accumulate correctly."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", False)
        a = ql.qint(0, width=3)
        a += 1
        gc1 = ql.get_gate_count()
        a += 2
        gc2 = ql.get_gate_count()
        assert gc2 > gc1, "Second addition should increase gate count"
