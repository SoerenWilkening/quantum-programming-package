"""Tests for DAG nodes from automatic uncomputation.

Issue: Quantum_Assembly-e2s

Validates that _run_inverted_on_circuit records an "uncompute" node in the
DAG via record_operation, so that gate costs from auto-uncomputation are
visible in call_graph.aggregate().
"""

import quantum_language as ql
from quantum_language import qint


class TestUncomputeNodeInDAG:
    """Compiled function with temporary qbool produces uncompute DAG node."""

    def test_with_block_temporary_produces_uncompute_node(self):
        """A with block using a comparison creates a temporary qbool that
        gets uncomputed at block exit; the uncompute should appear in DAG."""
        ql.circuit()

        @ql.compile(opt=1)
        def apply_cond(x):
            cond = x == 5
            with cond:
                x += 1
            return x

        a = qint(0, width=4)
        apply_cond(a)

        dag = apply_cond.call_graph
        assert dag is not None

        uncompute_nodes = [n for n in dag.nodes if n.operation_type == "uncompute"]
        assert len(uncompute_nodes) >= 1, (
            f"Expected at least 1 uncompute node in DAG, "
            f"got {len(uncompute_nodes)}. "
            f"All op types: {[n.operation_type for n in dag.nodes]}"
        )

    def test_uncompute_node_has_nonzero_gate_count(self):
        """Uncompute DAG node should have a non-zero gate_count."""
        ql.circuit()

        @ql.compile(opt=1)
        def apply_cond(x):
            cond = x == 5
            with cond:
                x += 1
            return x

        a = qint(0, width=4)
        apply_cond(a)

        dag = apply_cond.call_graph
        uncompute_nodes = [n for n in dag.nodes if n.operation_type == "uncompute"]
        assert len(uncompute_nodes) >= 1
        for n in uncompute_nodes:
            assert n.gate_count > 0, f"Uncompute node gate_count should be > 0, got {n.gate_count}"

    def test_uncompute_node_marked_inverted(self):
        """Uncompute DAG node should have invert=True."""
        ql.circuit()

        @ql.compile(opt=1)
        def apply_cond(x):
            cond = x == 5
            with cond:
                x += 1
            return x

        a = qint(0, width=4)
        apply_cond(a)

        dag = apply_cond.call_graph
        uncompute_nodes = [n for n in dag.nodes if n.operation_type == "uncompute"]
        assert len(uncompute_nodes) >= 1
        for n in uncompute_nodes:
            assert n.invert is True, f"Uncompute node should have invert=True, got {n.invert}"


class TestUncomputeGateCountAgreement:
    """DAG aggregate gate count should account for uncomputation gates."""

    def test_aggregate_gates_includes_uncomputation(self):
        """call_graph.aggregate()['gates'] should include uncompute costs."""
        ql.circuit()

        @ql.compile(opt=1)
        def apply_cond(x):
            cond = x == 5
            with cond:
                x += 1
            return x

        a = qint(0, width=4)
        apply_cond(a)

        dag = apply_cond.call_graph
        assert dag is not None

        agg = dag.aggregate()
        # The total gate count should be positive (includes both forward
        # operations and uncomputation)
        assert agg["gates"] > 0

        # Verify uncompute gates are part of the total
        uncompute_gates = sum(n.gate_count for n in dag.nodes if n.operation_type == "uncompute")
        non_uncompute_gates = sum(
            n.gate_count for n in dag.nodes if n.operation_type != "uncompute" and n.operation_type
        )
        assert agg["gates"] >= uncompute_gates + non_uncompute_gates, (
            f"Aggregate gates ({agg['gates']}) should be >= "
            f"uncompute ({uncompute_gates}) + other ({non_uncompute_gates})"
        )
