"""Unit tests for the CallGraphDAG module (call_graph.py).

Tests DAGNode metadata, bitmask computation, overlap edge construction,
parallel group detection, and builder stack management.
"""

import numpy as np

from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _dag_builder_stack,
    current_dag_context,
    pop_dag_context,
    push_dag_context,
)

# ---------------------------------------------------------------------------
# DAGNode tests
# ---------------------------------------------------------------------------


class TestDAGNode:
    """Tests for DAGNode data storage and bitmask computation."""

    def test_stores_metadata(self):
        node = DAGNode("my_func", {0, 1, 2}, 42, ("key", 3))
        assert node.func_name == "my_func"
        assert node.qubit_set == frozenset({0, 1, 2})
        assert node.gate_count == 42
        assert node.cache_key == ("key", 3)

    def test_qubit_set_stored_as_frozenset(self):
        node = DAGNode("f", {3, 5}, 10, ())
        assert isinstance(node.qubit_set, frozenset)
        assert node.qubit_set == frozenset({3, 5})

    def test_bitmask_single_qubit(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.bitmask == np.uint64(0b1)

    def test_bitmask_multiple_qubits(self):
        node = DAGNode("f", {0, 2}, 1, ())
        assert node.bitmask == np.uint64(0b101)

    def test_bitmask_higher_qubits(self):
        node = DAGNode("f", {3, 7}, 1, ())
        expected = np.uint64((1 << 3) | (1 << 7))
        assert node.bitmask == expected

    def test_bitmask_empty_qubit_set(self):
        node = DAGNode("f", set(), 0, ())
        assert node.bitmask == np.uint64(0)


# ---------------------------------------------------------------------------
# CallGraphDAG.add_node tests
# ---------------------------------------------------------------------------


class TestAddNode:
    """Tests for adding nodes to the call graph DAG."""

    def test_add_node_returns_index(self):
        dag = CallGraphDAG()
        idx = dag.add_node("f", {0, 1}, 10, ("k",))
        assert idx == 0

    def test_add_multiple_nodes_increments_index(self):
        dag = CallGraphDAG()
        i0 = dag.add_node("f", {0}, 5, ())
        i1 = dag.add_node("g", {1}, 3, ())
        assert i0 == 0
        assert i1 == 1

    def test_add_node_stores_dag_node(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, ("k",))
        assert len(dag.nodes) == 1
        assert dag.nodes[0].func_name == "f"

    def test_add_node_with_parent_creates_call_edge(self):
        dag = CallGraphDAG()
        p = dag.add_node("parent", {0, 1, 2}, 20, ())
        c = dag.add_node("child", {0, 1}, 5, (), parent_index=p)
        # The underlying PyDAG should have an edge from parent to child
        edges = dag.dag.edge_list()
        assert (p, c) in edges

    def test_add_node_with_parent_edge_has_call_type(self):
        dag = CallGraphDAG()
        p = dag.add_node("parent", {0, 1}, 10, ())
        c = dag.add_node("child", {0}, 5, (), parent_index=p)
        edge_data = dag.dag.get_edge_data(p, c)
        assert edge_data == {"type": "call"}

    def test_node_count_property(self):
        dag = CallGraphDAG()
        assert dag.node_count == 0
        dag.add_node("f", {0}, 1, ())
        assert dag.node_count == 1

    def test_len(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, ())
        dag.add_node("g", {1}, 1, ())
        assert len(dag) == 2


# ---------------------------------------------------------------------------
# CallGraphDAG.build_overlap_edges tests
# ---------------------------------------------------------------------------


class TestBuildOverlapEdges:
    """Tests for qubit overlap edge computation."""

    def test_overlapping_nodes_get_edge(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2}, 10, ())
        dag.add_node("g", {1, 2, 3}, 8, ())
        dag.build_overlap_edges()
        # Should have an overlap edge between node 0 and node 1
        edges = dag.dag.edge_list()
        assert (0, 1) in edges

    def test_overlap_edge_weight_is_intersection_size(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2}, 10, ())
        dag.add_node("g", {1, 2, 3}, 8, ())
        dag.build_overlap_edges()
        # Intersection is {1, 2} -> weight = 2
        edge_data = dag.dag.get_edge_data(0, 1)
        assert edge_data["type"] == "overlap"
        assert edge_data["weight"] == 2

    def test_disjoint_nodes_no_edge(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, ())
        dag.add_node("g", {2, 3}, 8, ())
        dag.build_overlap_edges()
        edges = dag.dag.edge_list()
        # Filter to only overlap edges (no call edges expected either)
        assert len(edges) == 0

    def test_skip_parent_child_pairs(self):
        """build_overlap_edges should NOT add overlap edges for parent-child pairs
        that already have a 'call' edge."""
        dag = CallGraphDAG()
        p = dag.add_node("parent", {0, 1, 2}, 20, ())
        c = dag.add_node("child", {0, 1}, 5, (), parent_index=p)
        dag.build_overlap_edges()
        # Should still have exactly 1 edge (the call edge), not an additional overlap edge
        edges = dag.dag.edge_list()
        assert len(edges) == 1
        edge_data = dag.dag.get_edge_data(p, c)
        assert edge_data == {"type": "call"}

    def test_multiple_overlaps(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 5, ())
        dag.add_node("b", {1, 2}, 5, ())
        dag.add_node("c", {2, 3}, 5, ())
        dag.build_overlap_edges()
        edges = dag.dag.edge_list()
        # a-b overlap on {1}, b-c overlap on {2}, a-c disjoint
        overlap_edges = [(s, t) for s, t in edges]
        assert (0, 1) in overlap_edges  # a-b
        assert (1, 2) in overlap_edges  # b-c
        assert (0, 2) not in overlap_edges  # a-c disjoint

    def test_empty_dag_handles_gracefully(self):
        dag = CallGraphDAG()
        dag.build_overlap_edges()  # Should not raise
        assert dag.node_count == 0

    def test_single_node_handles_gracefully(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, ())
        dag.build_overlap_edges()  # Should not raise
        assert len(dag.dag.edge_list()) == 0


