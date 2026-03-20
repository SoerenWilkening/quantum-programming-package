"""Tests for DAG dual variant gate count fix.

Issue: Quantum_Assembly-yyj
Spec: R16.11

Tests that DAG nodes show BOTH uncontrolled and controlled gate counts
when a compiled function is called in both contexts.
"""

import quantum_language as ql
from quantum_language import qint


class TestDualVariantQFTMode:
    """opt=1 QFT mode (IR path): DAG nodes have both counts after both contexts."""

    def test_uncontrolled_then_controlled_has_both_counts(self):
        """After calling uncontrolled then controlled, DAG nodes have both gate counts."""
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

        # At least some nodes should have BOTH counts non-zero
        add_nodes = [n for n in nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count > 0, (
                f"controlled_gate_count should be > 0, got {node.controlled_gate_count}"
            )

    def test_controlled_then_uncontrolled_has_both_counts(self):
        """After calling controlled then uncontrolled, DAG nodes have both gate counts."""
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
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0
            assert node.controlled_gate_count > 0

    def test_no_duplicate_nodes_with_dual_context(self):
        """Calling in both contexts does NOT create duplicate nodes."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def add_two(x):
            x += 2
            return x

        a = qint(0, width=4)
        b = qint(0, width=4)
        cond = a == 0

        add_two(b)
        n_after_first = add_two.call_graph.node_count

        with cond:
            add_two(b)

        # Should still have the same number of nodes (updated, not duplicated)
        assert add_two.call_graph.node_count == n_after_first


class TestDualVariantToffoliMode:
    """Toffoli mode (record_operation path): proportional dual counts."""

    def test_toffoli_uncontrolled_then_controlled(self):
        """After calling in both contexts, Toffoli nodes have both counts."""
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
                assert node.uncontrolled_gate_count > 0
                # Controlled count should be populated (proportional estimate)
                assert node.controlled_gate_count > 0


class TestDualVariantCoarseNode:
    """Non-opt=1 (coarse node path): dual counts from block/controlled_block on replay."""

    def test_coarse_node_has_dual_counts_on_replay(self):
        """Non-opt=1 replay DAG node has both uncontrolled and controlled counts."""
        ql.circuit()

        @ql.compile(opt=0)
        def add_fn(x, y):
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        # First call: capture (builds DAG from record_operation, single variant)
        add_fn(a, b)
        # Second call: replay (builds coarse node with dual counts)
        add_fn(a, b)

        dag = add_fn.call_graph
        assert dag is not None
        nodes = dag.nodes
        assert len(nodes) > 0

        # The coarse node should have the uncontrolled count
        node = nodes[0]
        assert node.uncontrolled_gate_count > 0, (
            f"coarse node uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
        )
        # Controlled count should also be populated from controlled_block
        assert node.controlled_gate_count > 0, (
            f"coarse node controlled_gate_count should be > 0, got {node.controlled_gate_count}"
        )

    def test_report_no_dash_dash_for_coarse_replay(self):
        """report() should not show '- / -' for non-opt=1 coarse nodes on replay."""
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
        lines = report.split("\n")
        for line in lines:
            # Skip header and total lines
            if "TOTAL" in line or "Gates" in line or "---" in line or not line.strip():
                continue
            if "- / -" in line:
                raise AssertionError(f"report() shows '- / -' for coarse node: {line}")
