"""Tests for calling-context DAG tracking of arithmetic ops (add, mul).

Issue: Quantum_Assembly-4ji (Step 11.4) — arithmetic ops calling-context cleanup

Tests:
- test_add_qq_uc_cc — quantum-quantum add in uncontrolled/controlled contexts
- test_mul_cq_uc_cc — classical multiply
- test_mul_qq_uc_cc — quantum-quantum multiply
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    pop_dag_context,
    push_dag_context,
)

# ---------------------------------------------------------------------------
# test_add_qq_uc_cc — quantum-quantum add calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestAddQqUcCc:
    """QQ addition tracks UC/CC gate counts via calling context."""

    def test_add_qq_uncontrolled(self):
        """(a + b) uncontrolled: add_qq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a + b
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        assert len(add_nodes) > 0, "Expected at least one add_qq node"
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_add_qq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for add_qq."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a + b
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        for node in add_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_add_qq_controlled(self):
        """(c += b) inside with block: add_qq node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            c = qint(0, width=4)
            cond = a == 3
            with cond:
                c += b
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        ctrl_add = [n for n in add_nodes if n.controlled]
        assert len(ctrl_add) > 0, "Expected controlled add_qq node"

    def test_add_qq_no_dash_dash(self):
        """report() does not show '- / -' for add_qq operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a + b
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "add_qq" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for add_qq: {line}"


# ---------------------------------------------------------------------------
# test_mul_cq_uc_cc — classical multiply calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestMulCqUcCc:
    """CQ multiplication tracks UC/CC gate counts via calling context."""

    def test_mul_cq_uncontrolled(self):
        """(a * 3) uncontrolled: mul_cq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a * 3
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_cq"]
        assert len(mul_nodes) > 0, "Expected at least one mul_cq node"
        for node in mul_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_mul_cq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for mul_cq."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a * 3
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_cq"]
        for node in mul_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_mul_cq_controlled(self):
        """(a * 3) inside with block: mul_cq node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(0, width=4)
            cond = a == 3
            with cond:
                _ = b * 3
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_cq"]
        ctrl_mul = [n for n in mul_nodes if n.controlled]
        assert len(ctrl_mul) > 0, "Expected controlled mul_cq node"

    def test_mul_cq_no_dash_dash(self):
        """report() does not show '- / -' for mul_cq operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a * 3
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "mul_cq" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for mul_cq: {line}"


# ---------------------------------------------------------------------------
# test_mul_qq_uc_cc — quantum-quantum multiply calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestMulQqUcCc:
    """QQ multiplication tracks UC/CC gate counts via calling context."""

    def test_mul_qq_uncontrolled(self):
        """(a * b) uncontrolled: mul_qq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a * b
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_qq"]
        assert len(mul_nodes) > 0, "Expected at least one mul_qq node"
        for node in mul_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_mul_qq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for mul_qq."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a * b
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_qq"]
        for node in mul_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_mul_qq_controlled(self):
        """(a * b) inside with block: mul_qq node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            cond = a == 3
            with cond:
                _ = a * b
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_qq"]
        ctrl_mul = [n for n in mul_nodes if n.controlled]
        assert len(ctrl_mul) > 0, "Expected controlled mul_qq node"

    def test_mul_qq_no_dash_dash(self):
        """report() does not show '- / -' for mul_qq operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            _ = a * b
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "mul_qq" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for mul_qq: {line}"
