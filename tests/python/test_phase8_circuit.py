"""Phase 8: Circuit Optimization Tests

Tests for CIRC-01, CIRC-02, CIRC-03, CIRC-04 requirements.
"""

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
