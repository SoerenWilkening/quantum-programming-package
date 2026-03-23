"""Call graph DAG module for tracking compiled function call structure.

Provides CallGraphDAG (rustworkx-backed directed graph), DAGNode (per-invocation
metadata with pre-computed qubit bitmask), and a module-level builder stack for
operation recording during @ql.compile execution.

Edges represent execution ordering: operations sharing qubits are linked
incrementally during capture via a last_node_per_qubit map.
"""

from __future__ import annotations

import numpy as np
import rustworkx as rx

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
# Dual gate count formatting
# ---------------------------------------------------------------------------


def _format_dual(uncontrolled: int, controlled: int) -> str:
    """Format dual U/C values as ``'X / Y'`` with ``'-'`` for unavailable.

    Parameters
    ----------
    uncontrolled : int
        Value for the uncontrolled variant.  0 means unavailable.
    controlled : int
        Value for the controlled variant.  0 means unavailable.

    Returns
    -------
    str
        Formatted string, e.g. ``'24 / 18'``, ``'24 / -'``, ``'- / 18'``.
    """
    uc = str(uncontrolled) if uncontrolled else "-"
    ct = str(controlled) if controlled else "-"
    return f"{uc} / {ct}"


# Backward-compatible alias
_format_dual_gates = _format_dual


# ---------------------------------------------------------------------------
# Sequence gate count resolution
# ---------------------------------------------------------------------------

try:
    from ._core import _sequence_gate_count
except ImportError:
    _sequence_gate_count = None


