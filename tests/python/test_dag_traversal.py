"""Tests for Step 12.5: DAG traversal execution.

Validates that execute_dag traverses the DAG in topological order and
calls run_instruction for each node, producing the same gate count as
direct execution.
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    execute_dag,
)

# ---------------------------------------------------------------------------
# Unit tests: execute_dag with manually constructed DAGs
# ---------------------------------------------------------------------------


class TestExecuteDAGUnit:
    """Unit-level tests for execute_dag on manually built DAGs."""

    def test_empty_dag_returns_zero(self):
        dag = CallGraphDAG()
        assert execute_dag(dag) == 0

    def test_skips_merged_nodes(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, (), sequence_ptr=0xDEAD)
        dag._nodes[0]._merged = True
        # No circuit -> would crash if it tried to execute; 0 means skipped
        assert execute_dag(dag) == 0

    def test_skips_composite_nodes(self):
        dag = CallGraphDAG()
        dag.add_node("add_cq", {0, 1}, 10, (), is_composite=True)
        assert execute_dag(dag) == 0

    def test_skips_nodes_without_sequence_ptr(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, ())
        assert execute_dag(dag) == 0

    def test_skips_nodes_without_qubit_mapping(self):
        dag = CallGraphDAG()
        dag.add_node("f", set(), 0, (), sequence_ptr=0xDEAD, qubit_mapping=())
        assert execute_dag(dag) == 0

    def test_execute_method_delegates_to_function(self):
        dag = CallGraphDAG()
        result = dag.execute()
        assert result == 0

    def test_call_node_without_compiled_func_ref_skipped(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, (), is_call_node=True)
        # _compiled_func_ref is None by default, should be skipped
        assert execute_dag(dag) == 0


# ---------------------------------------------------------------------------
# Integration tests: QFT mode (non-composite operations with sequence_ptr)
# ---------------------------------------------------------------------------


class TestExecuteDAGIntegrationQFT:
    """Integration tests: DAG traversal produces same gates as direct execution."""

    def test_qft_add_cq_dag_traversal(self):
        """QFT-mode add constant: DAG traversal produces same gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        gc_before = ql.get_gate_count()
        inc(a)
        gc_direct = ql.get_gate_count() - gc_before

        dag = inc.call_graph
        assert dag is not None
        assert dag.node_count > 0

        # Verify all nodes have sequence_ptr (QFT mode, non-composite)
        for node in dag.nodes:
            if not node.is_call_node:
                assert node.sequence_ptr != 0 or node.uncontrolled_seq != 0, (
                    f"Node {node.func_name} has no sequence pointer"
                )

        # Execute via DAG traversal on fresh circuit
        ql.circuit()
        ql.option("fault_tolerant", False)
        _b = qint(3, width=4)  # noqa: F841 — allocate qubits for DAG replay

        gc_before_dag = ql.get_gate_count()
        executed = execute_dag(dag)
        gc_dag = ql.get_gate_count() - gc_before_dag

        assert executed > 0, "No nodes were executed"
        assert gc_dag == gc_direct, f"DAG traversal gate count {gc_dag} != direct {gc_direct}"

    def test_qft_not_dag_traversal(self):
        """QFT-mode NOT: DAG traversal produces same gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def not_op(x):
            x = ~x
            return x

        a = qint(0b1010, width=4)
        gc_before = ql.get_gate_count()
        not_op(a)
        gc_direct = ql.get_gate_count() - gc_before

        dag = not_op.call_graph
        assert dag is not None

        ql.circuit()
        ql.option("fault_tolerant", False)
        _b = qint(0b1010, width=4)  # noqa: F841 — allocate qubits for DAG replay

        gc_before_dag = ql.get_gate_count()
        executed = execute_dag(dag)
        gc_dag = ql.get_gate_count() - gc_before_dag

        assert executed > 0
        assert gc_dag == gc_direct

    def test_qft_xor_dag_traversal(self):
        """QFT-mode XOR: DAG traversal produces same gate count."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def xor_op(x, y):
            x ^= y
            return x

        a = qint(5, width=4)
        b = qint(3, width=4)
        gc_before = ql.get_gate_count()
        xor_op(a, b)
        gc_direct = ql.get_gate_count() - gc_before

        dag = xor_op.call_graph
        assert dag is not None

        ql.circuit()
        ql.option("fault_tolerant", False)
        _c = qint(5, width=4)  # noqa: F841 — allocate qubits for DAG replay
        _d = qint(3, width=4)  # noqa: F841 — allocate qubits for DAG replay

        gc_before_dag = ql.get_gate_count()
        executed = execute_dag(dag)
        gc_dag = ql.get_gate_count() - gc_before_dag

        assert executed > 0
        assert gc_dag == gc_direct

    def test_topological_order_respects_dependencies(self):
        """Nodes sharing qubits are executed in correct order."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def multi_op(x):
            x += 1
            x += 2
            return x

        a = qint(0, width=4)
        multi_op(a)
        dag = multi_op.call_graph
        assert dag is not None

        # Verify execution order edges exist between nodes sharing qubits
        edges = dag.execution_order_edges()
        if dag.node_count > 1:
            assert len(edges) > 0, "Expected execution order edges"

    def test_dag_execute_returns_node_count(self):
        """execute_dag returns the number of nodes actually executed."""
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None

        ql.circuit()
        ql.option("fault_tolerant", False)
        _b = qint(3, width=4)  # noqa: F841 — allocate qubits for DAG replay

        executed = execute_dag(dag)
        # Should match non-composite, non-call nodes with sequence_ptr
        expected = sum(
            1
            for n in dag.nodes
            if not n._merged
            and not n.is_call_node
            and not n.is_composite
            and (n.sequence_ptr != 0 or n.uncontrolled_seq != 0)
            and len(n.qubit_mapping) > 0
        )
        assert executed == expected
