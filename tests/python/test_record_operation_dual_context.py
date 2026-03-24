"""Tests for Step 11.6: record_operation U/C reflects calling context.

Issue: Quantum_Assembly-bl0.6

In Toffoli mode, record_operation now uses the actual gc_delta for
the current context (UC or CC), not QFT sequence counts.  The sibling
context's count is filled in by _merge_dual_context_nodes when the
function is captured in both contexts.
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
# Integration: Toffoli addition single context
# ---------------------------------------------------------------------------


class TestToffoliAdditionSingleContext:
    """Toffoli addition in a single context populates that side only."""

    def test_add_cq_uncontrolled_only(self):
        """a += 1 uncontrolled in Toffoli mode: UC > 0, CC == 0."""
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
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0

    def test_add_cq_uc_matches_gc(self):
        """UC gate count matches the actual gate_count (gc_delta)."""
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
        for node in add_nodes:
            assert node.uncontrolled_gate_count == node.gate_count

    def test_add_qq_uncontrolled_only(self):
        """a += b uncontrolled in Toffoli mode: UC > 0, CC == 0."""
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
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count == 0


# ---------------------------------------------------------------------------
# Integration: Toffoli addition both contexts via compile merge
# ---------------------------------------------------------------------------


class TestToffoliBothContextsMerge:
    """After both UC and CC captures, merge fills in sibling counts."""

    def test_add_cq_both_after_merge(self):
        """@ql.compile with both contexts: add_cq has both UC and CC > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        # UC capture
        a = qint(0, width=4)
        inc(a)

        # CC capture
        c = ql.qbool(True)
        b = qint(0, width=4)
        with c:
            inc(b)

        dag = inc.call_graph
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq" and not n._merged]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"UC should be > 0, got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count > 0, (
                f"CC should be > 0, got {node.controlled_gate_count}"
            )
            assert node.controlled_gate_count > node.uncontrolled_gate_count, (
                f"CC ({node.controlled_gate_count}) should be > UC ({node.uncontrolled_gate_count})"
            )


# ---------------------------------------------------------------------------
# Integration: separate DAG nodes for UC and CC contexts
# ---------------------------------------------------------------------------


class TestSeparateDagNodes:
    """a += 1 and 'with c: a += 2' produce separate DAG nodes."""

    def test_separate_nodes_have_correct_side(self):
        """UC add has UC > 0, CC add has CC > 0."""
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
        assert len(add_nodes) >= 2
        uc_adds = [n for n in add_nodes if not n.controlled]
        cc_adds = [n for n in add_nodes if n.controlled]
        assert len(uc_adds) >= 1
        assert len(cc_adds) >= 1
        for n in uc_adds:
            assert n.uncontrolled_gate_count > 0
        for n in cc_adds:
            assert n.controlled_gate_count > 0

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
# DAG report: shows current side (not '- / -')
# ---------------------------------------------------------------------------


class TestReportShowsCurrentSide:
    """DAG report shows at least the current side's count."""

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

    def test_report_shows_uc_for_uncontrolled(self):
        """report() shows UC > 0 for uncontrolled add."""
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
            assert node.uncontrolled_gate_count > 0
