"""Benchmark tests for qint operations.

Run with: pytest tests/benchmarks/ -v --benchmark-only
Or skip benchmarks: pytest tests/benchmarks/ --benchmark-skip

These tests measure circuit generation performance,
not quantum execution performance.

Note: Operations that allocate new qubits (add, mul, bitwise) require
fresh circuits per iteration to avoid qubit exhaustion. We use
benchmark.pedantic with setup functions for these cases.
"""

import pytest

# Skip entire module if pytest-benchmark not installed
pytest.importorskip("pytest_benchmark")

import quantum_language as ql


class TestQintAddition:
    """Benchmark qint addition operations."""

    def test_add_8bit(self, benchmark):
        """Benchmark 8-bit qint addition."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_add(a, b):
            return a + b

        benchmark.pedantic(do_add, setup=setup, rounds=100, warmup_rounds=5)

    def test_add_16bit(self, benchmark):
        """Benchmark 16-bit qint addition."""

        def setup():
            ql.circuit()
            a = ql.qint(12345, width=16)
            b = ql.qint(6789, width=16)
            return (a, b), {}

        def do_add(a, b):
            return a + b

        benchmark.pedantic(do_add, setup=setup, rounds=100, warmup_rounds=5)

    @pytest.mark.parametrize("width", [4, 8, 16, 32])
    def test_add_scaling(self, benchmark, width):
        """Benchmark addition scaling with bit width."""

        def setup():
            ql.circuit()
            a = ql.qint(1, width=width)
            b = ql.qint(1, width=width)
            return (a, b), {}

        def do_add(a, b):
            return a + b

        benchmark.pedantic(do_add, setup=setup, rounds=50, warmup_rounds=3)

    def test_iadd_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit in-place addition (no qubit allocation)."""
        a = ql.qint(5, width=8)

        def do_iadd():
            nonlocal a
            a += 3
            return a

        benchmark(do_iadd)

    def test_iadd_quantum_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit in-place quantum addition (no qubit allocation)."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        def do_iadd():
            nonlocal a
            a += b
            return a

        benchmark(do_iadd)


class TestQintMultiplication:
    """Benchmark qint multiplication operations."""

    def test_mul_8bit(self, benchmark):
        """Benchmark 8-bit qint multiplication."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_mul(a, b):
            return a * b

        benchmark.pedantic(do_mul, setup=setup, rounds=50, warmup_rounds=3)

    def test_mul_classical(self, benchmark):
        """Benchmark qint * classical multiplication."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            return (a,), {}

        def do_mul(a):
            return a * 3

        benchmark.pedantic(do_mul, setup=setup, rounds=50, warmup_rounds=3)


class TestQintBitwise:
    """Benchmark qint bitwise operations."""

    def test_xor_8bit(self, benchmark):
        """Benchmark 8-bit qint XOR."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_xor(a, b):
            return a ^ b

        benchmark.pedantic(do_xor, setup=setup, rounds=100, warmup_rounds=5)

    def test_and_8bit(self, benchmark):
        """Benchmark 8-bit qint AND."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_and(a, b):
            return a & b

        benchmark.pedantic(do_and, setup=setup, rounds=100, warmup_rounds=5)

    def test_or_8bit(self, benchmark):
        """Benchmark 8-bit qint OR."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_or(a, b):
            return a | b

        benchmark.pedantic(do_or, setup=setup, rounds=100, warmup_rounds=5)


class TestQintComparison:
    """Benchmark qint comparison operations."""

    def test_eq_8bit(self, benchmark):
        """Benchmark 8-bit qint equality comparison."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_eq(a, b):
            return a == b

        benchmark.pedantic(do_eq, setup=setup, rounds=100, warmup_rounds=5)

    def test_lt_8bit(self, benchmark):
        """Benchmark 8-bit qint less-than comparison."""

        def setup():
            ql.circuit()
            a = ql.qint(5, width=8)
            b = ql.qint(3, width=8)
            return (a, b), {}

        def do_lt(a, b):
            return a < b

        benchmark.pedantic(do_lt, setup=setup, rounds=100, warmup_rounds=5)


class TestCircuitCreation:
    """Benchmark circuit setup overhead."""

    def test_circuit_creation(self, benchmark):
        """Benchmark circuit() call overhead."""
        benchmark(ql.circuit)

    def test_qint_creation_8bit(self, benchmark):
        """Benchmark qint creation."""

        def setup():
            ql.circuit()
            return (), {}

        def do_create():
            return ql.qint(5, width=8)

        benchmark.pedantic(do_create, setup=setup, rounds=100, warmup_rounds=5)

    def test_qint_creation_16bit(self, benchmark):
        """Benchmark 16-bit qint creation."""

        def setup():
            ql.circuit()
            return (), {}

        def do_create():
            return ql.qint(12345, width=16)

        benchmark.pedantic(do_create, setup=setup, rounds=100, warmup_rounds=5)
