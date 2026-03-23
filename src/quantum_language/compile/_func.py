"""CompiledFunc class and public compile decorator.

Contains the ``CompiledFunc`` wrapper returned by ``@ql.compile`` and
the ``compile`` decorator factory.  Capture logic is in ``_capture``,
replay logic in ``_replay``, IR execution in ``_ir``, inverse classes
(``_InverseCompiledFunc``, ``_AncillaInverseProxy``) in ``_inverse``,
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
    _get_controlled,
    _get_qubit_saving_mode,
    get_current_layer,
    get_gate_count,
)
from ..call_graph import (
    CallGraphDAG,
    current_dag_context,
    pop_dag_context,
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
        register_compiled_func(self)
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
        """Return an ``_AncillaInverseProxy`` for uncomputing a prior forward call."""
        if self._inverse_proxy is None:
            self._inverse_proxy = _AncillaInverseProxy(self)
        return self._inverse_proxy

    @property
    def adjoint(self):
        """Return an ``_InverseCompiledFunc`` for standalone adjoint replay."""
        if self._adjoint_func is None:
            self._adjoint_func = _InverseCompiledFunc(self)
        return self._adjoint_func

    def _reset_for_circuit(self):
        """Reset cache for a new circuit while preserving parametric state."""
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
        """Clear this function's compilation cache and parametric state."""
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
