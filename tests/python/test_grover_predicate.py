"""Phase 80: Predicate Synthesis and Adaptive Search Tests.

Tests covering:
- SYNTH-01: Lambda predicate oracles (simple, compound, closure)
- SYNTH-02: Compound predicates with & operator
- SYNTH-03: Predicate oracles with existing qint comparison operators
- ADAPT-01: BBHT adaptive search for unknown solution count
- ADAPT-02: Adaptive search termination and classical verification

Note: Oracle pattern uses `with flag: x.phase += math.pi` for phase marking.
The `with flag: pass` pattern is a no-op (comparison compute+uncompute cancel).

Note: All six comparison operators (==, !=, <, >, <=, >=) are supported.
BUG-CMP-MSB (hardcoded qubit index 63 for MSB in inequality operators)
was fixed in Phase 80 Plan 03.  Inequality predicate tests close
verification gaps SYNTH-01, SYNTH-02, and SYNTH-03.
"""

import math

import pytest

import quantum_language as ql
from quantum_language.grover import _verify_classically


# ---------------------------------------------------------------------------
# Group 1: Predicate Synthesis Tests (SYNTH-01, SYNTH-02, SYNTH-03)
# ---------------------------------------------------------------------------
class TestPredicateSynthesis:
    """Tests for lambda/callable predicate-to-oracle synthesis."""

    def test_lambda_predicate_simple(self):
        """Lambda x == 3 in 2-bit space. N=4, M=1, k=1 -> exact P=1.0.

        SYNTH-01: User can pass Python predicate lambda as oracle.
        """
        value, iters = ql.grover(lambda x: x == 3, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1

    def test_lambda_predicate_equality_different_target(self):
        """Lambda x == 2 in 2-bit space. N=4, M=1, k=1 -> exact P=1.0.

        SYNTH-03: Predicate oracles work with existing qint comparison operators.
        """
        value, iters = ql.grover(lambda x: x == 2, width=2, m=1)
        assert value == 2, f"Expected 2, got {value}"
        assert iters == 1

    def test_lambda_predicate_not_equal(self):
        """Lambda x != 0 in 2-bit space. M=3 (values 1, 2, 3).

        SYNTH-03: Predicate oracles work with != operator.
        Run 10 trials, expect >= 5 valid hits.
        """
        valid_count = 0
        for _ in range(10):
            value, iters = ql.grover(lambda x: x != 0, width=2, m=3)
            if value != 0:
                valid_count += 1
        assert valid_count >= 5, f"Expected >=5/10 valid hits, got {valid_count}"

    def test_compound_predicate_and(self):
        """Compound predicate (x != 0) & (x != 3) in 2-bit space.

        SYNTH-02: Compound predicates compile to valid oracles.
        M=2 solutions: {1, 2}.
        """
        valid_count = 0
        for _ in range(10):
            value, iters = ql.grover(lambda x: (x != 0) & (x != 3), width=2, m=2)
            if value in {1, 2}:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/10 valid hits, got {valid_count}"

    def test_lambda_with_closure(self):
        """Closure capturing classical value.

        SYNTH-01: Support closures capturing classical values.
        target = 3; lambda x: x == target finds value 3.
        """
        target = 3
        value, iters = ql.grover(lambda x: x == target, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"

    def test_lambda_closure_different_values(self):
        """Two closures with different captured values produce different oracles.

        SYNTH-01: Closure variable values in cache key.
        t1=2 -> finds value == 2. t2=1 -> finds value == 1.
        """
        t1 = 2
        result1 = ql.grover(lambda x: x == t1, width=2, m=1)
        assert result1[0] == 2, f"Expected value 2, got {result1[0]}"

        t2 = 1
        result2 = ql.grover(lambda x: x == t2, width=2, m=1)
        assert result2[0] == 1, f"Expected value 1, got {result2[0]}"

    def test_named_function_predicate(self):
        """Named function (not lambda) works as predicate.

        SYNTH-01: Accept any callable predicate -- lambdas, named functions.
        """

        def pred(x):
            return x == 3

        value, iters = ql.grover(pred, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"

    def test_predicate_non_qbool_error(self):
        """Predicate returning Python bool raises clear TypeError.

        SYNTH-03: Error handling for non-quantum return types.
        """
        with pytest.raises(TypeError, match="quantum type"):
            ql.grover(lambda x: True, width=2, m=1)

    # --- Inequality predicate tests (Phase 80 Plan 03, BUG-CMP-MSB fix) ---

    def test_lambda_predicate_greater_than(self):
        """Lambda x > 1 in 3-bit space (N=8, M=6).

        SYNTH-01 gap closure: inequality operator > in predicate oracle.
        Uses adaptive path for reliable convergence with high M/N ratio.
        Run 5 trials, at least 3 should find a valid solution.
        """
        valid_count = 0
        for _ in range(5):
            result = ql.grover(lambda x: x > 1, width=3)
            if result is not None and result[0] > 1:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/5 valid hits, got {valid_count}"

    def test_lambda_predicate_less_than(self):
        """Lambda x < 2 in 3-bit space (N=8, M=2).

        SYNTH-03 gap closure: inequality operator < in predicate oracle.
        M/N=0.25 gives optimal k=1 iteration with high success probability.
        """
        valid_count = 0
        for _ in range(5):
            result = ql.grover(lambda x: x < 2, width=3, m=1)
            if result is not None and result[0] < 2:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/5 valid hits, got {valid_count}"

    def test_lambda_predicate_greater_equal(self):
        """Lambda x >= 2 in 3-bit space (N=8, M=6).

        SYNTH-03 gap closure: inequality operator >= in predicate oracle.
        Uses adaptive path for reliable convergence with high M/N ratio.
        """
        valid_count = 0
        for _ in range(5):
            result = ql.grover(lambda x: x >= 2, width=3)
            if result is not None and result[0] >= 2:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/5 valid hits, got {valid_count}"

    def test_lambda_predicate_less_equal(self):
        """Lambda x <= 1 in 3-bit space (N=8, M=2).

        SYNTH-03 gap closure: inequality operator <= in predicate oracle.
        M/N=0.25 gives optimal k=1 iteration with high success probability.
        """
        valid_count = 0
        for _ in range(5):
            result = ql.grover(lambda x: x <= 1, width=3, m=1)
            if result is not None and result[0] <= 1:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/5 valid hits, got {valid_count}"

    def test_compound_predicate_inequality_and(self):
        """Compound predicate (x > 0) & (x < 3) in 2-bit space.

        SYNTH-02 gap closure: compound inequality predicate with & operator.
        M=2 (values {1, 2}). Two inequality comparisons plus AND.
        Uses adaptive path for reliable convergence with compound predicates.
        Run 5 trials, at least 3 should find a valid solution.
        """
        valid_count = 0
        for _ in range(5):
            result = ql.grover(lambda x: (x > 0) & (x < 3), width=2)
            if result is not None and result[0] in {1, 2}:
                valid_count += 1
        assert valid_count >= 3, f"Expected >=3/5 valid hits, got {valid_count}"


# ---------------------------------------------------------------------------
# Group 2: Adaptive Search Tests (ADAPT-01, ADAPT-02)
# ---------------------------------------------------------------------------
class TestAdaptiveSearch:
    """Tests for BBHT adaptive Grover search."""

    def test_adaptive_finds_solution(self):
        """Adaptive search (no m=) finds x == 3 in 2-bit space.

        ADAPT-01: When M is unknown, Grover uses BBHT strategy.
        N=4, only 1 solution. Classical verification ensures correctness.
        Run up to 5 times to account for probabilistic nature.
        """
        found = False
        for _ in range(5):
            result = ql.grover(lambda x: x == 3, width=2)
            if result is not None and result[0] == 3:
                found = True
                break
        assert found, "Adaptive search failed to find x=3 in 5 attempts"

    def test_adaptive_returns_iterations(self):
        """Return format is (value, total_iterations) with total >= 0.

        ADAPT-01: Same return format for both adaptive and exact paths.
        """
        # Use 2-bit space with == 3 (1 solution out of 4)
        # Run multiple attempts to handle probabilistic nature
        result = None
        for _ in range(5):
            result = ql.grover(lambda x: x == 3, width=2)
            if result is not None:
                break
        assert result is not None, "Expected a result within 5 attempts"
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2, f"Expected 2 elements, got {len(result)}"
        assert result[1] >= 0, f"Expected non-negative iterations, got {result[1]}"

    def test_adaptive_with_max_attempts(self):
        """max_attempts limits the search.

        ADAPT-02: User can set max_attempts parameter.
        Use generous max_attempts to ensure success.
        """
        # 2-bit space, 1 solution out of 4. With max_attempts=20, should find it.
        result = ql.grover(lambda x: x == 3, width=2, max_attempts=20)
        assert result is not None, "Expected a result with max_attempts=20"
        assert result[0] == 3, f"Expected value 3, got {result[0]}"

    def test_adaptive_returns_none_when_no_solution(self):
        """Oracle that has no valid solutions returns None.

        ADAPT-02: Adaptive search terminates when search space exhausted.
        x == 255 in 3-bit space (0-7) has no solutions. Classical
        verification rejects all measurements.
        """
        result = ql.grover(lambda x: x == 255, width=3, max_attempts=1)
        assert result is None, f"Expected None, got {result}"

    def test_adaptive_returns_none_no_solution_more_attempts(self):
        """Oracle with no valid solutions returns None even with more attempts.

        ADAPT-02: max_attempts bound ensures termination.
        x == 100 in 3-bit space (0-7) has no solutions.
        """
        result = ql.grover(lambda x: x == 100, width=3, max_attempts=5)
        assert result is None, f"Expected None, got {result}"

    def test_adaptive_classical_verification(self):
        """Classical verification correctly accepts/rejects measurements.

        ADAPT-02: Always verify found results.
        Unit test _verify_classically directly.
        """
        # Single-register predicates
        assert _verify_classically(lambda x: x > 5, (7,)) is True
        assert _verify_classically(lambda x: x > 5, (3,)) is False
        assert _verify_classically(lambda x: x == 3, (3,)) is True
        assert _verify_classically(lambda x: x == 3, (2,)) is False

        # Multi-register predicates
        assert _verify_classically(lambda x, y: x + y == 10, (6, 4)) is True
        assert _verify_classically(lambda x, y: x + y == 10, (3, 4)) is False

    def test_exact_path_still_works_with_m(self):
        """Exact path (m= provided) with lambda predicate.

        Verify exact iteration count is used and value is correct.
        """
        value, iters = ql.grover(lambda x: x == 3, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1, f"Expected 1 iteration, got {iters}"


# ---------------------------------------------------------------------------
# Group 3: Backwards Compatibility Tests
# ---------------------------------------------------------------------------
class TestBackwardsCompatibility:
    """Tests verifying existing oracle patterns still work unchanged."""

    def test_decorated_oracle_still_works(self):
        """Existing decorated oracle pattern unchanged.

        Copy of test_grover_single_solution_2bit from test_grover.py.
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_three, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1

    def test_compiled_func_auto_wrap(self):
        """@ql.compile function auto-wrapped as oracle.

        Same pattern as existing test_grover_auto_wrap_compiled_func.
        """

        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_three, width=2, m=1)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1
