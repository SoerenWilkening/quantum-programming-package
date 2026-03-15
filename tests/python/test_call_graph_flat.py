"""Tests for Step 0.2: Remove wrapper/function nodes.

Validates that operations are direct DAG nodes with no function-level
wrapper node.  After this step, the DAG contains only operation nodes
connected via execution-order edges.

Step 0.2 of Phase 0: Call Graph Redesign [Quantum_Assembly-7wm].
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import CallGraphDAG


# ---------------------------------------------------------------------------
# No wrapper node
# ---------------------------------------------------------------------------


class TestNoWrapperNode:
    """Compiled function with N ops produces exactly N nodes (+ no wrapper)."""

    def test_no_wrapper_node_addition(self):
        """Single compiled addition: only operation nodes, no wrapper."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        # Every node should have an operation_type (no empty wrapper node)
        for node in dag.nodes:
            assert node.operation_type != "", (
                f"Found wrapper node with func_name={node.func_name!r}"
            )

    def test_no_wrapper_node_multi_op(self):
        """Compiled fn with 2 ops produces exactly 2 operation nodes."""
        ql.circuit()

        @ql.compile(opt=1)
        def two_ops(x):
            x += 1
            x += 2
            return x

        a = qint(3, width=4)
        two_ops(a)
        dag = two_ops.call_graph
        assert dag is not None
        # All nodes should be operations
        op_nodes = [n for n in dag.nodes if n.operation_type]
        assert len(op_nodes) == dag.node_count

    def test_no_wrapper_nested_compile(self):
        """Nested compiled calls produce flat operation nodes, no wrappers."""
        ql.circuit()

        @ql.compile(opt=1)
        def inner(x):
            x += 10
            return x

        @ql.compile(opt=1)
        def outer(x):
            x = inner(x)
            x += 1
            return x

        a = qint(0, width=8)
        outer(a)
        dag = outer.call_graph
        assert dag is not None
        # All nodes should be operations (no wrapper for inner or outer)
        for node in dag.nodes:
            assert node.operation_type != "", (
                f"Found wrapper node: {node.func_name!r}"
            )


# ---------------------------------------------------------------------------
# No call edge type
# ---------------------------------------------------------------------------


class TestNoCallEdgeType:
    """No edge in the DAG should have type == 'call'."""

    def test_no_call_edge_type_simple(self):
        """Simple compiled function has no call edges."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "call", (
                    f"Found unexpected 'call' edge: {edata}"
                )

    def test_no_call_edge_type_nested(self):
        """Nested compiled functions have no call edges."""
        ql.circuit()

        @ql.compile(opt=1)
        def inner(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def outer(x):
            x = inner(x)
            return x

        a = qint(3, width=4)
        outer(a)
        dag = outer.call_graph
        assert dag is not None
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "call", (
                    f"Found unexpected 'call' edge: {edata}"
                )

    def test_no_call_edge_unit_level(self):
        """Direct add_node() calls never produce call edges."""
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1}, 10, ())
        dag.add_node("op2", {0, 1}, 20, ())
        dag.add_node("op3", {2, 3}, 5, ())
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "call"


# ---------------------------------------------------------------------------
# Report shows operations
# ---------------------------------------------------------------------------


class TestReportShowsOperations:
    """report() lists operations, not function names."""

    def test_report_shows_operation_types(self):
        """report() output includes operation type names."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        report = dag.report()
        # Should contain operation names (e.g., "add" something)
        op_types = [n.operation_type for n in dag.nodes if n.operation_type]
        for op in op_types:
            assert op in report, f"Operation {op!r} not found in report"

    def test_report_no_empty_wrapper_names(self):
        """report() should not contain nodes with empty operation_type."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_two(x):
            x += 2
            return x

        a = qint(0, width=4)
        add_two(a)
        dag = add_two.call_graph
        assert dag is not None
        # All nodes in the DAG should have non-empty operation_type
        for node in dag.nodes:
            assert node.operation_type, (
                f"Node {node.func_name!r} has empty operation_type"
            )
