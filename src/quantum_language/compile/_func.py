"""CompiledFunc class and public compile decorator.

Contains the ``CompiledFunc`` wrapper returned by ``@ql.compile`` and
the ``compile`` decorator factory.  Capture logic is in ``_capture``,
replay logic in ``_replay``, IR execution in ``_ir``, inverse classes
(``_InverseCompiledFunc``, ``_AncillaInverseProxy``) in ``_inverse``.
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
    _get_controlled,
    _get_qubit_saving_mode,
    _register_cache_clear_hook,
    add_gate_count,
    get_current_layer,
    get_gate_count,
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
    CompiledBlock,
)
from ._capture import (
    _capture as _capture_impl,
)
from ._capture import (
    _capture_and_cache_both as _capture_and_cache_both_impl,
)
from ._capture import (
    _derive_controlled_block as _derive_controlled_block_impl,
)
from ._replay import (
    _apply_merge as _apply_merge_impl,
)
from ._replay import (
    _replay as _replay_impl,
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
        return _capture_impl(self, args, kwargs, quantum_args)

    def _capture_inner(self, args, kwargs, quantum_args):
        """Inner capture logic (delegates to _capture module)."""
        from ._capture import _capture_inner as _ci

        return _ci(self, args, kwargs, quantum_args)

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
        """Handle cache miss: capture uncontrolled, derive controlled, cache both."""
        return _capture_and_cache_both_impl(
            self,
            args,
            kwargs,
            quantum_args,
            classical_args,
            widths,
            is_controlled,
            cache_key,
        )

    def _derive_controlled_block(self, uncontrolled_block):
        """Create a controlled CompiledBlock from an uncontrolled one."""
        return _derive_controlled_block_impl(self, uncontrolled_block)

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
