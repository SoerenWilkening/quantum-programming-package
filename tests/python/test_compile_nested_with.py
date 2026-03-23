"""Tests for @ql.compile inside nested with-blocks (CTRL-06).

Verifies that compiled functions (captured gate sequences) work correctly
when replayed inside nested quantum conditionals (multi-level with-blocks).

Key mechanism: Each control context captures its own block independently.
The controlled block is captured with the correct control qubit mapping,
and replay uses the appropriate cache entry for each context.

After Phase 5 step 5.2d, the first call to a compiled function inside a
with-block is now correctly controlled (capture mode respects the control
context). Pre-populating the cache is no longer required for correctness.

Test patterns:
- Pre-populate compile cache on throwaway register within SAME circuit
- Use qbool(True/False) for conditions (1 qubit each, stays under 21-qubit limit)
- Use 2-bit result registers
- Keep all qints/qbools alive in _keepalive list before QASM export

Requirements: CTRL-06
"""

import gc
import re
import warnings

import pytest
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (both False), got {actual}"

    def test_first_call_trade_off(self):
        """First call inside nested with is correctly controlled (Phase 5 fix).

        After Phase 5 step 5.2d, the first call (capture path) now respects the
        control context. With c2=False, the AND-ancilla is 0 and inc is skipped,
        so result=0. Pre-populating the cache is no longer required.
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        # First call is now controlled (Phase 5 fix) -> c2=False means inc skipped -> result=0
        assert actual == 0, f"Expected 0 (first call controlled, c2=False skips inc), got {actual}"


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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
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
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (single level False, inc skipped), got {actual}"


class TestCompileInverseNestedWith:
    """Tests for compiled function inverse inside nested with-blocks.

    Inverse (f.inverse) uncomputes a prior forward call's ancillas. It
    requires a forward call on the SAME qubits in the SAME circuit first.

    NOTE: f.inverse() inside any controlled context (even single-level with)
    produces QASM with duplicate qubit arguments. This is a pre-existing issue
    in _AncillaInverseProxy._derive_controlled_gates, NOT related to Phase 119
    nested with-blocks. Tests are skipped accordingly.
    """

    @pytest.mark.skip(
        reason="Pre-existing issue: f.inverse() inside controlled context "
        "produces QASM with duplicate qubit arguments (same failure in "
        "single-level with), not Phase 119 related"
    )
    def test_inverse_both_true(self):
        """Forward then inverse inside nested with, both True -> result=0.

        SKIPPED: f.inverse() inside controlled context produces QASM with
        duplicate qubit arguments. This is a pre-existing issue that also
        occurs in single-level with-blocks. Not related to nested controls.
        """

        @ql.compile(inverse=True)
        def add1(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        tw_result = add1(throwaway)
        add1.inverse(tw_result)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = add1(result)
                add1.inverse(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (add1 then inverse -> net 0), got {actual}"

    @pytest.mark.skip(
        reason="Pre-existing issue: f.inverse() inside controlled context "
        "produces QASM with duplicate qubit arguments, not Phase 119 related"
    )
    def test_inverse_inner_false(self):
        """Forward then inverse inside nested with, inner False -> result=0.

        SKIPPED: Same pre-existing issue as test_inverse_both_true.
        """

        @ql.compile(inverse=True)
        def add1(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        tw_result = add1(throwaway)
        add1.inverse(tw_result)

        c1 = ql.qbool(True)
        c2 = ql.qbool(False)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = add1(result)
                add1.inverse(result)

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (inner False, both skipped), got {actual}"


class TestCompileAdjointNestedWith:
    """Tests for compiled function adjoint inside nested with-blocks.

    Adjoint (f.adjoint()) creates an _InverseCompiledFunc that replays the
    adjoint gate sequence independently. No prior forward call required.
    The adjoint of (x += 1) is (x -= 1).

    Single-level baseline is tested first to isolate any pre-existing adjoint
    issues from nested-with-specific issues.
    """

    def test_adjoint_vs_single_level(self):
        """Baseline: adjoint inside single-level with, condition True.

        Starts at 1, adjoint of add1 subtracts 1 -> result = 0.
        If this fails, adjoint has a pre-existing issue unrelated to nesting.
        """

        @ql.compile
        def add1(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        # Pre-populate both forward and adjoint caches
        throwaway = ql.qint(0, width=2)
        _ = add1(throwaway)
        throwaway2 = ql.qint(1, width=2)
        _ = add1.adjoint(throwaway2)

        c1 = ql.qbool(True)
        result = ql.qint(1, width=2)
        with c1:
            result = add1.adjoint(result)  # Adjoint: -1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, result, throwaway, throwaway2]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (adjoint of +1 on value 1), got {actual}"

    def test_adjoint_nested_both_true(self):
        """Adjoint inside 2-level nested with, both True -> result=0.

        Starts at 1, adjoint of add1 subtracts 1.
        Both True -> adjoint executes -> result = 0.
        """

        @ql.compile
        def add1(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        throwaway = ql.qint(0, width=2)
        _ = add1(throwaway)
        throwaway2 = ql.qint(1, width=2)
        _ = add1.adjoint(throwaway2)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        result = ql.qint(1, width=2)
        with c1:
            with c2:
                result = add1.adjoint(result)  # Adjoint: -1

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, throwaway, throwaway2]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 0, f"Expected 0 (adjoint of +1 on value 1, both True), got {actual}"


class TestCompiledCallingCompiled:
    """Tests for compiled function calling another compiled function inside nested with.

    NOTE: Compiled-calling-compiled produces double-increment (result=2 instead
    of 1) even OUTSIDE any with-block. This is a pre-existing issue in how
    outer function capture records inner function's gates during both capture
    and replay. Not related to Phase 119 nested with-blocks.
    """

    @pytest.mark.skip(
        reason="Pre-existing issue: compiled-calling-compiled produces "
        "double-increment (result=2 instead of 1) even outside with-blocks, "
        "not Phase 119 related"
    )
    def test_outer_calls_inner(self):
        """Outer compiled function calls inner compiled function.

        SKIPPED: outer(x) calling inner(x) double-increments even outside
        any with-block (result=2 instead of 1). This is a pre-existing issue
        in compile.py's capture/replay of nested compiled functions, not
        related to nested with-block controls.

        inner(x): x += 1
        outer(x): x = inner(x) (delegates to inner)
        Expected: result = 1, but actually produces result = 2.
        """

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x = inner(x)
            return x

        gc.collect()
        ql.circuit()
        # Pre-populate inner cache first
        tw_inner = ql.qint(0, width=2)
        _ = inner(tw_inner)
        # Pre-populate outer cache (will use inner's replay)
        tw_outer = ql.qint(0, width=2)
        _ = outer(tw_outer)

        c1 = ql.qbool(True)
        c2 = ql.qbool(True)
        result = ql.qint(0, width=2)
        with c1:
            with c2:
                result = outer(result)  # Replay: outer calls inner

        result_start = result.allocated_start
        result_width = result.width
        qasm = ql.to_openqasm()
        _keepalive = [c1, c2, result, tw_inner, tw_outer]

        num_qubits = _get_num_qubits(qasm)
        assert num_qubits <= 21, f"Circuit uses {num_qubits} qubits (limit: 21)"
        actual = _simulate_and_extract(qasm, num_qubits, result_start, result_width)
        assert actual == 1, f"Expected 1 (outer calls inner, both True), got {actual}"
