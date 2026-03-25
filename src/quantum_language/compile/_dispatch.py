"""Call dispatch logic for CompiledFunc.

Contains the inner call dispatch (``_call_inner_impl``) and the parametric
call lifecycle (``_parametric_call_impl``).  Both are free functions that
receive the ``CompiledFunc`` instance as their first argument (``cf``),
following the same delegation pattern used in ``_capture`` and ``_replay``.
"""

import sys

from .._core import (
    add_gate_count,
    option,
)
from ..call_graph import (
    _compute_depth,
    _compute_t_count,
    current_dag_context,
)


def _merge_dual_context_nodes(dag, old_indices, new_indices, new_controlled):
    """Merge second-context DAG nodes into first-context nodes.

    For each matching position, copies the new context's gate count, depth,
    and T-count onto the existing node.  The new (duplicate) nodes are
    marked ``_merged=True`` so they are skipped in ``report()`` and
    ``aggregate()``.

    With calling-context semantics, U/C on each node represent the cost when
    the enclosing function is called uncontrolled/controlled.  The merge copies
    the new context's cost to the appropriate side of the old nodes.  When the
    uncontrolled context is the new one, also update the old node's func_name
    (only the uncontrolled capture correctly applies the "c_" prefix for
    internally controlled operations).

    Parameters
    ----------
    dag : CallGraphDAG
        The DAG containing both sets of nodes.
    old_indices : list[int]
        Node indices from the first context.
    new_indices : list[int]
        Node indices from the second context.
    new_controlled : bool
        Whether the second context is the controlled context.
    """
    # Only merge when both captures produce the same number of nodes.
    # When they differ (e.g., controlled context introduces AND nodes),
    # keep all nodes from both captures — no positional merge.
    if len(old_indices) != len(new_indices):
        return
    n = len(old_indices)
    for i in range(n):
        old_node = dag._nodes[old_indices[i]]
        new_node = dag._nodes[new_indices[i]]
        if new_controlled:
            if new_node.controlled_gate_count and not old_node.controlled_gate_count:
                old_node.controlled_gate_count = new_node.controlled_gate_count
            if new_node.controlled_depth and not old_node.controlled_depth:
                old_node.controlled_depth = new_node.controlled_depth
            if new_node.controlled_t_count and not old_node.controlled_t_count:
                old_node.controlled_t_count = new_node.controlled_t_count
        else:
            if new_node.uncontrolled_gate_count and not old_node.uncontrolled_gate_count:
                old_node.uncontrolled_gate_count = new_node.uncontrolled_gate_count
            if new_node.uncontrolled_depth and not old_node.uncontrolled_depth:
                old_node.uncontrolled_depth = new_node.uncontrolled_depth
            if new_node.uncontrolled_t_count and not old_node.uncontrolled_t_count:
                old_node.uncontrolled_t_count = new_node.uncontrolled_t_count
            # The uncontrolled capture has the correct "c_" prefix for
            # internally controlled ops.  Update old node's name.
            old_node.func_name = new_node.func_name
        new_node._merged = True


def _call_inner_impl(
    cf,
    args,
    kwargs,
    quantum_args,
    classical_args,
    widths,
    is_controlled,
    control_count,
    qubit_saving,
    mode_flags,
    cache_key,
    _building_dag,
):
    """Inner call logic, separated for DAG try/finally wrapper.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    All other parameters forwarded from ``CompiledFunc.__call__``.
    """
    from . import (
        _build_dag_from_ir,
        _build_qubit_set_numpy,
    )

    # Parametric routing (PAR-02): if parametric and has classical args,
    # use the parametric probe/replay lifecycle instead of normal caching.
    if cf._parametric and classical_args:
        result = cf._parametric_call(
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            control_count,
            qubit_saving,
            mode_flags,
            cache_key,
        )
        # Record DAG node for parametric path
        if _building_dag:
            dag = current_dag_context()
            if dag is not None:
                block = cf._cache.get(cache_key)
                extra = None
                if (
                    block
                    and hasattr(block, "_capture_virtual_to_real")
                    and block._capture_virtual_to_real
                ):
                    extra = block._capture_virtual_to_real.values()
                qubit_set, _ = _build_qubit_set_numpy(quantum_args, extra)
                _gates = block.gates if block else []
                dag.add_node(
                    cf._func.__name__,
                    qubit_set,
                    len(_gates),
                    cache_key,
                    depth=_compute_depth(_gates),
                    t_count=_compute_t_count(_gates),
                    controlled=is_controlled,
                )
        return result

    is_hit = cache_key in cf._cache

    if is_hit:
        result = _replay_hit(
            cf,
            cache_key,
            quantum_args,
            is_controlled,
            _building_dag,
            _build_dag_from_ir,
            _build_qubit_set_numpy,
        )
    else:
        result = _capture_miss(
            cf,
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
            _building_dag,
            _build_dag_from_ir,
        )

    if cf._debug:
        _log_debug(cf, cache_key, is_hit)

    return result


