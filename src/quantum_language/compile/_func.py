"""CompiledFunc class and public compile decorator.

Contains the ``CompiledFunc`` wrapper returned by ``@ql.compile`` and
the ``compile`` decorator factory.  Capture logic is in ``_capture``,
replay logic in ``_replay``, IR execution in ``_ir``, inverse classes
(``_InverseProxy``) in ``_inverse``,
call dispatch in ``_dispatch``, and cache registry in ``_registry``.
"""

import contextlib
import functools

from .._compile_state import (
    _get_active_compile_block,
    _record_call,
    _set_active_compile_block,
)
from .._core import (
    _get_control_stack,
    _get_controlled,
    _get_qubit_saving_mode,
    get_current_layer,
    get_gate_count,
)
from ..call_graph import (
    CallGraphDAG,
    _compute_depth,
    _compute_t_count,
    current_dag_context,
    pop_calling_context,
    pop_dag_context,
    push_calling_context,
    push_dag_context,
)
from ._block import (
    CompiledBlock,
)
from ._capture import (
    _capture as _capture_impl,
)
from ._capture import (
    _capture_and_cache as _capture_and_cache_impl,
)
from ._dispatch import (
    _call_inner_impl,
    _parametric_call_impl,
)
from ._registry import (
    classify_args,
    hierarchical_gate_count,
    register_compiled_func,
)
from ._replay import (
    _apply_merge as _apply_merge_impl,
)
from ._replay import (
    _replay as _replay_impl,
)


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
        import collections

        functools.update_wrapper(self, func)
        self._func = func
        self._cache = collections.OrderedDict()
        self._max_cache = max_cache
        self._key_func = key
        self._verify = verify
        self._optimize = optimize
        self._inverse_eager = inverse
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
        register_compiled_func(self)
        # Eagerly create inverse wrapper when inverse=True
        if inverse:
            _ = self.inverse  # force lazy creation

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
        from . import (
            _get_mode_flags,
            _get_quantum_arg_qubit_indices,
        )

        # Classify args into quantum and classical
        quantum_args, classical_args, widths = self._classify_args(args, kwargs)

        # Detect controlled context
        is_controlled = _get_controlled()
        control_count = 1 if is_controlled else 0

        # Build cache key (includes control_count so controlled and
        # uncontrolled calls produce separate cache entries with
        # independent, correct original_gate_count values)
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._key_func:
            cache_key = (self._key_func(*args, **kwargs), qubit_saving, control_count) + mode_flags
        else:
            cache_key = (
                tuple(classical_args),
                tuple(widths),
                qubit_saving,
                control_count,
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
        _pushed_calling_ctx = False

        # Determine if this call has internal control relative to the
        # outer function (i.e., is called inside a ``with c:`` block in
        # the outer function's source).  Compare the current control
        # depth with the outer function's baseline.
        _has_internal_control = False
        if _building_dag:
            from ..call_graph import current_calling_context as _cur_cc

            _outer_ctx = _cur_cc()
            if _outer_ctx is not None:
                _, _outer_baseline = _outer_ctx
                _has_internal_control = len(_get_control_stack()) > _outer_baseline
            else:
                _has_internal_control = is_controlled

        # When this is a nested compiled-function call and an outer DAG
        # context exists, temporarily pop the outer DAG so that inner
        # operations (record_operation calls) do not pollute the outer
        # function's DAG.  After the inner call completes, restore the
        # outer DAG and add a single call node representing this invocation.
        _outer_dag = None
        if _building_dag and _nested_call_record is not None:
            _outer_dag = current_dag_context()
            if _outer_dag is not None:
                pop_dag_context()
        if _building_dag:
            ctx = current_dag_context()
            if ctx is None:
                # Top-level call: create fresh DAG (or reuse for opt=1
                # which accumulates nodes across calls for DAG-only mode)
                if self._opt != 1 or self._call_graph is None:
                    self._call_graph = CallGraphDAG(func_name=self._func.__name__)
                push_dag_context(self._call_graph)
                _is_top_level_dag = True
            # Push calling context so record_operation knows whether the
            # enclosing function was called controlled or uncontrolled.
            # Include the control depth baseline so internal control
            # (from ``with c:`` inside the function) can be distinguished
            # from external control (from the calling context).
            push_calling_context(is_controlled, len(_get_control_stack()))
            _pushed_calling_ctx = True

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
            # Pop calling context before restoring outer DAG
            if _pushed_calling_ctx:
                pop_calling_context()
            if _is_top_level_dag:
                pop_dag_context()
                if self._call_graph is not None:
                    if self._opt == 2:
                        self._apply_merge()
                    # Backfill call nodes whose sibling context wasn't
                    # available at creation time but is now cached.
                    self._call_graph.backfill_call_node_siblings()
                    # opt=1 accumulates nodes across calls, so do not
                    # freeze the DAG after each call.  Other opt levels
                    # freeze immediately (graph is rebuilt each call).
                    if self._opt != 1:
                        self._call_graph.freeze()
            # Restore the outer DAG context and add a call node for this
            # nested compiled-function invocation.
            if _outer_dag is not None:
                push_dag_context(_outer_dag)
                self._add_nested_call_dag_node(
                    _outer_dag,
                    quantum_args,
                    cache_key,
                    is_controlled,
                    _has_internal_control,
                )

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
        return _call_inner_impl(
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
        )

    def _add_nested_call_dag_node(
        self, dag, quantum_args, cache_key, is_controlled, has_internal_control=False
    ):
        """Add a call node to *dag* representing this nested compiled call.

        With calling-context semantics:
        - U = this call's actual cost (cost when enclosing function is uncontrolled)
        - C = cost with one more control (cost when enclosing function is controlled)
        - For calls without internal control, C = sibling variant's cost.
        - For calls with internal control, C = 0 (doubly-controlled unknown).
        - Name is prefixed with "c_" when has_internal_control is True.

        Parameters
        ----------
        has_internal_control : bool
            Whether this call is inside a ``with c:`` block in the outer
            function's source code.  Determined by comparing control stack
            depth with the outer function's baseline.
        """
        from . import _build_qubit_set_numpy

        block = self._cache.get(cache_key)
        _gc = 0
        _depth = 0
        _t_count = 0
        if block is not None:
            _gc = block.original_gate_count if block.original_gate_count else len(block.gates)
            _depth = _compute_depth(block.gates)
            _t_count = _compute_t_count(block.gates)

        # Wrapper functions (those that only call other compiled functions
        # with no direct operations) have empty block.gates and
        # original_gate_count == 0.  Fall back to the inner call_graph
        # aggregate which correctly accounts for all nested calls.
        _is_wrapper = _gc == 0 and self._call_graph is not None and self._call_graph.node_count > 0
        if _is_wrapper:
            agg = self._call_graph.aggregate()
            if is_controlled:
                _gc = agg.get("gates_cc", 0) or agg["gates"]
                _depth = agg.get("depth_cc", 0) or agg["depth"]
                _t_count = agg.get("t_count_cc", 0) or agg["t_count"]
            else:
                _gc = agg.get("gates_uc", 0) or agg["gates"]
                _depth = agg.get("depth_uc", 0) or agg["depth"]
                _t_count = agg.get("t_count_uc", 0) or agg["t_count"]

        extra = None
        if block and block._capture_virtual_to_real:
            extra = block._capture_virtual_to_real.values()
        qubit_set, _ = _build_qubit_set_numpy(quantum_args, extra)

        # Determine if the OUTER function is called controlled so we put
        # _gc on the correct side (U vs C).
        from ..call_graph import current_calling_context as _cur_cc

        _outer_ctx = _cur_cc()
        _outer_is_controlled = _outer_ctx[0] if _outer_ctx else False

        # Place cost on the correct side based on outer calling context.
        # No sibling lookup — only populate the side that was actually captured.
        if _outer_is_controlled:
            cc_gc, cc_depth, cc_tc = _gc, _depth, _t_count
            uc_gc, uc_depth, uc_tc = 0, 0, 0
        else:
            uc_gc, uc_depth, uc_tc = _gc, _depth, _t_count
            cc_gc, cc_depth, cc_tc = 0, 0, 0

        # Prefix name with "c_" for internally controlled calls
        func_name = self._func.__name__
        if has_internal_control:
            func_name = "c_" + func_name

        node_idx = dag.add_node(
            func_name,
            qubit_set,
            _gc,
            cache_key,
            depth=_depth,
            t_count=_t_count,
            controlled=is_controlled,
            is_call_node=True,
            uncontrolled_gate_count=uc_gc,
            controlled_gate_count=cc_gc,
            uncontrolled_depth=uc_depth,
            controlled_depth=cc_depth,
            uncontrolled_t_count=uc_tc,
            controlled_t_count=cc_tc,
        )
        # Store ref so backfill_call_node_siblings can resolve sibling costs
        dag._nodes[node_idx]._compiled_func_ref = self

    def _classify_args(self, args, kwargs):
        """Separate quantum and classical arguments."""
        return classify_args(args, kwargs)

    def _capture(self, args, kwargs, quantum_args):
        """Capture gate sequence during first call."""
        return _capture_impl(self, args, kwargs, quantum_args)

    def _capture_inner(self, args, kwargs, quantum_args):
        """Inner capture logic (delegates to _capture module)."""
        from ._capture import _capture_inner as _ci

        return _ci(self, args, kwargs, quantum_args)

    def _capture_and_cache(
        self,
        args,
        kwargs,
        quantum_args,
        classical_args,
        widths,
        is_controlled,
        cache_key,
    ):
        """Handle cache miss: capture and cache a single block."""
        return _capture_and_cache_impl(
            self,
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
        )

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
        """Handle parametric compilation (delegates to _dispatch)."""
        return _parametric_call_impl(
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
        )

    def _replay(self, block, quantum_args, track_forward=True, kind=None):
        """Replay cached gates with qubit remapping."""
        return _replay_impl(self, block, quantum_args, track_forward=track_forward, kind=kind)

    # ------------------------------------------------------------------
    # Selective sequence merging (opt=2)
    # ------------------------------------------------------------------
    def _apply_merge(self):
        """Merge overlapping sequences after first call (opt=2)."""
        return _apply_merge_impl(self)

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
        """Hierarchical gate count: own gates + sum of referenced function gate counts."""
        return self._hierarchical_gate_count()

    def _hierarchical_gate_count(self, visited=None):
        """Compute hierarchical gate count, with cycle detection."""
        return hierarchical_gate_count(self, visited=visited)

    @property
    def inverse(self):
        """Return an ``_InverseProxy`` for applying the inverse of this function.

        The proxy auto-dispatches: if a forward-call record exists for
        the input qubits, it reuses the original ancilla qubits and
        deallocates them; otherwise it does a standalone adjoint replay.
        """
        if self._inverse_proxy is None:
            self._inverse_proxy = _InverseProxy(self)
        return self._inverse_proxy

    @property
    def adjoint(self):
        """Alias for :attr:`inverse`."""
        return self.inverse

    def _reset_for_circuit(self):
        """Reset cache for a new circuit while preserving parametric state."""
        self._cache.clear()
        self._forward_calls.clear()
        self._call_graph = None
        self._merged_blocks = None
        # Preserve parametric state across circuits; only clear the block
        # reference since its cache entry is gone.
        self._parametric_block = None
        if self._inverse_proxy is not None:
            self._inverse_proxy._reset_for_circuit()

    def clear_cache(self):
        """Clear this function's compilation cache and parametric state."""
        self._cache.clear()
        self._forward_calls.clear()
        # Full reset of parametric state
        self._parametric_topology = None
        self._parametric_block = None
        self._parametric_probed = False
        self._parametric_safe = None
        self._parametric_first_classical = None
        if self._inverse_proxy is not None:
            self._inverse_proxy.clear_cache()

    @property
    def call_graph(self):
        """Return the CallGraphDAG from the most recent top-level call, or None."""
        return self._call_graph

    def report(self):
        """Return a compilation report grouped by compiled variant.

        Each cache entry (unique classical args + control context) is
        shown as a separate table section.

        Returns
        -------
        str
            Multi-line formatted report.
        """
        if not self._cache:
            return f"Compilation Report: {self._func.__name__}\n\n  (not compiled yet)"

        dag = self._call_graph
        if dag is None:
            return f"Compilation Report: {self._func.__name__}\n\n  (no call graph)"

        header = f"{'Name':<20s} | {'Gates':>8s} | {'Depth':>8s} | {'Qubits':>8s} | {'T-count':>8s}"
        sep = "-" * len(header)
        lines = [f"Compilation Report: {self._func.__name__}"]

        for cache_key, block in self._cache.items():
            # Build section label
            classical_args = cache_key[0] if cache_key else ()
            is_ctrl = getattr(block, "_captured_controlled", False)
            context = "Controlled" if is_ctrl else "Uncontrolled"
            if classical_args:
                args_str = ", ".join(str(a) for a in classical_args)
                label = f"{context} ({args_str})"
            else:
                label = context

            # Pick the right gate count attributes for this context
            if is_ctrl:
                g_attr = "controlled_gate_count"
                d_attr = "controlled_depth"
                t_attr = "controlled_t_count"
            else:
                g_attr = "uncontrolled_gate_count"
                d_attr = "uncontrolled_depth"
                t_attr = "uncontrolled_t_count"

            # Collect all operations from DAG node indices.
            # This includes both @ql.compile call nodes (make_move, foo)
            # and built-in ops (eq_cq, add_cq) dispatched by the backend.
            nodes = []
            indices = block._dag_node_indices
            if indices:
                for idx in indices:
                    if idx < len(dag._nodes):
                        n = dag._nodes[idx]
                        if getattr(n, g_attr, 0):
                            nodes.append(n)

            # For wrappers (no dag nodes), use call records instead.
            if not nodes:
                call_records = getattr(block, "_call_records", None)
                if call_records:
                    for cr in call_records:
                        inner = cr.compiled_func_ref
                        if inner is None:
                            continue
                        inner_block = inner._cache.get(cr.cache_key)
                        if inner_block is None:
                            continue
                        name = inner._func.__name__
                        gc = (
                            inner_block.original_gate_count
                            if inner_block.original_gate_count
                            else len(inner_block.gates)
                        )
                        inner_dag = inner._call_graph
                        if gc == 0 and inner_dag is not None:
                            agg = inner_dag.aggregate()
                            if is_ctrl:
                                gc = agg.get("gates_cc", 0) or agg.get("gates", 0)
                                tc = agg.get("t_count_cc", 0) or agg.get("t_count", 0)
                            else:
                                gc = agg.get("gates_uc", 0) or agg.get("gates", 0)
                                tc = agg.get("t_count_uc", 0) or agg.get("t_count", 0)
                        else:
                            tc = _compute_t_count(inner_block.gates)
                        if gc:
                            nodes.append(_ReportRow(name, gc, 0, set(), tc))

            if not nodes:
                continue

            lines.append("")
            lines.append(f"  {label}:")
            lines.append(f"  {header}")
            lines.append(f"  {sep}")
            total_g = 0
            total_t = 0
            for nd in nodes:
                g = getattr(nd, g_attr, 0) if hasattr(nd, g_attr) else nd.gate_count
                d = getattr(nd, d_attr, 0) if hasattr(nd, d_attr) else nd.depth
                t = getattr(nd, t_attr, 0) if hasattr(nd, t_attr) else nd.t_count
                qs = nd.qubit_set if hasattr(nd, "qubit_set") else set()
                total_g += g
                total_t += t
                lines.append(f"  {nd.func_name:<20s} | {g:>8d} | {d:>8d} | {len(qs):>8d} | {t:>8d}")
            lines.append(f"  {sep}")
            total_d = max(
                (getattr(n, d_attr, 0) if hasattr(n, d_attr) else n.depth for n in nodes),
                default=0,
            )
            total_q = (
                len(
                    set().union(
                        *(n.qubit_set for n in nodes if hasattr(n, "qubit_set") and n.qubit_set)
                    )
                )
                if nodes
                else 0
            )
            lines.append(
                f"  {'TOTAL':<20s} | {total_g:>8d} | {total_d:>8d} | {total_q:>8d} | {total_t:>8d}"
            )

        return "\n".join(lines)


class _ReportRow:
    """Lightweight stand-in for a DAGNode in report tables."""

    __slots__ = ("func_name", "gate_count", "depth", "qubit_set", "t_count")

    def __init__(self, func_name, gate_count, depth, qubit_set, t_count):
        self.func_name = func_name
        self.gate_count = gate_count
        self.depth = depth
        self.qubit_set = qubit_set
        self.t_count = t_count

    def __repr__(self):
        return f"<CompiledFunc {self._func.__name__}>"


# ---------------------------------------------------------------------------
# Inverse classes (delegated to _inverse module)
# ---------------------------------------------------------------------------
from ._inverse import _InverseProxy  # noqa: E402


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
        If True, enable parametric compilation mode.

    Returns
    -------
    CompiledFunc or decorator
        CompiledFunc wrapper or decorator function.
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
