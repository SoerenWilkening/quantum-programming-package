"""Compile-mode global state for instruction-level IR recording.

This module is intentionally dependency-free (imports nothing from the
quantum_language package) to avoid circular imports between compile.py
and qint.pyx.
"""

import dataclasses

# ---------------------------------------------------------------------------
# InstructionRecord
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class InstructionRecord:
    """A single instruction captured during compile-mode execution.

    Attributes
    ----------
    name : str
        Human-readable instruction name (e.g. ``'add_cq'``, ``'eq_cq'``).
    registers : tuple
        Qubit indices involved in this instruction.
    uncontrolled_seq : int
        Pointer to uncontrolled ``sequence_t`` (as Python int), or 0.
    controlled_seq : int
        Pointer to controlled ``sequence_t`` (as Python int), or 0.
    invert : bool
        Whether the instruction was inverted (subtraction, etc.).
    """

    name: str
    registers: tuple
    uncontrolled_seq: int
    controlled_seq: int
    invert: bool = False


# ---------------------------------------------------------------------------
# CallRecord
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class CallRecord:
    """A reference to a nested compiled function call during capture.

    Instead of inlining the inner function's gates, the outer function
    stores a ``CallRecord`` in its block's ``_call_records`` list.  This
    enables hierarchical gate counting and visualization without memory
    explosion from gate duplication.

    Attributes
    ----------
    compiled_func_ref : object
        Reference to the inner ``CompiledFunc`` instance.
    cache_key : tuple
        Cache key used for the inner function's ``CompiledBlock``.
    quantum_arg_indices : list[list[int]]
        Virtual qubit indices per quantum argument at call time.
    """

    compiled_func_ref: object
    cache_key: tuple
    quantum_arg_indices: list
    gate_layer_start: int = -1  # circuit layer before inner call (inclusive)
    gate_layer_end: int = -1  # circuit layer after inner call (exclusive)


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

# The active CompiledBlock receiving IR entries (set by compile_mode()).
_active_compile_block = None


def _is_compile_mode():
    """Return True if compile-mode IR recording is active."""
    return _active_compile_block is not None


def _get_active_compile_block():
    """Return the active CompiledBlock, or None."""
    return _active_compile_block


def _set_active_compile_block(block):
    """Set the active compile block (called by compile_mode context manager)."""
    global _active_compile_block
    _active_compile_block = block


def _record_instruction(name, registers, uncontrolled_seq=0, controlled_seq=0, invert=False):
    """Append an InstructionRecord to the active CompiledBlock.

    Parameters
    ----------
    name : str
        Instruction name (e.g. ``'add_cq'``).
    registers : tuple[int, ...]
        Qubit indices involved.
    uncontrolled_seq : int
        Pointer to uncontrolled ``sequence_t`` as Python int.
    controlled_seq : int
        Pointer to controlled ``sequence_t`` as Python int.
    invert : bool
        Whether the instruction is inverted.
    """
    block = _active_compile_block
    if block is None:
        return
    block._instruction_ir.append(
        InstructionRecord(
            name=name,
            registers=registers,
            uncontrolled_seq=uncontrolled_seq,
            controlled_seq=controlled_seq,
            invert=invert,
        )
    )


def _record_call(compiled_func, cache_key, quantum_arg_indices):
    """Record a nested compiled function call on the active block.

    Appends a ``CallRecord`` to the active block's ``_call_records``
    list.  This is a no-op when compile-mode is not active.

    Parameters
    ----------
    compiled_func : object
        The inner ``CompiledFunc`` instance being called.
    cache_key : tuple
        Cache key identifying the inner function's compiled variant.
    quantum_arg_indices : list[list[int]]
        Virtual qubit indices for each quantum argument at call time.
    """
    block = _active_compile_block
    if block is None:
        return
    if not hasattr(block, "_call_records") or block._call_records is None:
        block._call_records = []
    block._call_records.append(
        CallRecord(
            compiled_func_ref=compiled_func,
            cache_key=cache_key,
            quantum_arg_indices=quantum_arg_indices,
        )
    )
