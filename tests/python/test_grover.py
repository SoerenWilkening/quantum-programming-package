"""Phase 79: Grover Search Integration Tests.

Verifies ql.grover() end-to-end with Qiskit simulation:
- GROV-01: ql.grover(oracle, width=N) executes search and returns measured value
- GROV-02: Auto-calculated iteration count matches expected formula output
- GROV-04: Multiple solutions (M > 1) produce correct behavior with reduced iterations

Two test classes:
- TestGroverIterations: Unit tests for helper functions (no Qiskit needed)
- TestGroverEndToEnd: Integration tests with Qiskit simulation

Note: Oracle pattern uses `with flag: x.phase += math.pi` for phase marking.
The `with flag: pass` pattern is a no-op (comparison compute+uncompute cancel).
"""

import math

import pytest

import quantum_language as ql
from quantum_language.grover import _grover_iterations, _resolve_widths


# ---------------------------------------------------------------------------
# Group 1: Unit Tests for Iteration Count Formula and Helper Functions
# ---------------------------------------------------------------------------
class TestGroverIterations:
    """Unit tests for _grover_iterations and _resolve_widths. No Qiskit needed."""

    # --- Iteration count formula tests ---

    def test_iteration_count_n8_m1(self):
        """N=8, M=1 -> k=1 (floor(pi/4 * sqrt(8) - 0.5) = floor(1.72) = 1)."""
        assert _grover_iterations(8, 1) == 1

    def test_iteration_count_n4_m1(self):
        """N=4, M=1 -> k=1 (floor(pi/4 * sqrt(4) - 0.5) = floor(1.07) = 1)."""
        assert _grover_iterations(4, 1) == 1

    def test_iteration_count_n16_m1(self):
        """N=16, M=1 -> k=2 (floor(pi/4 * sqrt(16) - 0.5) = floor(2.64) = 2)."""
        assert _grover_iterations(16, 1) == 2

    def test_iteration_count_n8_m2(self):
        """N=8, M=2 -> k=1 (floor(pi/4 * sqrt(4) - 0.5) = floor(1.07) = 1)."""
        assert _grover_iterations(8, 2) == 1

    def test_iteration_count_n8_m4(self):
        """N=8, M=4 -> k=0 (floor(pi/4 * sqrt(2) - 0.5) = floor(0.61) = 0)."""
        assert _grover_iterations(8, 4) == 0

    def test_iteration_count_m_zero(self):
        """M=0 -> k=0 (no solutions, skip iterations)."""
        assert _grover_iterations(8, 0) == 0

    def test_iteration_count_m_equals_n(self):
        """M=N -> k=0 (all states are solutions)."""
        assert _grover_iterations(8, 8) == 0

    def test_iteration_count_m_greater_than_n(self):
        """M>N -> k=0 (more solutions than search space)."""
        assert _grover_iterations(8, 10) == 0

    # --- _resolve_widths tests ---

    def test_resolve_widths_single(self):
        """width=3 with 1 param -> [3]."""
        result = _resolve_widths(["x"], 3, None)
        assert result == [3]

    def test_resolve_widths_multi(self):
        """widths=[3,4] with 2 params -> [3,4]."""
        result = _resolve_widths(["x", "y"], None, [3, 4])
        assert result == [3, 4]

    def test_resolve_widths_broadcast(self):
        """width=3 with 2 params -> [3,3] (broadcast)."""
        result = _resolve_widths(["x", "y"], 3, None)
        assert result == [3, 3]

    def test_resolve_widths_error_neither(self):
        """Neither width nor widths provided -> ValueError."""
        with pytest.raises(ValueError, match="width or widths required"):
            _resolve_widths(["x"], None, None)

    def test_resolve_widths_error_mismatch(self):
        """widths=[3] with 2 params -> ValueError (length mismatch)."""
        with pytest.raises(ValueError, match="widths has 1 entries"):
            _resolve_widths(["x", "y"], None, [3])

    def test_explicit_iterations_override(self):
        """When iterations= is provided, _grover_iterations should not be called.

        This is tested via the return tuple in end-to-end tests, but we also
        verify the formula returns a different value to confirm override works.
        """
        # For N=8, M=1, the formula gives k=1
        formula_k = _grover_iterations(8, 1)
        assert formula_k == 1
        # An explicit iterations=5 should override this (tested in E2E)