def _replay_hit(
    cf,
    cache_key,
    quantum_args,
    is_controlled,
    _building_dag,
    _build_dag_from_ir,
    _build_qubit_set_numpy,
):
    """Handle a cache hit: replay the cached block."""
    # Move to end (most recently used)
    cf._cache.move_to_end(cache_key)
    _track_fwd = cf._inverse_eager
    block = cf._cache[cache_key]
    result = cf._replay(block, quantum_args, track_forward=_track_fwd, kind="compiled_fn")
    # Credit gate count from the replayed block.  Per-context caching
    # ensures block.original_gate_count is always the correct cost.
    # When the block has executable IR (non-zero sequence pointers)
    # and simulation is active, run_instruction already credited
    # gate_count during _replay — skip to avoid double-counting.
    if block is not None and block.original_gate_count:
        _ir_credited = (
            option("simulate")
            and block._instruction_ir
            and any(e.uncontrolled_seq or e.controlled_seq for e in block._instruction_ir)
        )
        if not _ir_credited:
            add_gate_count(block.original_gate_count)
    # Record DAG node for replay path (no nesting -- body not
    # re-executed).
    if _building_dag:
        if cf._opt == 1 and block and block._instruction_ir:
            # opt=1 with IR (QFT mode): build DAG nodes from
            # instruction IR.
            _ctx = bool(is_controlled)
            if _ctx not in block._dag_built_contexts:
                _ir_added = _build_dag_from_ir(
                    block,
                    cf._func.__name__,
                    is_controlled=is_controlled,
                )
                if _ir_added > 0:
                    block._dag_built_contexts.add(_ctx)
                    block._dag_built = True
        elif cf._opt == 1 and block and not block._instruction_ir:
            # opt=1 Toffoli mode (no IR): DAG nodes were created by
            # record_operation during capture with only one variant.
            _ctx = bool(is_controlled)
            if _ctx not in block._dag_built_contexts and block._dag_node_indices:
                block._dag_built_contexts.add(_ctx)
                # On replay in a different context, merge with sibling
                # block's nodes to fill in the other variant's counts.
                dag = current_dag_context()
                if dag is not None:
                    for other_key, other_block in cf._cache.items():
                        if other_key == cache_key:
                            continue
                        if other_block._dag_node_indices:
                            _merge_dual_context_nodes(
                                dag,
                                other_block._dag_node_indices,
                                block._dag_node_indices,
                                new_controlled=is_controlled,
                            )
                            break
        if cf._opt != 1:
            # Non-opt=1: add a coarse call-level DAG node per call.
            dag = current_dag_context()
            if dag is not None:
                extra = (
                    block._capture_virtual_to_real
                    if (block and block._capture_virtual_to_real)
                    else None
                )
                qubit_set, _ = _build_qubit_set_numpy(quantum_args, extra)
                _gates = block.gates if block else []
                _node_gate_count = (
                    block.original_gate_count
                    if block and not _gates and block.original_gate_count
                    else len(_gates)
                )
                node_idx = dag.add_node(
                    cf._func.__name__,
                    qubit_set,
                    _node_gate_count,
                    cache_key,
                    depth=_compute_depth(_gates),
                    t_count=_compute_t_count(_gates),
                    controlled=is_controlled,
                )
                # Store block ref for merge support (opt=2)
                if block is not None:
                    dag._nodes[node_idx]._block_ref = block
                    dag._nodes[node_idx]._v2r_ref = block._capture_virtual_to_real
    return result