def _resolve_gate_count(seq_ptr: int) -> int:
    """Resolve gate count from a sequence pointer.

    Uses ``_sequence_gate_count`` from the Cython layer when available.
    Returns 0 when the helper is not yet built or the pointer is null.
    """
    if _sequence_gate_count is None or seq_ptr == 0:
        return 0
    return _sequence_gate_count(seq_ptr)


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
    uncontrolled_gate_count : int
        Gate count for the uncontrolled variant (from ``_sequence_gate_count``).
        0 when the uncontrolled sequence pointer is unavailable.
    controlled_gate_count : int
        Gate count for the controlled variant (from ``_sequence_gate_count``).
        0 when the controlled sequence pointer is unavailable.
    cache_key : tuple
        Cache key identifying this compiled variant.
    bitmask : int
        Pre-computed bitmask encoding qubit_set (Python int for >64 qubit support).
    depth : int
        Circuit depth for this node.
    t_count : int
        T-gate count for this node.
    uncontrolled_depth : int
        Circuit depth for the uncontrolled variant.  0 when unavailable.
    controlled_depth : int
        Circuit depth for the controlled variant.  0 when unavailable.
    uncontrolled_t_count : int
        T-gate count for the uncontrolled variant.  0 when unavailable.
    controlled_t_count : int
        T-gate count for the controlled variant.  0 when unavailable.
    sequence_ptr : int
        C pointer to ``sequence_t`` (cast to Python int). Used for call-graph
        replay without re-executing the function body.
    uncontrolled_seq : int
        Pointer to the uncontrolled ``sequence_t`` variant (as Python int), or 0.
    controlled_seq : int
        Pointer to the controlled ``sequence_t`` variant (as Python int), or 0.
    qubit_mapping : tuple[int, ...]
        Physical qubit indices for ``run_instruction``.
    operation_type : str
        Operation identifier (e.g. ``"add"``, ``"mul"``, ``"xor"``, ``"eq"``).
    invert : bool
        Whether this is an inverse (uncomputation) operation.
    """

    __slots__ = (
        "func_name",
        "qubit_set",
        "gate_count",
        "uncontrolled_gate_count",
        "controlled_gate_count",
        "cache_key",
        "bitmask",
        "depth",
        "t_count",
        "uncontrolled_depth",
        "controlled_depth",
        "uncontrolled_t_count",
        "controlled_t_count",
        "sequence_ptr",
        "uncontrolled_seq",
        "controlled_seq",
        "qubit_mapping",
        "operation_type",
        "invert",
        "controlled",
        "is_call_node",
        "_merged",
        "_block_ref",
        "_v2r_ref",
        "_qubit_array",
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
        uncontrolled_depth: int = 0,
        controlled_depth: int = 0,
        uncontrolled_t_count: int = 0,
        controlled_t_count: int = 0,
        sequence_ptr: int = 0,
        uncontrolled_seq: int = 0,
        controlled_seq: int = 0,
        uncontrolled_gate_count: int = 0,
        controlled_gate_count: int = 0,
        qubit_mapping: tuple = (),
        operation_type: str = "",
        invert: bool = False,
        controlled: bool = False,
        is_call_node: bool = False,
    ):
        self.func_name = func_name
        self.qubit_set = frozenset(qubit_set)
        self._qubit_array = np.array(sorted(self.qubit_set), dtype=np.intp)
        self.gate_count = gate_count
        self.uncontrolled_gate_count = uncontrolled_gate_count
        self.controlled_gate_count = controlled_gate_count
        self.cache_key = cache_key
        self.depth = depth
        self.t_count = t_count
        self.uncontrolled_depth = uncontrolled_depth
        self.controlled_depth = controlled_depth
        self.uncontrolled_t_count = uncontrolled_t_count
        self.controlled_t_count = controlled_t_count
        self.sequence_ptr = sequence_ptr
        self.uncontrolled_seq = uncontrolled_seq
        self.controlled_seq = controlled_seq
        self.qubit_mapping = qubit_mapping
        self.operation_type = operation_type
        self.invert = invert
        self.controlled = controlled
        self.is_call_node = is_call_node
        self._merged = False  # True when this node was merged into another
        self._block_ref = None  # CompiledBlock ref for merge (opt=2)
        self._v2r_ref = None  # virtual-to-real mapping for merge (opt=2)
        # Pre-compute bitmask from qubit_set (Python int for >64 qubit support)
        bitmask = 0
        for q in qubit_set:
            bitmask |= 1 << q
        self.bitmask = bitmask

    def __repr__(self) -> str:
        parts = [
            f"DAGNode({self.func_name!r}, qubits={set(self.qubit_set)}, "
            f"gates={self.gate_count}, depth={self.depth}, t_count={self.t_count}"
        ]
        if self.operation_type:
            parts.append(f", op={self.operation_type!r}")
        if self.invert:
            parts.append(", invert=True")
        if self.controlled:
            parts.append(", controlled=True")
        parts.append(")")
        return "".join(parts)


# ---------------------------------------------------------------------------
# CallGraphDAG
# ---------------------------------------------------------------------------


class CallGraphDAG:
    """Call graph DAG capturing program structure from @ql.compile calls.

    Wraps a rustworkx PyDAG with convenience methods for execution-order
    edge construction, parallel group detection, and graph immutability.
    """

    def __init__(self):
        self._dag: rx.PyDAG = rx.PyDAG()
        self._nodes: list[DAGNode] = []
        self._qubit_last_node: dict[int, int] = {}
        self._frozen: bool = False

    # -- Node management ----------------------------------------------------

    def add_node(
        self,
        func_name: str,
        qubit_set,
        gate_count: int,
        cache_key: tuple,
        *,
        depth: int = 0,
        t_count: int = 0,
        uncontrolled_depth: int = 0,
        controlled_depth: int = 0,
        uncontrolled_t_count: int = 0,
        controlled_t_count: int = 0,
        sequence_ptr: int = 0,
        uncontrolled_seq: int = 0,
        controlled_seq: int = 0,
        uncontrolled_gate_count: int = 0,
        controlled_gate_count: int = 0,
        qubit_mapping: tuple = (),
        operation_type: str = "",
        invert: bool = False,
        controlled: bool = False,
        is_call_node: bool = False,
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
        depth : int
            Circuit depth for this node.
        t_count : int
            T-gate count for this node.
        uncontrolled_depth : int
            Circuit depth for the uncontrolled variant.
        controlled_depth : int
            Circuit depth for the controlled variant.
        uncontrolled_t_count : int
            T-gate count for the uncontrolled variant.
        controlled_t_count : int
            T-gate count for the controlled variant.
        sequence_ptr : int
            C pointer to ``sequence_t`` (cast to Python int).
        uncontrolled_seq : int
            Pointer to the uncontrolled ``sequence_t`` variant (as Python int).
        controlled_seq : int
            Pointer to the controlled ``sequence_t`` variant (as Python int).
        uncontrolled_gate_count : int
            Gate count for the uncontrolled variant.
        controlled_gate_count : int
            Gate count for the controlled variant.
        qubit_mapping : tuple of int
            Physical qubit indices for ``run_instruction``.
        operation_type : str
            Operation identifier (e.g. ``"add"``, ``"mul"``, ``"xor"``).
        invert : bool
            Whether this is an inverse operation.
        controlled : bool
            Whether this call was inside a controlled context.
        is_call_node : bool
            Whether this node represents a hierarchical call reference
            (from a ``CallRecord``).

        Returns
        -------
        int
            Index of the newly added node.

        Raises
        ------
        RuntimeError
            If the DAG has been frozen via ``freeze()``.
        """
        if self._frozen:
            raise RuntimeError(
                "Cannot add node to frozen CallGraphDAG. The graph is immutable after capture."
            )
        node = DAGNode(
            func_name,
            qubit_set,
            gate_count,
            cache_key,
            depth=depth,
            t_count=t_count,
            uncontrolled_depth=uncontrolled_depth,
            controlled_depth=controlled_depth,
            uncontrolled_t_count=uncontrolled_t_count,
            controlled_t_count=controlled_t_count,
            sequence_ptr=sequence_ptr,
            uncontrolled_seq=uncontrolled_seq,
            controlled_seq=controlled_seq,
            uncontrolled_gate_count=uncontrolled_gate_count,
            controlled_gate_count=controlled_gate_count,
            qubit_mapping=qubit_mapping,
            operation_type=operation_type,
            invert=invert,
            controlled=controlled,
            is_call_node=is_call_node,
        )
        idx = self._dag.add_node(node)
        self._nodes.append(node)
        # Build execution-order edges for nodes with qubit information.
        if qubit_set:
            self._connect_by_execution_order(idx, node.qubit_set)
        return idx

    def _connect_by_execution_order(self, node_idx: int, qubit_set: frozenset) -> None:
        """Add execution-order edges from predecessor nodes to *node_idx*.

        For each qubit in *qubit_set*, look up the last node that touched it
        in ``_qubit_last_node``.  Collect the unique set of parent node
        indices.  Add an ``{"type": "execution_order"}`` edge from each
        parent to *node_idx*.  If no parents are found the node is an
        execution-order root (first to touch these qubits).

        After adding edges, update ``_qubit_last_node[q] = node_idx`` for
        every qubit in *qubit_set*.
        """
        parents: set[int] = set()
        for q in qubit_set:
            prev = self._qubit_last_node.get(q)
            if prev is not None:
                parents.add(prev)

        for p in parents:
            self._dag.add_edge(p, node_idx, {"type": "execution_order"})

        for q in qubit_set:
            self._qubit_last_node[q] = node_idx

    def add_call_edge(self, caller_idx: int, callee_idx: int) -> None:
        """Add a call relationship edge from caller to callee.

        These edges represent hierarchical function call relationships
        (outer compiled function calls inner compiled function).  They
        are distinct from execution-order edges.

        Parameters
        ----------
        caller_idx : int
            Node index of the calling (outer) function.
        callee_idx : int
            Node index of the called (inner) function.
        """
        self._dag.add_edge(caller_idx, callee_idx, {"type": "call"})

    def call_edges(self) -> list[tuple[int, int]]:
        """Return all call relationship edges as (caller, callee) pairs."""
        result = []
        for eidx in self._dag.edge_indices():
            edata = self._dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict) and edata.get("type") == "call":
                src, tgt = self._dag.get_edge_endpoints_by_index(eidx)
                result.append((src, tgt))
        return result

    # -- Freeze control -----------------------------------------------------

    def freeze(self) -> None:
        """Freeze the DAG, making it immutable.

        After calling this method, ``add_node()`` will raise
        ``RuntimeError``.  Read-only methods (``report()``, ``to_dot()``,
        ``parallel_groups()``, etc.) continue to work normally.
        """
        self._frozen = True

    @property
    def frozen(self) -> bool:
        """Return whether the DAG has been frozen."""
        return self._frozen

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

        for i in range(n):
            arr_i = self._nodes[i]._qubit_array
            for j in range(i + 1, n):
                w = len(np.intersect1d(arr_i, self._nodes[j]._qubit_array))
                if w > 0:
                    g.add_edge(i, j, w)

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
        for i in range(n):
            arr_i = self._nodes[i]._qubit_array
            for j in range(i + 1, n):
                w = len(np.intersect1d(arr_i, self._nodes[j]._qubit_array))
                if w >= threshold:
                    g.add_edge(i, j, w)
        components = rx.connected_components(g)
        return [sorted(comp) for comp in components if len(comp) > 1]

    # -- Aggregate metrics ---------------------------------------------------

    def aggregate(self) -> dict:
        """Compute aggregate metrics across all nodes in the DAG.

        Returns
        -------
        dict
            Keys: gates (total gate count), depth (critical-path depth),
            qubits (number of unique physical qubits), t_count (total T-gates),
            gates_uc, gates_cc (per-context gate totals),
            depth_uc, depth_cc (per-context critical-path depth),
            t_count_uc, t_count_cc (per-context T-gate totals).
        """
        if not self._nodes:
            return {
                "gates": 0,
                "depth": 0,
                "qubits": 0,
                "t_count": 0,
                "gates_uc": 0,
                "gates_cc": 0,
                "depth_uc": 0,
                "depth_cc": 0,
                "t_count_uc": 0,
                "t_count_cc": 0,
            }

        active = [n for n in self._nodes if not n._merged]
        total_gates = sum(n.gate_count for n in active)
        total_t = sum(n.t_count for n in active)
        all_qubits: set[int] = set()
        for n in active:
            all_qubits.update(n.qubit_set)

        groups = self.parallel_groups()
        total_depth = sum(
            max(
                (self._nodes[idx].depth for idx in group if not self._nodes[idx]._merged), default=0
            )
            for group in groups
        )

        # Per-context totals
        gates_uc = sum(n.uncontrolled_gate_count for n in active)
        gates_cc = sum(n.controlled_gate_count for n in active)
        depth_uc = sum(
            max(
                (
                    self._nodes[idx].uncontrolled_depth
                    for idx in group
                    if not self._nodes[idx]._merged
                ),
                default=0,
            )
            for group in groups
        )
        depth_cc = sum(
            max(
                (
                    self._nodes[idx].controlled_depth
                    for idx in group
                    if not self._nodes[idx]._merged
                ),
                default=0,
            )
            for group in groups
        )
        t_count_uc = sum(n.uncontrolled_t_count for n in active)
        t_count_cc = sum(n.controlled_t_count for n in active)

        return {
            "gates": total_gates,
            "depth": total_depth,
            "qubits": len(all_qubits),
            "t_count": total_t,
            "gates_uc": gates_uc,
            "gates_cc": gates_cc,
            "depth_uc": depth_uc,
            "depth_cc": depth_cc,
            "t_count_uc": t_count_uc,
            "t_count_cc": t_count_cc,
        }

    # -- DOT export ---------------------------------------------------------

    def to_dot(self, *, file_prefix: str | None = None) -> str:
        """Return a DOT-language string representing the call graph.

        Nodes are rendered as boxes with multi-line labels showing function
        name, gate count, depth, qubit count, and T-count. Execution-order
        edges are solid arrows labeled "exec". When multiple parallel
        groups exist, each group is wrapped in a ``subgraph cluster_N``
        with dotted border.

        Parameters
        ----------
        file_prefix : str or None
            When provided, each node includes a ``URL`` attribute pointing
            to ``{file_prefix}_{func_name}.png``, enabling hyperlinked
            navigation to per-function sub-diagrams in rendered SVGs/PDFs.

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
            dual_gates = _format_dual(nd.uncontrolled_gate_count, nd.controlled_gate_count)
            dual_depth = _format_dual(nd.uncontrolled_depth, nd.controlled_depth)
            dual_t = _format_dual(nd.uncontrolled_t_count, nd.controlled_t_count)
            return (
                f"{name}\\n"
                f"gates: {dual_gates}\\n"
                f"depth: {dual_depth}\\n"
                f"qubits: {len(nd.qubit_set)}\\n"
                f"T-count: {dual_t}"
            )

        def _node_url(idx: int) -> str:
            nd = self._nodes[idx]
            name = nd.func_name.replace(" ", "_")
            return f"{file_prefix}_{name}.png"

        def _emit_node(idx: int) -> str:
            nd = self._nodes[idx]
            url_attr = ""
            if file_prefix is not None:
                url_attr = f', URL="{_node_url(idx)}"'
            if nd.is_call_node:
                return f'  n{idx} [label="{_node_label(idx)}", style=dashed{url_attr}];'
            return f'  n{idx} [label="{_node_label(idx)}"{url_attr}];'

        if use_clusters:
            for gi, group in enumerate(groups):
                lines.append(f"  subgraph cluster_{gi} {{")
                lines.append("    style=dotted;")
                lines.append(f'    label="Group {gi}";')
                for idx in sorted(group):
                    if not self._nodes[idx]._merged:
                        lines.append(f"  {_emit_node(idx)}")
                lines.append("  }")
        else:
            for idx in range(len(self._nodes)):
                if not self._nodes[idx]._merged:
                    lines.append(_emit_node(idx))

        # Edges (iterate by index to handle multi-edges correctly)
        for eidx in self._dag.edge_indices():
            src, tgt = self._dag.get_edge_endpoints_by_index(eidx)
            # Skip edges referencing merged nodes (no corresponding node definition)
            if self._nodes[src]._merged or self._nodes[tgt]._merged:
                continue
            edge_data = self._dag.get_edge_data_by_index(eidx)
            if isinstance(edge_data, dict):
                etype = edge_data.get("type")
                if etype == "execution_order":
                    lines.append(f'  n{src} -> n{tgt} [label="exec"];')
                elif etype == "call":
                    lines.append(f'  n{src} -> n{tgt} [label="call", style=dashed, color=blue];')

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

        # Column widths: Name=20, Gates(U/C)=15, Depth(U/C)=15, Qubits=8, T-count(U/C)=15, Group=8
        header = (
            f"{'Name':<20s} | {'Gates (U/C)':>15s} | {'Depth (U/C)':>15s} | "
            f"{'Qubits':>8s} | {'T-count (U/C)':>15s} | {'Group':>8s}"
        )
        sep = "-" * len(header)
        lines.append(header)
        lines.append(sep)

        for idx, nd in enumerate(self._nodes):
            if nd._merged:
                continue
            grp = node_to_group.get(idx, 0)
            dual_gates = _format_dual(nd.uncontrolled_gate_count, nd.controlled_gate_count)
            dual_depth = _format_dual(nd.uncontrolled_depth, nd.controlled_depth)
            dual_t = _format_dual(nd.uncontrolled_t_count, nd.controlled_t_count)
            row = (
                f"{nd.func_name:<20s} | {dual_gates:>15s} | {dual_depth:>15s} | "
                f"{len(nd.qubit_set):>8d} | {dual_t:>15s} | {grp:>8d}"
            )
            lines.append(row)

        lines.append(sep)
        dual_gates_total = _format_dual(agg["gates_uc"], agg["gates_cc"])
        dual_depth_total = _format_dual(agg["depth_uc"], agg["depth_cc"])
        dual_t_total = _format_dual(agg["t_count_uc"], agg["t_count_cc"])
        totals = (
            f"{'TOTAL':<20s} | {dual_gates_total:>15s} | {dual_depth_total:>15s} | "
            f"{agg['qubits']:>8d} | {dual_t_total:>15s} | {'-':>8s}"
        )
        lines.append(totals)

        # Hierarchical breakdown: show own vs referenced gates when call
        # nodes or call edges are present.
        call_node_indices = [
            i for i, nd in enumerate(self._nodes) if nd.is_call_node and not nd._merged
        ]
        cedges = self.call_edges()
        if call_node_indices or cedges:
            lines.append("")
            lines.append("Hierarchical Breakdown:")

            # Identify own-gate nodes vs call-reference nodes
            own_gates = sum(
                nd.gate_count
                for i, nd in enumerate(self._nodes)
                if not nd.is_call_node and not nd._merged
            )
            ref_gates = sum(
                nd.gate_count
                for i, nd in enumerate(self._nodes)
                if nd.is_call_node and not nd._merged
            )
            lines.append(f"  Own gates:        {own_gates}")
            lines.append(f"  Referenced gates:  {ref_gates}")
            lines.append(f"  Total:            {own_gates + ref_gates}")

            if cedges:
                lines.append("")
                lines.append("  Call relationships:")
                for src, tgt in cedges:
                    src_name = self._nodes[src].func_name
                    tgt_name = self._nodes[tgt].func_name
                    lines.append(f"    {src_name} -> {tgt_name}")

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

    def execution_order_edges(self) -> list[tuple[int, int]]:
        """Return all execution-order edges as (src, tgt) pairs."""
        result = []
        for eidx in self._dag.edge_indices():
            edata = self._dag.get_edge_data_by_index(eidx)
            if isinstance(edata, dict) and edata.get("type") == "execution_order":
                src, tgt = self._dag.get_edge_endpoints_by_index(eidx)
                result.append((src, tgt))
        return result

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

_dag_builder_stack: list[CallGraphDAG] = []
"""Stack of CallGraphDAG instances.

