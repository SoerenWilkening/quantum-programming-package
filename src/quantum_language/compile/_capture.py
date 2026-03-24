"""Capture logic for compiled quantum functions.

Contains standalone functions for gate capture: ``_capture``,
``_capture_inner``, and ``_capture_and_cache``.  These are called by
``CompiledFunc`` methods which delegate to them with ``self`` as the
first argument.
"""

from .._core import (
    _get_control_bool,
    _get_control_stack,
    _get_controlled,
    _set_control_stack,
    extract_gate_range,
    get_current_layer,
    get_gate_count,
    option,
)
from . import _block
from ._block import (
    _MAX_CAPTURE_DEPTH,
    AncillaRecord,
    CompiledBlock,
)


def _capture(cf, args, kwargs, quantum_args):
    """Capture gate sequence during first call.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    args, kwargs : tuple, dict
        Original call arguments.
    quantum_args : list
        Classified quantum arguments.
    """
    if _block._capture_depth >= _MAX_CAPTURE_DEPTH:
        raise RecursionError(
            f"Compiled function nesting depth exceeded {_MAX_CAPTURE_DEPTH}. "
            "Possible circular compiled function calls."
        )
    _block._capture_depth += 1
    try:
        return _capture_inner(cf, args, kwargs, quantum_args)
    finally:
        _block._capture_depth -= 1


