"""Tests for DAG nodes for nested compiled function calls.

Issue: Quantum_Assembly-eiq

Validates that compiled function calls within another compiled function
appear as named nodes in the outer function's DAG with correct gate counts,
and that inner operations stay in the inner function's DAG.
"""

import quantum_language as ql
from quantum_language import qint


class TestThreeFooCallsThreeNodes:
    """main calling foo 3x produces 3 foo DAG nodes."""

    def test_three_foo_calls_three_nodes(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a, b):
            a += 1
            a += 2
            a += 3

        @ql.compile(opt=1)
        def main(a, b):
            foo(a, b)
            foo(a, b)
            foo(a, b)

        a = qint(0, width=4)
        b = qint(0, width=4)
        main(a, b)

        dag = main.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 3, f"Expected 3 foo nodes in main's DAG, got {len(foo_nodes)}"

    def test_foo_nodes_are_call_nodes(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def main(a):
            foo(a)
            foo(a)

        a = qint(0, width=4)
        main(a)

        dag = main.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 2
        for node in foo_nodes:
            assert node.is_call_node, "foo DAG nodes should have is_call_node=True"


class TestFooNodeGateCount:
    """Each foo node has foo's gate count."""

    def test_foo_node_gate_count(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1
            a += 2
            a += 3

        @ql.compile(opt=1)
        def main(a):
            foo(a)
            foo(a)
            foo(a)

        a = qint(0, width=4)
        main(a)

        dag = main.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 3

        # All foo nodes should have the same gate count (foo's total)
        gate_counts = [n.gate_count for n in foo_nodes]
        assert all(gc > 0 for gc in gate_counts), (
            f"All foo nodes should have gate_count > 0, got {gate_counts}"
        )
        assert len(set(gate_counts)) == 1, (
            f"All foo nodes should have the same gate count, got {gate_counts}"
        )


class TestPrecompiledFooStillShowsNodes:
    """foo compiled before main still produces foo nodes in main's DAG."""

    def test_precompiled_foo_still_shows_nodes(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1
            a += 2

        # Pre-compile foo by calling it before main
        a = qint(0, width=4)
        foo(a)

        @ql.compile(opt=1)
        def main(a):
            foo(a)
            foo(a)
            foo(a)

        main(a)

        dag = main.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 3, (
            f"Expected 3 foo nodes even with pre-compiled foo, got {len(foo_nodes)}"
        )
        for node in foo_nodes:
            assert node.gate_count > 0, (
                f"Pre-compiled foo node should have gate_count > 0, got {node.gate_count}"
            )


class TestNestedCallReportTotals:
    """Report totals account for all foo calls (3x foo gate count)."""

    def test_nested_call_report_totals(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def main(a):
            foo(a)
            foo(a)
            foo(a)

        a = qint(0, width=4)
        main(a)

        dag = main.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 3

        # Total gate count should be 3x a single foo's gate count
        single_gc = foo_nodes[0].gate_count
        total_gc = sum(n.gate_count for n in foo_nodes)
        assert total_gc == 3 * single_gc, (
            f"Total gate count should be 3 * {single_gc} = {3 * single_gc}, got {total_gc}"
        )

        # Aggregate should reflect the total
        agg = dag.aggregate()
        assert agg["gates"] >= total_gc, (
            f"Aggregate gates should be >= {total_gc}, got {agg['gates']}"
        )


class TestInnerOpsNotInOuterDag:
    """main's DAG does not contain cq_add nodes from foo."""

    def test_inner_ops_not_in_outer_dag(self):
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1
            a += 2
            a += 3

        @ql.compile(opt=1)
        def main(a):
            foo(a)
            foo(a)

        a = qint(0, width=4)
        main(a)

        dag = main.call_graph
        assert dag is not None

        # main's DAG should NOT contain add_cq operation nodes
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) == 0, (
            f"main's DAG should not contain add operation nodes, found {len(add_nodes)}: "
            f"{[n.operation_type for n in add_nodes]}"
        )

        # main's DAG should only contain foo call nodes
        foo_nodes = [n for n in dag.nodes if n.func_name == "foo"]
        assert len(foo_nodes) == 2
        assert dag.node_count == 2, (
            f"main's DAG should only have 2 nodes (foo calls), got {dag.node_count}"
        )
