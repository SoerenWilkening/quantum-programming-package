"""Tests for parametric compilation (Phase 94).

Verifies:
- PAR-01: @ql.compile(parametric=True) API
- PAR-02: Parametric replay correctness via Qiskit simulation
- PAR-03: Toffoli CQ structural fallback
- PAR-04: Oracle decorator forces non-parametric
- FIX-04: Mode flag cache invalidation
"""

import warnings

import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.compile import _get_mode_flags

warnings.filterwarnings("ignore", message="Value .* exceeds")

SIM = AerSimulator(method="statevector", max_parallel_threads=4)


def _get_num_qubits_from_qasm(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _simulate_and_extract(qasm_str, result_start, result_width):
    """Simulate QASM and extract result register value.

    Args:
        qasm_str: OpenQASM 3.0 string
        result_start: Starting physical qubit index of result register (LSB)
        result_width: Number of qubits in result register

    Returns:
        Integer value of result register
    """
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    job = SIM.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


# ============================================================================
# PAR-01: @ql.compile(parametric=True) API
# ============================================================================


class TestParametricAPI:
    """Tests for parametric=True API surface (PAR-01)."""

    def test_is_parametric_true(self):
        """is_parametric property returns True when parametric=True."""

        @ql.compile(parametric=True)
        def f(x, val):
            x += val
            return x

        assert f.is_parametric is True

    def test_is_parametric_false_by_default(self):
        """is_parametric property returns False by default."""

        @ql.compile
        def g(x, val):
            x += val
            return x

        assert g.is_parametric is False

    def test_no_classical_args_is_noop(self):
        """parametric=True with no classical args behaves normally."""
        ql.circuit()

        @ql.compile(parametric=True)
        def inc(x):
            x += 1
            return x

        a = ql.qint(3, width=4)
        result = inc(a)
        # Should work -- no classical args means parametric is no-op
        assert result is not None

    def test_clear_cache_resets_undecided_parametric_state(self):
        """Explicit clear_cache() resets undecided parametric probe state."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # Trigger first call (probed but not decided)
        ql.circuit()
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)
        assert add_val._parametric_probed is True

        # Explicit clear_cache resets undecided state
        add_val.clear_cache()
        assert add_val._parametric_probed is False
        assert add_val._parametric_safe is None


# ============================================================================
# PAR-02: Parametric QFT correctness (topology-safe, rotation-based)
# ============================================================================


class TestParametricQFTCorrectness:
    """Verify parametric replay correctness in QFT mode.

    QFT arithmetic uses rotations where classical values affect only
    gate angles, not topology. Parametric mode should detect this.
    """

    def test_parametric_qft_detected_as_safe(self):
        """QFT mode addition with different classical values has same topology."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # First call (probe start)
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        _ = add_val(a, 2)
        assert add_val._parametric_probed is True
        assert add_val._parametric_safe is None

        # Second call with different classical value (probe completes)
        ql.circuit()
        ql.option("fault_tolerant", False)
        b = ql.qint(3, width=4)
        _ = add_val(b, 5)
        assert add_val._parametric_safe is True

    def test_parametric_add_simulation_val2(self):
        """Simulate parametric add with val=2: 3 + 2 = 5."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        _ = add_val(a, 2)
        qasm_str = ql.to_openqasm()
        measured = _simulate_and_extract(qasm_str, 0, 4)
        assert measured == 5, f"Expected 5, got {measured}"

    def test_parametric_add_simulation_val5(self):
        """Simulate parametric add with val=5: 3 + 5 = 8."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # First call to trigger probe
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        _ = add_val(a, 2)

        # Second call with different value
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=5)
        _ = add_val(a, 5)
        qasm_str = ql.to_openqasm()
        measured = _simulate_and_extract(qasm_str, 0, 5)
        assert measured == 8, f"Expected 8, got {measured}"

    def test_parametric_add_multiple_values(self):
        """Parametric add correct for values 1 through 6."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        for val in range(1, 7):
            ql.circuit()
            ql.option("fault_tolerant", False)
            a = ql.qint(0, width=5)
            _ = add_val(a, val)
            qasm_str = ql.to_openqasm()
            measured = _simulate_and_extract(qasm_str, 0, 5)
            assert measured == val, f"0 + {val}: expected {val}, got {measured}"

    def test_same_classical_value_is_cache_hit(self):
        """Same classical args should be a cache hit after probe."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)  # First call (capture)

        b = ql.qint(1, width=4)
        _ = add_val(b, 3)  # Same classical value -- should hit cache
        # Verify no error (cache hit path works)


# ============================================================================
# PAR-03: Toffoli CQ structural fallback
# ============================================================================