def _capture_miss(
    cf,
    args,
    kwargs,
    quantum_args,
    classical_args,
    widths,
    is_controlled,
    cache_key,
    _building_dag,
    _build_dag_from_ir,
):
    """Handle a cache miss: capture, cache, and optionally build DAG."""
    from . import _build_qubit_set_numpy

    result = cf._capture_and_cache(
        args,
        kwargs,
        quantum_args,
        classical_args,
        widths,
        is_controlled,
        cache_key,
    )
    block = cf._cache.get(cache_key)
    # For opt=1 capture, record control state on the cached block
    # so DAG consumers can query it without adding a wrapper node.
    # Also build DAG nodes from the instruction IR so the DAG is
    # populated even with simulate=False or QFT mode (where
    # record_operation does not fire during compile-mode capture).
    if cf._opt == 1:
        if block is not None:
            block._captured_controlled = is_controlled
            _ctx = bool(is_controlled)
            if _building_dag and block._instruction_ir and _ctx not in block._dag_built_contexts:
                _ir_added = _build_dag_from_ir(
                    block,
                    cf._func.__name__,
                    is_controlled=is_controlled,
                )
                if _ir_added > 0:
                    block._dag_built_contexts.add(_ctx)
                    block._dag_built = True
            elif _building_dag and not block._instruction_ir and block._dag_node_indices:
                # Toffoli mode: record_operation created DAG nodes
                # during capture.  Mark the capture context as built.
                block._dag_built_contexts.add(_ctx)
                block._dag_built = True
                # Merge with sibling block's nodes from the other context
                dag = current_dag_context()
                if dag is not None:
                    for other_key, other_block in cf._cache.items():
                        if other_key == cache_key:
                            continue
                        if other_block._dag_node_indices:
                            _merge_dual_context_nodes(
                                dag,
                                other_block._dag_node_indices,
                                block._dag_node_indices,
                                new_controlled=is_controlled,
                            )
                            break
            elif _building_dag and block._call_records:
                # Nested compiled function calls: call nodes were added
                # to the outer DAG by __call__ via _add_nested_call_dag_node.
                # Mark the context as built to prevent replay duplication.
                block._dag_built_contexts.add(_ctx)
                block._dag_built = True
    elif _building_dag and block is not None:
        # Non-opt=1: add a coarse call-level DAG node on capture miss
        # so that per-context cache entries (controlled vs uncontrolled)
        # each produce a DAG node.
        dag = current_dag_context()
        if dag is not None:
            extra = block._capture_virtual_to_real if block._capture_virtual_to_real else None
            qubit_set, _ = _build_qubit_set_numpy(quantum_args, extra)
            _gates = block.gates if block else []
            _node_gate_count = (
                block.original_gate_count
                if not _gates and block.original_gate_count
                else len(_gates)
            )
            node_idx = dag.add_node(
                cf._func.__name__,
                qubit_set,
                _node_gate_count,
                cache_key,
                depth=_compute_depth(_gates),
                t_count=_compute_t_count(_gates),
                controlled=is_controlled,
            )
            if block is not None:
                dag._nodes[node_idx]._block_ref = block
                dag._nodes[node_idx]._v2r_ref = block._capture_virtual_to_real
    return result


def _log_debug(cf, cache_key, is_hit):
    """Print debug info and update stats."""
    block = cf._cache.get(cache_key)
    if block is not None:
        if is_hit:
            cf._total_hits += 1
        else:
            cf._total_misses += 1
        print(
            f"[ql.compile] {cf._func.__name__}: "
            f"{'HIT' if is_hit else 'MISS'} | "
            f"original={block.original_gate_count} -> "
            f"optimized={len(block.gates)} gates | "
            f"cache_entries={len(cf._cache)}",
            file=sys.stderr,
        )
        cf._stats = {
            "cache_hit": is_hit,
            "original_gate_count": block.original_gate_count,
            "optimized_gate_count": len(block.gates),
            "cache_size": len(cf._cache),
            "total_hits": cf._total_hits,
            "total_misses": cf._total_misses,
        }


