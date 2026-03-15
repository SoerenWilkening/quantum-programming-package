"""Tests for execution-order edge builder in CallGraphDAG.

Validates the incremental edge construction that replaces O(n^2) overlap
computation with per-operation last_node_per_qubit tracking.

Step 0.1 of Phase 0: Call Graph Redesign [Quantum_Assembly-3s1].
"""

import rustworkx as rx

from quantum_language.call_graph import CallGraphDAG


def _exec_edges(dag: CallGraphDAG) -> list[tuple[int, int]]:
    """Return execution-order edges as sorted (src, tgt) pairs."""
    return sorted(dag.execution_order_edges())


def _has_exec_edge(dag: CallGraphDAG, src: int, tgt: int) -> bool:
    """Check if an execution_order edge exists from src to tgt."""
    return (src, tgt) in dag.execution_order_edges()


# ---------------------------------------------------------------------------
# Basic linear chain
# ---------------------------------------------------------------------------


class TestLinearChain:
    """3 ops on same qubits produce a linear chain: op1->op2->op3."""

    def test_linear_chain(self):
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 10, ())
        i1 = dag.add_node("op2", {0, 1}, 10, ())
        i2 = dag.add_node("op3", {0, 1}, 10, ())

        edges = _exec_edges(dag)
        assert (i0, i1) in edges
        assert (i1, i2) in edges
        # No direct edge from op1 to op3 (handled by transitivity)
        assert (i0, i2) not in edges
        assert len(edges) == 2

    def test_ten_additions_ten_edges(self):
        """10 ops on same qubits produce exactly 9 edges (not 45)."""
        dag = CallGraphDAG()
        indices = []
        for k in range(10):
            indices.append(dag.add_node(f"op{k}", {0, 1, 2}, 5, ()))
        edges = _exec_edges(dag)
        # Linear chain: op0->op1->...->op9 = 9 edges
        assert len(edges) == 9
        for k in range(9):
            assert (indices[k], indices[k + 1]) in edges


# ---------------------------------------------------------------------------
# Parallel branches (disjoint qubits)
# ---------------------------------------------------------------------------


class TestParallelBranches:
    """Ops on disjoint qubits produce independent branches, not connected."""

    def test_parallel_branches(self):
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 10, ())
        i1 = dag.add_node("op2", {2, 3}, 10, ())

        edges = _exec_edges(dag)
        # No execution_order edge between disjoint ops
        assert (i0, i1) not in edges
        assert (i1, i0) not in edges
        assert len(edges) == 0

    def test_three_disjoint_ops(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0}, 1, ())
        dag.add_node("b", {1}, 1, ())
        dag.add_node("c", {2}, 1, ())
        edges = _exec_edges(dag)
        assert len(edges) == 0


# ---------------------------------------------------------------------------
# Merge node (touches qubits from two branches)
# ---------------------------------------------------------------------------


class TestMergeNode:
    """Op touching qubits from two independent branches gets 2 parent edges."""

    def test_merge_node(self):
        dag = CallGraphDAG()
        i0 = dag.add_node("branch_a", {0, 1}, 10, ())
        i1 = dag.add_node("branch_b", {2, 3}, 10, ())
        # Merge touches qubits from both branches
        i2 = dag.add_node("merge", {1, 2}, 10, ())

        edges = _exec_edges(dag)
        assert _has_exec_edge(dag, i0, i2)
        assert _has_exec_edge(dag, i1, i2)
        # No edge between the two independent branches
        assert not _has_exec_edge(dag, i0, i1)
        assert not _has_exec_edge(dag, i1, i0)
        assert len(edges) == 2

    def test_merge_after_chain(self):
        """Chain on {0,1}, independent on {2,3}, then merge on {0,2}."""
        dag = CallGraphDAG()
        i0 = dag.add_node("a", {0, 1}, 5, ())
        i1 = dag.add_node("b", {0, 1}, 5, ())  # chains after a
        i2 = dag.add_node("c", {2, 3}, 5, ())  # independent
        i3 = dag.add_node("merge", {0, 2}, 5, ())  # merge b and c

        edges = _exec_edges(dag)
        assert _has_exec_edge(dag, i0, i1)
        assert _has_exec_edge(dag, i1, i3)
        assert _has_exec_edge(dag, i2, i3)
        assert not _has_exec_edge(dag, i0, i3)  # no transitive edge
        assert len(edges) == 3


# ---------------------------------------------------------------------------
# All nodes reachable
# ---------------------------------------------------------------------------