Used during @ql.compile execution to track the active DAG for
operation recording.
"""


def push_dag_context(dag: CallGraphDAG) -> None:
    """Push a DAG context onto the builder stack.

    Parameters
    ----------
    dag : CallGraphDAG
        The DAG being built.
    """
    _dag_builder_stack.append(dag)


def pop_dag_context() -> CallGraphDAG | None:
    """Pop the top DAG context from the builder stack.

    Returns
    -------
    CallGraphDAG or None
        The popped DAG, or None if stack was empty.
    """
    if not _dag_builder_stack:
        return None
    return _dag_builder_stack.pop()


def current_dag_context() -> CallGraphDAG | None:
    """Return the top of the builder stack without popping.

    Returns
    -------
    CallGraphDAG or None
        The current DAG, or None if stack is empty.
    """
    if not _dag_builder_stack:
        return None
    return _dag_builder_stack[-1]


# ---------------------------------------------------------------------------
# Operation recording helper (Module 7)
# ---------------------------------------------------------------------------


def record_operation(
    operation_type: str,
    qubit_indices: tuple | list,
    *,
    gate_count: int = 0,
    sequence_ptr: int = 0,
    invert: bool = False,
    controlled: bool = False,
    depth: int = 0,
    t_count: int = 0,
    uncontrolled_gate_count: int = 0,
    controlled_gate_count: int = 0,
) -> int | None:
    """Record a primitive operation (arithmetic/bitwise/comparison) on the DAG.

    Called from Cython-level operations during ``@ql.compile`` capture to
    log each ``run_instruction`` call as a DAG node with sequence metadata.

    This is a fast no-op when no DAG context is active (i.e., outside
    ``@ql.compile`` execution), so it is safe to call unconditionally.

    Parameters
    ----------
    operation_type : str
        Short identifier for the operation (e.g. ``"add_cq"``, ``"mul_qq"``,
        ``"xor"``, ``"eq"``).
    qubit_indices : tuple or list of int
        Physical qubit indices passed to ``run_instruction``.
    gate_count : int
        Number of gates in the operation, typically read from
        ``sequence_t.total_gate_count`` after ``run_instruction``.
    sequence_ptr : int
        C pointer to the ``sequence_t`` (cast to Python int via
        ``<unsigned long long>``).  Default 0 means pointer not captured.
    invert : bool
        Whether this is an inverse (adjoint) operation.
    controlled : bool
        Whether this operation was executed inside a controlled context.
        Used for the ``controlled`` flag on the DAGNode and as fallback
        for populating dual gate counts when explicit counts are not
        provided.
    depth : int
        Circuit depth for this operation.
    t_count : int
        T-gate count for this operation.
    uncontrolled_gate_count : int
        Gate count for the uncontrolled calling context.  When both this
        and *controlled_gate_count* are provided (non-zero), they are used
        directly.  When both are 0, *gate_count* is assigned to the
        appropriate side based on *controlled*.
    controlled_gate_count : int
        Gate count for the controlled calling context.

    Returns
    -------
    int or None
        Node index in the DAG if a node was added, None otherwise.
    """
    if not _dag_builder_stack:
        return None

    dag = _dag_builder_stack[-1]

    qubit_mapping = tuple(qubit_indices)
    qubit_set = frozenset(qubit_mapping)

    # When explicit dual counts are provided, use them directly.
    # Otherwise fall back to single-sided assignment from gate_count.
    uc_gc = uncontrolled_gate_count
    cc_gc = controlled_gate_count
    if uc_gc == 0 and cc_gc == 0:
        if controlled:
            cc_gc = gate_count
        else:
            uc_gc = gate_count

    # Depth and T-count remain single-sided (reflecting the actual
    # execution context) until a future issue adds dual resolution.
    if controlled:
        uc_depth, cc_depth = 0, depth
        uc_tc, cc_tc = 0, t_count
    else:
        uc_depth, cc_depth = depth, 0
        uc_tc, cc_tc = t_count, 0

    node_idx = dag.add_node(
        operation_type,
        qubit_set,
        gate_count,
        (),  # cache_key -- not applicable for primitives
        depth=depth,
        t_count=t_count,
        uncontrolled_depth=uc_depth,
        controlled_depth=cc_depth,
        uncontrolled_t_count=uc_tc,
        controlled_t_count=cc_tc,
        sequence_ptr=sequence_ptr,
        qubit_mapping=qubit_mapping,
        operation_type=operation_type,
        invert=invert,
        controlled=controlled,
        uncontrolled_gate_count=uc_gc,
        controlled_gate_count=cc_gc,
    )

    # Track node index on the active compile block so that _dispatch
    # can update missing variant counts on replay in a different context.
    from ._compile_state import _get_active_compile_block

    active_block = _get_active_compile_block()
    if active_block is not None and hasattr(active_block, "_dag_node_indices"):
        active_block._dag_node_indices.append(node_idx)

    return node_idx
