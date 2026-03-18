"""Phase 1 integration test: end-to-end automatic uncomputation.

Exercises all Phase 1 subsystems (Steps 1.1-1.7) together in realistic
scenarios to verify they compose correctly:

1. with block with simple comparison
2. compound expression (a + 3) > 5
3. nested with blocks
4. variables surviving past with blocks
5. measurement discards history
6. eager uncomputation frees qubits
7. circuit output matches expected gate count

[Quantum_Assembly-2ab.8]
"""

import gc

import quantum_language as ql
from quantum_language._core import _get_circuit_active

# ---------------------------------------------------------------------------
# 1. with block with simple comparison
# ---------------------------------------------------------------------------


class TestWithBlockSimpleComparison:
    """End-to-end: simple comparison condition in a with block triggers
    history recording, controlled execution, and uncomputation on exit."""

    def test_eq_cq_records_then_uncomputes(self):
        """CQ equality: history recorded on creation, cleared on with exit."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5

        # Step 1.2: history was recorded
        assert len(cond.history) == 1
        seq_ptr, qm, num_anc, _kind = cond.history.entries[0]
        assert seq_ptr != 0
        assert isinstance(qm, tuple)
        assert len(qm) > 0

        gc_before = ql.get_gate_count()
        with cond:
            pass
        gc_after = ql.get_gate_count()

        # Step 1.3: __exit__ emitted inverse gates
        assert gc_after > gc_before
        # Step 1.3: history cleared after with block
        assert len(cond.history) == 0

    def test_gt_cq_records_then_uncomputes(self):
        """CQ greater-than: history recorded on creation, cleared on exit.

        Uses borrow-ancilla pattern (no widened temporaries / children).
        The key invariant is that history is cleared after the with block.
        """
        ql.circuit()
        a = ql.qint(6, width=4)
        cond = a > 3

        assert len(cond.history) >= 1
        with cond:
            pass

        # History cleared after with exit
        assert len(cond.history) == 0
        assert len(cond.history.children) == 0

    def test_with_block_controlled_arithmetic(self):
        """Arithmetic inside with block executes; uncomputation still runs."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = ql.qint(0, width=4)
        cond = a == 5

        gc_before_with = ql.get_gate_count()
        with cond:
            result += 1
        gc_after_with = ql.get_gate_count()

        # Gates emitted for both body and uncomputation
        assert gc_after_with > gc_before_with
        assert len(cond.history) == 0

    def test_inverse_gate_count_matches_forward(self):
        """Inverse gate count from __exit__ equals the forward comparison."""
        ql.circuit()
        a = ql.qint(5, width=4)
        gc_after_init = ql.get_gate_count()

        cond = a == 5
        gc_after_cmp = ql.get_gate_count()
        forward_gates = gc_after_cmp - gc_after_init

        with cond:
            pass
        gc_after_with = ql.get_gate_count()
        inverse_gates = gc_after_with - gc_after_cmp

        assert inverse_gates == forward_gates, f"Forward={forward_gates}, inverse={inverse_gates}"


# ---------------------------------------------------------------------------
# 2. compound expression (a + 3) > 5
# ---------------------------------------------------------------------------


class TestCompoundExpression:
    """End-to-end: compound expression creates temporaries tracked as
    children, and with-block exit cascades uncomputation to them."""

    def test_add_then_gt_creates_history(self):
        """(a + 3) > 5 produces a condition with history entries."""
        ql.circuit()
        a = ql.qint(4, width=4)
        temp = a + 3
        cond = temp > 5

        # Borrow-ancilla pattern: no widened temporaries (no children)
        assert len(cond.history) >= 1

    def test_compound_with_clears_history(self):
        """with (temp > 5): cascades uncomputation."""
        ql.circuit()
        a = ql.qint(4, width=4)
        temp = a + 3
        cond = temp > 5

        with cond:
            pass

        # History cleared after cascade
        assert len(cond.history.children) == 0
        assert len(cond.history) == 0

    def test_compound_preserves_input(self):
        """Input variable a is untouched after compound with block."""
        ql.circuit()
        a = ql.qint(4, width=4)
        original_history = len(a.history)
        temp = a + 3
        cond = temp > 5

        with cond:
            pass

        assert a.width == 4
        assert len(a.history) == original_history
        assert not a._is_uncomputed


