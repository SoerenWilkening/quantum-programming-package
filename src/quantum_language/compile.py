"""Compile decorator for quantum function capture and replay.

Provides @ql.compile decorator that captures gate sequences on first call
and replays them with qubit remapping on subsequent calls.  When
``optimize=True`` (the default), adjacent inverse gates are cancelled and
consecutive rotations on the same qubit are merged before the sequence is
cached, so every replay benefits from the reduced gate count.

Usage
-----
>>> import quantum_language as ql
>>> ql.circuit()
>>> @ql.compile
... def add_one(x):
...     x += 1
...     return x
>>> a = ql.qint(3, width=4)
>>> result = add_one(a)   # Capture + optimise
>>> b = ql.qint(5, width=4)
>>> result2 = add_one(b)  # Replay (optimised sequence)
"""

import collections
import functools
import sys
import weakref

import numpy as np

from ._core import (
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
from .call_graph import (
    CallGraphDAG,
    _compute_depth,
    _compute_t_count,
    _dag_builder_stack,
    current_dag_context,
    pop_dag_context,
    push_dag_context,
)
from .qint import qint

# ---------------------------------------------------------------------------
# Gate type constants (from c_backend/include/types.h  Standardgate_t)
# ---------------------------------------------------------------------------
_X, _Y, _Z, _R, _H, _Rx, _Ry, _Rz, _P, _M = range(10)
_SELF_ADJOINT = frozenset({_X, _Y, _Z, _H})
_ROTATION_GATES = frozenset({_P, _Rx, _Ry, _Rz, _R})
_NON_REVERSIBLE = frozenset({_M})


# ---------------------------------------------------------------------------
# Mode flag helpers (FIX-04)
# ---------------------------------------------------------------------------
def _get_mode_flags():
    """Return current arithmetic mode flags for cache key inclusion.

    Returns a tuple of (arithmetic_mode, cla_override, tradeoff_policy)
    that uniquely identifies the arithmetic configuration.  Including these
    in the cache key ensures that switching modes between calls causes a
    clean cache miss rather than replaying stale gates (FIX-04).
    """
    arithmetic_mode = 1 if option("fault_tolerant") else 0
    cla_override = 0 if option("cla") else 1
    tradeoff_policy = option("tradeoff")
    return (arithmetic_mode, cla_override, tradeoff_policy)


# ---------------------------------------------------------------------------
# Parametric topology helpers
# ---------------------------------------------------------------------------
def _extract_topology(gates):
    """Extract the structural topology of a gate sequence.

    Returns a tuple of (gate_type, target, controls_tuple, num_controls)
    for each gate, which captures the circuit structure without angle
    values. Two gate sequences with identical topology differ only in
    rotation angles -- safe for parametric replay.

    Parameters
    ----------
    gates : list[dict]
        Virtual gate dicts from a CompiledBlock.

    Returns
    -------
    tuple[tuple]
        Hashable topology signature.
    """
    return tuple((g["type"], g["target"], tuple(g["controls"]), g["num_controls"]) for g in gates)


def _extract_angles(gates):
    """Extract rotation angles from a gate sequence.

    Returns a list of angles (float or None for non-rotation gates)
    preserving gate order. Used to build the parametric replay template.

    Parameters
    ----------
    gates : list[dict]
        Virtual gate dicts from a CompiledBlock.

    Returns
    -------
    list[float | None]
        Angle per gate (None for non-rotation gates).
    """
    return [g.get("angle") for g in gates]


def _apply_angles(template_gates, new_angles):
    """Create fresh gate list by applying new angles to a topology template.

    Parameters
    ----------
    template_gates : list[dict]
        Gate dicts from the cached parametric block (used as template).
    new_angles : list[float | None]
        New angle values from a fresh capture.

    Returns
    -------
    list[dict]
        New gate dicts with updated angles. Non-rotation gates are
        unchanged. Each gate dict is a fresh copy (no mutation).
    """
    result = []
    for g, angle in zip(template_gates, new_angles, strict=False):
        ng = dict(g)
        if angle is not None:
            ng["angle"] = angle
        result.append(ng)
    return result


# ---------------------------------------------------------------------------
# Inverse (adjoint) helpers
# ---------------------------------------------------------------------------
def _adjoint_gate(gate):
    """Return the adjoint of *gate*.

    Self-adjoint gates (X, Y, Z, H) are unchanged.  Rotation gates have
    their angle negated.  Measurement gates cannot be inverted.
    """
    if gate["type"] in _NON_REVERSIBLE:
        raise ValueError("Cannot invert compiled function containing measurement gates")
    adj = dict(gate)
    if gate["type"] in _ROTATION_GATES:
        adj["angle"] = -gate["angle"]
    return adj


def _inverse_gate_list(gates):
    """Return the adjoint of a gate list (reversed order, adjoint gates)."""
    return [_adjoint_gate(g) for g in reversed(gates)]


# ---------------------------------------------------------------------------
# Gate list optimisation helpers
# ---------------------------------------------------------------------------
def _gates_cancel(g1, g2):
    """Return True if *g1* followed by *g2* is identity (they cancel).

    Rules
    -----
    * Must have identical target, num_controls, controls and type.
    * Self-adjoint gates (X, Y, Z, H) always cancel with themselves.
    * Rotation gates (P, Rx, Ry, Rz, R) cancel when their angles sum to
      zero within floating-point tolerance.
    * Measurement gates never cancel.
    """
    if g1["type"] != g2["type"]:
        return False
    if g1["target"] != g2["target"]:
        return False
    if g1["num_controls"] != g2["num_controls"]:
        return False
    if g1["controls"] != g2["controls"]:
        return False

    gt = g1["type"]
    if gt == _M:
        return False
    if gt in _SELF_ADJOINT:
        return True
    if gt in _ROTATION_GATES:
        return abs(g1["angle"] + g2["angle"]) < 1e-12
    return False


def _gates_merge(g1, g2):
    """Return True if *g1* and *g2* can be merged into a single gate.

    Only rotation gates on the same qubit (same target, controls, type) are
    mergeable.  Self-adjoint and measurement gates cannot merge (they would
    cancel, not merge).
    """
    if g1["type"] != g2["type"]:
        return False
    if g1["target"] != g2["target"]:
        return False
    if g1["num_controls"] != g2["num_controls"]:
        return False
    if g1["controls"] != g2["controls"]:
        return False

    gt = g1["type"]
    if gt in _ROTATION_GATES:
        # Cancellation is handled by _gates_cancel; here we only say
        # "yes these can be combined".  The caller uses _merged_gate
        # which may still return None when the sum is zero.
        return True
    return False


def _merged_gate(g1, g2):
    """Return a new gate dict with merged angle, or *None* if result is zero.

    Copies all fields from *g1* and replaces the angle with the sum.
    """
    new_angle = g1["angle"] + g2["angle"]
    if abs(new_angle) < 1e-12:
        return None  # gate disappears
    merged = dict(g1)
    merged["angle"] = new_angle
    return merged


def _optimize_gate_list(gates):
    """Optimise a gate list with multi-pass adjacent cancellation / merge.

    Each pass scans left-to-right, cancelling adjacent inverse pairs and
    merging consecutive rotations on the same qubit.  Passes repeat until
    the list stops shrinking or *max_passes* is reached.
    """
    prev_count = len(gates) + 1
    optimized = list(gates)
    max_passes = 10  # safety limit
    passes = 0
    while len(optimized) < prev_count and passes < max_passes:
        prev_count = len(optimized)
        passes += 1
        result = []
        for gate in optimized:
            if result and _gates_cancel(result[-1], gate):
                result.pop()  # Adjacent inverse cancellation
            elif result and _gates_merge(result[-1], gate):
                merged = _merged_gate(result[-1], gate)
                if merged is None:
                    result.pop()  # Merged to zero
                else:
                    result[-1] = merged
            else:
                result.append(gate)
        optimized = result
    return optimized


# ---------------------------------------------------------------------------
# Merge-and-optimize (selective sequence merging helper)
# ---------------------------------------------------------------------------


def _merge_and_optimize(blocks_with_mappings, optimize=True):
    """Concatenate gate lists from multiple blocks in physical qubit space and optimize.

    Parameters
    ----------
    blocks_with_mappings : list of (CompiledBlock, dict)
        Each tuple is (block, virtual_to_real_mapping) in temporal call order.
    optimize : bool
        Whether to run _optimize_gate_list on the concatenated result.

    Returns
    -------
    tuple of (list[dict], int)
        (optimized_gates, original_gate_count)
    """
    merged_gates = []
    for block, v2r in blocks_with_mappings:
        for g in block.gates:
            pg = dict(g)
            pg["target"] = v2r[g["target"]]
            if g.get("num_controls", 0) > 0 and "controls" in g:
                pg["controls"] = [v2r[c] for c in g["controls"]]
            merged_gates.append(pg)
    original_count = len(merged_gates)
    if optimize and merged_gates:
        try:
            merged_gates = _optimize_gate_list(merged_gates)
        except Exception:
            pass
    return merged_gates, original_count


# ---------------------------------------------------------------------------
# Controlled variant derivation
# ---------------------------------------------------------------------------
def _derive_controlled_gates(gates, control_virtual_idx):
    """Add one control qubit to every gate in the list.

    Each gate's ``num_controls`` is incremented by 1 and
    *control_virtual_idx* is prepended to the ``controls`` list.
    """
    controlled = []
    for g in gates:
        cg = dict(g)
        cg["num_controls"] = g["num_controls"] + 1
        cg["controls"] = [control_virtual_idx] + list(g["controls"])
        controlled.append(cg)
    return controlled


# ---------------------------------------------------------------------------
# Nesting depth limit for compiled function capture
# ---------------------------------------------------------------------------
_capture_depth = 0
_MAX_CAPTURE_DEPTH = 16


# ---------------------------------------------------------------------------
# Global registry for cache invalidation on circuit reset
# ---------------------------------------------------------------------------
_compiled_funcs = []  # List of weakref.ref to CompiledFunc instances


def _clear_all_caches():
    """Clear compilation caches for all live CompiledFunc instances.

    Called automatically when a new circuit is created via ql.circuit().
    Dead weak references are pruned during iteration.
    """
    global _capture_depth
    _capture_depth = 0
    _dag_builder_stack.clear()
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
# CompiledBlock -- stores a captured and virtualised gate sequence
# ---------------------------------------------------------------------------
class CompiledBlock:
    """A captured and virtualised gate sequence from a single function call.

    Attributes
    ----------
    gates : list[dict]
        Gate dicts with virtual qubit indices.
    total_virtual_qubits : int
        Total count of virtual qubits (params + ancillas).
    param_qubit_ranges : list[tuple[int, int]]
        (start_virtual_idx, width) per quantum argument.
    internal_qubit_count : int
        Number of ancilla/temporary virtual qubits.
    return_qubit_range : tuple[int, int] or None
        (start_virtual_idx, width) of the return value, or None.
    return_is_param_index : int or None
        Index of the input parameter if the return value IS one of them.
    """

    __slots__ = (
        "gates",
        "total_virtual_qubits",
        "param_qubit_ranges",
        "internal_qubit_count",
        "return_qubit_range",
        "return_is_param_index",
        "original_gate_count",
        "control_virtual_idx",
        "_first_call_result",
        "_capture_ancilla_qubits",
        "_capture_virtual_to_real",
        "_modifies_inputs",
        "return_type",  # 'qint', 'qarray', or None
        "_return_qarray_element_widths",  # List of element widths for qarray return
    )

    def __init__(
        self,
        gates,
        total_virtual_qubits,
        param_qubit_ranges,
        internal_qubit_count,
        return_qubit_range,
        return_is_param_index=None,
        original_gate_count=None,
    ):
        self.gates = gates
        self.total_virtual_qubits = total_virtual_qubits
        self.param_qubit_ranges = param_qubit_ranges
        self.internal_qubit_count = internal_qubit_count
        self.return_qubit_range = return_qubit_range
        self.return_is_param_index = return_is_param_index
        self.original_gate_count = (
            original_gate_count if original_gate_count is not None else len(gates)
        )
        self.control_virtual_idx = None
        self._first_call_result = None
        self._capture_ancilla_qubits = None
        self._capture_virtual_to_real = None
        self._modifies_inputs = None
        self.return_type = None
        self._return_qarray_element_widths = None


# ---------------------------------------------------------------------------
# Ancilla tracking record
# ---------------------------------------------------------------------------
class AncillaRecord:
    """Record of a single forward call's ancilla allocations."""

    __slots__ = (
        "ancilla_qubits",
        "virtual_to_real",
        "block",
        "return_qint",
        "_auto_uncomputed",
        "_return_only_gates",
    )

    def __init__(self, ancilla_qubits, virtual_to_real, block, return_qint):
        self.ancilla_qubits = ancilla_qubits
        self.virtual_to_real = virtual_to_real
        self.block = block
        self.return_qint = return_qint
        self._auto_uncomputed = False
        self._return_only_gates = None


# ---------------------------------------------------------------------------
# Input side-effect detection
# ---------------------------------------------------------------------------
def _function_modifies_inputs(block):
    """Check if any gate in block targets a parameter (input) qubit.

    Returns True if the compiled function modifies its inputs, which means
    auto-uncompute should be skipped (uncomputing temp ancillas would also
    undo the input modifications).  Result is cached on the block.
    """
    if block._modifies_inputs is not None:
        return block._modifies_inputs
    param_count = sum(w for _, w in block.param_qubit_ranges)
    result = any(g["target"] < param_count for g in block.gates)
    block._modifies_inputs = result
    return result


# ---------------------------------------------------------------------------
# Ancilla partitioning (return vs temp) for auto-uncompute
# ---------------------------------------------------------------------------
def _partition_ancillas(block, virtual_to_real, ancilla_qubits):
    """Split ancilla physical qubits into return qubits and temp qubits.

    Returns (return_physical, temp_physical) where each is a list of
    physical qubit indices.
    """
    if block.return_qubit_range is None or block.return_is_param_index is not None:
        # No ancilla-based return value -- all ancillas are temp
        return [], list(ancilla_qubits)

    ret_start, ret_width = block.return_qubit_range
    return_virtual_set = set(range(ret_start, ret_start + ret_width))

    # Build reverse mapping: real -> virtual
    real_to_virt = {real: virt for virt, real in virtual_to_real.items()}

    return_physical = []
    temp_physical = []
    for real_q in ancilla_qubits:
        virt_q = real_to_virt.get(real_q)
        if virt_q is not None and virt_q in return_virtual_set:
            return_physical.append(real_q)
        else:
            temp_physical.append(real_q)

    return return_physical, temp_physical


# ---------------------------------------------------------------------------
# Virtual qubit mapping helpers
# ---------------------------------------------------------------------------
def _build_virtual_mapping(gates, param_qubit_indices):
    """Map real qubit indices to a virtual namespace.

    Parameter qubits are mapped first (in argument order), then any
    ancilla/temporary qubits encountered in the gate list.

    Parameters
    ----------
    gates : list[dict]
        Raw gate dicts from extract_gate_range (real qubit indices).
    param_qubit_indices : list[list[int]]
        Real qubit indices per quantum argument.

    Returns
    -------
    tuple
        (virtual_gates, real_to_virtual, total_virtual_count)
    """
    real_to_virtual = {}
    virtual_idx = 0

    # Map parameter qubits first (in argument order)
    for qubit_list in param_qubit_indices:
        for real_q in qubit_list:
            if real_q not in real_to_virtual:
                real_to_virtual[real_q] = virtual_idx
                virtual_idx += 1

    # Map remaining qubits (ancillas/temporaries) encountered in gates
    for gate in gates:
        for real_q in [gate["target"]] + gate["controls"]:
            if real_q not in real_to_virtual:
                real_to_virtual[real_q] = virtual_idx
                virtual_idx += 1

    # Remap gates to virtual indices
    virtual_gates = _remap_gates(gates, real_to_virtual)
    return virtual_gates, real_to_virtual, virtual_idx


def _remap_gates(gates, mapping):
    """Remap qubit indices in gate dicts through a mapping."""
    remapped = []
    for g in gates:
        ng = dict(g)
        ng["target"] = mapping[g["target"]]
        ng["controls"] = [mapping[c] for c in g["controls"]]
        remapped.append(ng)
    return remapped


def _get_qint_qubit_indices(q):
    """Extract real qubit indices from a qint, ordered LSB to MSB."""
    return [int(q.qubits[64 - q.width + i]) for i in range(q.width)]


def _get_qarray_qubit_indices(arr):
    """Extract all real qubit indices from a qarray, ordered by element then bit position."""
    indices = []
    for elem in arr:  # Use iteration protocol (qarray supports __iter__)
        indices.extend(_get_qint_qubit_indices(elem))
    return indices


def _get_quantum_arg_qubit_indices(qa):
    """Get qubit indices from a qint or qarray argument."""
    from .qarray import qarray

    if isinstance(qa, qarray):
        return _get_qarray_qubit_indices(qa)
    else:
        return _get_qint_qubit_indices(qa)


def _get_quantum_arg_width(qa):
    """Get total qubit count from a qint or qarray argument."""
    from .qarray import qarray

    if isinstance(qa, qarray):
        return sum(elem.width if hasattr(elem, "width") else 1 for elem in qa)
    else:
        return qa.width


def _input_qubit_key(quantum_args):
    """Build a hashable key from physical qubits of all quantum arguments."""
    key_parts = []
    for qa in quantum_args:
        key_parts.extend(_get_quantum_arg_qubit_indices(qa))
    return tuple(key_parts)


def _build_qubit_set_numpy(quantum_args, extra_values=None):
    """Build qubit set using numpy operations (np.unique/np.concatenate).

    Returns (frozenset, np.ndarray) for dual storage compatibility with DAGNode.
    """
    arrays = []
    for qa in quantum_args:
        indices = _get_quantum_arg_qubit_indices(qa)
        if indices:
            arrays.append(np.array(indices, dtype=np.intp))
    if extra_values is not None:
        vals = list(extra_values)
        if vals:
            arrays.append(np.array(vals, dtype=np.intp))
    if not arrays:
        arr = np.empty(0, dtype=np.intp)
    else:
        arr = np.unique(np.concatenate(arrays))
    return frozenset(arr.tolist()), arr


# ---------------------------------------------------------------------------
# Return value construction for replay
# ---------------------------------------------------------------------------
def _build_return_qint(block, virtual_to_real, start_layer, end_layer):
    """Construct a usable qint from replay-mapped qubits.

    Uses the qint(create_new=False, bit_list=...) pattern from qbool.copy().
    Sets ownership metadata so the result is fully usable in subsequent
    quantum operations.
    """
    ret_start, ret_width = block.return_qubit_range

    # Build qubit array for return qint (right-aligned in 64-element array)
    ret_qubits = np.zeros(64, dtype=np.uint32)
    first_real_qubit = None
    for i in range(ret_width):
        virt_q = ret_start + i
        real_q = virtual_to_real[virt_q]
        ret_qubits[64 - ret_width + i] = real_q
        if first_real_qubit is None:
            first_real_qubit = real_q

    # Create qint with existing qubits (no allocation)
    result = qint(create_new=False, bit_list=ret_qubits, width=ret_width)

    # Transfer ownership metadata
    result.allocated_start = first_real_qubit
    result.allocated_qubits = True
    result._start_layer = start_layer
    result._end_layer = end_layer
    result.operation_type = "COMPILED"

    return result


def _build_return_qarray(block, virtual_to_real, start_layer, end_layer):
    """Construct a qarray return value from replay-mapped qubits.

    Creates new qint elements with qubits mapped from virtual space,
    preserving the original element widths stored in the CompiledBlock.
    """
    from .qarray import qarray

    ret_start, ret_qubit_count = block.return_qubit_range
    element_widths = block._return_qarray_element_widths

    if element_widths is None:
        raise ValueError("CompiledBlock missing element widths for qarray return")

    new_elements = []
    virt_offset = ret_start

    for elem_width in element_widths:
        # Build qubit array for this element (right-aligned in 64-element array)
        ret_qubits = np.zeros(64, dtype=np.uint32)
        first_real_qubit = None

        for i in range(elem_width):
            virt_q = virt_offset + i
            real_q = virtual_to_real[virt_q]
            ret_qubits[64 - elem_width + i] = real_q
            if first_real_qubit is None:
                first_real_qubit = real_q

        virt_offset += elem_width

        # Create qint element with existing qubits (no allocation)
        new_elem = qint(create_new=False, bit_list=ret_qubits, width=elem_width)
        new_elem.allocated_start = first_real_qubit
        new_elem.allocated_qubits = True
        new_elem._start_layer = start_layer
        new_elem._end_layer = end_layer
        new_elem.operation_type = "COMPILED"
        new_elements.append(new_elem)

    # Create qarray view with the new elements
    return qarray._create_view(new_elements, (len(new_elements),))


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
        # Register for cache invalidation on circuit reset
        _compiled_funcs.append(weakref.ref(self))
        # Eagerly create inverse wrapper when inverse=True
        if inverse:
            self._inverse_func = _InverseCompiledFunc(self)

    def __call__(self, *args, **kwargs):
        """Call the compiled function (capture or replay)."""
        # Classify args into quantum and classical
        quantum_args, classical_args, widths = self._classify_args(args, kwargs)

        # Detect controlled context
        is_controlled = _get_controlled()
        control_count = 1 if is_controlled else 0

        # Build cache key (includes control_count, qubit_saving, and mode flags)
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._key_func:
            cache_key = (self._key_func(*args, **kwargs), control_count, qubit_saving) + mode_flags
        else:
            cache_key = (
                tuple(classical_args),
                tuple(widths),
                control_count,
                qubit_saving,
            ) + mode_flags

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
                if self._call_graph is not None and self._opt == 2:
                    self._apply_merge()

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
                    )
            # Auto-uncompute (same as normal path)
            if qubit_saving:
                cached_block = self._cache.get(cache_key)
                if cached_block is not None and cached_block.internal_qubit_count > 0:
                    if not _function_modifies_inputs(cached_block):
                        input_key = _input_qubit_key(quantum_args)
                        record = self._forward_calls.get(input_key)
                        if record is not None:
                            self._auto_uncompute(record, quantum_args, is_controlled)
            return result

        is_hit = cache_key in self._cache

        if is_hit:
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            _track_fwd = self._inverse_func is not None
            block = self._cache[cache_key]
            result = self._replay(block, quantum_args, track_forward=_track_fwd)
            # Manually credit the gate count when simulate=False (no gates
            # injected) or opt=1 (inject_remapped_gates/add_gate does not
            # increment gate_count) so get_gate_count() reflects the
            # logical cost of this replay.
            if (not option('simulate') or self._opt == 1) and block is not None:
                _replay_count = (
                    block.original_gate_count
                    if block.original_gate_count
                    else len(block.gates)
                )
                if _replay_count:
                    add_gate_count(_replay_count)
            # Record DAG node for replay path (no nesting -- body not
            # re-executed).  Skip for opt=1: the DAG was fully built
            # during capture and should not grow on subsequent calls.
            if _building_dag and self._opt != 1:
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

        # Auto-uncompute temp ancillas when qubit_saving mode is active
        if qubit_saving:
            cached_block = self._cache.get(cache_key)
            if cached_block is not None and cached_block.internal_qubit_count > 0:
                if not _function_modifies_inputs(cached_block):
                    input_key = _input_qubit_key(quantum_args)
                    record = self._forward_calls.get(input_key)
                    if record is not None:
                        self._auto_uncompute(record, quantum_args, is_controlled)

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
        from .qarray import qarray

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
        global _capture_depth
        if _capture_depth >= _MAX_CAPTURE_DEPTH:
            raise RecursionError(
                f"Compiled function nesting depth exceeded {_MAX_CAPTURE_DEPTH}. "
                "Possible circular compiled function calls."
            )
        _capture_depth += 1
        try:
            return self._capture_inner(args, kwargs, quantum_args)
        finally:
            _capture_depth -= 1

    def _capture_inner(self, args, kwargs, quantum_args):
        """Inner capture logic (separated for nesting depth tracking)."""
        # Record start layer
        start_layer = get_current_layer()

        # Check if circuit is in tracking-only mode (simulate=False).
        # Gate count is used to compute per-block cost when gates aren't stored.
        _use_tracking = not option('simulate')
        _gate_count_before = get_gate_count() if _use_tracking else 0

        # Collect parameter qubit indices BEFORE execution
        param_qubit_indices = []
        for qa in quantum_args:
            param_qubit_indices.append(_get_quantum_arg_qubit_indices(qa))

        # Execute function normally (gates flow to circuit as usual,
        # or in tracking-only mode when ql.option('simulate') is False).
        # Operations inside the body are recorded as direct DAG nodes
        # via record_operation() — no wrapper/placeholder node.
        result = self._func(*args, **kwargs)

        # Record end layer
        end_layer = get_current_layer()

        # In tracking-only mode, compute gate count from circ->gate_count
        # difference (gates were counted but not stored in the circuit).
        _tracking_gate_count = 0
        if _use_tracking:
            _tracking_gate_count = get_gate_count() - _gate_count_before

        # Extract captured gates (empty in tracking-only mode (simulate=False)
        # since gates are counted but not stored)
        raw_gates = extract_gate_range(start_layer, end_layer)

        # Build virtual mapping
        virtual_gates, real_to_virtual, total_virtual = _build_virtual_mapping(
            raw_gates, param_qubit_indices
        )

        # Determine return value qubit range (if result is qint or qarray)
        from .qarray import qarray

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

        # Build param ranges in virtual space
        param_ranges = []
        vidx = 0
        for qa in quantum_args:
            qa_width = _get_quantum_arg_width(qa)
            param_ranges.append((vidx, qa_width))
            vidx += qa_width
        internal_count = total_virtual - vidx

        # Optimise the virtual gate list (cancel adjacent inverses, merge
        # consecutive rotations) before caching so every replay benefits.
        original_count = (
            _tracking_gate_count if _use_tracking
            else len(virtual_gates)
        )
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

        First call of a compiled function inside a ``with`` block executes
        the uncontrolled body; subsequent calls correctly replay controlled
        gates.  This is an accepted trade-off -- the first-call circuit
        contains uncontrolled gates because gates already emitted into the
        circuit cannot be retroactively controlled.
        """
        # Always capture in uncontrolled mode
        if is_controlled:
            saved_stack = list(_get_control_stack())
            _set_control_stack([])
            try:
                block = self._capture(args, kwargs, quantum_args)
            finally:
                _set_control_stack(saved_stack)
        else:
            block = self._capture(args, kwargs, quantum_args)

        # Cache uncontrolled variant
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._key_func:
            unctrl_key = (self._key_func(*args, **kwargs), 0, qubit_saving) + mode_flags
        else:
            unctrl_key = (tuple(classical_args), tuple(widths), 0, qubit_saving) + mode_flags
        self._cache[unctrl_key] = block

        # Derive and cache controlled variant
        try:
            controlled_block = self._derive_controlled_block(block)
        except Exception:
            # Fallback: re-capture in controlled mode (not expected with
            # current gate set, but guards against future gate types)
            controlled_block = self._capture(args, kwargs, quantum_args)
        if self._key_func:
            ctrl_key = (self._key_func(*args, **kwargs), 1, qubit_saving) + mode_flags
        else:
            ctrl_key = (tuple(classical_args), tuple(widths), 1, qubit_saving) + mode_flags
        self._cache[ctrl_key] = controlled_block

        # Evict oldest if over capacity (we added 2 entries)
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

        The control qubit receives virtual index
        ``uncontrolled_block.total_virtual_qubits`` (one beyond all
        uncontrolled virtual qubits).
        """
        control_virt_idx = uncontrolled_block.total_virtual_qubits

        controlled_gates = _derive_controlled_gates(
            uncontrolled_block.gates,
            control_virt_idx,
        )

        controlled_block = CompiledBlock(
            gates=controlled_gates,
            total_virtual_qubits=uncontrolled_block.total_virtual_qubits + 1,
            param_qubit_ranges=list(uncontrolled_block.param_qubit_ranges),
            internal_qubit_count=uncontrolled_block.internal_qubit_count,
            return_qubit_range=uncontrolled_block.return_qubit_range,
            return_is_param_index=uncontrolled_block.return_is_param_index,
            original_gate_count=uncontrolled_block.original_gate_count,
        )
        controlled_block.control_virtual_idx = control_virt_idx
        controlled_block.return_type = uncontrolled_block.return_type
        controlled_block._return_qarray_element_widths = (
            uncontrolled_block._return_qarray_element_widths
        )
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
                    return self._replay(self._cache[cache_key], quantum_args)
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
                return self._replay(self._cache[cache_key], quantum_args)
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
            return self._replay(self._cache[cache_key], quantum_args)

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

    def _replay(self, block, quantum_args, track_forward=True):
        """Replay cached gates with qubit remapping."""
        # Build virtual-to-real mapping from caller's qints/qarrays
        virtual_to_real = {}
        vidx = 0
        for qa in quantum_args:
            indices = _get_quantum_arg_qubit_indices(qa)
            for real_q in indices:
                virtual_to_real[vidx] = real_q
                vidx += 1

        # Validate total qubit count matches cached block's param ranges
        expected_param_qubits = sum(w for _, w in block.param_qubit_ranges)
        if vidx != expected_param_qubits:
            raise ValueError(
                f"qarray element widths don't match captured widths: "
                f"expected {expected_param_qubits} qubits, got {vidx}"
            )

        # Allocate fresh ancillas for internal qubits, with control
        # qubit remapping for controlled variants
        ancilla_qubits = []
        for v in range(vidx, block.total_virtual_qubits):
            if block.control_virtual_idx is not None and v == block.control_virtual_idx:
                # Map control placeholder to actual control qubit
                control_bool = _get_control_bool()
                virtual_to_real[v] = int(control_bool.qubits[63])
            else:
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

        # Inject remapped gates (skip when simulate=False)
        if option('simulate'):
            inject_remapped_gates(block.gates, virtual_to_real)

        end_layer = get_current_layer()
        # Restore layer_floor
        _set_layer_floor(saved_floor)

        # Build return value
        result = None
        if block.return_qubit_range is not None:
            if block.return_is_param_index is not None:
                # Return value IS one of the input params -- return caller's qint/qarray
                result = quantum_args[block.return_is_param_index]
            elif block.return_type == "qarray":
                result = _build_return_qarray(block, virtual_to_real, start_layer, end_layer)
            else:
                result = _build_return_qint(block, virtual_to_real, start_layer, end_layer)

        # Record forward call for inverse support (only when ancillas were allocated)
        if track_forward and ancilla_qubits:
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
    # Auto-uncompute (qubit-saving mode)
    # ------------------------------------------------------------------
    def _auto_uncompute(self, record, quantum_args, is_controlled):
        """Uncompute temp ancillas, preserving return qubits.

        Called after forward call when qubit_saving mode is active.
        Injects adjoint gates for temp-only ancillas, deallocates them,
        and updates the AncillaRecord so f.inverse() operates on return
        qubits only.
        """
        from ._core import _deallocate_qubits

        block = record.block
        return_physical, temp_physical = _partition_ancillas(
            block, record.virtual_to_real, record.ancilla_qubits
        )

        if not temp_physical:
            return  # Nothing to uncompute

        # Build reverse mapping: real -> virtual
        real_to_virt = {real: virt for virt, real in record.virtual_to_real.items()}

        # Identify temp virtual indices
        temp_virtual_set = set()
        for real_q in temp_physical:
            virt_q = real_to_virt.get(real_q)
            if virt_q is not None:
                temp_virtual_set.add(virt_q)

        # Extract gates that target temp ancillas only
        temp_gates = [g for g in block.gates if g["target"] in temp_virtual_set]

        if not temp_gates:
            # No gates on temp qubits -- just deallocate
            for qubit_idx in temp_physical:
                _deallocate_qubits(qubit_idx, 1)
            if return_physical:
                record.ancilla_qubits = return_physical
                record._auto_uncomputed = True
                record._return_only_gates = []
            else:
                # No return qubits either -- remove the forward call record
                input_key = _input_qubit_key(quantum_args)
                self._forward_calls.pop(input_key, None)
            return

        # Generate adjoint of temp-only gates
        temp_adjoint = _inverse_gate_list(temp_gates)

        # Handle controlled context
        vtr = record.virtual_to_real
        if is_controlled:
            control_bool = _get_control_bool()
            ctrl_qubit = int(control_bool.qubits[63])
            ctrl_virt_idx = block.total_virtual_qubits
            temp_adjoint = _derive_controlled_gates(temp_adjoint, ctrl_virt_idx)
            vtr = dict(vtr)
            vtr[ctrl_virt_idx] = ctrl_qubit

        # Inject adjoint gates
        saved_floor = _get_layer_floor()
        _set_layer_floor(get_current_layer())
        inject_remapped_gates(temp_adjoint, vtr)
        _set_layer_floor(saved_floor)

        # Deallocate temp qubits
        for qubit_idx in temp_physical:
            _deallocate_qubits(qubit_idx, 1)

        # Update AncillaRecord
        if return_physical:
            # Compute return-only gates for future f.inverse() use
            ret_start, ret_width = block.return_qubit_range
            return_virtual_set = set(range(ret_start, ret_start + ret_width))
            return_only_gates = [g for g in block.gates if g["target"] in return_virtual_set]
            record.ancilla_qubits = return_physical
            record._auto_uncomputed = True
            record._return_only_gates = return_only_gates
        else:
            # No return qubits -- remove forward call record entirely
            input_key = _input_qubit_key(quantum_args)
            self._forward_calls.pop(input_key, None)

    # ------------------------------------------------------------------
    # Selective sequence merging (opt=2)
    # ------------------------------------------------------------------
    def _apply_merge(self):
        """Merge overlapping sequences after first call (opt=2).

        Gets merge groups from the call graph, collects CompiledBlocks and
        their virtual-to-real mappings, runs _merge_and_optimize, and stores
        merged CompiledBlocks keyed by frozenset of node indices.
        """
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
# _InverseCompiledFunc -- lightweight wrapper for adjoint replay
# ---------------------------------------------------------------------------
class _InverseCompiledFunc:
    """Wrapper that replays the adjoint (inverse) gate sequence of a ``CompiledFunc``.

    Does NOT inherit from ``CompiledFunc``.  Reuses the original's
    ``_classify_args``, ``_replay``, and cache, but maintains its own
    cache of inverted ``CompiledBlock`` objects.
    """

    def __init__(self, original):
        self._original = original
        self._opt = original._opt
        self._inv_cache = {}
        functools.update_wrapper(self, original._func)

    def __call__(self, *args, **kwargs):
        """Call the inverse compiled function."""
        quantum_args, classical_args, widths = self._original._classify_args(args, kwargs)

        # Detect controlled context
        is_controlled = _get_controlled()
        control_count = 1 if is_controlled else 0

        # Build cache key (same logic as CompiledFunc.__call__, includes mode flags)
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._original._key_func:
            cache_key = (
                self._original._key_func(*args, **kwargs),
                control_count,
                qubit_saving,
            ) + mode_flags
        else:
            cache_key = (
                tuple(classical_args),
                tuple(widths),
                control_count,
                qubit_saving,
            ) + mode_flags

        # Check inverse cache
        if cache_key not in self._inv_cache:
            # Ensure original has the block cached
            if cache_key not in self._original._cache:
                # Trigger capture by calling the original (side-effect: may
                # record a forward call -- clean it up since adjoint is stateless)
                self._original(*args, **kwargs)
                # Remove any forward call record created as side-effect
                input_key = _input_qubit_key(quantum_args)
                self._original._forward_calls.pop(input_key, None)

            block = self._original._cache[cache_key]
            # Invert the gates
            inverted_gates = _inverse_gate_list(block.gates)
            inverted_block = CompiledBlock(
                gates=inverted_gates,
                total_virtual_qubits=block.total_virtual_qubits,
                param_qubit_ranges=list(block.param_qubit_ranges),
                internal_qubit_count=block.internal_qubit_count,
                return_qubit_range=block.return_qubit_range,
                return_is_param_index=block.return_is_param_index,
                original_gate_count=block.original_gate_count,
            )
            inverted_block.control_virtual_idx = block.control_virtual_idx
            inverted_block.return_type = block.return_type
            inverted_block._return_qarray_element_widths = block._return_qarray_element_widths
            self._inv_cache[cache_key] = inverted_block

        return self._original._replay(self._inv_cache[cache_key], quantum_args, track_forward=False)

    def inverse(self):
        """Return the original ``CompiledFunc`` (round-trip)."""
        return self._original

    def _reset_for_circuit(self):
        """Reset for circuit change (same as clear_cache for inverse)."""
        self._inv_cache.clear()

    def clear_cache(self):
        """Clear the inverse cache."""
        self._inv_cache.clear()

    def __repr__(self):
        return f"<InverseCompiledFunc {self._original._func.__name__}>"