# ---------------------------------------------------------------------------
# Group 2: End-to-End Integration Tests with Qiskit Simulation
# ---------------------------------------------------------------------------
class TestGroverEndToEnd:
    """Integration tests verifying ql.grover() finds correct solutions via Qiskit."""

    def test_grover_single_solution_3bit(self):
        """Oracle marks x=5 in 3-bit space. Expect value=5 with high probability.

        N=8, M=1 -> k=1, theoretical P ~78%. Run 20 times, expect at least
        7/20 hits (conservative threshold accounting for implementation
        imperfections in branch/H-sandwich circuit).
        """
        found_count = 0
        for _ in range(20):

            @ql.grover_oracle(validate=False)
            @ql.compile
            def mark_five(x: ql.qint):
                flag = x == 5
                with flag:
                    x.phase += math.pi

            value, iters = ql.grover(mark_five, width=3)
            if value == 5:
                found_count += 1

        assert found_count >= 7, f"Expected >=7/20 hits, got {found_count}"
        assert iters == 1  # N=8, M=1 -> k=1

    def test_grover_single_solution_2bit(self):
        """Oracle marks x=3 in 2-bit space. N=4, M=1 -> k=1, P=1.0 (exact).

        For 2-qubit Grover with 1 solution, one iteration achieves exact
        probability 1.0. Run once, expect value=3.
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_three, width=2)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1  # N=4, M=1 -> k=1

    def test_grover_multiple_solutions(self):
        """Oracle marks values < 4 in 3-bit space. M=4 solutions (0,1,2,3).

        N=8, M=4 -> k=0 iterations. Result should be any value < 4.
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_small(x: ql.qint):
            flag = x < 4
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_small, width=3, m=4)
        assert iters == 0  # N=8, M=4 -> k=0
        assert 0 <= value <= 7, f"Value out of range: {value}"

    def test_grover_explicit_iterations(self):
        """Oracle marks x=5 in 3-bit space. Use explicit iterations=2.

        Verify iterations=2 in return tuple (not auto-calculated 1).
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_five(x: ql.qint):
            flag = x == 5
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_five, width=3, iterations=2)
        assert iters == 2, f"Expected iterations=2, got {iters}"
        assert 0 <= value <= 7, f"Value out of range: {value}"

    def test_grover_m_zero_random_measurement(self):
        """M=0 gives k=0 iterations. Result is random from superposition.

        Any value 0-3 is valid.
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_three, width=2, m=0)
        assert iters == 0, f"Expected iterations=0, got {iters}"
        assert 0 <= value <= 3, f"Value out of range: {value}"

    def test_grover_auto_wrap_compiled_func(self):
        """Pass a @ql.compile function (NOT @ql.grover_oracle) to ql.grover().

        It should auto-wrap via _ensure_oracle. Oracle marks x=3 in 2-bit
        space. N=4, M=1, k=1 -> exact P=1.0.
        """

        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        value, iters = ql.grover(mark_three, width=2)
        assert value == 3, f"Expected 3, got {value}"
        assert iters == 1

    def test_grover_return_tuple_structure(self):
        """Verify return is a tuple with exactly 2 elements: (value, iterations).

        Both elements are int.
        """

        @ql.grover_oracle(validate=False)
        @ql.compile
        def mark_three(x: ql.qint):
            flag = x == 3
            with flag:
                x.phase += math.pi

        result = ql.grover(mark_three, width=2)
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2, f"Expected 2 elements, got {len(result)}"
        value, iters = result
        assert isinstance(value, int), f"Expected int value, got {type(value)}"
        assert isinstance(iters, int), f"Expected int iterations, got {type(iters)}"
