"""Replay logic for compiled quantum functions.

Contains standalone functions for gate replay: ``_replay`` (replay cached
gates with qubit remapping) and ``_apply_merge`` (selective sequence
merging for opt=2).  These are called by ``CompiledFunc`` methods which
delegate to them with ``self`` as the first argument.
"""

from .._core import (
    _allocate_qubit,
    _get_control_bool,
    _get_controlled,
    _get_layer_floor,
    _set_layer_floor,
    get_current_layer,
    inject_remapped_gates,
    option,
)
from ._block import (
    AncillaRecord,
    CompiledBlock,
)


def _replay(cf, block, quantum_args, track_forward=True, kind=None):
    """Replay cached gates with qubit remapping.

    Each control context (controlled vs uncontrolled) has its own
    independently captured block stored under a separate cache key.
    The block is replayed directly with no variant selection.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    block : CompiledBlock
        The cached block for this context.
    quantum_args : list
        Caller's quantum arguments (qint / qarray).
    track_forward : bool
        Whether to record ancilla allocations for inverse support.
    kind : str or None
        History kind tag (e.g. ``"compiled_fn"``).
    """
    from . import (
        _build_return_qarray,
        _build_return_qint,
        _execute_ir,
        _get_quantum_arg_qubit_indices,
        _input_qubit_key,
        _replay_call_records,
    )

    is_controlled = _get_controlled()

    # Build virtual-to-real mapping from caller's qints/qarrays.
    # Virtual index 0 is reserved for the control qubit; params
    # start at index 1.
    virtual_to_real = {}

    # Map control qubit at index 0 when in controlled context.
    # The gate-level path needs this to remap virtual index 0
    # (the control slot) to the actual control qubit.  The IR
    # path handles control injection internally via the control
    # stack, so this mapping is only consumed by gate-level replay.
    if is_controlled:
        control_bool = _get_control_bool()
        virtual_to_real[0] = int(control_bool.qubits[63])

    vidx = 1  # params start at virtual index 1
    for qa in quantum_args:
        indices = _get_quantum_arg_qubit_indices(qa)
        for real_q in indices:
            virtual_to_real[vidx] = real_q
            vidx += 1

    # Validate total qubit count matches cached block's param ranges
    expected_param_qubits = sum(end - start for start, end in block.param_qubit_ranges)
    if vidx - 1 != expected_param_qubits:
        raise ValueError(
            f"qarray element widths don't match captured widths: "
            f"expected {expected_param_qubits} qubits, got {vidx - 1}"
        )

    # Determine replay path before allocation: prefer IR path
    # (handles controlled context via controlled_seq), fall back to
    # gate-level injection.
    _ir_source = None
    if block._instruction_ir:
        _ir_source = block

    # Determine which virtual indices are transient.  For the IR path,
    # run_instruction allocates its own internal ancillas, so we skip
    # allocation for transient virtual indices (Step 8.2).  For the
    # gate-level path, all internal qubits must be allocated (the
    # injected gate tuples reference them directly).
    _will_use_ir = (
        _ir_source is not None
        and _ir_source._instruction_ir
        and option("simulate")
        and not (cf._opt == 1 and not is_controlled and not option("simulate"))
    )
    _transient_set = block.transient_virtual_indices if _will_use_ir else frozenset()

    # Allocate fresh ancillas for internal qubits (skip index 0
    # which is the control slot, already mapped or unused).
    # On the IR path, transient virtual indices are skipped — they
    # are not referenced by IR register tuples and run_instruction
    # handles its own ancillas for them.
    ancilla_qubits = []
    for v in range(vidx, block.total_virtual_qubits):
        if v in _transient_set:
            continue
        real_q = _allocate_qubit()
        virtual_to_real[v] = real_q
        ancilla_qubits.append(real_q)

    # Save layer_floor, set to current layer to prevent gate reordering
    # into earlier circuit layers. This ensures consistent depth behavior:
    # - Forward replay f(x) and inverse replay f.inverse(x) produce EQUAL
    #   circuit depth because both use this same replay path with the same
    #   layer_floor constraint (verified Phase 56 FIX-02).
    # - Capture vs replay may differ if capture occurs after operations on
    #   non-overlapping qubits (capture can pack into earlier layers).
    saved_floor = _get_layer_floor()
    start_layer = get_current_layer()
    _set_layer_floor(start_layer)

    # Inject gates into the circuit when simulate is True.
    # When simulate is False (tracking-only / DAG-only mode),
    # gates are not stored — gate counts are credited separately
    # in _call_inner.
    #
    # opt=1 DAG-only replay: skip gate injection only in uncontrolled
    # context AND when simulate=False (the DAG node in _call_inner
    # records the cost).  When simulate=True the user expects gates
    # in the circuit for every call.  Gate injection is also always
    # required in controlled contexts (inside ``with`` blocks) for
    # correct quantum state evolution.
    #
    # Track which path was used so _call_inner can decide whether to
    # credit gate_count manually:
    # - IR path: run_instruction already increments circ->gate_count
    # - Gate-level path: inject_remapped_gates does NOT increment it
    # - No path (simulate=False or opt=1 skip): nothing increments it
    cf._last_replay_used_ir = False
    _skip_injection = cf._opt == 1 and not is_controlled and not option("simulate")
    if option("simulate") and not _skip_injection:
        if _ir_source is not None and _ir_source._instruction_ir:
            # IR path: _execute_ir handles controlled sequences and
            # control qubit injection internally.
            # Build capture-physical -> replay-physical mapping from
            # the block's virtual-to-real data. IR entries store
            # capture-time physical qubit indices, so we need to map
            # them to the replay-time physical indices.
            ir_qubit_mapping = None
            v2r_capture = _ir_source._capture_virtual_to_real
            if v2r_capture and virtual_to_real:
                ir_qubit_mapping = {}
                for virt_idx, capture_phys in v2r_capture.items():
                    if virt_idx in virtual_to_real:
                        ir_qubit_mapping[capture_phys] = virtual_to_real[virt_idx]
            _execute_ir(_ir_source, qubit_mapping=ir_qubit_mapping)
            cf._last_replay_used_ir = True
        elif block.gates:
            # Gate-level path: inject remapped gates into the circuit.
            # When replaying in a controlled context, derive controlled
            # gates.  The approach depends on how the block was captured:
            #
            # - Block NOT captured in controlled context (including
            #   inverted blocks from _InverseCompiledFunc): the gates
            #   represent the uncontrolled operation.  Apply
            #   _derive_controlled_gates directly to add virtual index 0
            #   as a control to every gate.
            #
            # - Block captured in controlled context (_captured_controlled
            #   is True): the gates were produced by Toffoli dispatch with
            #   control, then the control qubit was stripped.  The gate
            #   topology differs from the uncontrolled version so we
            #   cannot derive from it.  Instead, find the uncontrolled
            #   block from the cache and derive from that.
            replay_gates = block.gates
            if is_controlled:
                from . import _derive_controlled_gates

                _was_controlled_capture = getattr(block, "_captured_controlled", False)
                if _was_controlled_capture:
                    # Find the uncontrolled block from the cache
                    _unctrl_block = None
                    if hasattr(cf, "_cache"):
                        for _cb in cf._cache.values():
                            if (
                                _cb is not block
                                and not getattr(_cb, "_captured_controlled", False)
                                and _cb.param_qubit_ranges == block.param_qubit_ranges
                                and _cb.gates
                            ):
                                _unctrl_block = _cb
                                break
                    if _unctrl_block is not None:
                        replay_gates = _derive_controlled_gates(_unctrl_block.gates)
                    else:
                        # No uncontrolled block available; fall back to
                        # deriving from the current block's gates.
                        replay_gates = _derive_controlled_gates(replay_gates)
                else:
                    # Block gates are uncontrolled -- derive directly.
                    replay_gates = _derive_controlled_gates(replay_gates)
            inject_remapped_gates(replay_gates, virtual_to_real)

            # Free transient ancillas after gate injection (Phase 8.3).
            # The injected gates return transient qubits to |0>, so they
            # can be deallocated and reused. This prevents qubit count
            # growth on repeated gate-level replay calls.
            _transients = getattr(block, "transient_virtual_indices", None)
            if _transients:
                from .._core import _deallocate_qubits

                for virt_idx in _transients:
                    real_q = virtual_to_real.get(virt_idx)
                    if real_q is not None:
                        _deallocate_qubits(real_q, 1)
                        # Remove from ancilla_qubits so inverse()
                        # does not try to deallocate again
                        if real_q in ancilla_qubits:
                            ancilla_qubits.remove(real_q)

    # Replay nested compiled function calls via CallRecords.
    # Each CallRecord stores virtual qubit indices per argument;
    # compose with virtual_to_real to get replay-time physical qubits.
    _replay_call_records(block, virtual_to_real)

    # Restore layer_floor
    _set_layer_floor(saved_floor)

    # Build return value
    result = None
    if block.return_qubit_range is not None:
        if block.return_is_param_index is not None:
            # Return value IS one of the input params -- return caller's qint/qarray
            result = quantum_args[block.return_is_param_index]
        elif block.return_type == "qarray":
            result = _build_return_qarray(block, virtual_to_real)
        else:
            result = _build_return_qint(block, virtual_to_real)

    # Record compiled-function history entry for inverse cancellation
    if kind is not None and quantum_args:
        _qm = tuple(q for qa in quantum_args for q in _get_quantum_arg_qubit_indices(qa))
        target = quantum_args[0]
        if hasattr(target, "history"):
            target.history.append(id(cf), _qm, len(ancilla_qubits), kind=kind)

    # Record forward call for inverse support.
    # Always record when internal qubits exist, even if ancilla_qubits
    # is empty after transient freeing -- inverse() still needs the
    # virtual_to_real mapping to replay adjoint gates.
    if track_forward and block.internal_qubit_count > 0:
        input_key = _input_qubit_key(quantum_args)
        record = AncillaRecord(
            ancilla_qubits=ancilla_qubits,
            virtual_to_real=dict(virtual_to_real),
            block=block,
            return_qint=result
            if (block.return_qubit_range is not None and block.return_is_param_index is None)
            else None,
        )
        # Use a stack (list) per key so multiple forward calls with the
        # same physical qubits can coexist (e.g. is_valid called in a
        # loop over moves).  Inverse pops LIFO.
        if input_key not in cf._forward_calls:
            cf._forward_calls[input_key] = []
        cf._forward_calls[input_key].append(record)

    return result