# ---------------------------------------------------------------------------
# _AncillaInverseProxy -- uncomputes a prior forward call's ancillas
# ---------------------------------------------------------------------------
class _AncillaInverseProxy:
    """Callable proxy that uncomputes a prior forward call's ancillas.

    Returned by CompiledFunc.inverse (as a property). When called as
    f.inverse(x), looks up the forward call record by input qubit identity,
    replays adjoint gates on the original physical ancilla qubits, deallocates
    them, and invalidates the return qint.
    """

    def __init__(self, compiled_func):
        self._cf = compiled_func

    def __call__(self, *args, **kwargs):
        from ._core import _deallocate_qubits

        quantum_args, _, _ = self._cf._classify_args(args, kwargs)
        input_key = _input_qubit_key(quantum_args)

        record = self._cf._forward_calls.get(input_key)
        if record is None:
            raise ValueError(
                f"No prior forward call of '{self._cf._func.__name__}' found "
                f"for these input qubits. Call the function forward first."
            )

        # Generate adjoint gates -- use reduced gate set if auto-uncomputed
        if record._auto_uncomputed and record._return_only_gates is not None:
            adjoint_gates = _inverse_gate_list(record._return_only_gates)
        else:
            adjoint_gates = _inverse_gate_list(record.block.gates)

        # Handle controlled context
        is_controlled = _get_controlled()
        if is_controlled:
            control_bool = _get_control_bool()
            ctrl_qubit = int(control_bool.qubits[63])
            ctrl_virt_idx = record.block.total_virtual_qubits
            adjoint_gates = _derive_controlled_gates(adjoint_gates, ctrl_virt_idx)
            vtr = dict(record.virtual_to_real)
            vtr[ctrl_virt_idx] = ctrl_qubit
        else:
            vtr = record.virtual_to_real

        # Inject adjoint gates with original qubit mapping
        saved_floor = _get_layer_floor()
        _set_layer_floor(get_current_layer())
        inject_remapped_gates(adjoint_gates, vtr)
        _set_layer_floor(saved_floor)

        # Deallocate ancilla qubits (one at a time, may be non-contiguous)
        for qubit_idx in record.ancilla_qubits:
            _deallocate_qubits(qubit_idx, 1)

        # Invalidate return qint
        if record.return_qint is not None:
            record.return_qint._is_uncomputed = True
            record.return_qint.allocated_qubits = False

        # Remove forward call record
        del self._cf._forward_calls[input_key]

        return None

    def __repr__(self):
        return f"<AncillaInverseProxy {self._cf._func.__name__}>"


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