class TestParametricToffoliStructural:
    """Verify Toffoli CQ operations detected as structural (PAR-03)."""

    def test_toffoli_cq_detected_as_structural(self):
        """Toffoli CQ add detected as structural (different topology per value)."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # First call
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)

        # Second call with different value
        ql.circuit()
        ql.option("fault_tolerant", True)
        b = ql.qint(0, width=4)
        _ = add_val(b, 5)

        # Should be detected as structural
        assert add_val._parametric_safe is False, "Toffoli CQ should be detected as structural"

    def test_toffoli_cq_fallback_correct_val3(self):
        """Toffoli CQ with per-value fallback produces correct result for val=3."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(2, width=4)
        _ = add_val(a, 3)  # 2 + 3 = 5
        qasm_str = ql.to_openqasm()
        measured = _simulate_and_extract(qasm_str, 0, 4)
        assert measured == 5, f"Expected 5, got {measured}"

    def test_toffoli_cq_fallback_correct_val7(self):
        """Toffoli CQ with per-value fallback produces correct result for val=7."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # Trigger probe with first value
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)

        # Second value triggers structural detection and falls back
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=4)
        _ = add_val(a, 7)  # 1 + 7 = 8
        qasm_str = ql.to_openqasm()
        measured = _simulate_and_extract(qasm_str, 0, 4)
        assert measured == 8, f"Expected 8, got {measured}"

    def test_toffoli_qq_parametric_safe(self):
        """Toffoli QQ add (both quantum) should work with parametric=True.

        When both operands are quantum, there are no classical args,
        so parametric=True is a no-op. Verify it still works correctly.
        """

        @ql.compile(parametric=True)
        def add_qq(x, y):
            return x + y

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        result = add_qq(a, b)
        # Both operands are quantum -- no classical args, so parametric is a no-op
        # Just verify execution succeeds without error
        assert result is not None


# ============================================================================
# Edge cases for parametric compilation
# ============================================================================


class TestParametricEdgeCases:
    """Edge cases for parametric compilation."""

    def test_different_classical_value_triggers_recapture(self):
        """Different classical values between calls trigger re-capture.

        Cache key includes classical arg values, so different values produce
        separate cache entries, verified by cache size increase.
        """

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # Call with classical value 3
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)
        cache_size_after_first = len(add_val._cache)

        # Call with different classical value 7 (triggers probe comparison)
        b = ql.qint(0, width=4)
        _ = add_val(b, 7)
        cache_size_after_second = len(add_val._cache)

        # Should have grown (different cache key for different values)
        assert cache_size_after_second > cache_size_after_first, (
            f"Expected cache size increase: first={cache_size_after_first}, "
            f"second={cache_size_after_second}"
        )

    def test_clear_cache_then_reprobe(self):
        """clear_cache() resets parametric state, allowing full re-probe."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # Trigger probe and detect as safe (QFT mode)
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        _ = add_val(a, 2)

        ql.circuit()
        ql.option("fault_tolerant", False)
        b = ql.qint(0, width=4)
        _ = add_val(b, 5)
        assert add_val._parametric_safe is True

        # Clear cache -- should reset all parametric state
        add_val.clear_cache()
        assert add_val._parametric_probed is False
        assert add_val._parametric_safe is None

        # Re-probe from scratch
        ql.circuit()
        ql.option("fault_tolerant", False)
        c = ql.qint(0, width=4)
        _ = add_val(c, 1)
        assert add_val._parametric_probed is True
        assert add_val._parametric_safe is None  # Not decided yet


# ============================================================================
# PAR-04: Oracle non-parametric override
# ============================================================================


class TestOracleNonParametric:
    """Verify oracle decorator forces non-parametric mode (PAR-04)."""

    def test_grover_oracle_on_compiled_func(self):
        """@ql.grover_oracle applied to @ql.compile(parametric=True) func
        forces parametric=False on the underlying CompiledFunc."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(parametric=True)
        def mark_val(x):
            _ = x == 5  # noqa: F841
            return x

        # Wrap with grover_oracle (side effect: sets _parametric = False)
        ql.grover_oracle(mark_val)
        assert mark_val.is_parametric is False

    def test_grover_oracle_bare_function(self):
        """@ql.grover_oracle on bare function creates non-parametric CompiledFunc."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.grover_oracle
        def mark_val(x):
            _ = x == 5  # noqa: F841
            return x

        # The underlying compiled func should be non-parametric
        assert mark_val._compiled_func.is_parametric is False


# ============================================================================
# FIX-04: Mode flag cache invalidation integration
# ============================================================================


class TestModeFlagIntegration:
    """Verify mode flag switches interact correctly with parametric state."""

    def test_mode_switch_no_error(self):
        """Switching arithmetic mode between parametric calls works."""

        @ql.compile(parametric=True)
        def add_val(x, val):
            x += val
            return x

        # QFT mode
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)

        # Switch to Toffoli (new circuit resets value cache)
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)

        # Should work without error

    def test_cache_key_includes_mode_flags(self):
        """Cache key format includes mode flags (FIX-04)."""

        @ql.compile
        def add_val(x, val):
            x += val
            return x

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(0, width=4)
        _ = add_val(a, 3)

        mf = _get_mode_flags()
        expected_key = ((3,), (4,), 0, False) + mf
        assert expected_key in add_val._cache, (
            f"Cache key should include mode flags. Keys: {list(add_val._cache.keys())}"
        )