# ---------------------------------------------------------------------------
# 3. nested with blocks
# ---------------------------------------------------------------------------


class TestNestedWithBlocksIntegration:
    """End-to-end: inner with block uncomputes before outer, each
    emitting inverse gates and clearing its own history."""

    def test_nested_history_ordering(self):
        """Inner condition history clears before outer."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        cond_outer = a == 5
        assert len(cond_outer.history) == 1

        with cond_outer:
            cond_inner = b == 3
            assert len(cond_inner.history) == 1
            with cond_inner:
                pass
            # Inner uncomputed first
            assert len(cond_inner.history) == 0
        # Then outer
        assert len(cond_outer.history) == 0

    def test_nested_gate_symmetry(self):
        """Each nesting level emits inverse gates matching its forward count."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)

        gc0 = ql.get_gate_count()
        cond_outer = a == 5
        gc1 = ql.get_gate_count()
        outer_forward = gc1 - gc0

        with cond_outer:
            gc2 = ql.get_gate_count()
            cond_inner = b == 3
            gc3 = ql.get_gate_count()
            inner_forward = gc3 - gc2

            with cond_inner:
                pass
            gc4 = ql.get_gate_count()
            inner_inverse = gc4 - gc3

            assert inner_inverse == inner_forward, (
                f"Inner: forward={inner_forward}, inverse={inner_inverse}"
            )
        gc5 = ql.get_gate_count()
        outer_inverse = gc5 - gc4

        assert outer_inverse == outer_forward, (
            f"Outer: forward={outer_forward}, inverse={outer_inverse}"
        )

    def test_nested_with_controlled_arithmetic(self):
        """Operations at each nesting depth emit gates; all histories clear."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        result = ql.qint(0, width=4)

        cond_outer = a == 5
        with cond_outer:
            result += 1
            cond_inner = b == 3
            with cond_inner:
                result += 1

        # Both histories cleared
        assert len(cond_outer.history) == 0
        assert len(cond_inner.history) == 0
        # Result and inputs preserved
        assert result.width == 4
        assert not result._is_uncomputed

    def test_triple_nested(self):
        """Three levels of nesting all uncompute correctly."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        c = ql.qint(7, width=4)

        c1 = a == 5
        with c1:
            c2 = b == 3
            with c2:
                c3 = c == 7
                with c3:
                    pass
                assert len(c3.history) == 0
            assert len(c2.history) == 0
        assert len(c1.history) == 0

        # All inputs preserved
        for var in [a, b, c]:
            assert var.width == 4
            assert not var._is_uncomputed


# ---------------------------------------------------------------------------
# 4. variables surviving past with blocks
# ---------------------------------------------------------------------------


