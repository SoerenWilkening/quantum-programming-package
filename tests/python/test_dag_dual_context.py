"""Tests for DAG report dual-context display.

Issue: Quantum_Assembly-83g

Tests:
1. test_report_uc_only — only uncontrolled compiled: shows 16 / - format
2. test_report_both_contexts — both compiled: shows 16 / 28 with correct values
3. test_report_dual_totals — totals row shows separate U and C sums
4. test_report_dual_depth — depth column shows dual values
5. test_report_three_ops_three_rows — foo with 3 add_cq ops displays 3 rows, not 6
6. test_aggregate_dual — aggregate() returns dict with gates_uc, gates_cc, depth_uc, depth_cc
"""

from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _format_dual,
    _format_dual_gates,
)

# ---------------------------------------------------------------------------
# test_report_uc_only
# ---------------------------------------------------------------------------


class TestReportUCOnly:
    """Only uncontrolled compiled: shows X / - format."""

    def test_report_uc_only(self):
        """Report shows uncontrolled value and '-' for controlled."""
        dag = CallGraphDAG()
        dag.add_node(
            "add_cq",
            {0, 1, 2},
            16,
            (),
            uncontrolled_gate_count=16,
            controlled_gate_count=0,
            uncontrolled_depth=5,
            controlled_depth=0,
            uncontrolled_t_count=7,
            controlled_t_count=0,
            operation_type="add_cq",
        )
        report = dag.report()
        assert "16 / -" in report
        assert "5 / -" in report
        assert "7 / -" in report

    def test_report_uc_only_depth_format(self):
        """Depth column shows 'X / -' when only uncontrolled available."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0},
            10,
            (),
            uncontrolled_depth=12,
            controlled_depth=0,
        )
        report = dag.report()
        assert "12 / -" in report

    def test_report_uc_only_tcount_format(self):
        """T-count column shows 'X / -' when only uncontrolled available."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0},
            10,
            (),
            uncontrolled_t_count=21,
            controlled_t_count=0,
        )
        report = dag.report()
        assert "21 / -" in report


# ---------------------------------------------------------------------------
# test_report_both_contexts
# ---------------------------------------------------------------------------


class TestReportBothContexts:
    """Both compiled: shows X / Y with correct values."""

    def test_report_both_contexts(self):
        """Report shows both uncontrolled and controlled values."""
        dag = CallGraphDAG()
        dag.add_node(
            "add_cq",
            {0, 1, 2},
            16,
            (),
            uncontrolled_gate_count=16,
            controlled_gate_count=28,
            uncontrolled_depth=5,
            controlled_depth=8,
            uncontrolled_t_count=7,
            controlled_t_count=14,
            operation_type="add_cq",
        )
        report = dag.report()
        assert "16 / 28" in report
        assert "5 / 8" in report
        assert "7 / 14" in report

    def test_report_controlled_only(self):
        """Report shows '- / Y' when only controlled is available."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0, 1},
            28,
            (),
            uncontrolled_gate_count=0,
            controlled_gate_count=28,
            uncontrolled_depth=0,
            controlled_depth=8,
            uncontrolled_t_count=0,
            controlled_t_count=14,
        )
        report = dag.report()
        assert "- / 28" in report
        assert "- / 8" in report
        assert "- / 14" in report


# ---------------------------------------------------------------------------
# test_report_dual_totals
# ---------------------------------------------------------------------------


class TestReportDualTotals:
    """Totals row shows separate U and C sums."""

    def test_report_dual_totals(self):
        """TOTAL row shows dual gate/depth/T-count sums."""
        dag = CallGraphDAG()
        dag.add_node(
            "op1",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=10,
            controlled_gate_count=20,
            uncontrolled_depth=3,
            controlled_depth=5,
            uncontrolled_t_count=7,
            controlled_t_count=14,
            operation_type="op1",
        )
        dag.add_node(
            "op2",
            {2, 3},
            15,
            (),
            uncontrolled_gate_count=15,
            controlled_gate_count=25,
            uncontrolled_depth=4,
            controlled_depth=6,
            uncontrolled_t_count=0,
            controlled_t_count=7,
            operation_type="op2",
        )
        report = dag.report()
        lines = report.split("\n")
        total_line = next(ln for ln in lines if "TOTAL" in ln)
        # gates_uc=25, gates_cc=45
        assert "25 / 45" in total_line
        # T-count: uc=7, cc=21
        assert "7 / 21" in total_line

    def test_report_total_row_aligned(self):
        """TOTAL row has same width as header."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0},
            10,
            (),
            uncontrolled_gate_count=10,
            controlled_gate_count=20,
        )
        report = dag.report()
        lines = report.split("\n")
        header_line = next(ln for ln in lines if "Gates (U/C)" in ln)
        total_line = next(ln for ln in lines if "TOTAL" in ln)
        assert len(total_line) == len(header_line)