def _parametric_call_impl(
    cf,
    args,
    kwargs,
    quantum_args,
    classical_args,
    widths,
    is_controlled,
    control_count,
    qubit_saving,
    mode_flags,
    cache_key,
):
    """Handle parametric compilation: probe, detect, replay or fallback.

    Lifecycle:
    1. First call: capture normally, store topology, wait for probe
    2. Second call (different classical args): capture again, compare
       topology
       - If topology matches: mark as parametric-safe, future calls
         use per-value cache (populated on demand)
       - If topology differs: mark as structural, fall back to normal
         per-value caching
    3. Subsequent calls:
       - Parametric-safe: per-value cache hit or capture-and-cache
         (topology verified defensively on new values)
       - Structural: standard per-value caching (same as non-parametric)

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    All other parameters forwarded from ``CompiledFunc.__call__``.
    """
    from . import _extract_topology

    # --- State: Unknown (first call ever) ---
    if cf._parametric_safe is None and not cf._parametric_probed:
        # First capture -- store topology for later probe
        result = cf._capture_and_cache(
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
        )
        block = cf._cache.get(cache_key)
        if block is not None:
            cf._parametric_topology = _extract_topology(block.gates)
            cf._parametric_block = block
            cf._parametric_probed = True
            cf._parametric_first_classical = tuple(classical_args)
        return result

    # --- State: Probed (waiting for second call with different args) ---
    if cf._parametric_safe is None and cf._parametric_probed:
        # Same classical args as first call? Normal cache hit
        if tuple(classical_args) == cf._parametric_first_classical:
            is_hit = cache_key in cf._cache
            if is_hit:
                cf._cache.move_to_end(cache_key)
                block = cf._cache[cache_key]
                return cf._replay(block, quantum_args, kind="compiled_fn")
            else:
                # Mode flags changed -- re-probe from scratch
                cf._parametric_probed = False
                cf._parametric_topology = None
                cf._parametric_block = None
                cf._parametric_first_classical = None
                return _parametric_call_impl(
                    cf,
                    args,
                    kwargs,
                    quantum_args,
                    classical_args,
                    widths,
                    is_controlled,
                    control_count,
                    qubit_saving,
                    mode_flags,
                    cache_key,
                )

        # Different classical args -- run the structural probe
        result = cf._capture_and_cache(
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
        )
        block = cf._cache.get(cache_key)
        if block is not None:
            probe_topology = _extract_topology(block.gates)
            if probe_topology == cf._parametric_topology:
                # Topology matches! Function is parametric-safe
                cf._parametric_safe = True
            else:
                # Topology differs -- structural parameter detected
                cf._parametric_safe = False
                cf._parametric_topology = None
                cf._parametric_block = None
        return result

    # --- State: Structural (fallback to per-value caching) ---
    if cf._parametric_safe is False:
        # Standard per-value behavior (same as non-parametric)
        is_hit = cache_key in cf._cache
        if is_hit:
            cf._cache.move_to_end(cache_key)
            block = cf._cache[cache_key]
            return cf._replay(block, quantum_args, kind="compiled_fn")
        return cf._capture_and_cache(
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
        )

    # --- State: Parametric-safe (PAR-02 fast path) ---
    # Check for per-value cache hit first
    if cache_key in cf._cache:
        cf._cache.move_to_end(cache_key)
        block = cf._cache[cache_key]
        return cf._replay(block, quantum_args, kind="compiled_fn")

    # New classical value: capture to get correct gates and cache per-value
    result = cf._capture_and_cache(
        args,
        kwargs,
        quantum_args,
        classical_args,
        widths,
        is_controlled,
        cache_key,
    )

    # Verify topology still matches (defensive guard against edge cases
    # where topology changes due to runtime state)
    block = cf._cache.get(cache_key)
    if block is not None:
        new_topology = _extract_topology(block.gates)
        if new_topology != cf._parametric_topology:
            # Topology diverged! Revert to per-value caching
            cf._parametric_safe = False
            cf._parametric_topology = None
            cf._parametric_block = None

    return result