def _capture_inner(cf, args, kwargs, quantum_args):
    """Inner capture logic (separated for nesting depth tracking).

    Execution proceeds in compile mode: the body runs with IR recording
    active (no gates emitted), then ``_execute_ir`` replays the recorded
    entries to produce actual gates.  The resulting gates are extracted
    and virtualised for the gate-level cache as before.

    The compile-mode (IR recording) phase always runs with the control
    stack cleared so that IR entries record uncontrolled registers.
    The execute phase (``_execute_ir``) runs with the original control
    stack intact so it can select controlled sequences and inject
    the control qubit when inside a ``with`` block.  This ensures the
    first call inside a ``with`` block produces correctly controlled
    gates in the circuit.

    The extracted gates are then normalised to uncontrolled form (any
    injected control qubit is stripped) before building the gate-level
    cache.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    args, kwargs : tuple, dict
        Original call arguments.
    quantum_args : list
        Classified quantum arguments.
    """
    from . import (
        _build_virtual_mapping,
        _execute_ir,
        _get_qarray_qubit_indices,
        _get_qint_qubit_indices,
        _get_quantum_arg_qubit_indices,
        _get_quantum_arg_width,
        _optimize_gate_list,
        _strip_control_qubit,
    )

    # Record start layer
    start_layer = get_current_layer()

    # Detect controlled context BEFORE clearing the control stack
    is_controlled = _get_controlled()
    control_physical_qubit = None
    if is_controlled:
        control_bool = _get_control_bool()
        control_physical_qubit = int(control_bool.qubits[63])

    # Check if circuit is in tracking-only mode (simulate=False).
    # Gate count is used to compute per-block cost when gates aren't stored.
    _use_tracking = not option("simulate")
    # Always record gate_count before body execution so we can compute
    # the accurate gate_count delta.  circ->gate_count (from run_instruction)
    # may differ from len(extracted_gates) due to Toffoli dispatch internals,
    # and the delta is what get_gate_count() observes during replay.
    _gate_count_before = get_gate_count()

    # Collect parameter qubit indices BEFORE execution
    param_qubit_indices = []
    for qa in quantum_args:
        param_qubit_indices.append(_get_quantum_arg_qubit_indices(qa))

    # Compile-mode capture: run the body with IR recording active,
    # then execute the recorded IR to produce gates in the circuit.
    #
    # Mode-dependent control stack handling:
    # - QFT mode: control stack is cleared during compile_mode so IR
    #   entries record uncontrolled registers.  After compile_mode, the
    #   stack is restored and _execute_ir selects controlled sequences.
    # - Toffoli mode: control stack is NOT cleared.  Toffoli dispatch
    #   handles control natively (passes _controlled + control_qubit).
    #   No IR entries are recorded, so _execute_ir is a no-op.
    ir_block = CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )
    _is_toffoli = option("fault_tolerant")
    if _is_toffoli:
        # Toffoli mode: keep control stack intact.  Toffoli dispatch
        # emits gates directly with the correct control context.
        with cf.compile_mode(ir_block):
            result = cf._func(*args, **kwargs)
    else:
        # QFT mode: clear control stack during IR recording, restore
        # it before IR execution so _execute_ir can inject control.
        saved_stack = list(_get_control_stack())
        _set_control_stack([])
        try:
            with cf.compile_mode(ir_block):
                result = cf._func(*args, **kwargs)
        finally:
            _set_control_stack(saved_stack)

    # Execute the recorded IR to produce gates in the circuit.
    # In QFT mode, _execute_ir checks the (now-restored) control
    # stack and uses controlled sequences when inside a with block.
    # In Toffoli mode, operations recorded directly to the DAG via
    # _record_operation without execution -- skip _execute_ir.
    if not _is_toffoli:
        _execute_ir(ir_block)

    # Record end layer
    end_layer = get_current_layer()

    # Compute gate count from circ->gate_count difference.
    # This is always needed (not just tracking-only mode) because
    # circ->gate_count (incremented by run_instruction) may differ
    # from the number of stored gate dicts (Toffoli dispatch internals).
    # The delta is what get_gate_count() reflects and what replay must
    # credit via add_gate_count to stay consistent.
    # Subtract inner call gate count deltas so original_gate_count
    # reflects only this function's OWN gates (inner gates are replayed
    # via _replay_call_records which credits them separately).
    # gate_count_delta is the total recursive delta (including
    # grandchildren), not just the inner function's own gates.
    _gate_count_delta = get_gate_count() - _gate_count_before
    if ir_block._call_records:
        for cr in ir_block._call_records:
            _gate_count_delta -= cr.gate_count_delta

    # Extract captured gates (empty in tracking-only mode (simulate=False)
    # since gates are counted but not stored).
    # When nested compiled functions were called, exclude their gate
    # ranges so the outer block stores only its OWN gates.
    _inner_ranges = []
    if ir_block._call_records:
        for cr in ir_block._call_records:
            if cr.gate_layer_start >= 0 and cr.gate_layer_end > cr.gate_layer_start:
                _inner_ranges.append((cr.gate_layer_start, cr.gate_layer_end))
        _inner_ranges.sort()

    if _inner_ranges:
        raw_gates = []
        # Extract gaps between inner call ranges
        cursor = start_layer
        for inner_start, inner_end in _inner_ranges:
            if cursor < inner_start:
                raw_gates.extend(extract_gate_range(cursor, inner_start))
            cursor = max(cursor, inner_end)
        if cursor < end_layer:
            raw_gates.extend(extract_gate_range(cursor, end_layer))
    else:
        raw_gates = extract_gate_range(start_layer, end_layer)

    # If the capture ran in a controlled context, the extracted gates
    # include the control qubit.  Strip it to get uncontrolled gates
    # for the gate-level cache.
    if is_controlled and control_physical_qubit is not None and raw_gates:
        raw_gates = _strip_control_qubit(raw_gates, control_physical_qubit)

    # Build virtual mapping
    virtual_gates, real_to_virtual, total_virtual = _build_virtual_mapping(
        raw_gates, param_qubit_indices
    )

    # Scan CallRecord quantum_arg_indices for physical qubits missing from
    # real_to_virtual.  Zero-arg compiled functions have no parameter qubits,
    # and raw_gates excludes inner call gate ranges, so physical qubits only
    # touched by nested compiled functions may be absent.  Without this,
    # the fallback real_to_virtual.get(phys, phys) maps them to raw physical
    # indices that can collide with reserved virtual slots (e.g. index 0 for
    # control), causing KeyError during replay.
    if ir_block._call_records:
        for cr in ir_block._call_records:
            for arg_indices in cr.quantum_arg_indices:
                for phys in arg_indices:
                    if phys not in real_to_virtual:
                        real_to_virtual[phys] = total_virtual
                        total_virtual += 1

    # Determine return value qubit range (if result is qint or qarray)
    from ..qarray import qarray
    from ..qint import qint

    return_range = None
    return_is_param_index = None
    return_type = None
    return_qarray_element_widths = None

    if isinstance(result, qarray):
        return_type = "qarray"
        # Get all qubit indices from the returned qarray
        ret_indices = _get_qarray_qubit_indices(result)

        # Store element widths for replay reconstruction
        return_qarray_element_widths = [
            elem.width if hasattr(elem, "width") else 1 for elem in result
        ]

        # Check if return qarray IS one of the input parameters
        for param_idx, param_indices in enumerate(param_qubit_indices):
            if ret_indices == param_indices:
                return_is_param_index = param_idx
                break

        # Map return qubits to virtual namespace
        if ret_indices:
            virt_ret = [real_to_virtual[r] for r in ret_indices]
            return_range = (min(virt_ret), len(ret_indices))
    elif isinstance(result, qint):
        return_type = "qint"
        ret_indices = _get_qint_qubit_indices(result)

        # Check if return value IS one of the input parameters (in-place)
        for param_idx, param_indices in enumerate(param_qubit_indices):
            if ret_indices == param_indices:
                return_is_param_index = param_idx
                break

        # Map return qubits to virtual namespace
        virt_ret = [real_to_virtual[r] for r in ret_indices]
        return_range = (min(virt_ret), result.width)

    # Build param ranges in virtual space (start, end) starting at 1
    param_ranges = []
    vidx = 1  # params start at virtual index 1 (0 reserved for control)
    for qa in quantum_args:
        qa_width = _get_quantum_arg_width(qa)
        param_ranges.append((vidx, vidx + qa_width))
        vidx += qa_width
    internal_count = total_virtual - vidx

    # Optimise the virtual gate list (cancel adjacent inverses, merge
    # consecutive rotations) before caching so every replay benefits.
    # Use the circ->gate_count delta as original_gate_count.  This is
    # more accurate than len(virtual_gates) because run_instruction may
    # count more gates than are stored as gate dicts (Toffoli dispatch).
    # In tracking-only mode (simulate=False), len(virtual_gates) is 0,
    # so the delta is the only source.  In simulate mode, use the max
    # to ensure replay credits at least what get_gate_count() observed.
    original_count = max(_gate_count_delta, len(virtual_gates))
    if cf._optimize:
        try:
            virtual_gates = _optimize_gate_list(virtual_gates)
        except Exception:
            pass  # Fall back to unoptimised on any error

    # Identify ancilla physical qubits (those not in param sets)
    param_real_set = set()
    for qubit_list in param_qubit_indices:
        param_real_set.update(qubit_list)
    capture_ancilla_qubits = [r for r in real_to_virtual if r not in param_real_set]

    # Build virtual-to-real mapping for capture (inverse of real_to_virtual)
    capture_vtr = {v: r for r, v in real_to_virtual.items()}

    block = CompiledBlock(
        gates=virtual_gates,
        total_virtual_qubits=total_virtual,
        param_qubit_ranges=param_ranges,
        internal_qubit_count=internal_count,
        return_qubit_range=return_range,
        return_is_param_index=return_is_param_index,
        original_gate_count=original_count,
    )
    block._first_call_result = result
    block._capture_ancilla_qubits = capture_ancilla_qubits
    block._capture_virtual_to_real = capture_vtr
    block.return_type = return_type
    block._return_qarray_element_widths = return_qarray_element_widths

    # Classify ancilla qubits as transient vs result/persistent (Phase 8).
    # After capture, query the allocator to determine which ancilla qubits
    # were freed during the operation (transient: carry bits, temp registers)
    # vs which are still allocated (result qubits, persistent intermediates).
    from .._core import _is_qubit_allocated

    transient_virtuals = set()
    for real_q in capture_ancilla_qubits:
        virt_idx = real_to_virtual.get(real_q)
        if virt_idx is not None and not _is_qubit_allocated(real_q):
            transient_virtuals.add(virt_idx)
    block.transient_virtual_indices = frozenset(transient_virtuals)

    # Transfer IR entries from the compile-mode block to the cached block
    block._instruction_ir = ir_block._instruction_ir

    # Transfer DAG node indices recorded by record_operation during capture
    if ir_block._dag_node_indices:
        block._dag_node_indices = ir_block._dag_node_indices

    # Transfer CallRecords from the compile-mode block, converting
    # capture-time physical qubit indices to virtual qubit indices
    # so that _replay can map them through virtual_to_real.
    if ir_block._call_records:
        for cr in ir_block._call_records:
            cr.quantum_arg_indices = [
                [real_to_virtual.get(phys, phys) for phys in arg_indices]
                for arg_indices in cr.quantum_arg_indices
            ]
        block._call_records = ir_block._call_records

    return block


