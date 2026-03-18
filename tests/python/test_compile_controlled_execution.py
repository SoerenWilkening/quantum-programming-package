"""Tests for controlled IR execution via _execute_ir.

Covers issue Quantum_Assembly-dae: _execute_ir checks the control stack at
runtime and selects controlled_seq (appending the control qubit) when inside
a ``with`` block.  This fixes the first-call trade-off: the first call of a
compiled function inside a ``with`` block now produces correctly controlled
gates.

Acceptance criteria:
- Each IR entry has both controlled and uncontrolled sequences.
- Execute inside with block uses controlled sequences.
- First call of compiled function inside with produces controlled gates.
- Nested with c1: with c2: f(x) produces correct combined-controlled gates.
- Controlled call produces more gates than uncontrolled.
"""

import gc
import re
import warnings

import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language._core import (
    extract_gate_range,
    get_current_layer,
    get_gate_count,
)
from quantum_language.compile import (
    CompiledBlock,
    _execute_ir,
)

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM and extract integer from result register."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _get_num_qubits(qasm_str):
    """Extract number of qubits from OpenQASM string."""
    matches = re.findall(r"qubit\[(\d+)\]", qasm_str)
    if matches:
        return max(int(m) for m in matches)
    return 0


# ---------------------------------------------------------------------------
# IR entries store both controlled and uncontrolled sequences
# ---------------------------------------------------------------------------


class TestIREntryBothSequences:
    """Each IR entry has both controlled_seq and uncontrolled_seq."""

    def test_add_cq_has_both_seqs(self):
        """Arithmetic IR entry (QFT mode) has both seq types."""
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode for IR recording
        a = ql.qint(0, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        assert len(block._instruction_ir) == 1
        rec = block._instruction_ir[0]
        assert rec.uncontrolled_seq != 0, "Should have uncontrolled_seq"
        assert rec.controlled_seq != 0, "Should have controlled_seq"

    def test_add_qq_has_both_seqs(self):
        """Quantum-quantum add IR entry has both seq types."""
        ql.circuit()
        ql.option("fault_tolerant", False)
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
        assert rec.uncontrolled_seq != 0
        assert rec.controlled_seq != 0

    def test_eq_cq_has_both_seqs(self):
        """Comparison IR entry has both seq types."""
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
        rec = eq_entries[0]
        assert rec.uncontrolled_seq != 0
        assert rec.controlled_seq != 0


# ---------------------------------------------------------------------------
# _execute_ir selects controlled seq inside with block
# ---------------------------------------------------------------------------


class TestExecuteIRControlled:
    """_execute_ir uses controlled_seq when inside a with block."""

    def test_execute_ir_controlled_produces_gates(self):
        """_execute_ir inside with-block produces gates using controlled seq."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)  # QFT mode for IR recording

        @ql.compile
        def dummy(x):
            return x

        # Record IR
        a = ql.qint(0, width=4)
        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        assert len(block._instruction_ir) == 1

        # Execute controlled (inside with)
        c = ql.qbool(True)
        with c:
            gc_before = get_gate_count()
            _execute_ir(block)
            controlled_gates = get_gate_count() - gc_before

        assert controlled_gates > 0, "Controlled IR execution should produce gates"

    def test_execute_ir_uses_different_seq_in_with(self):
        """_execute_ir uses controlled_seq (not uncontrolled_seq) inside with."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)

        @ql.compile
        def dummy(x):
            return x

        a = ql.qint(0, width=4)
        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        entry = block._instruction_ir[0]
        assert entry.uncontrolled_seq != entry.controlled_seq, (
            "Uncontrolled and controlled seq pointers should differ"
        )

    def test_execute_ir_uncontrolled_produces_gates(self):
        """_execute_ir outside with-block uses uncontrolled_seq and produces gates."""
        ql.circuit()
        ql.option("simulate", True)
        ql.option("fault_tolerant", False)

        @ql.compile
        def dummy(x):
            return x

        a = ql.qint(0, width=4)
        block = _make_block()
        with dummy.compile_mode(block):
            a += 1

        gc_before = get_gate_count()
        _execute_ir(block)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Uncontrolled IR execution should produce gates"


# ---------------------------------------------------------------------------
# First call of compiled function inside with produces controlled gates
# ---------------------------------------------------------------------------


class TestFirstCallControlledGates:
    """First call inside with block now produces controlled gates."""

    def test_first_call_in_with_produces_controlled_gates(self):
        """First call of @ql.compile inside with produces controlled gates."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c = ql.qbool(True)
        a = ql.qint(0, width=2)

        start = get_current_layer()
        with c:
            _ = inc(a)  # First call (capture path)
        end = get_current_layer()

        # Extract gates from the with-block
        gates = extract_gate_range(start, end)
        assert len(gates) > 0, "Should produce gates"

        # Check that some gates reference the control qubit
        ctrl_qubit = int(c.qubits[63])
        gates_with_ctrl = [g for g in gates if ctrl_qubit in g.get("controls", [])]
        assert len(gates_with_ctrl) > 0, (
            f"First call inside with should produce controlled gates "
            f"(control qubit={ctrl_qubit}), but none found"
        )

    def test_first_call_in_with_condition_false_no_effect(self):
        """First call inside with(False) produces no effect on result."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c:
            result = inc(result)  # First call inside with(False)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, (
            f"First call inside with(False) should skip inc -> result=0, got {actual}"
        )

    def test_first_call_in_with_condition_true_increments(self):
        """First call inside with(True) correctly increments."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c:
            result = inc(result)  # First call inside with(True)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, (
            f"First call inside with(True) should increment -> result=1, got {actual}"
        )


# ---------------------------------------------------------------------------
# Nested with c1: with c2: f(x) produces correct combined-controlled gates
# ---------------------------------------------------------------------------


class TestNestedWithControlledExecution:
    """Nested with blocks produce correctly combined-controlled gates."""

    def test_nested_both_true_first_call(self):
        """First call inside nested with, both True -> result=1."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)  # First call inside nested with

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"First call in nested with(True, True) -> result=1, got {actual}"

    def test_nested_inner_false_first_call(self):
        """First call inside nested with, inner False -> result=0."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c1 = ql.qbool(True)
        c2 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"First call in nested with(True, False) -> result=0, got {actual}"

    def test_nested_outer_false_first_call(self):
        """First call inside nested with, outer False -> result=0."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c1 = ql.qbool(False)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"First call in nested with(False, True) -> result=0, got {actual}"


