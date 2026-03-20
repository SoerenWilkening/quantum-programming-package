"""CompiledFunc class and public compile decorator.

Contains the ``CompiledFunc`` wrapper returned by ``@ql.compile`` and
the ``compile`` decorator factory.  Inverse classes
(``_InverseCompiledFunc``, ``_AncillaInverseProxy``) are in ``_inverse``.
"""

import collections
import contextlib
import functools
import sys
import weakref

from .._compile_state import (
    _get_active_compile_block,
    _record_call,
    _set_active_compile_block,
)
from .._core import (
    _allocate_qubit,
    _get_control_bool,
    _get_control_stack,
    _get_controlled,
    _get_layer_floor,
    _get_qubit_saving_mode,
    _register_cache_clear_hook,
    _set_control_stack,
    _set_layer_floor,
    add_gate_count,
    extract_gate_range,
    get_current_layer,
    get_gate_count,
    inject_remapped_gates,
    option,
)
from ..call_graph import (
    CallGraphDAG,
    _compute_depth,
    _compute_t_count,
    _dag_builder_stack,
    current_dag_context,
    pop_dag_context,
    push_dag_context,
)
from ..qint import qint
from . import _block
from ._block import (
    _MAX_CAPTURE_DEPTH,
    AncillaRecord,
    CompiledBlock,
)

# ---------------------------------------------------------------------------
# Global registry for cache invalidation on circuit reset
# ---------------------------------------------------------------------------
_compiled_funcs = []  # List of weakref.ref to CompiledFunc instances


def _clear_all_caches():
    """Clear compilation caches for all live CompiledFunc instances.

    Called automatically when a new circuit is created via ql.circuit().
    Dead weak references are pruned during iteration.

    Also enables simulate mode so gates are stored in the circuit.
    The C default is simulate=0 (tracking-only), but full simulation
    is required for QASM export, compiled function replay, and any
    operation that needs gate data in the circuit.

    Note: this means ql.circuit() forces simulate=True.  Users who
    want tracking-only mode should set ql.option('simulate', False)
    AFTER calling ql.circuit(), or avoid calling ql.circuit() entirely
    (the circuit initializes automatically).
    """
    _block._capture_depth = 0
    _dag_builder_stack.clear()
    option("simulate", True)
    alive = []
    for ref in _compiled_funcs:
        obj = ref()
        if obj is not None:
            obj._reset_for_circuit()
            alive.append(ref)
    _compiled_funcs[:] = alive


# Register the hook so circuit.__init__ calls us
_register_cache_clear_hook(_clear_all_caches)


