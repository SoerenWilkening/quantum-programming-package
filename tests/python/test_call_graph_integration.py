"""Phase 0 integration test: end-to-end call graph verification.

Compiles functions with additions, multiplications, and comparisons on
different registers and validates execution-order edge structure, parallel
branches, merge nodes, non-zero gate counts, graph immutability after
replay, and clean to_dot() output.

[Quantum_Assembly-vmq]
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    _dag_builder_stack,
    pop_dag_context,
    push_dag_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec_edges(dag: CallGraphDAG) -> list[tuple[int, int]]:
    """Return execution-order edges as sorted (src, tgt) pairs."""
    return sorted(dag.execution_order_edges())


def _op_nodes(dag: CallGraphDAG) -> list:
    """Return nodes that have a non-empty operation_type."""
    return [n for n in dag.nodes if n.operation_type]


def _reachable_from_roots(dag: CallGraphDAG) -> set[int]:
    """BFS from root nodes (no incoming exec edges) over exec edges."""
    exec_edges = dag.execution_order_edges()
    all_nodes = set(range(dag.node_count))
    targets = {tgt for _, tgt in exec_edges}
    roots = all_nodes - targets
    if not roots:
        roots = {0}

    adj: dict[int, list[int]] = {}
    for src, tgt in exec_edges:
        adj.setdefault(src, []).append(tgt)

    visited = set()
    queue = list(roots)
    visited.update(roots)
    while queue:
        node = queue.pop(0)
        for child in adj.get(node, []):
            if child not in visited:
                visited.add(child)
                queue.append(child)
    return visited


# ---------------------------------------------------------------------------
# Test: Mixed operations on separate registers via DAG context
# ---------------------------------------------------------------------------


class TestMixedOperationsDirect:
    """Direct DAG-context test with mixed arithmetic on separate registers.

    Uses explicit push_dag_context/pop_dag_context to capture operations
    from regular qint arithmetic (without @ql.compile wrapping) so that
    we can inspect the DAG structure in detail.
    """

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_separate_registers_produce_parallel_branches(self):
        """Operations on disjoint registers yield independent DAG branches."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            # These two operations touch different qubits.
            a += 1
            b += 1
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        assert len(nodes) >= 2, f"Expected >= 2 operation nodes, got {len(nodes)}"

        # Nodes on disjoint qubits should NOT have an execution-order edge
        # between them (they can execute in parallel).
        edges = _exec_edges(dag)
        # All qubit sets should be disjoint across the two registers
        a_qubit_set = nodes[0].qubit_set
        b_qubit_set = nodes[1].qubit_set
        assert a_qubit_set.isdisjoint(b_qubit_set), (
            f"Expected disjoint qubit sets, got {a_qubit_set} and {b_qubit_set}"
        )
        # No execution-order edges between disjoint ops
        assert len(edges) == 0, (
            f"Expected no execution-order edges between disjoint operations, "
            f"got {len(edges)}: {edges}"
        )

    def test_same_register_produces_chain(self):
        """Multiple operations on the same register produce a linear chain."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
            a += 2
            a += 3
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        assert len(nodes) == 3, f"Expected 3 operation nodes, got {len(nodes)}"

        edges = _exec_edges(dag)
        # Linear chain: 0->1->2
        assert len(edges) == 2
        assert (0, 1) in edges
        assert (1, 2) in edges
        # No transitive edge
        assert (0, 2) not in edges

    def test_merge_node_from_cross_register_operation(self):
        """An operation touching both registers creates a merge node."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1  # op on register A
            b += 1  # op on register B (independent)
            a += b  # op touching BOTH registers -> merge
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        assert len(nodes) >= 3

        # The merge node (a += b) should have edges from both the
        # a-register op and the b-register op.
        merge_node_idx = dag.node_count - 1
        edges = _exec_edges(dag)
        parents_of_merge = [src for src, tgt in edges if tgt == merge_node_idx]
        assert len(parents_of_merge) == 2, (
            f"Merge node should have 2 parent edges, got {len(parents_of_merge)}"
        )

    def test_all_gate_counts_nonzero(self):
        """Every operation node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1
            b += 2
            a += b
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        assert len(nodes) > 0
        for node in nodes:
            assert node.gate_count > 0, (
                f"Node {node.operation_type} has gate_count={node.gate_count}, expected > 0"
            )

    def test_all_nodes_reachable(self):
        """All nodes are reachable from roots via BFS over execution-order edges."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1
            b += 1
            a += b
        finally:
            pop_dag_context()

        reachable = _reachable_from_roots(dag)
        assert reachable == set(range(dag.node_count))

    def test_aggregate_positive(self):
        """Aggregate gate count is positive after mixed operations."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
            a += 2
        finally:
            pop_dag_context()

        agg = dag.aggregate()
        assert agg["gates"] > 0
        assert agg["qubits"] > 0


# ---------------------------------------------------------------------------
# Test: @ql.compile integration with mixed operations
# ---------------------------------------------------------------------------


class TestCompileMixedOperations:
    """Integration via @ql.compile: mixed ops produce correct DAG structure."""

    def test_compile_addition_gate_counts(self):
        """Addition operations inside @ql.compile produce DAG nodes
        with nonzero gate counts."""
        ql.circuit()

        @ql.compile(opt=1)
        def mixed(x, y):
            x += 1
            y += 2
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        mixed(a, b)

        dag = mixed.call_graph
        assert dag is not None
        nodes = _op_nodes(dag)
        assert len(nodes) >= 3

        for node in nodes:
            assert node.gate_count > 0, (
                f"Node {node.operation_type} has gate_count={node.gate_count}"
            )

    def test_compile_produces_frozen_dag(self):
        """DAG is frozen after capture via @ql.compile."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc_both(x, y):
            x += 1
            y += 1
            return x

        a = qint(0, width=4)
        b = qint(0, width=4)
        inc_both(a, b)

        dag = inc_both.call_graph
        assert dag is not None
        assert dag.frozen

    def test_graph_unchanged_after_replay(self):
        """Node count and edge list are unchanged after replay."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_inc(x, y):
            x += y
            x += 1
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        add_inc(a, b)

        dag = add_inc.call_graph
        count_after_capture = dag.node_count
        edges_after_capture = sorted(dag.execution_order_edges())

        c = qint(1, width=4)
        d = qint(1, width=4)
        add_inc(c, d)

        assert dag.node_count == count_after_capture
        assert sorted(dag.execution_order_edges()) == edges_after_capture

    def test_compile_edge_structure_matches_algorithm(self):
        """Verify edges match the execution-order algorithm:
        operations on the same qubits chain, disjoint qubits are parallel."""
        ql.circuit()

        @ql.compile(opt=1)
        def chain_fn(x):
            x += 1
            x += 2
            x += 3
            return x

        a = qint(0, width=4)
        chain_fn(a)

        dag = chain_fn.call_graph
        assert dag is not None
        nodes = _op_nodes(dag)
        assert len(nodes) == 3

        edges = _exec_edges(dag)
        # Linear chain: node0 -> node1 -> node2
        assert len(edges) == 2
        node_indices = [i for i in range(dag.node_count) if dag.nodes[i].operation_type]
        assert (node_indices[0], node_indices[1]) in edges
        assert (node_indices[1], node_indices[2]) in edges

    def test_compile_parallel_groups(self):
        """Operations on disjoint registers belong to separate parallel groups."""
        ql.circuit()

        @ql.compile(opt=1)
        def disjoint(x, y):
            x += 1
            y += 2
            return x

        a = qint(0, width=4)
        b = qint(0, width=4)
        disjoint(a, b)

        dag = disjoint.call_graph
        assert dag is not None
        groups = dag.parallel_groups()
        assert len(groups) >= 2, (
            f"Expected >= 2 parallel groups for disjoint registers, got {len(groups)}"
        )

    def test_multiplication_gate_counts(self):
        """Multiplication with DAG context produces DAG nodes with
        nonzero gate counts."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a *= 2
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        mul_nodes = [n for n in nodes if "mul" in n.operation_type]
        assert len(mul_nodes) > 0, "Expected at least one mul operation node"
        for node in mul_nodes:
            assert node.gate_count > 0, f"mul node gate_count should be > 0, got {node.gate_count}"

    def test_comparison_gate_counts(self):
        """Comparison with DAG context produces DAG nodes with
        nonzero gate counts."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            _ = a == 5
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        eq_nodes = [n for n in nodes if "eq" in n.operation_type]
        assert len(eq_nodes) > 0, "Expected at least one eq operation node"
        for node in eq_nodes:
            assert node.gate_count > 0, f"eq node gate_count should be > 0, got {node.gate_count}"

    def test_mixed_all_operation_types(self):
        """Addition, multiplication, and comparison together produce
        DAG nodes for each operation type, all with nonzero gate counts."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(2, width=4)
            b = qint(3, width=4)
            a += 1
            b *= 2
            _ = a == 3
            a += b
        finally:
            pop_dag_context()

        nodes = _op_nodes(dag)
        op_types = {n.operation_type for n in nodes}

        # Verify we have addition, multiplication, and comparison nodes
        has_add = any("add" in t for t in op_types)
        has_mul = any("mul" in t for t in op_types)
        has_eq = any("eq" in t for t in op_types)
        assert has_add, f"Expected add operation, got types: {op_types}"
        assert has_mul, f"Expected mul operation, got types: {op_types}"
        assert has_eq, f"Expected eq operation, got types: {op_types}"

        # All nodes have nonzero gate counts
        for node in nodes:
            assert node.gate_count > 0, (
                f"Node {node.operation_type} has gate_count={node.gate_count}"
            )


