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
    _get_controlled,
    _get_layer_floor,
    _get_list_of_controls,
    _get_qubit_saving_mode,
    _register_cache_clear_hook,
    _set_control_bool,
    _set_controlled,
    _set_layer_floor,
    _set_list_of_controls,
    extract_gate_range,
    get_current_layer,
    inject_remapped_gates,
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
    alive = []
    for ref in _compiled_funcs:
        obj = ref()
        if obj is not None:
            obj.clear_cache()
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
        self, func, max_cache=128, key=None, verify=False, optimize=True, inverse=False, debug=False
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
        self._forward_calls = {}
        self._inverse_proxy = None
        self._adjoint_func = None
        self._stats = None
        self._total_hits = 0
        self._total_misses = 0
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

        # Build cache key (always includes control_count and qubit_saving mode)
        qubit_saving = _get_qubit_saving_mode()
        if self._key_func:
            cache_key = (self._key_func(*args, **kwargs), control_count, qubit_saving)
        else:
            cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving)

        is_hit = cache_key in self._cache

        if is_hit:
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            result = self._replay(self._cache[cache_key], quantum_args)
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

        # Collect parameter qubit indices BEFORE execution
        param_qubit_indices = []
        for qa in quantum_args:
            param_qubit_indices.append(_get_quantum_arg_qubit_indices(qa))

        # Execute function normally (gates flow to circuit as usual)
        try:
            result = self._func(*args, **kwargs)
        except Exception:
            # Do NOT cache partial result -- let exception propagate
            raise

        # Record end layer
        end_layer = get_current_layer()

        # Extract captured gates
        raw_gates = extract_gate_range(start_layer, end_layer)

        # Build virtual mapping
        virtual_gates, real_to_virtual, total_virtual = _build_virtual_mapping(
            raw_gates, param_qubit_indices
        )

        # Determine return value qubit range (if result is qint)
        return_range = None
        return_is_param_index = None

        if isinstance(result, qint):
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
            param_ranges.append((vidx, qa.width))
            vidx += qa.width
        internal_count = total_virtual - vidx

        # Optimise the virtual gate list (cancel adjacent inverses, merge
        # consecutive rotations) before caching so every replay benefits.
        original_count = len(virtual_gates)
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
            saved_controlled = _get_controlled()
            saved_control_bool = _get_control_bool()
            saved_list_of_controls = list(_get_list_of_controls())
            _set_controlled(False)
            _set_control_bool(None)
            _set_list_of_controls([])
            try:
                block = self._capture(args, kwargs, quantum_args)
            finally:
                _set_controlled(saved_controlled)
                _set_control_bool(saved_control_bool)
                _set_list_of_controls(saved_list_of_controls)
        else:
            block = self._capture(args, kwargs, quantum_args)

        # Cache uncontrolled variant
        qubit_saving = _get_qubit_saving_mode()
        if self._key_func:
            unctrl_key = (self._key_func(*args, **kwargs), 0, qubit_saving)
        else:
            unctrl_key = (tuple(classical_args), tuple(widths), 0, qubit_saving)
        self._cache[unctrl_key] = block

        # Derive and cache controlled variant
        try:
            controlled_block = self._derive_controlled_block(block)
        except Exception:
            # Fallback: re-capture in controlled mode (not expected with
            # current gate set, but guards against future gate types)
            controlled_block = self._capture(args, kwargs, quantum_args)
        if self._key_func:
            ctrl_key = (self._key_func(*args, **kwargs), 1, qubit_saving)
        else:
            ctrl_key = (tuple(classical_args), tuple(widths), 1, qubit_saving)
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
        return controlled_block

    def _replay(self, block, quantum_args, track_forward=True):
        """Replay cached gates with qubit remapping."""
        # Build virtual-to-real mapping from caller's qints
        virtual_to_real = {}
        vidx = 0
        for qa in quantum_args:
            indices = _get_qint_qubit_indices(qa)
            for real_q in indices:
                virtual_to_real[vidx] = real_q
                vidx += 1

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
        saved_floor = _get_layer_floor()
        start_layer = get_current_layer()
        _set_layer_floor(start_layer)

        # Inject remapped gates
        inject_remapped_gates(block.gates, virtual_to_real)

        end_layer = get_current_layer()
        # Restore layer_floor
        _set_layer_floor(saved_floor)

        # Build return value
        result = None
        if block.return_qubit_range is not None:
            if block.return_is_param_index is not None:
                # Return value IS one of the input params -- return caller's qint
                result = quantum_args[block.return_is_param_index]
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

    def clear_cache(self):
        """Clear this function's compilation cache."""
        self._cache.clear()
        self._forward_calls.clear()
        if self._inverse_func is not None:
            self._inverse_func.clear_cache()
        if self._adjoint_func is not None:
            self._adjoint_func.clear_cache()

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
        self._inv_cache = {}
        functools.update_wrapper(self, original._func)

    def __call__(self, *args, **kwargs):
        """Call the inverse compiled function."""
        quantum_args, classical_args, widths = self._original._classify_args(args, kwargs)

        # Detect controlled context
        is_controlled = _get_controlled()
        control_count = 1 if is_controlled else 0

        # Build cache key (same logic as CompiledFunc.__call__)
        qubit_saving = _get_qubit_saving_mode()
        if self._original._key_func:
            cache_key = (self._original._key_func(*args, **kwargs), control_count, qubit_saving)
        else:
            cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving)

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
            self._inv_cache[cache_key] = inverted_block

        return self._original._replay(self._inv_cache[cache_key], quantum_args, track_forward=False)

    def inverse(self):
        """Return the original ``CompiledFunc`` (round-trip)."""
        return self._original

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
    func=None, *, max_cache=128, key=None, verify=False, optimize=True, inverse=False, debug=False
):
    """Decorator that compiles a quantum function for cached gate replay.

    Supports three forms:
      @ql.compile
      @ql.compile()
      @ql.compile(max_cache=N, key=..., verify=..., optimize=...)

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

    Returns
    -------
    CompiledFunc or decorator
        CompiledFunc wrapper or decorator function.

    Examples
    --------
    >>> @ql.compile
    ... def add_one(x):
    ...     x += 1
    ...     return x

    >>> @ql.compile(max_cache=16)
    ... def multiply(x, y):
    ...     return x * y

    >>> @ql.compile(optimize=False)
    ... def raw_capture(x):
    ...     x += 1
    ...     return x
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
        )
    # Called as @ql.compile() or @ql.compile(max_cache=N)
    return decorator