class TestVariablesSurvivePastWith:
    """End-to-end: input variables, result variables, and other quantum
    values remain usable after with-block exit uncomputation."""

    def test_single_operand_preserved(self):
        """a is usable after with (a == 5): block."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        with cond:
            pass
        assert a.width == 4
        assert not a._is_uncomputed
        # Can still use a in further operations
        a += 1
        assert ql.get_gate_count() > 0

    def test_both_operands_preserved_qq(self):
        """Both a and b survive after with (a == b): block."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(5, width=4)
        cond = a == b
        with cond:
            pass
        assert a.width == 4
        assert b.width == 4
        assert not a._is_uncomputed
        assert not b._is_uncomputed

    def test_result_variable_preserved_after_controlled_op(self):
        """Result modified inside with block is still valid afterwards."""
        ql.circuit()
        a = ql.qint(5, width=4)
        result = ql.qint(0, width=4)
        cond = a == 5
        with cond:
            result += 1
        # Both a and result remain valid
        assert a.width == 4
        assert result.width == 4
        assert not a._is_uncomputed
        assert not result._is_uncomputed

    def test_variable_usable_after_nested_with(self):
        """Variables survive nested with blocks and remain usable."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        result = ql.qint(0, width=4)

        c1 = a == 5
        with c1:
            c2 = b == 3
            with c2:
                result += 1

        # All variables preserved
        assert a.width == 4
        assert b.width == 4
        assert result.width == 4
        assert not a._is_uncomputed
        assert not b._is_uncomputed
        assert not result._is_uncomputed

        # Can still use them
        gc_before = ql.get_gate_count()
        result += a
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before

    def test_condition_variable_survives_with_empty_history(self):
        """Condition qbool survives with empty history after with block."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        with cond:
            pass
        # cond still exists as a valid qbool, just with empty history
        assert cond.width == 1
        assert len(cond.history) == 0
        assert not cond._is_uncomputed


# ---------------------------------------------------------------------------
# 5. measurement discards history
# ---------------------------------------------------------------------------