# ---------------------------------------------------------------------------
# CallGraphDAG.parallel_groups tests
# ---------------------------------------------------------------------------


class TestParallelGroups:
    """Tests for parallel group (connected component) detection."""

    def test_disjoint_nodes_separate_groups(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0}, 1, ())
        dag.add_node("b", {1}, 1, ())
        dag.add_node("c", {2}, 1, ())
        groups = dag.parallel_groups()
        assert len(groups) == 3
        # Each group is a singleton set
        group_sizes = sorted(len(g) for g in groups)
        assert group_sizes == [1, 1, 1]

    def test_all_overlapping_single_group(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 1, ())
        dag.add_node("b", {1, 2}, 1, ())
        dag.add_node("c", {2, 3}, 1, ())
        groups = dag.parallel_groups()
        # a overlaps b, b overlaps c -> all in one group
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_mixed_groups(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 1, ())
        dag.add_node("b", {1, 2}, 1, ())
        dag.add_node("c", {5, 6}, 1, ())
        dag.add_node("d", {6, 7}, 1, ())
        groups = dag.parallel_groups()
        assert len(groups) == 2
        group_sizes = sorted(len(g) for g in groups)
        assert group_sizes == [2, 2]

    def test_all_disjoint_returns_n_singletons(self):
        dag = CallGraphDAG()
        for i in range(5):
            dag.add_node(f"f{i}", {i}, 1, ())
        groups = dag.parallel_groups()
        assert len(groups) == 5

    def test_all_overlapping_returns_single_set(self):
        dag = CallGraphDAG()
        # All share qubit 0
        for i in range(4):
            dag.add_node(f"f{i}", {0, i + 1}, 1, ())
        groups = dag.parallel_groups()
        assert len(groups) == 1
        assert len(groups[0]) == 4

    def test_empty_dag_returns_empty_list(self):
        dag = CallGraphDAG()
        groups = dag.parallel_groups()
        assert groups == [] or len(groups) == 0


# ---------------------------------------------------------------------------
# Builder stack tests
# ---------------------------------------------------------------------------


class TestBuilderStack:
    """Tests for the module-level DAG builder stack."""

    def setup_method(self):
        """Ensure clean stack before each test."""
        _dag_builder_stack.clear()

    def test_push_and_current(self):
        dag = CallGraphDAG()
        push_dag_context(dag, parent_index=None)
        ctx = current_dag_context()
        assert ctx is not None
        assert ctx[0] is dag
        assert ctx[1] is None

    def test_push_pop_returns_context(self):
        dag = CallGraphDAG()
        push_dag_context(dag, parent_index=5)
        result = pop_dag_context()
        assert result == (dag, 5)

    def test_pop_empties_stack(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        pop_dag_context()
        assert current_dag_context() is None

    def test_nested_push_pop(self):
        dag = CallGraphDAG()
        push_dag_context(dag, parent_index=None)
        push_dag_context(dag, parent_index=0)
        push_dag_context(dag, parent_index=1)

        ctx = current_dag_context()
        assert ctx == (dag, 1)

        pop_dag_context()
        ctx = current_dag_context()
        assert ctx == (dag, 0)

        pop_dag_context()
        ctx = current_dag_context()
        assert ctx == (dag, None)

        pop_dag_context()
        assert current_dag_context() is None

    def test_empty_stack_current_returns_none(self):
        assert current_dag_context() is None

    def test_empty_stack_pop_returns_none(self):
        result = pop_dag_context()
        assert result is None

    def teardown_method(self):
        """Clean up stack after each test."""
        _dag_builder_stack.clear()
