"""Tests for Step 0.4: Graph immutability after capture.

Validates that after capture completes, the call graph is frozen.
Attempting to add nodes after freeze raises RuntimeError.
Replay reads the graph but never modifies it.

Step 0.4 of Phase 0: Call Graph Redesign [Quantum_Assembly-488].
"""

import pytest

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import CallGraphDAG

# ---------------------------------------------------------------------------
# Freeze mechanism unit tests
# ---------------------------------------------------------------------------


class TestFreezeMechanism:
    """Tests for the _frozen flag and freeze() method."""

    def test_default_not_frozen(self):
        """DAG starts unfrozen."""
        dag = CallGraphDAG()
        assert not dag.frozen

    def test_freeze_sets_flag(self):
        """freeze() sets _frozen to True."""
        dag = CallGraphDAG()
        dag.freeze()
        assert dag.frozen

    def test_freeze_idempotent(self):
        """Calling freeze() multiple times is safe."""
        dag = CallGraphDAG()
        dag.freeze()
        dag.freeze()
        assert dag.frozen

    def test_add_node_after_freeze_raises(self):
        """add_node() raises RuntimeError on frozen DAG."""
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1}, 10, ())
        dag.freeze()
        with pytest.raises(RuntimeError, match="frozen"):
            dag.add_node("op2", {0, 1}, 5, ())

    def test_add_node_before_freeze_works(self):
        """add_node() works before freeze."""
        dag = CallGraphDAG()
        dag.add_node("op1", {0}, 1, ())
        dag.add_node("op2", {1}, 1, ())
        assert dag.node_count == 2
        dag.freeze()
        assert dag.node_count == 2


# ---------------------------------------------------------------------------
# Read-only methods still work after freeze
# ---------------------------------------------------------------------------


class TestReadAfterFreeze:
    """Read-only methods work on a frozen DAG."""

    def _make_frozen_dag(self):
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1}, 10, (), depth=3, t_count=1)
        dag.add_node("op2", {1, 2}, 20, (), depth=5, t_count=2)
        dag.add_node("op3", {3}, 5, (), depth=2, t_count=0)
        dag.freeze()
        return dag

    def test_report_after_freeze(self):
        dag = self._make_frozen_dag()
        report = dag.report()
        assert "Compilation Report:" in report
        assert "TOTAL" in report

    def test_to_dot_after_freeze(self):
        dag = self._make_frozen_dag()
        dot = dag.to_dot()
        assert dot.startswith("digraph CallGraph {")
        assert dot.rstrip().endswith("}")

    def test_parallel_groups_after_freeze(self):
        dag = self._make_frozen_dag()
        groups = dag.parallel_groups()
        assert len(groups) >= 1

    def test_aggregate_after_freeze(self):
        dag = self._make_frozen_dag()
        agg = dag.aggregate()
        assert agg["gates"] == 35
        assert agg["qubits"] == 4

    def test_nodes_property_after_freeze(self):
        dag = self._make_frozen_dag()
        nodes = dag.nodes
        assert len(nodes) == 3

    def test_execution_order_edges_after_freeze(self):
        dag = self._make_frozen_dag()
        edges = dag.execution_order_edges()
        # op1 -> op2 (shared qubit 1)
        assert (0, 1) in edges


# ---------------------------------------------------------------------------
# Integration: graph frozen after compile capture
# ---------------------------------------------------------------------------


class TestFreezeIntegration:
    """Integration tests: DAG is frozen after first compilation."""

    def test_graph_not_frozen_after_opt1_capture(self):
        """opt=1 DAGs are not frozen (they accumulate across calls)."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        assert not dag.frozen

    def test_replay_no_mutation(self):
        """Compile fn, call it again, assert node count unchanged."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        count_after_capture = dag.node_count
        edges_after_capture = list(dag.execution_order_edges())

        b = qint(5, width=4)
        inc(b)  # Replay

        # Node count and edge list unchanged after replay
        assert dag.node_count == count_after_capture
        assert list(dag.execution_order_edges()) == edges_after_capture

    def test_replay_does_not_add_edges(self):
        """Edge list identical before and after replay."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_two(x):
            x += 2
            return x

        a = qint(0, width=4)
        add_two(a)
        dag = add_two.call_graph
        edges_before = sorted(dag.dag.edge_list())

        b = qint(1, width=4)
        add_two(b)
        edges_after = sorted(dag.dag.edge_list())

        assert edges_before == edges_after

    def test_not_frozen_after_default_opt(self):
        """@ql.compile (bare) defaults to opt=1, which does not freeze."""
        ql.circuit()

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        assert not dag.frozen

    def test_frozen_after_opt0(self):
        """@ql.compile(opt=0) freezes the DAG after capture."""
        ql.circuit()

        @ql.compile(opt=0)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        assert dag.frozen
