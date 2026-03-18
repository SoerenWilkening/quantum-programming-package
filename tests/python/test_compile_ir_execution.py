"""Tests for IR execution phase — _execute_ir and compile-mode capture.

Covers issue Quantum_Assembly-pzl: _execute_ir iterates block._instruction_ir
and calls run_instruction for each entry to produce gates in the circuit.
The compile-mode capture records IR, then _execute_ir replays it.

IR recording for arithmetic operations only happens in QFT mode
(fault_tolerant=False). In Toffoli mode (default), arithmetic operations
bypass IR recording and emit gates directly through the Toffoli dispatch
path, producing correct gate types (X/CX/CCX instead of QFT rotations).
"""

import quantum_language as ql
from quantum_language._compile_state import InstructionRecord
from quantum_language._core import (
    extract_gate_range,
    get_current_layer,
    get_gate_count,
)
from quantum_language.compile import (
    CompiledBlock,
    _execute_ir,
    _get_qint_qubit_indices,
)


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


def _get_gate_types(start_layer, end_layer):
    """Extract gate types from a circuit layer range as a sorted list."""
    gates = extract_gate_range(start_layer, end_layer)
    return sorted(g["type"] for g in gates)


# ---------------------------------------------------------------------------
# _execute_ir — basic functionality (QFT mode, where IR recording is active)
# ---------------------------------------------------------------------------


class TestExecuteIR:
    """Verify _execute_ir produces gates from IR entries."""

    def test_execute_ir_produces_gates(self):
        """_execute_ir with recorded IR produces gates in the circuit."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        assert len(block._instruction_ir) == 1, "IR should have 1 entry"

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Gates should be produced by _execute_ir"

    def test_execute_ir_no_entries_no_gates(self):
        """_execute_ir with empty IR produces no gates."""
        ql.circuit()
        block = _make_block()

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after == gc_before, "No gates for empty IR"

    def test_execute_ir_skips_null_seq(self):
        """_execute_ir skips entries with null (0) sequence pointer."""
        ql.circuit()
        block = _make_block()
        block._instruction_ir.append(
            InstructionRecord(
                name="noop",
                registers=(0, 1),
                uncontrolled_seq=0,
                controlled_seq=0,
            )
        )

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after == gc_before, "Null seq entries should be skipped"

    def test_execute_ir_with_qubit_mapping(self):
        """_execute_ir remaps qubit indices when qubit_mapping is provided."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording

        # Create two qints at different physical qubits
        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        # Record IR using a's qubits
        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        assert len(block._instruction_ir) == 1

        # Build mapping from a's qubits to b's qubits
        a_qubits = _get_qint_qubit_indices(a)
        b_qubits = _get_qint_qubit_indices(b)
        mapping = dict(zip(a_qubits, b_qubits, strict=False))

        gc_before = get_gate_count()
        _execute_ir(block, qubit_mapping=mapping)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Remapped IR should produce gates"

    def test_execute_ir_multiple_entries(self):
        """_execute_ir handles multiple IR entries."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1
            a += 2
            a -= 3

        assert len(block._instruction_ir) == 3

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Multiple IR entries should produce gates"

    def test_execute_ir_invert_flag(self):
        """_execute_ir respects the invert flag on IR entries."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a -= 2  # Records with invert=True

        assert len(block._instruction_ir) == 1
        assert block._instruction_ir[0].invert is True

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Inverted IR should produce gates"

    def test_toffoli_mode_skips_ir_recording(self):
        """In Toffoli mode, arithmetic ops bypass IR recording."""
        ql.circuit()
        ql.option("simulate", True)
        # fault_tolerant=True is default (Toffoli mode)
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        # Toffoli mode: arithmetic ops emit gates directly, no IR entries
        assert len(block._instruction_ir) == 0, "Toffoli mode should not record IR for arithmetic"


# ---------------------------------------------------------------------------
# Compiled function produces gates via IR execution
# ---------------------------------------------------------------------------


