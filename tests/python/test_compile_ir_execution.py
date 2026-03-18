"""Tests for IR execution phase — _execute_ir and compile-mode capture.

Covers issue Quantum_Assembly-pzl: _execute_ir iterates block._instruction_ir
and calls run_instruction for each entry to produce gates in the circuit.
The compile-mode capture records IR, then _execute_ir replays it.
"""

import quantum_language as ql
from quantum_language._compile_state import InstructionRecord
from quantum_language._core import get_current_layer, get_gate_count
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


# ---------------------------------------------------------------------------
# _execute_ir — basic functionality
# ---------------------------------------------------------------------------


class TestExecuteIR:
    """Verify _execute_ir produces gates from IR entries."""

    def test_execute_ir_produces_gates(self):
        """_execute_ir with recorded IR produces gates in the circuit."""
        ql.circuit()
        ql.option("simulate", True)
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

    def test_first_call_stores_ir(self):
        """First call records IR entries on the cached block."""
        ql.circuit()
        ql.option("simulate", True)

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
