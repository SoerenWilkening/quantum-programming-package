"""IR execution and DAG construction from instruction records.

Contains ``_execute_ir`` (replay ``InstructionRecord`` entries via
``run_instruction``), ``_build_dag_from_ir`` (populate DAG nodes from
IR), and ``_replay_call_records`` (recursive replay of nested compiled
function calls via ``CallRecord``).
"""

import numpy as np

from .._core import (
    _get_control_bool,
    _get_controlled,
    _run_instruction_py,
    add_gate_count,
)
from ..call_graph import (
    _resolve_gate_count,
    current_dag_context,
)
from ..qint import qint


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