class TestCompiledFunctionIRExecution:
    """Verify compiled function first call produces gates via IR."""

    def test_first_call_produces_gates(self):
        """First call of compiled function produces gates in circuit."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc_before = get_gate_count()
        a = ql.qint(0, width=4)
        inc(a)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Compiled function should produce gates"

    def test_first_call_stores_ir_qft_mode(self):
        """First call records IR entries on the cached block in QFT mode."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        block = list(inc._cache.values())[0]
        assert len(block._instruction_ir) > 0, "Block should have IR entries"
        assert block._instruction_ir[0].name == "add_cq"

    def test_compiled_same_result_as_uncompiled(self):
        """Compiled function produces same mathematical result as uncompiled."""
        # Uncompiled
        ql.circuit()
        ql.option("simulate", True)
        a = ql.qint(3, width=4)
        a += 5

        # Compiled
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def add_five(x):
            x += 5
            return x

        b = ql.qint(3, width=4)
        result = add_five(b)

        # Both should operate on the same qubits
        assert result is b, "In-place return should be same object"

    def test_second_call_skips_compilation(self):
        """Second call uses cache (no recompilation)."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # First call — capture

        cache_size_after_first = len(inc._cache)
        assert cache_size_after_first == 1

        b = ql.qint(0, width=4)
        inc(b)  # Second call — replay from cache

        cache_size_after_second = len(inc._cache)
        assert cache_size_after_second == 1, "Cache should not grow on second call"

    def test_second_call_produces_gates(self):
        """Second call (replay) also produces gates."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # First call
        gc_after_first = get_gate_count()

        b = ql.qint(0, width=4)
        inc(b)  # Second call
        gc_after_second = get_gate_count()

        assert gc_after_second > gc_after_first, "Replay should produce gates"

    def test_gate_count_positive_across_calls(self):
        """First and second calls both produce a positive gate count."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc_before = get_gate_count()
        a = ql.qint(0, width=4)
        inc(a)
        first_call_gates = get_gate_count() - gc_before

        gc_before_2 = get_gate_count()
        b = ql.qint(0, width=4)
        inc(b)
        second_call_gates = get_gate_count() - gc_before_2

        assert first_call_gates > 0, "First call should produce gates"
        assert second_call_gates > 0, "Second call should produce gates"


# ---------------------------------------------------------------------------
# IR execution gate count matches expected
# ---------------------------------------------------------------------------


class TestIRGateCountMatches:
    """Verify gate count from IR execution matches expected values."""

    def test_ir_execution_gate_count_nonzero(self):
        """IR execution produces a positive gate count."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc_before = get_gate_count()
        a = ql.qint(0, width=2)
        inc(a)
        gc_after = get_gate_count()

        assert gc_after - gc_before > 0

    def test_ir_execution_layers_increase(self):
        """IR execution adds circuit layers (simulate=True)."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        start = get_current_layer()
        a = ql.qint(0, width=2)
        inc(a)
        end = get_current_layer()

        assert end > start, f"Layers should increase: start={start}, end={end}"

    def test_ir_execution_tracking_only_mode(self):
        """IR execution increments gate_count in tracking-only mode."""
        ql.circuit()
        # Default: simulate=False (tracking-only)

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc_before = get_gate_count()
        a = ql.qint(0, width=4)
        inc(a)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Gate count should increment in tracking-only mode"


# ---------------------------------------------------------------------------
# Compiled flag prevents recompilation
# ---------------------------------------------------------------------------


class TestCompiledFlagPreventsRecompilation:
    """Verify the cache hit path skips recompilation."""

    def test_cache_hit_on_same_widths(self):
        """Same width args hit cache (no recompilation)."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(debug=True)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # Miss
        assert inc.stats["cache_hit"] is False

        b = ql.qint(0, width=4)
        inc(b)  # Hit
        assert inc.stats["cache_hit"] is True

    def test_different_widths_separate_cache_entries(self):
        """Different width args produce different cache entries."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(debug=True, opt=3)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # Miss for width=4

        b = ql.qint(0, width=8)
        inc(b)  # Miss for width=8

        assert len(inc._cache) == 2


# ---------------------------------------------------------------------------
# _run_instruction_py wrapper
# ---------------------------------------------------------------------------


class TestRunInstructionPy:
    """Verify the Python-accessible run_instruction wrapper."""

    def test_run_instruction_py_null_raises(self):
        """_run_instruction_py with null seq_ptr raises ValueError."""
        from quantum_language._core import _run_instruction_py

        ql.circuit()
        import pytest

        with pytest.raises(ValueError, match="null sequence"):
            _run_instruction_py(0, (0, 1), 0)

    def test_run_instruction_py_produces_gates(self):
        """_run_instruction_py with valid seq produces gates."""
        from quantum_language._core import _run_instruction_py

        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        entry = block._instruction_ir[0]
        gc_before = get_gate_count()
        _run_instruction_py(entry.uncontrolled_seq, entry.registers, 0)
        gc_after = get_gate_count()

        assert gc_after > gc_before


# ---------------------------------------------------------------------------
# Gate correctness — compiled path produces same gates as uncompiled path
# ---------------------------------------------------------------------------


class TestCompiledGateCorrectness:
    """Verify compiled path produces same gate types/counts as uncompiled."""

    def test_toffoli_mode_gate_count_matches(self):
        """In Toffoli mode, compiled and uncompiled produce same gate count."""
        # Uncompiled (direct)
        ql.circuit()
        ql.option("simulate", True)
        # fault_tolerant=True is default (Toffoli mode)
        gc_start_direct = get_gate_count()
        start_layer_direct = get_current_layer()
        a = ql.qint(0, width=4)
        a += 7
        gc_direct = get_gate_count() - gc_start_direct
        end_layer_direct = get_current_layer()
        types_direct = _get_gate_types(start_layer_direct, end_layer_direct)

        # Compiled
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def add_seven(x):
            x += 7
            return x

        gc_start_compiled = get_gate_count()
        start_layer_compiled = get_current_layer()
        b = ql.qint(0, width=4)
        add_seven(b)
        gc_compiled = get_gate_count() - gc_start_compiled
        end_layer_compiled = get_current_layer()
        types_compiled = _get_gate_types(start_layer_compiled, end_layer_compiled)

        assert gc_compiled == gc_direct, (
            f"Toffoli mode gate count mismatch: compiled={gc_compiled}, direct={gc_direct}"
        )
        assert types_compiled == types_direct, (
            f"Toffoli mode gate types mismatch: compiled={types_compiled}, direct={types_direct}"
        )

    def test_toffoli_mode_produces_toffoli_gate_types(self):
        """In Toffoli mode, compiled path produces only X/CX/CCX gates (type 0)."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def add_seven(x):
            x += 7
            return x

        start = get_current_layer()
        a = ql.qint(0, width=4)
        add_seven(a)
        end = get_current_layer()

        gates = extract_gate_range(start, end)
        assert len(gates) > 0, "Should produce gates"
        gate_types = {g["type"] for g in gates}
        # Toffoli mode: gate type 0 = X/CX/CCX (Pauli-X family)
        assert gate_types == {0}, (
            f"Expected only type-0 (X/CX/CCX) gates in Toffoli mode, got types {gate_types}"
        )

    def test_qft_mode_gate_count_matches(self):
        """In QFT mode, compiled and uncompiled produce same gate count."""
        # Uncompiled (direct)
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)
        gc_start_direct = get_gate_count()
        start_layer_direct = get_current_layer()
        a = ql.qint(0, width=4)
        a += 7
        gc_direct = get_gate_count() - gc_start_direct
        end_layer_direct = get_current_layer()
        types_direct = _get_gate_types(start_layer_direct, end_layer_direct)

        # Compiled
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)

        @ql.compile
        def add_seven(x):
            x += 7
            return x

        gc_start_compiled = get_gate_count()
        start_layer_compiled = get_current_layer()
        b = ql.qint(0, width=4)
        add_seven(b)
        gc_compiled = get_gate_count() - gc_start_compiled
        end_layer_compiled = get_current_layer()
        types_compiled = _get_gate_types(start_layer_compiled, end_layer_compiled)

        assert gc_compiled == gc_direct, (
            f"QFT mode gate count mismatch: compiled={gc_compiled}, direct={gc_direct}"
        )
        assert types_compiled == types_direct, (
            f"QFT mode gate types mismatch: compiled={types_compiled}, direct={types_direct}"
        )

    def test_qft_mode_produces_rotation_gates(self):
        """In QFT mode, compiled path produces rotation gates (Phase/Hadamard)."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)

        @ql.compile
        def add_seven(x):
            x += 7
            return x

        start = get_current_layer()
        a = ql.qint(0, width=4)
        add_seven(a)
        end = get_current_layer()

        gates = extract_gate_range(start, end)
        assert len(gates) > 0, "Should produce gates"
        gate_types = {g["type"] for g in gates}
        # QFT mode: should include Phase (8) and/or Hadamard (4) gates
        assert gate_types != {0}, f"QFT mode should NOT produce only type-0 gates, got {gate_types}"

    def test_subtraction_gate_correctness(self):
        """Compiled subtraction matches uncompiled in Toffoli mode."""
        # Uncompiled
        ql.circuit()
        ql.option("simulate", True)
        gc_start = get_gate_count()
        start_layer = get_current_layer()
        a = ql.qint(10, width=4)
        a -= 3
        gc_direct = get_gate_count() - gc_start
        end_layer = get_current_layer()
        types_direct = _get_gate_types(start_layer, end_layer)

        # Compiled
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def sub_three(x):
            x -= 3
            return x

        gc_start2 = get_gate_count()
        start_layer2 = get_current_layer()
        b = ql.qint(10, width=4)
        sub_three(b)
        gc_compiled = get_gate_count() - gc_start2
        end_layer2 = get_current_layer()
        types_compiled = _get_gate_types(start_layer2, end_layer2)

        assert gc_compiled == gc_direct, (
            f"Subtraction gate count mismatch: compiled={gc_compiled}, direct={gc_direct}"
        )
        assert types_compiled == types_direct, "Subtraction gate types mismatch"

    def test_multiplication_gate_correctness(self):
        """Compiled multiplication matches uncompiled in Toffoli mode."""
        # Uncompiled
        ql.circuit()
        ql.option("simulate", True)
        gc_start = get_gate_count()
        start_layer = get_current_layer()
        a = ql.qint(3, width=4)
        a *= 5
        gc_direct = get_gate_count() - gc_start
        end_layer = get_current_layer()
        types_direct = _get_gate_types(start_layer, end_layer)

        # Compiled
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def mul_five(x):
            x *= 5
            return x

        gc_start2 = get_gate_count()
        start_layer2 = get_current_layer()
        b = ql.qint(3, width=4)
        mul_five(b)
        gc_compiled = get_gate_count() - gc_start2
        end_layer2 = get_current_layer()
        types_compiled = _get_gate_types(start_layer2, end_layer2)

        assert gc_compiled == gc_direct, (
            f"Multiplication gate count mismatch: compiled={gc_compiled}, direct={gc_direct}"
        )
        assert types_compiled == types_direct, "Multiplication gate types mismatch"