def _capture_and_cache(
    cf,
    args,
    kwargs,
    quantum_args,
    classical_args,
    widths,
    is_controlled,
    cache_key,
):
    """Handle cache miss: capture and cache a single block.

    Each context (controlled vs uncontrolled) captures its own block
    independently.  There is no derived controlled variant.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    args, kwargs : tuple, dict
        Original call arguments.
    quantum_args : list
        Classified quantum arguments.
    classical_args : list
        Classified classical arguments.
    widths : list
        Qubit widths per quantum argument.
    is_controlled : bool
        Whether the call is inside a controlled context.
    cache_key : tuple
        Cache key for this call.
    """
    from . import _input_qubit_key

    block = _capture(cf, args, kwargs, quantum_args)

    # Cache the block
    cf._cache[cache_key] = block

    # Evict oldest if over capacity
    while len(cf._cache) > cf._max_cache:
        cf._cache.popitem(last=False)

    # Record forward call for inverse support (first call / capture path)
    result = block._first_call_result
    capture_ancillas = block._capture_ancilla_qubits or []
    if capture_ancillas:
        input_key = _input_qubit_key(quantum_args)
        cf._forward_calls[input_key] = AncillaRecord(
            ancilla_qubits=capture_ancillas,
            virtual_to_real=block._capture_virtual_to_real or {},
            block=block,
            return_qint=result
            if (block.return_qubit_range is not None and block.return_is_param_index is None)
            else None,
        )

    return result