# ---------------------------------------------------------------------------
# test_report_dual_depth
# ---------------------------------------------------------------------------


class TestReportDualDepth:
    """Depth column shows dual values."""

    def test_report_dual_depth(self):
        """Depth column displays dual U/C format."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0, 1},
            10,
            (),
            uncontrolled_depth=5,
            controlled_depth=8,
            operation_type="fn",
        )
        report = dag.report()
        assert "Depth (U/C)" in report
        assert "5 / 8" in report

    def test_report_header_has_depth_uc(self):
        """report() header contains 'Depth (U/C)'."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, ())
        report = dag.report()
        assert "Depth (U/C)" in report

    def test_report_header_has_tcount_uc(self):
        """report() header contains 'T-count (U/C)'."""
        dag = CallGraphDAG()
        dag.add_node("fn", {0}, 10, ())
        report = dag.report()
        assert "T-count (U/C)" in report


# ---------------------------------------------------------------------------
# test_report_three_ops_three_rows
# ---------------------------------------------------------------------------


class TestReportThreeOpsThreeRows:
    """foo with 3 add_cq ops displays 3 rows, not 6."""

    def test_three_ops_three_rows(self):
        """Three operations produce exactly three data rows in report."""
        dag = CallGraphDAG()
        for i in range(3):
            dag.add_node(
                "add_cq",
                {i * 2, i * 2 + 1},
                10,
                (),
                uncontrolled_gate_count=10,
                controlled_gate_count=15,
                uncontrolled_depth=3,
                controlled_depth=5,
                operation_type="add_cq",
            )
        report = dag.report()
        lines = report.split("\n")
        # Find data rows (between separator lines)
        sep_indices = [i for i, ln in enumerate(lines) if ln.startswith("---")]
        assert len(sep_indices) >= 2
        data_lines = lines[sep_indices[0] + 1 : sep_indices[1]]
        assert len(data_lines) == 3, f"Expected 3 data rows, got {len(data_lines)}: {data_lines}"

    def test_merged_nodes_not_in_report(self):
        """Merged nodes (from dual context) do not appear as extra rows."""
        dag = CallGraphDAG()
        # Simulate first context: 3 nodes
        for i in range(3):
            dag.add_node(
                "add_cq",
                {i * 2, i * 2 + 1},
                10,
                (),
                uncontrolled_gate_count=10,
                controlled_gate_count=0,
                operation_type="add_cq",
            )
        # Simulate second context: 3 nodes that get merged
        for i in range(3):
            idx = dag.add_node(
                "add_cq",
                {i * 2, i * 2 + 1},
                15,
                (),
                uncontrolled_gate_count=0,
                controlled_gate_count=15,
                operation_type="add_cq",
            )
            dag._nodes[idx]._merged = True
            # Merge counts into original
            dag._nodes[i].controlled_gate_count = 15

        report = dag.report()
        lines = report.split("\n")
        sep_indices = [i for i, ln in enumerate(lines) if ln.startswith("---")]
        data_lines = lines[sep_indices[0] + 1 : sep_indices[1]]
        assert len(data_lines) == 3, f"Expected 3 data rows (merged), got {len(data_lines)}"
        # Each row should show both values
        for row in data_lines:
            assert "10 / 15" in row


# ---------------------------------------------------------------------------
# test_aggregate_dual
# ---------------------------------------------------------------------------