class TestMeasurementDiscardsHistory:
    """End-to-end: measuring a variable clears its history, preventing
    both with-block and __del__ uncomputation paths."""

    def test_measure_clears_comparison_history(self):
        """Measuring a comparison result clears its history."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        assert len(cond.history) == 1

        cond.measure()
        assert len(cond.history) == 0

    def test_measure_then_del_no_gates(self):
        """After measurement, __del__ is a no-op (no inverse gates)."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        cond.measure()
        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()
        assert gc_after == gc_before

    def test_measure_clears_children(self):
        """Measurement clears history (borrow-ancilla: no children)."""
        ql.circuit()
        a = ql.qint(4, width=4)
        temp = a + 3
        cond = temp > 5

        cond.measure()
        assert len(cond.history.children) == 0
        assert len(cond.history) == 0

    def test_measure_preserves_input(self):
        """Measuring the condition does not affect input variables."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        cond.measure()
        assert a.width == 4
        assert not a._is_uncomputed
        assert len(a.history) == 0

    def test_measure_returns_value(self):
        """measure() returns the correct classical value."""
        ql.circuit()
        a = ql.qint(7, width=4)
        result = a.measure()
        assert result == 7
        assert len(a.history) == 0


# ---------------------------------------------------------------------------
# 6. eager uncomputation frees qubits
# ---------------------------------------------------------------------------


class TestEagerUncomputationFreesQubits:
    """End-to-end: with qubit_saving=True, __del__ on a temporary
    emits inverse gates and frees qubits back to the allocator."""

    def test_eager_del_frees_qubit(self):
        """In EAGER mode, deleting a comparison result reduces current_in_use."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5

        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        gc_before = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after = ql.get_gate_count()

        # Inverse gates emitted
        assert gc_after > gc_before

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        # Qubits freed: current_in_use decreased
        assert in_use_after < in_use_before, (
            f"Expected current_in_use to decrease: {in_use_before} -> {in_use_after}"
        )

    def test_eager_preserves_peak(self):
        """Peak allocation is not reduced by eager uncomputation."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5

        stats_before = ql.circuit_stats()
        peak_before = stats_before["peak_allocated"]

        del cond
        gc.collect()

        stats_after = ql.circuit_stats()
        peak_after = stats_after["peak_allocated"]

        assert peak_after >= peak_before

    def test_eager_no_double_uncompute(self):
        """Eager __del__ emits exactly one round of inverse gates."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)

        gc_after_init = ql.get_gate_count()
        cond = a == 5
        gc_after_cmp = ql.get_gate_count()
        forward_gates = gc_after_cmp - gc_after_init

        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        inverse_gates = gc_after_del - gc_after_cmp

        assert inverse_gates == forward_gates, (
            f"Double uncomputation? forward={forward_gates}, inverse={inverse_gates}"
        )

    def test_eager_bitwise_frees_qubit(self):
        """Bitwise AND temporary also frees qubits in EAGER mode."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        c = a & 0b0111

        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        del c
        gc.collect()

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        assert in_use_after < in_use_before

    def test_with_then_del_eager_no_extra_gates(self):
        """After with-block exit, EAGER del does not double-uncompute."""
        ql.circuit()
        ql.option("qubit_saving", True)
        a = ql.qint(5, width=4)
        cond = a == 5
        with cond:
            pass
        gc_after_exit = ql.get_gate_count()
        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        assert gc_after_del == gc_after_exit


# ---------------------------------------------------------------------------
# 7. circuit output matches expected gate count
# ---------------------------------------------------------------------------


class TestCircuitGateCountIntegration:
    """End-to-end: verify that complete scenarios produce the expected
    total gate counts, confirming forward + inverse symmetry."""

    def test_simple_comparison_with_symmetry(self):
        """Simple with block: total = init + forward + inverse = init + 2*forward."""
        ql.circuit()
        gc_start = ql.get_gate_count()
        a = ql.qint(5, width=4)
        gc_after_init = ql.get_gate_count()
        init_gates = gc_after_init - gc_start

        cond = a == 5
        gc_after_cmp = ql.get_gate_count()
        forward_gates = gc_after_cmp - gc_after_init

        with cond:
            pass
        gc_after_with = ql.get_gate_count()
        inverse_gates = gc_after_with - gc_after_cmp

        # Forward and inverse are symmetric
        assert forward_gates == inverse_gates
        # Total is deterministic
        total = gc_after_with - gc_start
        assert total == init_gates + 2 * forward_gates

    def test_nested_comparison_with_symmetry(self):
        """Nested with: each level's inverse matches its forward."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)

        gc0 = ql.get_gate_count()
        c_outer = a == 5
        gc1 = ql.get_gate_count()
        outer_fwd = gc1 - gc0

        with c_outer:
            gc2 = ql.get_gate_count()
            c_inner = b == 3
            gc3 = ql.get_gate_count()
            inner_fwd = gc3 - gc2

            with c_inner:
                pass
            gc4 = ql.get_gate_count()
            inner_inv = gc4 - gc3
            assert inner_inv == inner_fwd

        gc5 = ql.get_gate_count()
        outer_inv = gc5 - gc4
        assert outer_inv == outer_fwd

        # Total gates: init(a) + init(b) + outer_fwd + inner_fwd + inner_inv + outer_inv
        init_gates = gc0
        expected = init_gates + outer_fwd + inner_fwd + inner_inv + outer_inv
        assert gc5 == expected

    def test_del_gate_count_matches_forward(self):
        """__del__ inverse gate count equals forward comparison count."""
        ql.circuit()
        a = ql.qint(5, width=4)
        gc_after_init = ql.get_gate_count()

        cond = a == 5
        gc_after_cmp = ql.get_gate_count()
        forward_gates = gc_after_cmp - gc_after_init

        del cond
        gc.collect()
        gc_after_del = ql.get_gate_count()
        inverse_gates = gc_after_del - gc_after_cmp

        assert inverse_gates == forward_gates

    def test_circuit_stats_consistency(self):
        """circuit_stats fields are consistent after a full scenario."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)

        cond = a == 5
        with cond:
            pass

        stats = ql.circuit_stats()
        # Peak should be at least the qubits for a + b + comparison result
        assert stats["peak_allocated"] >= a.width + b.width
        # Total allocations should be positive
        assert stats["total_allocations"] > 0
        # Current in use should be non-negative
        assert stats["current_in_use"] >= 0


# ---------------------------------------------------------------------------
# Full end-to-end scenario combining all subsystems
# ---------------------------------------------------------------------------


class TestFullEndToEnd:
    """Comprehensive scenario that exercises all Phase 1 subsystems
    in a single realistic workflow."""

    def test_complete_scenario(self):
        """Full workflow: create, compare, nest, measure, verify gate counts."""
        ql.circuit()
        assert _get_circuit_active()

        # Create input variables (Step 1.1: empty history)
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        result = ql.qint(0, width=4)
        assert len(a.history) == 0
        assert len(b.history) == 0
        assert len(result.history) == 0

        # Simple comparison (Step 1.2: records history)
        gc_before_cmp = ql.get_gate_count()
        cond1 = a == 5
        gc_after_cmp = ql.get_gate_count()
        fwd1 = gc_after_cmp - gc_before_cmp
        assert len(cond1.history) == 1
        assert fwd1 > 0

        # with block with controlled ops and uncomputation (Step 1.3)
        with cond1:
            result += 1
        assert len(cond1.history) == 0

        # Compound expression (borrow-ancilla: no widened temp children)
        temp = a + 3
        cond2 = temp > 5
        assert len(cond2.history) >= 1

        with cond2:
            result += 1
        assert len(cond2.history) == 0
        assert len(cond2.history.children) == 0

        # Nested with (Step 1.3)
        cond3 = a == 5
        with cond3:
            cond4 = b == 3
            with cond4:
                result += 1
            assert len(cond4.history) == 0
        assert len(cond3.history) == 0

        # Variables survive (Step 1.3 live-variable preservation)
        assert a.width == 4
        assert b.width == 4
        assert result.width == 4
        assert not a._is_uncomputed
        assert not b._is_uncomputed
        assert not result._is_uncomputed

        # Measurement discards history (Step 1.5)
        cond5 = a == 5
        assert len(cond5.history) == 1
        cond5.measure()
        assert len(cond5.history) == 0

        # __del__ after measurement is a no-op
        gc_before_del = ql.get_gate_count()
        del cond5
        gc.collect()
        gc_after_del = ql.get_gate_count()
        assert gc_after_del == gc_before_del

        # Gate count is positive and consistent
        total_gates = ql.get_gate_count()
        assert total_gates > 0

        # circuit_stats is consistent
        stats = ql.circuit_stats()
        assert stats["peak_allocated"] > 0
        assert stats["total_allocations"] > 0
        assert stats["current_in_use"] >= 0

    def test_eager_complete_scenario(self):
        """Full workflow with qubit_saving=True: eager uncomputation."""
        ql.circuit()
        ql.option("qubit_saving", True)

        a = ql.qint(5, width=4)

        # Create and immediately discard a comparison (eager path)
        gc_before = ql.get_gate_count()
        cond = a == 5
        gc_after_cmp = ql.get_gate_count()
        forward = gc_after_cmp - gc_before

        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        del cond
        gc.collect()

        gc_after_del = ql.get_gate_count()
        inverse = gc_after_del - gc_after_cmp

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        # Inverse matches forward (no double-uncompute)
        assert inverse == forward
        # Qubits were freed
        assert in_use_after < in_use_before
        # Peak was not reduced
        assert stats_after["peak_allocated"] >= stats_before["peak_allocated"]

    def test_exception_in_with_still_uncomputes(self):
        """Exception in with-body does not prevent uncomputation."""
        ql.circuit()
        a = ql.qint(5, width=4)
        cond = a == 5
        assert len(cond.history) == 1

        gc_before = ql.get_gate_count()
        try:
            with cond:
                raise ValueError("test error")
        except ValueError:
            pass
        gc_after = ql.get_gate_count()

        # Inverse gates emitted despite exception
        assert gc_after > gc_before
        # History cleared
        assert len(cond.history) == 0
        # Input preserved
        assert a.width == 4
        assert not a._is_uncomputed
