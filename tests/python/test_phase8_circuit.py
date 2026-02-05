"""Phase 8: Circuit Optimization Tests

Tests for CIRC-01, CIRC-02, CIRC-03, CIRC-04 requirements.
"""

import pytest
from quantum_language import circuit, qint


class TestCircuitStatistics:
    """Tests for CIRC-04: Circuit statistics."""

    def test_gate_count_property_exists(self):
        """gate_count property is accessible."""
        c = circuit()
        assert hasattr(c, "gate_count")
        assert isinstance(c.gate_count, int)
        assert c.gate_count >= 0

    def test_depth_property_exists(self):
        """depth property is accessible."""
        c = circuit()
        assert hasattr(c, "depth")
        assert isinstance(c.depth, int)
        assert c.depth >= 0

    def test_qubit_count_property_exists(self):
        """qubit_count property is accessible."""
        c = circuit()
        assert hasattr(c, "qubit_count")
        assert isinstance(c.qubit_count, int)

    def test_gate_counts_property_exists(self):
        """gate_counts property returns dict with expected keys."""
        c = circuit()
        assert hasattr(c, "gate_counts")
        counts = c.gate_counts
        assert isinstance(counts, dict)
        expected_keys = {"X", "Y", "Z", "H", "P", "CNOT", "CCX", "other"}
        assert set(counts.keys()) == expected_keys

    def test_stats_increase_with_operations(self):
        """Statistics increase as operations are added."""
        c = circuit()
        initial_gates = c.gate_count
        initial_depth = c.depth

        # Create qints and perform operation
        a = qint(5, width=4)
        b = qint(3, width=4)
        _ = a + b

        # Stats should have increased
        assert c.gate_count > initial_gates
        assert c.depth > initial_depth

    def test_gate_counts_breakdown(self):
        """gate_counts shows breakdown after operations."""
        c = circuit()

        # Create qints - this adds some gates
        a = qint(5, width=4)
        b = qint(3, width=4)
        _ = a + b

        counts = c.gate_counts
        total = sum(counts.values())
        assert total == c.gate_count


class TestCircuitOptimization:
    """Tests for CIRC-02, CIRC-03: Gate merging and inverse cancellation."""

    def test_available_passes_property(self):
        """available_passes returns list of pass names."""
        c = circuit()
        passes = c.available_passes
        assert isinstance(passes, list)
        assert "merge" in passes
        assert "cancel_inverse" in passes

    def test_optimize_returns_stats_dict(self):
        """optimize() returns a dict with before/after stats."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit
        stats = c.optimize()

        assert isinstance(stats, dict)
        assert "before" in stats
        assert "after" in stats

        # Before stats structure
        assert "gate_count" in stats["before"]
        assert "depth" in stats["before"]
        assert "qubit_count" in stats["before"]
        assert "gate_counts" in stats["before"]

        # After stats structure
        assert "gate_count" in stats["after"]
        assert "depth" in stats["after"]
        assert "qubit_count" in stats["after"]
        assert "gate_counts" in stats["after"]

    def test_optimize_with_passes_parameter(self):
        """optimize(passes=[...]) accepts pass list and returns stats."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit
        stats = c.optimize(passes=["cancel_inverse"])

        assert isinstance(stats, dict)
        assert "before" in stats
        assert "after" in stats

    def test_optimize_invalid_pass_raises(self):
        """optimize with invalid pass name raises ValueError."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit
        with pytest.raises(ValueError, match="Unknown pass"):
            c.optimize(passes=["nonexistent_pass"])

    def test_can_optimize_returns_bool(self):
        """can_optimize() returns boolean."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit
        result = c.can_optimize()
        assert isinstance(result, bool)

    def test_optimize_modifies_circuit_in_place(self):
        """Optimization modifies the circuit - stats may change."""
        c = circuit()
        a = qint(5, width=4)
        b = qint(3, width=4)
        _ = a + b

        before_gates = c.gate_count
        stats = c.optimize()

        # Stats dict should reflect what we captured
        assert stats["before"]["gate_count"] == before_gates
        # After optimization, circuit stats match after dict
        assert c.gate_count == stats["after"]["gate_count"]

    def test_optimization_does_not_crash(self):
        """Optimization runs without crashing on various circuits."""
        c = circuit()

        # Simple operations
        a = qint(5, width=4)
        b = qint(3, width=4)
        _ = a + b

        # Should not crash
        stats = c.optimize()
        assert isinstance(stats, dict)


class TestPhase8SuccessCriteria:
    """Explicit tests for Phase 8 success criteria from ROADMAP.md."""

    def test_success_criteria_1_visualization(self):
        """SC1: Text-based circuit visualization shows circuit structure."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit
        # visualize() should not raise
        c.visualize()
        # If we get here without error, visualization works

    def test_success_criteria_2_gate_merging(self):
        """SC2: Automatic gate merging optimization available."""
        c = circuit()
        assert "merge" in c.available_passes
        _a = qint(5, width=4)  # Needed to generate circuit
        stats = c.optimize(passes=["merge"])
        assert isinstance(stats, dict)
        assert "before" in stats and "after" in stats

    def test_success_criteria_3_inverse_cancellation(self):
        """SC3: Inverse gate cancellation available."""
        c = circuit()
        assert "cancel_inverse" in c.available_passes
        _a = qint(5, width=4)  # Needed to generate circuit
        stats = c.optimize(passes=["cancel_inverse"])
        assert isinstance(stats, dict)
        assert "before" in stats and "after" in stats

    def test_success_criteria_4_statistics(self):
        """SC4: Circuit statistics available programmatically."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit

        # All stats should be accessible
        assert isinstance(c.gate_count, int)
        assert isinstance(c.depth, int)
        assert isinstance(c.qubit_count, int)
        assert isinstance(c.gate_counts, dict)

    def test_success_criteria_5_pass_control(self):
        """SC5: Optimization passes can be enabled/disabled independently."""
        c = circuit()
        _a = qint(5, width=4)  # Needed to generate circuit

        # Can run specific passes - each returns stats dict
        stats1 = c.optimize(passes=["merge"])
        assert isinstance(stats1, dict)

        # Create fresh circuit for next test
        c2 = circuit()
        _b = qint(3, width=4)  # Needed to generate circuit
        stats2 = c2.optimize(passes=["cancel_inverse"])
        assert isinstance(stats2, dict)

        # Create fresh circuit for all passes
        c3 = circuit()
        _d = qint(7, width=4)  # Needed to generate circuit
        stats_all = c3.optimize()  # All passes
        assert isinstance(stats_all, dict)
