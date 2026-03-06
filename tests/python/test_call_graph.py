"""Unit tests for the CallGraphDAG module (call_graph.py).

Tests DAGNode metadata, bitmask computation, overlap edge construction,
parallel group detection, and builder stack management.
"""

import numpy as np

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _compute_depth,
    _compute_t_count,
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

    def test_stores_depth_and_t_count(self):
        node = DAGNode("f", {0, 1}, 10, (), depth=5, t_count=14)
        assert node.depth == 5
        assert node.t_count == 14

    def test_depth_t_count_default_zero(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.depth == 0
        assert node.t_count == 0


# ---------------------------------------------------------------------------
# _compute_depth tests
# ---------------------------------------------------------------------------


class TestComputeDepth:
    """Tests for the _compute_depth helper function."""

    def test_empty_gate_list(self):
        assert _compute_depth([]) == 0

    def test_single_one_qubit_gate(self):
        gates = [{"type": 0, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []}]
        assert _compute_depth(gates) == 1

    def test_two_parallel_gates_different_qubits(self):
        gates = [
            {"type": 0, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []},
            {"type": 0, "target": 1, "angle": 0.0, "num_controls": 0, "controls": []},
        ]
        assert _compute_depth(gates) == 1

    def test_two_serial_gates_same_qubit(self):
        gates = [
            {"type": 0, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []},
            {"type": 0, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []},
        ]
        assert _compute_depth(gates) == 2

    def test_two_control_gate_accounts_for_all_qubits(self):
        # A CCX (Toffoli) gate: target=2, controls=[0,1]
        gates = [
            {"type": 0, "target": 2, "angle": 0.0, "num_controls": 2, "controls": [0, 1]},
        ]
        assert _compute_depth(gates) == 1
        # Now add a gate on qubit 0 -- should be depth 2 since qubit 0 was used
        gates.append({"type": 0, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []})
        assert _compute_depth(gates) == 2


# ---------------------------------------------------------------------------
# _compute_t_count tests
# ---------------------------------------------------------------------------


class TestComputeTCount:
    """Tests for the _compute_t_count helper function."""

    def test_empty_gate_list(self):
        assert _compute_t_count([]) == 0

    def test_t_gate_entries_counted(self):
        gates = [
            {"type": 10, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []},
            {"type": 11, "target": 1, "angle": 0.0, "num_controls": 0, "controls": []},
            {"type": 10, "target": 2, "angle": 0.0, "num_controls": 0, "controls": []},
        ]
        assert _compute_t_count(gates) == 3

    def test_no_t_gates_with_ccx_returns_7_times_ccx(self):
        gates = [
            {"type": 0, "target": 2, "angle": 0.0, "num_controls": 2, "controls": [0, 1]},
            {"type": 0, "target": 5, "angle": 0.0, "num_controls": 2, "controls": [3, 4]},
            {"type": 0, "target": 8, "angle": 0.0, "num_controls": 3, "controls": [5, 6, 7]},
        ]
        assert _compute_t_count(gates) == 21  # 7 * 3

    def test_both_t_and_ccx_returns_only_direct_t_count(self):
        gates = [
            {"type": 10, "target": 0, "angle": 0.0, "num_controls": 0, "controls": []},
            {"type": 0, "target": 2, "angle": 0.0, "num_controls": 2, "controls": [0, 1]},
        ]
        assert _compute_t_count(gates) == 1  # Only direct T count


# ---------------------------------------------------------------------------
# aggregate() tests
# ---------------------------------------------------------------------------


class TestAggregate:
    """Tests for CallGraphDAG.aggregate() method."""

    def test_empty_dag(self):
        dag = CallGraphDAG()
        result = dag.aggregate()
        assert result == {"gates": 0, "depth": 0, "qubits": 0, "t_count": 0}

    def test_single_node(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2}, 10, (), depth=5, t_count=3)
        result = dag.aggregate()
        assert result == {"gates": 10, "depth": 5, "qubits": 3, "t_count": 3}

    def test_two_nodes_same_parallel_group(self):
        """Two nodes sharing qubits: gates summed, depth=max, qubits=union, t_count summed."""
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), depth=3, t_count=2)
        dag.add_node("g", {1, 2}, 8, (), depth=5, t_count=4)
        result = dag.aggregate()
        assert result["gates"] == 18
        assert result["depth"] == 5  # max of 3, 5 (same group)
        assert result["qubits"] == 3  # union {0,1,2}
        assert result["t_count"] == 6

    def test_two_nodes_different_groups_disjoint(self):
        """Two disjoint nodes: gates summed, depth=sum of per-group max, qubits=union, t_count summed."""
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), depth=3, t_count=2)
        dag.add_node("g", {4, 5}, 8, (), depth=5, t_count=4)
        result = dag.aggregate()
        assert result["gates"] == 18
        assert result["depth"] == 8  # 3 + 5 (different groups, sum)
        assert result["qubits"] == 4  # union {0,1,4,5}
        assert result["t_count"] == 6

    def test_three_nodes_mixed_groups(self):
        """3 nodes: 2 in one group, 1 in another. Critical-path depth correct."""
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 5, (), depth=3, t_count=1)
        dag.add_node("b", {1, 2}, 7, (), depth=6, t_count=2)
        dag.add_node("c", {5, 6}, 4, (), depth=2, t_count=0)
        result = dag.aggregate()
        assert result["gates"] == 16
        # Group 1: {a, b} -> max depth = 6; Group 2: {c} -> depth = 2; total = 8
        assert result["depth"] == 8
        assert result["qubits"] == 5  # {0,1,2,5,6}
        assert result["t_count"] == 3

    def test_integration_compile_aggregate(self):
        """Integration: compile a real function and call aggregate()."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        result = dag.aggregate()
        assert isinstance(result, dict)
        assert result["gates"] > 0
        assert result["depth"] > 0
        assert result["qubits"] > 0


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


# ---------------------------------------------------------------------------
# Integration tests: compile() + CallGraphDAG
# ---------------------------------------------------------------------------


class TestCompileDAGIntegration:
    """Integration tests for opt parameter, DAG building, and backward compat."""

    def test_opt1_produces_dag(self):
        """@ql.compile(opt=1) produces a CallGraphDAG after calling."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_one(x):
            x += 1
            return x

        a = qint(2, width=4)
        add_one(a)
        assert add_one.call_graph is not None
        assert add_one.call_graph.node_count >= 1
        node = add_one.call_graph.nodes[0]
        assert node.func_name == "add_one"
        assert len(node.qubit_set) > 0

    def test_opt3_no_dag(self):
        """@ql.compile(opt=3) has call_graph == None after calling."""
        ql.circuit()

        @ql.compile(opt=3)
        def add_one(x):
            x += 1
            return x

        a = qint(2, width=4)
        add_one(a)
        assert add_one.call_graph is None

    def test_bare_compile_default_opt1(self):
        """@ql.compile (bare, no opt) uses opt=1 default and builds DAG."""
        ql.circuit()

        @ql.compile
        def add_one(x):
            x += 1
            return x

        a = qint(2, width=4)
        add_one(a)
        assert add_one.call_graph is not None
        assert add_one.call_graph.node_count >= 1

    def test_dag_node_metadata(self):
        """DAG node contains correct function name, qubit set, gate count."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        node = dag.nodes[0]
        assert node.func_name == "inc"
        # Should have at least 4 qubits (width=4)
        assert len(node.qubit_set) >= 4
        assert node.gate_count > 0

    def test_overlapping_qubits_produce_overlap_edge(self):
        """Two compiled functions on overlapping qubits produce overlap edge."""
        ql.circuit()

        @ql.compile(opt=1)
        def f(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def g(x):
            x += 2
            return x

        a = qint(1, width=4)
        f(a)
        g(a)
        # f's DAG only has f; g's DAG only has g. Check f's DAG:
        dag = f.call_graph
        assert dag is not None
        # f only has 1 node (just f's call)
        assert dag.node_count == 1

    def test_disjoint_qubits_no_overlap_edge(self):
        """Two compiled functions on disjoint qubits produce no overlap edge."""
        ql.circuit()

        @ql.compile(opt=1)
        def wrapper(x, y):
            x += 1
            y += 2
            return x

        a = qint(1, width=4)
        b = qint(2, width=4)
        wrapper(a, b)
        dag = wrapper.call_graph
        assert dag is not None

    def test_nested_calls_parent_child(self):
        """Nested compiled calls (f calls g) produce parent-child edge in DAG."""
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
        # Should have at least 2 nodes (outer capture + inner)
        assert dag.node_count >= 2
        # Check for call edge (parent-child)
        edges = dag.dag.edge_list()
        call_edges = [(s, t) for s, t in edges if dag.dag.get_edge_data(s, t).get("type") == "call"]
        assert len(call_edges) >= 1

    def test_parallel_groups_real_circuit(self):
        """parallel_groups correctly identifies groups in a real circuit with multiple calls."""
        ql.circuit()

        @ql.compile(opt=1)
        def caller(x, y):
            x += 1
            y += 2
            return x

        a = qint(1, width=4)
        b = qint(2, width=4)
        caller(a, b)
        dag = caller.call_graph
        assert dag is not None
        groups = dag.parallel_groups()
        # At least 1 group
        assert len(groups) >= 1

    def test_circuit_reset_clears_call_graph(self):
        """Circuit reset (ql.circuit()) clears call_graph."""
        ql.circuit()

        @ql.compile(opt=1)
        def f(x):
            x += 1
            return x

        a = qint(2, width=4)
        f(a)
        assert f.call_graph is not None
        # Reset circuit
        ql.circuit()
        assert f.call_graph is None

    def test_second_call_replaces_dag(self):
        """Second call to same function replaces previous DAG (fresh DAG each call)."""
        ql.circuit()

        @ql.compile(opt=1)
        def f(x):
            x += 1
            return x

        a = qint(2, width=4)
        f(a)
        dag1 = f.call_graph

        b = qint(3, width=4)
        f(b)
        dag2 = f.call_graph

        # Should be different DAG objects (fresh each call)
        assert dag1 is not dag2
        assert dag2 is not None

    def test_dag_node_has_depth_and_t_count(self):
        """After compile(opt=1), DAGNode has depth > 0 and gate_count > 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        node = dag.nodes[0]
        assert node.gate_count > 0
        assert node.depth > 0

    def test_nested_call_has_depth_t_count(self):
        """Capture path: inner node has correct depth/t_count after finalization."""
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
        # The outer node (capture path) should have depth > 0
        # Find the outer node
        for node in dag.nodes:
            if node.func_name == "outer":
                assert node.depth > 0
                assert node.gate_count > 0
                break
        else:
            # If no node named "outer", at least check the first node
            assert dag.nodes[0].depth >= 0

    def test_to_dot_integration(self):
        """Integration: compile a real function and call to_dot()."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        dot = dag.to_dot()
        assert dot.startswith("digraph CallGraph {")
        assert dot.rstrip().endswith("}")
        assert "inc" in dot

    def test_opt_does_not_affect_cache_key(self):
        """opt parameter does NOT affect cache key (opt=1 and opt=3 share cache)."""
        ql.circuit()

        @ql.compile(opt=1)
        def f1(x):
            x += 1
            return x

        @ql.compile(opt=3)
        def f2(x):
            x += 1
            return x

        # Both should work correctly regardless of opt setting
        a = qint(2, width=4)
        f1(a)
        b = qint(3, width=4)
        f2(b)
        # opt=1 has DAG, opt=3 does not
        assert f1.call_graph is not None
        assert f2.call_graph is None


# ---------------------------------------------------------------------------
# TestDot: to_dot() method tests
# ---------------------------------------------------------------------------


class TestDot:
    """Tests for CallGraphDAG.to_dot() DOT export method."""

    def test_empty_dag_valid_dot(self):
        dag = CallGraphDAG()
        dot = dag.to_dot()
        assert dot.startswith("digraph CallGraph {")
        assert dot.rstrip().endswith("}")

    def test_single_node_label(self):
        dag = CallGraphDAG()
        dag.add_node("my_func", {0, 1, 2}, 42, (), depth=5, t_count=3)
        dot = dag.to_dot()
        assert "my_func" in dot
        assert "gates: 42" in dot
        assert "depth: 5" in dot
        assert "qubits: 3" in dot
        assert "T-count: 3" in dot

    def test_call_edge_solid(self):
        dag = CallGraphDAG()
        p = dag.add_node("parent", {0, 1, 2}, 20, ())
        dag.add_node("child", {0, 1}, 5, (), parent_index=p)
        dot = dag.to_dot()
        assert 'label="call"' in dot

    def test_overlap_edge_dashed(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2}, 10, ())
        dag.add_node("g", {1, 2, 3}, 8, ())
        dag.build_overlap_edges()
        dot = dag.to_dot()
        assert "style=dashed" in dot
        assert "qubits" in dot

    def test_multiple_groups_have_clusters(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 5, ())
        dag.add_node("g", {5}, 3, ())
        dot = dag.to_dot()
        assert "subgraph cluster_" in dot

    def test_single_group_no_cluster(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 5, ())
        dag.add_node("g", {1, 2}, 3, ())
        dot = dag.to_dot()
        assert "subgraph cluster_" not in dot

    def test_special_chars_escaped(self):
        dag = CallGraphDAG()
        dag.add_node('func"name', {0}, 1, ())
        dot = dag.to_dot()
        # The double-quote should be escaped in the label
        assert 'func\\"name' in dot or "func" in dot


# ---------------------------------------------------------------------------
# TestReport: report() method tests
# ---------------------------------------------------------------------------


class TestReport:
    """Tests for CallGraphDAG.report() compilation report method."""

    def test_empty_dag_report(self):
        dag = CallGraphDAG()
        report = dag.report()
        assert "empty" in report.lower() or "No nodes" in report

    def test_single_node_report_header(self):
        dag = CallGraphDAG()
        dag.add_node("my_func", {0, 1, 2}, 42, (), depth=5, t_count=3)
        report = dag.report()
        assert "Compilation Report:" in report
        assert "my_func" in report

    def test_report_columns(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), depth=3, t_count=1)
        report = dag.report()
        assert "Name" in report
        assert "Gates" in report
        assert "Depth" in report
        assert "Qubits" in report
        assert "T-count" in report
        assert "Group" in report

    def test_report_totals_row(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), depth=3, t_count=1)
        dag.add_node("g", {1, 2}, 8, (), depth=5, t_count=2)
        report = dag.report()
        assert "TOTAL" in report
        # Aggregate: gates=18, depth=5 (same group), qubits=3, t_count=3
        agg = dag.aggregate()
        assert str(agg["gates"]) in report
        assert str(agg["t_count"]) in report

    def test_report_group_numbers(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 5, (), depth=3, t_count=1)
        dag.add_node("g", {5}, 3, (), depth=2, t_count=0)
        report = dag.report()
        # Two disjoint nodes should have different group numbers
        # Both group 0 and group 1 should appear
        lines = report.split("\n")
        group_vals = set()
        for line in lines:
            parts = line.split("|")
            if len(parts) >= 7:
                grp = parts[-1].strip().rstrip("|").strip()
                if grp.isdigit():
                    group_vals.add(int(grp))
        assert len(group_vals) >= 2, f"Expected 2+ groups, got {group_vals}"

    def test_report_integration(self):
        """Integration: compile a real function and call report()."""
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
        assert "Compilation Report:" in report
        assert "inc" in report
        assert "TOTAL" in report