class TestReachability:
    """All operation nodes are reachable from the first node(s) via BFS."""

    def _reachable_from_roots(self, dag: CallGraphDAG) -> set[int]:
        """BFS over execution_order edges from nodes with no incoming exec edges."""
        exec_edges = dag.execution_order_edges()
        all_nodes = set(range(dag.node_count))
        targets = {tgt for _, tgt in exec_edges}
        roots = all_nodes - targets  # nodes with no incoming exec edges
        if not roots:
            roots = {0}  # fallback

        visited = set()
        # Build adjacency from execution_order edges
        adj: dict[int, list[int]] = {}
        for src, tgt in exec_edges:
            adj.setdefault(src, []).append(tgt)

        queue = list(roots)
        visited.update(roots)
        while queue:
            node = queue.pop(0)
            for child in adj.get(node, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return visited

    def test_all_nodes_reachable_linear(self):
        dag = CallGraphDAG()
        for k in range(5):
            dag.add_node(f"op{k}", {0}, 1, ())
        reachable = self._reachable_from_roots(dag)
        assert reachable == set(range(5))

    def test_all_nodes_reachable_mixed(self):
        dag = CallGraphDAG()
        dag.add_node("a", {0}, 1, ())
        dag.add_node("b", {1}, 1, ())
        dag.add_node("c", {0, 1}, 1, ())  # merge
        reachable = self._reachable_from_roots(dag)
        assert reachable == {0, 1, 2}

    def test_all_nodes_reachable_disjoint(self):
        """Disjoint ops are all roots -- all reachable trivially."""
        dag = CallGraphDAG()
        dag.add_node("a", {0}, 1, ())
        dag.add_node("b", {1}, 1, ())
        dag.add_node("c", {2}, 1, ())
        reachable = self._reachable_from_roots(dag)
        assert reachable == {0, 1, 2}


# ---------------------------------------------------------------------------
# No redundant (transitive) edges
# ---------------------------------------------------------------------------


class TestNoRedundantEdges:
    """Execution-order edges are minimal: no transitive shortcuts."""

    def test_no_redundant_edges(self):
        """op3 does NOT connect to op1 when op2 is in between on shared qubits."""
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 10, ())
        i1 = dag.add_node("op2", {0, 1}, 10, ())
        i2 = dag.add_node("op3", {0, 1}, 10, ())

        edges = _exec_edges(dag)
        assert (i0, i1) in edges
        assert (i1, i2) in edges
        assert (i0, i2) not in edges  # no transitive edge

    def test_only_immediate_predecessor(self):
        """With 4 serial ops, each only connects to its immediate predecessor."""
        dag = CallGraphDAG()
        indices = [dag.add_node(f"op{k}", {0}, 1, ()) for k in range(4)]
        edges = _exec_edges(dag)
        assert len(edges) == 3
        for k in range(3):
            assert (indices[k], indices[k + 1]) in edges
        # No skip edges
        assert (indices[0], indices[2]) not in edges
        assert (indices[0], indices[3]) not in edges
        assert (indices[1], indices[3]) not in edges


# ---------------------------------------------------------------------------
# Single operation
# ---------------------------------------------------------------------------


class TestSingleOp:
    """Single operation produces no execution_order edges."""

    def test_single_op(self):
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1}, 10, ())
        edges = _exec_edges(dag)
        # No execution_order edges for a single op (no predecessors)
        assert len(edges) == 0


# ---------------------------------------------------------------------------
# Partial overlap
# ---------------------------------------------------------------------------


class TestPartialOverlap:
    """Ops sharing some (not all) qubits are connected."""

    def test_partial_overlap(self):
        """op1 on {0,1}, op2 on {1,2} -> op1->op2 (shared qubit 1)."""
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 10, ())
        i1 = dag.add_node("op2", {1, 2}, 10, ())

        edges = _exec_edges(dag)
        assert (i0, i1) in edges
        assert len(edges) == 1

    def test_partial_overlap_three_ops(self):
        """op1 on {0,1}, op2 on {2,3}, op3 on {1,3} -> merges both."""
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 5, ())
        i1 = dag.add_node("op2", {2, 3}, 5, ())
        i2 = dag.add_node("op3", {1, 3}, 5, ())

        edges = _exec_edges(dag)
        assert _has_exec_edge(dag, i0, i2)  # shared qubit 1
        assert _has_exec_edge(dag, i1, i2)  # shared qubit 3
        assert not _has_exec_edge(dag, i0, i1)  # disjoint
        assert len(edges) == 2


# ---------------------------------------------------------------------------
# Edge type verification
# ---------------------------------------------------------------------------


class TestEdgeType:
    """Execution-order edges have the correct type metadata."""

    def test_edge_type_is_execution_order(self):
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0}, 1, ())
        i1 = dag.add_node("op2", {0}, 1, ())
        edge_indices = dag.dag.edge_indices_from_endpoints(i0, i1)
        exec_found = False
        for eidx in edge_indices:
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict) and edata.get("type") == "execution_order":
                exec_found = True
        assert exec_found

    def test_execution_order_edges_helper(self):
        """execution_order_edges() returns exactly the right edges."""
        dag = CallGraphDAG()
        i0 = dag.add_node("a", {0, 1}, 5, ())
        i1 = dag.add_node("b", {1, 2}, 5, ())
        i2 = dag.add_node("c", {3, 4}, 5, ())  # disjoint

        edges = dag.execution_order_edges()
        assert (i0, i1) in edges
        assert (i0, i2) not in edges
        assert (i1, i2) not in edges
        assert len(edges) == 1


# ---------------------------------------------------------------------------
# Empty qubit set (should not create execution_order edges)
# ---------------------------------------------------------------------------