# ---------------------------------------------------------------------------
# Test: to_dot() output quality
# ---------------------------------------------------------------------------


class TestToDotIntegration:
    """Verify to_dot() produces valid, clean DOT output."""

    def test_to_dot_valid_structure(self):
        """to_dot() output starts with digraph and ends with }."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1
            b += 1
            a += b
        finally:
            pop_dag_context()

        dot = dag.to_dot()
        assert dot.startswith("digraph CallGraph {")
        assert dot.rstrip().endswith("}")

    def test_to_dot_contains_exec_edges(self):
        """to_dot() output contains exec edge labels for connected ops."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
            a += 2
        finally:
            pop_dag_context()

        dot = dag.to_dot()
        assert '"exec"' in dot, "Expected exec edge labels in DOT output"

    def test_to_dot_contains_gate_counts(self):
        """to_dot() labels include gate counts from operation nodes."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()

        dot = dag.to_dot()
        assert "gates:" in dot

    def test_to_dot_shows_clusters_for_parallel_groups(self):
        """When there are multiple parallel groups, to_dot() uses subgraph clusters."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1
            b += 1
        finally:
            pop_dag_context()

        groups = dag.parallel_groups()
        assert len(groups) > 1, (
            f"Expected > 1 parallel groups for disjoint registers, got {len(groups)}"
        )
        dot = dag.to_dot()
        assert "subgraph cluster_" in dot


