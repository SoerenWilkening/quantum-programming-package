"""Tests for calling-context DAG tracking of bitwise, division, and comparison ops.

Issues:
- Quantum_Assembly-9p6 (Step 11.5) — bitwise operations
- Quantum_Assembly-n9l (Step 11.6) — division and comparison operations

Tests:
- test_xor_uc_cc — XOR in uncontrolled/controlled contexts
- test_and_or_uc_cc — AND/OR bitwise ops
- test_shift_uc_cc — left/right shift ops
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


# ---------------------------------------------------------------------------
# test_xor_uc_cc — XOR calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestXorUcCc:
    """XOR operations track UC/CC gate counts via calling context."""

    def test_xor_qq_uncontrolled(self):
        """(a ^ b) uncontrolled: xor node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a ^ b
        finally:
            pop_dag_context()
        xor_nodes = [n for n in dag.nodes if n.operation_type == "xor"]
        assert len(xor_nodes) > 0, "Expected at least one xor node"
        for node in xor_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_xor_qq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for xor."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a ^ b
        finally:
            pop_dag_context()
        xor_nodes = [n for n in dag.nodes if n.operation_type == "xor"]
        for node in xor_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_xor_cq_uncontrolled(self):
        """(a ^ 5) uncontrolled: xor node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a ^ 5
        finally:
            pop_dag_context()
        xor_nodes = [n for n in dag.nodes if n.operation_type == "xor"]
        assert len(xor_nodes) > 0, "Expected at least one xor node"
        for node in xor_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_ixor_cq_uncontrolled(self):
        """(a ^= 5) uncontrolled: ixor_cq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            a ^= 5
        finally:
            pop_dag_context()
        ixor_nodes = [n for n in dag.nodes if n.operation_type == "ixor_cq"]
        assert len(ixor_nodes) > 0, "Expected at least one ixor_cq node"
        for node in ixor_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_ixor_qq_uncontrolled(self):
        """(a ^= b) uncontrolled: ixor_qq node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            a ^= b
        finally:
            pop_dag_context()
        ixor_nodes = [n for n in dag.nodes if n.operation_type == "ixor_qq"]
        assert len(ixor_nodes) > 0, "Expected at least one ixor_qq node"
        for node in ixor_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_xor_no_dash_dash(self):
        """report() does not show '- / -' for xor operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a ^ b
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "xor" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for xor: {line}"


# ---------------------------------------------------------------------------
# test_and_or_uc_cc — AND/OR calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestAndOrUcCc:
    """AND and OR operations track UC/CC gate counts via calling context."""

    def test_and_qq_uncontrolled(self):
        """(a & b) uncontrolled: and node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a & b
        finally:
            pop_dag_context()
        and_nodes = [n for n in dag.nodes if n.operation_type == "and"]
        assert len(and_nodes) > 0, "Expected at least one and node"
        for node in and_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_and_qq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for and."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a & b
        finally:
            pop_dag_context()
        and_nodes = [n for n in dag.nodes if n.operation_type == "and"]
        for node in and_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_and_cq_uncontrolled(self):
        """(a & 5) uncontrolled: and node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a & 5
        finally:
            pop_dag_context()
        and_nodes = [n for n in dag.nodes if n.operation_type == "and"]
        assert len(and_nodes) > 0, "Expected at least one and node"
        for node in and_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_or_qq_uncontrolled(self):
        """(a | b) uncontrolled: or node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a | b
        finally:
            pop_dag_context()
        or_nodes = [n for n in dag.nodes if n.operation_type == "or"]
        assert len(or_nodes) > 0, "Expected at least one or node"
        for node in or_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_or_qq_uc_matches_gc(self):
        """UC gate count matches actual gate_count for or."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a | b
        finally:
            pop_dag_context()
        or_nodes = [n for n in dag.nodes if n.operation_type == "or"]
        for node in or_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_or_cq_uncontrolled(self):
        """(a | 3) uncontrolled: or node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = a | 3
        finally:
            pop_dag_context()
        or_nodes = [n for n in dag.nodes if n.operation_type == "or"]
        assert len(or_nodes) > 0, "Expected at least one or node"
        for node in or_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_not_uncontrolled(self):
        """~a uncontrolled: not node has UC > 0, CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = ~a
        finally:
            pop_dag_context()
        not_nodes = [n for n in dag.nodes if n.operation_type == "not"]
        assert len(not_nodes) > 0, "Expected at least one not node"
        for node in not_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_not_uc_matches_gc(self):
        """UC gate count matches actual gate_count for not."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = ~a
        finally:
            pop_dag_context()
        not_nodes = [n for n in dag.nodes if n.operation_type == "not"]
        for node in not_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_not_controlled(self):
        """~a inside with block: not node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(0, width=4)
            cond = a == 5
            with cond:
                _ = ~b
        finally:
            pop_dag_context()
        not_nodes = [n for n in dag.nodes if n.operation_type == "not"]
        ctrl_not = [n for n in not_nodes if n.controlled]
        assert len(ctrl_not) > 0, "Expected controlled not node"

    def test_and_or_no_dash_dash(self):
        """report() does not show '- / -' for and/or operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            b = qint(3, width=4)
            _ = a & b
            _ = a | b
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if (
                ("and" in line.lower() or "or" in line.lower())
                and "TOTAL" not in line
                and "---" not in line
            ):
                assert "- / -" not in line, f"report() shows '- / -' for and/or: {line}"


# ---------------------------------------------------------------------------
# test_shift_uc_cc — left/right shift calling-context DAG tracking
# ---------------------------------------------------------------------------


class TestShiftUcCc:
    """Shift operations track UC/CC gate counts via calling context."""

    def test_lshift_uncontrolled(self):
        """(a << 2) uncontrolled: produces DAG nodes with UC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a << 2
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from lshift"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from lshift"

    def test_rshift_uncontrolled(self):
        """(a >> 2) uncontrolled: produces DAG nodes with UC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a >> 1
        finally:
            pop_dag_context()
        assert len(dag.nodes) > 0, "Expected DAG nodes from rshift"
        total_uc = sum(n.uncontrolled_gate_count for n in dag.nodes)
        assert total_uc > 0, "Expected non-zero UC gate count from rshift"

    def test_lshift_no_cc(self):
        """Left shift uncontrolled: all CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a << 1
        finally:
            pop_dag_context()
        total_cc = sum(n.controlled_gate_count for n in dag.nodes)
        assert total_cc == 0, "Expected CC == 0 for uncontrolled lshift"

    def test_rshift_no_cc(self):
        """Right shift uncontrolled: all CC == 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a >> 1
        finally:
            pop_dag_context()
        total_cc = sum(n.controlled_gate_count for n in dag.nodes)
        assert total_cc == 0, "Expected CC == 0 for uncontrolled rshift"