# ---------------------------------------------------------------------------
# CompiledFunc -- the wrapper returned by @ql.compile
# ---------------------------------------------------------------------------
class CompiledFunc:
    """Wrapper for @ql.compile decorated functions.

    On first call with a given (classical_args, widths) key, captures the
    gate sequence produced by the function.  On subsequent calls with the
    same key, replays the cached gates onto the caller's qubits without
    re-executing the function body.

    Parameters
    ----------
    func : callable
        The quantum function to compile.
    max_cache : int
        Maximum number of cache entries (oldest evicted first).
    key : callable or None
        Optional custom cache key function.
    verify : bool
        If True, run both capture and replay and compare (dev mode).
    """

    def __init__(
        self,
        func,
        max_cache=128,
        key=None,
        verify=False,
        optimize=True,
        inverse=False,
        debug=False,
        parametric=False,
        opt=1,
        merge_threshold=1,
    ):
        functools.update_wrapper(self, func)
        self._func = func
        self._cache = collections.OrderedDict()
        self._max_cache = max_cache
        self._key_func = key
        self._verify = verify
        self._optimize = optimize
        self._inverse_eager = inverse
        self._inverse_func = None
        self._debug = debug
        self._parametric = parametric
        self._opt = opt
        self._merge_threshold = merge_threshold
        self._merged_blocks = None
        if self._parametric and self._opt == 2:
            raise ValueError("parametric=True is not supported with opt=2")
        self._call_graph = None
        self._forward_calls = {}
        self._inverse_proxy = None
        self._adjoint_func = None
        self._stats = None
        self._total_hits = 0
        self._total_misses = 0
        # Parametric compilation state
        self._parametric_topology = None  # Cached topology signature (from probe)
        self._parametric_block = None  # Reference CompiledBlock for replay
        self._parametric_probed = False  # True after first capture (waiting for probe)
        self._parametric_safe = None  # True=safe, False=structural, None=unknown
        self._parametric_first_classical = None  # Classical args from first capture
        self._compile_mode = False
        # Register for cache invalidation on circuit reset
        _compiled_funcs.append(weakref.ref(self))
        # Eagerly create inverse wrapper when inverse=True
        if inverse:
            self._inverse_func = _InverseCompiledFunc(self)

    # -- compile-mode context manager ------------------------------------

    @contextlib.contextmanager
    def compile_mode(self, block=None):
        """Activate compile-mode IR recording for the duration of the block.

        While active, ``self._compile_mode`` is ``True`` and the module-level
        ``_active_compile_block`` points to *block* (or a temporary
        ``CompiledBlock`` if none is provided).  DSL operators check
        ``_is_compile_mode()`` to decide whether to emit
        ``InstructionRecord`` entries instead of calling ``run_instruction``.
        The flag is always reset on exit (even on exception).

        Parameters
        ----------
        block : CompiledBlock or None
            Target block whose ``_instruction_ir`` receives the records.
            If *None*, a lightweight temporary block is created.
        """
        if block is None:
            block = CompiledBlock(
                gates=[],
                total_virtual_qubits=0,
                param_qubit_ranges=[],
                internal_qubit_count=0,
                return_qubit_range=None,
            )
        prev_block = _get_active_compile_block()
        _set_active_compile_block(block)
        self._compile_mode = True
        try:
            yield self
        finally:
            self._compile_mode = False
            _set_active_compile_block(prev_block)

    def __call__(self, *args, **kwargs):
        """Call the compiled function (capture or replay)."""
        # Import helpers lazily from the package __init__ to avoid circular
        # imports at module load time.
        from . import (
            _get_mode_flags,
            _get_quantum_arg_qubit_indices,
        )

        # Classify args into quantum and classical
        quantum_args, classical_args, widths = self._classify_args(args, kwargs)

        # Detect controlled context
        is_controlled = _get_controlled()
        control_count = 1 if is_controlled else 0

        # Build cache key (no control_count -- single entry stores both
        # uncontrolled and controlled variants, selected at replay time)
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._key_func:
            cache_key = (self._key_func(*args, **kwargs), qubit_saving) + mode_flags
        else:
            cache_key = (
                tuple(classical_args),
                tuple(widths),
                qubit_saving,
            ) + mode_flags

        # Record CallRecord when called from inside another compiled
        # function's capture (compile-mode is active).  This stores a
        # reference so the outer function can replay us recursively
        # without inlining our gates.
        parent_block = _get_active_compile_block()
        _nested_call_record = None
        _nested_gc_before = 0
        if parent_block is not None:
            arg_indices = [_get_quantum_arg_qubit_indices(qa) for qa in quantum_args]
            _record_call(self, cache_key, arg_indices)
            _nested_call_record = parent_block._call_records[-1]
            _nested_call_record.gate_layer_start = get_current_layer()
            _nested_gc_before = get_gate_count()

        # DAG building (opt != 3)
        _building_dag = self._opt != 3
        _is_top_level_dag = False
        if _building_dag:
            ctx = current_dag_context()
            if ctx is None:
                # Top-level call: create fresh DAG (or reuse for opt=1
                # which accumulates nodes across calls for DAG-only mode)
                if self._opt != 1 or self._call_graph is None:
                    self._call_graph = CallGraphDAG()
                push_dag_context(self._call_graph)
                _is_top_level_dag = True

        try:
            result = self._call_inner(
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
            )
        finally:
            if _is_top_level_dag:
                pop_dag_context()
                if self._call_graph is not None:
                    if self._opt == 2:
                        self._apply_merge()
                    # opt=1 accumulates nodes across calls, so do not
                    # freeze the DAG after each call.  Other opt levels
                    # freeze immediately (graph is rebuilt each call).
                    if self._opt != 1:
                        self._call_graph.freeze()

        # Record the layer range and total gate count delta of the inner
        # call so the outer capture can exclude these gates from its own block.
        if _nested_call_record is not None:
            _nested_call_record.gate_layer_end = get_current_layer()
            _nested_call_record.gate_count_delta = get_gate_count() - _nested_gc_before

        return result

    def _call_inner(
        self,
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
        """Inner call logic, separated for DAG try/finally wrapper."""
        from . import (
            _build_dag_from_ir,
            _build_qubit_set_numpy,
        )

        # Parametric routing (PAR-02): if parametric and has classical args,
        # use the parametric probe/replay lifecycle instead of normal caching.
        if self._parametric and classical_args:
            result = self._parametric_call(
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
                    block = self._cache.get(cache_key)
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
                        self._func.__name__,
                        qubit_set,
                        len(_gates),
                        cache_key,
                        depth=_compute_depth(_gates),
                        t_count=_compute_t_count(_gates),
                        controlled=is_controlled,
                    )
            return result

        is_hit = cache_key in self._cache

        if is_hit:
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            _track_fwd = self._inverse_func is not None
            block = self._cache[cache_key]
            # _replay selects controlled/uncontrolled variant at runtime
            result = self._replay(block, quantum_args, track_forward=_track_fwd, kind="compiled_fn")
            # Manually credit gate count when run_instruction did NOT
            # already increment it.  run_instruction (IR path) always
            # increments circ->gate_count, so skip the manual credit
            # when the IR path was used.  inject_remapped_gates (gate-
            # level path) does NOT increment gate_count, and when
            # simulate=False neither path runs — both need manual credit.
            _used_ir = getattr(self, "_last_replay_used_ir", False)
            if not _used_ir and block is not None:
                _replay_count = (
                    block.original_gate_count if block.original_gate_count else len(block.gates)
                )
                if _replay_count:
                    add_gate_count(_replay_count)
            # Record DAG node for replay path (no nesting -- body not
            # re-executed).
            if _building_dag:
                if self._opt == 1 and block and block._instruction_ir and not block._dag_built:
                    # opt=1 with IR (QFT mode): build DAG nodes from
                    # instruction IR on the first replay only.
                    _ir_added = _build_dag_from_ir(
                        block,
                        self._func.__name__,
                        is_controlled=is_controlled,
                    )
                    if _ir_added > 0:
                        block._dag_built = True
                if self._opt != 1:
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
                        node_idx = dag.add_node(
                            self._func.__name__,
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
        else:
            result = self._capture_and_cache_both(
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
            if self._opt == 1:
                block = self._cache.get(cache_key)
                if block is not None:
                    block._captured_controlled = is_controlled
                    if _building_dag and block._instruction_ir and not block._dag_built:
                        _ir_added = _build_dag_from_ir(
                            block,
                            self._func.__name__,
                            is_controlled=is_controlled,
                        )
                        if _ir_added > 0:
                            block._dag_built = True

        if self._debug:
            block = self._cache.get(cache_key)
            if block is not None:
                if is_hit:
                    self._total_hits += 1
                else:
                    self._total_misses += 1
                print(
                    f"[ql.compile] {self._func.__name__}: "
                    f"{'HIT' if is_hit else 'MISS'} | "
                    f"original={block.original_gate_count} -> "
                    f"optimized={len(block.gates)} gates | "
                    f"cache_entries={len(self._cache)}",
                    file=sys.stderr,
                )
                self._stats = {
                    "cache_hit": is_hit,
                    "original_gate_count": block.original_gate_count,
                    "optimized_gate_count": len(block.gates),
                    "cache_size": len(self._cache),
                    "total_hits": self._total_hits,
                    "total_misses": self._total_misses,
                }

        return result

    def _classify_args(self, args, kwargs):
        """Separate quantum and classical arguments.

        Returns (quantum_args, classical_args, widths).
        quantum_args: list of qint/qbool/qarray in positional order.
        classical_args: list of non-quantum values.
        widths: list of int widths for qint, or ('arr', length) for qarray.
        """
        from ..qarray import qarray

        quantum_args = []
        classical_args = []
        widths = []

        for arg in args:
            if isinstance(arg, qarray):
                # Validate: empty qarray not supported
                if len(arg) == 0:
                    raise ValueError("Empty qarray not supported as compiled function argument")
                # Validate: stale qarray elements
                for elem in arg:  # Use iteration protocol
                    if getattr(elem, "_is_uncomputed", False) or not getattr(
                        elem, "allocated_qubits", True
                    ):
                        raise ValueError("qarray contains deallocated qubits")
                quantum_args.append(arg)
                widths.append(("arr", len(arg)))
            elif isinstance(arg, qint):
                quantum_args.append(arg)
                widths.append(arg.width)
            else:
                classical_args.append(arg)

        # Also classify kwargs (sorted by key for determinism)
        for k in sorted(kwargs):
            val = kwargs[k]
            if isinstance(val, qarray):
                # Validate: empty qarray not supported
                if len(val) == 0:
                    raise ValueError("Empty qarray not supported as compiled function argument")
                # Validate: stale qarray elements
                for elem in val:  # Use iteration protocol
                    if getattr(elem, "_is_uncomputed", False) or not getattr(
                        elem, "allocated_qubits", True
                    ):
                        raise ValueError("qarray contains deallocated qubits")
                quantum_args.append(val)
                widths.append(("arr", len(val)))
            elif isinstance(val, qint):
                quantum_args.append(val)
                widths.append(val.width)
            else:
                classical_args.append(val)

        return quantum_args, classical_args, widths

    def _capture(self, args, kwargs, quantum_args):
        """Capture gate sequence during first call."""
        if _block._capture_depth >= _MAX_CAPTURE_DEPTH:
            raise RecursionError(
                f"Compiled function nesting depth exceeded {_MAX_CAPTURE_DEPTH}. "
                "Possible circular compiled function calls."
            )
        _block._capture_depth += 1
        try:
            return self._capture_inner(args, kwargs, quantum_args)
        finally:
            _block._capture_depth -= 1

    def _capture_inner(self, args, kwargs, quantum_args):
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
        cache, so ``_derive_controlled_block`` can re-add control correctly.
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
        _gate_count_before = get_gate_count() if _use_tracking else 0

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
            with self.compile_mode(ir_block):
                result = self._func(*args, **kwargs)
        else:
            # QFT mode: clear control stack during IR recording, restore
            # it before IR execution so _execute_ir can inject control.
            saved_stack = list(_get_control_stack())
            _set_control_stack([])
            try:
                with self.compile_mode(ir_block):
                    result = self._func(*args, **kwargs)
            finally:
                _set_control_stack(saved_stack)

        # Execute the recorded IR to produce gates in the circuit.
        # In QFT mode, _execute_ir checks the (now-restored) control
        # stack and uses controlled sequences when inside a with block.
        # In Toffoli mode, _instruction_ir is empty (Toffoli dispatch
        # emitted gates directly), so this is a no-op.
        _execute_ir(ir_block)

        # Record end layer
        end_layer = get_current_layer()

        # In tracking-only mode, compute gate count from circ->gate_count
        # difference (gates were counted but not stored in the circuit).
        # Subtract inner call gate count deltas so original_gate_count
        # reflects only this function's OWN gates (inner gates are replayed
        # via _replay_call_records which credits them separately).
        # gate_count_delta is the total recursive delta (including
        # grandchildren), not just the inner function's own gates.
        _tracking_gate_count = 0
        if _use_tracking:
            _tracking_gate_count = get_gate_count() - _gate_count_before
            if ir_block._call_records:
                for cr in ir_block._call_records:
                    _tracking_gate_count -= cr.gate_count_delta

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
        # for the gate-level cache (controlled variant is derived later
        # by _derive_controlled_block).
        if is_controlled and control_physical_qubit is not None and raw_gates:
            raw_gates = _strip_control_qubit(raw_gates, control_physical_qubit)

        # Build virtual mapping
        virtual_gates, real_to_virtual, total_virtual = _build_virtual_mapping(
            raw_gates, param_qubit_indices
        )

        # Determine return value qubit range (if result is qint or qarray)
        from ..qarray import qarray

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
        original_count = _tracking_gate_count if _use_tracking else len(virtual_gates)
        if self._optimize:
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

    def _capture_and_cache_both(
        self,
        args,
        kwargs,
        quantum_args,
        classical_args,
        widths,
        is_controlled,
        cache_key,
    ):
        """Handle cache miss: capture uncontrolled, derive controlled, cache both.

        IR recording always happens with the control stack cleared (inside
        ``_capture_inner``).  IR execution (``_execute_ir``) runs with
        the original control stack intact, so the first call inside a
        ``with`` block produces correctly controlled gates.
        """
        from . import _input_qubit_key

        # _capture_inner handles control stack save/clear/restore internally:
        # IR recording runs uncontrolled, IR execution sees the real stack.
        block = self._capture(args, kwargs, quantum_args)

        # Derive controlled variant and attach to the same block
        try:
            controlled_block = self._derive_controlled_block(block)
        except Exception:
            # Fallback: re-capture in controlled mode (not expected with
            # current gate set, but guards against future gate types)
            controlled_block = self._capture(args, kwargs, quantum_args)
        block.controlled_block = controlled_block

        # Cache single entry (both variants stored on the block)
        self._cache[cache_key] = block

        # Evict oldest if over capacity
        while len(self._cache) > self._max_cache:
            self._cache.popitem(last=False)

        # Record forward call for inverse support (first call / capture path)
        result = block._first_call_result
        capture_ancillas = block._capture_ancilla_qubits or []
        if capture_ancillas:
            input_key = _input_qubit_key(quantum_args)
            self._forward_calls[input_key] = AncillaRecord(
                ancilla_qubits=capture_ancillas,
                virtual_to_real=block._capture_virtual_to_real or {},
                block=block,
                return_qint=result
                if (block.return_qubit_range is not None and block.return_is_param_index is None)
                else None,
            )

        return result

    def _derive_controlled_block(self, uncontrolled_block):
        """Create a controlled ``CompiledBlock`` from an uncontrolled one.

        The control qubit uses virtual index 0 (reserved by
        ``_build_virtual_mapping``).  ``total_virtual_qubits`` is the
        same as the uncontrolled block since index 0 is already counted.
        """
        from . import _derive_controlled_gates

        controlled_gates = _derive_controlled_gates(
            uncontrolled_block.gates,
        )

        controlled_block = CompiledBlock(
            gates=controlled_gates,
            total_virtual_qubits=uncontrolled_block.total_virtual_qubits,
            param_qubit_ranges=list(uncontrolled_block.param_qubit_ranges),
            internal_qubit_count=uncontrolled_block.internal_qubit_count,
            return_qubit_range=uncontrolled_block.return_qubit_range,
            return_is_param_index=uncontrolled_block.return_is_param_index,
            original_gate_count=uncontrolled_block.original_gate_count,
        )
        controlled_block.control_virtual_idx = 0
        controlled_block.return_type = uncontrolled_block.return_type
        controlled_block._return_qarray_element_widths = (
            uncontrolled_block._return_qarray_element_widths
        )
        # Share CallRecords so controlled replay also delegates to inner
        # functions (inner functions handle their own control propagation).
        controlled_block._call_records = uncontrolled_block._call_records
        controlled_block.transient_virtual_indices = uncontrolled_block.transient_virtual_indices
        return controlled_block

    # ------------------------------------------------------------------
    # Parametric compilation lifecycle (PAR-02 / PAR-03)
    # ------------------------------------------------------------------
    def _parametric_call(
        self,
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
        All parameters forwarded from __call__.
        """
        from . import _extract_topology

        # --- State: Unknown (first call ever) ---
        if self._parametric_safe is None and not self._parametric_probed:
            # First capture -- store topology for later probe
            result = self._capture_and_cache_both(
                args,
                kwargs,
                quantum_args,
                classical_args,
                widths,
                is_controlled,
                cache_key,
            )
            block = self._cache.get(cache_key)
            if block is not None:
                self._parametric_topology = _extract_topology(block.gates)
                self._parametric_block = block
                self._parametric_probed = True
                self._parametric_first_classical = tuple(classical_args)
            return result

        # --- State: Probed (waiting for second call with different args) ---
        if self._parametric_safe is None and self._parametric_probed:
            # Same classical args as first call? Normal cache hit
            if tuple(classical_args) == self._parametric_first_classical:
                is_hit = cache_key in self._cache
                if is_hit:
                    self._cache.move_to_end(cache_key)
                    block = self._cache[cache_key]
                    return self._replay(block, quantum_args, kind="compiled_fn")
                else:
                    # Mode flags changed -- re-probe from scratch
                    self._parametric_probed = False
                    self._parametric_topology = None
                    self._parametric_block = None
                    self._parametric_first_classical = None
                    return self._parametric_call(
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
            result = self._capture_and_cache_both(
                args,
                kwargs,
                quantum_args,
                classical_args,
                widths,
                is_controlled,
                cache_key,
            )
            block = self._cache.get(cache_key)
            if block is not None:
                probe_topology = _extract_topology(block.gates)
                if probe_topology == self._parametric_topology:
                    # Topology matches! Function is parametric-safe
                    self._parametric_safe = True
                else:
                    # Topology differs -- structural parameter detected
                    self._parametric_safe = False
                    self._parametric_topology = None
                    self._parametric_block = None
            return result

        # --- State: Structural (fallback to per-value caching) ---
        if self._parametric_safe is False:
            # Standard per-value behavior (same as non-parametric)
            is_hit = cache_key in self._cache
            if is_hit:
                self._cache.move_to_end(cache_key)
                block = self._cache[cache_key]
                return self._replay(block, quantum_args, kind="compiled_fn")
            return self._capture_and_cache_both(
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
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            block = self._cache[cache_key]
            return self._replay(block, quantum_args, kind="compiled_fn")

        # New classical value: capture to get correct gates and cache per-value
        result = self._capture_and_cache_both(
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
        block = self._cache.get(cache_key)
        if block is not None:
            new_topology = _extract_topology(block.gates)
            if new_topology != self._parametric_topology:
                # Topology diverged! Revert to per-value caching
                self._parametric_safe = False
                self._parametric_topology = None
                self._parametric_block = None

        return result

    def _replay(self, block, quantum_args, track_forward=True, kind=None):
        """Replay cached gates with qubit remapping.

        Checks the control stack at runtime and selects the appropriate gate
        sequence.  If the block has a ``controlled_block`` and we are inside
        a controlled context (``with qbool:``), the controlled variant is
        used and its control virtual index is mapped to the actual control
        qubit.  Otherwise the uncontrolled variant is used directly.

        Parameters
        ----------
        block : CompiledBlock
            The *base* (uncontrolled) block.  ``block.controlled_block`` is
            used automatically when the control stack is active.
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

        # --- Runtime sequence selection (Phase 5, Step 5.2) ---
        is_controlled = _get_controlled()
        if is_controlled and block.controlled_block is not None:
            block = block.controlled_block

        # Build virtual-to-real mapping from caller's qints/qarrays.
        # Virtual index 0 is reserved for the control qubit; params
        # start at index 1.
        virtual_to_real = {}

        # Map control qubit at index 0 when in controlled context
        if is_controlled and block.control_virtual_idx is not None:
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
        #
        # Find the base (uncontrolled) block that has IR entries.
        # The derived controlled_block does not store IR — _execute_ir
        # handles control selection internally using the control stack.
        _ir_source = None
        if block._instruction_ir:
            _ir_source = block
        elif hasattr(self, "_cache"):
            for _cb in self._cache.values():
                if _cb.controlled_block is block and _cb._instruction_ir:
                    _ir_source = _cb
                    break

        # Determine which virtual indices are transient.  For the IR path,
        # run_instruction allocates its own internal ancillas, so we skip
        # allocation for transient virtual indices (Step 8.2).  For the
        # gate-level path, all internal qubits must be allocated (the
        # injected gate tuples reference them directly).
        _will_use_ir = (
            _ir_source is not None
            and _ir_source._instruction_ir
            and option("simulate")
            and not (self._opt == 1 and not is_controlled and not option("simulate"))
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
        # - Forward replay f(x) and adjoint replay f.adjoint(x) produce EQUAL
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
        self._last_replay_used_ir = False
        _skip_injection = self._opt == 1 and not is_controlled and not option("simulate")
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
                self._last_replay_used_ir = True
            elif block.gates:
                # Gate-level path: inject remapped gates into the circuit.
                inject_remapped_gates(block.gates, virtual_to_real)

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
                target.history.append(id(self), _qm, len(ancilla_qubits), kind=kind)

        # Record forward call for inverse support.
        # Always record when internal qubits exist, even if ancilla_qubits
        # is empty after transient freeing -- inverse() still needs the
        # virtual_to_real mapping to replay adjoint gates.
        if track_forward and block.internal_qubit_count > 0:
            input_key = _input_qubit_key(quantum_args)
            if input_key in self._forward_calls:
                raise ValueError(
                    f"Compiled function '{self._func.__name__}' already has an uninverted "
                    f"forward call with these input qubits. Call {self._func.__name__}.inverse() first."
                )
            self._forward_calls[input_key] = AncillaRecord(
                ancilla_qubits=ancilla_qubits,
                virtual_to_real=dict(virtual_to_real),
                block=block,
                return_qint=result
                if (block.return_qubit_range is not None and block.return_is_param_index is None)
                else None,
            )

        return result

    # ------------------------------------------------------------------
    # Selective sequence merging (opt=2)
    # ------------------------------------------------------------------
    def _apply_merge(self):
        """Merge overlapping sequences after first call (opt=2).

        Gets merge groups from the call graph, collects CompiledBlocks and
        their virtual-to-real mappings, runs _merge_and_optimize, and stores
        merged CompiledBlocks keyed by frozenset of node indices.
        """
        from . import _merge_and_optimize

        if self._call_graph is None:
            return
        groups = self._call_graph.merge_groups(self._merge_threshold)
        if not groups:
            return

        merged_blocks = {}
        for group in groups:
            blocks_with_mappings = []
            for node_idx in group:
                node = self._call_graph._nodes[node_idx]
                block = node._block_ref
                v2r = node._v2r_ref
                if block is None or v2r is None:
                    # Block not available for this node; skip this group
                    break
                blocks_with_mappings.append((block, v2r))
            else:
                # All blocks found -- merge them
                merged_gates, original_count = _merge_and_optimize(
                    blocks_with_mappings, optimize=self._optimize
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
            self._merged_blocks = merged_blocks

        if self._debug and merged_blocks:
            merge_stats = {
                "merge_groups": len(groups),
                "merged_blocks": len(merged_blocks),
            }
            for gk, mb in merged_blocks.items():
                merge_stats[f"group_{sorted(gk)}_gates"] = len(mb.gates)
                merge_stats[f"group_{sorted(gk)}_original"] = mb.original_gate_count
            if self._stats is None:
                self._stats = {}
            self._stats["merge"] = merge_stats

    # ------------------------------------------------------------------
    # Parametric introspection
    # ------------------------------------------------------------------
    @property
    def is_parametric(self):
        """Whether this compiled function uses parametric mode."""
        return self._parametric

    # ------------------------------------------------------------------
    # Debug introspection
    # ------------------------------------------------------------------
    @property
    def stats(self):
        """Return debug stats dict, or None when debug=False."""
        return self._stats

    # ------------------------------------------------------------------
    # Optimisation statistics
    # ------------------------------------------------------------------
    @property
    def original_gates(self):
        """Total original (pre-optimisation) gate count across all cache entries."""
        return sum(b.original_gate_count for b in self._cache.values())

    @property
    def optimized_gates(self):
        """Total optimised gate count across all cache entries."""
        return sum(len(b.gates) for b in self._cache.values())

    @property
    def reduction_percent(self):
        """Percentage reduction from optimisation."""
        orig = self.original_gates
        if orig == 0:
            return 0.0
        return 100.0 * (1.0 - self.optimized_gates / orig)

    @property
    def gate_count(self):
        """Hierarchical gate count: own gates + sum of referenced function gate counts.

        For each cached ``CompiledBlock``, computes the block's own gate count
        plus the recursive gate count of any ``CallRecord`` references.
        Returns a dict with ``'own'``, ``'referenced'``, and ``'total'`` keys.

        If no blocks are cached, returns zeros.
        """
        return self._hierarchical_gate_count()

    def _hierarchical_gate_count(self, visited=None):
        """Compute hierarchical gate count, with cycle detection.

        Parameters
        ----------
        visited : set or None
            Set of ``id(CompiledFunc)`` already visited, to prevent infinite
            recursion from circular references.

        Returns
        -------
        dict
            ``{'own': int, 'referenced': int, 'total': int,
              'breakdown': list[dict]}``
        """
        if visited is None:
            visited = set()

        my_id = id(self)
        if my_id in visited:
            return {"own": 0, "referenced": 0, "total": 0, "breakdown": []}
        visited.add(my_id)

        total_own = 0
        total_referenced = 0
        breakdown = []

        for _cache_key, block in self._cache.items():
            own_gates = len(block.gates)
            total_own += own_gates

            call_records = getattr(block, "_call_records", None) or []
            for cr in call_records:
                inner_func = cr.compiled_func_ref
                if inner_func is not None and hasattr(inner_func, "_hierarchical_gate_count"):
                    inner_counts = inner_func._hierarchical_gate_count(visited=set(visited))
                    ref_total = inner_counts["total"]
                    total_referenced += ref_total
                    breakdown.append(
                        {
                            "func_name": getattr(inner_func, "__name__", str(inner_func)),
                            "cache_key": cr.cache_key,
                            "gate_count": ref_total,
                        }
                    )

        return {
            "own": total_own,
            "referenced": total_referenced,
            "total": total_own + total_referenced,
            "breakdown": breakdown,
        }

    @property
    def inverse(self):
        """Return an ``_AncillaInverseProxy`` for uncomputing a prior forward call.

        Usage: f.inverse(x) -- looks up the forward call where x was the input,
        replays adjoint gates on the original ancilla qubits, deallocates them.
        Returns None.
        """
        if self._inverse_proxy is None:
            self._inverse_proxy = _AncillaInverseProxy(self)
        return self._inverse_proxy

    @property
    def adjoint(self):
        """Return an ``_InverseCompiledFunc`` for standalone adjoint replay.

        Usage: f.adjoint(x) -- runs the adjoint gate sequence with fresh
        ancillas. No prior forward call needed. Does NOT track ancillas.
        """
        if self._adjoint_func is None:
            self._adjoint_func = _InverseCompiledFunc(self)
        return self._adjoint_func

    def _reset_for_circuit(self):
        """Reset cache for a new circuit while preserving parametric state.

        Called by the circuit-reset hook (``ql.circuit()``).  Preserves
        parametric detection state (topology, probed, safe) so that the
        two-capture probe can span multiple circuits.  The topology
        signature is a function-intrinsic property that does not depend
        on circuit state.
        """
        self._cache.clear()
        self._forward_calls.clear()
        self._call_graph = None
        self._merged_blocks = None
        # Preserve parametric state across circuits; only clear the block
        # reference since its cache entry is gone.
        self._parametric_block = None
        if self._inverse_func is not None:
            self._inverse_func._reset_for_circuit()
        if self._adjoint_func is not None:
            self._adjoint_func._reset_for_circuit()

    def clear_cache(self):
        """Clear this function's compilation cache and parametric state.

        Fully resets all state, including parametric probe detection.
        Use this for explicit cache invalidation.
        """
        self._cache.clear()
        self._forward_calls.clear()
        # Full reset of parametric state
        self._parametric_topology = None
        self._parametric_block = None
        self._parametric_probed = False
        self._parametric_safe = None
        self._parametric_first_classical = None
        if self._inverse_func is not None:
            self._inverse_func.clear_cache()
        if self._adjoint_func is not None:
            self._adjoint_func.clear_cache()

    @property
    def call_graph(self):
        """Return the CallGraphDAG from the most recent top-level call, or None."""
        return self._call_graph

    def __repr__(self):
        return f"<CompiledFunc {self._func.__name__}>"


# ---------------------------------------------------------------------------
# Inverse classes (delegated to _inverse module)
# ---------------------------------------------------------------------------
from ._inverse import _AncillaInverseProxy, _InverseCompiledFunc  # noqa: E402


# ---------------------------------------------------------------------------
# Public decorator API
# ---------------------------------------------------------------------------
def compile(
    func=None,
    *,
    max_cache=128,
    key=None,
    verify=False,
    optimize=True,
    inverse=False,
    debug=False,
    parametric=False,
    opt=1,
    merge_threshold=1,
):
    """Decorator that compiles a quantum function for cached gate replay.

    Supports three forms:
      @ql.compile
      @ql.compile()
      @ql.compile(max_cache=N, key=..., verify=..., optimize=..., parametric=...)

    Parameters
    ----------
    func : callable, optional
        When used as bare @ql.compile (no parens).
    max_cache : int
        Maximum cache entries per function (default 128).
    key : callable or None
        Custom cache key function. Receives same args as decorated function.
    verify : bool
        If True, compare capture vs replay gate sequences (dev mode).
    optimize : bool
        If True (default), optimise the captured gate list by cancelling
        adjacent inverse gates and merging consecutive rotations before
        caching.  Set to False to store the raw captured sequence.
    parametric : bool
        If True, enable parametric compilation mode.  The function is
        captured once and replayed with different classical argument
        values without re-capturing the gate sequence.  Falls back to
        per-value caching when classical arguments affect gate topology
        (e.g. Toffoli CQ operations where the value determines which
        qubits receive X gates).  If the function has no classical
        arguments, ``parametric=True`` is a silent no-op.

        Toffoli CQ note: operations like ``x += classical_val`` produce
        value-dependent gate topology because CQ encoding maps each set
        bit of the classical value to an X gate.  Parametric mode
        detects this automatically on the second call with a different
        classical value and falls back to per-value caching for
        correctness.  No user action is required.

    Returns
    -------
    CompiledFunc or decorator
        CompiledFunc wrapper or decorator function.

    Notes
    -----
    Gate simulation is controlled by ``ql.option('simulate')``, not by a
    per-function parameter.  When ``simulate`` is False (default), gates
    are counted but not stored in the circuit.  Set
    ``ql.option('simulate', True)`` before calling compiled functions to
    enable full circuit construction.

    Examples
    --------
    >>> @ql.compile
    ... def add_one(x):
    ...     x += 1
    ...     return x

    >>> @ql.compile(max_cache=16)
    ... def multiply(x, y):
    ...     return x * y
    """

    def decorator(fn):
        return CompiledFunc(
            fn,
            max_cache=max_cache,
            key=key,
            verify=verify,
            optimize=optimize,
            inverse=inverse,
            debug=debug,
            parametric=parametric,
            opt=opt,
            merge_threshold=merge_threshold,
        )

    if func is not None:
        # Called as @ql.compile (bare) -- func is the decorated function
        return CompiledFunc(
            func,
            max_cache=max_cache,
            key=key,
            verify=verify,
            optimize=optimize,
            inverse=inverse,
            debug=debug,
            parametric=parametric,
            opt=opt,
            merge_threshold=merge_threshold,
        )
    # Called as @ql.compile() or @ql.compile(max_cache=N)
    return decorator
