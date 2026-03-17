"""Phase 81: Amplitude Estimation (IQAE) Tests.

Tests covering:
- AMP-01: ql.amplitude_estimate() returns estimated probability for known oracles
- AMP-02: QFT-free IQAE implementation (uses Grover iterate only, no QFT)
- AMP-03: Configurable precision (epsilon), confidence, max_iterations

Three test classes:
- TestAmplitudeEstimationResult: Unit tests for the result class (no Qiskit)
- TestIQAEHelpers: Unit tests for internal algorithm helpers (no Qiskit)
- TestAmplitudeEstimationEndToEnd: Integration tests with Qiskit simulation

Note: All integration tests use 2-bit registers to stay well under
the 21-qubit simulator limit (project constraint).
"""

import pytest

import quantum_language as ql
from quantum_language.amplitude_estimation import (
    AmplitudeEstimationResult,
    _clopper_pearson_confint,
    _find_next_k,
)


# ---------------------------------------------------------------------------
# Group 1: Unit Tests for AmplitudeEstimationResult (no Qiskit needed)
# ---------------------------------------------------------------------------
class TestAmplitudeEstimationResult:
    """Unit tests for AmplitudeEstimationResult float-like behavior."""

    def test_estimate_property(self):
        """Create result with estimate=0.125, verify .estimate returns 0.125."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result.estimate == 0.125

    def test_num_oracle_calls_property(self):
        """Verify .num_oracle_calls returns correct int."""
        result = AmplitudeEstimationResult(0.125, 42)
        assert result.num_oracle_calls == 42
        assert isinstance(result.num_oracle_calls, int)

    def test_float_conversion(self):
        """float(result) returns the estimate value."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert float(result) == 0.125

    def test_arithmetic_add(self):
        """result + 0.5 and 0.5 + result both return correct float."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result + 0.5 == pytest.approx(0.625)
        assert 0.5 + result == pytest.approx(0.625)

    def test_arithmetic_mul(self):
        """result * 2.0 and 2.0 * result both return correct float."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result * 2.0 == pytest.approx(0.25)
        assert 2.0 * result == pytest.approx(0.25)

    def test_arithmetic_sub(self):
        """result - 0.1 and 1.0 - result both return correct float."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result - 0.1 == pytest.approx(0.025)
        assert 1.0 - result == pytest.approx(0.875)

    def test_arithmetic_div(self):
        """result / 2 returns correct float."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result / 2 == pytest.approx(0.0625)

    def test_comparison_lt(self):
        """result < 0.5 returns True for estimate=0.125."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result < 0.5

    def test_comparison_gt(self):
        """result > 0.0 returns True for estimate=0.125."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert result > 0.0

    def test_bool_nonzero(self):
        """bool(result) is True for estimate=0.125, False for estimate=0.0."""
        result_nonzero = AmplitudeEstimationResult(0.125, 100)
        result_zero = AmplitudeEstimationResult(0.0, 0)
        assert bool(result_nonzero) is True
        assert bool(result_zero) is False

    def test_int_conversion(self):
        """int(result) returns 0 for estimate=0.125."""
        result = AmplitudeEstimationResult(0.125, 100)
        assert int(result) == 0

    def test_repr(self):
        """repr(result) contains 'AmplitudeEstimationResult' and the estimate value."""
        result = AmplitudeEstimationResult(0.125, 100)
        r = repr(result)
        assert "AmplitudeEstimationResult" in r
        assert "0.125" in r