def _apply_merge(cf):
    """Merge overlapping sequences after first call (opt=2).

    Gets merge groups from the call graph, collects CompiledBlocks and
    their virtual-to-real mappings, runs _merge_and_optimize, and stores
    merged CompiledBlocks keyed by frozenset of node indices.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    """
    from . import _merge_and_optimize

    if cf._call_graph is None:
        return
    groups = cf._call_graph.merge_groups(cf._merge_threshold)
    if not groups:
        return

    merged_blocks = {}
    for group in groups:
        blocks_with_mappings = []
        for node_idx in group:
            node = cf._call_graph._nodes[node_idx]
            block = node._block_ref
            v2r = node._v2r_ref
            if block is None or v2r is None:
                # Block not available for this node; skip this group
                break
            blocks_with_mappings.append((block, v2r))
        else:
            # All blocks found -- merge them
            merged_gates, original_count = _merge_and_optimize(
                blocks_with_mappings, optimize=cf._optimize
            )
            # Determine max physical qubit used
            max_phys = 0
            for g in merged_gates:
                if g["target"] > max_phys:
                    max_phys = g["target"]
                for c in g.get("controls", []):
                    if c > max_phys:
                        max_phys = c
            total_vqubits = max_phys + 1 if merged_gates else 0
            merged_block = CompiledBlock(
                gates=merged_gates,
                total_virtual_qubits=total_vqubits,
                param_qubit_ranges=[],
                internal_qubit_count=0,
                return_qubit_range=None,
                original_gate_count=original_count,
            )
            # Identity mapping: physical qubits are already correct
            merged_block._capture_virtual_to_real = {i: i for i in range(total_vqubits)}
            group_key = frozenset(group)
            merged_blocks[group_key] = merged_block

    if merged_blocks:
        cf._merged_blocks = merged_blocks

    if cf._debug and merged_blocks:
        merge_stats = {
            "merge_groups": len(groups),
            "merged_blocks": len(merged_blocks),
        }
        for gk, mb in merged_blocks.items():
            merge_stats[f"group_{sorted(gk)}_gates"] = len(mb.gates)
            merge_stats[f"group_{sorted(gk)}_original"] = mb.original_gate_count
        if cf._stats is None:
            cf._stats = {}
        cf._stats["merge"] = merge_stats
