"""Tests for compile-mode infrastructure (InstructionRecord, IR list, flag).

Covers issue Quantum_Assembly-fkp: foundational data structures for
instruction-level IR recording.
"""

import quantum_language as ql
from quantum_language.compile import CompiledBlock, InstructionRecord

# ---------------------------------------------------------------------------
# InstructionRecord
# ---------------------------------------------------------------------------


def test_instruction_record_fields():
    """InstructionRecord stores name, registers, both sequences."""
    rec = InstructionRecord(
        name="add",
        registers=["r0", "r1"],
        uncontrolled_seq=[{"gate": "cx"}],
        controlled_seq=[{"gate": "ccx"}],
    )
    assert rec.name == "add"
    assert rec.registers == ["r0", "r1"]
    assert rec.uncontrolled_seq == [{"gate": "cx"}]
    assert rec.controlled_seq == [{"gate": "ccx"}]


def test_instruction_record_is_dataclass():
    """InstructionRecord is a dataclass (supports eq, repr, etc.)."""
    a = InstructionRecord("add", [1], [], [])
    b = InstructionRecord("add", [1], [], [])
    assert a == b

    c = InstructionRecord("sub", [1], [], [])
    assert a != c


def test_instruction_record_empty_sequences():
    """InstructionRecord works with empty sequences."""
    rec = InstructionRecord(name="noop", registers=[], uncontrolled_seq=[], controlled_seq=[])
    assert rec.uncontrolled_seq == []
    assert rec.controlled_seq == []


# ---------------------------------------------------------------------------
# CompiledBlock._instruction_ir
# ---------------------------------------------------------------------------


def test_compiled_block_instruction_ir_default():
    """CompiledBlock._instruction_ir is an empty list by default."""
    block = CompiledBlock(
        gates=[],
        total_virtual_qubits=2,
        param_qubit_ranges=[(1, 2)],
        internal_qubit_count=0,
        return_qubit_range=None,
    )
    assert block._instruction_ir == []
    assert isinstance(block._instruction_ir, list)


def test_compiled_block_instruction_ir_mutable():
    """_instruction_ir can be appended to after construction."""
    block = CompiledBlock(
        gates=[],
        total_virtual_qubits=2,
        param_qubit_ranges=[(1, 2)],
        internal_qubit_count=0,
        return_qubit_range=None,
    )
    rec = InstructionRecord("xor", [0], [{"g": 1}], [{"g": 2}])
    block._instruction_ir.append(rec)
    assert len(block._instruction_ir) == 1
    assert block._instruction_ir[0].name == "xor"


def test_compiled_block_instruction_ir_independent():
    """Each CompiledBlock gets its own _instruction_ir list."""
    b1 = CompiledBlock([], 1, [], 0, None)
    b2 = CompiledBlock([], 1, [], 0, None)
    b1._instruction_ir.append(InstructionRecord("a", [], [], []))
    assert len(b2._instruction_ir) == 0


# ---------------------------------------------------------------------------
# CompiledFunc._compile_mode flag & context manager
# ---------------------------------------------------------------------------


def test_compile_mode_default_false():
    """CompiledFunc._compile_mode is False by default."""

    @ql.compile
    def dummy(x):
        return x

    assert dummy._compile_mode is False


def test_compile_mode_context_manager():
    """compile_mode() context manager activates and deactivates the flag."""

    @ql.compile
    def dummy(x):
        return x

    assert dummy._compile_mode is False
    with dummy.compile_mode():
        assert dummy._compile_mode is True
    assert dummy._compile_mode is False


def test_compile_mode_context_manager_exception_safety():
    """compile_mode() resets the flag even if an exception occurs."""

    @ql.compile
    def dummy(x):
        return x

    try:
        with dummy.compile_mode():
            assert dummy._compile_mode is True
            raise RuntimeError("test error")
    except RuntimeError:
        pass

    assert dummy._compile_mode is False


def test_compile_mode_context_manager_yields_self():
    """compile_mode() yields the CompiledFunc instance."""

    @ql.compile
    def dummy(x):
        return x

    with dummy.compile_mode() as cf:
        assert cf is dummy