# ---------------------------------------------------------------------------
# Test: no overlap edges remain
# ---------------------------------------------------------------------------


class TestNoOverlapEdges:
    """Confirm that after the Phase 0 redesign, no overlap-type edges exist."""

    def test_no_overlap_edges_in_integration(self):
        """No edge in the DAG has type == 'overlap' after real operations."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(2, width=4)
            a += 1
            b += 1
            a += b
        finally:
            pop_dag_context()

        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "overlap", f"Found unexpected overlap edge: {edata}"

    def test_all_edges_are_execution_order(self):
        """Every edge in the DAG is of type 'execution_order'."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
            a += 2
        finally:
            pop_dag_context()

        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            assert isinstance(edata, dict)
            assert edata.get("type") == "execution_order"


# ---------------------------------------------------------------------------
# Test: no wrapper/function nodes
# ---------------------------------------------------------------------------


class TestNoWrapperNodes:
    """Verify there are no function-level wrapper nodes in the DAG."""

    def test_compile_no_wrapper_node(self):
        """@ql.compile with multiple ops has only operation nodes (+ no wrapper)."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_chain(x):
            x += 1
            x += 2
            x += 3
            return x

        a = qint(0, width=4)
        add_chain(a)

        dag = add_chain.call_graph
        assert dag is not None
        # All nodes should be operation nodes (have operation_type set)
        for node in dag.nodes:
            assert node.operation_type, f"Found node without operation_type: {node}"


# ---------------------------------------------------------------------------
# Test: comprehensive end-to-end scenario
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full end-to-end: compile a complex function, verify all Phase 0 properties."""

    def test_full_scenario(self):
        """Compile a function with addition, multiplication, and comparison
        on multiple registers, then verify all Phase 0 invariants."""
        ql.circuit()

        @ql.compile(opt=1)
        def complex_fn(x, y):
            x += 1  # add on x register
            y *= 2  # mul on y register (independent)
            _ = x == 3  # comparison on x register
            x += y  # merge: touches both registers
            x += 3  # add on (now-merged) registers
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        complex_fn(a, b)

        dag = complex_fn.call_graph
        assert dag is not None

        # 1. Correct number of operation nodes (add, mul, eq, add_qq, add_cq, uncompute)
        # The comparison `x == 3` creates a temporary qbool whose auto-uncomputation
        # is now recorded as an "uncompute" DAG node.
        nodes = _op_nodes(dag)
        assert len(nodes) == 6, f"Expected 6 operation nodes, got {len(nodes)}"

        # 2. All gate counts non-zero
        for node in nodes:
            assert node.gate_count > 0, (
                f"Node {node.operation_type} has gate_count={node.gate_count}"
            )

        # 3. Aggregate gate count positive
        agg = dag.aggregate()
        assert agg["gates"] > 0
        assert agg["qubits"] > 0

        # 4. Graph is frozen
        assert dag.frozen

        # 5. Edge structure: at least some execution-order edges
        edges = _exec_edges(dag)
        assert len(edges) >= 2, f"Expected at least 2 execution-order edges, got {len(edges)}"

        # 6. No overlap edges
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "overlap"

        # 7. All nodes reachable
        reachable = _reachable_from_roots(dag)
        assert reachable == set(range(dag.node_count))

        # 8. to_dot() produces valid output
        dot = dag.to_dot()
        assert dot.startswith("digraph CallGraph {")
        assert dot.rstrip().endswith("}")

        # 9. Graph unchanged after replay
        count_before = dag.node_count
        edges_before = sorted(dag.execution_order_edges())

        c = qint(1, width=4)
        d = qint(1, width=4)
        complex_fn(c, d)

        assert dag.node_count == count_before
        assert sorted(dag.execution_order_edges()) == edges_before

        # 10. report() produces output with gate counts
        report = dag.report()
        assert "TOTAL" in report
        assert "Gates" in report or "gates" in report.lower()