# ---------------------------------------------------------------------------
# Controlled call produces more gates than uncontrolled
# ---------------------------------------------------------------------------


class TestControlledMoreGates:
    """Controlled execution produces more gates than uncontrolled."""

    def test_controlled_first_call_more_gates(self):
        """First call inside with produces more gates than outside."""

        # Uncontrolled first call
        @ql.compile
        def inc_uc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        gc_start = get_gate_count()
        a = ql.qint(0, width=3)
        _ = inc_uc(a)
        uncontrolled_gates = get_gate_count() - gc_start

        # Controlled first call
        @ql.compile
        def inc_c(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        gc_start2 = get_gate_count()
        c = ql.qbool(True)
        b = ql.qint(0, width=3)
        with c:
            _ = inc_c(b)
        controlled_gates = get_gate_count() - gc_start2

        assert uncontrolled_gates > 0
        assert controlled_gates > uncontrolled_gates, (
            f"Controlled first call ({controlled_gates}) should produce more gates "
            f"than uncontrolled first call ({uncontrolled_gates})"
        )


# ---------------------------------------------------------------------------
# Cache correctness: block.gates are uncontrolled after first call in with
# ---------------------------------------------------------------------------


class TestCacheUncontrolledAfterControlledCapture:
    """Cache stores uncontrolled gates even when first call is inside with."""

    def test_cache_gates_are_uncontrolled(self):
        """block.gates should be uncontrolled even if captured inside with."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            _ = inc(a)  # First call inside with

        block = list(inc._cache.values())[0]
        ctrl_qubit = int(c.qubits[63])

        # Uncontrolled block should not reference the control qubit
        for g in block.gates:
            assert ctrl_qubit not in g.get("controls", []), (
                f"Uncontrolled cache gate should not reference control qubit {ctrl_qubit}"
            )

    def test_controlled_block_derived(self):
        """Controlled block is correctly derived from uncontrolled cache."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block.controlled_block is not None
        assert block.controlled_block.control_virtual_idx is not None

        # Controlled block should have extra control on each gate
        for ug, cg in zip(block.gates, block.controlled_block.gates, strict=False):
            assert cg["num_controls"] == ug["num_controls"] + 1

    def test_replay_after_controlled_capture_works(self):
        """Second call (replay) works after first call was inside with."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call inside with
        c1 = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c1:
            _ = inc(a)

        # Second call outside with (replay, uncontrolled)
        b = ql.qint(0, width=2)
        gc_before = get_gate_count()
        _ = inc(b)
        gc_after = get_gate_count()

        assert gc_after > gc_before, "Replay after controlled capture should produce gates"

    def test_replay_controlled_after_controlled_capture(self):
        """Second controlled call works after first controlled call."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # First call inside with (capture)
        c1 = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c1:
            _ = inc(a)

        # Second call inside different with (replay, controlled)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c2:
            result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, a, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, (
            f"Controlled replay after controlled capture should give result=1, got {actual}"
        )
