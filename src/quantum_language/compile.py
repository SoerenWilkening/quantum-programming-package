"""Compile decorator for quantum function capture and replay.

Provides @ql.compile decorator that captures gate sequences on first call
and replays them with qubit remapping on subsequent calls.  When
``optimize=True`` (the default), adjacent inverse gates are cancelled and
consecutive rotations on the same qubit are merged before the sequence is
cached, so every replay benefits from the reduced gate count.

Usage
-----
>>> import quantum_language as ql
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
import contextlib
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
    _run_instruction_py,
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
    _resolve_gate_count,
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
def _derive_controlled_gates(gates):
    """Add virtual index 0 as a control qubit to every gate.

    Each gate's ``num_controls`` is incremented by 1 and index 0
    (the reserved control slot) is prepended to the ``controls`` list.
    """
    controlled = []
    for g in gates:
        cg = dict(g)
        cg["num_controls"] = g["num_controls"] + 1
        cg["controls"] = [0] + list(g["controls"])
        controlled.append(cg)
    return controlled


def _strip_control_qubit(gates, control_qubit):
    """Remove a physical control qubit from each gate's controls list.

    Used to normalise controlled gates back to uncontrolled form for
    the gate-level cache.  Each gate's ``num_controls`` is decremented
    by 1 and *control_qubit* is removed from ``controls``.  Gates that
    do not reference *control_qubit* in their controls are left unchanged.

    Parameters
    ----------
    gates : list[dict]
        Raw gate dicts from ``extract_gate_range`` (physical qubit indices).
    control_qubit : int
        Physical qubit index of the control to strip.

    Returns
    -------
    list[dict]
        Gate dicts with the control qubit removed.
    """
    stripped = []
    for g in gates:
        if control_qubit in g.get("controls", []):
            sg = dict(g)
            new_controls = [c for c in g["controls"] if c != control_qubit]
            sg["controls"] = new_controls
            sg["num_controls"] = len(new_controls)
            stripped.append(sg)
        else:
            stripped.append(g)
    return stripped


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

    Also enables simulate mode so gates are stored in the circuit.
    The C default is simulate=0 (tracking-only), but full simulation
    is required for QASM export, compiled function replay, and any
    operation that needs gate data in the circuit.

    Note: this means ql.circuit() forces simulate=True.  Users who
    want tracking-only mode should set ql.option('simulate', False)
    AFTER calling ql.circuit(), or avoid calling ql.circuit() entirely
    (the circuit initializes automatically).
    """
    global _capture_depth
    _capture_depth = 0
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
# InstructionRecord & compile-mode global state (from _compile_state)
# ---------------------------------------------------------------------------
from ._compile_state import (  # noqa: E402 – after qint import is fine
    CallRecord,  # noqa: F401 – re-exported for tests
    InstructionRecord,  # noqa: F401 – re-exported for tests
    _get_active_compile_block,
    _record_call,  # noqa: F401 – re-exported for tests
    _set_active_compile_block,
)

# ---------------------------------------------------------------------------
# IR execution — replay InstructionRecord entries via run_instruction
# ---------------------------------------------------------------------------


def _execute_ir(block, qubit_mapping=None):
    """Execute recorded IR entries to produce gates in the circuit.

    Iterates ``block._instruction_ir`` and calls ``run_instruction`` for
    each entry.  Checks the control stack at runtime: if inside a ``with``
    block (controlled context), uses ``entry.controlled_seq`` and appends
    the control qubit to the register tuple.  Otherwise uses
    ``entry.uncontrolled_seq``.

    An optional *qubit_mapping* dict remaps capture-time physical qubit
    indices to replay-time physical indices (for replaying on different
    qubits).

    Parameters
    ----------
    block : CompiledBlock
        Block whose ``_instruction_ir`` list contains the entries to execute.
    qubit_mapping : dict or None
        If provided, maps capture-time physical qubit index (int) to
        replay-time physical qubit index (int).  When *None*, registers
        are used as-is (identity mapping — same physical qubits as capture).
    """
    is_controlled = _get_controlled()
    control_qubit = None
    if is_controlled:
        control_bool = _get_control_bool()
        control_qubit = int(control_bool.qubits[63])

    for entry in block._instruction_ir:
        if is_controlled and entry.controlled_seq != 0:
            seq_ptr = entry.controlled_seq
        else:
            seq_ptr = entry.uncontrolled_seq
        if seq_ptr == 0:
            continue
        if qubit_mapping is not None:
            regs = tuple(qubit_mapping[r] for r in entry.registers)
        else:
            regs = entry.registers
        if is_controlled and control_qubit is not None:
            regs = regs + (control_qubit,)
        _run_instruction_py(seq_ptr, regs, int(entry.invert))


