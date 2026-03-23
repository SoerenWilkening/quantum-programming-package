"""Tests for DAG variant gate counts with per-context cache.

Issue: Quantum_Assembly-yyj (updated by Quantum_Assembly-czb)

Tests that DAG nodes correctly record gate counts for the context in
which they were captured. With per-context caching, each control context
produces its own cache entry and its own DAG nodes.
"""

import quantum_language as ql
from quantum_language import qint


class TestDualVariantQFTMode:
    """opt=1 QFT mode (IR path): separate DAG nodes per context."""

    def test_uncontrolled_then_controlled_creates_nodes(self):
        """Calling uncontrolled then controlled creates DAG nodes for both."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode produces IR

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(0, width=4)
        b = qint(0, width=4)
        cond = a == 0

        # First call: uncontrolled
        inc(b)
        # Second call: controlled
        with cond:
            inc(b)

        dag = inc.call_graph
        assert dag is not None
        nodes = dag.nodes
        assert len(nodes) > 0

        # Nodes should exist from the capture(s)
        add_nodes = [n for n in nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0

    def test_controlled_then_uncontrolled_creates_nodes(self):
        """Calling controlled then uncontrolled creates DAG nodes for both."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def dec(x):
            x -= 1
            return x

        a = qint(0, width=4)
        b = qint(5, width=4)
        cond = a == 0

        # First call: controlled
        with cond:
            dec(b)
        # Second call: uncontrolled
        dec(b)

        dag = dec.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0


class TestDualVariantToffoliMode:
    """Toffoli mode (record_operation path): per-context DAG nodes."""

    def test_toffoli_uncontrolled_then_controlled(self):
        """Calling in both contexts creates DAG nodes for both."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def toffoli_inc(x):
            x += 1
            return x

        a = qint(0, width=4)
        b = qint(0, width=4)
        cond = a == 0

        # First call: uncontrolled
        toffoli_inc(b)
        # Second call: controlled
        with cond:
            toffoli_inc(b)

        dag = toffoli_inc.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        if add_nodes:
            for node in add_nodes:
                # At least one variant's count should be populated
                assert node.uncontrolled_gate_count > 0 or node.controlled_gate_count > 0


class TestCoarseNode:
    """Non-opt=1 (coarse node path): gate counts on replay."""

    def test_coarse_node_has_gate_count_on_replay(self):
        """Non-opt=1 replay DAG node has gate count."""
        ql.circuit()

        @ql.compile(opt=0)
        def add_fn(x, y):
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        # First call: capture (builds DAG from record_operation)
        add_fn(a, b)
        # Second call: replay (builds coarse node)
        add_fn(a, b)

        dag = add_fn.call_graph
        assert dag is not None
        nodes = dag.nodes
        assert len(nodes) > 0

        # The coarse node should have a gate count
        node = nodes[0]
        assert node.gate_count > 0, f"coarse node gate_count should be > 0, got {node.gate_count}"

    def test_coarse_node_report_renders(self):
        """report() renders without errors for non-opt=1 coarse nodes on replay."""
        ql.circuit()

        @ql.compile(opt=0)
        def inc_fn(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc_fn(a)  # capture
        inc_fn(a)  # replay (coarse node path)

        dag = inc_fn.call_graph
        assert dag is not None
        report = dag.report()
        # Report should contain the function name
        assert "inc_fn" in report