class TestEmptyQubitSet:
    """Nodes with empty qubit sets do not participate in execution ordering."""

    def test_empty_qubit_set_no_edges(self):
        dag = CallGraphDAG()
        dag.add_node("placeholder", set(), 0, ())
        dag.add_node("op", {0, 1}, 10, ())
        edges = _exec_edges(dag)
        # The placeholder has no qubits, so no execution_order edges from/to it
        assert len(edges) == 0


# ---------------------------------------------------------------------------
# Complex scenario
# ---------------------------------------------------------------------------


class TestComplexScenario:
    """Multi-step scenario combining chains, branches, and merges."""

    def test_diamond_pattern(self):
        """Diamond: root -> A (q0), root -> B (q1), merge C (q0,q1)."""
        dag = CallGraphDAG()
        ia = dag.add_node("A", {0}, 5, ())
        ib = dag.add_node("B", {1}, 5, ())
        ic = dag.add_node("C", {0, 1}, 5, ())

        edges = _exec_edges(dag)
        assert _has_exec_edge(dag, ia, ic)
        assert _has_exec_edge(dag, ib, ic)
        assert not _has_exec_edge(dag, ia, ib)
        assert len(edges) == 2

    def test_interleaved_registers(self):
        """Interleaved operations on two registers."""
        dag = CallGraphDAG()
        # Register A: qubits {0,1}, Register B: qubits {2,3}
        a1 = dag.add_node("add_A", {0, 1}, 10, ())
        b1 = dag.add_node("add_B", {2, 3}, 10, ())
        a2 = dag.add_node("mul_A", {0, 1}, 20, ())
        b2 = dag.add_node("mul_B", {2, 3}, 20, ())

        edges = _exec_edges(dag)
        # Chain within register A: a1 -> a2
        assert _has_exec_edge(dag, a1, a2)
        # Chain within register B: b1 -> b2
        assert _has_exec_edge(dag, b1, b2)
        # No cross-register edges
        assert not _has_exec_edge(dag, a1, b1)
        assert not _has_exec_edge(dag, a1, b2)
        assert not _has_exec_edge(dag, a2, b1)
        assert not _has_exec_edge(dag, a2, b2)
        assert len(edges) == 2

    def test_qubit_last_node_updated(self):
        """Internal _qubit_last_node map tracks the last op per qubit."""
        dag = CallGraphDAG()
        i0 = dag.add_node("op1", {0, 1}, 5, ())
        i1 = dag.add_node("op2", {1, 2}, 5, ())
        # After op2: qubit 0 -> op1, qubit 1 -> op2, qubit 2 -> op2
        assert dag._qubit_last_node[0] == i0
        assert dag._qubit_last_node[1] == i1
        assert dag._qubit_last_node[2] == i1

    def test_fan_out_pattern(self):
        """One op on many qubits, then separate ops on subsets."""
        dag = CallGraphDAG()
        root = dag.add_node("big_op", {0, 1, 2, 3}, 50, ())
        a = dag.add_node("sub_a", {0, 1}, 10, ())
        b = dag.add_node("sub_b", {2, 3}, 10, ())

        edges = _exec_edges(dag)
        assert _has_exec_edge(dag, root, a)
        assert _has_exec_edge(dag, root, b)
        assert not _has_exec_edge(dag, a, b)
        assert len(edges) == 2


# ---------------------------------------------------------------------------
# Step 0.3: No overlap edge type
# ---------------------------------------------------------------------------


class TestNoOverlapEdgeType:
    """After removing build_overlap_edges(), no overlap edges should exist."""

    def test_no_overlap_edge_type(self):
        """No edge in the DAG has type == 'overlap'."""
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1, 2}, 10, ())
        dag.add_node("op2", {1, 2, 3}, 8, ())
        dag.add_node("op3", {0, 3}, 5, ())
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict):
                assert edata.get("type") != "overlap", (
                    f"Found unexpected 'overlap' edge: {edata}"
                )

    def test_edge_set_matches_execution_order(self):
        """Edge set is identical to the Step 0.1 execution-order algorithm output."""
        dag = CallGraphDAG()
        # Build a mixed topology: chain + branch + merge
        i0 = dag.add_node("a", {0, 1}, 5, ())
        i1 = dag.add_node("b", {0, 1}, 5, ())  # chains after a
        i2 = dag.add_node("c", {2, 3}, 5, ())   # independent branch
        i3 = dag.add_node("merge", {1, 2}, 5, ())  # merges b and c

        # All edges should be execution_order type only
        all_edges = dag.dag.edge_list()
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            assert edata.get("type") == "execution_order"

        exec_edges = dag.execution_order_edges()
        assert (i0, i1) in exec_edges
        assert (i1, i3) in exec_edges
        assert (i2, i3) in exec_edges
        assert len(exec_edges) == 3

    def test_no_build_overlap_edges_method(self):
        """CallGraphDAG no longer has a build_overlap_edges() method."""
        dag = CallGraphDAG()
        assert not hasattr(dag, "build_overlap_edges")
