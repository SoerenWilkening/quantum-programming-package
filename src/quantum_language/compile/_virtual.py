"""Virtual qubit mapping and return value construction helpers.

Pure functions for mapping real qubit indices to virtual namespace,
extracting qubit indices from quantum arguments, and constructing
return values from replay-mapped qubits.  No dependency on ``CompiledFunc``.
"""

import numpy as np

from ..qint import qint


# ---------------------------------------------------------------------------
# Virtual qubit mapping helpers
# ---------------------------------------------------------------------------
def _build_virtual_mapping(gates, param_qubit_indices):
    """Map real qubit indices to a virtual namespace.

    Virtual index 0 is reserved for the control qubit.  Parameter
    qubits are mapped starting at index 1, then any ancilla/temporary
    qubits encountered in the gate list.

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


# ---------------------------------------------------------------------------
# Qubit index extraction
# ---------------------------------------------------------------------------
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