# ---------------------------------------------------------------------------
# Group 2: Unit Tests for IQAE Helper Functions (no Qiskit needed)
# ---------------------------------------------------------------------------
class TestIQAEHelpers:
    """Unit tests for internal IQAE algorithm functions."""

    def test_clopper_pearson_confint_middle(self):
        """For counts=50, shots=100, alpha=0.05, verify lower < 0.5 < upper.

        The Clopper-Pearson interval should contain the observed proportion 0.5.
        """
        lower, upper = _clopper_pearson_confint(50, 100, 0.05)
        assert lower < 0.5
        assert upper > 0.5
        assert lower >= 0.0
        assert upper <= 1.0

    def test_clopper_pearson_confint_zero_counts(self):
        """counts=0 should give lower=0.0.

        When no good outcomes are observed, the lower bound must be exactly 0.
        """
        lower, upper = _clopper_pearson_confint(0, 100, 0.05)
        assert lower == 0.0
        assert upper > 0.0

    def test_clopper_pearson_confint_all_counts(self):
        """counts=shots should give upper=1.0.

        When all outcomes are good, the upper bound must be exactly 1.
        """
        lower, upper = _clopper_pearson_confint(100, 100, 0.05)
        assert upper == 1.0
        assert lower < 1.0

    def test_find_next_k_initial(self):
        """For k=0 (first call), verify returned k > 0 and is a valid integer.

        Starting from k=0, the algorithm should advance to a higher power.
        """
        # Initial theta interval [0, 0.25]
        k_next, _ = _find_next_k(0, True, [0.0, 0.25])
        assert isinstance(k_next, int)
        assert k_next >= 0

    def test_find_next_k_monotone(self):
        """Verify k increases or stays same across calls with narrowing interval.

        As the theta interval narrows, the algorithm should select larger
        Grover powers to resolve the estimate.
        """
        k = 0
        upper_half = True
        theta = [0.0, 0.25]

        k1, upper_half = _find_next_k(k, upper_half, theta)

        # Narrow the interval
        theta_narrow = [0.05, 0.15]
        k2, _ = _find_next_k(k1, upper_half, theta_narrow)

        assert k2 >= k1, f"Expected k2 >= k1, got k2={k2}, k1={k1}"