def _build_dag_from_ir(block, func_name, is_controlled=False, qubit_mapping=None):
    """Build DAG nodes from a block's instruction IR.

    Each ``InstructionRecord`` in ``block._instruction_ir`` becomes a DAG
    node in the current DAG context.  This allows opt=1 (DAG-only) mode
    to populate the DAG from IR entries even when ``simulate=False``
    (no gates are emitted to the circuit).

    Parameters
    ----------
    block : CompiledBlock
        Block whose ``_instruction_ir`` list provides the entries.
    func_name : str
        Name of the compiled function (used as prefix for node names).
    is_controlled : bool
        Whether the call is inside a controlled context.  Recorded in
        each DAGNode's ``controlled`` attribute.
    qubit_mapping : dict or None
        If provided, maps capture-time physical qubit indices to
        replay-time physical indices.  When *None*, registers are
        used as-is.

    Returns
    -------
    int
        Number of DAG nodes added.
    """
    dag = current_dag_context()
    if dag is None:
        return 0

    count = 0
    for entry in block._instruction_ir:
        if qubit_mapping is not None:
            regs = tuple(qubit_mapping.get(r, r) for r in entry.registers)
        else:
            regs = entry.registers
        qubit_set = frozenset(regs)

        # Store both sequence pointers from InstructionRecord on the node.
        # sequence_ptr is set to the variant matching the current context
        # for backward compatibility.
        if is_controlled and entry.controlled_seq != 0:
            seq_ptr = entry.controlled_seq
        else:
            seq_ptr = entry.uncontrolled_seq

        # Resolve gate counts from sequence pointers.
        uc_gc = _resolve_gate_count(entry.uncontrolled_seq)
        ct_gc = _resolve_gate_count(entry.controlled_seq)

        dag.add_node(
            entry.name,
            qubit_set,
            0,  # gate_count -- not available from IR alone
            (),  # cache_key
            sequence_ptr=seq_ptr,
            uncontrolled_seq=entry.uncontrolled_seq,
            controlled_seq=entry.controlled_seq,
            uncontrolled_gate_count=uc_gc,
            controlled_gate_count=ct_gc,
            qubit_mapping=regs,
            operation_type=entry.name,
            invert=entry.invert,
            controlled=is_controlled,
        )
        count += 1
    return count


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
        (start_virtual_idx, end_virtual_idx) per quantum argument.
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
        "return_type",  # 'qint', 'qarray', or None
        "_return_qarray_element_widths",  # List of element widths for qarray return
        "controlled_block",  # Derived controlled CompiledBlock (Phase 5)
        "_captured_controlled",  # Whether capture was inside control context
        "_instruction_ir",  # list[InstructionRecord] – compile-mode IR
        "_call_records",  # list[CallRecord] – nested compiled function calls
        "_dag_built",  # bool – DAG nodes already built from IR (no duplication on replay)
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
        self.return_type = None
        self._return_qarray_element_widths = None
        self.controlled_block = None
        self._captured_controlled = False
        self._instruction_ir = []
        self._call_records = []
        self._dag_built = False


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
    )

    def __init__(self, ancilla_qubits, virtual_to_real, block, return_qint):
        self.ancilla_qubits = ancilla_qubits
        self.virtual_to_real = virtual_to_real
        self.block = block
        self.return_qint = return_qint


# ---------------------------------------------------------------------------
# Virtual qubit mapping helpers
# ---------------------------------------------------------------------------
def _build_virtual_mapping(gates, param_qubit_indices):
    """Map real qubit indices to a virtual namespace.

    Virtual index 0 is reserved for the control qubit (used by
    ``_derive_controlled_block``).  Parameter qubits are mapped starting
    at index 1, then any ancilla/temporary qubits encountered in the
    gate list.

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
    virtual_idx = 1  # Reserve index 0 for control qubit

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
def _build_return_qint(block, virtual_to_real):
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
    result.operation_type = "COMPILED"

    return result


def _build_return_qarray(block, virtual_to_real):
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
        _tracking_gate_count = 0
        if _use_tracking:
            _tracking_gate_count = get_gate_count() - _gate_count_before

        # Extract captured gates (empty in tracking-only mode (simulate=False)
        # since gates are counted but not stored)
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

        # Transfer IR entries from the compile-mode block to the cached block
        block._instruction_ir = ir_block._instruction_ir

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

        # Allocate fresh ancillas for internal qubits (skip index 0
        # which is the control slot, already mapped or unused)
        ancilla_qubits = []
        for v in range(vidx, block.total_virtual_qubits):
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

        # Execute replay: prefer IR path (handles controlled context via
        # controlled_seq), fall back to gate-level injection.
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

        # Build cache key (no control_count -- matches CompiledFunc.__call__)
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._original._key_func:
            cache_key = (
                self._original._key_func(*args, **kwargs),
                qubit_saving,
            ) + mode_flags
        else:
            cache_key = (
                tuple(classical_args),
                tuple(widths),
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
            # Invert uncontrolled gates
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
            inverted_block.control_virtual_idx = None
            inverted_block.return_type = block.return_type
            inverted_block._return_qarray_element_widths = block._return_qarray_element_widths
            # Derive controlled variant for the inverted block
            try:
                inverted_controlled = self._original._derive_controlled_block(inverted_block)
            except Exception:
                inverted_controlled = None
            inverted_block.controlled_block = inverted_controlled
            self._inv_cache[cache_key] = inverted_block

        inv_block = self._inv_cache[cache_key]
        # _replay selects controlled/uncontrolled variant at runtime
        return self._original._replay(
            inv_block, quantum_args, track_forward=False, kind="compiled_fn_inv"
        )

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

        # Generate adjoint gates
        adjoint_gates = _inverse_gate_list(record.block.gates)

        # Handle controlled context
        is_controlled = _get_controlled()
        if is_controlled:
            control_bool = _get_control_bool()
            ctrl_qubit = int(control_bool.qubits[63])
            adjoint_gates = _derive_controlled_gates(adjoint_gates)
            vtr = dict(record.virtual_to_real)
            vtr[0] = ctrl_qubit  # control at reserved index 0
        else:
            vtr = record.virtual_to_real

        # Inject adjoint gates with original qubit mapping
        saved_floor = _get_layer_floor()
        _set_layer_floor(get_current_layer())
        inject_remapped_gates(adjoint_gates, vtr)
        _set_layer_floor(saved_floor)

        # Record compiled-function inverse history entry for cancellation
        if quantum_args:
            _qm = tuple(q for qa in quantum_args for q in _get_quantum_arg_qubit_indices(qa))
            target = quantum_args[0]
            if hasattr(target, "history"):
                target.history.append(
                    id(self._cf),
                    _qm,
                    len(record.ancilla_qubits),
                    kind="compiled_fn_inv",
                )

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
