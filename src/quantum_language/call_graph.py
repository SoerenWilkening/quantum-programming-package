"""Call graph DAG module for tracking compiled function call structure.

Provides CallGraphDAG (rustworkx-backed directed graph), DAGNode (per-invocation
metadata with pre-computed qubit bitmask), and a module-level builder stack for
nested call tracking during @ql.compile execution.

The overlap computation uses NumPy bitmask intersection with a byte-level
popcount LUT for fast pairwise qubit overlap detection.
"""

from __future__ import annotations

import numpy as np
import rustworkx as rx

# ---------------------------------------------------------------------------
# Popcount lookup table (module-level, computed once)
# ---------------------------------------------------------------------------

_POPCOUNT_LUT: np.ndarray = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def _popcount_array(arr: np.ndarray) -> np.ndarray:
    """Vectorized popcount using byte LUT.

    Parameters
    ----------
    arr : np.ndarray of uint64
        Array of bitmask values.

    Returns
    -------
    np.ndarray of int32
        Popcount for each element.
    """
    result = np.zeros(len(arr), dtype=np.int32)
    for shift in range(0, 64, 8):
        byte_vals = ((arr >> np.uint64(shift)) & np.uint64(0xFF)).astype(np.uint8)
        result += _POPCOUNT_LUT[byte_vals].astype(np.int32)
    return result


# ---------------------------------------------------------------------------
# Per-node stat helpers
# ---------------------------------------------------------------------------


def _compute_depth(gates: list) -> int:
    """Compute circuit depth via ASAP qubit occupancy scheduling.

    For each gate, collects target + control qubits, finds the max current
    time across those qubits, and assigns all to max+1. Returns the overall
    maximum time step, or 0 for an empty list.
    """
    if not gates:
        return 0
    occupancy: dict[int, int] = {}
    max_depth = 0
    for g in gates:
        qubits = [g["target"]]
        if g.get("num_controls", 0) > 0:
            qubits.extend(g["controls"])
        current_max = max((occupancy.get(q, 0) for q in qubits), default=0)
        new_time = current_max + 1
        for q in qubits:
            occupancy[q] = new_time
        if new_time > max_depth:
            max_depth = new_time
    return max_depth


def _compute_t_count(gates: list) -> int:
    """Compute T-gate count using dual formula.

    Counts direct T_GATE (type 10) and TDG_GATE (type 11) occurrences.
    If none found, falls back to 7 * CCX count (gates with num_controls >= 2).
    """
    if not gates:
        return 0
    t_direct = 0
    ccx_count = 0
    for g in gates:
        gtype = g.get("type", -1)
        if gtype == 10 or gtype == 11:
            t_direct += 1
        if g.get("num_controls", 0) >= 2:
            ccx_count += 1
    return t_direct if t_direct > 0 else 7 * ccx_count


# ---------------------------------------------------------------------------
# DAGNode
# ---------------------------------------------------------------------------


class DAGNode:
    """Data stored at each node in the call graph DAG.

    Attributes
    ----------
    func_name : str
        Name of the compiled function.
    qubit_set : frozenset[int]
        Physical qubit indices touched by this invocation.
    gate_count : int
        Number of gates in the compiled block.
    cache_key : tuple
        Cache key identifying this compiled variant.
    bitmask : np.uint64
        Pre-computed bitmask encoding qubit_set for fast overlap.
    """

    __slots__ = (
        "func_name",
        "qubit_set",
        "gate_count",
        "cache_key",
        "bitmask",
        "depth",
        "t_count",
        "_block_ref",
        "_v2r_ref",
    )

    def __init__(
        self,
        func_name: str,
        qubit_set,
        gate_count: int,
        cache_key: tuple,
        *,
        depth: int = 0,
        t_count: int = 0,
    ):
        self.func_name = func_name
        self.qubit_set = frozenset(qubit_set)
        self.gate_count = gate_count
        self.cache_key = cache_key
        self.depth = depth
        self.t_count = t_count
        self._block_ref = None  # CompiledBlock ref for merge (opt=2)
        self._v2r_ref = None  # virtual-to-real mapping for merge (opt=2)
        # Pre-compute bitmask from qubit_set
        bitmask = np.uint64(0)
        for q in qubit_set:
            bitmask |= np.uint64(1 << q)
        self.bitmask = bitmask

    def __repr__(self) -> str:
        return (
            f"DAGNode({self.func_name!r}, qubits={set(self.qubit_set)}, "
            f"gates={self.gate_count}, depth={self.depth}, t_count={self.t_count})"
        )