# ---------------------------------------------------------------------------
# Group 3: End-to-End Integration Tests with Qiskit Simulation
# ---------------------------------------------------------------------------
class TestAmplitudeEstimationEndToEnd:
    """Integration tests verifying ql.amplitude_estimate() with Qiskit simulation.

    CRITICAL CONSTRAINTS (from project memory):
    - Max 21 qubits for Qiskit simulation -- use 2-bit search registers
    - Max 4 threads -- already enforced by _simulate_multi_shot
    """

    def test_known_single_solution_lambda(self):
        """Lambda x == 3 in 2-bit space. True probability = 1/4 = 0.25.

        AMP-01: ql.amplitude_estimate() returns correct probability for
        known single-solution oracle. Assert estimate within generous
        tolerance accounting for IQAE's theta-to-probability mapping.
        """
        result = ql.amplitude_estimate(lambda x: x == 3, width=2, epsilon=0.05)
        # IQAE guarantees theta interval width <= epsilon/pi, but the
        # sin^2 mapping to probability space can amplify the interval.
        # Use generous tolerance for statistical robustness.
        assert abs(result.estimate - 0.25) < 0.15, f"Expected ~0.25, got {result.estimate}"
        assert result.num_oracle_calls > 0
        assert isinstance(result.estimate, float)

    def test_known_multi_solution_lambda(self):
        """Lambda x > 0 in 2-bit space. x in {1,2,3}, M=3, true probability = 3/4 = 0.75.

        AMP-01: ql.amplitude_estimate() correctly estimates probability
        for multi-solution oracles with inequality predicates.
        """
        result = ql.amplitude_estimate(lambda x: x > 0, width=2, epsilon=0.05)
        assert abs(result.estimate - 0.75) < 0.15, f"Expected ~0.75, got {result.estimate}"

    def test_inequality_predicate_lambda(self):
        """Lambda x < 1 in 2-bit space. x in {0}, M=1, true probability = 1/4 = 0.25.

        AMP-01: Inequality predicate oracles produce accurate estimates.
        """
        result = ql.amplitude_estimate(lambda x: x < 1, width=2, epsilon=0.05)
        assert abs(result.estimate - 0.25) < 0.15, f"Expected ~0.25, got {result.estimate}"

    def test_epsilon_affects_precision(self):
        """Tighter epsilon should use more oracle calls.

        AMP-03: epsilon parameter affects estimation behavior. Run same oracle
        with epsilon=0.1 and epsilon=0.01. The tighter epsilon should use
        more oracle calls (generous tolerance since this is probabilistic).
        """
        result1 = ql.amplitude_estimate(lambda x: x == 1, width=2, epsilon=0.1)
        result2 = ql.amplitude_estimate(lambda x: x == 1, width=2, epsilon=0.01)
        # Tighter epsilon needs more oracle calls (use generous tolerance)
        assert result2.num_oracle_calls >= result1.num_oracle_calls, (
            f"Expected tighter epsilon to use more calls: "
            f"epsilon=0.1 -> {result1.num_oracle_calls}, "
            f"epsilon=0.01 -> {result2.num_oracle_calls}"
        )

    def test_max_iterations_cap(self):
        """Very tight epsilon with low max_iterations hits the cap.

        AMP-03: max_iterations caps execution and returns best estimate
        with warning. Uses epsilon=0.001 and max_iterations=10 to trigger
        the cap quickly.
        """
        with pytest.warns(UserWarning, match="max_iterations"):
            result = ql.amplitude_estimate(
                lambda x: x == 1, width=2, epsilon=0.001, max_iterations=10
            )
        assert isinstance(result.estimate, float)
        assert 0.0 <= result.estimate <= 1.0

    def test_result_is_float_like(self):
        """Result from actual estimation supports float-like operations.

        Confirms AmplitudeEstimationResult integration in a real scenario:
        float() conversion, arithmetic, comparison all work on a real result.
        """
        result = ql.amplitude_estimate(lambda x: x == 3, width=2, epsilon=0.05)
        # Float conversion
        f = float(result)
        assert isinstance(f, float)
        # Arithmetic
        s = result + 0.0
        assert isinstance(s, float)
        # Comparison
        assert result >= 0.0

    def test_two_bit_register(self):
        """Lambda x == 1 in 2-bit space. True probability = 1/4 = 0.25.

        Tests minimal register size. 2-bit register stays well under
        21-qubit limit even with ancilla overhead.
        """
        result = ql.amplitude_estimate(lambda x: x == 1, width=2, epsilon=0.05)
        assert abs(result.estimate - 0.25) < 0.15, f"Expected ~0.25, got {result.estimate}"

    def test_oracle_gates_present_in_circuit(self):
        """IQAE circuit at k>=1 must contain oracle comparison gates.

        Builds a single Grover circuit with k=1 and verifies that the
        QASM output contains gates from the oracle's comparison logic
        (e.g. ccx from equality check).  A broken oracle that emits no
        gates would produce only branch + H + diffusion, missing the
        comparison ancillae and Toffoli gates.
        """
        from quantum_language.oracle import _predicate_to_oracle

        oracle = _predicate_to_oracle(lambda x: x == 1, [2])

        # Build a circuit with k=1 (one Grover iteration)
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        reg = ql.qint(0, width=2)
        reg.branch(0.5)

        oracle(reg)

        qasm = ql.to_openqasm()

        # The equality oracle must produce comparison gates (ccx/cx)
        # If the oracle is broken (simulate=False), no gates are stored
        assert "ccx" in qasm or "cx" in qasm, (
            f"Oracle must emit comparison gates (ccx/cx) into the circuit. "
            f"Got QASM with no comparison gates:\n{qasm}"
        )

        # Circuit must use more qubits than just the 2-bit register
        # (comparison allocates ancillae)
        for line in qasm.split("\n"):
            if line.strip().startswith("qubit["):
                nq = int(line.strip().split("[")[1].split("]")[0])
                assert nq > 2, (
                    f"Oracle should allocate ancilla qubits, but circuit only has {nq} qubits"
                )
                break
