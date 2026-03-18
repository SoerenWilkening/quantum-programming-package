"""Tests for dual gate counts on DAGNode — uncontrolled / controlled display.

Issue: Quantum_Assembly-u71
Spec: R16.11

Tests:
1. test_dag_node_dual_gate_counts — both fields stored and formatted correctly.
2. test_dag_node_single_variant — '-' shown for unavailable variant.
3. test_to_dot_dual_format — to_dot() output uses 'gates: X / Y' format.
"""

from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _format_dual_gates,
)

# ---------------------------------------------------------------------------
# test_dag_node_dual_gate_counts
# ---------------------------------------------------------------------------


class TestDAGNodeDualGateCounts:
    """DAGNode stores both uncontrolled_gate_count and controlled_gate_count."""

    def test_both_fields_in_slots(self):
        """uncontrolled_gate_count and controlled_gate_count in __slots__."""
        assert "uncontrolled_gate_count" in DAGNode.__slots__
        assert "controlled_gate_count" in DAGNode.__slots__

    def test_default_values_zero(self):
        """Both fields default to 0."""
        node = DAGNode("f", {0}, 10, ())
        assert node.uncontrolled_gate_count == 0
        assert node.controlled_gate_count == 0

    def test_stores_both_counts(self):
        """Both fields are stored when passed to constructor."""
        node = DAGNode(
            "f",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=24,
            controlled_gate_count=18,
        )
        assert node.uncontrolled_gate_count == 24
        assert node.controlled_gate_count == 18

    def test_add_node_passes_through(self):
        """CallGraphDAG.add_node() passes dual gate counts to DAGNode."""
        dag = CallGraphDAG()
        dag.add_node(
            "f",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=30,
            controlled_gate_count=50,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 30
        assert node.controlled_gate_count == 50

    def test_format_dual_gates_both(self):
        """_format_dual_gates with both values non-zero."""
        assert _format_dual_gates(24, 18) == "24 / 18"

    def test_format_dual_gates_large(self):
        """_format_dual_gates with large values."""
        assert _format_dual_gates(100000, 200000) == "100000 / 200000"


# ---------------------------------------------------------------------------
# test_dag_node_single_variant
# ---------------------------------------------------------------------------


class TestDAGNodeSingleVariant:
    """'-' displayed when a variant's gate count is 0 (unavailable)."""

    def test_format_uncontrolled_only(self):
        """Only uncontrolled available: shows 'X / -'."""
        assert _format_dual_gates(24, 0) == "24 / -"

    def test_format_controlled_only(self):
        """Only controlled available: shows '- / Y'."""
        assert _format_dual_gates(0, 18) == "- / 18"

    def test_format_neither_available(self):
        """Neither available: shows '- / -'."""
        assert _format_dual_gates(0, 0) == "- / -"

    def test_node_with_uncontrolled_only(self):
        """Node with only uncontrolled_gate_count set."""
        node = DAGNode(
            "f",
            {0},
            10,
            (),
            uncontrolled_gate_count=42,
            controlled_gate_count=0,
        )
        assert node.uncontrolled_gate_count == 42
        assert node.controlled_gate_count == 0

    def test_node_with_controlled_only(self):
        """Node with only controlled_gate_count set."""
        node = DAGNode(
            "f",
            {0},
            10,
            (),
            uncontrolled_gate_count=0,
            controlled_gate_count=33,
        )
        assert node.uncontrolled_gate_count == 0
        assert node.controlled_gate_count == 33


# ---------------------------------------------------------------------------
# test_to_dot_dual_format
# ---------------------------------------------------------------------------


class TestToDotDualFormat:
    """to_dot() output uses 'gates: X / Y' format."""

    def test_dot_dual_format_both(self):
        """to_dot() label shows 'gates: 24 / 18' when both counts set."""
        dag = CallGraphDAG()
        dag.add_node(
            "my_fn",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=24,
            controlled_gate_count=18,
        )
        dot = dag.to_dot()
        assert "gates: 24 / 18" in dot

    def test_dot_dual_format_uncontrolled_only(self):
        """to_dot() label shows 'gates: 24 / -' when only uncontrolled set."""
        dag = CallGraphDAG()
        dag.add_node(
            "my_fn",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=24,
            controlled_gate_count=0,
        )
        dot = dag.to_dot()
        assert "gates: 24 / -" in dot

    def test_dot_dual_format_controlled_only(self):
        """to_dot() label shows 'gates: - / 18' when only controlled set."""
        dag = CallGraphDAG()
        dag.add_node(
            "my_fn",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=0,
            controlled_gate_count=18,
        )
        dot = dag.to_dot()
        assert "gates: - / 18" in dot

    def test_dot_dual_format_neither(self):
        """to_dot() label shows 'gates: - / -' when neither set."""
        dag = CallGraphDAG()
        dag.add_node("my_fn", {0, 1}, 10, ())
        dot = dag.to_dot()
        assert "gates: - / -" in dot

    def test_dot_still_has_depth_and_tcount(self):
        """to_dot() still includes depth and T-count lines."""
        dag = CallGraphDAG()
        dag.add_node(
            "my_fn",
            {0, 1},
            10,
            (),
            depth=5,
            t_count=14,
            uncontrolled_gate_count=24,
            controlled_gate_count=18,
        )
        dot = dag.to_dot()
        assert "depth: 5" in dot
        assert "T-count: 14" in dot


# ---------------------------------------------------------------------------
# Report dual gate count column
# ---------------------------------------------------------------------------


class TestReportDualGateColumn:
    """report() table shows dual gate count column."""

    def test_report_header_has_gates_uc(self):
        """report() header contains 'Gates (U/C)'."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, (), uncontrolled_gate_count=24, controlled_gate_count=18)
        report = dag.report()
        assert "Gates (U/C)" in report

    def test_report_row_dual_format(self):
        """report() row shows dual format for gate counts."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, (), uncontrolled_gate_count=24, controlled_gate_count=18)
        report = dag.report()
        assert "24 / 18" in report

    def test_report_row_single_variant(self):
        """report() row shows '-' for unavailable variant."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, (), uncontrolled_gate_count=24, controlled_gate_count=0)
        report = dag.report()
        assert "24 / -" in report

    def test_report_still_has_total(self):
        """report() still has a TOTAL row."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, (), uncontrolled_gate_count=24, controlled_gate_count=18)
        report = dag.report()
        assert "TOTAL" in report
