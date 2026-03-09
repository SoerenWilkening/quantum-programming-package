"""Tests for @ql.compile inside nested with-blocks (CTRL-06).

Verifies that compiled functions (captured gate sequences) work correctly
when replayed inside nested quantum conditionals (multi-level with-blocks).

Key mechanism: During replay, compile.py maps block.control_virtual_idx to
_get_control_bool().qubits[63], which is the AND-ancilla qubit in nested
contexts. This means replayed gates are automatically controlled on the
combined condition (outer AND inner).

Trade-off: The first call to a compiled function inside a with-block always
emits uncontrolled gates (capture mode). Only subsequent calls (replay path)
are correctly controlled. This is documented behavior, not a bug.

Test patterns:
- Pre-populate compile cache on throwaway register within SAME circuit
- Use qbool(True/False) for conditions (1 qubit each, stays under 17-qubit limit)
- Use 2-bit result registers
- Keep all qints/qbools alive in _keepalive list before QASM export

Requirements: CTRL-06
"""

import gc
import re
import warnings

import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


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


class TestCompileNestedWith:
    """Tests for compiled function replay inside 2-level nested with-blocks.

    Verifies that @ql.compile captured functions work correctly when
    replayed inside nested quantum conditionals. The compile cache must
    be pre-populated on a throwaway register within the SAME circuit
    (ql.circuit() clears the cache).

    Qubit budget (2-level): 2 conds + 2 AND-ancilla + 2 result + 2 throwaway
    + ~4 internal = ~12 qubits (well under 17).
    """

    def test_replay_both_true(self):
        """Compiled inc(x) replayed inside nested with, both True -> result=1.

        Pre-populate cache on throwaway, then replay inside:
        with c1(True): with c2(True): result = inc(result)
        Both conditions True -> AND-ancilla = 1 -> inc executes -> result = 1.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)  # Pre-populate cache

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)  # REPLAY path

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (both True, inc executes), got {actual}"

    def test_replay_inner_false(self):
        """Compiled inc(x) replayed inside nested with, inner False -> result=0.

        with c1(True): with c2(False): result = inc(result)
        c2=False -> AND-ancilla = 0 -> inc skipped -> result = 0.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(True)
        c2 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (inner False, inc skipped), got {actual}"

    def test_replay_outer_false(self):
        """Compiled inc(x) replayed inside nested with, outer False -> result=0.

        with c1(False): with c2(True): result = inc(result)
        c1=False -> outer blocks all -> result = 0.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(False)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (outer False, all blocked), got {actual}"

    def test_replay_both_false(self):
        """Compiled inc(x) replayed inside nested with, both False -> result=0.

        with c1(False): with c2(False): result = inc(result)
        Both False -> result = 0.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(False)
        c2 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (both False), got {actual}"

    def test_first_call_trade_off(self):
        """First call inside nested with emits uncontrolled gates (known trade-off).

        When the compile cache is empty, the first call captures in uncontrolled
        mode (compile.py:1204-1210). Gates emitted during capture are NOT
        controlled, so result=1 even though c2=False. This is documented and
        accepted behavior that also applies to single-level with blocks.

        This test documents the trade-off, not a bug.
        """

        @ql.compile
        def inc_fresh(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        # NO cache pre-population -- first call inside nested with
        c1 = ql.qbool(True)
        c2 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = inc_fresh(result)  # First call: capture path

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        # First call emits uncontrolled gates -> result=1 even though c2=False
        assert actual == 1, f"Expected 1 (first-call trade-off: uncontrolled capture), got {actual}"


class TestCompileThreeLevelSmoke:
    """Smoke tests for compiled function replay inside 3-level nested with.

    Verifies AND-composition chains at depth 3: outer AND middle AND inner.
    Qubit budget: 3 conds + 3 AND-ancillas + 2 result + 2 throwaway + ~4 = ~14.
    """

    def test_three_level_all_true(self):
        """Compiled inc replayed at 3-level depth, all True -> result=1.

        with c1(True): with c2(True): with c3(True): result = inc(result)
        All True -> all AND-ancillas = 1 -> inc executes -> result = 1.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        c3 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                with c3:
                    result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, c3, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (all True, inc executes), got {actual}"

    def test_three_level_inner_false(self):
        """Compiled inc replayed at 3-level depth, innermost False -> result=0.

        with c1(True): with c2(True): with c3(False): result = inc(result)
        c3=False -> innermost AND-ancilla = 0 -> inc skipped -> result = 0.
        """

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        c3 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                with c3:
                    result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, c3, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (innermost False, inc skipped), got {actual}"


class TestCompileSingleLevelRegression:
    """Regression tests: compiled function inside single-level with-block.

    Ensures the non-nested path is not broken by any nested controls changes.
    """

    def test_single_level_true(self):
        """Compiled inc inside single with, condition True -> result=1."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (single level True, inc executes), got {actual}"

    def test_single_level_false(self):
        """Compiled inc inside single with, condition False -> result=0."""

        @ql.compile
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = inc(throwaway)

        c1 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            result = inc(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 17, f"Circuit uses {num_qubits} qubits (limit: 17)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (single level False, inc skipped), got {actual}"
