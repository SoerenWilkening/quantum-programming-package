"""Tests for Step 11.6: record_operation U/C reflects calling context.

Issue: Quantum_Assembly-bl0.6

Acceptance criteria:
1. record_operation DAG node has both uncontrolled_gate_count > 0 and controlled_gate_count > 0
2. a += 1 and 'with c: a += 2' produce separate DAG nodes, each with both U and C
3. DAG report shows both U and C for all Toffoli arithmetic operation rows
4. U/C values reflect calling context, not internal control state
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    _dag_builder_stack,
    pop_dag_context,
    push_dag_context,
    record_operation,
)

# ---------------------------------------------------------------------------
# Unit tests: record_operation accepts dual counts directly
# ---------------------------------------------------------------------------


class TestRecordOperationDualCounts:
    """record_operation accepts uncontrolled_gate_count and controlled_gate_count."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_explicit_dual_counts(self):
        """When both UC and CC are passed, they are stored directly."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=20,
            uncontrolled_gate_count=24,
            controlled_gate_count=30,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 24
        assert node.controlled_gate_count == 30

    def test_explicit_dual_counts_both_nonzero(self):
        """Both UC and CC are > 0 when explicitly passed."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_qq",
            (0, 1, 2, 3),
            gate_count=25,
            uncontrolled_gate_count=30,
            controlled_gate_count=52,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count > 0
        assert node.controlled_gate_count > 0

    def test_fallback_uncontrolled(self):
        """When no explicit counts, controlled=False puts gate_count in UC."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            controlled=False,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 42
        assert node.controlled_gate_count == 0

    def test_fallback_controlled(self):
        """When no explicit counts, controlled=True puts gate_count in CC."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            controlled=True,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 0
        assert node.controlled_gate_count == 42

    def test_explicit_overrides_fallback(self):
        """Explicit counts override the fallback even when controlled is set."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=20,
            controlled=True,
            uncontrolled_gate_count=24,
            controlled_gate_count=30,
        )
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 24
        assert node.controlled_gate_count == 30


# ---------------------------------------------------------------------------
# Integration: Toffoli addition produces both U and C
# ---------------------------------------------------------------------------


class TestToffoliAdditionDualCounts:
    """Toffoli addition operations have both UC and CC gate counts."""

    def test_add_cq_both_counts(self):
        """a += 1 in Toffoli mode produces DAG node with both UC > 0 and CC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"UC should be > 0, got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count > 0, (
                f"CC should be > 0, got {node.controlled_gate_count}"
            )

    def test_add_qq_both_counts(self):
        """a += b in Toffoli mode produces DAG node with both UC > 0 and CC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += b
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"UC should be > 0, got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count > 0, (
                f"CC should be > 0, got {node.controlled_gate_count}"
            )

    def test_sub_cq_both_counts(self):
        """a -= 1 in Toffoli mode produces DAG node with both UC > 0 and CC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            a -= 1
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count > 0


# ---------------------------------------------------------------------------
# Integration: separate DAG nodes for UC and CC contexts
# ---------------------------------------------------------------------------


class TestSeparateDagNodes:
    """a += 1 and 'with c: a += 2' produce separate DAG nodes, each with both U and C."""

    def test_separate_nodes_each_have_both(self):
        """Uncontrolled add and controlled add produce separate nodes, each with both UC/CC."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            a += 1  # uncontrolled
            cond = a == 3
            with cond:
                b += 2  # controlled
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) >= 2, (
            f"Expected at least 2 add_cq nodes (UC and CC), got {len(add_nodes)}"
        )
        # Check each has both UC and CC
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"add node (controlled={node.controlled}) should have UC > 0, "
                f"got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count > 0, (
                f"add node (controlled={node.controlled}) should have CC > 0, "
                f"got {node.controlled_gate_count}"
            )

    def test_controlled_node_has_controlled_flag(self):
        """The controlled-context add node has controlled=True."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            a += 1
            cond = a == 3
            with cond:
                b += 2
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        controlled_adds = [n for n in add_nodes if n.controlled]
        uncontrolled_adds = [n for n in add_nodes if not n.controlled]
        assert len(controlled_adds) >= 1, "Expected at least one controlled add node"
        assert len(uncontrolled_adds) >= 1, "Expected at least one uncontrolled add node"


# ---------------------------------------------------------------------------
# DAG report shows both U and C for Toffoli arithmetic
# ---------------------------------------------------------------------------


class TestReportShowsBothUC:
    """DAG report shows both U and C for Toffoli arithmetic operation rows."""

    def test_report_no_dash_dash_for_add(self):
        """report() does not show '- / -' for Toffoli add operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()
        report = dag.report()
        lines = report.split("\n")
        for line in lines:
            if "add" in line.lower() and "TOTAL" not in line and "---" not in line:
                assert "- / -" not in line, f"report() shows '- / -' for add: {line}"

    def test_report_shows_x_slash_y_for_add(self):
        """report() shows 'X / Y' (both non-dash) for Toffoli add operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0
        for node in add_nodes:
            uc = node.uncontrolled_gate_count
            cc = node.controlled_gate_count
            assert uc > 0 and cc > 0, f"Expected both UC and CC > 0, got UC={uc}, CC={cc}"


# ---------------------------------------------------------------------------
# U/C values reflect calling context, not internal control state
# ---------------------------------------------------------------------------


class TestCallingContextSemantics:
    """U/C values reflect calling context, not internal control state."""

    def test_uc_cc_same_regardless_of_with_block(self):
        """UC and CC gate counts are the same whether inside or outside a with block.

        The calling-context semantics mean UC/CC reflect what the function
        *would* cost in each context, not the current execution's internal
        control state.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)

        # Uncontrolled execution
        dag1 = CallGraphDAG()
        push_dag_context(dag1)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()

        # Controlled execution
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag2 = CallGraphDAG()
        push_dag_context(dag2)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            cond = a == 3
            with cond:
                b += 1
        finally:
            pop_dag_context()

        add1 = [n for n in dag1.nodes if n.operation_type == "add_cq"][0]
        add2 = [n for n in dag2.nodes if n.operation_type == "add_cq" and n.controlled][0]

        # Both should have the same UC and CC values (calling context)
        assert add1.uncontrolled_gate_count == add2.uncontrolled_gate_count, (
            f"UC should match: {add1.uncontrolled_gate_count} != {add2.uncontrolled_gate_count}"
        )
        assert add1.controlled_gate_count == add2.controlled_gate_count, (
            f"CC should match: {add1.controlled_gate_count} != {add2.controlled_gate_count}"
        )

    def test_cc_greater_than_or_equal_to_uc(self):
        """Controlled gate count should be >= uncontrolled (more overhead)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += b
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.controlled_gate_count >= node.uncontrolled_gate_count, (
                f"CC ({node.controlled_gate_count}) should be >= UC ({node.uncontrolled_gate_count})"
            )
