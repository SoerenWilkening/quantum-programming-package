"""Tests for dual gate counts on DAGNode — uncontrolled / controlled display.

Issue: Quantum_Assembly-u71
Spec: R16.11

Tests:
1. test_dag_node_dual_gate_counts — both fields stored and formatted correctly.
2. test_dag_node_single_variant — '-' shown for unavailable variant.
3. test_to_dot_dual_format — to_dot() output uses 'gates: X / Y' format.
4. test_resolve_gate_count — _resolve_gate_count code paths.
"""

from unittest.mock import patch

from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _format_dual_gates,
    _resolve_gate_count,
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
        """report() TOTAL row is aligned with header and data rows."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, (), uncontrolled_gate_count=24, controlled_gate_count=18)
        report = dag.report()
        lines = report.split("\n")
        # Find the header, separator, data, and total rows
        header_line = next(ln for ln in lines if "Gates (U/C)" in ln)
        total_line = next(ln for ln in lines if "TOTAL" in ln)
        # TOTAL row must have the same width as the header row
        assert len(total_line) == len(header_line), (
            f"TOTAL row length {len(total_line)} != header length {len(header_line)}\n"
            f"  header: {header_line!r}\n"
            f"  total:  {total_line!r}"
        )
        # TOTAL row must contain the aggregate gate count (15-char padded)
        assert "TOTAL" in total_line
        assert "|" in total_line


# ---------------------------------------------------------------------------
# _resolve_gate_count code paths
# ---------------------------------------------------------------------------


class TestResolveGateCount:
    """_resolve_gate_count resolves gate count from a sequence pointer."""

    def test_returns_zero_when_helper_unavailable(self):
        """Returns 0 when _sequence_gate_count is None (Cython not built)."""
        with patch("quantum_language.call_graph._sequence_gate_count", None):
            assert _resolve_gate_count(12345) == 0

    def test_returns_zero_for_null_pointer(self):
        """Returns 0 when seq_ptr is 0 (null pointer)."""
        # Even if _sequence_gate_count is available, ptr=0 should return 0
        with patch("quantum_language.call_graph._sequence_gate_count", lambda p: 999):
            assert _resolve_gate_count(0) == 0

    def test_calls_helper_with_valid_pointer(self):
        """Delegates to _sequence_gate_count when helper is available and ptr != 0."""
        sentinel = 42
        with patch(
            "quantum_language.call_graph._sequence_gate_count",
            lambda p: sentinel if p == 7777 else 0,
        ):
            assert _resolve_gate_count(7777) == sentinel