# ---------------------------------------------------------------------------
# CallGraphDAG
# ---------------------------------------------------------------------------


class CallGraphDAG:
    """Call graph DAG capturing program structure from @ql.compile calls.

    Wraps a rustworkx PyDAG with convenience methods for overlap edge
    computation and parallel group detection.
    """

    def __init__(self):
        self._dag: rx.PyDAG = rx.PyDAG()
        self._nodes: list[DAGNode] = []

    # -- Node management ----------------------------------------------------

    def add_node(
        self,
        func_name: str,
        qubit_set,
        gate_count: int,
        cache_key: tuple,
        parent_index: int | None = None,
        *,
        depth: int = 0,
        t_count: int = 0,
    ) -> int:
        """Add a node to the DAG.

        Parameters
        ----------
        func_name : str
            Name of the compiled function.
        qubit_set : set or frozenset of int
            Physical qubit indices.
        gate_count : int
            Number of gates.
        cache_key : tuple
            Cache key for this compiled variant.
        parent_index : int or None
            If not None, add a hierarchical 'call' edge from parent to this node.
        depth : int
            Circuit depth for this node.
        t_count : int
            T-gate count for this node.

        Returns
        -------
        int
            Index of the newly added node.
        """
        node = DAGNode(func_name, qubit_set, gate_count, cache_key, depth=depth, t_count=t_count)
        idx = self._dag.add_node(node)
        self._nodes.append(node)
        if parent_index is not None:
            self._dag.add_edge(parent_index, idx, {"type": "call"})
        return idx

    # -- Overlap edge computation -------------------------------------------

    def build_overlap_edges(self) -> None:
        """Compute qubit overlap edges between all node pairs.

        For each pair (i, j) where i < j, computes bitmask AND + popcount.
        If weight > 0 and no existing 'call' edge exists between them,
        adds an edge with data ``{'type': 'overlap', 'weight': w}``.
        """
        n = len(self._nodes)
        if n < 2:
            return

        # Collect existing call-edge pairs to skip
        call_pairs: set[tuple[int, int]] = set()
        for src, tgt in self._dag.edge_list():
            edge_data = self._dag.get_edge_data(src, tgt)
            if isinstance(edge_data, dict) and edge_data.get("type") == "call":
                call_pairs.add((min(src, tgt), max(src, tgt)))

        bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)

        for i in range(n):
            overlaps = np.bitwise_and(bitmasks[i], bitmasks[i + 1 :])
            weights = _popcount_array(overlaps)
            for j_off in range(len(weights)):
                w = int(weights[j_off])
                if w > 0:
                    j = i + 1 + j_off
                    pair = (i, j)
                    if pair not in call_pairs:
                        self._dag.add_edge(i, j, {"type": "overlap", "weight": w})

    # -- Parallel group detection -------------------------------------------

    def parallel_groups(self) -> list[set[int]]:
        """Return list of sets of node indices that are mutually qubit-disjoint.

        Builds an undirected overlap graph and returns its connected components.
        Nodes within the same component share qubits (directly or transitively).
        Nodes in different components are fully independent.
        """
        n = len(self._nodes)
        if n == 0:
            return []

        g = rx.PyGraph()
        for _ in range(n):
            g.add_node(None)

        if n < 2:
            return [set(comp) for comp in rx.connected_components(g)]

        bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)

        for i in range(n):
            overlaps = np.bitwise_and(bitmasks[i], bitmasks[i + 1 :])
            weights = _popcount_array(overlaps)
            for j_off in range(len(weights)):
                if weights[j_off] > 0:
                    g.add_edge(i, i + 1 + j_off, int(weights[j_off]))

        return [set(comp) for comp in rx.connected_components(g)]

    # -- Merge group detection -----------------------------------------------

    def merge_groups(self, threshold: int = 1) -> list[list[int]]:
        """Connected components where all overlap edges >= threshold.

        Returns list of sorted node-index lists. Single-node groups excluded.

        Parameters
        ----------
        threshold : int
            Minimum qubit overlap (popcount of bitmask AND) for two nodes
            to be considered merge candidates. Default 1.

        Returns
        -------
        list[list[int]]
            Each inner list is a group of node indices sorted in temporal
            (insertion) order. Only groups with 2+ nodes are returned.
        """
        n = len(self._nodes)
        if n < 2:
            return []
        g = rx.PyGraph()
        for _ in range(n):
            g.add_node(None)
        bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)
        for i in range(n):
            overlaps = np.bitwise_and(bitmasks[i], bitmasks[i + 1 :])
            weights = _popcount_array(overlaps)
            for j_off in range(len(weights)):
                if weights[j_off] >= threshold:
                    g.add_edge(i, i + 1 + j_off, int(weights[j_off]))
        components = rx.connected_components(g)
        return [sorted(comp) for comp in components if len(comp) > 1]

    # -- Aggregate metrics ---------------------------------------------------

    def aggregate(self) -> dict:
        """Compute aggregate metrics across all nodes in the DAG.

        Returns
        -------
        dict
            Keys: gates (total gate count), depth (critical-path depth),
            qubits (number of unique physical qubits), t_count (total T-gates).
            Critical-path depth = sum of per-group max depths, where groups
            are determined by parallel_groups() (qubit-disjoint components).
        """
        if not self._nodes:
            return {"gates": 0, "depth": 0, "qubits": 0, "t_count": 0}

        total_gates = sum(n.gate_count for n in self._nodes)
        total_t = sum(n.t_count for n in self._nodes)
        all_qubits: set[int] = set()
        for n in self._nodes:
            all_qubits.update(n.qubit_set)

        groups = self.parallel_groups()
        total_depth = sum(max(self._nodes[idx].depth for idx in group) for group in groups)

        return {
            "gates": total_gates,
            "depth": total_depth,
            "qubits": len(all_qubits),
            "t_count": total_t,
        }

    # -- DOT export ---------------------------------------------------------

    def to_dot(self) -> str:
        """Return a DOT-language string representing the call graph.

        Nodes are rendered as boxes with multi-line labels showing function
        name, gate count, depth, qubit count, and T-count. Call edges are
        solid arrows labeled "call"; overlap edges are dashed arrows labeled
        with shared qubit count. When multiple parallel groups exist, each
        group is wrapped in a ``subgraph cluster_N`` with dotted border.

        Returns
        -------
        str
            Valid DOT string starting with ``digraph CallGraph {``.
        """
        lines: list[str] = []
        lines.append("digraph CallGraph {")
        lines.append("  rankdir=TB;")
        lines.append('  node [shape=box, fontname="Courier"];')

        groups = self.parallel_groups()
        # Build node -> group mapping
        node_to_group: dict[int, int] = {}
        for gi, group in enumerate(groups):
            for idx in group:
                node_to_group[idx] = gi

        use_clusters = len(groups) > 1

        def _node_label(idx: int) -> str:
            nd = self._nodes[idx]
            name = nd.func_name.replace('"', '\\"')
            return (
                f"{name}\\n"
                f"gates: {nd.gate_count}\\n"
                f"depth: {nd.depth}\\n"
                f"qubits: {len(nd.qubit_set)}\\n"
                f"T-count: {nd.t_count}"
            )

        def _emit_node(idx: int) -> str:
            return f'  n{idx} [label="{_node_label(idx)}"];'

        if use_clusters:
            for gi, group in enumerate(groups):
                lines.append(f"  subgraph cluster_{gi} {{")
                lines.append("    style=dotted;")
                lines.append(f'    label="Group {gi}";')
                for idx in sorted(group):
                    lines.append(f"  {_emit_node(idx)}")
                lines.append("  }")
        else:
            for idx in range(len(self._nodes)):
                lines.append(_emit_node(idx))

        # Edges
        for src, tgt in self._dag.edge_list():
            edge_data = self._dag.get_edge_data(src, tgt)
            if isinstance(edge_data, dict):
                if edge_data.get("type") == "call":
                    lines.append(f'  n{src} -> n{tgt} [label="call"];')
                elif edge_data.get("type") == "overlap":
                    w = edge_data.get("weight", 0)
                    lines.append(f'  n{src} -> n{tgt} [style=dashed, label="{w} qubits"];')

        lines.append("}")
        return "\n".join(lines)

    # -- Compilation report --------------------------------------------------

    def report(self) -> str:
        """Return a formatted compilation report string.

        The report includes a header with the top-level function name,
        a table with per-node stats (Name, Gates, Depth, Qubits, T-count,
        Group), and an aggregate totals footer row.

        Returns
        -------
        str
            Multi-line formatted report.
        """
        if not self._nodes:
            return "Compilation Report: (empty)\n\nNo nodes."

        top_name = self._nodes[0].func_name
        groups = self.parallel_groups()
        node_to_group: dict[int, int] = {}
        for gi, group in enumerate(groups):
            for idx in group:
                node_to_group[idx] = gi

        agg = self.aggregate()

        lines: list[str] = []
        lines.append(f"Compilation Report: {top_name}")
        lines.append("")

        # Column widths: Name=20, Gates=8, Depth=8, Qubits=8, T-count=8, Group=8
        header = (
            f"{'Name':<20s} | {'Gates':>8s} | {'Depth':>8s} | "
            f"{'Qubits':>8s} | {'T-count':>8s} | {'Group':>8s}"
        )
        sep = "-" * len(header)
        lines.append(header)
        lines.append(sep)

        for idx, nd in enumerate(self._nodes):
            grp = node_to_group.get(idx, 0)
            row = (
                f"{nd.func_name:<20s} | {nd.gate_count:>8d} | {nd.depth:>8d} | "
                f"{len(nd.qubit_set):>8d} | {nd.t_count:>8d} | {grp:>8d}"
            )
            lines.append(row)

        lines.append(sep)
        totals = (
            f"{'TOTAL':<20s} | {agg['gates']:>8d} | {agg['depth']:>8d} | "
            f"{agg['qubits']:>8d} | {agg['t_count']:>8d} | {'-':>8s}"
        )
        lines.append(totals)

        return "\n".join(lines)

    # -- Properties ---------------------------------------------------------

    @property
    def nodes(self) -> list[DAGNode]:
        """Return list of DAGNode objects."""
        return list(self._nodes)

    @property
    def node_count(self) -> int:
        """Return number of nodes in the DAG."""
        return len(self._nodes)

    @property
    def dag(self) -> rx.PyDAG:
        """Return the underlying rustworkx PyDAG for advanced queries."""
        return self._dag

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"CallGraphDAG(nodes={len(self._nodes)}, edges={len(self._dag.edge_list())})"


