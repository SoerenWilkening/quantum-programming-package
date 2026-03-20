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

import numpy as np

from .._core import (
    _get_control_bool,
    _get_controlled,
    _run_instruction_py,
    add_gate_count,
    option,
)
from ..call_graph import (
    _resolve_gate_count,
    current_dag_context,
)
from ..qint import qint
from . import _block as _block  # noqa: F401 – re-exported
from ._block import _H as _H  # noqa: F401 – re-exported
from ._block import _M, _ROTATION_GATES, _SELF_ADJOINT
from ._block import _MAX_CAPTURE_DEPTH as _MAX_CAPTURE_DEPTH  # noqa: F401
from ._block import _P as _P  # noqa: F401 – re-exported
from ._block import _R as _R  # noqa: F401 – re-exported
from ._block import _X as _X  # noqa: F401 – re-exported
from ._block import _Y as _Y  # noqa: F401 – re-exported
from ._block import _Z as _Z  # noqa: F401 – re-exported
from ._block import AncillaRecord as AncillaRecord  # noqa: F401
from ._block import CompiledBlock as CompiledBlock  # noqa: F401
from ._block import _Rx as _Rx  # noqa: F401 – re-exported
from ._block import _Ry as _Ry  # noqa: F401 – re-exported
from ._block import _Rz as _Rz  # noqa: F401 – re-exported


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
# Parametric and inverse helpers (delegated to _parametric / _inverse modules)
# ---------------------------------------------------------------------------
from ._inverse import _adjoint_gate as _adjoint_gate  # noqa: E402, F401
from ._inverse import _inverse_gate_list as _inverse_gate_list  # noqa: E402, F401
from ._parametric import _apply_angles as _apply_angles  # noqa: E402, F401
from ._parametric import _extract_angles as _extract_angles  # noqa: E402, F401
from ._parametric import _extract_topology as _extract_topology  # noqa: E402, F401


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
# InstructionRecord & compile-mode global state (from _compile_state)
# ---------------------------------------------------------------------------
from .._compile_state import (  # noqa: E402 – after qint import is fine
    CallRecord,  # noqa: F401 – re-exported for tests
    InstructionRecord,  # noqa: F401 – re-exported for tests
    _record_call,  # noqa: F401 – re-exported for tests
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
# Recursive replay of nested compiled function calls via CallRecord
# ---------------------------------------------------------------------------


def _replay_call_records(block, virtual_to_real):
    """Replay nested compiled function calls recorded during capture.

    Iterates ``block._call_records`` and, for each ``CallRecord``, builds
    the inner function's quantum arguments by mapping the record's virtual
    qubit indices through *virtual_to_real* (outer virtual -> replay physical).
    Then delegates to the inner function's ``_replay`` with the resolved
    quantum args.

    Parameters
    ----------
    block : CompiledBlock
        Block whose ``_call_records`` list contains nested call references.
    virtual_to_real : dict
        Mapping from outer function's virtual qubit indices to replay-time
        physical qubit indices.
    """
    call_records = getattr(block, "_call_records", None)
    if not call_records:
        return

    for cr in call_records:
        inner_func = cr.compiled_func_ref
        if inner_func is None or not hasattr(inner_func, "_cache"):
            continue

        # Look up the inner function's cached block
        inner_block = inner_func._cache.get(cr.cache_key)
        if inner_block is None:
            continue

        # Build qint wrappers from the mapped physical qubit indices.
        # Each entry in quantum_arg_indices is a list of virtual indices
        # (in the outer function's virtual space) for one quantum arg.
        inner_quantum_args = []
        for arg_virtual_indices in cr.quantum_arg_indices:
            # Map outer virtual -> replay physical
            phys_indices = [virtual_to_real[v] for v in arg_virtual_indices]
            width = len(phys_indices)

            # Build a qint view over these physical qubits
            qubits_arr = np.zeros(64, dtype=np.uint32)
            for i, pq in enumerate(phys_indices):
                qubits_arr[64 - width + i] = pq
            q = qint(create_new=False, bit_list=qubits_arr, width=width)
            inner_quantum_args.append(q)

        # Delegate to the inner function's _replay
        inner_func._replay(inner_block, inner_quantum_args, track_forward=False)

        # Credit gate count for the inner call (inject_remapped_gates
        # does not increment circ->gate_count, and we bypassed __call__).
        _used_ir = getattr(inner_func, "_last_replay_used_ir", False)
        if not _used_ir:
            _inner_gc = (
                inner_block.original_gate_count
                if inner_block.original_gate_count
                else len(inner_block.gates)
            )
            if _inner_gc:
                add_gate_count(_inner_gc)


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
    from ..qarray import qarray

    if isinstance(qa, qarray):
        return _get_qarray_qubit_indices(qa)
    else:
        return _get_qint_qubit_indices(qa)


def _get_quantum_arg_width(qa):
    """Get total qubit count from a qint or qarray argument."""
    from ..qarray import qarray

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
    from ..qarray import qarray

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
# CompiledFunc, compile decorator, inverse classes
# ---------------------------------------------------------------------------
from ._func import CompiledFunc as CompiledFunc  # noqa: E402
from ._func import _clear_all_caches as _clear_all_caches  # noqa: E402
from ._func import _compiled_funcs as _compiled_funcs  # noqa: E402
from ._func import compile as compile  # noqa: E402
from ._inverse import _AncillaInverseProxy as _AncillaInverseProxy  # noqa: E402
from ._inverse import _InverseCompiledFunc as _InverseCompiledFunc  # noqa: E402
