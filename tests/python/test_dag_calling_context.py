"""Tests for calling-context DAG tracking of division and comparison ops.

Issue: Quantum_Assembly-n9l (Step 11.6)

Tests:
- test_div_mod_uc_cc — division/modulo in uncontrolled/controlled contexts
- test_comparison_uc_cc — comparison ops (eq, lt, gt, etc.)
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    pop_dag_context,
    push_dag_context,
)

# ---------------------------------------------------------------------------
# test_div_mod_uc_cc — division/modulo calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestDivModUcCc:
    """Division and modulo operations track UC/CC gate counts via calling context."""

    def test_floordiv_cq_uncontrolled(self):
        """a // 3 uncontrolled: divmod_cq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a // 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type == "divmod_cq"]
        assert len(div_nodes) > 0, "Expected at least one divmod_cq node"
        for node in div_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_floordiv_cq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for divmod_cq."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a // 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type == "divmod_cq"]
        for node in div_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_mod_cq_uncontrolled(self):
        """a % 3 uncontrolled: divmod_cq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a % 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type == "divmod_cq"]
        assert len(div_nodes) > 0, "Expected at least one divmod_cq node"
        for node in div_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_floordiv_cq_controlled(self):
        """a // 3 inside with block: divmod_cq node has CC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            cond = a == 7
            with cond:
                _ = a // 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type == "divmod_cq"]
        assert len(div_nodes) > 0, "Expected at least one divmod_cq node"
        # The divmod_cq node should have controlled=True since it ran
        # inside a with block
        ctrl_div = [n for n in div_nodes if n.controlled]
        assert len(ctrl_div) > 0, "Expected controlled divmod_cq node"

    def test_floordiv_cq_no_dash_dash(self):
        """report() does not show '- / -' for divmod operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a // 3
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "divmod" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for divmod: {line}"


# ---------------------------------------------------------------------------
# test_comparison_uc_cc — comparison ops calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestComparisonUcCc:
    """Comparison operations track UC/CC gate counts via calling context."""

    def test_eq_cq_uncontrolled(self):
        """(a == 5) uncontrolled: eq_cq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a == 5
        finally:
            pop_dag_context()
        eq_nodes = [n for n in dag.nodes if n.operation_type == "eq_cq"]
        assert len(eq_nodes) > 0, "Expected at least one eq_cq node"
        for node in eq_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_eq_cq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for eq_cq."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a == 5
        finally:
            pop_dag_context()
        eq_nodes = [n for n in dag.nodes if n.operation_type == "eq_cq"]
        for node in eq_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_eq_cq_controlled(self):
        """(a == 5) inside with block: eq_cq node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(0, width=4)
            cond = a == 3
            with cond:
                _ = b == 5
        finally:
            pop_dag_context()
        eq_nodes = [n for n in dag.nodes if n.operation_type == "eq_cq"]
        ctrl_eq = [n for n in eq_nodes if n.controlled]
        assert len(ctrl_eq) > 0, "Expected controlled eq_cq node"

    def test_eq_cq_no_dash_dash(self):
        """report() does not show '- / -' for eq operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a == 5
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "eq" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for eq: {line}"

    def test_lt_qq_tracks_dag_nodes(self):
        """(a < b) QQ produces DAG nodes with UC gate counts."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            _ = a < b
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from QQ lt comparison"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from lt"

    def test_gt_qq_tracks_dag_nodes(self):
        """(a > b) QQ produces DAG nodes with UC gate counts."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(2, width=4)
            _ = a > b
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from QQ gt comparison"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from gt"

    def test_ne_tracks_dag_nodes(self):
        """(a != 3) produces DAG nodes with gate counts (via eq + not)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = a != 3
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from ne comparison"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from ne"

    def test_le_qq_tracks_dag_nodes(self):
        """(a <= b) QQ produces DAG nodes with UC gate counts."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            _ = a <= b
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from QQ le comparison"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from le"

    def test_ge_qq_tracks_dag_nodes(self):
        """(a >= b) QQ produces DAG nodes with UC gate counts."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(2, width=4)
            _ = a >= b
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from QQ ge comparison"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from ge"