# ---------------------------------------------------------------------------
# Builder stack (module-level, mirrors _capture_depth pattern)
# ---------------------------------------------------------------------------

_dag_builder_stack: list[tuple[CallGraphDAG, int | None]] = []
"""Stack of (CallGraphDAG, parent_node_index_or_None) tuples.

Used during @ql.compile execution to track the active DAG and current
parent node for nested call recording.
"""


def push_dag_context(dag: CallGraphDAG, parent_index: int | None = None) -> None:
    """Push a DAG context onto the builder stack.

    Parameters
    ----------
    dag : CallGraphDAG
        The DAG being built.
    parent_index : int or None
        Node index of the current parent (for nested calls).
    """
    _dag_builder_stack.append((dag, parent_index))


def pop_dag_context() -> tuple[CallGraphDAG, int | None] | None:
    """Pop the top DAG context from the builder stack.

    Returns
    -------
    tuple of (CallGraphDAG, int or None) or None
        The popped context, or None if stack was empty.
    """
    if not _dag_builder_stack:
        return None
    return _dag_builder_stack.pop()


def current_dag_context() -> tuple[CallGraphDAG, int | None] | None:
    """Return the top of the builder stack without popping.

    Returns
    -------
    tuple of (CallGraphDAG, int or None) or None
        The current context, or None if stack is empty.
    """
    if not _dag_builder_stack:
        return None
    return _dag_builder_stack[-1]