class TestAggregateDual:
    """aggregate() returns dict with gates_uc, gates_cc, depth_uc, depth_cc."""

    def test_aggregate_dual_keys(self):
        """aggregate() returns all dual keys."""
        dag = CallGraphDAG()
        dag.add_node(
            "fn",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=10,
            controlled_gate_count=20,
            uncontrolled_depth=3,
            controlled_depth=5,
            uncontrolled_t_count=7,
            controlled_t_count=14,
        )
        agg = dag.aggregate()
        assert "gates_uc" in agg
        assert "gates_cc" in agg
        assert "depth_uc" in agg
        assert "depth_cc" in agg
        assert "t_count_uc" in agg
        assert "t_count_cc" in agg

    def test_aggregate_dual_values(self):
        """aggregate() computes correct per-context sums."""
        dag = CallGraphDAG()
        dag.add_node(
            "op1",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=10,
            controlled_gate_count=20,
            uncontrolled_depth=3,
            controlled_depth=5,
            uncontrolled_t_count=7,
            controlled_t_count=14,
        )
        dag.add_node(
            "op2",
            {2, 3},
            15,
            (),
            uncontrolled_gate_count=15,
            controlled_gate_count=25,
            uncontrolled_depth=4,
            controlled_depth=6,
            uncontrolled_t_count=3,
            controlled_t_count=7,
        )
        agg = dag.aggregate()
        assert agg["gates_uc"] == 25
        assert agg["gates_cc"] == 45
        assert agg["t_count_uc"] == 10
        assert agg["t_count_cc"] == 21
        # depth: max per group. op1 and op2 on different qubits = same group
        # if disjoint, depth_uc = max(3,4) = 4, depth_cc = max(5,6) = 6
        # Since qubits are disjoint, they're in separate parallel groups:
        # depth_uc = 3 + 4 = 7... wait, parallel groups means independent.
        # Actually: parallel_groups returns connected components. Disjoint
        # qubits = separate groups. depth = sum of per-group max depths.
        # group1: op1 (depth_uc=3), group2: op2 (depth_uc=4)
        # total depth_uc = 3 + 4 = 7
        assert agg["depth_uc"] == 7
        assert agg["depth_cc"] == 11

    def test_aggregate_dual_empty(self):
        """aggregate() returns zeros for empty DAG."""
        dag = CallGraphDAG()
        agg = dag.aggregate()
        assert agg["gates_uc"] == 0
        assert agg["gates_cc"] == 0
        assert agg["depth_uc"] == 0
        assert agg["depth_cc"] == 0
        assert agg["t_count_uc"] == 0
        assert agg["t_count_cc"] == 0

    def test_aggregate_skips_merged_nodes(self):
        """aggregate() excludes merged (duplicate) nodes."""
        dag = CallGraphDAG()
        dag.add_node(
            "op1",
            {0, 1},
            10,
            (),
            uncontrolled_gate_count=10,
            controlled_gate_count=20,
        )
        # Merged duplicate
        idx = dag.add_node(
            "op1",
            {0, 1},
            20,
            (),
            uncontrolled_gate_count=0,
            controlled_gate_count=20,
        )
        dag._nodes[idx]._merged = True

        agg = dag.aggregate()
        assert agg["gates_uc"] == 10
        assert agg["gates_cc"] == 20
        # gate_count total should only count non-merged
        assert agg["gates"] == 10


# ---------------------------------------------------------------------------
# _format_dual backward compatibility and generalization
# ---------------------------------------------------------------------------


class TestFormatDual:
    """_format_dual is generalized; _format_dual_gates is backward-compatible alias."""

    def test_format_dual_both(self):
        assert _format_dual(24, 18) == "24 / 18"

    def test_format_dual_uc_only(self):
        assert _format_dual(24, 0) == "24 / -"

    def test_format_dual_cc_only(self):
        assert _format_dual(0, 18) == "- / 18"

    def test_format_dual_neither(self):
        assert _format_dual(0, 0) == "- / -"

    def test_format_dual_gates_alias(self):
        """_format_dual_gates still works as before."""
        assert _format_dual_gates(24, 18) == "24 / 18"
        assert _format_dual_gates is _format_dual


# ---------------------------------------------------------------------------
# DAGNode new fields
# ---------------------------------------------------------------------------


class TestDAGNodeDualFields:
    """DAGNode has uncontrolled/controlled depth and T-count fields."""

    def test_new_fields_in_slots(self):
        assert "uncontrolled_depth" in DAGNode.__slots__
        assert "controlled_depth" in DAGNode.__slots__
        assert "uncontrolled_t_count" in DAGNode.__slots__
        assert "controlled_t_count" in DAGNode.__slots__

    def test_new_fields_default_zero(self):
        node = DAGNode("f", {0}, 10, ())
        assert node.uncontrolled_depth == 0
        assert node.controlled_depth == 0
        assert node.uncontrolled_t_count == 0
        assert node.controlled_t_count == 0

    def test_new_fields_stored(self):
        node = DAGNode(
            "f",
            {0},
            10,
            (),
            uncontrolled_depth=5,
            controlled_depth=8,
            uncontrolled_t_count=7,
            controlled_t_count=14,
        )
        assert node.uncontrolled_depth == 5
        assert node.controlled_depth == 8
        assert node.uncontrolled_t_count == 7
        assert node.controlled_t_count == 14

    def test_merged_flag_default(self):
        node = DAGNode("f", {0}, 10, ())
        assert node._merged is False
