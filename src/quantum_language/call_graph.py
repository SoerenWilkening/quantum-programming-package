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

    __slots__ = ("func_name", "qubit_set", "gate_count", "cache_key", "bitmask", "depth", "t_count")

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
