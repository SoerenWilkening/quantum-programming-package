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
