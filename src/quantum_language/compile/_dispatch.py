"""Call dispatch logic for CompiledFunc.

Contains the inner call dispatch (``_call_inner_impl``) and the parametric
call lifecycle (``_parametric_call_impl``).  Both are free functions that
receive the ``CompiledFunc`` instance as their first argument (``cf``),
following the same delegation pattern used in ``_capture`` and ``_replay``.
"""

import sys

from .._core import (
    add_gate_count,
)
from ..call_graph import (
    _compute_depth,
    _compute_t_count,
    current_dag_context,
)


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
    _track_fwd = cf._inverse_func is not None
    block = cf._cache[cache_key]
    # _replay selects controlled/uncontrolled variant at runtime
    result = cf._replay(block, quantum_args, track_forward=_track_fwd, kind="compiled_fn")
    # Manually credit gate count when run_instruction did NOT
    # already increment it.  run_instruction (IR path) always
    # increments circ->gate_count, so skip the manual credit
    # when the IR path was used.  inject_remapped_gates (gate-
    # level path) does NOT increment gate_count, and when
    # simulate=False neither path runs — both need manual credit.
    _used_ir = getattr(cf, "_last_replay_used_ir", False)
    if not _used_ir and block is not None:
        _replay_count = block.original_gate_count if block.original_gate_count else len(block.gates)
        if _replay_count:
            add_gate_count(_replay_count)
    # Record DAG node for replay path (no nesting -- body not
    # re-executed).
    if _building_dag:
        if cf._opt == 1 and block and block._instruction_ir:
            # opt=1 with IR (QFT mode): build DAG nodes from
            # instruction IR.  Context-aware: build once per control
            # context (uncontrolled / controlled) so both variants'
            # gate counts are populated on the DAG nodes.
            _ctx = bool(is_controlled)
            if _ctx not in block._dag_built_contexts:
                if not block._dag_built_contexts:
                    # First context: build new DAG nodes from IR.
                    _ir_added = _build_dag_from_ir(
                        block,
                        cf._func.__name__,
                        is_controlled=is_controlled,
                    )
                    if _ir_added > 0:
                        block._dag_built_contexts.add(_ctx)
                        block._dag_built = True
                else:
                    # Second context: update existing DAG nodes with
                    # the missing variant's gate counts.
                    _update_dag_variant_counts(block, is_controlled)
                    block._dag_built_contexts.add(_ctx)
        elif cf._opt == 1 and block and not block._instruction_ir:
            # opt=1 Toffoli mode (no IR): DAG nodes were created by
            # record_operation during capture with only one variant.
            # On replay in a new context, update existing nodes with
            # the other variant's gate counts from the block totals.
            _ctx = bool(is_controlled)
            if _ctx not in block._dag_built_contexts and block._dag_node_indices:
                _update_dag_variant_counts_proportional(
                    block,
                    is_controlled,
                )
                block._dag_built_contexts.add(_ctx)
        if cf._opt != 1:
            # Non-opt=1: add a coarse call-level DAG node per call.
            # opt=1 accumulates fine-grained nodes during capture
            # (via record_operation or _build_dag_from_ir), so
            # replays must not append duplicate coarse nodes.
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
                # Compute dual gate counts from block and controlled_block
                _uc_gc, _cc_gc = _block_dual_gate_counts(block)
                node_idx = dag.add_node(
                    cf._func.__name__,
                    qubit_set,
                    _node_gate_count,
                    cache_key,
                    depth=_compute_depth(_gates),
                    t_count=_compute_t_count(_gates),
                    controlled=is_controlled,
                    uncontrolled_gate_count=_uc_gc,
                    controlled_gate_count=_cc_gc,
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
    result = cf._capture_and_cache_both(
        args,
        kwargs,
        quantum_args,
        classical_args,
        widths,
        is_controlled,
        cache_key,
    )
    # For opt=1 capture, record control state on the cached block
    # so DAG consumers can query it without adding a wrapper node.
    # Also build DAG nodes from the instruction IR so the DAG is
    # populated even with simulate=False or QFT mode (where
    # record_operation does not fire during compile-mode capture).
    if cf._opt == 1:
        block = cf._cache.get(cache_key)
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
        result = cf._capture_and_cache_both(
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
        result = cf._capture_and_cache_both(
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
        return cf._capture_and_cache_both(
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
    result = cf._capture_and_cache_both(
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


# ---------------------------------------------------------------------------
# DAG variant count helpers
# ---------------------------------------------------------------------------


def _block_dual_gate_counts(block):
    """Compute dual gate counts from a block and its controlled_block.

    Returns (uncontrolled_gate_count, controlled_gate_count).
    """
    uc_gc = block.original_gate_count if block.original_gate_count else len(block.gates)
    cc_gc = 0
    cb = block.controlled_block
    if cb is not None:
        cc_gc = len(cb.gates) if cb.gates else (cb.original_gate_count or 0)
    return uc_gc, cc_gc


def _update_dag_variant_counts(block, is_controlled):
    """Update existing DAG nodes with the missing variant's gate counts.

    Used for opt=1 IR path when the function is called in a second
    control context.  The IR entries store both sequence pointers, so
    we can resolve both gate counts from any context.
    """
    from ..call_graph import _resolve_gate_count

    dag = current_dag_context()
    if dag is None:
        return

    for node_idx in block._dag_node_indices:
        if node_idx >= len(dag._nodes):
            continue
        node = dag._nodes[node_idx]
        # Re-resolve both counts from sequence pointers
        if node.uncontrolled_seq and node.uncontrolled_gate_count == 0:
            node.uncontrolled_gate_count = _resolve_gate_count(node.uncontrolled_seq)
        if node.controlled_seq and node.controlled_gate_count == 0:
            node.controlled_gate_count = _resolve_gate_count(node.controlled_seq)


def _update_dag_variant_counts_proportional(block, is_controlled):
    """Update existing DAG nodes with proportional gate counts for the other variant.

    Used for opt=1 Toffoli mode (no IR) when the function is called in
    a second control context.  Per-operation counts for the new context
    are not available, so we proportionally distribute the block-level
    total from the controlled/uncontrolled block across existing nodes.
    """
    dag = current_dag_context()
    if dag is None:
        return

    uc_total, cc_total = _block_dual_gate_counts(block)

    for node_idx in block._dag_node_indices:
        if node_idx >= len(dag._nodes):
            continue
        node = dag._nodes[node_idx]
        if is_controlled and node.controlled_gate_count == 0 and node.uncontrolled_gate_count > 0:
            # Proportional estimate of controlled count
            if uc_total > 0:
                ratio = cc_total / uc_total
                node.controlled_gate_count = max(1, int(node.uncontrolled_gate_count * ratio))
        elif (
            not is_controlled
            and node.uncontrolled_gate_count == 0
            and node.controlled_gate_count > 0
        ):
            # Proportional estimate of uncontrolled count
            if cc_total > 0:
                ratio = uc_total / cc_total
                node.uncontrolled_gate_count = max(1, int(node.controlled_gate_count * ratio))
