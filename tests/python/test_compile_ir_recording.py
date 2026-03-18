"""Tests for compile-mode IR recording in DSL operators.

Covers issue Quantum_Assembly-5c2: DSL operators (+=, -=, <, &, etc.)
record InstructionRecord entries when compile-mode is active, without
calling run_instruction (no gates emitted to circuit).
"""

import quantum_language as ql
from quantum_language._compile_state import (
    _is_compile_mode,
)
from quantum_language.compile import CompiledBlock


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


# ---------------------------------------------------------------------------
# Compile-mode flag activation via global state
# ---------------------------------------------------------------------------


def test_compile_mode_sets_global_block():
    """compile_mode() sets the module-level _active_compile_block."""

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    assert not _is_compile_mode()
    with dummy.compile_mode(block):
        assert _is_compile_mode()
    assert not _is_compile_mode()


def test_compile_mode_global_cleared_on_exception():
    """Global compile block is cleared even on exception."""

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    try:
        with dummy.compile_mode(block):
            raise RuntimeError("test")
    except RuntimeError:
        pass
    assert not _is_compile_mode()


# ---------------------------------------------------------------------------
# Arithmetic IR recording
# ---------------------------------------------------------------------------


def test_iadd_int_records_ir():
    """a += 1 in compile mode records one 'add_cq' IR entry."""
    ql.circuit()
    a = ql.qint(0, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    gc_before = ql.get_gate_count()
    with dummy.compile_mode(block):
        a += 1
    gc_after = ql.get_gate_count()

    assert len(block._instruction_ir) == 1
    rec = block._instruction_ir[0]
    assert rec.name == "add_cq"
    assert isinstance(rec.registers, tuple)
    assert len(rec.registers) > 0
    assert rec.uncontrolled_seq != 0  # Valid sequence_t pointer
    assert rec.invert is False
    # No gates emitted during compile phase
    assert gc_after == gc_before


def test_isub_int_records_ir():
    """a -= 2 in compile mode records one 'add_cq' IR entry with invert=True."""
    ql.circuit()
    a = ql.qint(5, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a -= 2

    assert len(block._instruction_ir) == 1
    rec = block._instruction_ir[0]
    assert rec.name == "add_cq"
    assert rec.invert is True


def test_two_iadd_records_two_entries():
    """a += 1; a += 2 produces 2 IR entries (acceptance criterion)."""
    ql.circuit()
    a = ql.qint(0, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a += 1
        a += 2

    assert len(block._instruction_ir) == 2
    assert block._instruction_ir[0].name == "add_cq"
    assert block._instruction_ir[1].name == "add_cq"


def test_iadd_qint_records_add_qq():
    """a += b (both qint) records an 'add_qq' IR entry."""
    ql.circuit()
    a = ql.qint(3, width=4)
    b = ql.qint(2, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a += b

    assert len(block._instruction_ir) == 1
    rec = block._instruction_ir[0]
    assert rec.name == "add_qq"
    assert rec.uncontrolled_seq != 0


def test_no_gates_emitted_in_compile_mode():
    """No gates are emitted to the circuit during compile phase."""
    ql.circuit()
    a = ql.qint(0, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    gc_before = ql.get_gate_count()
    with dummy.compile_mode(block):
        a += 1
        a += 2
        a -= 3
    gc_after = ql.get_gate_count()
    assert gc_after == gc_before


# ---------------------------------------------------------------------------
# Multiplication IR recording
# ---------------------------------------------------------------------------


def test_mul_cq_records_ir():
    """a * 3 in compile mode records a 'mul_cq' IR entry."""
    ql.circuit()
    a = ql.qint(2, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a * 3

    # Out-of-place mul: first ixor (copy), then mul_cq
    mul_entries = [r for r in block._instruction_ir if r.name == "mul_cq"]
    assert len(mul_entries) == 1
    assert mul_entries[0].uncontrolled_seq != 0


# ---------------------------------------------------------------------------
# Comparison IR recording
# ---------------------------------------------------------------------------


def test_eq_int_records_ir():
    """(a == 5) in compile mode records an 'eq_cq' IR entry."""
    ql.circuit()
    a = ql.qint(5, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a == 5

    eq_entries = [r for r in block._instruction_ir if r.name == "eq_cq"]
    assert len(eq_entries) == 1
    assert eq_entries[0].uncontrolled_seq != 0
    assert eq_entries[0].controlled_seq != 0


def test_lt_records_ir():
    """(a < 5) in compile mode records an 'lt' IR entry."""
    ql.circuit()
    a = ql.qint(3, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a < 5

    lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
    assert len(lt_entries) == 1


def test_gt_records_ir():
    """(a > 2) in compile mode records a 'gt' IR entry."""
    ql.circuit()
    a = ql.qint(5, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a > 2

    gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
    assert len(gt_entries) == 1


# ---------------------------------------------------------------------------
# Bitwise IR recording
# ---------------------------------------------------------------------------


def test_and_qq_records_ir():
    """(a & b) in compile mode records an 'and_qq' IR entry."""
    ql.circuit()
    a = ql.qint(0b1101, width=4)
    b = ql.qint(0b1011, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a & b

    and_entries = [r for r in block._instruction_ir if r.name == "and_qq"]
    assert len(and_entries) == 1
    assert and_entries[0].uncontrolled_seq != 0


def test_or_qq_records_ir():
    """(a | b) in compile mode records an 'or_qq' IR entry."""
    ql.circuit()
    a = ql.qint(0b1100, width=4)
    b = ql.qint(0b0011, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a | b

    or_entries = [r for r in block._instruction_ir if r.name == "or_qq"]
    assert len(or_entries) == 1


def test_xor_records_ir():
    """(a ^ b) in compile mode records a 'xor' IR entry."""
    ql.circuit()
    a = ql.qint(0b1100, width=4)
    b = ql.qint(0b0110, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = a ^ b

    xor_entries = [r for r in block._instruction_ir if r.name == "xor"]
    assert len(xor_entries) == 1


def test_ixor_int_records_ir():
    """a ^= 5 in compile mode records an 'ixor_cq' IR entry."""
    ql.circuit()
    a = ql.qint(0, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a ^= 5

    ixor_entries = [r for r in block._instruction_ir if r.name == "ixor_cq"]
    assert len(ixor_entries) == 1


def test_ixor_qq_records_ir():
    """a ^= b in compile mode records an 'ixor_qq' IR entry."""
    ql.circuit()
    a = ql.qint(0, width=4)
    b = ql.qint(3, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a ^= b

    ixor_entries = [r for r in block._instruction_ir if r.name == "ixor_qq"]
    assert len(ixor_entries) == 1


def test_not_records_ir():
    """~a in compile mode records a 'not' IR entry."""
    ql.circuit()
    a = ql.qint(0b1010, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        _ = ~a  # noqa: F841

    not_entries = [r for r in block._instruction_ir if r.name == "not"]
    assert len(not_entries) == 1
    assert not_entries[0].uncontrolled_seq != 0
    assert not_entries[0].controlled_seq != 0


# ---------------------------------------------------------------------------
# Compile-mode flag lifecycle
# ---------------------------------------------------------------------------


def test_compile_mode_unset_after_completion():
    """Compile-mode flag is unset after compilation completes (acceptance criterion)."""

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        assert dummy._compile_mode is True
    assert dummy._compile_mode is False
    assert not _is_compile_mode()


def test_each_ir_entry_has_valid_sequence():
    """Each IR entry has a valid sequence_t (acceptance criterion)."""
    ql.circuit()
    a = ql.qint(0, width=4)

    @ql.compile
    def dummy(x):
        return x

    block = _make_block()
    with dummy.compile_mode(block):
        a += 1
        a += 2

    for rec in block._instruction_ir:
        # At least one of uncontrolled/controlled should be non-zero
        assert rec.uncontrolled_seq != 0 or rec.controlled_seq != 0, (
            f"IR entry '{rec.name}' has no valid sequence_t"
        )
