"""End-to-end verification for BUG-1 and BUG-2 fixes.

Issue: Quantum_Assembly-7i1

BUG-1: Division now dispatches to controlled C functions, producing
different (higher) gate counts when called inside a with-block.

BUG-2: Bitwise and equality ops no longer skip gate emission in
Toffoli compile-mode. A @ql.compile function using ==, &, ^, ~, and
with blocks produces non-zero original_gate_count matching direct execution.
"""

import gc
import warnings

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestBug1ControlledDivision:
    """BUG-1: Controlled division produces more gates than uncontrolled."""

    def test_divmod_cq_controlled_vs_uncontrolled(self):
        """divmod_cq gate count differs between controlled and uncontrolled."""
        # Uncontrolled
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        a = ql.qint(7, width=4)
        _ = a // 3
        uncontrolled_gates = ql.get_gate_count()

        # Controlled
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        b = ql.qint(7, width=4)
        c = ql.qbool(True)
        with c:
            _ = b // 3
        controlled_gates = ql.get_gate_count()

        assert uncontrolled_gates > 0, "Uncontrolled should produce gates"
        assert controlled_gates > uncontrolled_gates, (
            f"Controlled ({controlled_gates}) should produce more gates "
            f"than uncontrolled ({uncontrolled_gates})"
        )


class TestBug2CompileGateCount:
    """BUG-2: Compiled functions with bitwise/eq ops have correct gate counts."""

    def test_compiled_eq_nonzero_gate_count(self):
        """@ql.compile with == produces non-zero original_gate_count."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile
        def check_eq(x):
            eq = x == 5
            with eq:
                x += 1
            return x

        a = ql.qint(0, width=4)
        _ = check_eq(a)

        block = list(check_eq._cache.values())[0]
        assert block.original_gate_count > 0, (
            f"original_gate_count should be > 0, got {block.original_gate_count}"
        )

    def test_compiled_bitwise_nonzero_gate_count(self):
        """@ql.compile with &, ^, ~ produces non-zero original_gate_count."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile
        def bitwise_ops(x, y):
            _a = x & y  # noqa: F841
            _b = x ^ y  # noqa: F841
            _c = ~x  # noqa: F841
            return x

        x = ql.qint(0, width=4)
        y = ql.qint(0, width=4)
        _ = bitwise_ops(x, y)

        block = list(bitwise_ops._cache.values())[0]
        assert block.original_gate_count > 0, (
            f"original_gate_count should be > 0, got {block.original_gate_count}"
        )

    def test_compiled_matches_direct_execution(self):
        """@ql.compile gate count matches direct (uncompiled) execution.

        This is the key regression test: a compiled function using ==, &, ^, ~,
        and with blocks should produce non-zero original_gate_count that is
        close to direct execution (not the old buggy zero).
        """
        # --- Direct execution ---
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        x = ql.qint(0, width=4)
        y = ql.qint(0, width=4)

        eq = x == 3
        _a = x & y  # noqa: F841
        _b = x ^ y  # noqa: F841
        _c = ~x  # noqa: F841
        with eq:
            y += 1

        direct_gates = ql.get_gate_count()

        # --- Compiled execution ---
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile
        def mixed_ops(x, y):
            eq = x == 3
            _a = x & y  # noqa: F841
            _b = x ^ y  # noqa: F841
            _c = ~x  # noqa: F841
            with eq:
                y += 1
            return y

        x2 = ql.qint(0, width=4)
        y2 = ql.qint(0, width=4)
        _ = mixed_ops(x2, y2)

        block = list(mixed_ops._cache.values())[0]
        compiled_gates = block.original_gate_count

        assert direct_gates > 0, "Direct execution should produce gates"
        assert compiled_gates > 0, (
            f"Compiled original_gate_count should be > 0, got {compiled_gates}"
        )
        # Gate counts should be close (may differ slightly due to ancilla
        # management in compiled mode), but both must be non-zero.
        # Before BUG-2 fix, compiled_gates was ~0 (missing ~24 gates).
        assert abs(compiled_gates - direct_gates) < direct_gates * 0.2, (
            f"Compiled ({compiled_gates}) and direct ({direct_gates}) should "
            f"be within 20% of each other"
        )

    def test_compiled_with_inverse_nonzero(self):
        """@ql.compile(inverse=True) with bitwise/eq ops has non-zero gate count."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(inverse=True)
        def oracle(x):
            eq = x == 5
            _inv = ~x  # noqa: F841
            with eq:
                x += 1
            return x

        a = ql.qint(0, width=4)
        _ = oracle(a)

        block = list(oracle._cache.values())[0]
        assert block.original_gate_count > 0, (
            f"original_gate_count should be > 0, got {block.original_gate_count}"
        )
